#!/usr/bin/env python3
"""
Yem's — Générateur de site statique.

Assemble les pages HTML à partir de :
  data/products.json     le catalogue
  templates/base.html    le squelette de document
  templates/partials/    header, footer, définitions SVG
  templates/pages/       le contenu propre à chaque page écrite à la main

Sortie, à la racine du dépôt :
  index.html
  <categorie>.html         une par catégorie
  produit/<slug>.html      une par produit

Usage :  python3 tools/build.py
"""

import base64
import datetime
import hashlib
import json
import os
from urllib.parse import quote
import re
import shutil
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "products.json")
TPL = os.path.join(ROOT, "templates")
OUT_PRODUCTS = os.path.join(ROOT, "produit")

# Libellé court pour les vignettes, libellé explicite pour la fiche produit :
# « En route » ne dit rien à l'acheteur, « arrivage sous 10 jours » si.
STATUS = {
    "green": ("badge--green", "Disponible",  "En stock à Cotonou, expédié sous 72 h"),
    "amber": ("badge--amber", "En route",     "En route, arrivage sous 10 jours"),
    "red":   ("badge--red",   "Indisponible", "Sur commande uniquement"),
}


# ─────────────────────────────────────────────────────────── utilitaires

# Les notes de travail (« À valider », « Capacité à confirmer »…) servent à
# Abou, pas au visiteur : lire « prix indicatifs à confirmer » sur une boutique
# ouverte suffit à faire renoncer quelqu'un. Elles ne sortent donc que si on
# le demande explicitement :
#     BROUILLON=1 python3 tools/build.py
BROUILLON = os.environ.get("BROUILLON") == "1"

# Mode de règlement effectif. Il doit correspondre à PAYMENT_MODE de
# wrangler.toml : c'est lui qui décide de ce que le site a le droit d'annoncer.
#   PAYMENT_MODE=online python3 tools/build.py
PAYMENT_MODE = os.environ.get("PAYMENT_MODE", "offline")


def strip_notes(html):
    """Retire les blocs <p>…<span class="todo-note">…</span>…</p> du rendu public."""
    if BROUILLON:
        return html
    # Le paragraphe entier part, pas seulement l'étiquette : sans elle, la
    # phrase qui suit resterait orpheline au milieu de la page.
    return re.sub(r'\n?\s*<p[^>]*>(?:(?!</p>).)*?todo-note.*?</p>', '', html, flags=re.S)


# Typographie française : le signe ne quitte pas le mot qu'il accompagne.
# Avec une espace ordinaire, le navigateur pouvait couper juste avant « : »
# ou « ? », ou juste après « « », et laisser le signe seul en début ou en fin
# de ligne. Certains textes portaient déjà &nbsp;, pas tous : la règle est
# donc appliquée ici, une fois, au texte de toutes les pages.
SEPARATEURS = re.compile(r'(<script\b.*?</script\s*>|<style\b.*?</style\s*>|<!--.*?-->|<[^>]+>)',
                         flags=re.S | re.I)


def espaces_insecables(html):
    """Espace insécable avant : ; ? ! et à l'intérieur des guillemets.

    Seul le texte visible est touché : balises, attributs, scripts, styles et
    commentaires restent tels quels (les empreintes de la CSP ne bougent pas).
    """
    def texte(t):
        t = re.sub(r'«[ \t\n]+', '« ', t)
        t = re.sub(r'[ \t\n]+»', ' »', t)
        return re.sub(r'(?<=\S)[ \t\n]+([:;?!])', ' \\1', t)

    morceaux = SEPARATEURS.split(html)
    return "".join(m if i % 2 else texte(m) for i, m in enumerate(morceaux))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def fill(template, **values):
    """Remplace les {{clés}} du gabarit. Signale toute clé oubliée."""
    for key, value in values.items():
        template = template.replace("{{%s}}" % key, str(value))
    leftover = sorted(set(re.findall(r"\{\{(\w+)\}\}", template)))
    if leftover:
        raise SystemExit("!! placeholders non remplis : %s" % ", ".join(leftover))
    return template


def nombre_en_lettres(n):
    """7 → « Sept » : un nombre en tête de phrase s'écrit en lettres."""
    mots = ["Aucun", "Un", "Deux", "Trois", "Quatre", "Cinq", "Six", "Sept",
            "Huit", "Neuf", "Dix", "Onze", "Douze"]
    return mots[n] if 0 <= n < len(mots) else str(n)


def price(value):
    """85000 → « 85 000 F » — espace insécable fine avant l'unité."""
    return "{:,}".format(int(value)).replace(",", " ") + " F"


def badge(status, extra="", long=False, slug=None):
    """
    Pastille de disponibilité.

    L'attribut data-badge sert de point d'ancrage : quand l'atelier change la
    disponibilité depuis son écran, le Worker réécrit cette pastille au vol
    dans la page statique, sans qu'il faille reconstruire le site. Le suffixe
    dit s'il faut le libellé court (vignette) ou détaillé (fiche produit).
    """
    cls, short, detailed = STATUS[status]
    ancre = (' data-badge="%s" data-badge-long="%s"' % (slug, "1" if long else "0")
             if slug else "")
    return ('<span class="badge %s %s"%s><span class="badge__dot"></span>%s</span>'
            % (cls, extra, ancre, detailed if long else short))


# ─────────────────────────────────────────────────────────── composants

# Place réellement occupée par une image, selon l'endroit où elle s'affiche.
# Une valeur fausse fait charger au navigateur une image trop grande, ou trop
# petite et donc floue : ces trois chaînes décrivent les trois grilles du site.
GRID_SIZES = "(max-width: 759px) 46vw, (max-width: 1179px) 31vw, 23vw"   # vignettes de grille
MAIN_SIZES = "(max-width: 900px) 92vw, 45vw"                            # photo d'ouverture d'une fiche
THUMB_SIZES = "(max-width: 900px) 30vw, 15vw"                           # petites vues sous la photo


def picture(product, base, index=0, lazy=True, sizes=None):
    """<picture> WebP + JPEG, ou placeholder beige si la photo manque."""
    images = product.get("images") or []
    if not images:
        # Un cadre assumé plutôt qu'un trou.
        #
        # « Photo à venir » sur fond beige se lit comme une page inachevée.
        # Le monogramme en filigrane et le mot « atelier » disent au contraire
        # que la pièce existe et qu'on ne veut pas la montrer n'importe
        # comment. C'est le même propos que la page « Ce qui se prépare »,
        # tenu à l'échelle d'une vignette.
        return ('<div class="pshot__empty">'
                '<svg class="pshot__mark" aria-hidden="true"><use href="#i-logo"></use></svg>'
                '</div>')

    img = images[index]
    loading = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'

    # Deux largeurs, et le navigateur choisit.
    #
    # Le site ne servait que le fichier de 1000 px. Sur un téléphone de 375 px
    # affichant une vignette sur la moitié de l'écran, c'était jusqu'à quatre
    # fois plus de pixels que nécessaire, payés par le visiteur.
    #
    # « sizes » n'est pas décoratif : sans lui le navigateur suppose que
    # l'image occupe toute la largeur de la fenêtre et reprend la grande.
    # La valeur par défaut décrit la grille réelle : pleine largeur sur
    # téléphone, une demie sur tablette, un tiers sur grand écran.
    mesure = sizes or GRID_SIZES
    petit = os.path.exists(os.path.join(ROOT, "assets", "img", img["file"] + "-500.webp"))

    def jeu(ext):
        if not petit:
            return "%sassets/img/%s.%s" % (base, img["file"], ext)
        return ("%sassets/img/%s-500.%s 500w, %sassets/img/%s.%s %dw"
                % (base, img["file"], ext, base, img["file"], ext, img["w"]))

    return (
        '<picture>\n'
        '            <source srcset="%s" sizes="%s" type="image/webp">\n'
        '            <img src="%sassets/img/%s.jpg" srcset="%s" sizes="%s"\n'
        '                 width="%d" height="%d"%s\n'
        '                 alt="%s">\n'
        '          </picture>'
        % (jeu("webp"), mesure,
           base, img["file"], jeu("jpg"), mesure,
           img["w"], img["h"], loading,
           escape(img["alt"], quote=True))
    )


def mention_ia():
    """
    La pastille « Visuel IA » posée sur chaque image — retirée du rendu.

    Abou l'a demandée enlevée : trente pastilles sur six pages, posées sur
    toutes les photos de la boutique, finissaient par être le premier élément
    qu'on voyait d'une vignette produit.

    LA TRANSPARENCE, ELLE, NE DISPARAÎT PAS. Elle n'est plus répétée sur
    chaque image : elle est dite une fois par page, en pied de page
    (templates/partials/footer.html), et développée dans les mentions légales
    (« Les visuels des pièces »). La phrase des mentions légales a été
    réécrite en conséquence — elle promettait une pastille sur chaque fiche,
    elle aurait été fausse sans cela.

    La fonction reste, et reste appelée partout : c'est le seul endroit à
    modifier pour remettre la pastille, et l'attribut data-visuel-ia que le
    Worker supprime (api/_lib/rewrite.js) retrouverait alors sa cible.
    """
    return ""


ORIGINES = {}   # rempli au démarrage depuis data/products.json


def origine_marque(product, long=False):
    """
    Dit d'où vient la pièce, sur chaque vignette et chaque fiche.

    Ce n'est pas une mention légale reléguée en bas de page : c'est la
    promesse même de la maison. Un client doit savoir avant d'acheter si
    l'atelier a fabriqué la pièce ou l'a choisie, parce que la garantie
    n'est pas la même — ressemelage à vie d'un côté, échange un an de l'autre.
    """
    o = ORIGINES.get(product.get("origine", "selection"))
    if not o:
        return ""
    cls = "origine origine--%s" % product.get("origine", "selection")
    if long:
        return ('<p class="%s origine--long"><strong>%s</strong>%s</p>'
                % (cls, escape(o["nom"]), escape(o["phrase"])))
    return '<span class="%s">%s</span>' % (cls, escape(o["court"]))


def product_card(product, base, delay=0, level=3, sizes=None, eager=False):
    """Carte produit, telle qu'elle apparaît dans une grille."""
    href = "%sproduit/%s.html" % (base, product["slug"])
    style = ' style="--reveal-delay:%dms"' % delay if delay else ""
    images = product.get("images") or []
    empty = "" if images else " pshot--empty"
    # Les mentions de transparence sur les visuels sont centralisées en bas
    # de page ; une pastille sur chaque photo surchargeait les cartes.
    note = ""
    texte = ligne_produit(product)
    ligne = '<p class="pcard__spec">%s</p>' % escape(texte) if texte else ""
    return f"""      <article class="pcard" data-reveal{style} data-piece="{product['slug']}">
        <a href="{href}" tabindex="-1" aria-hidden="true">
          <div class="pshot{empty}" data-shot>
            {badge(product['status'], 'pshot__badge', slug=product['slug'])}
            {picture(product, base, lazy=not eager, sizes=sizes)}{note}
          </div>
        </a>
        <div class="pcard__body">
          <h{level} class="pcard__name"><a href="{href}">{escape(product['name'])}</a></h{level}>
          {ligne}
          <div class="pcard__foot">
            {origine_marque(product)}
            <span class="pcard__price" data-prix="{product['slug']}">{price(product['price'])}</span>
          </div>
        </div>
      </article>"""


def ligne_produit(product):
    """
    La ligne de description d'une vignette : ce qu'est la pièce, en quelques
    mots, tirée de sa première caractéristique (« Derby à lacets · Noir »,
    « Pleine fleur tannée végétal, 2 mm »). Rien n'est inventé : sans
    caractéristique, la vignette s'en passe.

    L'ordre de la vignette est nom, ligne, origine, prix : l'origine reste
    au-dessus du prix, comme le veut la maison, sans faire surtitre au-dessus
    du nom.
    """
    specs = [s for s in product.get("specs") or []
             if s.get("value") and "confirmer" not in s["value"]]
    if not specs:
        return ""
    texte = specs[0]["value"]
    if len(specs) > 1 and specs[1].get("label") == "Coloris":
        texte += " · " + specs[1]["value"]
    return texte


def hero_piece(product, base):
    """
    La carte « En vitrine » posée dans le hero, sur grand écran.

    C'est la carte flottante en verre de la référence Framer (AestheticMatch) :
    un accès direct à une pièce, depuis l'image d'ouverture, sans attendre la
    grille. Elle reprend la première pièce de la vitrine, donc rien qu'elle
    affiche ne peut contredire le catalogue.

    data-piece et data-prix sont les ancres du Worker (api/_lib/rewrite.js) :
    une pièce retirée de la vente disparaît aussi d'ici, et un prix corrigé
    par l'atelier s'y corrige comme sur la vignette. La photo est décorative :
    le lien porte déjà le nom de la pièce.
    """
    if not product:
        return ""
    o = ORIGINES.get(product.get("origine", "selection")) or {}
    href = "%sproduit/%s.html" % (base, product["slug"])
    return f"""<a class="hero-piece" href="{href}" data-piece="{product['slug']}" data-reveal style="--reveal-delay:240ms">
    <span class="hero-piece__photo" aria-hidden="true">
          {picture(product, base, sizes="112px")}
    </span>
    <span class="hero-piece__corps">
      <span class="hero-piece__surtitre">En vitrine</span>
      <span class="hero-piece__nom">{escape(product['name'])}</span>
      <span class="hero-piece__meta">{escape(o.get('court', ''))}</span>
      <span class="hero-piece__prix" data-prix="{product['slug']}">{price(product['price'])}</span>
    </span>
    <span class="hero-piece__aller" aria-hidden="true"><svg><use href="#i-arrow-biais"></use></svg></span>
  </a>"""


