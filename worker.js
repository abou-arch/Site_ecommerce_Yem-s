/* ===========================================================================
   Yem's — Adaptateur Cloudflare Workers

   Seul fichier qui connaît Request et Response. Toute la logique vit dans
   api/_lib/handlers.js, qui ne dépend d'aucun hébergeur : changer de
   plateforme demain ne toucherait que ce fichier.

   Les pages HTML passent par ce Worker (run_worker_first dans
   wrangler.toml) pour recevoir les corrections de l'atelier ; les fichiers
   de assets/ sont servis directement, sans lui.
   =========================================================================== */

import {
  createOrder, verifyPayment, handleWebhook,
  adminAuthorized, listOrders, setOrderStatus,
  listCatalogue, saveProduct, anonymizeOrder, deleteOrder,
} from './api/_lib/handlers.js';
import { webhookIsAuthentic } from './api/_lib/kkiapay.js';
import { lireCorrections } from './api/_lib/overrides.js';
import { deposer, servir } from './api/_lib/media.js';
import { reecrire } from './api/_lib/rewrite.js';

/* Les pages et fichiers statiques reçoivent leurs en-têtes de sécurité de
   _headers. Ce que le Worker fabrique lui-même n'en recevait aucun : une
   réponse d'API n'a rien à charger, rien à exécuter, et rien à faire dans
   un cadre. */
const JSON_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
};

const reply = ({ status, body }) =>
  new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });

const fail = (message, status) =>
  new Response(JSON.stringify({ ok: false, error: message }), { status, headers: JSON_HEADERS });

const CORPS_MAX = 128 * 1024;

/** Corps JSON, borné : une charge utile démesurée ne doit pas nous occuper. */
async function body(request) {
  const length = Number(request.headers.get('content-length') || 0);
  if (length > CORPS_MAX) throw new Error('corps trop volumineux');
  const text = await request.text();
  // Envoyé par morceaux, un corps n'annonce pas sa taille : on la vérifie après.
  if (text.length > CORPS_MAX) throw new Error('corps trop volumineux');
  const data = text ? JSON.parse(text) : {};
  // « null », un nombre ou un tableau sont du JSON valide mais pas une
  // requête : les handlers lisaient payload.country sur null et répondaient 500.
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('JSON attendu : un objet');
  }
  return data;
}

/* Garde-fou minimal contre le martèlement. La mémoire d'une isolate n'est pas
   partagée entre régions : ça n'a pas valeur de rate-limit global, mais ça
   arrête un script naïf sans rien coûter. Pour un vrai plafond, utiliser
   le Rate Limiting de Cloudflare, réglable depuis le tableau de bord.
   Chaque famille de routes a son propre compteur : consulter l'admin ne doit
   pas consommer le quota de commandes de la même adresse. */
const hits = new Map();

function throttled(request, max = 20, windowMs = 60_000, famille = 'api') {
  const ip = request.headers.get('cf-connecting-ip') || 'inconnu';
  const cle = `${famille}|${ip}`;
  const now = Date.now();
  const seen = hits.get(cle);

  if (!seen || now > seen.reset) {
    hits.set(cle, { count: 1, reset: now + windowMs });
    if (hits.size > 500) for (const [k, v] of hits) if (now > v.reset) hits.delete(k);
    return false;
  }
  seen.count += 1;
  return seen.count > max;
}

/* Mauvais jetons admin, par adresse. Au-delà de dix en un quart d'heure,
   l'adresse n'est plus écoutée, même avec le bon jeton : sinon le blocage
   n'arrêterait rien, l'essai gagnant passerait quand même. Le jeton généré
   à l'installation (64 caractères hexadécimaux) ne se devine pas ; ce verrou
   protège le cas où un mot de passe plus faible aurait été choisi. */
const ECHECS_MAX = 10;
const ECHECS_FENETRE = 15 * 60_000;
const echecs = new Map();

function adminBloque(ip) {
  const e = echecs.get(ip);
  return Boolean(e && Date.now() < e.reset && e.count >= ECHECS_MAX);
}

function noterEchec(ip) {
  const now = Date.now();
  const e = echecs.get(ip);
  if (!e || now > e.reset) {
    echecs.set(ip, { count: 1, reset: now + ECHECS_FENETRE });
    if (echecs.size > 500) for (const [k, v] of echecs) if (now > v.reset) echecs.delete(k);
  } else {
    e.count += 1;
  }
}

const bearer = (request) => {
  const header = request.headers.get('authorization') || '';
  return header.startsWith('Bearer ') ? header.slice(7) : '';
};

/** Rend une réponse de refus, ou null si la requête admin peut passer. */
function gardeAdmin(request, env) {
  const ip = request.headers.get('cf-connecting-ip') || 'inconnu';
  if (adminBloque(ip)) return fail('trop de tentatives, réessayez dans un quart d’heure', 429);
  if (!adminAuthorized(bearer(request), env)) {
    noterEchec(ip);
    return fail('accès refusé', 401);
  }
  if (throttled(request, 60, 60_000, 'admin')) return fail('trop de requêtes', 429);
  return null;
}

