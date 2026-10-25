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

/**
 * Le produit du catalogue, corrigé par ce que l'atelier a modifié.
 *
 * C'EST LE POINT CRITIQUE DE TOUT L'ÉDIFICE. Le prix affiché sur la page est
 * réécrit en bordure à partir de ces mêmes corrections. Si cette fonction les
 * ignorait, la boutique afficherait 92 000 F et facturerait 85 000 : l'atelier
 * vendrait à perte sans jamais s'en apercevoir. Une seule source, lue des
 * deux côtés.
 */
function findProduct(slug, corrections = {}) {
  const base = catalog().products.find((p) => p.slug === slug) || null;
  if (!base) return null;

  const c = corrections[slug];
  if (!c) return base;

  return {
    ...base,
    price: c.price ?? base.price,
    status: c.status ?? base.status,
    short: c.short ?? base.short,
    images: c.images ?? base.images,
    hidden: Boolean(c.hidden),
  };
}

/* Les erreurs de ce fichier remontent telles quelles jusqu'au client, sous le
   bouton de commande : elles disent ce qui bloque et comment s'en sortir. */
const RETIRER = 'Retirez cette pièce du panier, puis validez à nouveau.';

function priceStandard(item, corrections) {
  const product = findProduct(item.id, corrections);
  if (!product) return { error: `Une pièce de votre panier n'est plus au catalogue. ${RETIRER}` };

  // Une pièce retirée de la vente ne peut plus entrer au panier, même si le
  // client avait gardé l'onglet ouvert avant le retrait.
  if (product.hidden) {
    return { error: `${product.name} n'est plus disponible. ${RETIRER}` };
  }

  /* Une pièce en attente de photos n'a ni fiche, ni vignette, ni prix engagé.
     Le générateur l'écarte du site, mais le serveur, lui, la trouvait encore
     par son slug : une requête forgée à la main suffisait à commander un
     Loafer Ouidah à 88 000 F, un modèle que la page « Ce qui se prépare »
     annonce justement comme non encore arrêté, prix compris.

     Le filtrage à la construction du site ne vaut donc rien sans ce garde-fou
     côté serveur. C'est la même règle que partout ailleurs ici : le HTML
     propose, le serveur décide. */
  if (product.a_venir) {
    return { error: `${product.name} n'est pas encore en vente. ${RETIRER}` };
  }

  // Un modèle vendu uniquement sur-mesure ne peut pas entrer au panier
  // par la voie standard, même si le client force la requête. Même règle
  // pour les formes qui n'existent que dans le configurateur : le générateur
  // les écarte des pages, le serveur doit les écarter du panier.
  if (product.bespoke_only || product.configurateur_only) {
    return { error: `${product.name} se commande uniquement en sur-mesure, depuis le configurateur.` };
  }

  /* Pointure et teinte ne sont retenues que si elles viennent du catalogue.
     Une valeur libre finissait telle quelle dans la base, dans l'admin et
     dans le message WhatsApp de l'atelier, sans limite de longueur. */
  let size = null;
  if (product.sizes?.length) {
    size = Number(item.size);
    if (!product.sizes.includes(size)) {
      return { error: `Cette pointure n'existe pas pour ${product.name}. ${RETIRER}` };
    }
  }

  let color = null;
  if (product.colors?.length && item.color) {
    color = product.colors.find((c) => c.name === item.color)?.name || null;
    if (!color) return { error: `Cette couleur n'existe pas pour ${product.name}. ${RETIRER}` };
  }

  return {
    product_slug: product.slug,
    name: product.name,
    unit_price: product.price,
    size: size != null ? String(size) : null,
    color,
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

  // Une seule phrase pour le client : quelle que soit l'option périmée, la
  // solution est la même.
  const perime = { error: 'Une option de votre paire sur-mesure n\'existe plus. '
                        + 'Retirez-la du panier et recomposez-la dans le configurateur.' };
  if (!shape || !leather || !sole || !cfg.sizes.includes(size)) return perime;

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
export function priceCart(rawCart, corrections = {}) {
  if (!Array.isArray(rawCart) || rawCart.length === 0) {
    return { error: 'Votre panier est vide : ajoutez une pièce avant de valider.' };
  }
  if (rawCart.length > 40) {
    return { error: 'Votre panier dépasse ce qu\'une commande en ligne peut contenir. '
                  + 'Écrivez-nous sur WhatsApp : on la prend à la main.' };
  }

  const items = [];
  let subtotal = 0;
  let hasStandard = false;
  let hasBespoke = false;

  for (const raw of rawCart) {
    if (!raw || typeof raw !== 'object') {
      return { error: 'Une ligne de votre panier est illisible. Videz le panier, puis ajoutez à nouveau vos pièces.' };
    }
    const qty = Math.floor(Number(raw.qty));
    if (!Number.isFinite(qty) || qty < 1 || qty > 20) {
      return { error: 'Une quantité du panier est hors limites : de 1 à 20 exemplaires par pièce.' };
    }

    const isBespoke = Boolean(raw.bespoke) || String(raw.id || '').startsWith('sur-mesure-');
    const priced = isBespoke ? priceBespoke(raw) : priceStandard(raw, corrections);
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
/**
 * Le catalogue tel qu'il doit apparaître : corrections appliquées, pièces
 * masquées retirées. Sert à l'écran d'administration et à la réécriture des
 * pages en bordure, pour que les deux lisent exactement la même chose.
 */
/** Ce que le public a le droit de voir.
 *  Deux motifs d'exclusion, et ils ne se confondent pas :
 *  hidden  = l'atelier l'a retirée depuis son écran ;
 *  a_venir = elle n'a pas encore été photographiée, donc elle n'existe pas
 *            encore pour un client. */
export function catalogueVisible(corrections = {}) {
  return catalog().products
    .map((p) => findProduct(p.slug, corrections))
    .filter((p) => p && !p.hidden && !p.a_venir);
}

/** Toutes les pièces, y compris masquées, avec l'état de leur correction.
 *  L'atelier doit voir ce qu'il a retiré pour pouvoir le remettre. */
export function catalogueComplet(corrections = {}) {
  return catalog().products.map((p) => ({
    ...findProduct(p.slug, corrections),
    correction: corrections[p.slug] || null,
    prix_catalogue: p.price,
    statut_catalogue: p.status,
    short_catalogue: p.short,
  }));
}

export function amountDue(total, kind) {
  if (kind === 'standard') return total;
  const pct = site().bespoke.deposit ?? 50;
  // arrondi aux 500 F supérieurs — on ne réclame pas 74 213 F en Mobile Money
  return Math.ceil((total * pct) / 100 / 500) * 500;
}
