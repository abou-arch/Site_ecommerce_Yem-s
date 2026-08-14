/* ===========================================================================
   Yem's — Corrections apportées au catalogue depuis l'atelier

   data/products.json reste la source. Cette table ne stocke que ce que
   l'atelier a changé : un prix, une disponibilité, une phrase, des photos.
   Un champ absent veut dire « garder ce que dit le catalogue ».

   POURQUOI PAS TOUT EN BASE : le catalogue en JSON est empaqueté dans le
   Worker, donc lisible sans aucun accès réseau. Y garder les noms, les textes
   longs et les pointures évite une requête sur des données qui ne changent
   jamais. Seuls les champs volatils passent par la base.
   =========================================================================== */

import { connect } from './db.js';

/* Cache mémoire, par isolate. Cloudflare garde une isolate chaude quelques
   minutes : sur une rafale de visites, une seule requête part vers Neon.
   30 secondes suffisent — l'atelier modifie un prix, il le voit en ligne le
   temps de recharger la page. */
const TTL = 30_000;
let cache = { at: 0, valeurs: null };

/** Invalide le cache. Appelé après chaque écriture, pour un effet immédiat. */
export function oublier() {
  cache = { at: 0, valeurs: null };
}

/**
 * Toutes les corrections, indexées par slug.
 * Rend un objet vide si la table n'existe pas encore : le site doit tourner
 * même quand la migration 002 n'a pas été passée.
 */
export async function lireCorrections(env) {
  const maintenant = Date.now();
  if (cache.valeurs && maintenant - cache.at < TTL) return cache.valeurs;

  const sql = connect(env);
  try {
    const lignes = await sql`
      SELECT slug, price, status, short, images, hidden
      FROM product_overrides
    `;
    const valeurs = {};
    for (const l of lignes) {
      valeurs[l.slug] = {
        price: l.price ?? undefined,
        status: l.status ?? undefined,
        short: l.short ?? undefined,
        images: l.images ?? undefined,
        hidden: Boolean(l.hidden),
      };
    }
    cache = { at: maintenant, valeurs };
    return valeurs;
  } catch (err) {
    // Table absente, base injoignable : le catalogue d'origine prend le relais.
    // Une boutique qui affiche des prix légèrement anciens vaut mieux qu'une
    // boutique en panne.
    console.error('[corrections] lecture impossible :', err?.message);
    return cache.valeurs || {};
  } finally {
    await sql.end({ timeout: 5 });
  }
}

/* ─────────────────────────────────────────────────────────────── écriture */

const CHAMPS = ['price', 'status', 'short', 'images', 'hidden'];

/**
 * Applique une correction et journalise ce qui a changé.
 * `patch` ne contient que les champs à modifier ; passer null efface la
 * correction et fait revenir la valeur du catalogue.
 */
export async function ecrireCorrection(slug, patch, env, actor = 'admin') {
  const sql = connect(env);
  try {
    const [avant] = await sql`
      SELECT price, status, short, images, hidden
      FROM product_overrides WHERE slug = ${slug}
    `;

    const valeur = (champ) =>
      Object.prototype.hasOwnProperty.call(patch, champ)
        ? patch[champ]
        : (avant ? avant[champ] : null);

    const p = valeur('price');
    const s = valeur('status');
    const t = valeur('short');
    const i = valeur('images');
    const h = valeur('hidden') ?? false;

    await sql`
      INSERT INTO product_overrides (slug, price, status, short, images, hidden, updated_by)
      VALUES (${slug}, ${p ?? null}, ${s ?? null}, ${t ?? null},
              ${i == null ? null : sql.json(i)}, ${Boolean(h)}, ${actor})
      ON CONFLICT (slug) DO UPDATE SET
        price = EXCLUDED.price, status = EXCLUDED.status,
        short = EXCLUDED.short, images = EXCLUDED.images,
        hidden = EXCLUDED.hidden, updated_by = EXCLUDED.updated_by,
        updated_at = now()
    `;

    // Journal : uniquement ce qui a réellement bougé.
    const lisible = (v) => (v == null ? null
      : typeof v === 'object' ? `${v.length ?? 0} photo(s)` : String(v));

    for (const champ of CHAMPS) {
      if (!Object.prototype.hasOwnProperty.call(patch, champ)) continue;
      const vieux = lisible(avant ? avant[champ] : null);
      const neuf = lisible(patch[champ]);
      if (vieux === neuf) continue;
      await sql`
        INSERT INTO catalog_events (slug, champ, avant, apres, actor)
        VALUES (${slug}, ${champ}, ${vieux}, ${neuf}, ${actor})
      `;
    }
  } finally {
    await sql.end({ timeout: 5 });
    oublier();
  }
}

/** Les vingt dernières modifications, pour l'écran d'administration. */
export async function journalCatalogue(env, limite = 20) {
  const sql = connect(env);
  try {
    return await sql`
      SELECT slug, champ, avant, apres, created_at
      FROM catalog_events
      ORDER BY created_at DESC
      LIMIT ${Math.min(Number(limite) || 20, 100)}
    `;
  } catch {
    return [];
  } finally {
    await sql.end({ timeout: 5 });
  }
}
