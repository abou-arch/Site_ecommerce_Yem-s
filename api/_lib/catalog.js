/* ===========================================================================
   Yem's — Tarification côté serveur

   LA RÈGLE : le panier envoyé par le navigateur ne dit QUE ce que le client
   veut acheter. Jamais combien ça coûte.

   Le panier vit dans localStorage. N'importe qui peut ouvrir la console et
   écrire price: 1 avant de payer. Tout montant qui arrive du client est donc
   ignoré : on ne garde que le slug, la quantité et les options, et on
   recalcule à partir de data/products.json, qui est dans le dépôt.
   =========================================================================== */

/* Le catalogue est importé, pas lu sur disque : il est ainsi empaqueté au
   build. Sur Cloudflare Workers il n'y a pas de système de fichiers durable —
   node:fs y est virtuel et vidé à chaque requête. Un import fonctionne
   partout, et évite un accès disque à chaque appel. */
import data from '../../data/products.json' with { type: 'json' };

function catalog() {
  return data;
}

export function site() {
  return data.site;
}

/** Frais de port par pays, en FCFA. */
const SHIPPING = { BJ: 0, CI: 0, TG: 2000, SN: 3000, NE: 3000 };

export function shippingFor(country) {
  return SHIPPING[country] ?? 3000;
}

/* --------------------------------------------------------------- produits */

function findProduct(slug) {
  return catalog().products.find((p) => p.slug === slug) || null;
}

function priceStandard(item) {
  const product = findProduct(item.id);
  if (!product) return { error: `produit inconnu : ${item.id}` };

  // Un modèle vendu uniquement sur-mesure ne peut pas entrer au panier
  // par la voie standard, même si le client force la requête.
  if (product.bespoke_only) {
    return { error: `${product.name} est disponible en sur-mesure uniquement` };
  }

  if (product.sizes?.length) {
    const size = Number(item.size);
    if (!product.sizes.includes(size)) {
      return { error: `pointure indisponible pour ${product.name}` };
    }
  }

  if (product.colors?.length && item.color) {
    const known = product.colors.some((c) => c.name === item.color);
    if (!known) return { error: `teinte inconnue pour ${product.name}` };
  }

  return {
    product_slug: product.slug,
    name: product.name,
    unit_price: product.price,
    size: item.size != null ? String(item.size) : null,
    color: item.color || null,
    bespoke: null,
  };
}

/* -------------------------------------------------------------- sur-mesure */

function priceBespoke(item) {
  const cfg = site().bespoke;
  const spec = item.bespoke || {};

  const shape = cfg.shapes.find((s) => s.id === spec.shape);
  const leather = cfg.leathers.find((l) => l.id === spec.leather);
  const sole = cfg.soles.find((s) => s.id === spec.sole);
  const size = Number(spec.size);

  if (!shape) return { error: 'forme sur-mesure inconnue' };
  if (!leather) return { error: 'cuir sur-mesure inconnu' };
  if (!sole) return { error: 'semelle sur-mesure inconnue' };
  if (!cfg.sizes.includes(size)) return { error: 'pointure sur-mesure invalide' };

  // 4 caractères max, lettres et points : même règle que le champ côté client,
  // revalidée ici parce qu'un champ HTML ne protège rien.
  const initials = String(spec.initials || '')
    .toUpperCase().replace(/[^A-ZÀ-Ö\s.]/g, '').slice(0, 4).trim();

  const unit_price =
    shape.price + leather.price + sole.price + (initials ? cfg.initials.price : 0);

  return {
    product_slug: `sur-mesure-${shape.id}`,
    name: `${shape.name} — sur-mesure`,
    unit_price,
    size: String(size),
    color: leather.name,
    bespoke: {
      shape: shape.id, leather: leather.id, sole: sole.id,
      size, initials,
    },
  };
}

/* ------------------------------------------------------------------ panier */

/**
 * Transforme un panier client en lignes de commande vérifiées.
 * Retourne { items, subtotal, kind } ou { error }.
 */
export function priceCart(rawCart) {
  if (!Array.isArray(rawCart) || rawCart.length === 0) {
    return { error: 'panier vide' };
  }
  if (rawCart.length > 40) {
    return { error: 'panier trop volumineux' };
  }

  const items = [];
  let subtotal = 0;
  let hasStandard = false;
  let hasBespoke = false;

  for (const raw of rawCart) {
    const qty = Math.floor(Number(raw.qty));
    if (!Number.isFinite(qty) || qty < 1 || qty > 20) {
      return { error: 'quantité invalide' };
    }

    const isBespoke = Boolean(raw.bespoke) || String(raw.id || '').startsWith('sur-mesure-');
    const priced = isBespoke ? priceBespoke(raw) : priceStandard(raw);
    if (priced.error) return { error: priced.error };

    if (isBespoke) hasBespoke = true; else hasStandard = true;

    const line_total = priced.unit_price * qty;
    subtotal += line_total;
    items.push({ ...priced, qty, line_total });
  }

  return {
    items,
    subtotal,
    kind: hasBespoke && hasStandard ? 'mixed' : hasBespoke ? 'bespoke' : 'standard',
  };
}

/**
 * Ce qu'on encaisse maintenant.
 * Le sur-mesure part en production avant d'être payé en entier : on prend
 * l'acompte prévu au catalogue, le solde est réglé à la livraison.
 */
export function amountDue(total, kind) {
  if (kind === 'standard') return total;
  const pct = site().bespoke.deposit ?? 50;
  // arrondi aux 500 F supérieurs — on ne réclame pas 74 213 F en Mobile Money
  return Math.ceil((total * pct) / 100 / 500) * 500;
}
