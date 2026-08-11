/* ===========================================================================
   Yem's — Vérification des paiements KkiaPay

   Le navigateur annonce « c'est payé » avec un transactionId. Cette annonce ne
   vaut rien : elle peut être fabriquée depuis la console. On redemande donc à
   KkiaPay, avec la clé privée, ce qui s'est réellement passé — et on compare
   le montant encaissé à celui qu'on réclamait.

   Appels en fetch plutôt qu'avec @kkiapay-org/nodejs-sdk : le SDK n'apporte
   qu'un wrapper axios autour de deux routes REST. S'en passer supprime une
   dépendance et rend ce fichier exécutable tel quel sur Node comme sur
   Cloudflare Workers.
   =========================================================================== */

const BASE = {
  live: 'https://api.kkiapay.me',
  sandbox: 'https://api-sandbox.kkiapay.me',
};

const ROUTE_STATUS = '/api/v1/transactions/status';
const ROUTE_REVERT = '/api/v1/transactions/revert';

function credentials(env = {}) {
  const pick = (key) => env[key] ?? globalThis.process?.env?.[key];

  const publickey = pick('KKIAPAY_PUBLIC_KEY');
  const privatekey = pick('KKIAPAY_PRIVATE_KEY');
  const secretkey = pick('KKIAPAY_SECRET_KEY');

  if (!publickey || !privatekey || !secretkey) {
    throw new Error("clés KkiaPay absentes de l'environnement");
  }

  return {
    base: pick('KKIAPAY_SANDBOX') === 'true' ? BASE.sandbox : BASE.live,
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': publickey,
      'x-secret-key': secretkey,
      'x-private-key': privatekey,
    },
  };
}

async function call(route, payload, env) {
  const { base, headers } = credentials(env);

  // Un appel qui traîne bloquerait la fonction jusqu'à son plafond de durée.
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), 12_000);

  try {
    const res = await fetch(base + route, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: abort.signal,
    });

    const text = await res.text();
    let body;
    try {
      body = text ? JSON.parse(text) : {};
    } catch {
      body = { raw: text.slice(0, 500) };
    }

    if (!res.ok) {
      return { error: `KkiaPay a répondu ${res.status}`, body };
    }
    return { body };
  } catch (err) {
    const reason = err?.name === 'AbortError' ? 'délai dépassé' : (err?.message || 'erreur réseau');
    return { error: 'KkiaPay injoignable : ' + reason };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Interroge KkiaPay sur une transaction.
 *
 * @param {string} transactionId
 * @param {number} expectedAmount  montant réclamé, en FCFA
 * @param {object} env             variables d'environnement (Workers)
 */
export async function verifyTransaction(transactionId, expectedAmount, env) {
  const id = String(transactionId || '').trim();
  if (!id || id.length > 64) return { ok: false, reason: 'identifiant de transaction invalide' };

  const { body: raw, error } = await call(ROUTE_STATUS, { transactionId: id }, env);
  if (error) return { ok: false, reason: error, raw };

  if (!raw || raw.status !== 'SUCCESS') {
    return { ok: false, reason: `transaction non aboutie (${raw?.status || 'inconnue'})`, raw };
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

/** Remboursement. Les frais de transaction ne sont pas restitués par KkiaPay. */
export async function refundTransaction(transactionId, env) {
  const { body, error } = await call(ROUTE_REVERT, { transactionId: String(transactionId) }, env);
  return error ? { ok: false, reason: error, raw: body } : { ok: true, raw: body };
}

/**
 * Vérifie qu'un webhook vient bien de KkiaPay : il signe ses appels avec
 * l'en-tête x-kkiapay-secret.
 */
export function webhookIsAuthentic(secretReceived, env = {}) {
  const expected = env.KKIAPAY_SECRET_KEY ?? globalThis.process?.env?.KKIAPAY_SECRET_KEY;
  if (!expected) return false;
  if (typeof secretReceived !== 'string') return false;
  if (secretReceived.length !== expected.length) return false;

  // Comparaison à durée constante : une comparaison naïve laisse fuiter le
  // secret caractère par caractère si l'attaquant mesure le temps de réponse.
  let diff = 0;
  for (let i = 0; i < expected.length; i += 1) {
    diff |= expected.charCodeAt(i) ^ secretReceived.charCodeAt(i);
  }
  return diff === 0;
}
