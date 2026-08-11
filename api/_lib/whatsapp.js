/* ===========================================================================
   Yem's — Notification WhatsApp au propriétaire

   Deux modes, volontairement :

   1. API WhatsApp Cloud si WHATSAPP_TOKEN est configuré — le message part tout
      seul dès que le paiement est vérifié.
   2. Sinon, on fabrique un lien wa.me pré-rempli, stocké avec la commande et
      affiché dans l'admin. L'atelier peut encaisser dès le premier jour, sans
      attendre la validation d'un compte Meta Business.

   Une notification qui échoue ne doit jamais faire échouer un paiement déjà
   encaissé : toutes les erreurs sont avalées et journalisées.
   =========================================================================== */

const money = (n) => new Intl.NumberFormat('fr-FR').format(n) + ' F';

/** Message lisible sur un téléphone, sans mise en forme exotique. */
export function composeMessage(order, items) {
  const lines = items.map((i) => {
    const opts = [i.color, i.size ? `pointure ${i.size}` : null,
                  i.bespoke?.initials ? `initiales ${i.bespoke.initials}` : null,
                  i.bespoke?.sole ? `semelle ${i.bespoke.sole}` : null]
      .filter(Boolean).join(', ');
    return `• ${i.qty} × ${i.name}${opts ? ` (${opts})` : ''} — ${money(i.line_total)}`;
  });

  const reste = order.total - order.amount_due;

  return [
    `Nouvelle commande ${order.reference}`,
    '',
    ...lines,
    '',
    `Sous-total : ${money(order.subtotal)}`,
    order.shipping ? `Livraison : ${money(order.shipping)}` : null,
    `Total : ${money(order.total)}`,
    `Encaissé : ${money(order.amount_due)}`,
    reste > 0 ? `Reste à la livraison : ${money(reste)}` : null,
    '',
    `Client : ${order.ship_name} — ${order.ship_phone}`,
    `Livraison : ${order.ship_address}, ${order.ship_city} (${order.ship_country})`,
    order.ship_note ? `Note : ${order.ship_note}` : null,
  ].filter(Boolean).join('\n');
}

/** Lien de repli, à ouvrir d'un clic depuis l'admin. */
export function waLink(to, message) {
  return `https://wa.me/${String(to).replace(/\D/g, '')}?text=${encodeURIComponent(message)}`;
}

/**
 * Envoie le message. Ne lève jamais.
 * @returns {Promise<{sent:boolean, mode:'cloud'|'link', link?:string, error?:string}>}
 */
export async function notifyOwner(order, items) {
  const to = process.env.OWNER_WHATSAPP;
  const message = composeMessage(order, items);

  if (!to) return { sent: false, mode: 'link', error: 'OWNER_WHATSAPP non configuré' };

  const token = process.env.WHATSAPP_TOKEN;
  const phoneId = process.env.WHATSAPP_PHONE_ID;

  if (!token || !phoneId) {
    return { sent: false, mode: 'link', link: waLink(to, message) };
  }

  try {
    const res = await fetch(`https://graph.facebook.com/v21.0/${phoneId}/messages`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messaging_product: 'whatsapp',
        to: String(to).replace(/\D/g, ''),
        type: 'text',
        text: { preview_url: false, body: message },
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      return { sent: false, mode: 'link', link: waLink(to, message), error: detail.slice(0, 300) };
    }
    return { sent: true, mode: 'cloud' };
  } catch (err) {
    return { sent: false, mode: 'link', link: waLink(to, message), error: err?.message };
  }
}
