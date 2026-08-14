/* ===========================================================================
   Yem's — Adaptateur Cloudflare Workers

   Seul fichier qui connaît Request et Response. Toute la logique vit dans
   api/_lib/handlers.js, qui ne dépend d'aucun hébergeur : changer de
   plateforme demain ne toucherait que ce fichier.

   Les pages statiques sont servies par Cloudflare Pages ; ce Worker ne
   répond qu'aux routes /api/*.
   =========================================================================== */

import {
  createOrder, verifyPayment, handleWebhook,
  adminAuthorized, listOrders, setOrderStatus,
  listCatalogue, saveProduct, anonymizeOrder, deleteOrder,
} from './api/_lib/handlers.js';
import { lireCorrections } from './api/_lib/overrides.js';
import { deposer, servir } from './api/_lib/media.js';
import { reecrire } from './api/_lib/rewrite.js';

const JSON_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
};

const reply = ({ status, body }) =>
  new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });

const fail = (message, status) =>
  new Response(JSON.stringify({ ok: false, error: message }), { status, headers: JSON_HEADERS });

/** Corps JSON, borné : une charge utile démesurée ne doit pas nous occuper. */
async function body(request) {
  const length = Number(request.headers.get('content-length') || 0);
  if (length > 128 * 1024) throw new Error('corps trop volumineux');
  const text = await request.text();
  return text ? JSON.parse(text) : {};
}

/* Garde-fou minimal contre le martèlement. La mémoire d'une isolate n'est pas
   partagée entre régions : ça n'a pas valeur de rate-limit global, mais ça
   arrête un script naïf sans rien coûter. Pour un vrai plafond, utiliser
   le Rate Limiting de Cloudflare, réglable depuis le tableau de bord. */
const hits = new Map();

function throttled(request, max = 20, windowMs = 60_000) {
  const ip = request.headers.get('cf-connecting-ip') || 'inconnu';
  const now = Date.now();
  const seen = hits.get(ip);

  if (!seen || now > seen.reset) {
    hits.set(ip, { count: 1, reset: now + windowMs });
    if (hits.size > 500) for (const [k, v] of hits) if (now > v.reset) hits.delete(k);
    return false;
  }
  seen.count += 1;
  return seen.count > max;
}

const bearer = (request) => {
  const header = request.headers.get('authorization') || '';
  return header.startsWith('Bearer ') ? header.slice(7) : '';
};

export default {
  async fetch(request, env, ctx) {
    const { pathname, searchParams } = new URL(request.url);
    const method = request.method;

    /* ------------------------------------------------------------- photos
       Les fichiers déposés par l'atelier vivent dans R2, pas dans le dépôt.
       Leur nom contient un jeton aléatoire, donc leur contenu ne change
       jamais : ils peuvent être gardés en cache pour un an. */
    if (pathname.startsWith('/media/')) {
      const fichier = decodeURIComponent(pathname.slice(7));
      const photo = await servir(env.MEDIA, fichier);
      if (!photo) return fail('photo introuvable', 404);
      return new Response(photo.corps, {
        headers: {
          'Content-Type': photo.type,
          'Cache-Control': 'public, max-age=31536000, immutable',
          ETag: photo.etag,
        },
      });
    }

    // Tout ce qui n'est pas une route d'API repart vers les fichiers statiques.
    // La page 404 est servie ici plutôt que par not_found_handling : ce réglage
    // court-circuitait le Worker et répondait du HTML sur les routes /api/*.
    if (!pathname.startsWith('/api/')) {
      if (!env.ASSETS) return fail('route inconnue', 404);

      const asset = await env.ASSETS.fetch(request);

      /* Le catalogue statique est corrigé au vol par ce que l'atelier a
         modifié. Quand rien n'a été modifié — le cas courant — reecrire()
         rend la réponse telle quelle, sans rien analyser. */
      if (asset.status === 200 &&
          (asset.headers.get('content-type') || '').includes('text/html')) {
        try {
          return reecrire(asset, await lireCorrections(env));
        } catch (err) {
          // Une correction ratée ne doit jamais faire tomber la boutique :
          // on sert la page d'origine, prix d'hier compris.
          console.error('[reecriture]', err?.message);
          return asset;
        }
      }
      if (asset.status !== 404) return asset;

      const notFound = await env.ASSETS.fetch(new URL('/404.html', request.url));
      return new Response(notFound.body, {
        status: 404,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
      });
    }

    try {
      /* ------------------------------------------------------- diagnostic
         Répond sans authentification et sans toucher à la base : si cette
         route renvoie du JSON, c'est que le Worker est bien atteint. Elle
         indique quels réglages sont posés, jamais leur valeur. */
      if (pathname === '/api/health') {
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
            },
          },
        });
      }

      /* ------------------------------------------------ création de commande */
      if (pathname === '/api/orders/create') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        if (throttled(request, 12)) return fail('trop de requêtes, réessayez dans une minute', 429);
        return reply(await createOrder(await body(request), env));
      }

      /* -------------------------------------------------------- vérification */
      if (pathname === '/api/payments/verify') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        if (throttled(request, 20)) return fail('trop de requêtes', 429);
        return reply(await verifyPayment(await body(request), env));
      }

      /* -------------------------------------------------------------- webhook */
      if (pathname === '/api/webhooks/kkiapay') {
        if (method !== 'POST') return fail('méthode non autorisée', 405);
        const secret = request.headers.get('x-kkiapay-secret');
        // KkiaPay réessaie si on ne répond pas vite : on acquitte dès que la
        // signature est validée, et on laisse le traitement finir en tâche de fond.
        return reply(await handleWebhook(await body(request), secret, env));
      }

      /* ---------------------------------------------------------------- admin */
      if (pathname === '/api/admin/orders') {
        if (throttled(request, 60)) return fail('trop de requêtes', 429);
        if (!adminAuthorized(bearer(request), env)) return fail('accès refusé', 401);

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
        if (!adminAuthorized(bearer(request), env)) return fail('accès refusé', 401);
        const payload = await body(request);
        return reply(pathname.endsWith('/anonymize')
          ? await anonymizeOrder(payload, env)
          : await deleteOrder(payload, env));
      }

      /* ------------------------------------------------ catalogue, atelier */
      if (pathname === '/api/admin/catalogue') {
        if (throttled(request, 60)) return fail('trop de requêtes', 429);
        if (!adminAuthorized(bearer(request), env)) return fail('accès refusé', 401);
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
        if (!adminAuthorized(bearer(request), env)) return fail('accès refusé', 401);
        if (throttled(request, 30)) return fail('trop d’envois, patientez une minute', 429);

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
