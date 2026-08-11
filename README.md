# Yem's — Site e-commerce

> Différents par les détails.

Maroquinerie premium (souliers, ceintures, portefeuilles, entretien) pour le Bénin et la Côte d'Ivoire.
HTML / CSS / JS pur — aucun framework, aucune étape de build. Ouvrir `index.html` suffit.

---

## Ce qui est livré

| Fichier | Rôle |
|---|---|
| `index.html` | Homepage complète (hero → footer) |
| `assets/css/base.css` | Tokens (couleurs, typo, spacing), reset, motif saddle-stitch, animations |
| `assets/css/components.css` | Boutons, logo, header, footer, badges, cartes produit |
| `assets/css/home.css` | Sections de la homepage |
| `assets/css/motion.css` | Les 5 gestes d'animation |
| `assets/js/main.js` | Header au scroll, menu mobile, révélations, carrousel, compteur panier |
| `assets/js/motion.js` | Couture au scroll, titres ligne par ligne, volets, compteurs, boutons magnétiques |
| `assets/img/` | 7 visuels produits normalisés (JPEG + WebP) |
| `tools/process_images.py` | Script de normalisation des photos — relancer après chaque nouvel envoi |

### Sections de la homepage

1. **Hero** — accroche + visuel produit + 3 chiffres clés
2. **Bandeau défilant** — preuves de fabrication
3. **Récit** — les trois couches de problème, puis les 4 preuves techniques
4. **Collections** — 4 lignes photographiées, avec pastilles de disponibilité
5. **Sur-mesure** — 4 étapes + aperçu du configurateur avec facture
6. **Offres** — achat simple / pack / sur-mesure
7. **Garantie** — carte d'authenticité numérotée + 4 engagements
8. **Questions** — les 4 objections traitées en accordéon
9. **Témoignages** — carrousel (contenu à remplacer)
10. **CTA final** — configurateur + WhatsApp

---

## Direction artistique

**Palette** — espresso `#14100D` → `#4E3F38`, beige `#FBF7F1` → `#C4B195`, brass `#D9B87A` → `#7A5E33`.
Accent cuir patiné `#8C5A3C`.

**Typographie** — Fraunces (titres, axes `SOFT`/`WONK` exploités pour les italiques d'accent) + Inter (texte). Chargées via Google Fonts.

**Fil de sellier** — le motif est décliné en 4 utilitaires réutilisables :

```html
<hr class="stitch">                    <!-- séparateur pointillé -->
<div class="stitch stitch--angled">     <!-- couture en épi -->
<div class="stitch stitch--vertical">   <!-- couture verticale -->
<div class="stitch-frame">              <!-- encadré cousu -->
```

Il apparaît aussi dans le logo (semelle pointillée), le tracé du hero, le cadre du visuel hero, la carte d'authenticité et les séparateurs de la facture.

## Animation

Cinq gestes, pas un de plus. Le principe : peu d'effets, mais des durées longues
(700–1150 ms), une courbe unique (`--ease-out-expo`) et un décalage systématique entre
éléments voisins. Tout est neutralisé sous `prefers-reduced-motion`.

| Geste | Déclencheur | Où |
|---|---|---|
| **Le fil qui se coud** | position au scroll | 3 séparateurs `.seam` entre les sections |
| **Titres ligne par ligne** | entrée dans l'écran | 7 titres marqués `data-lines` |
| **Photos en volet** | entrée dans l'écran | 6 visuels marqués `data-shot` |
| **Compteurs** | entrée dans l'écran | chiffres du hero, `data-count` |
| **Boutons magnétiques** | curseur | tous les `.btn`, pointeur précis uniquement |

Le geste signature est la couture : un tracé SVG révélé par un masque dont le
`stroke-dashoffset` suit le scroll (`--seam` va de 1 à 0). Pour en ajouter une, copier
un bloc `.seam` et changer l'`id` du masque — il doit rester unique dans la page.

Pour ajouter un titre animé, il suffit de mettre `data-lines` sur un élément qui
contient des `<br>` : le JS découpe et enveloppe les lignes tout seul, le balisage
interne (italiques, accents) est conservé.

**Pastilles de disponibilité** (code couleur du brief) :

```html
<span class="badge badge--green"><span class="badge__dot"></span>Au Bénin</span>
<span class="badge badge--amber"><span class="badge__dot"></span>En route</span>
<span class="badge badge--red"><span class="badge__dot"></span>Indisponible</span>
```

---

## Photos produits

Les 7 photos envoyées ont été normalisées par `tools/process_images.py` :
détourage du fond d'origine, recomposition sur le dégradé beige de la charte,
reconstruction de l'ombre portée en multiplication (au lieu d'un aplat gris),
export JPEG + WebP (~25 Ko en WebP par visuel).

| Fichier | Ligne | Usage |
|---|---|---|
| `loafer-ouidah` | Loafer | Hero + carte collection |
| `loafer-ouidah-alt` | Loafer | Variante marine, pour la page produit |
| `derby-cotonou` | Derby | Carte collection |
| `derby-cotonou-alt` | Derby | Variante noire, pour la page produit |
| `boot-atakora` | Boot | Carte collection |
| `richelieu-abidjan` | Richelieu | Carte collection |
| `atelier-bicolore` | — | Aperçu du configurateur (fond étalonné, pas détouré) |

Pour retraiter après un nouvel envoi : ajouter une entrée dans `JOBS`, puis