def grid(products, base, klass="collections__grid", level=3, rare=True, sizes=None, eager=0):
    if not products:
        return """      <div class="empty-state">
        <p class="display">Cette ligne arrive bientôt.</p>
        <p class="text-muted">Écrivez-nous sur WhatsApp pour être prévenu du lancement.</p>
      </div>"""
    # eager : les premières vignettes d'une page qui ouvre sur la grille
    # partent tout de suite (pas de chargement différé), la première en
    # priorité. sizes : la largeur réelle de cette grille-là.
    cards = [product_card(p, base, delay=i * 90, level=level, sizes=sizes, eager=i < eager)
             for i, p in enumerate(products)]

    # La grille s'adapte au nombre de pièces réellement en vente.
    #
    # Une grille calibrée pour douze vignettes, remplie avec trois, donne des
    # images minuscules perdues dans le vide : la page a l'air d'un catalogue
    # dont on aurait retiré la marchandise. Tant que la maison n'a que trois
    # pièces photographiées, mieux vaut trois grandes vignettes qui remplissent
    # la rangée. La classe disparaîtra d'elle-même quand le catalogue
    # s'étoffera, sans qu'il y ait rien à modifier.
    #
    # La vitrine d'accueil s'en dispense (rare=False) : elle tient toujours
    # exactement quatre pièces, sa grille est donc calibrée pour quatre et
    # n'a aucun trou à combler.
    marque = " grid--rare" if rare and len(products) <= 4 else ""
    return '    <div class="%s%s">\n%s\n    </div>' % (klass, marque, "\n\n".join(cards))


def nav_links(entries, base, home, current=None, mobile=False):
    """
    Construit la navigation depuis site.nav.
    Une entrée dont le href commence par « # » est une ancre de la homepage :
    elle doit être préfixée par le chemin vers index.html depuis la page courante.
    """
    out = []
    for e in entries:
        href = e["href"]
        if href.startswith("#"):
            href = home + href
            active = False
        else:
            href = base + href
            active = href.endswith("%s.html" % current) if current else False
        aria = ' aria-current="page"' if active else ""
        if mobile:
            out.append('  <a href="%s"%s>%s</a>' % (href, aria, e["label"]))
        else:
            out.append('      <a class="nav__link" href="%s"%s>%s</a>'
                       % (href, aria, e["label"]))
    return "\n".join(out)


def breadcrumb(items):
    """items = [(libellé, href ou None)] — le dernier n'est pas cliquable."""
    parts = []
    for label, href in items:
        if href:
            parts.append('<a href="%s">%s</a>' % (href, escape(label)))
        else:
            parts.append('<span aria-current="page">%s</span>' % escape(label))
    return ('<nav class="crumb" aria-label="Fil d\'Ariane"><div class="container">%s</div></nav>'
            % '<span class="crumb__sep" aria-hidden="true">/</span>'.join(parts))


