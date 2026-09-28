#!/usr/bin/env node
/* ===========================================================================
   Yem's — Test de tarification : configurateur contre serveur

   Le prix du sur-mesure est calculé deux fois : dans le navigateur par
   assets/js/configurator.js, qui l'affiche et le met au panier, puis sur le
   serveur par priceCart() (api/_lib/catalog.js), qui seul fait foi à la
   commande. S'ils divergent, le client voit un prix et en paie un autre.

   Ce script fait tourner le VRAI configurator.js, avec les données que la
   page générée lui donne (#cfg-data dans configurateur.html), dans un DOM
   réduit au strict nécessaire. Il clique chaque combinaison que le
   configurateur permet (forme × cuir × semelle × pointure × initiales) et
   vérifie que trois montants sont identiques au total tiré de
   data/products.json : le total affiché, le prix mis au panier, et le prix
   recalculé par le serveur. Il vérifie aussi le total de l'aperçu
   sur-mesure de l'accueil.

   Aucune dépendance. Code de sortie 1 au premier écart.

   Usage :  npm run build && npm run test:pricing
   =========================================================================== */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { priceCart } from '../api/_lib/catalog.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const lire = (rel) => readFileSync(path.join(ROOT, rel), 'utf8');
const chiffres = (texte) => Number(String(texte).replace(/\D/g, '')) || 0;

const ecarts = [];
const ecart = (message) => ecarts.push(message);

function arreter() {
  if (!ecarts.length) return;
  console.error(`\n✗ ${ecarts.length} écart(s) de tarification :`);
  ecarts.slice(0, 20).forEach((e) => console.error('  - ' + e));
  if (ecarts.length > 20) console.error(`  … et ${ecarts.length - 20} autre(s)`);
  process.exit(1);
}

/* ─────────────────────────────────────────────────────────── données */

const cfg = JSON.parse(lire('data/products.json')).site.bespoke;
const pageCfg = lire('configurateur.html');

const bloc = pageCfg.match(/<script type="application\/json" id="cfg-data">([\s\S]*?)<\/script>/);
if (!bloc) {
  ecart('configurateur.html : #cfg-data introuvable. Lancer npm run build.');
  arreter();
}
const donneesPage = JSON.parse(bloc[1]);

// Une page générée avant un changement de prix affiche l'ancien : le dire
// clairement plutôt que de laisser mille écarts parler à sa place.
for (const cle of ['shapes', 'leathers', 'soles', 'initials']) {
  if (JSON.stringify(donneesPage[cle]) !== JSON.stringify(cfg[cle])) {
    ecart(`configurateur.html n'est pas à jour pour « ${cle} » : relancer npm run build`);
  }
}

/* ─────────────────────────────────────────────── un DOM minimal */

// Juste ce que configurator.js appelle. Un sélecteur inconnu lève une
// erreur : si le script change, le test le dit au lieu de mentir.
class Noeud {
  constructor(balise, attributs = {}, enfants = []) {
    this.tagName = balise.toUpperCase();
    this.attrs = { ...attributs };
    this.children = enfants;
    this.ecouteurs = {};
    this.textContent = '';
    this.innerHTML = '';
    this.value = '';
    this.disabled = false;
    this.classList = { toggle() {}, add() {}, remove() {} };
  }

  get dataset() {
    const d = {};
    for (const [k, v] of Object.entries(this.attrs)) {
      if (k.startsWith('data-')) d[k.slice(5).replace(/-(\w)/g, (_, c) => c.toUpperCase())] = v;
    }
    return d;
  }

