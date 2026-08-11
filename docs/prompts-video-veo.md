# Prompts vidéo — Yem's

Pack de prompts pour **Veo 3.1** (Google AI Pro, via Gemini ou Flow).
Macro produit uniquement : aucune main, aucun visage.

---

## Ce qu'il faut savoir avant de lancer

| Contrainte | Valeur |
|---|---|
| Durée d'un clip | 4, 6 ou 8 secondes |
| Format | 16:9 (paysage) ou 9:16 (portrait), composés nativement |
| Résolution | 720p ou 1080p |
| Audio | généré nativement, synchronisé |
| Marquage | filigrane SynthID sur toute génération |

**La formule officielle de Veo 3.1** — les prompts ci-dessous la suivent tous :

```
[Cinématographie] + [Sujet] + [Action] + [Contexte] + [Style & Ambiance]
```

**Trois règles qui changent tout sur ce projet :**

1. **Écris les prompts en anglais.** Le modèle y est nettement plus précis. Les prompts sont donc livrés en anglais, prêts à coller.
2. **Le négatif se formule au positif.** Veo ne comprend pas bien « pas de texte ». Il comprend « clean unmarked leather with no lettering ». Chaque prompt a sa ligne de négatif rédigée dans ce sens.
3. **Le hero est muet.** L'autoplay navigateur impose `muted`. L'audio généré ne servira pas — mais laisse quand même la ligne « Ambient » dans le prompt : elle influence le rythme de l'image. En revanche, ne demande jamais de musique rythmée pour le hero, le modèle calerait les mouvements sur le beat.

**Le levier le plus utile : tes photos comme point de départ.**
Tes visuels `assets/img/*.jpg` sont déjà détourés sur le dégradé beige de la charte.
Passe-les en **image-to-video** (ou en *ingredients to video* pour garder la même
paire d'un plan à l'autre) : la vidéo hérite du bon produit, de la bonne couleur de
fond et de la bonne lumière. C'est la différence entre une vidéo « qui va avec le
site » et une vidéo générique.

---

## Le bloc de style Yem's

À coller **à la fin de chaque prompt**. C'est lui qui garantit que les huit vidéos
se ressemblent.

```
Style & ambiance: cinematic macro product film, shot on a 100mm macro lens,
very shallow depth of field, slow deliberate movement. Colour palette strictly
limited to dark espresso brown (#14100D to #3B2F29), warm beige and sand
(#FBF7F1 to #C4B195), and antique brass highlights (#C9A46A). Warm low-key
lighting from a single large soft source at a raking angle, deep soft shadows,
gentle brass specular highlights on the leather grain. Fine 35mm film grain,
no lens flare, no colour fringing. Calm, patient, luxurious mood — nothing
energetic, nothing bouncy.
```

Et la ligne de négatif, à adapter à la marge selon les plans :

```
Negative: plain undecorated leather with no logos, no lettering, no numbers,
no brand marks, no watermarks. Empty frame with no human hands, no faces,
no people. Static clean set with no floating dust particles, no smoke,
no sparkles, no lens flare. Natural leather colours only, with no blue,
no green, no purple, no neon tones.
```

---

## 1. Hero — 3 variantes

### Contrainte de composition, à ne pas négliger

Sur desktop, l'accroche et les boutons occupent **la moitié gauche** de l'écran.
La vidéo doit donc garder cette zone **sombre et vide**, et poser le sujet à droite.
Chaque prompt hero contient déjà l'instruction correspondante.

Le CSS applique déjà un dégradé sombre par-dessus (`.hero__media::after`), donc
inutile d'assombrir davantage à la génération — tu perdrais le grain du cuir.

---

### Variante A — « La couture » *(recommandée)*

Le geste signature de la marque, en image. C'est celle qui rime avec l'accroche
« Personne ne verra la couture ».

```
Extreme macro shot, 100mm macro lens, camera slowly tracking left to right at
a constant speed. Subject: a single waxed linen thread running through thick
full-grain leather in a saddle stitch, each stitch angled and evenly spaced,
the thread catching a warm brass highlight. Action: the camera glides along
the seam, stitch after stitch entering and leaving the frame, the leather
grain drifting in and out of focus. Context: a dark walnut workbench in a
quiet workshop, the background falling off into deep espresso shadow on the
left half of the frame, the lit leather sitting in the right half.

Style & ambiance: [BLOC DE STYLE]

Ambient: the faint creak of leather and a low room tone, no music.

Negative: plain undecorated leather with no logos, no lettering, no numbers,
no brand marks. Empty frame with no human hands, no needles held by anyone,
no faces. Left third of the frame kept dark and empty. Natural leather
colours only, with no blue, no green, no neon tones.
```

