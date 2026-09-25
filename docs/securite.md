# Sécurité — ce qui protège le site, ce qui reste à régler

Ce document suit l'audit de septembre 2026. Le code corrige tout ce qu'il peut
corriger seul ; la seconde partie liste les réglages qui se font dans les
tableaux de bord (Cloudflare, KkiaPay) et qu'aucune ligne de code ne remplace.

---

## Ce qui est en place

| Protection | Où | Contre quoi |
|---|---|---|
| Politique CSP : seuls les scripts du site s'exécutent | `_headers`, ligne écrite par `tools/build.py` | un script injecté (nom de produit, champ mal échappé) ne s'exécute pas |
| HSTS, `nosniff`, anti-iframe | `_headers`, et `worker.js` pour l'API | interception en HTTP clair, détournement de clic |
| Montants recalculés côté serveur | `api/_lib/catalog.js` | panier modifié dans la console |
| Pages réécrites par le Worker | `run_worker_first` dans `wrangler.toml` | prix affiché différent du prix facturé |
| Écritures refusées si elles viennent d'un autre site | `requeteEtrangere()` dans `worker.js` | commandes forgées depuis une page tierce |
| Blocage après dix mauvais jetons admin | `gardeAdmin()` dans `worker.js` | devinette du mot de passe de l'atelier |
| Rien n'est dit d'une commande sans preuve de paiement | `verifyPayment()` | relevé des références de toutes les commandes |
| Transaction rattachée à sa commande (`partnerId`) | `settle()` | paiement d'un autre client réutilisé |
| Bac à sable jamais « payé » | `settle()`, message WhatsApp | commandes réglées avec les numéros de test publics |
| Anonymisation complète | `anonymizeOrder()` | données personnelles gardées après la promesse d'effacement |
| Fichiers internes et secrets hors ligne | `.assetsignore`, `.gitignore` | `.dev.vars`, `.env.*`, notes de travail publiés |

### La CSP, en pratique

`npm run deploy` relance `tools/build.py`, qui relève l'empreinte SHA-256 de
chaque `<script>` écrit dans les pages et la reporte dans `_headers`. Deux
conséquences :

- **modifier un script en ligne sans relancer le build le fait bloquer** —
  d'où `npm run deploy`, jamais `wrangler deploy` seul ;
- **un attribut `onclick="…"` ou une adresse `javascript:` arrête le build** :
  passer par `addEventListener` dans un fichier de `assets/js/`.

Si un outil Cloudflare injecte un script (Web Analytics, Rocket Loader), la
console du navigateur affiche « Refused to load… » : ajouter le domaine dans
`ecrire_csp()`, puis relancer le build.

---

## À régler dans les tableaux de bord

### 1. Le jeton admin

Il doit sortir de la commande prévue, et de rien d'autre :

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
npx wrangler secret put ADMIN_TOKEN
```

Si le jeton actuel a été choisi à la main ou fait moins de 32 caractères, le
remplacer. Le blocage après dix essais ralentit une attaque, il ne rend pas
sûr un mot de passe devinable.

### 2. Mettre l'administration derrière Cloudflare Access

Le jeton est la seule barrière devant les coordonnées de tous les clients.
Cloudflare Zero Trust (gratuit jusqu'à 50 utilisateurs) ajoute un code reçu
par e-mail, demandé **avant** que la requête n'atteigne le Worker :

*Zero Trust → Access → Applications → Add an application → Self-hosted*,
domaine `maisonyems.com`, chemins `admin.html` et `api/admin/*`, règle
*Allow* sur les adresses e-mail de l'atelier.

### 3. Limiter le débit à l'entrée

Le limiteur du Worker vit dans la mémoire de chaque instance : il arrête un
script naïf, pas une attaque répartie. Le plan gratuit offre une règle de
limitation (*Security → WAF → Rate limiting rules*, selon la version du
tableau de bord) : chemin commençant par `/api/`, par exemple 30 requêtes par
10 secondes et par IP, action *Block*.

### 4. Avant d'ouvrir le paiement en ligne

- tester d'abord en bac à sable : une commande payée avec un numéro de test
  reste « À confirmer » et l'alerte dit « AUCUN ARGENT REÇU » — c'est voulu ;
- vérifier dans l'admin, sur cette commande de test, qu'aucun « transaction
  rattachée à une autre commande » n'apparaît : si c'était le cas, KkiaPay
  renverrait un `partnerId` différent du numéro de commande, à signaler avant
  d'aller plus loin ;
- passer **ensemble** `PAYMENT_MODE = "online"`, `KKIAPAY_SANDBOX = "false"`
  et les clés de production, puis régénérer en mode online pour que la CSP
  autorise le widget (sous PowerShell : `$env:PAYMENT_MODE="online"; npm run deploy`) ;
- déclarer le webhook (voir `docs/back-end.md`).

### 5. À l'atelier

La référence `YMS-2509-0042` se devine : c'est la date et un compteur. Avant
de changer une adresse de livraison ou un mode de règlement demandé par
message, rappeler le numéro de téléphone enregistré sur la commande.
