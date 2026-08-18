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

## Le nom de domaine : maisonyems.com

Le domaine est acheté. Voici comment le brancher sur le Worker.

### 1. Rattacher le domaine à Cloudflare

Dans le tableau de bord Cloudflare : **Add a site**, saisir `maisonyems.com`,
choisir le plan **Free**. Cloudflare affiche alors deux serveurs de noms, du
type `ana.ns.cloudflare.com` et `bob.ns.cloudflare.com`.

Il faut aller **chez le registrar où tu as acheté le domaine** et remplacer ses
serveurs de noms par ces deux-là. C'est l'étape que tout le monde rate : tant
qu'elle n'est pas faite, tu peux ajouter tous les enregistrements DNS que tu
veux dans Cloudflare, personne ne les lira. Cloudflare n'est pas encore
l'autorité sur ton domaine.

La propagation prend de quelques minutes à 24 h. Cloudflare envoie un e-mail
quand le domaine passe en **Active**. Ne fais rien tant que ce n'est pas le cas.

### 2. Déclarer les routes

Une fois le domaine actif, dans `wrangler.toml` :

```toml
routes = [
  { pattern = "maisonyems.com", custom_domain = true },
  { pattern = "www.maisonyems.com", custom_domain = true }
]
```

Puis `npm run deploy`. Wrangler crée lui-même les enregistrements DNS et
demande le certificat HTTPS. Compter une quinzaine de minutes avant que le
cadenas apparaisse : entre-temps le navigateur affiche un avertissement, c'est
normal et ça se règle tout seul.

### 3. Choisir une seule adresse, et s'y tenir

Le site est généré avec `maisonyems.com` **sans `www`** comme adresse
canonique (`data/products.json` → `site.url`). Il faut donc que
`www.maisonyems.com` redirige vers la version sans `www`, sinon Google voit
deux sites identiques et n'en référence correctement aucun.

Dans Cloudflare : **Rules → Redirect Rules → Create rule**

| Champ | Valeur |
|---|---|
| Nom | `www vers apex` |
| Si | `Hostname` `equals` `www.maisonyems.com` |
| Alors | `Dynamic` → `concat("https://maisonyems.com", http.request.uri.path)` |
| Code | `301` (permanent) |

### 4. Vérifier

```powershell
curl.exe -I https://maisonyems.com/
curl.exe -I https://www.maisonyems.com/      # doit répondre 301
curl.exe    https://maisonyems.com/api/health
curl.exe    https://maisonyems.com/sitemap.xml
```

### L'alerte de commande par e-mail

Aujourd'hui, l'atelier n'est prévenu d'une commande que par WhatsApp. Or l'API
WhatsApp Cloud réclame `WHATSAPP_TOKEN` et `WHATSAPP_PHONE_ID`, qui ne sont pas
posés : le site se rabat sur un lien `wa.me` que personne ne voit tant que la
page d'administration n'est pas ouverte. **Une commande peut donc arriver sans
que tu le saches.**

Cloudflare Email Sending bouche ce trou gratuitement. La documentation est
explicite : l'envoi vers une **adresse de destination vérifiée du compte** est
gratuit sur tous les plans, Email Routing seul suffit. C'est exactement notre
cas, puisque le destinataire, c'est toi.

Écrire au **client** (confirmation de commande) viserait une adresse non
vérifiée et exigerait le plan **Workers Paid à 5 $/mois**. Ce n'est pas branché.

**Marche à suivre, dans cet ordre :**

1. Le domaine doit être `Active` dans Cloudflare.
2. **Email → Email Routing → Destination addresses** : ajouter ton adresse,
   puis cliquer le lien de confirmation reçu. Sans cette vérification, l'envoi
   est refusé.
3. Dans `wrangler.toml`, renseigner `OWNER_EMAIL` et décommenter le bloc
   `[[send_email]]`.
4. `npm run deploy`

