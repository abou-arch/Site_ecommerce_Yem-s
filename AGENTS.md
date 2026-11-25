## Imported Claude Cowork project instructions

## Refonte « maison » (novembre 2026) : règles pour les prochaines modifications

- Le site est généré : `python tools/build.py` écrit les HTML de la racine à partir de
  `templates/` et `data/products.json`. Ne jamais modifier un HTML généré.
- Direction validée par le propriétaire : `.impeccable/surfaces/templates-pages-index-html.md`
  (registre « canon » des maisons de souliers). Système de design : `DESIGN.md`.
- Feuilles : `assets/css/maison.css` (jetons et composants partagés, chargée sur toutes les
  pages), `accueil.css` (accueil), `fiche.css` (fiches produit), `boutique.css` (boutique,
  sélection, atelier) ; le configurateur garde `configurator.css`, dont le bloc final
  « Refonte maison » surcharge l'ancien registre sombre. Les feuilles historiques (base, components, home, shop, motion) restent
  chargées avant et sont surchargées : ne pas y ajouter de styles nouveaux.
- Palette : ivoire #F6F1E8, encre #14100D, cognac #8C5A3C (seul accent : origine, liens,
  focus), sable #ECE4D6 (fonds d'image, panneaux calmes). Polices : Prata (titres, noms, prix),
  Hanken Grotesk (texte, contrôles), Marcellus pour le seul mot « YEM'S ».
- Interdits : surtitre au-dessus d'un titre, texte en dégradé, verre décoratif, barre latérale
  sur une boîte, boutons arrondis, ombres dures, numéros de section décoratifs, tiret cadratin
  dans le texte visible, animation sur l'image d'ouverture ou sur un prix.
- Vignette produit : nom (lien qui couvre la carte), ligne de description tirée de la première
  caractéristique, origine, prix. L'origine est toujours au-dessus du prix.
- Ancres du Worker à préserver : `data-prix`, `data-court`, `data-badge`, `data-piece`,
  `data-add-to-cart` + `data-id`. Les prix ne s'écrivent jamais dans un gabarit.
- Les faits (prix, délais, garanties, paiement, essai à la livraison) viennent de
  `data/products.json`, des CGV et de `PRODUCT.md` ; ne rien inventer. Toutes les images sont
  générées par IA et le pied de page le dit.
- Fichiers de travail de la refonte : `.bunshin/` (ignoré par git et par le déploiement).
