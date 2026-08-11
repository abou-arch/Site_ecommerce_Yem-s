/* ===========================================================================
   Yem's — Aides HTTP communes aux fonctions serveur
   =========================================================================== */

export function json(res, status, body) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.status(status).end(JSON.stringify(body));
}

export function fail(res, status, message, extra = {}) {
  return json(res, status, { ok: false, error: message, ...extra });
}

/** N'autorise que la méthode attendue. */
export function methodGuard(req, res, method) {
  if (req.method === method) return true;
  res.setHeader('Allow', method);
  fail(res, 405, 'méthode non autorisée');
  return false;
}

/** Corps JSON, que la plateforme l'ait déjà analysé ou non. */
export async function readJson(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 128 * 1024) throw new Error('corps trop volumineux');
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString('utf8');
  return raw ? JSON.parse(raw) : {};
}

/** Corps brut — nécessaire pour vérifier une signature de webhook. */
export async function readRaw(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
}

/* ------------------------------------------------------------ validation */

export function cleanText(value, max = 200) {
  return String(value ?? '').replace(/\s+/g, ' ').trim().slice(0, max);
}

/**
 * Normalise un numéro ouest-africain : on retire tout sauf les chiffres,
 * et on préfixe l'indicatif si le client a saisi son numéro local.
 * 97 00 00 00 → 22997000000
 */
export function cleanPhone(value, country = 'BJ') {
  const digits = String(value ?? '').replace(/\D/g, '');
  if (!digits) return null;
  const cc = { BJ: '229', CI: '225', TG: '228', SN: '221', NE: '227' }[country] || '229';
  if (digits.startsWith(cc)) return digits.slice(0, 15);
  if (digits.length <= 10) return (cc + digits).slice(0, 15);
  return digits.slice(0, 15);
}

export function isEmail(value) {
  const v = String(value ?? '').trim();
  return v === '' || /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
}

export const COUNTRIES = ['BJ', 'CI', 'TG', 'SN', 'NE'];

/* --------------------------------------------------------------- limitation

   Garde-fou minimal contre le martèlement d'une même IP. La mémoire d'une
   instance serverless n'est pas partagée : ça ne remplace pas un vrai
   rate-limit, mais ça arrête un script naïf sans rien coûter.            */

const hits = new Map();

export function tooManyRequests(req, { max = 20, windowMs = 60_000 } = {}) {
  const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'inconnu';
  const now = Date.now();
  const entry = hits.get(ip);

  if (!entry || now > entry.reset) {
    hits.set(ip, { count: 1, reset: now + windowMs });
    if (hits.size > 500) for (const [k, v] of hits) if (now > v.reset) hits.delete(k);
    return false;
  }
  entry.count += 1;
  return entry.count > max;
}
