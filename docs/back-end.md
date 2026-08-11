# Back-end — mise en route

Le site reste généré par `tools/build.py`. Ce qui change : il n'est plus servi
par GitHub Pages mais par **Vercel**, qui héberge en plus les fonctions serveur.

GitHub Pages ne peut pas faire tourner de code serveur. Or la clé privée KkiaPay
ne doit jamais descendre dans le navigateur, et toute transaction doit être
vérifiée côté serveur — c'est explicite dans la documentation KkiaPay. D'où le
déménagement.

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

### 3. Déployer

```bash
npm install
npx vercel            # première fois : lie le projet
npx vercel --prod
```

Puis reporter les variables dans **Vercel → Settings → Environment Variables**.

### 4. Le webhook

Dans le tableau de bord KkiaPay → Développeurs → Webhook, déclarer :

```
https://<votre-domaine>/api/webhooks/kkiapay
```

Il sert de filet : si le client ferme son navigateur juste après avoir payé,
`/api/payments/verify` n'est jamais appelé et la commande resterait « pending »
alors que l'argent est encaissé. KkiaPay prévient alors le serveur directement.

### 5. Tester avant d'ouvrir

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

## Le cycle de vie d'une commande

```
pending ──paiement vérifié──► paid          (achat standard, réglé en entier)
        └─────────────────► deposit        (sur-mesure, acompte 50 %)
                                │
                                ▼
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
- [ ] Migrer le domaine depuis GitHub Pages une fois Vercel validé

---

## Sources

- [SDK JavaScript KkiaPay](https://docs.kkiapay.me/v1/plugin-et-sdk/sdk-javascript)
- [SDK Node.js serveur](https://docs.kkiapay.me/v1/plugin-et-sdk/admin-sdks-server-side/node.js-admin-sdk)
- [Webhook KkiaPay](https://docs.kkiapay.me/v1/tableau-de-bord/webhook)