```bash
python3 tools/process_images.py
```

Le paramètre `tol` règle la tolérance de détourage (30 = fond très propre, 72 = fond avec ombre marquée).

### ⚠ Point à trancher avant mise en ligne

Deux visuels portent des marques de fabricants tiers, visibles à l'écran :

- `loafer-ouidah` — un logo `VT` sur la bride et une signature manuscrite sur le flanc
- `loafer-ouidah-alt` — un blason estampé dans la première de propreté

Ce sont des photos de produits d'autres marques. Les publier sous le nom Yem's pose
un risque juridique (marque, droit d'auteur du photographe) et un risque de crédibilité
si un client reconnaît la pièce. Trois options : retoucher les marques, remplacer par
des photos de la production Yem's, ou n'utiliser ces visuels qu'en interne.

---

## Copy

**Accroche retenue** — « Personne ne verra la couture. Tout le monde verra la différence. »

Elle est alignée sur le slogan (« Différents par les détails »), porte un conflit
invisible/visible, couvre toutes les catégories (pas seulement la chaussure) et
n'engage aucune promesse chiffrée que le client devrait prouver. La version précédente
(« Portées encore dans six ans ») vendait la durabilité — un argument rationnel qui
tirait dans une autre direction que le slogan.

La copy applique les cadres de `course_all.txt` :

- **Les trois couches de problème** (section « Récit ») — externe : la semelle qui lâche ;
  interne : le regard qui redescend vers ses pieds ; philosophique : « le solide vient
  forcément d'ailleurs ». Puis la résolution.
- **Les deux émotions** — l'accroche du récit joue sur l'évitement (le samedi de cérémonie),
  le hero sur la projection (« portées encore dans six ans »).
- **Concret plutôt qu'abstrait** — « cuir de qualité » → « pleine fleur tannée végétal,
  1,8 à 2 mm » ; « livraison rapide » → « Cotonou et Abidjan en 48 h ».
- **Pyramide de croyance** — la section Récit valide d'abord la croyance existante avant
  de la déplacer ; les preuves techniques arrivent après l'émotion, jamais avant.
- **Offre irrésistible** — piliers par offre, risk reversal développé (section Garantie),
  rareté (capacité de production mensuelle).
- **Traitement des objections** — section « Questions » : prix, délai, chaussant, paiement.

### Chiffres à valider avant mise en ligne

Ces affirmations sont chiffrées pour être crédibles, mais le client doit pouvoir les tenir :

- « portées encore dans six ans » et le calcul coût-sur-5-ans de la FAQ (225 000 F vs 162 000 F)
- le prix de ressemelage implicite (~7 000 F)
- l'épaisseur du cuir (1,8 à 2 mm) et le tannage végétal
- les délais 48 h Cotonou / Abidjan, 5 jours autres villes
- la capacité mensuelle de production sur-mesure (le nombre est volontairement absent)
- tous les prix FCFA

---

## À fournir par le client

Emplacements balisés par des commentaires `TODO client` et, côté visuel, par la pastille `.todo-note`.

- [ ] **Logo définitif** — le monogramme actuel est un SVG provisoire (`<symbol id="i-logo">`). Un seul endroit à remplacer, réutilisé partout.
- [ ] **Vidéo hero** — les prompts Veo 3.1, les commandes de compression et le snippet HTML sont prêts dans [`docs/prompts-video-veo.md`](docs/prompts-video-veo.md). Déposer le résultat dans `assets/video/`.
- [ ] **Prix définitifs FCFA** — actuellement indicatifs (85 000 / 98 000 / 125 000 / 135 000 F ; pack 128 000 F ; sur-mesure dès 148 000 F).
- [ ] **Témoignages réels** — 3 slides à remplacer (nom, ville, verbatim).
- [ ] **Numéro WhatsApp de l'atelier** — remplacer `22900000000` (2 occurrences : CTA final + footer).
- [ ] **E-mail de contact** — remplacer `contact@yems.example`.
- [ ] **Photos ceintures, portefeuilles et entretien** — aucune reçue à ce jour.

---

## Reste à construire

1. **Pages produits** — `produit-loafer.html`, `produit-derby.html`, `produit-boot.html`, `produit-richelieu.html` (les liens pointent déjà dessus).
2. **Configurateur sur-mesure** — `configurateur.html`. Flow : configuration → facture à l'écran → notification WhatsApp au propriétaire → paiement immédiat **ou différé**. À traiter séparément du tunnel produit standard.
3. **Panier + checkout** — `panier.html`, `checkout.html`.
4. **KkiaPay** — Mobile Money MTN/Moov, Wave, carte bancaire.

Le panier est déjà amorcé côté JS : `window.YemsCart` expose `read()`, `refresh()` et la clé localStorage `yems.cart`. Format d'un article attendu : `{ id, name, price, qty, variant }`.

---

## Accessibilité

- Contrastes vérifiés WCAG AA sur toutes les paires texte/fond (min. 4,72:1 pour le texte secondaire).
- Navigation clavier : skip-link, `:focus-visible` sur tous les interactifs, menu mobile fermable par `Échap`, accordéons FAQ natifs (`<details>`).
- `prefers-reduced-motion` respecté (animations neutralisées, autoplay du carrousel désactivé).
- Toutes les images ont un `alt` descriptif et des dimensions explicites (pas de saut de mise en page).