**Réglages :** 8 s · 16:9 · 1080p
**Pourquoi elle marche :** aucun mouvement complexe, aucune main, aucune physique difficile. Veo réussit très bien ce type de plan.

---

### Variante B — « La lumière rasante »

Plus abstraite, plus luxe. À privilégier si la variante A rend une couture irrégulière.

```
Extreme macro shot, 100mm macro lens, slow push-in with a shallow rack focus
from foreground to background. Subject: the surface of a piece of full-grain
vegetable-tanned leather in deep cognac, its pores and natural creases visible
in relief. Action: a hard raking light sweeps slowly across the surface from
right to left, revealing the grain ridge by ridge, then settling into a soft
warm pool of light on the right of the frame. Context: the leather lies flat
on a dark surface, the frame otherwise empty, the left side dissolving into
deep espresso shadow.

Style & ambiance: [BLOC DE STYLE]

Ambient: deep low room tone only, no music.

Negative: plain undecorated leather with no logos, no lettering, no stitching
visible, no brand marks. Empty frame with no human hands, no faces. Left half
of the frame kept dark and empty. Natural cognac and espresso tones only,
with no blue, no green, no neon.
```

**Réglages :** 8 s · 16:9 · 1080p
**Pourquoi elle marche :** c'est le plan le plus sûr techniquement — une surface, une lumière. Quasiment impossible à rater.

---

### Variante C — « La paire qui sort de l'ombre »

La plus vendeuse, la plus risquée. À générer en **image-to-video** depuis
`assets/img/loafer-ouidah.jpg` pour que ce soit le bon produit.

```
Slow orbital tracking shot, 85mm lens, the camera arcing gently around the
subject from left to right at eye level. Subject: a single pair of black
full-grain leather loafers with a chunky lug sole, standing on a smooth
sand-beige surface. Action: the pair emerges from deep shadow into a warm
pool of light as the camera arcs, the brass-toned highlight travelling along
the welt and the top line of the shoe. Context: a seamless warm beige studio
backdrop that falls off into darkness towards the left of the frame, the pair
positioned right of centre.

Style & ambiance: [BLOC DE STYLE]

Ambient: a very quiet studio room tone, no music.

Negative: plain unmarked shoes with no logos, no lettering, no monograms, no
signatures on the leather, no brand marks on the sole. Empty set with no human
hands, no feet, no faces, no shoelaces moving on their own. Left third of the
frame kept dark and empty. Natural black, beige and brass tones only.
```

**Réglages :** 8 s · 16:9 · 1080p · image de départ `loafer-ouidah.jpg`
**Attention :** les photos sources portent des marques de fabricants tiers (le logo `VT`, la signature manuscrite). La ligne de négatif demande explicitement de les supprimer — vérifie image par image que c'est bien le cas avant publication.

---

### Version « timestamp » — pour un hero qui raconte

Veo 3.1 accepte le découpage seconde par seconde dans un seul prompt. Utile si
tu veux trois plans dans les 8 secondes plutôt qu'un seul mouvement.

```
[00:00-00:03] Extreme macro shot, 100mm macro lens, camera tracking slowly
left to right along a saddle stitch in thick espresso leather, the waxed
thread catching a warm brass highlight.

[00:03-00:05] Cut to an extreme close-up of the welt where the sole meets the
upper, a single continuous line of stitching running through the frame, shallow
depth of field, the background falling into deep shadow.

[00:05-00:08] Slow pull-back to a wide macro of a black leather loafer standing
on a sand-beige surface, positioned right of centre, the left of the frame
remaining dark and empty, warm light settling on the toe.

Style & ambiance: [BLOC DE STYLE]

Ambient: leather creak and a low room tone, no music.

Negative: plain unmarked leather with no logos, no lettering, no brand marks.
Empty frame with no human hands, no faces. Natural leather colours only.
```

---

## 2. Vidéos produit — une par ligne

6 secondes, 16:9, à poser en haut des pages produit. Génère chacune en
**image-to-video** depuis le fichier correspondant : c'est ce qui garantit que
la vidéo montre bien *ton* produit.

**Prompt commun**, en changeant la description du sujet :

```
Slow 180-degree orbital shot, 85mm lens, the camera arcing smoothly around
the subject at a low three-quarter angle. Subject: [SUJET]. Action: the pair
rotates slowly into the light, a soft brass highlight travelling along the
welt and the edge of the sole, the leather grain resolving into focus.
Context: a seamless warm beige studio sweep, softly graded from cream at the
top to sand at the bottom, no props, no background objects.

Style & ambiance: [BLOC DE STYLE]

Ambient: quiet studio room tone, no music.

Negative: plain unmarked shoes with no logos, no lettering, no monograms,
no signatures, no brand marks on the sole. Empty set with no human hands,
no feet, no faces. Natural leather tones only.
```

