/* ===========================================================================
   POST /api/webhooks/kkiapay

   Filet de sécurité. Si le client ferme son navigateur juste après avoir payé,
   /api/payments/verify n'est jamais appelé et la commande resterait « pending »
   alors que l'argent est encaissé. KkiaPay nous prévient ici.

   La signature x-kkiapay-secret est vérifiée avant toute chose : sans ça,
   n'importe qui pourrait valider des commandes en appelant cette URL.
   =========================================================================== */

import { db, logEvent } from '../_lib/db.js';
import { verifyTransaction, webhookIsAuthentic } from '../_lib/kkiapay.js';
import { notifyOwner } from '../_lib/whatsapp.js';
import { json, fail, methodGuard, readRaw } from '../_lib/http.js';

export const config = { api: { bodyParser: false } };

export default async function handler(req, res) {
  if (!methodGuard(req, res, 'POST')) return;

  if (!webhookIsAuthentic(req)) {
    console.warn('[webhook] signature invalide');
    return fail(res, 401, 'signature invalide');
  }

  let event;
  try {
    event = JSON.parse(await readRaw(req));
  } catch {
    return fail(res, 400, 'charge utile illisible');
  }

  const transactionId = String(
    event.transactionId || event.transaction_id || event.id || ''
  ).trim();
  if (!transactionId) return json(res, 200, { ok: true, ignored: 'sans transactionId' });

  const sql = db();

  // Déjà traitée par /api/payments/verify : on acquitte et on s'arrête.
  const [known] = await sql`
    SELECT id FROM payments WHERE transaction_id = ${transactionId} AND status = 'success'
  `;
  if (known) return json(res, 200, { ok: true, already: true });

  // On retrouve la commande par la référence transmise dans « data », sinon
  // par le partnerId. Le widget place order_id dans data à l'ouverture.
  let orderId = Number(event.order_id || event.partnerId);
  if (!Number.isInteger(orderId) || orderId <= 0) {
    try {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      orderId = Number(data?.order_id);
    } catch { /* données libres non exploitables */ }
  }
  if (!Number.isInteger(orderId) || orderId <= 0) {
    return json(res, 200, { ok: true, ignored: 'commande non identifiable' });
  }

  const [order] = await sql`
    SELECT id, reference, status, kind, subtotal, shipping, total, amount_due,
           ship_name, ship_phone, ship_address, ship_city, ship_country, ship_note
    FROM orders WHERE id = ${orderId}
  `;
  if (!order) return json(res, 200, { ok: true, ignored: 'commande introuvable' });
  if (order.status !== 'pending') return json(res, 200, { ok: true, already: true });

  // Même contrôle que par la voie normale : on ne fait pas confiance au
  // contenu du webhook non plus, on revérifie la transaction à la source.
  const check = await verifyTransaction(transactionId, order.amount_due);
  if (!check.ok) {
    await logEvent(sql, orderId, 'webhook rejeté', { reason: check.reason }, 'webhook');
    return json(res, 200, { ok: true, ignored: check.reason });
  }

  const p = check.payment;
  const newStatus = order.kind === 'standard' ? 'paid' : 'deposit';

  await sql.begin(async (tx) => {
    const inserted = await tx`
      INSERT INTO payments (
        order_id, transaction_id, status, amount, method, provider, payer_phone, raw, verified_at
      ) VALUES (
        ${orderId}, ${p.transaction_id}, 'success', ${p.amount},
        ${p.method}, ${p.provider}, ${p.payer_phone}, ${tx.json(check.raw)}, now()
      )
      ON CONFLICT (transaction_id) DO NOTHING
      RETURNING id
    `;
    if (inserted.length === 0) return;

    await tx`UPDATE orders SET status = ${newStatus} WHERE id = ${orderId} AND status = 'pending'`;
    await logEvent(tx, orderId, 'paiement confirmé par webhook', {
      transaction_id: p.transaction_id, amount: p.amount,
    }, 'webhook');
  });

  try {
    const items = await sql`
      SELECT name, qty, line_total, size, color, bespoke
      FROM order_items WHERE order_id = ${orderId} ORDER BY id
    `;
    const notice = await notifyOwner(order, items);
    if (notice.sent) await sql`UPDATE orders SET notified_at = now() WHERE id = ${orderId}`;
  } catch (err) {
    console.error('[webhook] notification', err);
  }

  return json(res, 200, { ok: true });
}
