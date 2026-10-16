# Prompt pour Claude Code — refonte Yem’s

Tu travailles dans le dépôt Yem’s, à la racine :

`C:\Users\abouc\OneDrive\Documents\GitHub\Site_ecommerce_Yem's`

Commence par lire `AGENTS.md` et `README.md`, puis inspecte le fonctionnement actuel du site avant de modifier quoi que ce soit. Implémente la refonte dans le vrai site, en respectant le générateur et les conventions déjà en place. Ne te contente pas de retoucher la maquette.

## Direction attendue

Inspire-toi de la template visuelle fournie : grand hero éditorial avec navigation intégrée, typographie ample derrière le mannequin, bandeau de réassurance, sélection de produits lisible, bloc de marque sombre et pied de page structuré. Adapte cette composition à Yem’s : souliers, atelier de Cotonou, palette espresso/ivoire/laiton et ton premium. Ne reprends pas les catégories ou produits de mode de la référence.

La page d’accueil doit montrer le hero puis mener rapidement aux produits. Déplace les explications détaillées sur l’atelier, la sélection et les engagements vers une vraie page **About us**. Conserve les informations produit, prix, origines et garanties exactes de la source de données ; n’invente aucune promesse commerciale.

Références visuelles dans le dépôt :

- Template : `.codex-remote-attachments/01a145ca-d64b-7151-bb42-57aa543ddf6e/006915fe-8313-451d-bdd6-051939fc690a/1-1000329353.jpg`
- Avatar : `.codex-remote-attachments/01a145ca-d64b-7151-bb42-57aa543ddf6e/006915fe-8313-451d-bdd6-051939fc690a/4-1000321412.jpg`
- Maquette actuelle : `marque/proposition-identite-2026/accueil-produits.html`, `marque/proposition-identite-2026/about-us.html` et `marque/proposition-identite-2026/site-style.css`
- Visuel hero validé : `assets/img/hero-yems-avatar-v7.png`
- Visuel atelier de la maquette : `assets/img/atelier-yems-couture-v1.png`
- Propositions de logo : `marque/proposition-identite-2026/logo-yems-v2-principal.svg`, `logo-yems-v2-principal-inverse.svg`, `logo-yems-v2-monogramme.svg` et `logo-yems-v2-sceau.svg`

Les pages de `marque/proposition-identite-2026/` sont des références de conception. La source de vérité du site en production est `templates/`, `data/` et `assets/`.

## Fichiers de production à examiner

- `templates/pages/index.html` — source de la page d’accueil.
- `templates/base.html` — squelette commun ; il charge les styles et scripts partagés.
- `templates/partials/header.html` et `templates/partials/footer.html` — navigation et pied de page.
- `templates/partials/svg-defs.html` — symboles SVG et logo actuellement utilisés.
- `tools/build.py` — génère les pages HTML ; ajoute proprement la route About us au générateur.
- `data/products.json` — source de vérité du catalogue et des catégories.
- `assets/css/base.css`, `components.css`, `home.css`, `shop.css` et `motion.css` — tokens, composants, accueil, boutique et animations.
- `assets/js/main.js` et `assets/js/motion.js` — interactions et animations déjà présentes.
- `assets/img/` et `tools/process_images.py` — visuels et pipeline de traitement d’images.

Le dépôt produit des pages HTML générées. **Ne modifie pas directement `index.html`, les pages de catégories ou `produit/*.html`** : ces fichiers sont réécrits au build. Modifie leurs sources et lance le générateur. La page About us n’existe pas encore dans `templates/pages/` : crée sa source puis enregistre sa génération dans `tools/build.py`, avec les bons liens dans la navigation et le footer.

## Responsive et animations

- Ajuste les proportions pour ordinateur, tablette et téléphone : hero, navigation, grille produit, images et blocs éditoriaux doivent se réorganiser sans débordement.
- Ajoute des animations sobres et cohérentes avec le luxe éditorial : apparition du hero, révélations progressives des cartes produit et transitions de survol discrètes.
- Examine d’abord `assets/css/motion.css` et `assets/js/motion.js` : réutilise les mécanismes existants (`data-reveal`, `data-lines`, `data-shot`) et évite les doublons. Respecte `prefers-reduced-motion`.
- N’ajoute pas de bibliothèque d’animation lourde. Privilégie `transform` et `opacity`, évite les lectures/écritures répétées au scroll et ne retarde ni l’affichage du hero ni l’accès aux produits.
- Garde les interactions accessibles au clavier et les liens/contrôles suffisamment grands sur téléphone.

## Performance et ménage des fichiers

- Le site commence à ralentir : mesure et identifie les causes avant d’ajouter des effets ou médias. Réutilise les variantes WebP/JPEG responsives et le pipeline existant ; ne sers pas un PNG de plusieurs mégaoctets quand une variante optimisée suffit.
- Donne la priorité au visuel hero réellement affiché, réserve les dimensions des images pour éviter les sauts de mise en page et charge paresseusement les images hors écran.
- Après l’implémentation, inventorie les images et fichiers devenus inutiles. Vérifie leurs références dans les templates, HTML générés, CSS, JS, données et scripts de traitement avant toute suppression. Supprime seulement les fichiers dont l’absence de référence est confirmée ; conserve les images sources, `.codex-remote-attachments/`, `.retirees/` et les fichiers encore utilisés par la maquette ou les outils.
- Dans le compte rendu, indique les fichiers modifiés, les fichiers réellement supprimés et pourquoi, ainsi que les optimisations effectuées. Ne déploie rien.

## Vérifications et livrables

Construis le site avec `npm run build`, puis vérifie les pages générées, les liens About us, les images utilisées et l’absence d’erreur de build. Vérifie visuellement au minimum ordinateur, tablette et téléphone si un navigateur de prévisualisation est disponible. Termine par un résumé clair des changements et des éventuels points qui nécessitent une validation humaine.
