/* ===========================================================================
   Yem's — Logique métier, indépendante de l'hébergeur

   Chaque fonction reçoit des données déjà décodées et rend { status, body }.
   Aucune ne touche à Request, Response, req ou res : c'est l'adaptateur
   (worker.js) qui s'en charge. Le jour où l'on change d'hébergeur, seul
   l'adaptateur bouge.
   =========================================================================== */

import { connect, nextReference, logEvent } from './db.js';
import { priceCart, amountDue, shippingFor } from './catalog.js';
import { verifyTransaction, webhookIsAuthentic } from './kkiapay.js';
import { notifyOwner, waLink, composeMessage } from './whatsapp.js';
import { cleanText, cleanPhone, isEmail, COUNTRIES } from './http.js';

const ok = (body, status = 200) => ({ status, body: { ok: true, ...body } });
const ko = (message, status = 400) => ({ status, body: { ok: false, error: message } });

const env0 = (env, key) => env?.[key] ?? globalThis.process?.env?.[key];

const STATUSES = [
  'pending', 'paid', 'deposit', 'in_workshop',
  'shipped', 'delivered', 'cancelled', 'refunded',
];

/* ═══════════════════════════════════════════════════ création de commande */

export async function createOrder(payload, env) {
  const country = COUNTRIES.includes(payload.country) ? payload.country : 'BJ';
  const name = cleanText(payload.name, 120);
  const phone = cleanPhone(payload.phone, country);
  const address = cleanText(payload.address, 300);
  const city = cleanText(payload.city, 120);
  const email = cleanText(payload.email, 160);
  const note = cleanText(payload.note, 500);

  if (name.length < 3) return ko('nom et prénom requis');
  if (!phone || phone.length < 10) return ko('numéro de téléphone invalide');
  if (address.length < 5) return ko('adresse de livraison requise');
  if (city.length < 2) return ko('ville requise');
  if (!isEmail(email)) return ko('adresse e-mail invalide');

  // Les montants sortent d'ici, jamais du panier envoyé par le navigateur.
  const priced = priceCart(payload.cart);
  if (priced.error) return ko(priced.error);

  const shipping = shippingFor(country);
  const total = priced.subtotal + shipping;
  const due = amountDue(total, priced.kind);

  const sql = connect(env);
  try {
    const order = await sql.begin(async (tx) => {
      // Le client est reconnu à son numéro : ici c'est lui l'identité, pas l'e-mail.
      const [customer] = await tx`
        INSERT INTO customers (phone, full_name, email, city, country)
        VALUES (${phone}, ${name}, ${email || null}, ${city}, ${country})
        ON CONFLICT (phone) DO UPDATE
          SET full_name = EXCLUDED.full_name,
              email     = COALESCE(EXCLUDED.email, customers.email),
              city      = EXCLUDED.city,
              country   = EXCLUDED.country
        RETURNING id, is_vip
      `;

      const reference = await nextReference(tx);

      const [created] = await tx`
        INSERT INTO orders (
          reference, customer_id, status, kind,
          subtotal, shipping, total, amount_due,
          ship_name, ship_phone, ship_address, ship_city, ship_country, ship_note
        ) VALUES (
          ${reference}, ${customer.id}, 'pending', ${priced.kind},
          ${priced.subtotal}, ${shipping}, ${total}, ${due},
          ${name}, ${phone}, ${address}, ${city}, ${country}, ${note || null}
        )
        RETURNING id, reference, total, amount_due
      `;

      for (const item of priced.items) {
        await tx`
          INSERT INTO order_items (
            order_id, product_slug, name, unit_price, qty, line_total, size, color, bespoke
          ) VALUES (
            ${created.id}, ${item.product_slug}, ${item.name}, ${item.unit_price},
            ${item.qty}, ${item.line_total}, ${item.size}, ${item.color},
            ${item.bespoke ? tx.json(item.bespoke) : null}
          )
        `;
      }

      await logEvent(tx, created.id, 'commande créée', {
        kind: priced.kind, total, due, vip: customer.is_vip,
      });
      return created;
    });

    return ok({
      order_id: order.id,
      reference: order.reference,
      total: order.total,
      amount_due: order.amount_due,
      // Seule la clé PUBLIQUE descend au navigateur. La privée reste ici.
      public_key: env0(env, 'KKIAPAY_PUBLIC_KEY') || null,
      sandbox: env0(env, 'KKIAPAY_SANDBOX') === 'true',
    }, 201);
  } finally {
    await sql.end({ timeout: 5 });
  }
}

