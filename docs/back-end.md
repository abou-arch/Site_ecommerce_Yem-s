# Back-end — mise en route

Le site reste généré par `tools/build.py`. Ce qui change : il n'est plus servi
par GitHub Pages mais par **Cloudflare**, qui héberge en plus les fonctions
serveur.

GitHub Pages ne peut pas faire tourner de code serveur. Or la clé privée KkiaPay
ne doit jamais descendre dans le navigateur, et toute transaction doit être
vérifiée côté serveur — c'est explicite dans la documentation KkiaPay. D'où le
déménagement.

Cloudflare plutôt qu'un autre : ses points de présence en Afrique de l'Ouest
raccourcissent le trajet depuis Cotonou et Abidjan, et c'est là que sont les
clients.

## Une architecture qui ne dépend pas de l'hébergeur

```
                      Cloudflare
   navigateur ──────► Pages (statique)      pages générées par build.py
        │             Worker (/api/*)  ◄──  worker.js   ← le seul fichier
        │                   │                             qui connaît
        │                   ▼                             Request/Response
        │             api/_lib/handlers.js  ← toute la logique, portable
        │                   │
        │                   ├─► Hyperdrive ──► Postgres (Neon)
        │                   ├─► api.kkiapay.me   (fetch, sans SDK)
        │                   └─► graph.facebook.com (WhatsApp, facultatif)
        │
        └──────────────────► cdn.kkiapay.me/k.js  (widget, clé publique)
```

`api/_lib/` ne connaît ni Request, ni Response, ni `process.env` : chaque
fonction reçoit `env` en argument et rend `{ status, body }`. Changer
d'hébergeur ne toucherait que `worker.js`, une centaine de lignes.

Deux dépendances ont été supprimées pour y arriver :

