/* ===========================================================================
   POST /api/payments/verify

   Le navigateur annonce un transactionId après le widget KkiaPay. On ne le
   croit pas : on redemande à KkiaPay, avec la clé privée, et on compare le
   montant encaissé à celui inscrit en base pour cette commande.

   Idempotent : la contrainte d'unicité sur transaction_id fait qu'un double
   appel — rechargement de page, webhook arrivé en même temps — ne peut pas
   marquer la commande payée deux fois.
   =========================================================================== */

import { db, logEvent } from '../_lib/db.js';
import { verifyTransaction } from '../_lib/kkiapay.js';
import { notifyOwner } from '../_lib/whatsapp.js';
import { json, fail, methodGuard, readJson, tooManyRequests } from '../_lib/http.js';

export default async function handler(req, res) {
  if (!methodGuard(req, res, 'POST')) return;
  if (tooManyRequests(req, { max: 20 })) return fail(res, 429, 'trop de requêtes');

  let body;
  try {
    body = await readJson(req);
  } catch {
    return fail(res, 400, 'corps de requête illisible');
  }

  const orderId = Number(body.order_id);
  const transactionId = String(body.transaction_id || '').trim();

  if (!Number.isInteger(orderId) || orderId <= 0) return fail(res, 400, 'commande invalide');
  if (!transactionId) return fail(res, 400, 'transaction manquante');

  const sql = db();

  const [order] = await sql`
    SELECT id, reference, status, kind, subtotal, shipping, total, amount_due,
           ship_name, ship_phone, ship_address, ship_city, ship_country, ship_note
    FROM orders WHERE id = ${orderId}
  `;
  if (!order) return fail(res, 404, 'commande introuvable');

  // Déjà réglée : on répond succès sans rien retoucher.
  if (order.status !== 'pending') {
    return json(res, 200, { ok: true, already: true, reference: order.reference, status: order.status });
  }

  /* ------------------------------------ on redemande à la source */

  const check = await verifyTransaction(transactionId, order.amount_due);

  if (!check.ok) {
    await sql`
      INSERT INTO payments (order_id, transaction_id, status, amount, raw)
      VALUES (${orderId}, ${transactionId}, 'failed', 0, ${sql.json(check.raw ?? {})})
      ON CONFLICT (transaction_id) DO NOTHING
    `;
    await logEvent(sql, orderId, 'paiement refusé', { reason: check.reason }, 'system');
    return fail(res, 402, check.reason);
  }

  /* ------------------------------------------------ encaissement */

  const p = check.payment;
  const newStatus = order.kind === 'standard' ? 'paid' : 'deposit';

  let items;
  try {
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

      // Aucune ligne insérée : la transaction avait déjà été encaissée ailleurs.
      if (inserted.length === 0) return;

      await tx`UPDATE orders SET status = ${newStatus} WHERE id = ${orderId} AND status = 'pending'`;
      await logEvent(tx, orderId, 'paiement vérifié', {
        transaction_id: p.transaction_id, amount: p.amount, provider: p.provider,
      }, 'system');
    });

    items = await sql`
      SELECT name, qty, line_total, size, color, bespoke
      FROM order_items WHERE order_id = ${orderId} ORDER BY id
    `;
  } catch (err) {
    console.error('[payments/verify]', err);
    return fail(res, 500, 'paiement encaissé mais commande non mise à jour — contactez l\'atelier');
  }

  /* --------------------------------------------------- notification

     Le paiement est acquis. Si WhatsApp échoue, la commande reste valide :
     on note l'échec, l'admin affichera un lien à cliquer.                  */

  try {
    const notice = await notifyOwner(order, items);
    if (notice.sent) {
      await sql`UPDATE orders SET notified_at = now() WHERE id = ${orderId}`;
    }
    await logEvent(sql, orderId, notice.sent ? 'atelier notifié' : 'notification à envoyer', notice, 'system');
  } catch (err) {
    console.error('[payments/verify] notification', err);
  }

  return json(res, 200, {
    ok: true,
    reference: order.reference,
    status: newStatus,
    amount_paid: p.amount,
    remaining: order.total - order.amount_due,
  });
}