/* ═══════════════════════════════════════════════ encaissement d'un paiement */

/** Cœur partagé entre la vérification normale et le webhook. */
async function settle(sql, order, transactionId, env, actor) {
  const check = await verifyTransaction(transactionId, order.amount_due, env);

  if (!check.ok) {
    await sql`
      INSERT INTO payments (order_id, transaction_id, status, amount, raw)
      VALUES (${order.id}, ${String(transactionId)}, 'failed', 0, ${sql.json(check.raw ?? {})})
      ON CONFLICT (transaction_id) DO NOTHING
    `;
    await logEvent(sql, order.id, 'paiement refusé', { reason: check.reason }, actor);
    return { settled: false, reason: check.reason };
  }

  const p = check.payment;
  const newStatus = order.kind === 'standard' ? 'paid' : 'deposit';
  let fresh = false;

  await sql.begin(async (tx) => {
    // L'unicité sur transaction_id rend l'opération idempotente : un double
    // appel — rechargement de page, webhook simultané — ne peut pas encaisser
    // deux fois la même transaction.
    const inserted = await tx`
      INSERT INTO payments (
        order_id, transaction_id, status, amount, method, provider, payer_phone, raw, verified_at
      ) VALUES (
        ${order.id}, ${p.transaction_id}, 'success', ${p.amount},
        ${p.method}, ${p.provider}, ${p.payer_phone}, ${tx.json(check.raw)}, now()
      )
      ON CONFLICT (transaction_id) DO NOTHING
      RETURNING id
    `;
    if (inserted.length === 0) return;

    fresh = true;
    await tx`UPDATE orders SET status = ${newStatus} WHERE id = ${order.id} AND status = 'pending'`;
    await logEvent(tx, order.id, 'paiement vérifié', {
      transaction_id: p.transaction_id, amount: p.amount, provider: p.provider,
    }, actor);
  });

  return { settled: true, fresh, payment: p, status: newStatus };
}

/** Notification de l'atelier. N'échoue jamais : l'argent est déjà encaissé. */
async function announce(sql, order, env) {
  try {
    const items = await sql`
      SELECT name, qty, line_total, size, color, bespoke
      FROM order_items WHERE order_id = ${order.id} ORDER BY id
    `;
    const notice = await notifyOwner(order, items, env);
    if (notice.sent) await sql`UPDATE orders SET notified_at = now() WHERE id = ${order.id}`;
    await logEvent(sql, order.id,
      notice.sent ? 'atelier notifié' : 'notification à envoyer', notice, 'system');
  } catch (err) {
    console.error('[notification]', err?.message);
  }
}

export async function verifyPayment(payload, env) {
  const orderId = Number(payload.order_id);
  const transactionId = String(payload.transaction_id || '').trim();

  if (!Number.isInteger(orderId) || orderId <= 0) return ko('commande invalide');
  if (!transactionId) return ko('transaction manquante');

  const sql = connect(env);
  try {
    const [order] = await sql`
      SELECT id, reference, status, kind, subtotal, shipping, total, amount_due,
             ship_name, ship_phone, ship_address, ship_city, ship_country, ship_note
      FROM orders WHERE id = ${orderId}
    `;
    if (!order) return ko('commande introuvable', 404);

    if (order.status !== 'pending') {
      return ok({ already: true, reference: order.reference, status: order.status });
    }

    const result = await settle(sql, order, transactionId, env, 'system');
    if (!result.settled) return ko(result.reason, 402);

    if (result.fresh) await announce(sql, order, env);

    return ok({
      reference: order.reference,
      status: result.status,
      amount_paid: result.payment.amount,
      remaining: order.total - order.amount_due,
    });
  } finally {
    await sql.end({ timeout: 5 });
  }
}

