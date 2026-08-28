# Refaire les deux vidéos du configurateur

Ce document ne concerne **que** `cuirs.mp4` et `fils.mp4`, les deux plans
verticaux du configurateur sur-mesure. La vidéo d'accueil est conservée telle
quelle.

---

## Pourquoi les refaire

Ce n'est pas une question de qualité, elles sont bonnes. C'est une question de
véracité, et c'est le même principe que celui qui a fait retirer sept photos.

**`cuirs.mp4`** montre quatre échantillons dont un noir texturé façon saffiano,
un grain croisé qui vient de la maroquinerie industrielle. Le configurateur, lui,
ne propose que quatre teintes, toutes en **pleine fleur tannée végétal** :

| Teinte | Code | Ce qu'elle doit avoir l'air d'être |
|---|---|---|
| Cognac | `#8C5A3C` | patine chaude, grain naturel, se creuse avec les années |
| Espresso | `#3B2F29` | brun très sombre, presque neutre |
| Noir | `#1A1614` | noir profond, **lisse**, jamais texturé |
| Marine | `#232B3D` | bleu sourd, teinture longue |

Un client qui choisit « noir » en voyant un grain saffiano à l'écran ne recevra
pas ce qu'il a cru commander. C'est exactement le genre d'écart qui se paie au
premier retour.

**`fils.mp4`** montre quatre bobines dont une orange vif et une écrue, alors
que l'atelier coud au fil de lin poissé dans les tons du cuir. La bobine orange
n'existe nulle part dans l'offre.

---

## Réglages communs

| | |
|---|---|
| Format | **9:16 vertical** |
| Durée | 8 s (le site boucle par lecture inversée, voir plus bas) |
| Résolution | 1080p en sortie, on redescend à 574×960 au réencodage |
| Son | aucun, les vidéos sont muettes sur le site |
| Mouvement | lent, continu, sans coupe |

**Le point le plus important : pas de coupe, pas de raccord.** Les deux plans
tournent en boucle sur la page. Une coupe au milieu produit un saut visible
toutes les huit secondes, et c'est la première chose que l'œil remarque.

---

## Bloc de style, à coller dans chaque prompt

```
Cinematic macro product footage. Warm low-key lighting, single soft
key light from the upper left, deep shadows, no visible light source.
Colour palette limited to espresso brown (#14100D), warm beige
(#F4EDE2) and antique brass (#B08D57). Shallow depth of field,
85mm macro lens look, subtle film grain. Slow continuous camera
movement, no cuts, no transitions. Photorealistic, no CGI look.
```

Négatif, à renseigner dans le champ prévu :

```
text, letters, numbers, logos, watermarks, brand names, hands, people,
faces, sewing machine, plastic, synthetic sheen, saturated colours,
orange, red, teal, neon, fast motion, cuts, zoom snaps, lens flare
```

---

## 1. `cuirs.mp4` — les quatre cuirs

```
Four rectangular swatches of vegetable-tanned full-grain leather laid
flat in a vertical column on a dark espresso surface, seen from
directly above. From top to bottom: warm cognac brown, very dark
espresso brown, deep matte black with a smooth unembossed surface,
and muted navy blue. All four share the same fine natural grain and
soft satin finish. The camera drifts slowly downward along the column,
light grazing across the leather to reveal its texture and slight
irregularities.
```

Puis le bloc de style, puis le négatif.

**Le mot qui compte : `smooth unembossed`** sur le noir. Sans lui, les
générateurs mettent presque systématiquement un grain saffiano ou croco, parce
que c'est ce qui domine dans leurs données d'entraînement. C'est précisément
l'erreur de la vidéo actuelle.

---

## 2. `fils.mp4` — les fils de couture

```
Four spools of waxed linen thread standing upright side by side on a
dark espresso wooden surface, seen from the front. The four colours are
close in tone: warm cognac, dark chocolate brown, deep black and pale
natural ecru. The thread is matte, slightly fibrous, with a visible
twist. The camera drifts slowly sideways across the spools, a soft
grazing light picking out the texture of the wound thread.
```

Puis le bloc de style, puis le négatif.

**Ce qui change par rapport à la vidéo actuelle :** quatre tons proches au lieu
d'un contraste orange vif. Le fil doit être **mat et fibreux**, pas brillant :
un fil brillant, c'est du polyester, et ça contredit tout ce que la fiche
produit raconte sur le lin poissé.

---

## Après la génération

### 1. Vérifier avant de garder

Regarde chaque rendu en entier, deux fois, et vérifie :

- [ ] Aucun texte, aucun logo, aucune main dans le champ
- [ ] Le noir est lisse, pas texturé
- [ ] Aucune couleur hors palette, en particulier pas d'orange
- [ ] Aucune coupe, aucun saut de mouvement
- [ ] Le mouvement va dans un seul sens du début à la fin

Un seul défaut, on relance. Une vidéo qu'on garde « parce qu'elle est presque
bien » finit toujours par se voir.

### 2. Réencoder au format du site

Les fichiers exportés font en général 5 à 15 Mo. Sur le site, les deux vidéos
actuelles pèsent 487 et 788 Ko. Il faut redescendre à cet ordre de grandeur,
sinon le configurateur devient inutilisable sur un téléphone.

```powershell
ffmpeg -i cuirs-source.mp4 -vf "scale=574:960" -c:v libx264 -crf 30 -preset slow -an -movflags +faststart assets/video/cuirs.mp4
ffmpeg -i cuirs-source.mp4 -vf "scale=574:960" -c:v libvpx-vp9 -crf 38 -b:v 0 -an assets/video/cuirs.webm
```

Idem pour `fils`. `-an` retire la piste audio, inutile ici et coûteuse.
`+faststart` place l'index au début du fichier : sans lui, la lecture ne
démarre qu'une fois tout téléchargé.

### 3. Boucler proprement

Si le mouvement ne revient pas à son point de départ, la boucle saute. Le
remède est de concaténer la vidéo avec sa version inversée :

```powershell
ffmpeg -i cuirs.mp4 -filter_complex "[0]reverse[r];[0][r]concat=n=2:v=1" -an cuirs-boucle.mp4
```

La durée double, le poids aussi. À n'utiliser que si le saut se voit.

### 4. Contrôler le poids

```powershell
ls assets/video/
```

Au-dessus de 800 Ko par fichier, relance avec un `-crf` plus élevé : 32, puis
34. La perte de détail est presque invisible sur un plan macro sombre, et
chaque centaine de kilo-octets compte sur un forfait à Cotonou.

### 5. Publier

```powershell
npm run deploy
```

Aucune modification du code n'est nécessaire : les chemins ne changent pas.
