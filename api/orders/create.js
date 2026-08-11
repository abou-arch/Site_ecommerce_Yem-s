/* ===========================================================================
   POST /api/orders/create

   Reçoit un panier et des coordonnées de livraison. Recalcule intégralement
   les montants depuis le catalogue, enregistre la commande en « pending »,
   et renvoie le montant à payer.

   Ce que le client envoie ne sert qu'à dire QUOI il achète. Le COMBIEN sort
   d'ici, et c'est ce montant-là que le widget KkiaPay devra encaisser.
   =========================================================================== */

import { db, nextReference, logEvent } from '../_lib/db.js';
import { priceCart, amountDue, shippingFor } from '../_lib/catalog.js';
import {
  json, fail, methodGuard, readJson,
  cleanText, cleanPhone, isEmail, COUNTRIES, tooManyRequests,
} from '../_lib/http.js';

export default async function handler(req, res) {
  if (!methodGuard(req, res, 'POST')) return;
  if (tooManyRequests(req, { max: 12 })) return fail(res, 429, 'trop de requêtes, réessayez dans une minute');

  let body;
  try {
    body = await readJson(req);
  } catch {
    return fail(res, 400, 'corps de requête illisible');
  }

  /* ---------------------------------------------------- coordonnées */

  const country = COUNTRIES.includes(body.country) ? body.country : 'BJ';
  const name = cleanText(body.name, 120);
  const phone = cleanPhone(body.phone, country);
  const address = cleanText(body.address, 300);
  const city = cleanText(body.city, 120);
  const email = cleanText(body.email, 160);
  const note = cleanText(body.note, 500);

  if (name.length < 3) return fail(res, 400, 'nom et prénom requis');
  if (!phone || phone.length < 10) return fail(res, 400, 'numéro de téléphone invalide');
  if (address.length < 5) return fail(res, 400, 'adresse de livraison requise');
  if (city.length < 2) return fail(res, 400, 'ville requise');
  if (!isEmail(email)) return fail(res, 400, 'adresse e-mail invalide');

  /* -------------------------------------------------------- montants */

  const priced = priceCart(body.cart);
  if (priced.error) return fail(res, 400, priced.error);

  const shipping = shippingFor(country);
  const total = priced.subtotal + shipping;
  const due = amountDue(total, priced.kind);

  /* ------------------------------------------------- enregistrement */

  const sql = db();

  try {
    const result = await sql.begin(async (tx) => {
      // Le client est reconnu à son numéro : chez nous c'est lui l'identité,
      // pas l'e-mail. On met à jour ses coordonnées au passage.
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

      const [order] = await tx`
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
            ${order.id}, ${item.product_slug}, ${item.name}, ${item.unit_price},
            ${item.qty}, ${item.line_total}, ${item.size}, ${item.color},
            ${item.bespoke ? tx.json(item.bespoke) : null}
          )
        `;
      }

      await logEvent(tx, order.id, 'commande créée', {
        kind: priced.kind, total, due, vip: customer.is_vip,
      });

      return order;
    });

    return json(res, 201, {
      ok: true,
      order_id: result.id,
      reference: result.reference,
      total: result.total,
      amount_due: result.amount_due,
      // La clé PUBLIQUE seule descend au navigateur ; la privée reste ici.
      public_key: process.env.KKIAPAY_PUBLIC_KEY || null,
      sandbox: process.env.KKIAPAY_SANDBOX === 'true',
    });
  } catch (err) {
    console.error('[orders/create]', err);
    return fail(res, 500, 'commande non enregistrée');
  }
}