/* Une page d'un autre site peut faire poster le navigateur de ses visiteurs
   ici : un formulaire, ou un fetch en text/plain, part sans demander
   l'autorisation CORS. N'importe quel site pouvait ainsi déposer des
   commandes au nom de ses visiteurs, depuis autant d'adresses IP, donc hors
   de portée du limiteur, et autant d'alertes pour l'atelier. On exige notre
   propre origine quand le navigateur l'annonce, et du JSON, qu'un autre
   site ne peut pas envoyer sans une pré-vérification CORS que nous
   n'accordons pas. */
function requeteEtrangere(request, { json = true } = {}) {
  const origine = request.headers.get('origin');
  if (origine && origine !== new URL(request.url).origin) return fail('origine refusée', 403);
  const type = (request.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
  if (json && type !== 'application/json') return fail('contenu JSON attendu', 415);
  return null;
}

const estHtml = (reponse) => (reponse.headers.get('content-type') || '').includes('text/html');

/** Pages et fichiers statiques, corrigés au vol par ce que l'atelier a modifié. */
async function servirPage(request, env) {
  let asset = await env.ASSETS.fetch(request);

  // La page 404 est servie ici plutôt que par not_found_handling : ce réglage
  // court-circuitait le Worker et répondait du HTML sur les routes /api/*.
  // Ses en-têtes sont gardés : ce sont ceux de _headers, CSP comprise.
  if (asset.status === 404) {
    const notFound = await env.ASSETS.fetch(new URL('/404.html', request.url));
    return new Response(notFound.body, { status: 404, headers: notFound.headers });
  }

  /* Le catalogue statique est corrigé au vol par ce que l'atelier a
     modifié. Quand rien n'a été modifié — le cas courant — la réponse part
     telle quelle, sans rien analyser. Un navigateur qui revalide sa copie
     (304) alors que des corrections existent reçoit la page entière : sa
     copie peut dater d'avant le dernier changement de prix. */
  const navigation = (request.headers.get('accept') || '').includes('text/html');
  if (!((asset.status === 200 && estHtml(asset)) || (asset.status === 304 && navigation))) {
    return asset;
  }

  let corrections = {};
  try {
    corrections = await lireCorrections(env);
  } catch (err) {
    console.error('[corrections]', err?.message);
  }
  if (Object.keys(corrections).length === 0) return asset;

  if (asset.status === 304) {
    const entetes = new Headers(request.headers);
    entetes.delete('if-none-match');
    entetes.delete('if-modified-since');
    asset = await env.ASSETS.fetch(new Request(request, { headers: entetes }));
    if (!(asset.status === 200 && estHtml(asset))) return asset;
  }

  try {
    return reecrire(asset, corrections);
  } catch (err) {
    // Une correction ratée ne doit jamais faire tomber la boutique :
    // on sert la page d'origine, prix d'hier compris.
    console.error('[reecriture]', err?.message);
    return asset;
  }
}

export default {
  async fetch(request, env, ctx) {
    const { pathname, searchParams } = new URL(request.url);
    const method = request.method;

    /* ------------------------------------------------------------- photos
       Les fichiers déposés par l'atelier vivent dans R2, pas dans le dépôt.
       Leur nom contient un jeton aléatoire, donc leur contenu ne change
       jamais : ils peuvent être gardés en cache pour un an. */
    if (pathname.startsWith('/media/')) {
      if (method !== 'GET' && method !== 'HEAD') return fail('méthode non autorisée', 405);
      let fichier;
      try {
        fichier = decodeURIComponent(pathname.slice(7));
      } catch {
        // « %E0%A4%A » n'est pas un encodage valide : l'exception remontait
        // jusqu'au client sous forme de page d'erreur Cloudflare.
        return fail('photo introuvable', 404);
      }
      const photo = await servir(env.MEDIA, fichier);
      if (!photo) return fail('photo introuvable', 404);
      return new Response(photo.corps, {
        headers: {
          'Content-Type': photo.type,
          'Cache-Control': 'public, max-age=31536000, immutable',
          ETag: photo.etag,
          // Une image et rien d'autre : ni devinette de type par le
          // navigateur, ni script si le fichier se faisait passer pour une page.
          'X-Content-Type-Options': 'nosniff',
          'Content-Security-Policy': 'sandbox',
        },
      });
    }

    // Tout ce qui n'est pas une route d'API repart vers les fichiers statiques.
    if (!pathname.startsWith('/api/')) {
      if (!env.ASSETS) return fail('route inconnue', 404);
      return servirPage(request, env);
    }

    try {
      /* ------------------------------------------------------- diagnostic
         Répond sans authentification et sans toucher à la base : si cette
         route renvoie du JSON, c'est que le Worker est bien atteint. Le
         détail des réglages est sur /api/admin/health : dire publiquement
         quelles clés manquent renseigne d'abord un attaquant. */
      if (pathname === '/api/health') {
        return reply({ status: 200, body: { ok: true, worker: 'yems' } });
      }

      // Toute écriture publique doit venir de nos propres pages.
      if (method === 'POST' && pathname !== '/api/webhooks/kkiapay') {
        const refus = requeteEtrangere(request, { json: pathname !== '/api/admin/media' });
        if (refus) return refus;
      }

      /* ------------------------------------------------ création de commande */
      if (pathname === '/api/orders/create') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        if (throttled(request, 12, 60_000, 'commande')) return fail('trop de requêtes, réessayez dans une minute', 429);
        return reply(await createOrder(await body(request), env));
      }

      /* -------------------------------------------------------- vérification */
      if (pathname === '/api/payments/verify') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        if (throttled(request, 20, 60_000, 'paiement')) return fail('trop de requêtes', 429);
        return reply(await verifyPayment(await body(request), env));
      }

      /* -------------------------------------------------------------- webhook */
      if (pathname === '/api/webhooks/kkiapay') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        const secret = request.headers.get('x-kkiapay-secret');
        // KkiaPay réessaie si on ne répond pas vite : on acquitte dès que la
        // signature est validée, et on laisse le traitement finir en tâche de fond.
        // La signature est vérifiée avant de lire le corps : un appel non
        // signé ne nous fait même pas analyser son JSON.
        if (!webhookIsAuthentic(secret, env)) return fail('signature invalide', 401);
        return reply(await handleWebhook(await body(request), secret, env));
      }

      /* ---------------------------------------------------------------- admin
         Une seule porte pour toutes les routes d'administration : jeton,
         blocage après échecs répétés, puis limitation du débit. */
      if (pathname.startsWith('/api/admin/')) {
        const refus = gardeAdmin(request, env);
        if (refus) return refus;
      }

      if (pathname === '/api/admin/health') {
        return reply({
          status: 200,
          body: {
            ok: true,
            worker: 'yems',
            payment_mode: env.PAYMENT_MODE || 'offline',
            configured: {
              hyperdrive: Boolean(env.HYPERDRIVE),
              admin_token: Boolean(env.ADMIN_TOKEN),
              owner_whatsapp: Boolean(env.OWNER_WHATSAPP),
              kkiapay_public: Boolean(env.KKIAPAY_PUBLIC_KEY),
              kkiapay_private: Boolean(env.KKIAPAY_PRIVATE_KEY),
              kkiapay_secret: Boolean(env.KKIAPAY_SECRET_KEY),
              kkiapay_sandbox: env.KKIAPAY_SANDBOX === 'true',
            },
          },
        });
      }

      if (pathname === '/api/admin/orders') {
        if (method === 'GET') {
          return reply(await listOrders({
            status: searchParams.get('status') || '',
            limit: searchParams.get('limit'),
          }, env));
        }
        if (method === 'POST') {
          return reply(await setOrderStatus(await body(request), env));
        }
        return fail('méthode non autorisée', 405);
      }

      /* ------------------------------------------- nettoyage des commandes */
      if (pathname === '/api/admin/orders/anonymize' ||
          pathname === '/api/admin/orders/delete') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        const payload = await body(request);
        return reply(pathname.endsWith('/anonymize')
          ? await anonymizeOrder(payload, env)
          : await deleteOrder(payload, env));
      }

      /* ------------------------------------------------ catalogue, atelier */
      if (pathname === '/api/admin/catalogue') {
        if (method === 'GET') return reply(await listCatalogue(env));
        if (method === 'POST') return reply(await saveProduct(await body(request), env));
        return fail('méthode non autorisée', 405);
      }

      /* ------------------------------------------------------ dépôt d'une photo
         Le corps est le fichier brut, pas un formulaire multipart : sur un
         Worker, lire un multipart demande de tout charger en mémoire, alors
         qu'ici le flux part directement vers R2. */
      if (pathname === '/api/admin/media') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        if (throttled(request, 30, 60_000, 'photo')) return fail('trop d’envois, patientez une minute', 429);

        const slug = searchParams.get('slug') || 'piece';
        const taille = Number(request.headers.get('content-length') || 0);
        if (taille > 6 * 1024 * 1024) return fail('photo trop lourde : 6 Mo maximum', 413);

        const buffer = await request.arrayBuffer();
        const rangee = await deposer(env.MEDIA, slug, buffer);
        if (rangee.error) return fail(rangee.error, 400);
        return reply({ status: 201, body: { ok: true, photo: rangee } });
      }

      return fail('route inconnue', 404);
    } catch (err) {
      // Le détail part dans les logs, jamais dans la réponse : un message
      // d'erreur bavard renseigne autant l'attaquant que le développeur.
      console.error(`[${method} ${pathname}]`, err?.stack || err?.message);
      const clientFault = /JSON|corps trop volumineux/.test(err?.message || '');
      return fail(clientFault ? 'requête illisible' : 'erreur serveur', clientFault ? 400 : 500);
    }
  },
};
