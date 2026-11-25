---
name: Yem's
description: Maison de souliers pour hommes, Cotonou. Un atelier qui coud à la main, et des pièces choisies par l'atelier.
colors:
  ivoire: "#F6F1E8"
  ivoire-haut: "#FBF8F2"
  sable: "#ECE4D6"
  sable-fonce: "#DED3C1"
  encre: "#14100D"
  encre-survol: "#3A2E26"
  cognac: "#8C5A3C"
  cognac-fonce: "#6F4329"
  texte-doux: "#4A3F36"
  texte-discret: "#5E5248"
  sombre-surface: "#1F1915"
  sombre-texte: "#F1EADF"
  cognac-sur-encre: "#D6B48E"
  statut-disponible: "#2F5A35"
  statut-en-route: "#7A5512"
  statut-indisponible: "#8E3A2E"
typography:
  display:
    fontFamily: "Prata, Georgia, Times New Roman, serif"
    fontSize: "3.5rem"
    fontWeight: 400
    lineHeight: 1.04
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Prata, Georgia, Times New Roman, serif"
    fontSize: "2.5rem"
    fontWeight: 400
    lineHeight: 1.12
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Prata, Georgia, Times New Roman, serif"
    fontSize: "1.1875rem"
    fontWeight: 400
    lineHeight: 1.3
  price:
    fontFamily: "Prata, Georgia, Times New Roman, serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    fontFeature: "tnum"
  body:
    fontFamily: "Hanken Grotesk, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Hanken Grotesk, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.4
  origine:
    fontFamily: "Hanken Grotesk, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "0.01em"
  marque:
    fontFamily: "Marcellus, Georgia, serif"
    fontSize: "1.375rem"
    fontWeight: 400
    letterSpacing: "0.08em"
rounded:
  none: "0px"
  sm: "2px"
spacing:
  sp-1: "0.25rem"
  sp-2: "0.5rem"
  sp-3: "0.75rem"
  sp-4: "1rem"
  sp-5: "1.5rem"
  sp-6: "2rem"
  sp-7: "3rem"
  sp-8: "4rem"
  section-y-phone: "3.5rem"
  section-y-desktop: "6rem"
components:
  button-primary:
    backgroundColor: "{colors.encre}"
    textColor: "{colors.ivoire}"
    rounded: "{rounded.none}"
    padding: "0.9rem 1.75rem"
    height: "52px"
    typography: "{typography.body}"
  button-primary-hover:
    backgroundColor: "{colors.encre-survol}"
    textColor: "{colors.ivoire}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.encre}"
    rounded: "{rounded.none}"
    padding: "0.9rem 1.75rem"
    height: "52px"
  button-ghost-hover:
    backgroundColor: "{colors.encre}"
    textColor: "{colors.ivoire}"
  button-small:
    rounded: "{rounded.none}"
    padding: "0.6rem 1.1rem"
    height: "44px"
  button-on-dark:
    backgroundColor: "{colors.ivoire}"
    textColor: "{colors.encre}"
    rounded: "{rounded.none}"
  text-link:
    textColor: "{colors.encre}"
    height: "44px"
  text-link-hover:
    textColor: "{colors.cognac}"
  product-card:
    backgroundColor: "transparent"
    rounded: "{rounded.none}"
    padding: "0"
  product-shot:
    backgroundColor: "{colors.sable}"
    rounded: "{rounded.none}"
  badge:
    backgroundColor: "{colors.ivoire}"
    textColor: "{colors.encre}"
    rounded: "{rounded.none}"
    padding: "0.3rem 0.55rem"
  size-chip:
    backgroundColor: "transparent"
    textColor: "{colors.encre}"
    rounded: "{rounded.none}"
    height: "48px"
    width: "52px"
  size-chip-active:
    backgroundColor: "{colors.encre}"
    textColor: "{colors.ivoire}"
  panel-sable:
    backgroundColor: "{colors.sable}"
    textColor: "{colors.texte-doux}"
    rounded: "{rounded.none}"
    padding: "1.5rem"
  header:
    backgroundColor: "{colors.ivoire}"
    textColor: "{colors.encre}"
    height: "60px"
  footer:
    backgroundColor: "{colors.encre}"
    textColor: "{colors.sombre-texte}"
    rounded: "{rounded.none}"