- **`node:fs`** — le catalogue est importé (`import data from '.../products.json'`)
  au lieu d'être lu sur disque. Sur Workers, [le système de fichiers est virtuel
  et vidé à chaque requête](https://developers.cloudflare.com/changelog/post/2025-08-15-nodejs-fs/) :
  le fichier n'y serait pas.
- **`@kkiapay-org/nodejs-sdk`** — ce paquet n'est qu'un habillage `axios` autour
  de deux routes REST (`/api/v1/transactions/status` et `/revert`, avec trois
  en-têtes). Vingt lignes de `fetch` font la même chose, sans dépendance.

Il ne reste qu'une dépendance d'exécution : le driver `postgres`.

---

## Le principe de sécurité, en une phrase

**Le panier dit ce que le client achète. Jamais combien ça coûte.**

Le panier vit dans le `localStorage` du navigateur. N'importe qui peut ouvrir la
console et écrire `price: 1` avant de payer. Alors :

1. `api/orders/create` ignore tout montant reçu et recalcule à partir de
   `data/products.json` (`api/_lib/catalog.js`).
2. Le widget KkiaPay est ouvert avec **le montant renvoyé par le serveur**.
3. `api/payments/verify` redemande la transaction à KkiaPay avec la clé privée
   et compare le montant réellement encaissé à celui inscrit en base.

Un client qui falsifie son panier obtient un prix correct. Un client qui
falsifie la réponse de paiement se fait refuser à l'étape 3.

---

## Mise en route

### 1. La base

Créer une base Postgres — [Neon](https://neon.tech) ou Supabase, les deux ont un
palier gratuit — puis :

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

Tables créées : `customers`, `orders`, `order_items`, `payments`, `order_events`,
`couriers`.

Deux choix qui comptent :

- **Les montants sont des entiers.** Le FCFA n'a pas de sous-unité, et un entier
  supprime tout arrondi flottant sur les totaux.
- **Les lignes de commande recopient nom et prix.** Si un tarif change demain,
  une commande passée hier garde ses montants.

### 2. Les clés

Copier `.env.example` en `.env`, remplir depuis
[app.kkiapay.me/dashboard](https://app.kkiapay.me/dashboard) → Développeurs.

| Variable | Où elle vit | Rôle |
|---|---|---|
| `KKIAPAY_PUBLIC_KEY` | serveur → navigateur | ouvre le widget |
| `KKIAPAY_PRIVATE_KEY` | **serveur seul** | vérifie les transactions |
| `KKIAPAY_SECRET_KEY` | **serveur seul** | authentifie les webhooks |
| `KKIAPAY_SANDBOX` | serveur | `true` tant que le compte n'est pas activé |
| `DATABASE_URL` | serveur | connexion Postgres |
| `OWNER_WHATSAPP` | serveur | numéro de l'atelier |
| `ADMIN_TOKEN` | serveur | accès à `/api/admin/*` — 32 caractères minimum |

Générer le jeton admin :

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### 3. Relier la base à Cloudflare

Hyperdrive maintient le pool de connexions côté Cloudflare et rapproche les
connexions de la base — sans lui, chaque requête depuis un Worker rouvrirait
une connexion à travers l'Atlantique.

```bash
npx wrangler hyperdrive create yems-db --connection-string="postgres://user:pass@host/db?sslmode=require"
```

Reporter l'identifiant renvoyé dans `wrangler.toml`, champ `id`.

> Utiliser la connexion **directe**, pas la « pooled » (`-pooler` dans le nom
> d'hôte) : Hyperdrive assure déjà le pooling, et empiler les deux provoque
> des erreurs SSL. Retirer aussi `channel_binding=require`.

### 4. Poser les secrets

Ils sont chiffrés côté Cloudflare, jamais écrits dans le dépôt :

```bash
npx wrangler secret put KKIAPAY_PUBLIC_KEY
npx wrangler secret put KKIAPAY_PRIVATE_KEY
npx wrangler secret put KKIAPAY_SECRET_KEY
npx wrangler secret put ADMIN_TOKEN
npx wrangler secret put WHATSAPP_TOKEN      # facultatif
npx wrangler secret put WHATSAPP_PHONE_ID   # facultatif
```

`KKIAPAY_SANDBOX` et `OWNER_WHATSAPP` sont dans `[vars]` de `wrangler.toml` :
ils ne sont pas secrets.

### 5. Déployer

```bash
npm install
npm run deploy        # build.py puis wrangler deploy
```

`.assetsignore` empêche la mise en ligne des sources : `api/`, `templates/`,
`tools/`, `data/`, la documentation et les fichiers de travail restent hors du
déploiement statique.

### 6. Le webhook

Dans le tableau de bord KkiaPay → Développeurs → Webhook, déclarer :

```
https://<votre-domaine>/api/webhooks/kkiapay
```

Il sert de filet : si le client ferme son navigateur juste après avoir payé,
`/api/payments/verify` n'est jamais appelé et la commande resterait « pending »
alors que l'argent est encaissé. KkiaPay prévient alors le serveur directement.

### 7. Tester avant d'ouvrir

Garder `KKIAPAY_SANDBOX=true` et utiliser les
[numéros de test KkiaPay](https://docs.kkiapay.me/v1/compte/kkiapay-sandbox-guide-de-test).
Ne passer à `false` qu'une fois le compte marchand activé.

---

## Les routes

| Route | Méthode | Rôle |
|---|---|---|
| `/api/orders/create` | POST | Valide le panier, recalcule les montants, crée la commande |
| `/api/payments/verify` | POST | Vérifie la transaction auprès de KkiaPay, encaisse, notifie |
| `/api/webhooks/kkiapay` | POST | Filet de sécurité, signature vérifiée |
| `/api/admin/orders` | GET / POST | Liste les commandes, change un statut |

### Idempotence

`payments.transaction_id` porte une contrainte d'unicité. C'est elle qui garantit
qu'une même transaction ne peut pas être encaissée deux fois — que le double appel
vienne d'un rechargement de page ou du webhook arrivé en même temps que la
vérification normale.

---

## La notification WhatsApp

Deux modes, volontairement :

- **API WhatsApp Cloud** si `WHATSAPP_TOKEN` et `WHATSAPP_PHONE_ID` sont remplis :
  le message part tout seul.
- **Sinon**, un lien `wa.me` pré-rempli est calculé et renvoyé par
  `/api/admin/orders`. L'atelier clique, WhatsApp s'ouvre avec le message prêt.

Le deuxième mode permet d'encaisser **dès le premier jour**, sans attendre la
validation d'un compte Meta Business — qui prend souvent plusieurs jours.

Une notification qui échoue ne fait jamais échouer un paiement déjà encaissé :
l'erreur est journalisée dans `order_events`, la commande reste valide.

---

---

## Deux modes de règlement

`PAYMENT_MODE` commande tout le tunnel.

| Mode | Ce qui se passe | Statut de la commande |
|---|---|---|
| `offline` *(défaut)* | commande enregistrée, atelier prévenu sur WhatsApp | `to_confirm` |
| `online` | widget du prestataire, vérification serveur | `paid` ou `deposit` |

Le mode `offline` existe parce qu'un compte marchand se mérite : pièce
d'identité, IFU, parfois RCCM, et des semaines d'instruction. Il n'y a aucune
raison de bloquer le lancement d'une boutique pour ça — la plupart des ateliers
de la sous-région encaissent à la livraison de toute façon.

En `offline`, le client choisit entre :

- **à la livraison** — espèces ou Mobile Money à la remise ;
- **par transfert** — l'atelier envoie son numéro, la production démarre à
  réception de l'acompte.

Le serveur impose le transfert dès que le panier contient une pièce sur-mesure :
elle engage de la matière, on ne la lance pas sans acompte. Et si
`PAYMENT_MODE = "online"` sans clé publique posée, le serveur **retombe seul**
sur `offline` — la boutique ne peut pas se retrouver avec des commandes
bloquées en attente d'un paiement impossible.

Le message WhatsApp change selon le mode : il indique à l'atelier ce qu'il
reste à encaisser et ce qu'il doit faire ensuite.

## Le cycle de vie d'une commande

```
                    ┌── mode online ──────────────────────────────┐
pending ──vérifié──►│ paid      (standard, réglé en entier)       │
                    │ deposit   (sur-mesure, acompte 50 %)        │
                    └────────────────────┬────────────────────────┘
                                         │
to_confirm ──────────────────────────────┤   ← mode offline
  (l'atelier rappelle, encaisse,         │
   puis fait avancer le statut)          ▼
                                   in_workshop ──► shipped ──► delivered
```

`cancelled` et `refunded` sont accessibles depuis l'admin à tout moment.

---

## Ce qui reste à faire

- [ ] Page d'administration (`/admin`) consommant `/api/admin/orders`
- [ ] Relance du solde sur-mesure à la livraison
- [ ] Statut VIP : le champ `customers.is_vip` existe, rien ne l'exploite encore
- [ ] Affectation d'un livreur : `orders.courier_id` existe, pas d'interface
- [ ] Facture PDF pour le sur-mesure
- [ ] Migrer le domaine depuis GitHub Pages une fois Cloudflare validé

---

## Sources

- [SDK JavaScript KkiaPay](https://docs.kkiapay.me/v1/plugin-et-sdk/sdk-javascript)
- [SDK Node.js serveur](https://docs.kkiapay.me/v1/plugin-et-sdk/admin-sdks-server-side/node.js-admin-sdk)
- [Webhook KkiaPay](https://docs.kkiapay.me/v1/tableau-de-bord/webhook)