/* ═══════════════════════════════════════════════════════════════ webhook */

export async function handleWebhook(event, secretHeader, env) {
  // Sans cette vérification, n'importe qui validerait des commandes en
  // appelant l'URL du webhook.
  if (!webhookIsAuthentic(secretHeader, env)) return ko('signature invalide', 401);

  const transactionId = String(
    event.transactionId || event.transaction_id || event.id || ''
  ).trim();
  if (!transactionId) return ok({ ignored: 'sans transactionId' });

  // L'identifiant de commande voyage dans « data », posé par le tunnel.
  let orderId = Number(event.order_id || event.partnerId);
  if (!Number.isInteger(orderId) || orderId > 0 === false) {
    try {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      orderId = Number(data?.order_id);
    } catch { /* données libres non exploitables */ }
  }
  if (!Number.isInteger(orderId) || orderId <= 0) return ok({ ignored: 'commande non identifiable' });

  const sql = connect(env);
  try {
    const [known] = await sql`
      SELECT id FROM payments WHERE transaction_id = ${transactionId} AND status = 'success'
    `;
    if (known) return ok({ already: true });

    const [order] = await sql`
      SELECT id, reference, status, kind, subtotal, shipping, total, amount_due,
             ship_name, ship_phone, ship_address, ship_city, ship_country, ship_note
      FROM orders WHERE id = ${orderId}
    `;
    if (!order) return ok({ ignored: 'commande introuvable' });
    if (order.status !== 'pending') return ok({ already: true });

    // On ne fait pas davantage confiance au contenu du webhook : on revérifie
    // la transaction à la source, comme par la voie normale.
    const result = await settle(sql, order, transactionId, env, 'webhook');
    if (!result.settled) return ok({ ignored: result.reason });
    if (result.fresh) await announce(sql, order, env);

    return ok({});
  } finally {
    await sql.end({ timeout: 5 });
  }
}

/* ═════════════════════════════════════════════════════════════════ admin */

export function adminAuthorized(bearer, env) {
  const expected = env0(env, 'ADMIN_TOKEN');
  if (!expected || expected.length < 16) return false;
  if (typeof bearer !== 'string' || bearer.length !== expected.length) return false;

  let diff = 0;
  for (let i = 0; i < expected.length; i += 1) {
    diff |= expected.charCodeAt(i) ^ bearer.charCodeAt(i);
  }
  return diff === 0;
}

export async function listOrders({ status, limit }, env) {
  const cap = Math.min(Number(limit) || 50, 200);
  const sql = connect(env);

  try {
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
      LEFT JOIN customers   c ON c.id = o.customer_id
      LEFT JOIN order_items i ON i.order_id = o.id
      ${status && STATUSES.includes(status) ? sql`WHERE o.status = ${status}` : sql``}
      GROUP BY o.id, c.is_vip
      ORDER BY o.created_at DESC
      LIMIT ${cap}
    `;

    const owner = env0(env, 'OWNER_WHATSAPP');

    // Pour toute commande payée mais pas encore notifiée, on prépare le lien
    // WhatsApp : l'atelier n'a qu'à cliquer, même sans API Meta configurée.
    const orders = rows.map((o) => ({
      ...o,
      whatsapp_link:
        owner && !o.notified_at && o.status !== 'pending'
          ? waLink(owner, composeMessage(o, o.items))
          : null,
    }));

    return ok({ count: orders.length, orders });
  } finally {
    await sql.end({ timeout: 5 });
  }
}

export async function setOrderStatus({ order_id, status }, env) {
  const id = Number(order_id);
  if (!Number.isInteger(id) || id <= 0) return ko('commande invalide');
  if (!STATUSES.includes(status)) return ko('statut inconnu');

  const sql = connect(env);
  try {
    const [updated] = await sql`
      UPDATE orders SET status = ${status} WHERE id = ${id}
      RETURNING id, reference, status
    `;
    if (!updated) return ko('commande introuvable', 404);

    await logEvent(sql, id, `statut → ${status}`, null, 'admin');
    return ok({ order: updated });
  } finally {
    await sql.end({ timeout: 5 });
  }
}
