/* ===========================================================================
   Yem's — Accès base

   Une connexion par invocation, refermée à la fin. En serverless, chaque
   requête peut réveiller une instance neuve : un pool classique ouvrirait
   des dizaines de connexions et saturerait Postgres.

   Sur Cloudflare, la chaîne de connexion vient de Hyperdrive, qui maintient
   le vrai pool côté Cloudflare et rapproche les connexions de la base.
   Ailleurs, on lit DATABASE_URL.
   =========================================================================== */

import postgres from 'postgres';

/** Ouvre une connexion. À refermer avec close() une fois la requête traitée. */
export function connect(env = {}) {
  const url =
    env.HYPERDRIVE?.connectionString ||
    env.DATABASE_URL ||
    globalThis.process?.env?.DATABASE_URL;

  if (!url) throw new Error('aucune chaîne de connexion (HYPERDRIVE ou DATABASE_URL)');

  return postgres(url, {
    max: 1,
    fetch_types: false,   // évite un aller-retour de découverte des types au démarrage
    prepare: false,       // requis derrière un pooler (Hyperdrive, PgBouncer)
    idle_timeout: 20,
    connect_timeout: 10,
    ssl: url.includes('localhost') ? false : 'require',
    onnotice: () => {},
  });
}

/**
 * Référence lisible par le client et par l'atelier : YMS-2608-0042.
 * Le compteur du jour évite les collisions sans exposer le volume total.
 */
export async function nextReference(sql) {
  const now = new Date();
  const stamp =
    String(now.getUTCDate()).padStart(2, '0') +
    String(now.getUTCMonth() + 1).padStart(2, '0');

  const [row] = await sql`
    SELECT count(*)::int AS n
    FROM orders
    WHERE created_at >= date_trunc('day', now())
  `;
  return `YMS-${stamp}-${String((row?.n ?? 0) + 1).padStart(4, '0')}`;
}

export async function logEvent(sql, orderId, label, detail = null, actor = 'system') {
  await sql`
    INSERT INTO order_events (order_id, label, detail, actor)
    VALUES (${orderId}, ${label}, ${detail ? sql.json(detail) : null}, ${actor})
  `;
}
