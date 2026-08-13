# Mettre le site en ligne

**Cinq étapes. Trente minutes.** Commandes données pour PowerShell (Windows).

Le paiement en ligne n'est **pas** dans ce guide : il n'est pas nécessaire pour
lancer la boutique. Il fait l'objet d'une section séparée, tout à la fin, pour
le jour où le compte marchand sera activé.

---

## Où tu en es

Coche au fur et à mesure.

- [ ] **1.** Base de données créée sur Neon
- [ ] **2.** Tables installées
- [ ] **3.** Hyperdrive relié
- [ ] **4.** Réglages posés
- [ ] **5.** Site déployé et vérifié

---

## 1. Créer la base

Sur [neon.tech](https://neon.tech) : crée un compte, puis un projet nommé
`yems`, région **Europe (Frankfurt)**.

Clique ensuite sur **Connect**, et **décoche la case « Pooled connection »**.

Copie la chaîne obtenue. Elle doit ressembler à ceci :

```
postgresql://neondb_owner:MOT_DE_PASSE@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

Si elle contient `-pooler` dans le nom d'hôte, ou `&channel_binding=require` à
la fin, tu n'as pas la bonne : reviens décocher la case, et supprime le
`&channel_binding=require` s'il persiste.

> Cette chaîne contient un mot de passe. Elle ne va que dans ton terminal —
> jamais dans un chat, une capture d'écran ou un fichier du projet.

---

## 2. Installer les tables

Le plus simple : dans Neon, ouvre **SQL Editor**. Ouvre le fichier
`db/schema.sql` du projet, copie tout son contenu, colle-le dans l'éditeur,
exécute.

Va ensuite dans l'onglet **Tables**. Tu dois voir six tables :

```
customers   orders   order_items   payments   order_events   couriers
```

Si tu les vois, l'étape est finie.

---

## 3. Relier la base à Cloudflare

Crée un compte sur [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up),
puis dans le dossier du projet :

```powershell
npm install
npx wrangler login
```

Un navigateur s'ouvre, tu autorises, tu reviens au terminal.

Ensuite — **tout sur une seule ligne**, PowerShell n'aime pas les commandes
coupées :

```powershell
npx wrangler hyperdrive create yems-db --connection-string="COLLE_TA_CHAINE_NEON"
```

La réponse contient un identifiant :

```
id = "a1b2c3d4e5f6..."
```

**Ouvre `wrangler.toml`** et remplace `REMPLACER_PAR_L_ID_HYPERDRIVE` par cet
identifiant.

> À quoi sert Hyperdrive : il garde des connexions ouvertes vers Neon côté
> Cloudflare. Sans lui, chaque commande passée sur le site rouvrirait une
> connexion jusqu'à Francfort.

---

## 4. Poser les réglages

**Le mot de passe de l'administration.** Génère-le :

```powershell
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Copie le résultat, note-le quelque part de sûr, puis :

```powershell
npx wrangler secret put ADMIN_TOKEN
```

Colle la valeur quand c'est demandé.

**Le numéro WhatsApp de l'atelier.** Ouvre `wrangler.toml` et corrige la
ligne `OWNER_WHATSAPP` avec le vrai numéro, format international sans le `+` :

```toml
[vars]
PAYMENT_MODE = "offline"
KKIAPAY_SANDBOX = "true"
OWNER_WHATSAPP = "22997000000"     ← le numéro de ton client
```

Ne touche pas à `PAYMENT_MODE` : `offline` est le mode qui permet de vendre
sans compte marchand.

---

## 5. Déployer et vérifier

```powershell
npm run deploy
```

### Note bien ton adresse

Wrangler termine par quelques lignes dont celle-ci :

```
Deployed yems triggers
  https://yems.a1b2c3.workers.dev      ← LA TIENNE sera différente
```

**Sélectionne cette adresse à la souris et fais `Ctrl + C`.** Ne la retape pas :
`*.workers.dev` accepte n'importe quel sous-domaine, donc une lettre oubliée ne
donne pas « host introuvable » — elle donne une **page d'erreur Cloudflare en
HTML**, qu'on prend facilement pour un bug du serveur. C'est le piège numéro un.

Si tu perds l'adresse : [dash.cloudflare.com](https://dash.cloudflare.com) →
**Compute (Workers)** → clique sur `yems`, elle est affichée en haut.

**Ouvre-la dans ton navigateur.** Tu dois voir la homepage avec la vidéo.
Clique sur *Chaussures*, puis sur un produit.

### D'abord, le Worker répond-il ?

Le `-i` affiche les en-têtes : c'est eux qui disent qui a répondu.

```powershell
curl.exe -i https://COLLE_TON_ADRESSE/api/health
```

Réponse attendue — du JSON, pas du HTML :

```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{"ok":true,"worker":"yems","payment_mode":"offline","configured":{"hyperdrive":true,"admin_token":true,...}}
```

Si tu reçois du HTML, lis d'abord les en-têtes :

| En-têtes | Ce qui se passe |
|---|---|
| `content-type: text/html` + page Cloudflare générique | **l'adresse est fausse** — recopie-la depuis `npm run deploy` |
| `content-type: text/html` + ta page 404 à toi | le Worker n'est pas atteint : vérifie `run_worker_first = ["/api/*"]` et l'absence de `not_found_handling`, puis redéploie |

Cette route ne demande aucun mot de passe et ne touche pas à la base. Elle dit
seulement quels réglages sont posés — jamais leur valeur.

### Le test qui compte

Dans la commande ci-dessous, remplace **les deux parties en majuscules** par
tes vraies valeurs — l'adresse que tu viens de copier, et ton jeton admin :

```powershell
curl.exe https://TON-ADRESSE.workers.dev/api/admin/orders -H "Authorization: Bearer TON-JETON"
```

Concrètement, ça donnera quelque chose comme :

```powershell
curl.exe https://yems.a1b2c3.workers.dev/api/admin/orders -H "Authorization: Bearer 4f8a2c...9e1b"
```

Réponse attendue :

```json
{"ok":true,"count":0,"orders":[]}
```

Si tu vois ça, **tout fonctionne** : le site est en ligne, le serveur répond,
la base est connectée.

> Sous PowerShell, écris bien `curl.exe` et non `curl` : `curl` seul y est un
> alias vers une autre commande qui ne comprend pas ces options.

---

## 6. Passer une vraie commande

Sur le site : ajoute une paire au panier, passe commande, choisis
**« à la livraison »**, valide.

Tu arrives sur une page de confirmation avec une référence du type
`YMS-1108-0001`.

Relance ensuite la commande `curl.exe` de l'étape 5. La commande doit
apparaître, avec :

- `"status":"to_confirm"` — elle attend que l'atelier rappelle
- `"whatsapp_link":"https://wa.me/..."` — **clique ce lien**

WhatsApp s'ouvre avec le détail complet de la commande et la consigne
d'encaissement, prêt à envoyer. C'est comme ça que l'atelier travaillera
chaque jour.

---

## Au quotidien

Après chaque modification du site ou du catalogue :

```powershell
npm run deploy
```

Trente secondes. Si le site semble ne pas avoir changé, fais `Ctrl + Maj + R`
dans le navigateur.

---

## Si ça coince

| Message | Ce qui se passe | Quoi faire |
|---|---|---|
| `Missing expression after unary operator '--'` | commande coupée sur deux lignes | tout remettre sur une seule ligne |
| `no such binding HYPERDRIVE` | l'identifiant n'a pas été reporté | revoir la fin de l'étape 3 |
| `aucune chaîne de connexion` | idem | idem |
| erreur SSL au premier test | chaîne Neon « pooled » | reprendre la chaîne **directe**, sans `-pooler` |
| `accès refusé` avec le bon jeton | `ADMIN_TOKEN` mal enregistré | refaire `npx wrangler secret put ADMIN_TOKEN` |
| `Could not resolve host: TON-ADRESSE...` | le texte à remplacer a été copié tel quel | mettre ta vraie adresse, celle affichée par `npm run deploy` |
| `Assertion failed: !(handle->flags…)` | bug Node sur Windows | sans conséquence, à ignorer |
| le site affiche du code source | `.assetsignore` déplacé | il doit rester à la racine du projet |
| `you should use a local Postgres connection string` | c'est `npm run dev`, pas le déploiement | utiliser `npm run deploy` |
| `python3 : terme non reconnu` | Python s'appelle `python` sur Windows | déjà géré par le script npm, relancer `npm run deploy` |
| `/api/...` renvoie du HTML au lieu du JSON | le Worker n'est pas atteint | tester `/api/health` ; vérifier `run_worker_first = ["/api/*"]` et l'absence de `not_found_handling` dans `wrangler.toml`, puis redéployer |
| `Expected "assets.run_worker_first" to be of type boolean` | Wrangler 3 installé | `npm install wrangler@4 --save-dev` |
| `CONNECT_TIMEOUT …hyperdrive.local:5432` | le driver réclame du TLS à Hyperdrive, qui n'en parle pas sur ce tronçon | vérifier que `api/_lib/db.js` passe `ssl: false` quand `env.HYPERDRIVE` existe |
| `relation "orders" does not exist` | le `db/schema.sql` n'a jamais été exécuté | refaire l'étape 2 |
| `column o.pay_mode does not exist` | schéma installé avant le mode hors ligne | exécuter `db/migration-001-paiement-hors-ligne.sql` dans Neon |

Pour voir ce qui se passe côté serveur en direct :

```powershell
npx wrangler tail
```

---

## Le nom de domaine

Quand tu voudras remplacer l'adresse `workers.dev` :

1. Achète le domaine.
2. Dans Cloudflare, **Add a site**, puis suis les instructions pour faire
   pointer les serveurs de noms du registrar vers Cloudflare.
3. Ajoute dans `wrangler.toml` :

```toml
routes = [
  { pattern = "yems.bj", custom_domain = true },
  { pattern = "www.yems.bj", custom_domain = true }
]
```

4. `npm run deploy`

Le certificat HTTPS est émis automatiquement.

---

---

# Plus tard : activer le paiement en ligne

**Rien de ce qui suit n'est nécessaire pour vendre.** À faire le jour où le
compte marchand est activé.

## Obtenir un compte

Le dossier est le point dur. Deux pistes :

**FedaPay — compte Travailleur Indépendant.** Demande seulement une **pièce
d'identité** et un **IFU**. Ni RCCM, ni société enregistrée. Limité à 10
transactions par semaine et 300 000 F par transaction — largement suffisant
pour démarrer. Convertible en compte Business ensuite, sans repartir de zéro.
Détail des pièces : [docs.fedapay.com](https://docs.fedapay.com/introduction/fr/compte-fr).

**KkiaPay.** C'est le prestataire déjà intégré dans le code. Renseigne-toi sur
les pièces exactes auprès de leur support.

Dans les deux cas, fais confirmer la liste par le prestataire avant d'engager
des démarches — je ne suis ni juriste ni comptable.

## Une fois le compte activé

Récupère les trois clés dans le tableau de bord du prestataire, menu
**Développeurs**, puis :

```powershell
npx wrangler secret put KKIAPAY_PUBLIC_KEY
npx wrangler secret put KKIAPAY_PRIVATE_KEY
npx wrangler secret put KKIAPAY_SECRET_KEY
```

La clé **publique** descend dans le navigateur — c'est normal, elle ne permet
que d'ouvrir la fenêtre de paiement. Les deux autres ne quittent jamais le
serveur : la privée vérifie les transactions, la secrète authentifie les
notifications du prestataire.

Puis dans `wrangler.toml` :

```toml
PAYMENT_MODE = "online"
```

Et `npm run deploy`.

## Déclarer le webhook

Dans le tableau de bord du prestataire → Développeurs → Webhook :

```
https://TON-ADRESSE/api/webhooks/kkiapay
```

Il sert de filet : si un client paie puis ferme son navigateur avant le retour
sur le site, le serveur ne saurait jamais que le paiement a abouti. Le
prestataire le prévient directement.

## Tester avant d'ouvrir

Garde `KKIAPAY_SANDBOX = "true"` et utilise les
[numéros de test](https://docs.kkiapay.me/v1/compte/kkiapay-sandbox-guide-de-test).

Puis passe à `"false"` et **fais une vraie commande d'un petit montant** avec
ton propre Mobile Money. Sandbox et production n'utilisent pas les mêmes
serveurs : quelque chose peut marcher en test et échouer en réel.

Si tu changes de prestataire, seul `api/_lib/kkiapay.js` est à réécrire —
environ 130 lignes. Le reste du code ignore qui encaisse.

---

## L'écran de l'atelier

Adresse : **`https://TON-ADRESSE/admin.html`**

Ton client y entre le mot de passe généré à l'étape 4, et voit ses commandes.
Il peut filtrer par statut, cliquer pour prévenir le client sur WhatsApp, et
faire avancer une commande (à confirmer → acompte reçu → en atelier → expédiée
→ livrée).

Trois choses à lui dire :

- **La page n'est liée depuis nulle part.** Il faut mettre l'adresse en favori.
  C'est volontaire : aucun visiteur ne doit tomber dessus par hasard.
- **Le mot de passe est oublié à la fermeture de l'onglet.** Un peu pénible,
  mais un mot de passe qui donne les coordonnées de tous les clients n'a rien
  à faire stocké durablement dans un navigateur.
- **La page ne contient aucune donnée en elle-même.** Tout arrive du serveur
  après vérification du mot de passe. Même téléchargée, elle est vide.

---

## Ce qui reste à faire sur le site

- [ ] Remplacer les photos portant des marques de fabricants tiers
- [ ] Prix définitifs, témoignages réels, numéro WhatsApp de l'atelier
- [ ] Statut VIP et affectation d'un livreur — les champs existent, pas d'interface
