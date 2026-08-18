/* ===========================================================================
   Yem's — Notification de commande par e-mail

   Pourquoi ce fichier existe
   --------------------------
   La notification de l'atelier ne passait que par WhatsApp. Or l'API WhatsApp
   Cloud exige WHATSAPP_TOKEN et WHATSAPP_PHONE_ID, qui ne sont pas posés :
   sans eux, whatsapp.js se contente de fabriquer un lien wa.me que personne ne
   voit tant que l'admin n'est pas ouverte. Autrement dit, aujourd'hui, une
   commande peut arriver sans que l'atelier soit prévenu.

   Cloudflare Email Sending comble ce trou sans rien coûter : l'envoi vers une
   adresse de destination VÉRIFIÉE du compte est gratuit sur tous les plans,
   Email Routing seul suffit. Écrire au client, lui, viserait une adresse non
   vérifiée et demanderait le plan Workers Paid : ce n'est pas ce qu'on fait ici.

   Le texte du message est celui de WhatsApp, volontairement
   ---------------------------------------------------------
   composeMessage() reste la seule source de vérité du contenu. Deux rédactions
   parallèles finiraient par diverger, et c'est toujours celle qu'on ne relit
   pas qui se trompe de total.
   =========================================================================== */

import { composeMessage } from './whatsapp.js';

/**
 * Échappement HTML.
 *
 * Indispensable, pas décoratif : ship_name, ship_address et surtout ship_note
 * sont saisis par le client. Sans échappement, n'importe qui pourrait injecter
 * du balisage, un lien ou une image pisteuse dans la boîte de l'atelier en
 * remplissant le champ « note » du checkout.
 */
function ech(v) {
  return String(v ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/**
 * Version HTML du message.
 *
 * Volontairement pauvre : styles en ligne, pas d'image, pas de police
 * distante. Un message lu sur un téléphone dans un atelier doit s'afficher
 * partout, y compris dans un client qui bloque tout. Les couleurs sont celles
 * de la marque, c'est la seule coquetterie.
 */
function enHtml(texte, reference) {
  const corps = ech(texte)
    .split('\n')
    .map((l) => (l.trim() === '' ? '<div style="height:10px"></div>' : `<div>${l}</div>`))
    .join('');

  return `<!DOCTYPE html><html lang="fr"><body style="margin:0;padding:24px;background:#F4EDE2;">
<div style="max-width:560px;margin:0 auto;background:#FBF7F1;border-radius:12px;overflow:hidden;
            font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1C1613">
  <div style="background:#14100D;color:#D9B87A;padding:18px 24px;font-size:13px;
              letter-spacing:.16em;text-transform:uppercase">Yem's &middot; ${ech(reference)}</div>
  <div style="padding:24px;font-size:15px;line-height:1.65;white-space:normal">${corps}</div>
  <div style="padding:16px 24px;border-top:1px solid rgba(28,22,19,.12);
              font-size:12px;color:rgba(28,22,19,.62)">
    Message automatique du site. Le détail complet est dans l'administration.
  </div>
</div></body></html>`;
}

/**
 * Prévient l'atelier par e-mail. Ne lève jamais.
 *
 * @returns {Promise<{sent:boolean, skipped?:string, error?:string}>}
 *   skipped porte la raison quand l'envoi n'est pas configuré : ce n'est pas
 *   une panne, et le journal ne doit pas le présenter comme telle.
 */
export async function previenirParCourriel(order, items, env = {}) {
  const pick = (k) => env[k] ?? globalThis.process?.env?.[k];

  // Le binding n'existe pas tant que send_email n'est pas déclaré dans
  // wrangler.toml. Tant qu'il manque, on sort proprement.
  if (!env.EMAIL || typeof env.EMAIL.send !== 'function') {
    return { sent: false, skipped: 'binding EMAIL absent' };
  }

  const to = pick('OWNER_EMAIL');
  if (!to) return { sent: false, skipped: 'OWNER_EMAIL non configuré' };

  const from = pick('ORDER_EMAIL_FROM') || 'commandes@maisonyems.com';
  const texte = composeMessage(order, items);

  try {
    await env.EMAIL.send({
      to,
      from,
      // L'objet doit se lire en entier dans la liste des messages, sans
      // ouvrir : la référence et le montant suffisent à décider si ça presse.
      // Pas de tiret cadratin : la charte l'interdit, y compris ici.
      subject: `Commande ${order.reference}, ${new Intl.NumberFormat('fr-FR').format(order.total)} F`,
      text: texte,
      html: enHtml(texte, order.reference),
    });
    return { sent: true };
  } catch (err) {
    return { sent: false, error: String(err?.message || err).slice(0, 300) };
  }
}
