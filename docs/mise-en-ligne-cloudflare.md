# Mise en ligne sur Cloudflare — pas à pas

Guide de mise en route, dans l'ordre. Compte environ une heure la première fois.
Chaque étape se termine par un point de contrôle : si ce que tu vois ne
correspond pas, ne passe pas à la suite.

Pour le pourquoi des choix techniques, voir [`back-end.md`](back-end.md).

---

## Avant de commencer

Trois comptes à créer, tous gratuits :

| Service | À quoi il sert | Lien |
|---|---|---|
| **Neon** | la base de données Postgres | [neon.tech](https://neon.tech) |
| **Cloudflare** | l'hébergement du site et des fonctions | [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) |
| **KkiaPay** | l'encaissement Mobile Money, Wave et carte | [kkiapay.me](https://kkiapay.me) |

Et sur ta machine : **Node.js 20 ou plus**. Pour vérifier :

```bash
node --version
```

> **Ce que ça coûte.** Rien au démarrage. Cloudflare offre 100 000 requêtes de
> base de données par jour et des fichiers statiques illimités sur le plan
> gratuit. Neon a un palier gratuit suffisant pour une boutique qui démarre.
> Tu ne paieras que si le trafic décolle vraiment.

---

## Étape 1 — Créer la base

1. Sur [neon.tech](https://neon.tech), crée un projet. Nomme-le `yems`.
2. Choisis la région **Europe (Frankfurt)** — c'est la plus proche de l'Afrique
   de l'Ouest parmi celles proposées.
3. Une fois créé, copie la **chaîne de connexion** (bouton *Connect*). Elle
   ressemble à :

```
postgresql://yems_owner:xxxxx@ep-quelque-chose.eu-central-1.aws.neon.tech/yems?sslmode=require
```

Garde-la de côté, tu vas t'en servir deux fois.

> ✓ **Contrôle** — tu as une chaîne qui commence par `postgresql://` et finit
> par `?sslmode=require`.

---

## Étape 2 — Installer le schéma

Dans le dossier du projet :

```bash
psql "COLLE_TA_CHAINE_ICI" -f db/schema.sql
```

Si `psql` n'est pas installé, Neon propose un éditeur SQL dans son interface
(*SQL Editor*) : ouvre `db/schema.sql`, copie tout, colle, exécute.

> ✓ **Contrôle** — dans Neon, onglet *Tables*, tu dois voir six tables :
> `customers`, `orders`, `order_items`, `payments`, `order_events`, `couriers`.

---

## Étape 3 — Se connecter à Cloudflare

```bash
npm install
npx wrangler login
```

Un navigateur s'ouvre, tu autorises Wrangler, tu reviens au terminal.

> ✓ **Contrôle** — `npx wrangler whoami` affiche ton adresse e-mail et ton
> identifiant de compte.

---

## Étape 4 — Créer la liaison Hyperdrive

Hyperdrive garde les connexions Postgres ouvertes côté Cloudflare. Sans lui,
chaque commande rouvrirait une connexion jusqu'à Francfort — plusieurs
centaines de millisecondes perdues à chaque fois.

```bash
npx wrangler hyperdrive create yems-db \
  --connection-string="COLLE_TA_CHAINE_NEON_ICI"
```

La commande répond avec un bloc contenant un `id` :

```
[[hyperdrive]]
binding = "HYPERDRIVE"
id = "a1b2c3d4e5f6..."
```

**Ouvre `wrangler.toml`** et remplace `REMPLACER_PAR_L_ID_HYPERDRIVE` par cet
identifiant.

> ✓ **Contrôle** — `npx wrangler hyperdrive list` affiche `yems-db`.

---

## Étape 5 — Récupérer les clés KkiaPay

Sur [app.kkiapay.me/dashboard](https://app.kkiapay.me/dashboard), menu
**Développeurs**. Tu y trouves trois clés.

| Clé | Où elle va |
|---|---|
| Publique | descend dans le navigateur — c'est normal, elle ne permet que d'ouvrir le widget |
| Privée | **ne quitte jamais le serveur** — elle vérifie les transactions |
| Secrète | **ne quitte jamais le serveur** — elle authentifie les webhooks |

> ⚠ Si la clé privée se retrouve dans le code du site, n'importe qui peut
> interroger ton compte marchand. Elle ne doit apparaître qu'à l'étape suivante,
> jamais dans un fichier du dépôt.

---

## Étape 6 — Poser les secrets

Chaque commande demande la valeur, que tu colles puis valides. Elles sont
chiffrées côté Cloudflare et ne réapparaissent jamais en clair.

```bash
npx wrangler secret put KKIAPAY_PUBLIC_KEY
npx wrangler secret put KKIAPAY_PRIVATE_KEY
npx wrangler secret put KKIAPAY_SECRET_KEY
npx wrangler secret put ADMIN_TOKEN
```

Pour `ADMIN_TOKEN`, génère-le d'abord :

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Note-le quelque part de sûr : c'est lui qui ouvrira l'administration.

Ensuite, ouvre `wrangler.toml` et corrige la section `[vars]` :

```toml
[vars]
KKIAPAY_SANDBOX = "true"          # on reste en test pour l'instant
OWNER_WHATSAPP = "22997XXXXXX"    # le vrai numéro de l'atelier
```

> ✓ **Contrôle** — `npx wrangler secret list` affiche les quatre noms (pas les
> valeurs, c'est normal).

---

## Étape 7 — Premier déploiement

```bash
npm run deploy
```

Cette commande génère les pages avec `build.py`, puis les envoie avec le Worker.

Wrangler affiche à la fin une adresse du type :

```
https://yems.TON-COMPTE.workers.dev
```

> ✓ **Contrôle** — ouvre cette adresse. Tu dois voir la homepage avec la vidéo.
> Clique sur *Chaussures*, puis sur un produit : les pages doivent s'afficher.

---

## Étape 8 — Vérifier que le serveur répond

Trois tests rapides, en remplaçant l'adresse par la tienne.

**Le panier vide doit être refusé :**

```bash
curl -X POST https://yems.TON-COMPTE.workers.dev/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{"cart":[]}'
```

Réponse attendue : `{"ok":false,"error":"panier vide"}`

**L'administration doit refuser sans jeton :**

```bash
curl https://yems.TON-COMPTE.workers.dev/api/admin/orders
```

Réponse attendue : `{"ok":false,"error":"accès refusé"}`

**Et l'accepter avec :**

```bash
curl https://yems.TON-COMPTE.workers.dev/api/admin/orders \
  -H "Authorization: Bearer TON_ADMIN_TOKEN"
```

Réponse attendue : `{"ok":true,"count":0,"orders":[]}`

> ✓ **Contrôle** — si le troisième test répond `count: 0`, la base est bien
> connectée. C'est le test le plus important de tous.

---

## Étape 9 — Brancher le webhook

Dans KkiaPay → **Développeurs** → **Webhook**, déclare :

```
https://yems.TON-COMPTE.workers.dev/api/webhooks/kkiapay
```

À quoi il sert : si un client paie puis ferme son navigateur avant le retour,
le site n'apprend jamais que le paiement a réussi. La commande resterait en
attente alors que l'argent est encaissé. KkiaPay prévient alors le serveur
directement.

---

## Étape 10 — Commander pour de faux

Toujours en `KKIAPAY_SANDBOX = "true"`.

1. Va sur le site, ajoute une paire au panier.
2. Passe commande avec tes vraies coordonnées.
3. Au moment du paiement, utilise un
   [numéro de test KkiaPay](https://docs.kkiapay.me/v1/compte/kkiapay-sandbox-guide-de-test).

> ✓ **Contrôle** — après le paiement, tu dois arriver sur la page de
> confirmation avec une référence du type `YMS-1108-0001`. Et
> `/api/admin/orders` doit maintenant retourner cette commande avec le statut
> `paid`, plus un `whatsapp_link` prêt à cliquer.

Si tu cliques ce lien, WhatsApp s'ouvre avec le récapitulatif de la commande
déjà rédigé. C'est le mode de fonctionnement tant que l'API Meta n'est pas
configurée — et c'est suffisant pour démarrer.

---

## Étape 11 — Passer en production

Quand le compte marchand KkiaPay est activé et que les tests passent :

1. Dans `wrangler.toml`, mets `KKIAPAY_SANDBOX = "false"`.
2. `npm run deploy`
3. Fais **une vraie commande, un petit montant**, avec ton propre Mobile Money.
   Vérifie que l'argent arrive sur le tableau de bord KkiaPay.

> Ne saute pas ce dernier test. Le mode sandbox et le mode réel n'utilisent pas
> les mêmes serveurs KkiaPay : quelque chose peut marcher en test et échouer en
> production.

---

## Le nom de domaine

L'adresse `workers.dev` fonctionne, mais pour le client il faut un vrai domaine.

1. Achète le domaine (`yems.bj`, `yems-cotonou.com`, ce que le client préfère).
2. Dans Cloudflare, **Add a site**, puis suis les instructions pour pointer les
   serveurs de noms du registrar vers Cloudflare.
3. Une fois le domaine actif, ajoute dans `wrangler.toml` :

```toml
routes = [
  { pattern = "yems.bj", custom_domain = true },
  { pattern = "www.yems.bj", custom_domain = true }
]
```

4. `npm run deploy`

Le certificat HTTPS est émis automatiquement par Cloudflare.

**N'oublie pas** de mettre à jour l'URL du webhook chez KkiaPay avec le nouveau
domaine.

---

## Au quotidien

Après chaque modification du site ou du catalogue :

```bash
npm run deploy
```

Environ trente secondes. Pas besoin de passer par GitHub.

Pour tester en local avant d'envoyer :

```bash
npm run dev          # démarre wrangler sur http://localhost:8787
```

---

## Si ça coince

| Symptôme | Cause probable | Quoi faire |
|---|---|---|
| `no such binding HYPERDRIVE` | l'id n'a pas été reporté | vérifier `wrangler.toml`, étape 4 |
| `aucune chaîne de connexion` | idem | idem |
| `/api/admin/orders` → `accès refusé` avec le bon jeton | `ADMIN_TOKEN` mal posé | refaire `wrangler secret put ADMIN_TOKEN` |
| `clés KkiaPay absentes` | un secret manque | `npx wrangler secret list` |
| `transaction non aboutie` en test | numéro de test non reconnu | prendre un numéro de la doc sandbox |
| `montant insuffisant` | le client a payé moins que demandé | c'est le comportement voulu — la commande reste en attente |
| Les pages sont à jour mais pas le style | cache navigateur | `Ctrl + Maj + R` |
| Le site affiche du code source | `.assetsignore` ignoré | vérifier qu'il est bien à la racine du dépôt |

Pour voir ce qui se passe côté serveur en direct :

```bash
npx wrangler tail
```

Les erreurs y apparaissent avec leur détail complet — celui qui n'est jamais
renvoyé au visiteur.

---

## Ce qui reste à construire

- [ ] Page d'administration : `/api/admin/orders` existe, il manque l'écran
- [ ] Relance du solde sur-mesure à la livraison
- [ ] Statut VIP — le champ existe, rien ne l'exploite
- [ ] Affectation d'un livreur — le champ existe, pas d'interface
- [ ] Remplacer les photos portant des marques de fabricants tiers
- [ ] Prix définitifs, témoignages réels, numéro WhatsApp de l'atelier
