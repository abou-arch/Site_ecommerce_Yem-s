/* ===========================================================================
   GET  /api/admin/orders          liste des commandes
   POST /api/admin/orders          { order_id, status } — changement de statut

   Protégé par un jeton porté dans l'en-tête Authorization. Ce n'est pas un
   système de comptes : c'est un secret partagé, suffisant pour une boutique
   à un seul gérant, et à remplacer si l'équipe s'agrandit.
   =========================================================================== */

import { db, logEvent } from '../_lib/db.js';
import { waLink, composeMessage } from '../_lib/whatsapp.js';
import { json, fail, readJson, tooManyRequests } from '../_lib/http.js';

const STATUSES = [
  'pending', 'paid', 'deposit', 'in_workshop',
  'shipped', 'delivered', 'cancelled', 'refunded',
];

function authorized(req) {
  const expected = process.env.ADMIN_TOKEN;
  if (!expected || expected.length < 16) return false;

  const header = String(req.headers.authorization || '');
  const received = header.startsWith('Bearer ') ? header.slice(7) : '';
  if (received.length !== expected.length) return false;

  let diff = 0;
  for (let i = 0; i < expected.length; i += 1) {
    diff |= expected.charCodeAt(i) ^ received.charCodeAt(i);
  }
  return diff === 0;
}

export default async function handler(req, res) {
  if (tooManyRequests(req, { max: 60 })) return fail(res, 429, 'trop de requêtes');
  if (!authorized(req)) return fail(res, 401, 'accès refusé');

  const sql = db();

  /* ------------------------------------------------ changement de statut */

  if (req.method === 'POST') {
    let body;
    try {
      body = await readJson(req);
    } catch {
      return fail(res, 400, 'corps illisible');
    }

    const orderId = Number(body.order_id);
    const status = String(body.status || '');

    if (!Number.isInteger(orderId) || orderId <= 0) return fail(res, 400, 'commande invalide');
    if (!STATUSES.includes(status)) return fail(res, 400, 'statut inconnu');

    const [updated] = await sql`
      UPDATE orders SET status = ${status} WHERE id = ${orderId}
      RETURNING id, reference, status
    `;
    if (!updated) return fail(res, 404, 'commande introuvable');

    await logEvent(sql, orderId, `statut → ${status}`, null, 'admin');
    return json(res, 200, { ok: true, order: updated });
  }

  /* ----------------------------------------------------------- la liste */

  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET, POST');
    return fail(res, 405, 'méthode non autorisée');
  }

  const status = String(req.query?.status || '');
  const limit = Math.min(Number(req.query?.limit) || 50, 200);

  const rows = await sql`
    SELECT o.id, o.reference, o.status, o.kind,
           o.subtotal, o.shipping, o.total, o.amount_due,
           o.ship_name, o.ship_phone, o.ship_address, o.ship_city,
           o.ship_country, o.ship_note, o.notified_at, o.created_at,
           c.is_vip,
           COALESCE(json_agg(
             json_build_object(
               'name', i.name, 'qty', i.qty, 'line_total', i.line_total,
               'size', i.size, 'color', i.color, 'bespoke', i.bespoke
             ) ORDER BY i.id
           ) FILTER (WHERE i.id IS NOT NULL), '[]') AS items
    FROM orders o
    LEFT JOIN customers  c ON c.id = o.customer_id
    LEFT JOIN order_items i ON i.order_id = o.id
    ${status && STATUSES.includes(status) ? sql`WHERE o.status = ${status}` : sql``}
    GROUP BY o.id, c.is_vip
    ORDER BY o.created_at DESC
    LIMIT ${limit}
  `;

  const owner = process.env.OWNER_WHATSAPP;

  // Pour toute commande payée mais pas encore notifiée, on prépare le lien
  // WhatsApp : l'atelier n'a qu'à cliquer, même sans API Meta configurée.
  const orders = rows.map((o) => ({
    ...o,
    whatsapp_link:
      owner && !o.notified_at && o.status !== 'pending'
        ? waLink(owner, composeMessage(o, o.items))
        : null,
  }));

  return json(res, 200, { ok: true, count: orders.length, orders });
}