def json_ld(payload):
    return ('<script type="application/ld+json">%s</script>\n'
            % json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


# Adresse canonique du site, renseignée au démarrage depuis data/products.json.
# Tant qu'elle est vide, le générateur se tait plutôt que d'écrire une adresse
# inventée : une balise canonical fausse est pire que pas de balise du tout,
# elle désigne à Google une page qui n'existe pas.
SITE_URL = ""

# Pages du tunnel de commande : elles répondent 200, elles ne sont pas en
# noindex (un client doit pouvoir y revenir), mais elles n'ont rien à faire
# dans un sitemap. Une page de confirmation indexée enverrait des visiteurs
# sur une commande vide, et une page de panier indexée capterait des
# recherches qu'elle ne sait pas satisfaire.
TUNNEL = {"panier.html", "checkout.html", "commande-confirmee.html", "404.html"}


def url_absolue(chemin):
    """« produit/derby.html » → « https://maisonyems.com/produit/derby.html »."""
    if not SITE_URL:
        return ""
    return "%s/%s" % (SITE_URL, chemin.replace("index.html", "").lstrip("/"))


def version_assets(html, root):
    """
    Ajoute une empreinte du contenu à chaque CSS et JS : assets/css/base.css
    devient assets/css/base.css?v=a1b2c3d4.

    Sans ça, le navigateur garde en cache l'ancienne feuille de style et
    l'applique au nouveau HTML — on croit alors que la mise en ligne a échoué.
    L'empreinte ne bouge que si le fichier a réellement changé.
    """
    cache = {}

    def stamp(m):
        rel = m.group(2)                      # ex. assets/css/base.css
        path = os.path.join(root, rel)
        if rel not in cache:
            if not os.path.exists(path):
                cache[rel] = None
            else:
                with open(path, "rb") as f:
                    cache[rel] = hashlib.sha1(f.read()).hexdigest()[:8]
        h = cache[rel]
        return m.group(0) if h is None else '%s%s?v=%s"' % (m.group(1), rel, h)

    return re.sub(r'((?:href|src)="(?:\.\./)*)((?:assets/(?:css|js)/[\w.-]+\.(?:css|js)))"',
                  stamp, html)


# ─────────────────────────────────────────────────────────── assemblage

class Builder:
    def __init__(self):
        self.data = json.loads(read(DATA))
        self.site = self.data["site"]
        # Les deux lignes de la maison, lues une fois et partagées par tous
        # les composants qui doivent afficher l'origine d'une pièce.
        ORIGINES.update(self.site.get("origines", {}))
        global SITE_URL
        SITE_URL = (self.site.get("url") or "").rstrip("/")
        # Une pièce en attente n'existe nulle part sur le site public : ni
        # vignette, ni fiche, ni panier. Elle reste dans le catalogue pour
        # qu'il suffise de basculer a_venir à false le jour des photos.
        self.a_venir = [p for p in self.data["products"] if p.get("a_venir")]
        # Les formes du configurateur existent dans le même catalogue éditorial
        # que les pièces visibles, mais ne doivent jamais s'échapper dans les
        # grilles, les catégories ou le panier si leur statut change plus tard.
        self.products = [
            p for p in self.data["products"]
            if not p.get("a_venir") and not p.get("configurateur_only")
        ]
        self.categories = self.data["categories"]
        self.base_tpl = read(os.path.join(TPL, "base.html"))
        self.svg_defs = read(os.path.join(TPL, "partials", "svg-defs.html")).strip()
        self.header_tpl = read(os.path.join(TPL, "partials", "header.html"))
        self.footer_tpl = read(os.path.join(TPL, "partials", "footer.html"))
        self.written = []
        self.indexables = []

    def by_category(self, slug):
        return [p for p in self.products if p["category"] == slug]

    def chrome(self, base, home, current):
        """Header et footer, résolus pour la profondeur de la page."""
        nav = self.site["nav"]
        header = fill(
            self.header_tpl,
            base=base,
            nav=nav_links(nav, base, home, current),
            nav_mobile=nav_links(nav, base, home, current, mobile=True),
            whatsapp=self.site["whatsapp"],
        )
        # Le footer ne liste que ce qui existe. Une catégorie sans pièce
        # visible n'a plus de page : y renvoyer créerait un lien mort.
        footer_cats = "\n".join(
            '          <li><a href="%s%s.html">%s</a></li>' % (base, c["slug"], c["name"])
            for c in self.categories if self.by_category(c["slug"])
        )
        if self.a_venir:
            footer_cats += ('\n          <li><a href="%sa-venir.html">'
                            'Ce qui se prépare</a></li>' % base)
        moyens = (self.site.get("paiement", {}) or {}).get(
            PAYMENT_MODE, ["Espèces"])
        footer = fill(
            self.footer_tpl,
            pay_logos="\n".join("          <span>%s</span>" % escape(m)
                                 for m in moyens),
            base=base, home=home,
            footer_categories=footer_cats,
            whatsapp=self.site["whatsapp"],
            email=self.site["email"],
        )
        return header, footer

    def page(self, path, *, content, title, description,
             og_title=None, og_type="website", og_image=None,
             current=None, depth=0, structured=None,
             extra_css=(), extra_js=(), noindex=False, body_class=""):
        base = "../" * depth
        home = "%sindex.html" % base if path != "index.html" else ""
        header, footer = self.chrome(base, home, current)

        html = fill(
            self.base_tpl,
            # contenu de <title> : c'est du texte, pas un attribut — les
            # apostrophes n'ont pas à être échappées (html.escape échappe par défaut)
            title=escape(title, quote=False),
            description=escape(description, quote=True),
            robots=('<meta name="robots" content="noindex, nofollow">\n'
                    if noindex else ""),
            # Une page qu'on demande aux robots d'ignorer n'a pas de version
            # canonique à déclarer : lui en donner une reviendrait à la
            # signaler tout en disant de ne pas la regarder.
            canonical=('<link rel="canonical" href="%s">\n' % url_absolue(path)
                       if (SITE_URL and not noindex) else ""),
            og_url=('<meta property="og:url" content="%s">\n' % url_absolue(path)
                    if (SITE_URL and not noindex) else ""),
            og_title=escape(og_title or title, quote=True),
            og_type=og_type,
            # og:image DOIT être une adresse absolue. WhatsApp, Facebook et
            # LinkedIn ignorent purement et simplement un chemin relatif : le
            # lien partagé apparaît alors sans vignette. Comme presque tout le
            # trafic de cette boutique passera par un lien WhatsApp, c'est la
            # balise la plus rentable de tout le fichier.
            og_image=('<meta property="og:image" content="%s">\n'
                      % url_absolue("assets/img/%s.jpg" % og_image)
                      if (og_image and SITE_URL) else ""),
            structured_data=json_ld(structured) if structured else "",
            # Les deux pages éditoriales (accueil, about us) ouvrent sur une
            # image pleine derrière laquelle l'en-tête doit disparaître. Les
            # autres gardent leur barre opaque : une barre transparente sur un
            # fond clair rendrait la navigation illisible.
            body_class=' class="%s"' % body_class if body_class else "",
            base=base,
            extra_css="\n".join(
                '<link rel="stylesheet" href="%sassets/css/%s.css">' % (base, f)
                for f in extra_css),
            extra_js="\n".join(
                '<script src="%sassets/js/%s.js" defer></script>' % (base, f)
                for f in extra_js),
            svg_defs=self.svg_defs,
            header=header,
            footer=footer,
            content=content,
        )
        html = strip_notes(html)
        html = espaces_insecables(html)
        html = version_assets(html, ROOT)
        write(os.path.join(ROOT, path), html)
        self.written.append((path, len(html.encode())))
        # Le sitemap se déduit de ce qui a réellement été écrit, jamais d'une
        # liste tenue à la main : une liste manuelle finit toujours par
        # annoncer une page supprimée ou par oublier une page ajoutée.
        if not noindex and path not in TUNNEL:
            self.indexables.append(path)

    # ── les trois types de page ──────────────────────────────────────

    def apercu_sur_mesure(self):
        """
        L'exemple de l'aperçu sur-mesure, sur l'accueil, calculé comme au panier.

        Le total était écrit à la main (« 158 000 F ») et ne correspondait plus
        au modèle affiché : un Derby Cotonou avec initiales coûte 166 000 +
        6 000 F. Il se déduit désormais des prix du catalogue, selon la règle
        de priceBespoke() dans api/_lib/catalog.js : forme + cuir + semelle,
        plus les initiales s'il y en a. Un prix changé dans products.json
        change l'aperçu au build suivant.
        """
        cfg = self.site["bespoke"]
        choix = cfg["apercu"]

        def option(liste, cle):
            o = next((o for o in cfg[liste] if o["id"] == choix[cle]), None)
            if o is None:
                raise SystemExit("!! bespoke.apercu.%s : « %s » absent de bespoke.%s"
                                 % (cle, choix[cle], liste))
            return o

        forme, cuir, semelle = option("shapes", "shape"), option("leathers", "leather"), option("soles", "sole")
        initiales = (choix.get("initials") or "").strip()
        total = (forme["price"] + cuir["price"] + semelle["price"]
                 + (cfg["initials"]["price"] if initiales else 0))
        return {
            "apercu_modele": escape(forme["name"]),
            "apercu_cuir": "Pleine fleur, %s" % escape(cuir["name"].lower()),
            "apercu_initiales": escape(initiales or "Aucune"),
            "apercu_total": price(total),
        }

    # Nombre de vignettes de la vitrine d'accueil. Quatre, parce que c'est ce
    # que la grille montre sur une rangée en grand écran et sur deux rangées
    # pleines au téléphone : trois laisseraient un trou, cinq couperaient.
    VITRINE = 4

    def vitrine(self):
        """
        Les pièces mises en vitrine sur l'accueil.

        Les pièces marquées « featured » passent devant, puis la vitrine se
        complète dans l'ordre du catalogue. Sans ce complément, la grille
        d'accueil tombait à deux vignettes : les quatre autres pièces mises en
        avant dans data/products.json sont encore « à venir », donc invisibles
        sur le site public. Une rangée à moitié vide fait une boutique vide.
        """
        choisies = [p for p in self.products if p.get("featured")]
        for p in self.products:
            if len(choisies) >= self.VITRINE:
                break
            if p not in choisies:
                choisies.append(p)
        return choisies[:self.VITRINE]

    def build_home(self):
        body = read(os.path.join(TPL, "pages", "index.html"))
        vitrine = self.vitrine()
        # Les chiffres de la section « Fabriqué ou choisi » sont tirés des
        # données, jamais écrits dans le gabarit : une pièce ajoutée à la
        # sélection ou un prix de forme corrigé se répercutent seuls.
        selection = [p for p in self.products
                     if p.get("origine") == "selection" and not p.get("a_venir")
                     and p.get("category") == "selection"]  # les souliers, pas l'entretien
        bespoke = self.site["bespoke"]
        body = fill(body, base="", whatsapp=self.site["whatsapp"],
                    featured_grid=grid(vitrine, "",
                                       klass="vitrine__grid", rare=False,
                                       sizes="(max-width: 899px) 46vw, 23vw"),
                    visuel_ia=mention_ia(),
                    nb_selection=nombre_en_lettres(len(selection)),
                    delai_sur_mesure=bespoke["lead_days"][:1].upper() + bespoke["lead_days"][1:],
                    prix_sur_mesure=price(min(f["price"] for f in bespoke["shapes"])),
                    acompte=bespoke["deposit"])
        self.page(
            "index.html",
            content=body,
            # page-maison : l'accueil de la refonte n'emprunte plus rien à
            # home.css (ancien hero, cartes arrondies, en-tête transparent) ;
            # ses styles sont dans accueil.css.
            body_class="page-maison",
            extra_css=("accueil",),
            title="Souliers et maroquinerie cousus main à Cotonou | Yem's",
            description=("Yem's : souliers, ceintures et portefeuilles cousus à la main à "
                         "Cotonou. Point sellier, cuir pleine fleur, semelle ressemelable. "
                         "Sélection disponible à Cotonou, sur-mesure en 15 jours, livré au Bénin et en Côte d'Ivoire."),
            og_title="Yem's. Le détail fait la différence.",
            # L'aperçu de partage montrait une photo qui n'appartenait pas à
            # l'atelier. Il n'y en a plus tant qu'une vraie n'aura pas été prise :
            # mieux vaut aucune vignette qu'une vignette empruntée.
            og_image=None,
            structured={
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Yem's",
                "slogan": self.site["slogan"],
                "areaServed": self.site["cities"],
                # « url » est ce qui permet à Google de rattacher la marque à
                # un site, et donc d'afficher le nom « Yem's » plutôt que
                # « maisonyems.com » dans les résultats.
                **({"url": SITE_URL + "/"} if SITE_URL else {}),
                "contactPoint": {
                    "@type": "ContactPoint",
                    "contactType": "customer service",
                    "telephone": "+" + self.site["whatsapp"],
                    "availableLanguage": "fr",
                },
            },
        )

    def build_about(self):
        """
        « About us » : la page qui porte tout ce que l'accueil racontait.

        L'accueil ouvrait sur sept sections de récit avant la première
        vignette produit. Le récit n'a pas disparu — il a changé d'adresse.
        Ici vivent les deux lignes, les quatre preuves techniques, les trois
        façons d'acheter, le sur-mesure étape par étape, les garanties et les
        objections. L'accueil ouvre et mène aux produits ; cette page répond
        à qui veut savoir avant d'acheter.

        Les ancres (#manifeste, #lignes, #offres, #sur-mesure, #garantie,
        #questions, #confiance) sont celles que le pied de page et les anciens
        liens d'accueil employaient déjà : elles ont suivi le contenu.
        """
        body = read(os.path.join(TPL, "pages", "about-us.html"))
        body = fill(body, base="", whatsapp=self.site["whatsapp"],
                    visuel_ia=mention_ia())
        self.page(
            "about-us.html",
            content=body,
            body_class="page-edito",
            current="about-us",
            title="About us : l'atelier et la sélection | Yem's",
            description=("Deux façons de travailler, une seule maison pour en répondre. "
                         "L'atelier de Cotonou, la sélection contrôlée, les garanties "
                         "ligne par ligne et le sur-mesure étape par étape."),
            og_title="Yem's. Personne ne verra la couture. Tout le monde verra la différence.",
            og_image=None,
            structured={
                "@context": "https://schema.org",
                "@type": "AboutPage",
                "name": "About us — Yem's",
                "description": ("La maison Yem's : un atelier à Cotonou, une sélection "
                                "contrôlée, et l'origine écrite sur chaque pièce."),
                **({"url": url_absolue("about-us.html")} if SITE_URL else {}),
            },
        )

    # ── la boutique et les pages catégorie (refonte « maison ») ─────
    #
    # Le registre est celui de l'accueil : un titre Prata aligné à gauche,
    # une ou deux phrases tirées des données, puis les pièces ; des filets
    # fins entre les sections, aucun surtitre, aucune carte numérotée. Les
    # styles sont dans assets/css/boutique.css, chargée sur ces pages seules.

    def ligne_origine(self, origine):
        """« Choisi par l'atelier. Échange un an, pointure ou défaut. » :
        l'origine et la garantie de la ligne, mot pour mot depuis
        site.origines, jamais réécrites dans le gabarit."""
        o = ORIGINES.get(origine)
        if not o:
            return ""
        return "<strong>%s.</strong> %s." % (escape(o["court"]), escape(o["garantie"]))

    def note_prix(self):
        """La réserve sur les prix, telle que l'accueil l'affiche."""
        return ('    <p class="bloc__note">\n'
                '      <span class="todo-note">À valider</span>\n'
                '      Prix indicatifs en FCFA, à confirmer avant mise en ligne.\n'
                '    </p>')

    def tete_rayon(self, titre, lede, ligne):
        """L'ouverture d'une page de rayon : le h1 à gauche, le texte à côté
        sur grand écran, dessous au téléphone. Rien n'y est animé : c'est le
        premier écran."""
        ligne = '\n      <p class="rayon-tete__ligne">%s</p>' % ligne if ligne else ""
        return f"""    <div class="rayon-tete">
      <h1 id="rayon-titre">{titre}</h1>
      <div class="rayon-tete__texte">
      <p class="rayon-tete__lede">{lede}</p>{ligne}
      </div>
    </div>"""

    def invitation(self, *, ident, titre, phrase, lien):
        """La dernière section : un filet, un titre, une phrase, un bouton.
        Sur fond ivoire, comme la question qui ferme l'accueil."""
        return f"""<section class="bloc bloc--filet invitation" aria-labelledby="{ident}">
  <div class="container container--narrow invitation__inner">
    <h2 id="{ident}" data-lines>{titre}</h2>
    <p>{phrase}</p>
    {lien}
  </div>
</section>"""

    def methode(self, origine="selection"):
        """
        Ce qui se passe avant que la paire arrive, sous la grille d'un rayon.

        Les trois cartes numérotées 01 / 02 / 03 et le bandeau d'icônes
        de l'ancien registre deviennent une liste à filets (dt / dd), comme
        « Payer et recevoir » sur l'accueil. Les faits sont les mêmes : le
        choix, le contrôle à la réception, la garantie et le numéro, rien à
        payer d'avance, 48 h à Cotonou et Abidjan. La numérotation ne disait
        rien qu'un ordre de lecture ne dise déjà : elle est retirée.

        Le bloc est gardé sur la page catégorie parce qu'il dit ce que l'en-tête
        ne dit pas (ce que l'on contrôle, la semelle collée, comment on paie).
        Il n'est plus posé sur la boutique : elle a déjà la garantie de chaque
        ligne en tête de page, et sa tâche est de montrer les pièces.
        """
        if origine == "atelier":
            faits = [
                ("Le cuir", "La peau est choisie à Cotonou, puis coupée à la "
                 "forme. C'est là que se décide la tenue d'une paire, bien "
                 "avant la couture."),
                ("La couture", "Point sellier, deux aiguilles, un fil de lin "
                 "poissé. Plus lent qu'une machine, et c'est le but : un point "
                 "qui lâche ne défait pas la ligne."),
                ("La garantie", "Ressemelage à vie, et une retouche offerte "
                 "après essayage sur le sur-mesure. La semelle se remplace, la "
                 "paire reste. Chaque pièce porte un numéro."),
            ]
        else:
            faits = [
                ("Le choix", "Ce que l'atelier ne fabrique pas, il va le "
                 "chercher lui-même, l'essaie et le compare avant de le retenir."),
                ("Le contrôle", "Chaque paire est ouverte à la réception : "
                 "couture, doublure, collage, symétrie. Ce qui ne passe pas ne "
                 "part pas."),
                ("La garantie", "Numérotée, échangeable un an, pointure ou "
                 "défaut. La semelle est collée : elle ne se ressemelle pas, "
                 "nous préférons le dire avant l'achat."),
            ]
        faits.append(("Payer et recevoir", "Rien à payer d'avance : vous réglez "
                      "à la livraison ou par Mobile Money. Expédiée sous 72 h, "
                      "puis livrée en 48 h à Cotonou et à Abidjan, sous 5 jours "
                      "ailleurs (jours ouvrés)."))

        lignes = "\n".join(
            f"""      <div data-reveal style="--reveal-delay:{i * 60}ms">
        <dt>{escape(titre)}</dt>
        <dd>{escape(texte, quote=False)}</dd>
      </div>""" for i, (titre, texte) in enumerate(faits))

        return f"""<section class="bloc bloc--filet methode-rayon" aria-labelledby="methode-titre">
  <div class="container container--wide methode-rayon__grille">
    <div class="methode-rayon__tete">
      <h2 id="methode-titre" data-lines>Avant que votre paire arrive</h2>
      <p>Ce que nous faisons de chaque pièce, et ce qui se passe si elle ne vous va pas.</p>
    </div>
    <dl class="methode-rayon__liste">
{lignes}
    </dl>
  </div>
</section>"""

    def build_category(self, cat):
        products = self.by_category(cat["slug"])
        # L'origine du rayon se lit sur ses pièces : un rayon où tout est
        # fabriqué à Cotonou affiche la garantie de l'atelier, un rayon de la
        # sélection celle de la sélection. Un rayon mêlé n'en affiche aucune
        # plutôt que d'en promettre une qui ne vaudrait pas pour tout.
        origines = {p.get("origine", "selection") for p in products}
        origine = cat.get("origine") or (next(iter(origines)) if len(origines) == 1 else None)

        rayon = f"""<section class="rayon-page" aria-labelledby="rayon-titre">
  <div class="container container--wide">
{self.tete_rayon(cat['heading'], cat['lede'], self.ligne_origine(origine) if origine else "")}

{grid(products, "", klass="rayon-grille", level=2, rare=False, eager=2)}

{self.note_prix()}
  </div>
</section>"""

        invitation = self.invitation(
            ident="invitation-titre",
            titre="Rien ne vous va exactement&nbsp;?",
            phrase=("Composez votre paire en deux minutes&nbsp;: le prix "
                    "s'affiche poste par poste, et l'atelier confirme la date "
                    "sur WhatsApp avant tout paiement."),
            lien='<a class="btn" href="configurateur.html">Composer ma paire</a>',
        )

        parties = [breadcrumb([("Accueil", "index.html"), (cat["name"], None)]), rayon]
        if origine:
            parties.append(self.methode(origine))
        parties.append(invitation)

        self.page(
            "%s.html" % cat["slug"],
            content="\n\n".join(parties),
            # « Yem's » n'est ajouté que s'il n'est pas déjà dans le titre
            # de la catégorie : « Sélection Yem's : … | Yem's » le disait deux
            # fois dans un onglet de navigateur.
            title=cat["title"] if "Yem's" in cat["title"] else "%s | Yem's" % cat["title"],
            description=cat["description"],
            current=cat["slug"],
            body_class="page-rayon",
            extra_css=("boutique",),
            structured={
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": cat["name"],
                "description": cat["description"],
            },
        )

    def build_product(self, product):
        cat = next(c for c in self.categories if c["slug"] == product["category"])
        base = "../"
        images = product.get("images") or []

        # galerie
        #
        # Une même pièce se décline en plusieurs teintes. Chaque photo porte
        # la sienne (« teinte » dans products.json) ; la fiche prépare un jeu
        # de photos par teinte et le bouton de couleur affiche le bon. Une
        # photo sans teinte vaut pour toutes. Tant que le client n'a rien
        # choisi, c'est la première teinte qui s'affiche.
        if images:
            teintes = [c["name"] for c in product.get("colors") or []]
            teintes = [t for t in teintes
                       if any(im.get("teinte") == t for im in images)] or [None]

            def vignette(i):
                # Les visuels générés viennent après les vraies photos et le
                # disent : la pièce livrée doit ressembler à ce que montre la
                # fiche, et une image générée est idéalisée par construction.
                note = mention_ia() if images[i].get("ia") else ""
                return '          <div class="pshot">%s%s</div>' % (
                    picture(product, base, i, sizes=THUMB_SIZES), note)

            jeux = []
            for n, teinte in enumerate(teintes):
                idx = [i for i, im in enumerate(images)
                       if teinte is None or im.get("teinte") in (teinte, None)]
                # La photo d'ouverture garde le format de l'image : un visuel
                # au format paysage enfermé dans un cadre portrait perdait un
                # quart de sa largeur, coupée à gauche et à droite.
                grand = images[idx[0]]
                main = ('<div class="pshot" data-shot style="--shot-ratio:%d/%d">%s\n          %s%s\n        </div>'
                        % (grand["w"], grand["h"],
                           badge(product["status"], "pshot__badge", slug=product["slug"]),
                           picture(product, base, idx[0], lazy=n > 0,
                                   sizes=MAIN_SIZES),
                           mention_ia() if grand.get("ia") else ""))
                thumbs = ""
                if len(idx) > 1:
                    thumbs = ('\n        <div class="gallery__thumbs">\n'
                              + "\n".join(vignette(i) for i in idx[1:])
                              + "\n        </div>")
                if teinte is None:
                    jeux.append(main + thumbs)
                else:
                    jeux.append('<div class="gallery__set" data-teinte="%s"%s>\n        %s%s\n      </div>'
                                % (escape(teinte, quote=True), " hidden" if n else "",
                                   main, thumbs))
            main_shot = "\n      ".join(jeux)
            thumbs = ""
        else:
            main_shot = ('<div class="pshot pshot--empty" data-shot>%s</div>'
                         % badge(product["status"], "pshot__badge", slug=product["slug"]))
            thumbs = ""

        # La ligne de la pièce décide de ce que la fiche a le droit de dire :
        # l'atelier ajuste ce qu'il monte, pas ce qu'il a choisi ailleurs, et
        # la garantie n'est pas la même (site.origines, section 2 des CGV).
        atelier = product.get("origine") == "atelier"
        ligne = ORIGINES.get(product.get("origine", "selection")) or {}

        # pointures
        sizes = ""
        if product.get("sizes"):
            buttons = "\n".join(
                '          <button class="size" type="button" data-size="%d">%d</button>' % (s, s)
                for s in product["sizes"])
            aide_pointure = (
                "Entre deux&nbsp;? Prenez la plus grande, l'atelier ajuste au montage."
                if atelier else
                "Entre deux pointures&nbsp;? Sur la sélection, la pointure "
                "s'échange pendant un an.")
            sizes = f"""        <div class="picker">
          <span class="picker__label">Pointure</span>
          <div class="picker__row">
{buttons}
          </div>
          <p class="picker__help">{aide_pointure}</p>
        </div>"""

        # couleurs
        colors = ""
        if product.get("colors"):
            # Un vrai bouton par couleur, avec son nom : une pastille muette
            # oblige à deviner, et « Marine » se confond avec « Noir » à 30 px.
            swatches = "\n".join(
                '          <button class="teinte swatch--btn" type="button" data-color="%s">'
                '<span class="teinte__dot" style="background:%s" aria-hidden="true"></span>%s</button>'
                % (escape(c["name"], quote=True), c["hex"], escape(c["name"]))
                for c in product["colors"])
            aide = ("Choisissez une couleur" if len(product["colors"]) > 1
                    else "Une seule couleur pour l'instant")
            colors = f"""        <div class="picker">
          <span class="picker__label">Couleur</span>
          <div class="picker__row">
{swatches}
          </div>
          <p class="picker__help" data-color-label>{aide}</p>
        </div>"""

        specs = "\n".join(
            '          <div class="spec-row"><dt>%s</dt><dd>%s</dd></div>'
            % (escape(s["label"]), s["value"]) for s in product["specs"])

        # Blocs dépliables : la construction propre au modèle, puis
        # l'entretien et la livraison, communs à toute la boutique.
        panels = []
        if product.get("details"):
            body = "".join(
                "<p><strong>%s</strong> : %s</p>" % (escape(d["title"]), d["text"])
                for d in product["details"])
            panels.append(("La construction", body))
        # Une fiche peut remplacer le texte d'un bloc commun par le sien,
        # au même identifiant : l'entretien d'un daim n'est pas celui d'un
        # cuir lisse, et la crème conseillée à l'un tacherait l'autre.
        propres = product.get("accordions") or {}
        for acc in self.site.get("accordions", []):
            panels.append((acc["title"],
                           "<p>%s</p>" % propres.get(acc.get("id"), acc["body"])))

        details = ""
        if panels:
            items = "\n".join(f"""      <details>
        <summary>{title}</summary>
        <div class="faq__body">{body}</div>
      </details>""" for title, body in panels)
            details = f"""
<section class="section">
  <div class="container">
    <div class="section-head" data-reveal>
      <h2>Ce qu'on ne voit pas de loin</h2>
    </div>

    <div class="faq" data-reveal style="--reveal-delay:100ms">
{items}
    </div>
  </div>
</section>"""

        # appel à l'action : sur-mesure seul, ou panier + sur-mesure
        if product.get("bespoke_only"):
            actions = f"""        <a class="btn btn--full" href="{base}configurateur.html">
          Composer ma paire sur-mesure
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
        <p class="text-muted" style="font-size:var(--fs-sm);margin-top:var(--sp-3)">
          Ce modèle n'existe qu'en sur-mesure. Délai de production : 15 jours.
        </p>"""
        else:
            actions = f"""        <button class="btn btn--full" type="button"
                data-add-to-cart
                data-id="{product['slug']}"
                data-name="{escape(product['name'], quote=True)}"
                data-price="{product['price']}"
                data-cart="{base}panier.html">
          Ajouter au panier
          <svg aria-hidden="true"><use href="#i-bag"></use></svg>
        </button>"""

        # LA BARRE D'ACHAT DU TÉLÉPHONE
        # Sur un téléphone, le bouton d'achat arrive après la galerie, le nom,
        # l'origine, deux paragraphes et les sélecteurs : à près de deux
        # écrans du haut de la fiche. Cette barre garde le prix et l'action à
        # portée de pouce tant que le vrai bouton n'est pas à l'écran.
        # Elle ne porte aucune logique : son bouton passe la main au bouton
        # de la fiche (main.js), qui vérifie pointure et couleur. Le prix porte
        # data-prix, que le Worker réécrit comme celui de la fiche.
        if product.get("bespoke_only"):
            barre_action = (f'<a class="btn btn--sm" '
                            f'href="{base}configurateur.html">Composer ma paire</a>')
        else:
            barre_action = ('<button class="btn btn--sm" type="button" '
                            'data-buybar-add>Ajouter au panier</button>')
        buybar = f"""
<div class="buybar" data-buybar inert aria-hidden="true">
  <span class="buybar__info">
    <span class="buybar__nom">{escape(product['name'])}</span>
    <span class="buybar__prix" data-prix="{product['slug']}">{price(product['price'])}</span>
  </span>
  {barre_action}
</div>"""

        related =[p for p in self.by_category(product["category"])
                   if p["slug"] != product["slug"]][:3]
        related_block = ""
        if related:
            # « La même construction » n'est vrai que de l'atelier : les pièces
            # de la sélection viennent de fabricants différents.
            titre, lien = (
                ("Les autres formes", "Toute la collection")
                if atelier else
                ("Les autres modèles", "Toute la sélection"))
            related_block = f"""
<section class="section section--light product-suite">
  <div class="container">
    <div class="section-head section-head--split" data-reveal>
      <h2>{titre}</h2>
      <a class="lien" href="{base}{cat['slug']}.html">
        {lien}
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
    </div>

{grid(related, base, klass='shop-grid', rare=False)}
  </div>
</section>"""

        # Le configurateur ne fabrique que les formes de l'atelier : il n'a
        # sa place sous le bouton que sur une fiche de l'atelier.
        lien_atelier = (f"""      <a class="lien" href="{base}configurateur.html">
        Composer une paire sur mesure à l'atelier
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>""" if atelier else "")

        # Commander sur WhatsApp : le message arrive déjà rédigé, avec le nom
        # de la pièce. Le prix n'y figure pas : l'atelier peut le corriger en
        # direct (Worker), et le message ne doit jamais contredire la fiche.
        if product.get("bespoke_only"):
            commande_wa = ""
        else:
            message = quote("Bonjour, je souhaite commander le %s." % product["name"])
            # main.js réécrit ce lien quand le client choisit sa pointure et sa
            # couleur (data-wa-nom, data-wa-base) : le message arrive complet.
            commande_wa = f"""        <a class="btn btn--ghost btn--full lien--wa" href="https://wa.me/{self.site['whatsapp']}?text={message}"
           data-wa-nom="{escape(product['name'], quote=True)}" data-wa-base="https://wa.me/{self.site['whatsapp']}"
           target="_blank" rel="noopener">
          <svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>
          Commander sur WhatsApp
        </a>"""

        content = f"""{breadcrumb([("Accueil", base + "index.html"),
                                  (cat["name"], base + cat["slug"] + ".html"),
                                  (product["name"], None)])}

<section class="section section--top">
  <div class="container product">
    <!-- Ni la galerie (l'image d'ouverture est le LCP) ni le bloc du prix ne
         sont animés : rien ne doit retarder l'achat. -->
    <div class="product__gallery">
      {main_shot}{thumbs}
    </div>

    <div class="product__info">
      <h1 class="product__name">{escape(product['name'])}</h1>
      {origine_marque(product)}
      <p class="product__price"><span data-prix="{product['slug']}">{price(product['price'])}</span>
        <small>francs CFA, prix indicatif</small></p>
      {badge(product['status'], long=True, slug=product['slug'])}
      <p class="lede" data-court="{product['slug']}">{product['short']}</p>

      <div class="product__pickers">
{colors}
{sizes}
      </div>

      <div class="product__actions">
{actions}
{commande_wa}
      </div>

      <!-- Payer et recevoir : ce qui se passe après le bouton, juste sous le
           bouton. Sources : CGV (paiement à la livraison ou Mobile Money,
           confirmation des frais sur WhatsApp avant tout règlement),
           site.origines (garantie de la ligne), confirmation de la maison du
           20 novembre 2026 pour l'essai à la livraison. -->
      <div class="recevoir-fiche">
        <h2 class="recevoir-fiche__titre">Payer et recevoir</h2>
        <ul>
          <li><strong>À la livraison ou par Mobile Money.</strong> En espèces, ou par MTN MoMo, Moov ou Wave, convenu avec l'atelier.</li>
          <li><strong>Essai à la livraison.</strong> Vous essayez la paire au moment où on vous la livre.</li>
          <li><strong>Confirmation sur WhatsApp.</strong> L'atelier confirme la commande et ses frais avant tout règlement.</li>
          <li><strong>Expédiée sous 72&nbsp;h</strong>, puis livrée en 48&nbsp;h à Cotonou et à Abidjan, sous 5 jours ailleurs au Bénin et en Côte d'Ivoire (jours ouvrés).</li>
          <li><strong>{escape(ligne.get('garantie', ''))}.</strong> {"Carte numérotée." if atelier else "Paire numérotée à la réception."}</li>
        </ul>
      </div>
{lien_atelier}

      <dl class="product__specs">
{specs}
      </dl>

      {origine_marque(product, long=True)}
      <p class="product__pitch">{product['pitch']}</p>
    </div>
  </div>
</section>
{details}{related_block}{buybar}"""

        self.page(
            "produit/%s.html" % product["slug"],
            content=content,
            title="%s, %s | Yem's" % (product["name"], cat["name"]),
            description=product["short"],
            og_type="product",
            og_image=images[0]["file"] if images else None,
            current=cat["slug"],
            depth=1,
            extra_css=("fiche",),
            structured={
                "@context": "https://schema.org",
                "@type": "Product",
                "name": product["name"],
                "description": product["short"],
                "category": cat["name"],
                "offers": {
                    "@type": "Offer",
                    "price": product["price"],
                    "priceCurrency": "XOF",
                    "availability": ("https://schema.org/InStock"
                                     if product["status"] == "green"
                                     else "https://schema.org/PreOrder"),
                },
            },
        )

    def build_stub(self, path, *, title, description, eyebrow, heading, text):
        """Page d'attente : évite les liens morts vers ce qui reste à construire."""
        content = f"""<section class="section section--top cta grain" style="min-height:70svh;display:grid;place-items:center">
  <div class="container container--narrow">
    <span class="eyebrow eyebrow--center" data-reveal>{eyebrow}</span>
    <h1 style="margin-top:var(--sp-4);font-size:var(--fs-3xl)" data-lines>{heading}</h1>
    <p class="lede mx-auto text-center" style="margin-top:var(--sp-5)" data-reveal>{text}</p>
    <div class="cta__actions" data-reveal>
      <a class="btn" href="selection.html">
        Voir les souliers
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
      <a class="btn btn--ghost" href="https://wa.me/{self.site['whatsapp']}" target="_blank" rel="noopener">
        <svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>
        Commander sur WhatsApp
      </a>
    </div>
  </div>
</section>"""
        self.page(path, content=content, title=title, description=description)


    # ── le configurateur sur-mesure ──────────────────────────────────

    def build_configurator(self):
        cfg = self.site["bespoke"]

        def opts(group, items, render):
            return ('    <div class="cfg-options" data-group="%s">\n%s\n    </div>'
                    % (group, "\n".join(render(o) for o in items)))

        # Les visuels de forme sont vides tant que l'atelier n'a pas
        # photographié sa propre production : le placeholder beige prend le
        # relais plutôt qu'une image qui appartient à quelqu'un d'autre.
        def vignette_forme(o):
            if not o.get("image"):
                return '<span class="cfg-opt__shot pshot--empty"></span>'
            return ('<span class="cfg-opt__shot"><picture>'
                    '<source srcset="assets/img/%s.webp" type="image/webp">'
                    '<img src="assets/img/%s.jpg" width="400" height="275" '
                    'loading="lazy" decoding="async" alt="%s"></picture></span>'
                    % (o["image"], o["image"], escape(o["name"], quote=True)))

        # Avant le premier choix, le total affichait « … » : sur la barre du
        # téléphone, c'était la seule chose lisible, et elle avait l'air d'un
        # chargement en panne. Le prix de départ est un fait du catalogue :
        # celui de la forme la moins chère, comme les « dès » des options.
        depart = "dès " + price(min(o["price"] for o in cfg["shapes"]))

        shapes = opts("shape", cfg["shapes"], lambda o: f"""      <button class="cfg-opt" type="button" aria-pressed="false" data-id="{o['id']}">
        {vignette_forme(o)}
        <span class="cfg-opt__top">
          <span class="cfg-opt__name">{escape(o['name'])}</span>
          <span class="cfg-opt__price">dès {price(o['price'])}</span>
        </span>
        <span class="cfg-opt__note">{o['note']}</span>
      </button>""")

        leathers = opts("leather", cfg["leathers"], lambda o: f"""      <button class="cfg-opt" type="button" aria-pressed="false" data-id="{o['id']}">
        <span class="cfg-opt__top">
          <span style="display:flex;align-items:center;gap:var(--sp-3)">
            <span class="cfg-opt__chip" style="background:{o['hex']}"></span>
            <span class="cfg-opt__name">{escape(o['name'])}</span>
          </span>
          <span class="cfg-opt__price">{"inclus" if not o["price"] else "+ " + price(o["price"])}</span>
        </span>
        <span class="cfg-opt__note">{o['note']}</span>
      </button>""")

        soles = opts("sole", cfg["soles"], lambda o: f"""      <button class="cfg-opt" type="button" aria-pressed="false" data-id="{o['id']}">
        <span class="cfg-opt__top">
          <span class="cfg-opt__name">{escape(o['name'])}</span>
          <span class="cfg-opt__price">{"inclus" if not o["price"] else "+ " + price(o["price"])}</span>
        </span>
        <span class="cfg-opt__note">{o['note']}</span>
      </button>""")

        sizes = "\n".join(
            '        <button class="size" type="button" aria-pressed="false" data-id="%d">%d</button>' % (n, n)
            for n in cfg["sizes"])

        # Les initiales sont facultatives : « À choisir » laissait croire
        # qu'il fallait en mettre pour commander.
        def line(key, label, vide="À choisir"):
            return (f'          <div class="spec-row" data-line="{key}" data-empty>'
                    f'<dt>{label}</dt>'
                    f'<dd><em data-extra></em><span data-value>{vide}</span></dd></div>')

        content = f"""{breadcrumb([("Accueil", "index.html"), ("Le sur-mesure", None)])}

<section class="section section--top">
  <div class="container">
    <!-- La mesure est en pixels, pas en « ch ». Le « ch » se calcule dans la
         police du bloc — Jost — alors qu'il contraint ici un titre en Playfair,
         dont les caractères sont bien plus larges : le titre tombait en six
         lignes de trois mots. -->
    <div class="section-head section-head--mesure" data-reveal>
      <span class="eyebrow">Le sur-mesure</span>
      <h1 data-lines>Une paire cousue<br>pour un seul pied au monde.<br>Le vôtre.</h1>
      <p class="lede">
        Six décisions, {cfg['lead_days']}. Chaque choix se voit dans l'aperçu et dans
        le prix. Rien ne se découvre à la fin.
      </p>
    </div>

    <div class="cfg" data-cfg>
      <div class="cfg__steps">

        <section class="cfg-step">
          <div class="cfg-step__head">
            <span class="cfg-step__num">01</span>
            <h2>La forme</h2>
            <p class="cfg-step__hint">Elle fixe le prix de base. Tout le reste s'y ajoute.</p>
          </div>
{shapes}
        </section>

        <section class="cfg-step">
          <div class="cfg-step__head">
            <span class="cfg-step__num">02</span>
            <h2>Le cuir</h2>
            <p class="cfg-step__hint">Pleine fleur, tannage végétal. Il foncera et se patinera avec les années, c'est voulu.</p>
          </div>
{leathers}
        </section>

        <section class="cfg-step">
          <div class="cfg-step__head">
            <span class="cfg-step__num">03</span>
            <h2>Le fil</h2>
            <p class="cfg-step__hint">Lin ciré, quatre teintes. Ton sur ton, la couture se devine. Contrastée, elle se voit à trois mètres. L'atelier vous demandera votre choix au moment de confirmer.</p>
          </div>
        </section>

        <section class="cfg-step">
          <div class="cfg-step__head">
            <span class="cfg-step__num">04</span>
            <h2>La semelle</h2>
            <p class="cfg-step__hint">Les deux se ressemellent. La gomme tient mieux sous la pluie.</p>
          </div>
{soles}
        </section>

        <section class="cfg-step">
          <div class="cfg-step__head">
            <span class="cfg-step__num">05</span>
            <h2>La pointure</h2>
            <p class="cfg-step__hint">Entre deux&nbsp;? Prenez la plus grande, l'atelier ajuste la forme à vos mesures exactes lors de la prise de cotes.</p>
          </div>
          <div class="cfg-sizes" data-group="size">
{sizes}
          </div>
        </section>

        <section class="cfg-step">
          <div class="cfg-step__head">
            <span class="cfg-step__num">06</span>
            <h2>Les initiales</h2>
            <p class="cfg-step__hint">{cfg['initials']['note']}</p>
          </div>
          <div class="cfg-initials">
            <label class="visually-hidden" for="cfg-init">Vos initiales</label>
            <input id="cfg-init" type="text" placeholder="A. C." maxlength="4"
                   autocomplete="off" data-cfg-initials>
            <span class="cfg-opt__price">+ {price(cfg['initials']['price'])}</span>
          </div>
        </section>

      </div>

      <aside class="cfg__summary">
        <div class="cfg-card">
          <div class="cfg-card__shot" data-cfg-shot></div>
          <h2>Votre paire</h2>

          <dl class="cfg-lines">
{line("shape", "Forme")}
{line("leather", "Cuir")}
{line("sole", "Semelle")}
{line("size", "Pointure")}
{line("initials", "Initiales", vide="Aucune")}
          </dl>

          <div class="cfg-total">
            <span class="cfg-total__label">Total</span>
            <span class="cfg-total__value" data-total>{depart}</span>
          </div>

          <button class="btn btn--full" type="button" data-cfg-add data-cart="panier.html" disabled>
            Ajouter au panier
            <svg aria-hidden="true"><use href="#i-bag"></use></svg>
          </button>

          <!-- Un bouton grisé sans explication fait chercher ce qui manque.
               configurator.js écrit ici les choix qui restent à faire, et
               retire la ligne quand tout est décidé. -->
          <p class="cfg-card__foot" data-cfg-manque aria-live="polite">
            Il reste à choisir : la forme, le cuir, la semelle et la pointure.
          </p>

          <p class="cfg-card__foot">
            Rien à payer maintenant. L'atelier vous rappelle dans la journée pour
            confirmer la date, puis vous versez un acompte de {cfg['deposit']}&nbsp;% :
            Mobile Money MTN, Moov ou Wave, ou espèces à l'atelier. Le solde à la livraison.
          </p>

          <ul class="cfg-trust">
            <li><svg aria-hidden="true"><use href="#i-needle"></use></svg>Point sellier main, une retouche offerte</li>
            <li><svg aria-hidden="true"><use href="#i-card"></use></svg>Carte d'authenticité numérotée</li>
            <li><svg aria-hidden="true"><use href="#i-truck"></use></svg>Cotonou &amp; Abidjan : 48&nbsp;h après l'atelier</li>
          </ul>
        </div>
      </aside>
    </div>
  </div>

  <div class="cfg-bar">
    <span class="cfg-bar__total">
      <span data-total>{depart}</span>
      <span class="cfg-bar__label">Cousue à la commande, {cfg['lead_days']}</span>
    </span>
    <!-- Ce bouton-là n'est jamais grisé : sur téléphone, un bouton mort au
         bas de l'écran ne dit pas quoi faire. Tant qu'un choix manque, il
         s'appelle « Continuer » et mène à l'étape qui manque. -->
    <button class="btn btn--sm" type="button" data-cfg-add data-cfg-bar data-cart="panier.html">Continuer</button>
  </div>
</section>

<script type="application/json" id="cfg-data">{json.dumps({
    "base": "",
    "shapes": cfg["shapes"],
    "leathers": cfg["leathers"],
    "soles": cfg["soles"],
    "initials": cfg["initials"],
}, ensure_ascii=False)}</script>"""

        self.page(
            "configurateur.html",
            content=content,
            title="Composer sa paire sur-mesure | Yem's",
            description="Composez votre paire sur-mesure : forme, cuir, semelle, pointure "
                        "et initiales. Prix en direct, %s, acompte de %d %% une fois "
                        "la date confirmée par l'atelier."
                        % (cfg["lead_days"], cfg["deposit"]),
            extra_css=("configurator",),
            extra_js=("configurator",),
        )


    # ── panier, checkout, confirmation ───────────────────────────────

    def build_cart(self):
        content = f"""{breadcrumb([("Accueil", "index.html"), ("Panier", None)])}

<section class="section section--top">
  <div class="container shop-grid">
    <div>
      <!-- « Votre sélection » se confondait avec la Sélection, la ligne des
           pièces choisies par l'atelier. Le surtitre dit plutôt où l'on en
           est : deux étapes, celle-ci et le formulaire de livraison. -->
      <div class="section-head" data-reveal>
        <span class="eyebrow">Étape 1 sur 2</span>
        <h1 class="page-title" data-lines>Votre panier</h1>
      </div>
      <div data-cart-list></div>
    </div>

    <aside class="shop-aside" data-cart-summary hidden>
      <div class="summary">
        <h2>Récapitulatif</h2>
        <div class="summary__total">
          <span>Sous-total</span>
          <span data-cart-subtotal>…</span>
        </div>
        <!-- Aucune de ces lignes ne promet plus que les CGV : rien n'est
             prélevé sur le site, les frais hors Bénin et Côte d'Ivoire sont
             confirmés par l'atelier, et la garantie citée vaut pour toutes
             les pièces (échange de pointure sous 7 jours, section 9). -->
        <p class="summary__note">
          Livraison offerte au Bénin et en Côte d'Ivoire. Pour un autre pays,
          l'atelier vous confirme les frais sur WhatsApp avant tout règlement.
        </p>
        <p class="summary__note" data-deposit-notice hidden>
          Votre panier contient une pièce sur-mesure : un acompte de
          {self.site['bespoke']['deposit']}&nbsp;% vous sera demandé avant sa fabrication, le solde
          à la livraison. Rien n'est prélevé sur le site.
        </p>
        <a class="btn btn--full" href="checkout.html">
          Passer commande
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
        <ul class="cfg-trust">
          <li><svg aria-hidden="true"><use href="#i-shield"></use></svg>Échange de pointure sous 7 jours</li>
          <li><svg aria-hidden="true"><use href="#i-card"></use></svg>Rien à payer à la commande</li>
          <li><svg aria-hidden="true"><use href="#i-truck"></use></svg>Cotonou &amp; Abidjan en 48&nbsp;h</li>
        </ul>
      </div>
    </aside>
  </div>
</section>"""

        self.page(
            "panier.html", content=content,
            title="Panier | Yem's",
            description="Votre panier Yem's. Commandez sans payer d'avance : l'atelier "
                        "vous rappelle et vous réglez à la livraison ou par Mobile Money.",
            extra_css=("checkout",), extra_js=("checkout",),
        )

    def build_checkout(self):
        countries = "\n".join(
            '            <option value="%s"%s>%s</option>' % (code, sel, label)
            for code, label, sel in [
                ("BJ", "Bénin", ' selected'), ("CI", "Côte d'Ivoire", ''),
                ("TG", "Togo", ''), ("SN", "Sénégal", ''), ("NE", "Niger", ''),
            ])

        content = f"""{breadcrumb([("Accueil", "index.html"), ("Panier", "panier.html"), ("Commande", None)])}

<section class="section section--top">
  <div class="container shop-grid">
    <div>
      <div class="section-head" data-reveal>
        <span class="eyebrow">Étape 2 sur 2</span>
        <h1 class="page-title" data-lines>Où livrons-nous<br>votre commande&nbsp;?</h1>
      </div>

      <form data-checkout-form novalidate>
        <label class="field">
          <span>Nom et prénom</span>
          <input name="name" type="text" required minlength="3" maxlength="120"
                 autocomplete="name" placeholder="Votre nom complet">
        </label>

        <div class="field-row">
          <label class="field">
            <span>Téléphone</span>
            <!-- Les numéros béninois ont dix chiffres depuis novembre 2024 :
                 un exemple à huit chiffres faisait douter du format attendu.
                 Le serveur accepte les deux (cleanPhone, api/_lib/http.js). -->
            <input name="phone" type="tel" required autocomplete="tel"
                   placeholder="01 97 00 00 00">
            <span class="field__hint">Celui de votre Mobile Money, c'est par là que l'atelier vous joindra.</span>
          </label>
          <label class="field">
            <span>Pays</span>
            <select name="country">
{countries}
            </select>
          </label>
        </div>

        <label class="field">
          <span>Adresse de livraison</span>
          <input name="address" type="text" required minlength="5" maxlength="300"
                 autocomplete="street-address" placeholder="Quartier, rue, repère">
        </label>

        <div class="field-row">
          <label class="field">
            <span>Ville</span>
            <input name="city" type="text" required maxlength="120"
                   autocomplete="address-level2" placeholder="Cotonou">
          </label>
          <label class="field">
            <span>E-mail <small style="text-transform:none;letter-spacing:0">(facultatif)</small></span>
            <input name="email" type="email" maxlength="160"
                   autocomplete="email" placeholder="vous@exemple.com"
                   aria-describedby="email-usage">
            <!-- Demander une donnée sans dire à quoi elle sert est ce qui fait
                 abandonner un formulaire, et ce qu'une note de confidentialité
                 interdit. Une ligne suffit à lever les deux objections. -->
            <small id="email-usage" class="field__aide">
              Uniquement si nous n'arrivons pas à vous joindre au téléphone.
              Jamais de publicité.
            </small>
          </label>
        </div>

        <label class="field">
          <span>Précision pour le livreur <small style="text-transform:none;letter-spacing:0">(facultatif)</small></span>
          <textarea name="note" maxlength="500"
                    placeholder="Un repère, un horaire, une consigne…"></textarea>
        </label>

        <fieldset class="pay-choice">
          <legend>Comment souhaitez-vous régler&nbsp;?</legend>

          <label class="pay-opt" data-pay-delivery>
            <input type="radio" name="pay_mode" value="delivery" checked>
            <span>
              <strong>À la livraison</strong>
              Espèces ou Mobile Money au moment de la remise. Vous ne payez
              rien avant d'avoir la paire en main.
            </span>
          </label>

          <label class="pay-opt" data-pay-transfer>
            <input type="radio" name="pay_mode" value="transfer">
            <span>
              <strong>Par transfert Mobile Money</strong>
              L'atelier vous envoie son numéro MTN MoMo, Moov ou Wave sur
              WhatsApp. Obligatoire pour le sur-mesure, qui engage la matière.
            </span>
          </label>

          <p class="field__hint" data-bespoke-notice hidden>
            Votre panier contient une pièce sur-mesure : le règlement à la
            livraison n'est pas proposé, car un acompte de
            {self.site['bespoke']['deposit']}&nbsp;% est demandé avant sa fabrication.
            Le solde se règle à la livraison.
          </p>
        </fieldset>

        <button class="btn btn--full" type="submit" data-checkout-submit>
          Valider ma commande
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </button>

        <p class="status" data-checkout-status role="status" hidden></p>

        <p class="summary__note">
          En validant, vous acceptez d'être recontacté sur WhatsApp pour la confirmation
          et le suivi de la livraison, ainsi que nos
          <a href="cgv.html">conditions de vente</a>. Vos informations sont
          traitées comme décrit dans la page
          <a href="donnees-personnelles.html">données personnelles</a>.
          Aucune donnée bancaire ne transite par nos serveurs.
        </p>
      </form>
    </div>

    <aside class="shop-aside">
      <div class="summary">
        <h2>Votre commande</h2>
        <dl data-checkout-recap></dl>
        <div class="summary__total">
          <span>Sous-total</span>
          <span data-cart-subtotal>…</span>
        </div>
        <p class="summary__note">
          Le montant définitif, frais de livraison compris, vous est confirmé
          par l'atelier sur WhatsApp avant tout règlement.
        </p>
        <ul class="cfg-trust">
          <li><svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>L'atelier vous rappelle dans la journée</li>
          <li><svg aria-hidden="true"><use href="#i-shield"></use></svg>Annulation sans frais avant l'appel de l'atelier</li>
          <li><svg aria-hidden="true"><use href="#i-truck"></use></svg>Cotonou &amp; Abidjan en 48&nbsp;h</li>
        </ul>
      </div>
    </aside>
  </div>
</section>

"""
        # Le script du prestataire de paiement se chargeait sur toutes les
        # commandes, alors que PAYMENT_MODE vaut "offline" et que rien ne
        # l'appelle. C'est une requête vers un tiers, donc l'adresse IP du
        # client transmise à une société qui n'a aucune raison de la connaître,
        # pour une fonction inactive. On le rebranchera le jour de l'activation.
        if PAYMENT_MODE == "online":
            content += '\n<script src="https://cdn.kkiapay.me/k.js"></script>'

        self.page(
            "checkout.html", content=content,
            title="Commande | Yem's",
            description="Laissez votre adresse de livraison. L'atelier vous rappelle "
                        "dans la journée pour confirmer et convenir du règlement.",
            extra_css=("checkout",), extra_js=("checkout",),
        )

    def build_confirmation(self):
        content = f"""<section class="section section--top cta grain" style="min-height:70svh;display:grid;place-items:center">
  <div class="container">
    <div class="done">
      <span class="eyebrow eyebrow--center" data-reveal>Commande enregistrée</span>
      <h1 style="margin-top:var(--sp-4);font-size:var(--fs-3xl)" data-lines>
        C'est noté.<br>L'atelier s'en occupe.
      </h1>

      <p class="done__ref" data-order-ref>…</p>

      <p class="lede mx-auto text-center" data-reveal data-done-message>
        Notez cette référence quelque part, elle suffit à retrouver votre commande.
      </p>

      <div class="cta__actions" data-reveal>
        <a class="btn" href="selection.html">Continuer mes achats</a>
        <a class="btn btn--ghost" href="https://wa.me/{self.site['whatsapp']}" target="_blank" rel="noopener">
          <svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>
          Écrire à l'atelier
        </a>
      </div>
    </div>
  </div>
</section>

<script>
  // Référence et mode de règlement arrivent en paramètres d'URL, écrits par le
  // tunnel de commande. Les deux sont validés avant affichage : ils viennent
  // de la barre d'adresse, donc de l'utilisateur.
  (function () {{
    var params = new URLSearchParams(location.search);

    var ref = params.get('ref');
    var refEl = document.querySelector('[data-order-ref]');
    if (refEl) {{
      refEl.textContent = ref && /^[A-Z0-9-]{{6,24}}$/.test(ref)
        ? ref : 'Référence envoyée sur WhatsApp';
    }}

    var messages = {{
      online: "Votre paiement est enregistré. L'atelier vous écrit sur WhatsApp "
            + "dans la journée pour confirmer la date de livraison.",
      delivery: "Vous n'avez rien payé, et c'est normal. L'atelier vous appelle "
              + "dans la journée pour confirmer, puis vous réglez au moment où "
              + "on vous remet la paire : espèces ou Mobile Money.",
      transfer: "L'atelier vous écrit sur WhatsApp dans la journée avec son "
              + "numéro Mobile Money. Une pièce en stock part dès le paiement "
              + "reçu ; une pièce sur-mesure entre en fabrication dès l'acompte reçu."
    }};

    var mode = params.get('mode');
    var msgEl = document.querySelector('[data-done-message]');
    if (msgEl && messages[mode]) {{
      msgEl.textContent = 'Gardez cette référence. ' + messages[mode];
    }}
  }})();
</script>"""

        self.page(
            "commande-confirmee.html", content=content,
            title="Commande confirmée | Yem's",
            description="Votre commande Yem's est enregistrée. L'atelier vous contacte sur WhatsApp.",
            extra_css=("checkout",),
        )


    def build_a_venir(self):
        """
        Une page pour tout ce qui n'est pas encore montrable.

        Abou l'a demandé ainsi, et il a raison : huit fiches avec un fond beige
        et un nom de produit donnent l'impression d'une boutique vide. Une page
        qui annonce donne l'impression d'une maison qui prépare quelque chose.

        Aucun nom de pièce n'y figure. Annoncer « Loafer Ouidah, 88 000 F »
        sans pouvoir le montrer, c'est prendre un engagement sur un prix et un
        modèle qui peuvent encore bouger.

        Refonte « maison » : le registre des pages de rayon (boutique.css).
        Le titre à gauche, deux phrases, puis l'image de l'atelier et trois
        façons d'agir en liste à filets (plus de cartes) ; WhatsApp en bouton
        plein, le sur-mesure et la sélection en liens.
        """
        atelier = sum(1 for p in self.a_venir if p.get("origine") == "atelier")
        nombre = ("Une pièce est" if atelier == 1
                  else "%s pièces sont" % nombre_en_lettres(atelier))
        wa = "https://wa.me/%s?text=%s" % (
            self.site["whatsapp"],
            "Bonjour%2C%20je%20voudrais%20voir%20les%20pi%C3%A8ces%20de%20l%27atelier.")

        # Les pièces de l'atelier qui ont déjà une image (la ceinture et le
        # portefeuille) se montrent ici, sans prix ni panier : le prix n'est
        # pas engagé tant que la pièce n'est pas en production. Le nom générique
        # (« La ceinture ») respecte la règle ci-dessus.
        montrables = [p for p in self.a_venir
                      if p.get("origine") == "atelier" and p.get("images")]
        pieces = ""
        if montrables:
            figures = "\n".join(
                '      <figure class="venir-piece">\n'
                '        <div class="venir-piece__image">\n          %s\n        </div>\n'
                '        <figcaption>%s</figcaption>\n'
                '      </figure>'
                % (picture(p, "", lazy=i > 0, sizes="(max-width: 899px) 46vw, 30vw"),
                   {"ceintures": "La ceinture", "portefeuilles": "Le portefeuille"}
                   .get(p.get("category"), "Une pièce de l'atelier"))
                for i, p in enumerate(montrables))
            pieces = f"""
<section class="venir-pieces" aria-label="Pièces en préparation">
  <div class="container container--wide">
    <div class="venir-pieces__grille">
{figures}
    </div>
  </div>
</section>
"""

        chargement_atelier = ('loading="lazy"' if montrables
                              else 'fetchpriority="high"')
        content = f"""<section class="rayon-page rayon-page--seule" id="a-venir" aria-labelledby="rayon-titre">
  <div class="container container--wide">
    <div class="rayon-tete">
      <h1 id="rayon-titre">Les pièces de l'atelier arrivent</h1>
      <div class="rayon-tete__texte">
        <p class="rayon-tete__lede">
          À Cotonou, notre atelier façonne une ligne de souliers et de
          maroquinerie. Chaque pièce aura ici sa fiche et son prix dès
          qu'elle sera en production.
        </p>
        <p class="rayon-tete__ligne">
          {nombre} en préparation&nbsp;: des souliers cousus à la main, une
          ceinture et un portefeuille taillés dans les mêmes peaux.
        </p>
      </div>
    </div>
  </div>
</section>
{pieces}
<section class="bloc groupe" aria-labelledby="venir-titre">
  <div class="container container--wide atelier-rayon atelier-rayon--haut">
    <figure class="atelier-rayon__image" data-reveal>
      <picture>
        <source type="image/webp"
                sizes="(max-width: 899px) 92vw, 50vw"
                srcset="assets/img/atelier-couture-500.webp 500w,
                        assets/img/atelier-couture-800.webp 800w,
                        assets/img/atelier-couture.webp 1200w">
        <img src="assets/img/atelier-couture-800.jpg"
             sizes="(max-width: 899px) 92vw, 50vw"
             srcset="assets/img/atelier-couture-500.jpg 500w,
                     assets/img/atelier-couture-800.jpg 800w,
                     assets/img/atelier-couture.jpg 1200w"
             width="1200" height="800" {chargement_atelier} decoding="async"
             alt="Des mains d'artisan piquent à l'alène la trépointe d'un soulier en cuir brun">
      </picture>
      {mention_ia()}
    </figure>

    <div class="atelier-rayon__texte">
      <h2 id="venir-titre" data-lines>En attendant</h2>
      <dl class="venir-liste">
        <div data-reveal>
          <dt>Être prévenu</dt>
          <dd>Écrivez à l'atelier sur WhatsApp&nbsp;: nous vous envoyons les
          photos et la fiche de chaque pièce dès qu'elle est prête.</dd>
        </div>
      </dl>
      <div class="venir-actions">
        <a class="btn" href="{wa}" target="_blank" rel="noopener">
          <svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>
          Écrire à l'atelier
        </a>
        <a class="lien" href="configurateur.html">
          Composer ma paire sur mesure
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
        <a class="lien" href="selection.html">
          Voir ce qui est disponible
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
      </div>
    </div>
  </div>
</section>"""

        self.page(
            "a-venir.html", content=content, current="a-venir",
            body_class="page-rayon",
            extra_css=("boutique",),
            title="Les pièces de l'atelier arrivent | Yem's",
            # Elle disait « Découvrez les pièces » sur une page qui n'en montre
            # aucune : la description d'un résultat de recherche doit dire ce
            # qu'on trouvera en cliquant.
            description="La ligne cousue main de l'atelier de Cotonou est en préparation. "
                        "Écrivez à l'atelier pour voir les pièces de près ou être "
                        "prévenu de leur mise en ligne.",
        )

    def groupe_atelier(self):
        """
        La ligne de l'atelier, sur la boutique, tant qu'elle est en préparation.

        Aucune vignette, aucun nom de pièce, aucun prix : la page « Ce qui se
        prépare » explique pourquoi. Le nombre de pièces vient des données
        (les pièces « a_venir » d'origine atelier), le délai du sur-mesure
        aussi. L'image est un visuel d'ambiance de l'atelier, pas une pièce à
        vendre : son texte alternatif ne nomme aucun modèle.
        """
        atelier = [p for p in self.a_venir if p.get("origine") == "atelier"]
        if not atelier:
            return ""
        n = len(atelier)
        compte = ("Une pièce en préparation" if n == 1 else
                  "%s pièces en préparation" % nombre_en_lettres(n))
        o = ORIGINES.get("atelier") or {}
        bespoke = self.site["bespoke"]
        formes = nombre_en_lettres(len(bespoke["shapes"])).lower()
        return f"""<section class="bloc groupe" id="atelier" aria-labelledby="groupe-atelier">
  <div class="container container--wide">
    <div class="groupe__tete">
      <h2 id="groupe-atelier" data-lines>L'atelier</h2>
      <p class="groupe__compte">{compte} · {escape(o.get('court', ''))}</p>
      <a class="lien groupe__lien" href="a-venir.html">
        Ce qui se prépare
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
    </div>

    <div class="atelier-rayon">
      <figure class="atelier-rayon__image" data-reveal>
        <picture>
          <source type="image/webp"
                  sizes="(max-width: 899px) 92vw, 50vw"
                  srcset="assets/img/atelier-etabli-500.webp 500w,
                          assets/img/atelier-etabli-800.webp 800w,
                          assets/img/atelier-etabli.webp 1200w">
          <img src="assets/img/atelier-etabli-800.jpg"
               sizes="(max-width: 899px) 92vw, 50vw"
               srcset="assets/img/atelier-etabli-500.jpg 500w,
                       assets/img/atelier-etabli-800.jpg 800w,
                       assets/img/atelier-etabli.jpg 1200w"
               width="1200" height="800" fetchpriority="high" decoding="async"
               alt="Une paire de mocassins en cuir brun sur un établi de bois, près d'une bobine de fil et d'outils de cordonnier">
        </picture>
        {mention_ia()}
      </figure>

      <div class="atelier-rayon__texte" data-reveal style="--reveal-delay:80ms">
        <p>
          Des souliers et de la maroquinerie cousus main au point sellier, sur
          trépointe. La ligne est en préparation à Cotonou&nbsp;; nous la
          montrerons dès que chaque pièce pourra l'être telle qu'elle est.
        </p>
        <p class="atelier-rayon__ligne">{self.ligne_origine('atelier')}</p>
        <p>
          En attendant, l'atelier coud votre paire sur mesure&nbsp;: {formes}
          formes, votre cuir, votre pointure, {escape(bespoke['lead_days'])}.
        </p>
        <a class="lien" href="configurateur.html">
          Composer ma paire
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
      </div>
    </div>
  </div>
</section>"""

    def build_shop(self):
        """
        La boutique entière, sur une page.

        Un titre, deux phrases, puis un groupe par rayon : un filet, le nom du
        rayon, son nombre de modèles et son origine, un lien vers sa page, et
        la grille. La ligne de l'atelier suit, en préparation, avec ce qu'on
        peut déjà en faire (le sur-mesure). On termine par la question sur
        WhatsApp, comme l'accueil.

        Pas de nombre de pièces en stock : la disponibilité change depuis
        l'écran de l'atelier sans reconstruire le site (le Worker réécrit les
        pastilles), et un « 7 pièces en stock » figé finirait par être faux.
        Le nombre de modèles du rayon, lui, vient du catalogue.
        """
        rayons = [(c, self.by_category(c["slug"])) for c in self.categories]
        # Un rayon vide n'a pas de groupe : il est annoncé sur a-venir.html.
        rayons = [(c, produits) for c, produits in rayons if produits]
        # L'entretien ferme le catalogue : on vient pour les souliers, la
        # crème et les embauchoirs viennent après.
        rayons.sort(key=lambda r: r[0]["slug"] == "entretien")
        groupes = []
        for i, (cat, produits) in enumerate(rayons):
            n = len(produits)
            mot = "pièce" if cat["slug"] == "entretien" else "modèle"
            compte = "%d %s%s" % (n, mot, "s" if n > 1 else "")
            origines = {p.get("origine", "selection") for p in produits}
            if len(origines) == 1:
                court = (ORIGINES.get(next(iter(origines))) or {}).get("court")
                if court:
                    compte += " · " + escape(court)
            # La réserve sur les prix ferme la dernière grille.
            note = "\n\n" + self.note_prix() if i == len(rayons) - 1 else ""
            groupes.append(f"""<section class="bloc groupe" id="{cat['slug']}" aria-labelledby="groupe-{cat['slug']}">
  <div class="container container--wide">
    <div class="groupe__tete">
      <h2 id="groupe-{cat['slug']}" data-lines>{escape(cat['name'])}</h2>
      <p class="groupe__compte">{compte}</p>
      <a class="lien groupe__lien" href="{cat['slug']}.html">
        Voir le rayon
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
    </div>

{grid(produits, "", klass="rayon-grille", level=3, rare=False)}{note}
  </div>
</section>""")

        # Les deux origines et leurs garanties, l'atelier d'abord.
        lignes = []
        for o in (ORIGINES.get("atelier"), ORIGINES.get("selection")):
            if o:
                lignes.append("<strong>%s</strong>&nbsp;: %s." % (
                    escape(o["court"]),
                    escape(o["garantie"][:1].lower() + o["garantie"][1:])))

        entete = self.tete_rayon(
            "Le catalogue",
            "Les pièces en stock à Cotonou partent sous 72&nbsp;h. Chacune "
            "dit, au-dessus de son prix, si nous l'avons fabriquée ou choisie.",
            " ".join(lignes))
        tete = f"""<section class="rayon-page rayon-page--seule" aria-labelledby="rayon-titre">
  <div class="container container--wide">
{entete}
  </div>
</section>"""

        invitation = self.invitation(
            ident="invitation-titre",
            titre="Une question avant de commander&nbsp;?",
            phrase="L'atelier répond sur WhatsApp, du lundi au samedi, de 8&nbsp;h à 19&nbsp;h.",
            lien=(f'<a class="btn" href="https://wa.me/{self.site["whatsapp"]}'
                  '?text=Bonjour%2C%20j\'ai%20une%20question%20sur%20vos%20souliers." '
                  'target="_blank" rel="noopener">\n'
                  '      <svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>\n'
                  '      Écrire à l\'atelier\n'
                  '    </a>'),
        )

        # L'atelier ouvre la boutique (PRODUCT.md : l'atelier mène), en bande
        # compacte ; la sélection, achat immédiat, suit aussitôt.
        fil = breadcrumb([("Accueil", "index.html"), ("Boutique", None)])
        content = "\n\n".join([fil, tete, self.groupe_atelier()] + groupes + [invitation])

        self.page(
            "boutique.html", content=content, current="boutique",
            body_class="page-rayon",
            extra_css=("boutique",),
            title="La boutique : tout le catalogue | Yem's",
            description="Les pièces Yem's disponibles aujourd'hui à Cotonou. "
                        "Origine indiquée sur chacune, échange un an, livraison "
                        "au Bénin et en Côte d'Ivoire.",
        )

    def build_admin(self):
        """
        Écran de suivi des commandes, pour l'atelier.

        Rien n'est rendu ici : la page arrive vide et se remplit depuis
        /api/admin/orders. Aucune donnée client ne se trouve donc dans un
        fichier statique servi publiquement, et le jeton reste le seul
        gardien. La page est en noindex et n'est liée depuis nulle part.
        """
        filtres = "\n".join(
            '        <button class="chip" type="button" data-filter="%s"%s>%s</button>'
            % (val, ' aria-pressed="true"' if val == "" else ' aria-pressed="false"', libelle)
            for val, libelle in [
                ("", "Tout"), ("to_confirm", "À confirmer"), ("deposit", "Acompte reçu"),
                ("paid", "Payées"), ("in_workshop", "En atelier"),
                ("shipped", "Expédiées"), ("delivered", "Livrées"),
            ])

        content = f"""<section class="section section--top admin" id="admin">
  <div class="container container--wide">

    <div class="admin__head">
      <div>
        <span class="eyebrow">Atelier</span>
        <h1 class="page-title" style="margin-top:var(--sp-3)">Les commandes</h1>
      </div>
      <button class="btn btn--sm btn--quiet" type="button" data-refresh hidden>Actualiser</button>
    </div>

    <form class="admin__gate" data-gate>
      <label class="field">
        <span class="field__label">Mot de passe de l'atelier</span>
        <input type="password" name="token" autocomplete="current-password"
               required minlength="16" spellcheck="false">
        <span class="field__hint">Celui généré à l'installation. Il n'est gardé
          que le temps de l'onglet : refermez-le et il faudra le ressaisir.</span>
      </label>
      <button class="btn" type="submit">Ouvrir</button>
      <p class="admin__error" data-gate-error hidden></p>
    </form>

    <div class="admin__body" data-body hidden>

      <div class="admin__onglets" role="tablist">
        <button class="onglet" type="button" role="tab" data-onglet="commandes"
                aria-selected="true">Commandes</button>
        <button class="onglet" type="button" role="tab" data-onglet="catalogue"
                aria-selected="false">Catalogue</button>
      </div>

      <div data-panneau="commandes">
        <div class="admin__filters" role="group" aria-label="Filtrer par statut">
{filtres}
        </div>
        <p class="admin__count" data-count aria-live="polite"></p>
        <div class="admin__list" data-list></div>

        <details class="menage">
          <summary>Faire le ménage dans les anciennes commandes</summary>
          <div class="menage__corps">
            <p>
              Une commande livrée contient encore le nom, le téléphone et
              l'adresse de votre client. Les garder des années sans raison
              n'est ni utile ni prudent.
            </p>
            <p>
              <strong>Anonymiser</strong> efface ces coordonnées et conserve la
              commande : vos totaux de l'année restent justes. C'est ce qu'il
              faut faire dans presque tous les cas.
            </p>
            <form class="menage__form" data-menage>
              <label class="field">
                <span class="field__label">Anonymiser les commandes terminées avant le</span>
                <input type="date" name="before" required>
              </label>
              <button class="btn btn--sm btn--quiet" type="submit">Anonymiser</button>
            </form>
            <p class="menage__retour" data-menage-retour hidden></p>
          </div>
        </details>
      </div>

      <div data-panneau="catalogue" hidden>
        <p class="admin__count">
          Modifiez le prix, la disponibilité et la phrase de présentation.
          Laissez un champ vide pour revenir à la valeur d'origine.
        </p>
        <div class="admin__list" data-catalogue></div>
        <div class="journal" data-journal hidden>
          <h2 class="journal__titre">Dernières modifications</h2>
          <ul class="journal__liste" data-journal-liste></ul>
        </div>
      </div>

    </div>

  </div>
</section>"""

        self.page(
            "admin.html", content=content,
            title="Suivi des commandes | Yem's",
            description="Espace réservé à l'atelier.",
            extra_css=("admin",), extra_js=("admin",), noindex=True,
        )

    def build_404(self):
        """Page servie par Cloudflare quand aucune URL ne correspond."""
        content = f"""<section class="section section--top cta grain" style="min-height:72svh;display:grid;place-items:center">
  <div class="container">
    <div class="done">
      <span class="eyebrow eyebrow--center" data-reveal>Erreur 404</span>
      <h1 style="margin-top:var(--sp-4);font-size:var(--fs-3xl)" data-lines>
        Cette page n'existe pas.<br>Celles-ci, si.
      </h1>
      <p class="lede mx-auto text-center" data-reveal>
        Le lien est peut-être ancien, ou la pièce n'est plus au catalogue.
        L'atelier répond sur WhatsApp si vous cherchiez quelque chose de précis.
      </p>
      <div class="cta__actions" data-reveal>
        <a class="btn" href="/selection.html">
          Voir les souliers
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
        <a class="btn btn--ghost" href="/configurateur.html">Composer ma paire</a>
      </div>
      <p class="summary__note" style="margin-top:var(--sp-6)">
        <a href="/index.html">Retour à l'accueil</a> ·
        <a href="https://wa.me/{self.site['whatsapp']}" target="_blank" rel="noopener">Écrire à l'atelier</a>
      </p>
    </div>
  </div>
</section>"""

        self.page(
            "404.html", content=content,
            title="Page introuvable | Yem's",
            description="Cette page n'existe pas ou n'existe plus.",
            extra_css=("checkout",),
        )

        # Cette page peut être servie sous n'importe quelle URL, y compris
        # /produit/inexistant.html. Des chemins relatifs y chercheraient
        # /produit/assets/… : on les passe donc tous en absolu.
        path = os.path.join(ROOT, "404.html")
        html = read(path)
        html = re.sub(r'(href|src|srcset)="(?!/|https?:|data:|#|mailto:)', r'\1="/', html)
        write(path, html)

    # Les trois documents que le code du numérique béninois exige au minimum
    # d'une plateforme de commerce électronique : mentions légales, conditions
    # générales de vente, politique de confidentialité.
    # Pages écrites à la main dans templates/pages/, rendues telles quelles.
    # Les trois dernières sont les documents que le code du numérique béninois
    # exige au minimum d'une plateforme de commerce électronique.
    LEGALES = [
        ("service-client", "Service client | Yem's",
         "Livraison, échange, garanties, entretien et règlement. "
         "L'atelier répond sous 48 heures, du lundi au samedi."),
        ("mentions-legales", "Mentions légales | Yem's",
         "Éditeur, hébergeur et informations légales du site Yem's, "
         "atelier de souliers et de maroquinerie à Cotonou."),
        ("cgv", "Conditions générales de vente | Yem's",
         "Prix, commande, règlement, livraison, garanties, échange et "
         "remboursement. Les engagements de Yem's, écrits en entier."),
        ("donnees-personnelles", "Données personnelles | Yem's",
         "Ce que Yem's collecte, pourquoi, combien de temps, et qui y a accès. "
         "Aucun traceur publicitaire."),
        # Les CGV disent ce qui se passe quand on achète ; celle-ci dit ce qui
        # vaut pour tout visiteur : visuels générés, erreurs de prix, propriété
        # des contenus, responsabilité, droit applicable.
        ("conditions-utilisation", "Conditions d'utilisation | Yem's",
         "Usage du site Yem's : visuels générés par IA, exactitude des "
         "informations, propriété des contenus, responsabilité et droit "
         "applicable."),
    ]

    def build_pages_ecrites(self):
        """
        Génère les trois pages légales depuis templates/pages/.

        Elles ne passent pas par strip_notes : les encarts « à compléter » y
        sont VOLONTAIREMENT visibles. Une mention légale incomplète qu'on ne
        voit pas est une mention légale qui ne sera jamais complétée.
        """
        mois = ("janvier février mars avril mai juin juillet août septembre "
                "octobre novembre décembre").split()
        aujourdhui = datetime.date.today()
        maj = "%d %s %d" % (aujourdhui.day, mois[aujourdhui.month - 1], aujourdhui.year)

        for slug, title, description in self.LEGALES:
            gabarit = read(os.path.join(TPL, "pages", "%s.html" % slug))
            content = (gabarit
                       .replace("{{maj}}", maj)
                       .replace("{{whatsapp}}", self.site["whatsapp"])
                       .replace("{{domaine}}", SITE_URL.replace("https://", "") or "ce site")
                       .replace("{{base}}", ""))
            self.page("%s.html" % slug, content=content,
                      title=title, description=description,
                      extra_css=("legal",))

    # Termes qui, s'ils apparaissent sur une page, promettent au visiteur un
    # règlement par carte. Le site n'a le droit de les employer que si la
    # passerelle est réellement branchée.
    TERMES_CARTE = ("carte bancaire", "visa", "mastercard", "gim-uemoa",
                    "paiement par carte", "payer par carte")

    def controler_paiement(self):
        """
        Refuse de livrer un site qui annonce un moyen de règlement inactif.

        Ce contrôle existe parce que l'erreur a déjà été commise : le site a
        annoncé le paiement en ligne pendant que PAYMENT_MODE valait
        « offline ». Un visiteur arrivait au bout du tunnel pour découvrir
        qu'il fallait finalement rappeler l'atelier. Au-delà de la déception,
        annoncer un moyen de paiement qu'on n'accepte pas est une pratique
        commerciale trompeuse.

        Une relecture humaine ne rattrape pas ça : la mention se glisse dans
        une phrase de réassurance écrite six mois plus tôt. Une vérification
        automatique, si.
        """
        if PAYMENT_MODE == "online":
            print("\n  paiement : mode « online », la carte peut être annoncée")
            return

        fautes = []
        for chemin, _ in self.written:
            texte = read(os.path.join(ROOT, chemin))
            texte = re.sub(r"<!--.*?-->", "", texte, flags=re.S).lower()
            for terme in self.TERMES_CARTE:
                if terme in texte:
                    fautes.append((chemin, terme))

        if fautes:
            lignes = "\n".join("      %s : « %s »" % f for f in fautes)
            raise SystemExit(
                "\n!! Le site annonce un règlement par carte alors que "
                "PAYMENT_MODE vaut « %s ».\n%s\n\n"
                "   Soit la passerelle est active et il faut générer avec "
                "PAYMENT_MODE=online,\n"
                "   soit la mention doit disparaître." % (PAYMENT_MODE, lignes))
        print("\n  paiement : mode « %s », aucune promesse de carte sur le site"
              % PAYMENT_MODE)

    # Dossiers qui ne partent jamais en ligne (voir .assetsignore). Tout autre
    # fichier .html du dépôt est publié, écrit par ce script ou non.
    NON_PUBLIES = {"api", "data", "db", "docs", "node_modules", "templates", "tools"}

    def ecrire_csp(self):
        """
        Politique de sécurité du contenu (CSP), écrite dans _headers.

        Elle n'autorise que les scripts du site : ceux de assets/js, et les
        quelques scripts écrits dans les pages, reconnus à leur empreinte
        SHA-256. Un script injecté par un tiers (un nom de produit piégé, un
        champ mal échappé) n'a pas d'empreinte connue : le navigateur refuse
        de l'exécuter. C'est le filet sous toutes les autres protections.

        Les empreintes sont recalculées à chaque génération, sur les pages
        telles qu'elles partent en ligne. Modifier un script en ligne sans
        relancer ce script le ferait bloquer : c'est voulu, npm run deploy
        relance toujours le build avant d'envoyer.

        Un gestionnaire écrit dans un attribut (onclick="…", onload="…") ne
        peut pas être autorisé ainsi : la génération s'arrête s'il en
        réapparaît un, plutôt que de livrer une page dont un bouton ne
        répondrait plus. Passer par addEventListener dans un script.

        En mode « online », le domaine de KkiaPay est ajouté pour son widget.
        S'il ne s'ouvre pas, la console du navigateur indique, ligne
        « Refused to load… », le domaine à ajouter ici.
        """
        empreintes = set()
        fautes = []
        for dossier, sous_dossiers, fichiers in os.walk(ROOT):
            if dossier == ROOT:
                sous_dossiers[:] = [d for d in sous_dossiers
                                    if not d.startswith(".") and d not in self.NON_PUBLIES]
            for nom in fichiers:
                if not nom.endswith(".html"):
                    continue
                chemin = os.path.join(dossier, nom)
                texte = re.sub(r"<!--.*?-->", "", read(chemin), flags=re.S)
                for attributs, corps in re.findall(
                        r"<script\b([^>]*)>(.*?)</script\s*>", texte, flags=re.S | re.I):
                    if re.search(r"\bsrc\s*=", attributs, re.I):
                        continue
                    genre = re.search(r"""\btype\s*=\s*["']?([^"'\s>]+)""", attributs, re.I)
                    if genre and genre.group(1).lower() not in (
                            "text/javascript", "application/javascript", "module"):
                        continue          # JSON-LD, données : jamais exécutés
                    empreintes.add("'sha256-%s'" % base64.b64encode(
                        hashlib.sha256(corps.encode("utf-8")).digest()).decode())
                balises = re.sub(r"<script\b.*?</script\s*>", "", texte, flags=re.S | re.I)
                for m in re.finditer(r"<[a-zA-Z][^>]*?\s(on[a-z]+)\s*=", balises):
                    fautes.append("%s : attribut %s"
                                  % (os.path.relpath(chemin, ROOT), m.group(1)))
                if re.search(r"""(?:href|src|action)\s*=\s*["']?\s*javascript:""", balises, re.I):
                    fautes.append("%s : adresse javascript:" % os.path.relpath(chemin, ROOT))

        if fautes:
            raise SystemExit(
                "\n!! Code JavaScript écrit dans un attribut : la CSP le bloquerait.\n"
                + "\n".join("      " + f for f in sorted(set(fautes)))
                + "\n\n   Le déplacer dans un script (addEventListener).")

        en_ligne = PAYMENT_MODE == "online"
        kkiapay = " https://*.kkiapay.me" if en_ligne else ""
        csp = "; ".join([
            "default-src 'self'",
            "script-src 'self' %s%s" % (" ".join(sorted(empreintes)),
                                        " https://cdn.kkiapay.me" if en_ligne else ""),
            # Les attributs style="" sont nombreux et ne peuvent pas exécuter
            # de code : les autoriser ne rouvre pas la porte aux scripts.
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data:" + kkiapay,
            "media-src 'self'",
            "connect-src 'self'" + kkiapay,
            "frame-src " + ("https://*.kkiapay.me" if en_ligne else "'none'"),
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'self'",
        ])

        # Cloudflare ignore, sans faire échouer le déploiement, toute ligne de
        # _headers de plus de 2 000 caractères : la CSP disparaîtrait en silence.
        ligne = "  Content-Security-Policy: " + csp
        if len(ligne) > 2000:
            raise SystemExit("!! CSP de %d caractères : Cloudflare ignore les lignes "
                             "de plus de 2 000. Réduire le nombre de scripts en ligne."
                             % len(ligne))

        chemin = os.path.join(ROOT, "_headers")
        texte = read(chemin)
        nouveau, n = re.subn(r"^  Content-Security-Policy: .*$",
                             lambda _: ligne, texte, flags=re.M)
        if n != 1:
            raise SystemExit("!! _headers : une ligne « Content-Security-Policy » "
                             "(et une seule) est attendue sous /*")
        if nouveau != texte:
            write(chemin, nouveau)
        print("\n  CSP : %d script(s) en ligne autorisé(s) par empreinte, mode « %s »"
              % (len(empreintes), PAYMENT_MODE))

    def build_sitemap(self):
        """
        sitemap.xml, déduit des pages effectivement écrites.

        Les priorités ne sont pas décoratives : elles disent à un robot dans
        quel ordre revisiter le site. L'accueil et les deux lignes bougent
        souvent, une fiche produit rarement, le sur-mesure jamais.
        """
        if not SITE_URL:
            print("\n  note : site.url est vide, sitemap.xml non généré")
            return

        def priorite(chemin):
            if chemin == "index.html":
                return "1.0", "weekly"
            if chemin in ("selection.html", "boutique.html", "a-venir.html"):
                return "0.9", "weekly"
            if chemin.startswith("produit/"):
                return "0.7", "monthly"
            return "0.6", "monthly"

        lignes = ['<?xml version="1.0" encoding="UTF-8"?>',
                  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for chemin in self.indexables:
            prio, freq = priorite(chemin)
            lignes += ["  <url>",
                       "    <loc>%s</loc>" % escape(url_absolue(chemin), quote=False),
                       "    <changefreq>%s</changefreq>" % freq,
                       "    <priority>%s</priority>" % prio,
                       "  </url>"]
        lignes.append("</urlset>")
        write(os.path.join(ROOT, "sitemap.xml"), "\n".join(lignes) + "\n")
        print("\n  sitemap.xml : %d adresses" % len(self.indexables))

    def run(self):
        if os.path.isdir(OUT_PRODUCTS):
            shutil.rmtree(OUT_PRODUCTS)

        self.build_home()
        self.build_about()
        for cat in self.categories:
            # Générer une page catégorie vide reviendrait à créer une impasse :
            # le visiteur clique, ne trouve rien, et repart.
            if self.by_category(cat["slug"]):
                self.build_category(cat)
        for product in self.products:
            self.build_product(product)

        self.build_a_venir()
        self.build_shop()
        self.build_configurator()
        self.build_cart()
        self.build_checkout()
        self.build_confirmation()
        self.build_admin()
        self.build_pages_ecrites()
        self.build_404()
        self.build_sitemap()

        print("%d pages générées :\n" % len(self.written))
        for path, size in self.written:
            print("  %-42s %5d Ko" % (path, size // 1024 or 1))

        self.controler_paiement()
        self.ecrire_csp()

        orphans = [c["slug"] for c in self.categories if not self.by_category(c["slug"])]
        if orphans:
            print("\n  note : catégories sans produit -> %s" % ", ".join(orphans))
        todo = [p["slug"] for p in self.products if not p.get("images")]
        if todo:
            print("  note : produits sans photo → %s" % ", ".join(todo))


if __name__ == "__main__":
    Builder().run()
