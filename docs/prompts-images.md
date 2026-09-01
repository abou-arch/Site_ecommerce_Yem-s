# Images à générer avec ChatGPT

On abandonne les vidéos. Trois images fixes les remplacent : une pour le hero,
deux pour le configurateur sur-mesure.

**C'est un bon échange.** Une image bien cadrée tient mieux qu'une vidéo de
huit secondes qui tourne en boucle, elle pèse dix fois moins, elle s'affiche
instantanément, et elle ne peut pas sauter au raccord. La vidéo n'apportait du
mouvement que pour le mouvement.

---

## Les trois images

| Fichier | Où | Format | Ce qu'elle montre |
|---|---|---|---|
| `hero.jpg` | premier écran de l'accueil | **16:9 paysage**, 2400 × 1350 | l'atelier, ambiance, pas un produit |
| `cuirs.jpg` | configurateur, choix du cuir | **9:16 vertical**, 1080 × 1920 | les quatre teintes réelles |
| `fils.jpg` | configurateur, choix du fil | **9:16 vertical**, 1080 × 1920 | les fils de lin poissé |

---

## Le bloc de style, à coller à la fin de chaque prompt

```
Photorealistic editorial photography, shot on a full-frame camera with
a fast prime lens. Warm low-key lighting from a single soft source at
the upper left, deep soft shadows, no visible light fixture. Colour
palette limited to espresso brown, warm cream and antique brass.
Shallow depth of field, natural film grain, no digital sharpening.
No text, no letters, no numbers, no logos, no watermarks, no brand
names anywhere in the image. No people, no faces, no hands.
Muted and desaturated, never bright or saturated.
```

**Pourquoi cette liste de refus est longue :** les générateurs adorent poser
une étiquette de marque inventée sur un objet de cuir. Une marque fictive sur
la photo d'accueil d'une vraie boutique, c'est exactement le problème pour
lequel on a retiré sept photos du site.

---

## 1. `hero.jpg` — le premier écran

Format **16:9 paysage**, le plus large possible.

```
A wide horizontal photograph of a leather workshop bench, seen at a low
three-quarter angle. On the worn dark wood surface: a half-finished
leather upper held in a wooden clamp, a curved awl, a spool of waxed
linen thread, and a folded piece of vegetable-tanned cognac leather.
The tools are arranged as if work has just been interrupted, not
styled for display.

Late afternoon light enters from a window on the left, raking low
across the bench and catching the grain of the leather and the twist
of the thread. The background falls away into deep warm shadow.

The left third of the frame is quiet and dark, with no objects, so
that text can sit there.
```

Puis le bloc de style.

**Les deux phrases à ne pas retirer.** Celle sur le travail interrompu :
sans elle, on obtient un étalage de catalogue, froid, qui ne raconte rien.
Et celle sur le tiers gauche vide : le titre du site s'affiche à cet endroit,
et sur une image chargée il devient illisible quel que soit le voile qu'on
pose par-dessus.

---

## 2. `cuirs.jpg` — les quatre cuirs

Format **9:16 vertical**.

```
A vertical overhead photograph of four rectangular swatches of
vegetable-tanned full-grain leather, laid flat in a single column on a
dark espresso wooden surface. From top to bottom: warm cognac brown,
very dark espresso brown, deep matte black, and muted navy blue.

All four share the same fine natural grain and the same soft satin
finish. The black swatch is perfectly smooth and even, with no
embossed, crosshatch or reptile pattern of any kind. The edges are cut
clean and slightly burnished.

A single soft light grazes across the leather from the upper left,
revealing the texture and the small natural irregularities of the hide.
```

Puis le bloc de style.

**`smooth and even, with no embossed, crosshatch or reptile pattern`** est la
phrase décisive. Sans elle, les générateurs mettent presque systématiquement
un grain saffiano sur le noir, parce que c'est ce qui domine dans leurs
données. C'est le défaut exact de la vidéo qu'on remplace, et un client qui
choisit « noir » sur cette image doit recevoir un cuir lisse.

---

## 3. `fils.jpg` — les fils de couture

Format **9:16 vertical**.

```
A vertical photograph of four spools of waxed linen thread standing
upright side by side on a dark espresso wooden surface, seen from the
front at eye level. The four colours sit close together in tone: warm
cognac, dark chocolate brown, deep black, and pale natural ecru.

The thread is matte and slightly fibrous, with a visible twist in the
fibre and a faint waxy sheen rather than a glossy one. A loose end
hangs from one spool.

A single soft light rakes across the spools from the upper left,
picking out the texture of the wound thread. The background falls into
deep shadow.
```

Puis le bloc de style.

**`matte, slightly fibrous, waxy sheen rather than glossy`** : un fil brillant,
c'est du polyester. La fiche produit parle de lin poissé, et l'image doit dire
la même chose que le texte.

---

## Si le rendu ne convient pas

ChatGPT accepte une correction en langage courant sur l'image précédente,
sans tout réécrire. Trois reprises efficaces :

> Même image, mais le cuir noir doit être parfaitement lisse, sans aucun motif.

> Même image, mais laisse le tiers gauche complètement vide et sombre.

> Même image, mais retire toute étiquette ou marque sur les objets.

Ne réécris pas le prompt entier à chaque essai : tu perds le cadrage que tu
venais d'obtenir.

---

## Avant de me les envoyer, vérifie

- [ ] Aucun texte, aucune étiquette, aucun logo, même minuscule
- [ ] Aucune main, aucun visage
- [ ] Le noir du cuir est lisse
- [ ] Aucune couleur hors palette, en particulier pas d'orange ni de rouge
- [ ] Sur le hero : le tiers gauche est bien vide et sombre

Regarde en grand, pas en vignette. Une marque inventée de trois millimètres se
voit très bien une fois l'image affichée en pleine largeur.

---

## Ce que je fais ensuite

Dépose les trois fichiers dans `assets/img/` et dis-le moi. Je m'occupe de :

1. **Redimensionner et compresser.** Le hero descend à 1920 px de large en JPEG
   et WebP, les deux verticales à 720 px. Objectif : moins de 150 Ko chacune,
   contre 495 Ko pour la seule vidéo hero aujourd'hui.
2. **Générer les variantes** pour téléphone, avec `srcset`, comme pour les
   photos produit.
3. **Remplacer le `<video>` par un `<picture>`** dans le hero et le
   configurateur, retirer les fichiers `.mp4` et `.webm`, et alléger le
   JavaScript qui gérait la lecture.
4. **Vérifier la lisibilité du titre** sur la nouvelle image, en mesurant le
   contraste réel du texte sur les pixels qui se trouvent derrière lui.

Le voile sombre en haut du hero est déjà en place : il garantit que l'en-tête
reste lisible quelle que soit la clarté de l'image que tu génères.