---

# Design System: Yem's

## Overview

**Creative North Star: "La maison de souliers, jouée droit"**

Le registre des grandes maisons de souliers (Corthay, Crockett & Jones, Septième Largeur), exécuté sans détour : un fond ivoire, une encre espresso, une seule couleur d'accent, des images à angle droit, des boutons pleins et rectangulaires, des filets fins entre les sections. L'image et la pièce mènent ; la ligne d'origine se lit au-dessus de chaque prix ; rien sur la page ne leur fait concurrence. La page est un aplat : pas de voile, pas de dégradé, pas d'objet qui flotte.

La densité est celle d'un catalogue de maison : peu de mots, des grilles plates de vignettes, des faits courts posés en rangées à filets plutôt qu'en cartes. Le titre d'ouverture est centré sous l'image ; tout le reste se compose à gauche. Le site est pensé d'abord pour un téléphone en plein jour, ouvert depuis un lien WhatsApp.

Ce que le système refuse, et que la concurrence régionale porte : les restes de gabarit, le chrome décoratif, les prix barrés, les preuves inventées, les surtitres au-dessus des titres.

**Key Characteristics:**
- Fond ivoire, encre espresso, cognac pour l'origine, les liens et le focus ; rien d'autre ne colore la page.
- Prata (serif à déliés tenus) pour titres, noms et prix ; Hanken Grotesk pour le texte et les contrôles.
- Angles droits partout ; le rond ne survit que là où il dit quelque chose (compteur du panier, pastille de teinte, point de statut).
- Profondeur par filets et fonds sable, presque jamais par ombre.
- Mouvement sobre : une courbe, 180 à 480 ms, rien sur l'image principale ni sur le prix.

## Colors

Une palette chaude et retenue : quatre valeurs portent tout le site (ivoire, sable, encre, cognac), les autres en sont des nuances fonctionnelles.