  get id() { return this.attrs.id || ''; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  toggleAttribute(k, force) { if (force) this.attrs[k] = ''; else delete this.attrs[k]; }
  addEventListener(type, fn) { (this.ecouteurs[type] ||= []).push(fn); }
  declencher(type) { (this.ecouteurs[type] || []).forEach((fn) => fn({ type, target: this })); }

  *descendants() {
    for (const e of this.children) { yield e; yield* e.descendants(); }
  }

  querySelectorAll(selecteur) {
    const m = selecteur.match(/^([a-z]+)?(?:\[([\w-]+)(?:="([^"]*)")?\])?$/i);
    if (!m) throw new Error(`sélecteur non pris en charge par le test : ${selecteur}`);
    const [, balise, attr, valeur] = m;
    return [...this.descendants()].filter((e) =>
      (!balise || e.tagName === balise.toUpperCase())
      && (!attr || (attr in e.attrs && (valeur === undefined || e.attrs[attr] === valeur))));
  }

  querySelector(selecteur) { return this.querySelectorAll(selecteur)[0] || null; }
}

const n = (balise, attributs, enfants) => new Noeud(balise, attributs, enfants);

// Les boutons d'option sont relevés dans la page générée : on clique ce
// que le visiteur peut réellement cliquer.
function groupe(cle) {
  const m = pageCfg.match(new RegExp(`data-group="${cle}">([\\s\\S]*?)</div>`));
  const ids = m ? [...m[1].matchAll(/<button[^>]*data-id="([^"]+)"/g)].map((x) => x[1]) : [];
  if (!ids.length) ecart(`configurateur.html : aucun bouton dans le groupe « ${cle} »`);
  return n('div', { 'data-group': cle }, ids.map((id) => n('button', { 'data-id': id })));
}

const ligne = (cle) => n('div', { 'data-line': cle },
  [n('em', { 'data-extra': '' }), n('span', { 'data-value': '' })]);

const donnees = n('script', { id: 'cfg-data' });
donnees.textContent = bloc[1];

const racine = n('div', { 'data-cfg': '' }, [
  groupe('shape'), groupe('leather'), groupe('sole'), groupe('size'),
  n('input', { 'data-cfg-initials': '' }),
  ...['shape', 'leather', 'sole', 'size', 'initials'].map(ligne),
  n('span', { 'data-total': '' }), n('span', { 'data-total': '' }),
  n('div', { 'data-cfg-shot': '' }),
  n('button', { 'data-cfg-add': '', 'data-cart': 'panier.html' }),
  n('button', { 'data-cfg-add': '', 'data-cart': 'panier.html' }),
]);
const html = n('html', {}, [racine, donnees]);

const document = {
  querySelector: (s) => html.querySelector(s),
  querySelectorAll: (s) => html.querySelectorAll(s),
  getElementById: (id) => [...html.descendants()].find((e) => e.id === id) || null,
};

/* ─────────────────────────────────────── le configurateur, tel quel */

const panier = [];
const bac = {
  document,
  console,
  CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init?.detail; } },
};
bac.window = bac;
bac.YemsCart = { add: (article) => panier.push(article) };
bac.dispatchEvent = () => true;
vm.createContext(bac);
vm.runInContext(lire('assets/js/configurator.js'), bac, { filename: 'assets/js/configurator.js' });

const cliquer = (cle, id) => {
  const bouton = racine.querySelector(`[data-group="${cle}"]`)?.querySelector(`button[data-id="${id}"]`);
  if (!bouton) return false;
  bouton.declencher('click');
  return true;
};

/* ─────────────────────────────────────────── toutes les combinaisons */

// Ce qu'un client peut taper, y compris ce que les deux côtés doivent
// ignorer : espaces seuls, chiffres, plus de quatre caractères.
const SAISIES = ['', 'AC', 'A. C.', 'éla', '   ', '12'];

// Le total attendu, lu dans le catalogue : forme + cuir + semelle, plus les
// initiales s'il en reste après nettoyage (même règle que le champ).
const nettoyer = (s) => s.toUpperCase().replace(/[^A-ZÀ-Ö\s.]/g, '').slice(0, 4).trim();
const attendu = (forme, cuir, semelle, saisie) =>
  forme.price + cuir.price + semelle.price + (nettoyer(saisie) ? cfg.initials.price : 0);

const champ = racine.querySelector('[data-cfg-initials]');
const totaux = racine.querySelectorAll('[data-total]');
const ajouter = racine.querySelector('[data-cfg-add]');
let combinaisons = 0;

for (const forme of cfg.shapes) {
  for (const cuir of cfg.leathers) {
    for (const semelle of cfg.soles) {
      for (const pointure of cfg.sizes) {
        for (const saisie of SAISIES) {
          combinaisons += 1;
          const nom = `${forme.id}/${cuir.id}/${semelle.id}/${pointure}/« ${saisie} »`;

          const absents = [['shape', forme.id], ['leather', cuir.id], ['sole', semelle.id],
                           ['size', String(pointure)]].filter(([cle, id]) => !cliquer(cle, id));
          if (absents.length) {
            ecart(`${nom} : option absente de la page (${absents.map((a) => a.join('=')).join(', ')})`);
            continue;
          }
          champ.value = saisie;
          champ.declencher('input');

          const prix = attendu(forme, cuir, semelle, saisie);

          totaux.forEach((el, i) => {
            if (chiffres(el.textContent) !== prix) {
              ecart(`${nom} : total affiché n° ${i + 1} « ${el.textContent} », attendu ${prix}`);
            }
          });

          panier.length = 0;
          ajouter.declencher('click');
          const article = panier[0];
          if (!article) { ecart(`${nom} : le bouton d'ajout n'a rien mis au panier`); continue; }
          if (article.price !== prix) ecart(`${nom} : prix mis au panier ${article.price}, attendu ${prix}`);

          const serveur = priceCart([article]);
          if (serveur.error) { ecart(`${nom} : refusé par le serveur (${serveur.error})`); continue; }
          if (serveur.items[0].unit_price !== prix || serveur.subtotal !== prix) {
            ecart(`${nom} : serveur ${serveur.items[0].unit_price} (sous-total ${serveur.subtotal}), attendu ${prix}`);
          }
        }
      }
    }
  }
}

/* ─────────────────────────────────── l'aperçu sur-mesure de l'accueil */

const apercu = cfg.apercu;
let prixApercu = null;
if (apercu) {
  const affiche = lire('index.html').match(/data-apercu-total>([^<]+)</);
  const serveur = priceCart([{
    id: `sur-mesure-${apercu.shape}`, qty: 1,
    bespoke: { ...apercu, size: cfg.sizes[0] },
  }]);
  if (!affiche) ecart('index.html : total de l\'aperçu sur-mesure introuvable (data-apercu-total)');
  else if (serveur.error) ecart(`aperçu de l'accueil refusé par le serveur (${serveur.error})`);
  else {
    prixApercu = serveur.subtotal;
    if (chiffres(affiche[1]) !== prixApercu) {
      ecart(`accueil : l'aperçu affiche « ${affiche[1]} », le serveur facturerait ${prixApercu}`);
    }
  }
}

arreter();
console.log(`✓ ${combinaisons} combinaisons sur-mesure : total affiché, prix au panier et prix serveur identiques`);
console.log(`  (${cfg.shapes.length} formes × ${cfg.leathers.length} cuirs × ${cfg.soles.length} semelles`
          + ` × ${cfg.sizes.length} pointures × ${SAISIES.length} saisies d'initiales)`);
if (prixApercu != null) console.log(`✓ aperçu de l'accueil : ${prixApercu} F, identique au serveur`);