Tant que ces étapes ne sont pas faites, rien ne casse : `courriel.js` détecte
l'absence du binding et sort proprement, la commande s'enregistre normalement.
Vérifié en test, avec les deux canaux muets, aucune exception ne remonte.

### Ce qui change ailleurs quand l'adresse change

L'adresse n'est écrite qu'à **un seul endroit** : `data/products.json`, clé
`site.url`. Le générateur en déduit les balises `canonical`, les `og:url`, les
`og:image` et le `sitemap.xml`. Une seule ligne reste à modifier à la main si
le domaine changeait un jour : la ligne `Sitemap:` de `robots.txt`, que le
format oblige à écrire en adresse absolue.

### Pourquoi ça compte plus qu'il n'y paraît

Les `og:image` sont désormais des adresses absolues. C'est ce qui fait qu'un
lien collé dans une conversation WhatsApp affiche une vignette et un titre au
lieu d'une ligne bleue nue. Avec un chemin relatif, WhatsApp, Facebook et
LinkedIn n'affichent rien du tout. Pour une boutique dont la quasi-totalité du
trafic arrivera par un lien partagé, c'est la différence entre un lien qu'on
clique et un lien qu'on ignore.

Ces balises ne peuvent pas fonctionner tant que le site répond sur
`workers.dev` : elles pointent vers `maisonyems.com`. Elles s'activeront
d'elles-mêmes dès que le domaine sera branché.

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

## Avant de déployer : deux ajouts

**1. La migration du catalogue.** Dans Neon → SQL Editor, exécute le contenu de
`db/migration-002-catalogue-editable.sql`. Sans elle, l'onglet Catalogue de
l'écran d'administration affichera une erreur — le reste du site continuera de
fonctionner normalement.

**2. Le bucket pour les photos.** Une seule commande :

```powershell
npx wrangler r2 bucket create yems-photos
```

Gratuit jusqu'à 10 Go, et Cloudflare ne facture pas la bande passante sortante.
Les photos que ton client dépose depuis son écran y vont ; celles du dépôt ne
bougent pas.

---

## L'écran de l'atelier

Adresse : **`https://TON-ADRESSE/admin.html`**

Ton client y entre le mot de passe généré à l'étape 4, et voit ses commandes.
Il peut filtrer par statut, cliquer pour prévenir le client sur WhatsApp, et
faire avancer une commande (à confirmer → acompte reçu → en atelier → expédiée
→ livrée).

### L'onglet Catalogue

Ton client y modifie **le prix, la disponibilité et la phrase de présentation**
de chaque pièce, et y **dépose des photos**. Il peut aussi retirer une pièce de
la vente sans l'effacer : elle disparaît des grilles, mais les anciennes
commandes qui la mentionnent restent lisibles.

Comment ça marche, en une phrase : le site reste entièrement statique, et le
serveur ne réécrit que les quelques valeurs modifiées, au moment où la page
part vers le visiteur. Rien à reconstruire, rien à redéployer, la vitesse ne
change pas.

**Le point important :** le prix affiché et le prix facturé viennent de la même
source. Un prix modifié dans cet écran est immédiatement celui qui sera
encaissé. Il n'y a aucun moment où la boutique afficherait un montant et en
prélèverait un autre.

Laisser un champ vide fait revenir la valeur d'origine du catalogue — pas
besoin de se souvenir de l'ancien prix.

### Le ménage dans les commandes

Sous la liste des commandes, un panneau permet d'**anonymiser** les commandes
terminées avant une date donnée : le nom, le téléphone et l'adresse
disparaissent, la commande et ses montants restent.

C'est volontairement l'anonymisation qui est proposée, et non la suppression.
Effacer une commande livrée effacerait aussi son chiffre d'affaires, et ça se
verrait au bilan de fin d'année. Une commande en cours, elle, ne peut être ni
anonymisée ni supprimée : l'atelier a encore besoin du téléphone pour livrer.

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
