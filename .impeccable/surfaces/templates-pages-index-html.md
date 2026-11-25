---
version: 1
slug: "templates-pages-index-html"
primary_target: "templates/pages/index.html"
related_targets: ["tools/build.py"]
---

## Direction contract

THESIS: The premium men's shoe house, played straight and executed at full craft: the image and the
piece lead, the origin line sits above every price, and nothing on the page competes with them. It
refuses no convention of the category; it refuses what the regional competition ships around it:
template leftovers, decorative chrome, crossed-out prices, invented proof.

OWN-WORLD: Warm ivory ground (#F6F1E8) for reading, espresso ink (#14100D) for text and solid
buttons, cognac (#8C5A3C) as the one accent (origin line, links, focus), a sand neutral for image
grounds and quiet panels, brass held to one detail at most. A serif display face for headlines,
centred in the hero and left-aligned in content; a sober sans for body and UI. Rectangular solid
buttons, square-cornered images, flat product cards (image on a light ground, origin, name, one spec
line, price), thin rules between sections. Quality bar: Corthay, Crockett & Jones, Septième Largeur.

STORY: A man arriving from a WhatsApp link sees the house, the portrait and one sentence, and
understands that Yem's makes some pieces in Cotonou and chooses others. He opens a piece, reads its
origin, three spec lines, its indicative price and how he pays and receives it (on delivery or by
Mobile Money, try-on at delivery, WhatsApp confirmation), picks his size and orders: cart, or
straight to WhatsApp. The bespoke configurator is one tap away for atelier shapes.

FIRST VIEWPORT: Phone (390×844): a slim header (wordmark, cart, menu) on ivory; the studio portrait
full width, about 55 % of the height, the shoes in the light; under it, centred, the serif headline
"Le détail fait la différence.", one line of lede and one solid espresso button to the shop.
Desktop: the same order, the image a wide band across the page, headline and button centred below
it, the next section's first cards beginning above the fold on 1440×900.

FORM: Canon, the category standard — the standing exit the user chose on the decision page
(2026-11-20) over "La peau, marquée à chaud" (the roll's assignment, list position 4) and "Le
registre de l'atelier" (pick). seed: seed:6fb7c1df94f20c08. Matched sketch:
.bunshin/direction/sketch-canon.html.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

INTERACTION THESIS: Sober motion that never delays the purchase block. Durations 180–480 ms,
ease-out cubic-bezier(.2,.7,.2,1). Images fade in once on scroll with an 8–12 px rise; headlines
rise once by line; on a fine pointer, product images scale 1.02 over 480 ms and links underline;
on touch, a 120 ms pressed state. A sticky one-line buy bar on product pages on phones once the main
button leaves the screen. Everything degrades to no motion under prefers-reduced-motion. Forbidden:
parallax, scroll-jacking, animated counters, decorative loops, letter-by-letter reveals, any
animation on the LCP image or the price block. (Carried from the user's earlier answer "a few sober
animations that stay light on phones"; the canon card did not print it.)

Allowed patterns: warm ivory / cream page ground, centred serif display headline in the hero,
full-width image hero, product card grid, solid dark primary button, thin section rules, scroll
reveal once per element, sticky buy bar on phone.

TYPE (chosen from rendered specimens, .bunshin/spec/display.png and pair.png): Prata for headlines,
product names and prices — its hairlines hold on a sunlit phone on ivory and on espresso, and its
figures read "103 000 F" cleanly, where Marcellus sets the zeros like capital O's ("1O3 OOO F").
Hanken Grotesk (400/500/600) for text, specs, sizes and buttons — firmer than Jost at 14 px. The
"YEM'S" wordmark keeps Marcellus: it is the brand's existing logo, not a type choice of this run.
Ruled out: Italiana, Antic Didone, Libre Caslon Display, Forum, Bellefair, Trirong (hairlines too
thin for a phone in daylight); Gloock, Young Serif (too heavy and casual for the house).