### Primary
- **Cognac** (#8C5A3C, 5,1:1 sur ivoire) : l'accent unique. La ligne d'origine (« Choisi par l'atelier », « Cousu à Cotonou ») sur les vignettes et sous le nom des fiches, le survol des liens, l'anneau de focus, la sélection de texte, le caret des champs, les mots forts des lignes de rayon.
- **Cognac foncé** (#6F4329) : l'accent appuyé (ancien `--accent-strong`), rarement visible.

### Neutral
- **Ivoire** (#F6F1E8) : le fond de lecture de toutes les pages, de l'en-tête, du menu téléphone et de la barre d'achat.
- **Ivoire haut** (#FBF8F2) : champs de saisie et panneaux qui avancent d'un cran.
- **Sable** (#ECE4D6) : le fond des images produit et des panneaux calmes (« Payer et recevoir » de la fiche, origine développée).
- **Sable foncé** (#DED3C1) : réserve de la gamme sable.
- **Encre espresso** (#14100D, 17,6:1 sur ivoire) : le texte, les boutons pleins, le pied de page.
- **Encre de survol** (#3A2E26) : le bouton plein au survol ; noir pur (#000) à l'appui.
- **Texte doux** (#4A3F36, 9,4:1) : chapeaux, descriptions, définitions des faits.
- **Texte discret** (#5E5248, 7,0:1) : notes, aides de pointure, libellés de caractéristiques.
- Les filets sont l'encre à 12 % (`rgba(20,16,13,.12)`), 28 % pour un filet appuyé, 50 % pour le contour des pointures et teintes (environ 3,3:1).

### Sur l'encre (pied de page)
- **Texte sur encre** (#F1EADF), atténué à 74 % et 66 % pour le secondaire, filets à 16 %.
- **Cognac éclairci** (#D6B48E, 8,9:1 sur encre) : l'accent quand le fond est sombre.

### Statuts
- **Disponible** (#2F5A35), **En route** (#7A5512), **Indisponible** (#8E3A2E) : couleur du texte de la pastille de disponibilité, jamais un fond.

### Named Rules
**The One Accent Rule.** Le cognac est la seule couleur de la page en dehors de l'ivoire, du sable et de l'encre. Il marque l'origine, les liens et le focus, et rien d'autre ; une seconde couleur d'accent (le laiton de l'ancien registre, un vert de promotion) est une dérive.

**The Origin Above Price Rule.** Sur chaque vignette et chaque fiche, la ligne d'origine, en cognac, se lit avant le prix. Elle n'est jamais grisée.

**The Flat Ground Rule.** Le fond est un aplat ivoire. Les voiles, dégradés d'ambiance et grains de l'ancien registre sont éteints (`--voile-*: none`) et ne reviennent pas.

## Typography

**Display Font:** Prata (repli Georgia, Times New Roman)
**Body Font:** Hanken Grotesk 400 / 500 / 600 (repli pile système)
**Marque:** Marcellus, pour le seul mot-symbole « YEM'S » (le logo existant de la maison)

**Character:** Prata donne la tenue d'une maison : ses déliés tiennent au soleil sur un téléphone, sur l'ivoire comme sur l'encre, et ses chiffres lisent « 103 000 F » proprement. Hanken Grotesk, plus ferme que Jost à 14 px, porte le texte, les pointures et les boutons sans se faire remarquer.

### Hierarchy
- **Display** (Prata 400 ; téléphone clamp(2.125rem, 9.2vw, 2.5rem), 1.06 ; grand écran 3.5rem, 1.04 ; -0.015em) : le seul titre d'ouverture de l'accueil, centré sous l'image. Les titres de rayon suivent la même voix à gauche (1.875rem, puis 3rem), le nom de produit sur la fiche aussi (2rem, puis 2.75rem).
- **Headline** (Prata 400 ; 1.75rem téléphone, 2.5rem grand écran ; 1.12) : titres de section, alignés à gauche.
- **Title** (Prata 400 ; 1.1875rem ; 1.3) : intitulés des faits (« Payer et recevoir », méthode), questions des blocs dépliables, titres du pied de page (1.0625rem). Les portes de l'accueil passent à 1.375rem.
- **Nom et prix de vignette** (Prata 400 ; 1.0625rem, puis 1.1875rem dès 900 px ; chiffres tabulaires) ; prix de fiche 1.75rem, suivi de « francs CFA, prix indicatif » en texte discret 0.875rem.
- **Body** (Hanken 400 ; 1rem au téléphone, 1.0625rem dès 900 px ; 1.5 à 1.6 dans les blocs de la refonte) : chapeaux et paragraphes, mesure tenue entre 34 et 52ch.
- **Label** (Hanken 600 ; 0.9375rem ; sans capitales ni espacement) : libellés des sélecteurs (« Couleur », « Pointure »), intitulés des faits courts.
- **Origine** (Hanken 500 ; 0.875rem ; 0.01em ; cognac) : la ligne d'origine.
- **Bouton** (Hanken 500 ; 1rem ; 0.02em).

### Named Rules
**The No Eyebrow Rule.** Aucun surtitre, aucune étiquette au-dessus d'un titre. Le titre porte son propre poids ; là où un ancien gabarit en garde un, il est masqué (`.eyebrow { display: none }`).

**The Plain Serif Rule.** Prata n'a pas d'italique et n'en reçoit pas : pas de mot en italique d'accent, pas de mot surligné dans un titre. Pas de capitales espacées pour les libellés.

## Layout

Conteneur jusqu'à 1200 px, 1440 px dès 1200 px de large ; gouttière `clamp(1.25rem, 4vw, 4rem)`, puis `clamp(2.5rem, 4vw, 4.5rem)`. Les points de rupture effectifs sont 560, 620, 760, 900 et 1180 px ; 900 px est la bascule téléphone / grand écran pour la typographie, l'en-tête (60 puis 68 px) et l'espacement vertical des sections (3.5rem puis 6rem).

L'échelle d'espacement va de 0.25rem à 4rem (sp-1 à sp-8). Les groupes serrés utilisent sp-2 à sp-4, la séparation entre blocs sp-6 à sp-8.

- **Ouverture de l'accueil** : l'image pleine largeur, à angle droit, environ 60svh au téléphone (360 à 520 px), une bande de 44vh au plus sur grand écran, cadrée sur les souliers ; dessous, titre, une ligne et un bouton centrés. Sur un écran court (navigateur intégré, 390 × 664), l'image se resserre à 44svh pour garder le bouton dans le premier écran.
- **Grilles de vignettes** : deux colonnes au téléphone (écarts sp-6 / sp-3), trois dès 760 px, quatre dès 1180 px (accueil : quatre dès 900 px). Image au ratio 4/5.
- **Faits à filets** : titre de bloc sur 4/12, liste sur 8/12 en deux colonnes sur grand écran ; une seule colonne au téléphone.
- **Image et texte** (le geste de l'atelier, l'atelier en boutique) : 7/12 et 5/12, image 3/2.
- **Fiche** : galerie à gauche, collante sur grand écran (couche héritée `shop.css`), colonne d'achat à droite ; au téléphone, une barre d'achat d'une ligne monte une fois le vrai bouton sorti de l'écran.

### Named Rules
**The Gutter Rule.** Les filets entre sections sont tirés dans la largeur du contenu, pas bord à bord : la page garde ses marges.

**The Thumb Rule.** Tout lien ou contrôle fait au moins 44 px de haut (boutons 52 px, pointures 48 px, liens texte et fil d'Ariane 44 px, entrées du menu téléphone 56 px).

## Elevation & Depth

Le système est plat. La profondeur vient des filets (1 px d'encre à 12 %) et des fonds (sable sous les images et les panneaux calmes), pas d'objets qui flottent. Les vignettes, les cartes, les blocs dépliables et les champs n'ont aucune ombre. L'en-tête est une barre ivoire pleine, sans flou, qui gagne un filet dessous une fois la page défilée.

### Shadow Vocabulary
- **Filet de surface** (`box-shadow: 0 1px 0 rgba(20,16,13,.06)`) : le jeton `--shadow`, un trait plutôt qu'une ombre.
- **Ombre portée basse** (`box-shadow: 0 18px 40px -24px rgba(20,16,13,.28)`) : `--shadow-lg`, réservée aux éléments qui flottent réellement au-dessus de la page (notification, panneaux du panier et du configurateur).

### Named Rules
**The Rule Not Shadow Rule.** Une séparation se dessine par un filet ou un changement de fond, jamais par une ombre. Une ombre n'existe que pour un élément qui couvre la page.

## Shapes

Angle droit partout : boutons, images, vignettes, pastilles, champs, menu, pied de page, focus (`radius: 0`). Un rayon de 2 px reste disponible et quasi inutilisé. Le rond ne survit que là où sa forme dit quelque chose : le compteur du panier (encre, 17 px), la pastille de teinte du nuancier, le point de statut de 6 px. Les filets sont pleins, jamais pointillés (la couture laiton de l'ancien registre est remplacée par un trait). Les images sont recadrées en `object-fit: cover` dans des cadres fixes (4/5 pour les pièces, 3/2 pour les scènes).

## Components

### Buttons
Pleins, rectangulaires, sans aimant ni élévation.
- **Shape:** angle droit (0px), hauteur minimale 52 px.
- **Primary:** fond encre, texte ivoire, filet encre de 1 px, rembourrage 0.9rem × 1.75rem.
- **Hover / Focus:** fond encre de survol en 240 ms ; appui noir en 120 ms ; focus par l'anneau cognac de 2 px décalé de 3 px. Aucun déplacement.
- **Ghost:** transparent, texte et filet encre ; au survol il se remplit d'encre. Sert au second chemin d'achat (« Commander sur WhatsApp ») et au bouton de l'en-tête.
- **Small:** 44 px (40 px dans l'en-tête), 0.6rem × 1.1rem, 0.9375rem.
- **Sur l'encre** (pied de page) : le bouton s'inverse, fond ivoire et texte encre ; le ghost prend le texte ivoire et un filet à 16 %.

### Text link
Le lien de la maison : encre 500, souligné fin (1 px, décalé de 0.22em, encre à 35 %), qui passe au cognac au survol avec son soulignement. Hauteur minimale 44 px, une flèche SVG de 14 px à la suite.

### Product card (signature)
La vignette plate : l'image sur le sable, à angle droit, ratio 4/5 ; dessous, sans cadre ni ombre, le nom en Prata, une ligne de caractéristiques en texte doux 0.875rem, l'origine en cognac, puis le prix en Prata à chiffres tabulaires, empilés à gauche. Toute la vignette est un seul lien : le nom porte le lien et son pseudo-élément couvre la carte ; l'image a son propre lien, retiré du clavier. Au pointeur fin, la photo grandit de 2 % en 480 ms et le nom se souligne. La pastille « Disponible » se tait sur une vignette ; « En route » et « Indisponible » restent, posées sur l'image.

### Badges
Une étiquette ivoire à 94 %, angle droit, 0.75rem, couleur du texte selon le statut, point plein de 6 px sans halo. Sur la fiche, la disponibilité devient une ligne de texte avec son point (0.9375rem).

### Inputs / Fields
- **Champs :** angle droit, fond ivoire haut, caret cognac.
- **Pointures et teintes :** carrés à filet encre à 50 %, 48 px de haut (pointure 52 px de large). Pointure choisie : pleine d'encre, texte ivoire. Teinte choisie : filet encre doublé à l'intérieur.

### Navigation
- **En-tête :** barre ivoire pleine collée en haut, 60 px puis 68 px, mot-symbole Marcellus, liens en texte doux 0.9375rem qui passent à l'encre au survol et à la page courante (trait cognac dessous), icônes de 20 px.
- **Téléphone :** menu burger ; une page ivoire sous la barre, entrées en Prata 1.5rem de 56 px séparées par des filets, un bouton plein en bas.
- **Fil d'Ariane :** 0.875rem, texte doux, cognac au survol, page courante à l'encre.

### Panneau sable
« Payer et recevoir » sur la fiche, placé juste sous les boutons d'achat, et l'origine développée : un aplat sable sans bordure ni barre latérale, rembourrage 1.5rem, titre Prata, faits en rangées à filets légers (encre à 10 %), mots forts à l'encre.

### Faits à filets
Le motif répété de l'accueil, de la boutique et de « Ce qui se prépare » : une liste de définitions, chaque fait séparé par un filet, intitulé en Prata 1.1875rem ou en Hanken 600, définition en texte doux. Il remplace les cartes à icône.

### Blocs dépliables
Des rangées à filets, sans fond ni ombre ni rayon ; question en Prata 1.1875rem, chevron encre.

### Footer
Un aplat d'encre bord à bord, titres de colonnes en Prata 1.0625rem, liens qui se soulignent au survol, logos de paiement en bloc 2 × 2. Au téléphone, les deux listes de liens se partagent la largeur.

### Motion
Une courbe (`cubic-bezier(.2,.7,.2,1)`), 240 ms pour les états, 480 ms pour les entrées. Les images apparaissent une fois par un fondu qui monte de 10 px ; les titres montent une fois ligne par ligne (70 ms d'écart) ; au toucher, un état pressé de 120 ms. Tout s'éteint sous `prefers-reduced-motion`, et le contenu reste visible sans JavaScript (`.js [data-reveal]`).

## Do's and Don'ts

### Do:
- **Do** poser chaque pièce sur le sable (#ECE4D6), à angle droit, au ratio 4/5 dans les grilles.
- **Do** écrire l'origine en cognac au-dessus du prix, sur chaque vignette et chaque fiche.
- **Do** séparer les sections par un filet de 1 px d'encre à 12 %, tiré dans la gouttière.
- **Do** donner une seule action pleine (encre) par bloc ; le second chemin est un ghost ou un lien texte.
- **Do** poser les faits en rangées à filets plutôt qu'en cartes.
- **Do** garder 44 px minimum pour tout ce qui se touche.
- **Do** composer les titres à gauche, sauf le titre d'ouverture de l'accueil, centré sous l'image.

### Don't:
- **Don't** mettre de surtitre au-dessus d'un titre, ni de numéro de section.
- **Don't** arrondir un bouton, une image, une vignette ou un champ ; le rond est réservé au compteur, à la teinte et au point de statut.
- **Don't** ajouter une seconde couleur d'accent : ni laiton, ni vert promotionnel, ni prix barré.
- **Don't** séparer par une ombre, un voile, un dégradé ou un flou ; la page est un aplat.
- **Don't** animer l'image principale, le prix ou le bloc d'achat ; pas de parallaxe, de compteur animé, de bouton aimanté, de boucle décorative ni de révélation lettre par lettre.
- **Don't** mettre une barre latérale colorée sur un panneau ; un panneau est un aplat sable plein.
- **Don't** remplacer une icône par un caractère Unicode ou un emoji ; les icônes sont des SVG du sprite de la maison.

<!--
État de la construction (relecture round 1, novembre 2026)

Couches chargées sur chaque page, dans l'ordre : base.css, components.css,
home.css, shop.css, motion.css (héritées, toujours chargées), puis maison.css
(les jetons et composants partagés de la refonte, qui redéfinissent les
anciens jetons), puis la feuille de la page : accueil.css, fiche.css ou
boutique.css. Les pages panier, commande, configurateur, légales et admin
chargent en plus checkout.css, configurator.css, legal.css ou admin.css,
non refaites. Les valeurs ci-dessus sont les valeurs effectives.

Ce qui reste des couches héritées et porte encore le rendu : base.css
(échelle d'espacement sp-*, conteneurs, gouttières, interlignes du corps),
components.css (structure de l'en-tête, du pied, des pastilles), shop.css
(grille de la fiche, galerie collante, notification d'ajout au panier),
motion.css et motion.js.

Ouvert, non corrigé à ce round :
- F25 : galerie de la fiche, cadre carré pour l'image principale et bande
  de vignettes à glisser au téléphone.
- F29 : mouvement hérité mort dans motion.js (boutons aimantés, compteurs,
  volet, fil de progression), neutralisé en CSS mais toujours exécuté.
- F30 : erreurs accessibles en ligne pour les sélecteurs de pointure et de
  couleur.
- F32 : retrait du srcset par le Worker (api/_lib/rewrite.js) et données
  structurées Product plus riches ; api/ hors du périmètre de ce passage.
- Questions au propriétaire (.bunshin/review/r1.json) : semelle du
  Mocassin Tokpa noir, matière et semelle des six pièces de la Sélection,
  conditions de l'échange de pointure, délais de livraison, libellé
  « About us », image de partage, recadrage large du portrait, réglage
  html_handling du déploiement, visites de l'atelier.

Dérives relevées, non canonisées : la notification d'ajout au panier
(shop.css) garde la forme pilule, le filet laiton et l'ombre de l'ancien
registre ; le laiton, que le contrat autorisait pour un détail au plus,
n'apparaît dans aucune couche de la refonte et n'est donc pas un jeton.
-->