| Fichier de départ | `[SUJET]` à insérer |
|---|---|
| `loafer-ouidah.jpg` | `a pair of black full-grain leather penny loafers with a chunky lug sole and a clean unmarked saddle strap` |
| `derby-cotonou.jpg` | `a pair of cognac brown leather derby shoes with open lacing and a visible apron stitch across the toe` |
| `boot-atakora.jpg` | `a pair of black leather chelsea boots with elastic side panels and a slim leather sole` |
| `richelieu-abidjan.jpg` | `a pair of black leather oxford shoes with closed lacing and a textured brogued panel` |

---

## 3. Sur-mesure — le bloc configurateur

Trois clips de 4 secondes, à passer en boucle derrière la section `#sur-mesure`.

**Le fil qu'on choisit**

```
Extreme macro shot, 100mm macro lens, static camera. Subject: four spools of
waxed linen thread in espresso brown, cognac, black and sand, lined up on a
dark walnut surface. Action: the light shifts slowly across them from left to
right, each spool lighting up in turn and falling back into shadow. Context:
a dark quiet workshop bench, the background almost black.

Style & ambiance: [BLOC DE STYLE]
Ambient: low room tone, no music.
Negative: plain spools with no labels, no lettering, no numbers, no brand
marks. Empty bench with no human hands, no faces. Natural thread colours only.
```

**Les quatre cuirs**

```
Overhead macro shot, 100mm macro lens, very slow vertical push-in. Subject:
four rectangular leather swatches laid edge to edge — deep espresso, cognac,
black and sand — each showing a different grain. Action: a soft raking light
travels slowly across the four swatches, revealing the texture of each in turn.
Context: a dark matte surface, the swatches filling the centre of the frame.

Style & ambiance: [BLOC DE STYLE]
Ambient: low room tone, no music.
Negative: plain swatches with no logos, no lettering, no stamps, no brand
marks. Empty surface with no human hands, no faces. Natural leather tones only.
```

**La gravure des initiales**

```
Extreme macro shot, 100mm macro lens, slow push-in. Subject: the smooth inner
lining of a leather shoe, warm sand coloured, filling the frame. Action: a
heated brass stamp presses slowly into the leather and lifts away, leaving a
crisp debossed impression, a faint wisp of warmth rising from the mark.
Context: a dark workshop bench, everything beyond the leather falling into
deep shadow.

Style & ambiance: [BLOC DE STYLE]
Ambient: a soft press and the creak of leather, no music.
Negative: an unmarked stamp with no readable letters, no numbers, no logos,
no brand names. Empty bench with no human hands, no faces. Natural leather
tones only.
```

> Note : ne demande **jamais** à Veo de graver des lettres précises. Les modèles
> vidéo écrivent mal. Laisse l'empreinte volontairement floue et illisible — c'est
> plus élégant et ça évite un rendu raté.

---

## 4. Carte d'authenticité

4 secondes, à poser derrière la section `#garantie`.

```
Overhead macro shot, 100mm macro lens, slow rotation of the subject clockwise.
Subject: a small dark espresso card with a dashed brass border, lying on a
sand-beige leather surface. Action: a warm light sweeps across the card,
catching the brass border and the debossed texture of the paper. Context:
a quiet dark surface, nothing else in frame.

Style & ambiance: [BLOC DE STYLE]
Ambient: the faint rustle of thick card, no music.
Negative: a blank card with no readable text, no numbers, no logos, no
lettering, no brand marks. Empty surface with no human hands, no faces.
Espresso, beige and brass tones only.
```

---

## 5. Formats sociaux — 9:16

Veo 3.1 compose nativement en 9:16, il ne recadre pas un master 16:9 : le cadrage,
le mouvement et les zones de texte sont pensés pour le vertical. Génère donc
directement en 9:16 plutôt que de recouper une vidéo paysage.

Ici l'audio **sert** — garde-le et sois précis dessus.

