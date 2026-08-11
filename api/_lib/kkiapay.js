/* ===========================================================================
   Yem's — Vérification des paiements KkiaPay

   Le navigateur nous annonce « c'est payé » avec un transactionId. Cette
   annonce ne vaut rien : elle peut être fabriquée depuis la console. On
   redemande donc à KkiaPay, avec la clé privée, ce qui s'est réellement
   passé — et on compare le montant encaissé à celui qu'on réclamait.
   =========================================================================== */

import { kkiapay } from '@kkiapay-org/nodejs-sdk';

let client = null;

function sdk() {
  if (client) return client;

  const privatekey = process.env.KKIAPAY_PRIVATE_KEY;
  const publickey = process.env.KKIAPAY_PUBLIC_KEY;
  const secretkey = process.env.KKIAPAY_SECRET_KEY;

  if (!privatekey || !publickey || !secretkey) {
    throw new Error('clés KkiaPay absentes de l\'environnement');
  }

  client = kkiapay({
    privatekey,
    publickey,
    secretkey,
    sandbox: process.env.KKIAPAY_SANDBOX === 'true',
  });
  return client;
}

/**
 * Interroge KkiaPay sur une transaction.
 *
 * @param {string} transactionId
 * @param {number} expectedAmount  montant réclamé, en FCFA
 * @returns {Promise<{ok:boolean, reason?:string, payment?:object, raw?:object}>}
 */
export async function verifyTransaction(transactionId, expectedAmount) {
  const id = String(transactionId || '').trim();
  if (!id || id.length > 64) return { ok: false, reason: 'identifiant de transaction invalide' };

  let raw;
  try {
    raw = await sdk().verify(id);
  } catch (err) {
    return { ok: false, reason: 'KkiaPay injoignable : ' + (err?.message || 'erreur') };
  }

  if (!raw || raw.status !== 'SUCCESS') {
    return {
      ok: false,
      reason: `transaction non aboutie (${raw?.status || 'inconnue'})`,
      raw,
    };
  }

  // Le contrôle qui compte : ce qui a été encaissé doit couvrir ce qu'on demandait.
  const paid = Math.round(Number(raw.amount));
  if (!Number.isFinite(paid) || paid < expectedAmount) {
    return {
      ok: false,
      reason: `montant insuffisant : ${paid} F encaissés pour ${expectedAmount} F attendus`,
      raw,
    };
  }

  return {
    ok: true,
    raw,
    payment: {
      transaction_id: raw.transactionId || id,
      amount: paid,
      method: raw.source || null,                 // MOBILE_MONEY, CARD…
      provider: raw.source_common_name || null,   // mtn-benin, moov, wave…
      payer_phone: raw.client?.phone || null,
      payer_name: raw.client?.fullname || null,
      payer_email: raw.client?.email || null,
    },
  };
}

/**
 * Vérifie qu'un webhook vient bien de KkiaPay.
 * KkiaPay signe ses appels avec l'en-tête x-kkiapay-secret.
 */
export function webhookIsAuthentic(req) {
  const expected = process.env.KKIAPAY_SECRET_KEY;
  if (!expected) return false;

  const received = req.headers['x-kkiapay-secret'];
  if (!received || typeof received !== 'string') return false;
  if (received.length !== expected.length) return false;

  // comparaison à durée constante : une comparaison naïve laisse fuiter le
  // secret caractère par caractère si l'attaquant mesure le temps de réponse
  let diff = 0;
  for (let i = 0; i < expected.length; i += 1) {
    diff |= expected.charCodeAt(i) ^ received.charCodeAt(i);
  }
  return diff === 0;
}
