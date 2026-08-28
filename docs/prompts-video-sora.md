# Refaire les deux vidéos du configurateur avec Sora (ChatGPT)

Pour `cuirs.mp4` et `fils.mp4` seulement. La vidéo d'accueil ne change pas.

Le rappel du problème, les couleurs de référence et toute la partie
réencodage sont dans `prompts-video-higgsfield.md`. Ce document ne contient
que ce qui est **propre à Sora**.

---

## À vérifier avant de générer quoi que ce soit

**Le filigrane.** D'après la documentation d'OpenAI, chaque vidéo produite par
Sora porte un petit filigrane « Sora » translucide, plus des métadonnées C2PA
signalant une origine générée. Sur une boutique, un filigrane d'un autre
service au milieu d'un plan produit, ce n'est pas envisageable.

**Vérifie ce point en premier**, avant d'écrire un seul prompt, en regardant
un fichier réellement téléchargé depuis ton compte. Trois issues possibles :

| Situation | Ce qu'on fait |
|---|---|
| Pas de filigrane sur l'export | on continue, tout va bien |
| Filigrane fixe dans un coin | on peut le recadrer, voir plus bas |
| Filigrane mobile ou centré | Sora n'est pas utilisable ici, reviens à Dreamina ou au téléphone |

Les métadonnées C2PA, elles, ne se voient pas et ne posent aucun problème.

**Recadrer un filigrane de coin.** Nos vidéos sont affichées en 574×960. Si le
filigrane est en bas à droite d'un rendu 1080×1920, on peut rogner 12 % en bas
et à droite avant de redimensionner :

```powershell
ffmpeg -i sora-cuirs.mp4 -vf "crop=iw*0.88:ih*0.88:0:0,scale=574:960" -c:v libx264 -crf 30 -preset slow -an -movflags +faststart assets/video/cuirs.mp4
```

Cadre le plan un peu large à la génération pour que ce rognage ne coupe pas le
sujet.

**Deux points de réglage :** l'abonnement Plus plafonne à 720p, ce qui suffit
puisqu'on redescend à 574 px de large. Et Sora accepte le 9:16 nativement,
donc demande le format vertical dès le départ plutôt que de recadrer un 16:9.

---

## Ce qui change dans l'écriture des prompts

Sora ne fonctionne pas comme Higgsfield. Il n'y a **pas de champ « négatif »
séparé** : tout tient dans un seul texte. Et il répond beaucoup mieux à de la
prose de tournage qu'à un empilement de mots-clés.

Trois règles qui changent le résultat :

1. **Écrire comme une note d'intention au chef opérateur**, pas comme une liste
   d'étiquettes. Objectif, lumière, matière, mouvement, dans cet ordre.
2. **Un seul mouvement de caméra par plan.** C'est la consigne la plus
   rentable : dès qu'on en demande deux, le raccord se voit et la boucle saute.
3. **Formuler les exclusions en fin de texte, en une phrase**, et surtout
   décrire positivement ce qu'on veut à la place. « Surface lisse et unie »
   marche mieux que « pas de grain saffiano ».

---

## 1. `cuirs.mp4`, les quatre cuirs

Format 9:16 vertical, 10 secondes.

```
A vertical 9:16 macro product shot, filmed on a 100mm macro lens at f/4.
Four rectangular swatches of vegetable-tanned full-grain leather lie
flat in a single column on a dark espresso wooden surface, viewed from
directly overhead. From top to bottom: warm cognac brown, very dark
espresso brown, deep matte black, and muted navy blue. All four have
the same fine natural grain and the same soft satin finish. The black
swatch is perfectly smooth and even, with no embossed or crosshatch
pattern of any kind.

A single soft key light enters from the upper left and grazes across
the leather, catching the natural irregularities of the hide and
casting long soft shadows. The rest of the frame falls into deep
shadow. Warm, desaturated colour grade limited to browns, cream and
antique brass.

The camera performs one slow continuous downward dolly along the
column, at a steady walking-pace crawl, from the first swatch to the
last. The move never stops, never reverses, and there are no cuts.

Photorealistic documentary product footage, subtle 35mm film grain.
No text, no logos, no hands, no people in frame. No saturated colours,
no orange or red, no lens flare.
```

**Le passage à ne pas alléger :** la phrase sur le noir. Sans elle, presque
tous les modèles posent un grain saffiano ou croco, parce que c'est ce qui
domine dans leurs données d'entraînement. C'est exactement l'erreur de la
vidéo actuelle.

---

## 2. `fils.mp4`, les fils de couture

Format 9:16 vertical, 10 secondes.

```
A vertical 9:16 macro product shot, filmed on a 100mm macro lens at f/4.
Four spools of waxed linen thread stand upright side by side on a dark
espresso wooden surface, seen from the front at eye level. The four
colours sit close together in tone: warm cognac, dark chocolate brown,
deep black, and pale natural ecru. The thread is matte and slightly
fibrous, with a visible twist in the fibre and a faint waxy sheen
rather than a glossy one.

A single soft key light comes from the upper left and rakes across the
spools, picking out the texture of the wound thread. The background
falls away into deep shadow. Warm, desaturated colour grade.

The camera performs one slow continuous lateral tracking move across
the four spools, left to right, at a steady crawl. The move never
stops and there are no cuts.

Photorealistic documentary product footage, subtle 35mm film grain.
No text, no logos, no hands, no people, no sewing machine in frame.
No bright or saturated colours, no orange, no neon.
```

**Ce qui compte ici :** `matte`, `slightly fibrous`, `waxy sheen rather than
glossy`. Un fil brillant, c'est du polyester, et ça contredit tout ce que la
fiche produit dit du lin poissé. La vidéo actuelle a ce défaut, en plus de sa
bobine orange.

---

## Si le rendu ne convient pas

Sora accepte qu'on lui demande une correction en langage courant sur le rendu
précédent. Deux reprises qui marchent bien :

> Same shot, but the black leather swatch must be completely smooth, with no
> texture pattern at all.

> Same shot, but slow the camera move down by half and keep it going all the
> way to the end of the clip.

Évite de tout réécrire à chaque essai : tu perds le cadrage que tu venais
d'obtenir.

---

## Après la génération

Reprends `prompts-video-higgsfield.md`, section **Après la génération** : la
liste de contrôle, le réencodage aux 574×960, la boucle par lecture inversée
et le contrôle du poids sont identiques quel que soit le générateur.

Une seule addition propre à Sora : **vérifie le filigrane sur le fichier final
réencodé**, pas sur l'aperçu dans ChatGPT.