```
Vertical 9:16 composition. Slow vertical push-in, 100mm macro lens. Subject:
a black leather loafer standing on a sand-beige surface, filling the lower two
thirds of the vertical frame. Action: the camera rises slowly from the sole to
the top line of the shoe, a warm brass highlight travelling up the welt, the
upper third of the frame left empty and dark for a caption. Context: a seamless
warm beige to espresso gradient backdrop.

Style & ambiance: [BLOC DE STYLE]

Ambient: the creak of new leather, a soft footstep on a wooden floor, and a
slow low double bass note. Warm, unhurried, no percussion.

Negative: plain unmarked shoes with no logos, no lettering, no monograms, no
brand marks. Empty set with no human hands, no feet, no faces. Upper third of
the frame kept empty for a caption. Natural leather tones only.
```

---

## 6. Après génération — export et intégration

### Compresser pour le web

Une vidéo hero doit rester **sous 2 Mo**. C'est un site qui vise Cotonou et
Abidjan : la connexion mobile n'est pas celle d'un bureau parisien.

```bash
# MP4 (H.264) — compatible partout
ffmpeg -i hero-brut.mp4 -an \
  -vf "scale=1920:-2,fps=25" \
  -c:v libx264 -crf 26 -preset slow -profile:v high -pix_fmt yuv420p \
  -movflags +faststart \
  assets/video/hero.mp4

# WebM (VP9) — nettement plus léger, servi en premier
ffmpeg -i hero-brut.mp4 -an \
  -vf "scale=1920:-2,fps=25" \
  -c:v libvpx-vp9 -crf 36 -b:v 0 -row-mt 1 \
  assets/video/hero.webm

# Image poster, prise à 1 seconde
ffmpeg -i assets/video/hero.mp4 -ss 1 -vframes 1 -q:v 3 \
  assets/img/hero-poster.jpg
```

`-an` retire la piste audio : elle est inutile sur un hero muet et pèse pour rien.
`-movflags +faststart` déplace l'index en tête de fichier, la lecture démarre sans
attendre le téléchargement complet.

### Boucler proprement

Veo ne génère pas de boucle : la dernière image ne rejoint pas la première, et le
raccord se voit. Deux solutions, toutes deux testées :

**Le fondu croisé** — la dernière seconde se fond sur la première. Invisible sur un
plan lent, sortie de 7 s :

```bash
ffmpeg -i hero.mp4 -filter_complex \
  "[0]split[a][b];\
   [a]trim=0:7,setpts=PTS-STARTPTS[v0];\
   [b]trim=7:8,setpts=PTS-STARTPTS[v1];\
   [v0][v1]xfade=transition=fade:duration=1:offset=6" \
  hero-loop.mp4
```

**Le va-et-vient** — le clip puis sa version inversée. Raccord parfait par
construction, sortie de 16 s. C'est la meilleure option pour les variantes A et B,
dont le mouvement de caméra est linéaire :

```bash
ffmpeg -i hero.mp4 -vf reverse hero-rev.mp4
ffmpeg -i hero.mp4 -i hero-rev.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0" hero-loop.mp4
```

Recompresse ensuite `hero-loop.mp4` avec les commandes de la section précédente —
ces deux étapes sortent un fichier non optimisé.

### Coller dans le hero

Dans `index.html`, remplace la ligne `<div class="hero__media" aria-hidden="true"></div>`
par :

```html
<div class="hero__media" aria-hidden="true">
  <video autoplay muted loop playsinline preload="metadata"
         poster="assets/img/hero-poster.jpg">
    <source src="assets/video/hero.webm" type="video/webm">
    <source src="assets/video/hero.mp4" type="video/mp4">
  </video>
</div>
```

Le dégradé actuel reste en fond du `div` : si la vidéo ne charge pas, ou si le
navigateur bloque l'autoplay, la section reste présentable. Le CSS gère déjà
`object-fit: cover` et le voile sombre par-dessus.

**Pense à couper la vidéo pour qui ne veut pas d'animation** — ajoute ceci à la
fin de `assets/js/motion.js` :

```js
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.querySelectorAll('.hero__media video').forEach((v) => {
    v.removeAttribute('autoplay');
    v.pause();
  });
}
```

---

## Ordre de production conseillé

Google AI Pro donne un quota de générations limité. Voilà l'ordre qui rentabilise
le mieux les essais :

1. **Variante B du hero** — la plus sûre, elle te donne un hero utilisable dès le premier essai.
2. **Variante A** — le geste signature. Deux ou trois essais peuvent être nécessaires pour une couture régulière.
3. **Les 4 vidéos produit** en image-to-video — chacune part d'une photo, le taux de réussite est élevé.
4. **Variante C** — la plus vendeuse, mais garde-la pour quand tu maîtrises le reste.
5. **Sur-mesure et carte d'authenticité** — utiles mais secondaires, la section tient déjà sans.
6. **Le 9:16** — une fois la direction validée sur le site.
