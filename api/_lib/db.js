/* ===========================================================================
   Yem's — Accès base

   En serverless, chaque requête peut réveiller une instance neuve. Un pool
   classique ouvrirait des dizaines de connexions et saturerait Postgres :
   d'où max = 1 et une inactivité courte. Le client est réutilisé entre deux
   invocations quand l'instance reste chaude.
   =========================================================================== */

import postgres from 'postgres';

let sql = null;

export function db() {
  if (sql) return sql;

  const url = process.env.DATABASE_URL;
  if (!url) throw new Error('DATABASE_URL absente');

  sql = postgres(url, {
    max: 1,
    idle_timeout: 20,
    connect_timeout: 10,
    ssl: url.includes('localhost') ? false : 'require',
    prepare: false,          // requis derrière un pooler type PgBouncer
    onnotice: () => {},
  });
  return sql;
}

/**
 * Référence lisible par le client et par l'atelier : YMS-2608-0042.
 * Le compteur du jour évite les collisions sans exposer le volume total.
 */
export async function nextReference(sqlc) {
  const now = new Date();
  const stamp =
    String(now.getUTCDate()).padStart(2, '0') +
    String(now.getUTCMonth() + 1).padStart(2, '0');

  const [row] = await sqlc`
    SELECT count(*)::int AS n
    FROM orders
    WHERE created_at >= date_trunc('day', now())
  `;
  return `YMS-${stamp}-${String((row?.n ?? 0) + 1).padStart(4, '0')}`;
}

export async function logEvent(sqlc, orderId, label, detail = null, actor = 'system') {
  await sqlc`
    INSERT INTO order_events (order_id, label, detail, actor)
    VALUES (${orderId}, ${label}, ${detail ? sqlc.json(detail) : null}, ${actor})
  `;
}
