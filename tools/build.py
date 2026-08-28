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

import datetime
import hashlib
import json
import os
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
    "green": ("badge--green", "Au Bénin",     "En stock à Cotonou, expédié sous 72 h"),
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

def picture(product, base, index=0, lazy=True, sizes=None):
    """<picture> WebP + JPEG, ou placeholder beige si la photo manque."""
    images = product.get("images") or []
    if not images:
        return ('<div class="pshot__empty">'
                '<span class="pshot__note">Photo à venir</span></div>')

    img = images[index]
    loading = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    attr_sizes = ' sizes="%s"' % sizes if sizes else ""
    return (
        '<picture>\n'
        '            <source srcset="%sassets/img/%s.webp" type="image/webp"%s>\n'
        '            <img src="%sassets/img/%s.jpg" width="%d" height="%d"%s\n'
        '                 alt="%s">\n'
        '          </picture>'
        % (base, img["file"], attr_sizes,
           base, img["file"], img["w"], img["h"], loading,
           escape(img["alt"], quote=True))
    )


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


def product_card(product, base, delay=0, level=3):
    """Carte produit, telle qu'elle apparaît dans une grille."""
    href = "%sproduit/%s.html" % (base, product["slug"])
    style = ' style="--reveal-delay:%dms"' % delay if delay else ""
    empty = "" if product.get("images") else " pshot--empty"
    return f"""      <article class="pcard" data-reveal{style} data-piece="{product['slug']}">
        <a href="{href}" aria-label="Découvrir {escape(product['name'])}">
          <div class="pshot{empty}" data-shot>
            {badge(product['status'], 'pshot__badge', slug=product['slug'])}
            {picture(product, base)}
          </div>
        </a>
        <div class="pcard__body">
          <div class="pcard__row">
            <h{level} class="pcard__name">{escape(product['name'])}</h{level}>
            <span class="pcard__price" data-prix="{product['slug']}">{price(product['price'])}</span>
          </div>
          <p class="pcard__desc" data-court="{product['slug']}">{product['short']}</p>
          {origine_marque(product)}
        </div>
      </article>"""


def grid(products, base, klass="collections__grid", level=3):
    if not products:
        return """      <div class="empty-state">
        <p class="display">Cette ligne arrive bientôt.</p>
        <p class="text-muted">Écrivez-nous sur WhatsApp pour être prévenu du lancement.</p>
      </div>"""
    cards = [product_card(p, base, delay=i * 90, level=level) for i, p in enumerate(products)]
    return '    <div class="%s">\n%s\n    </div>' % (klass, "\n\n".join(cards))


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
        self.products = [p for p in self.data["products"] if not p.get("a_venir")]
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
             extra_css=(), extra_js=(), noindex=False):
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
        html = version_assets(html, ROOT)
        write(os.path.join(ROOT, path), html)
        self.written.append((path, len(html.encode())))
        # Le sitemap se déduit de ce qui a réellement été écrit, jamais d'une
        # liste tenue à la main : une liste manuelle finit toujours par
        # annoncer une page supprimée ou par oublier une page ajoutée.
        if not noindex and path not in TUNNEL:
            self.indexables.append(path)

    # ── les trois types de page ──────────────────────────────────────

    def build_home(self):
        body = read(os.path.join(TPL, "pages", "index.html"))
        featured = [p for p in self.products if p.get("featured")]
        body = fill(body, base="", whatsapp=self.site["whatsapp"],
                    featured_grid=grid(featured, ""))
        self.page(
            "index.html",
            content=body,
            title="Yem's : souliers et maroquinerie cousus main | Différents par les détails",
            description=("Yem's : souliers, ceintures et portefeuilles cousus à la main à "
                         "Cotonou. Point sellier, cuir pleine fleur, semelle ressemelable. "
                         "Sélection disponible à Cotonou, sur-mesure en 15 jours, livré au Bénin et en Côte d'Ivoire."),
            og_title="Yem's. Personne ne verra la couture. Tout le monde verra la différence.",
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

    def build_category(self, cat):
        products = self.by_category(cat["slug"])
        content = f"""<section class="section section--top" id="{cat['slug']}">
  <div class="container">
    <div class="section-head section-head--split" data-reveal>
      <div>
        <span class="eyebrow">{cat['eyebrow']}</span>
        <h1 class="page-title" style="margin-top:var(--sp-4)" data-lines>{cat['heading']}</h1>
      </div>
      <p class="lede" style="max-width:40ch">{cat['lede']}</p>
    </div>

{grid(products, "", klass="shop-grid", level=2)}
  </div>
</section>

<div class="seam" data-seam aria-hidden="true">
  <svg viewBox="0 0 1440 160" preserveAspectRatio="none">
    <defs>
      <mask id="seam-cat">
        <path class="seam__reveal" pathLength="1" d="M0 40 C 300 40, 380 126, 720 126 S 1140 40, 1440 40"/>
      </mask>
    </defs>
    <path class="seam__thread" mask="url(#seam-cat)" d="M0 40 C 300 40, 380 126, 720 126 S 1140 40, 1440 40"/>
  </svg>
</div>

<section class="section cta grain">
  <div class="container">
    <span class="eyebrow eyebrow--center" data-reveal>Rien ne vous va exactement ?</span>
    <h2 style="margin-top:var(--sp-4)" data-reveal>C'est précisément<br>le sur-mesure</h2>
    <p class="lede mx-auto text-center" style="margin-top:var(--sp-5)" data-reveal>
      Composez en deux minutes, la facture s'affiche à l'écran, l'atelier confirme la
      date sur WhatsApp. Vous ne payez rien avant cette confirmation.
    </p>
    <div class="cta__actions" data-reveal>
      <a class="btn" href="configurateur.html">
        Ouvrir le configurateur
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
    </div>
  </div>
</section>"""

        crumb = breadcrumb([("Accueil", "index.html"), (cat["name"], None)])
        self.page(
            "%s.html" % cat["slug"],
            content=crumb + "\n\n" + content,
            title="%s | Yem's" % cat["title"],
            description=cat["description"],
            current=cat["slug"],
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
        if images:
            main_shot = ('<div class="pshot" data-shot>%s\n          %s\n        </div>'
                         % (badge(product["status"], "pshot__badge"),
                            picture(product, base, 0, lazy=False)))
            thumbs = ""
            if len(images) > 1:
                thumbs = '\n      <div class="gallery__thumbs">\n' + "\n".join(
                    '        <div class="pshot">%s</div>' % picture(product, base, i)
                    for i in range(1, len(images))
                ) + "\n      </div>"
        else:
            main_shot = ('<div class="pshot pshot--empty" data-shot>%s'
                         '<span class="pshot__note">Photo à venir</span></div>'
                         % badge(product["status"], "pshot__badge"))
            thumbs = ""

        # pointures
        sizes = ""
        if product.get("sizes"):
            buttons = "\n".join(
                '          <button class="size" type="button" data-size="%d">%d</button>' % (s, s)
                for s in product["sizes"])
            sizes = f"""        <div class="picker">
          <span class="picker__label">Pointure</span>
          <div class="picker__row">
{buttons}
          </div>
          <p class="picker__help">Entre deux&nbsp;? Prenez la plus grande, l'atelier ajuste au montage.</p>
        </div>"""

        # couleurs
        colors = ""
        if product.get("colors"):
            swatches = "\n".join(
                '          <button class="swatch swatch--btn" type="button" '
                'style="background:%s" data-color="%s" aria-label="%s"></button>'
                % (c["hex"], escape(c["name"], quote=True), escape(c["name"], quote=True))
                for c in product["colors"])
            colors = f"""        <div class="picker">
          <span class="picker__label">Cuir</span>
          <div class="picker__row">
{swatches}
          </div>
          <p class="picker__help" data-color-label>Choisissez une teinte</p>
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
        for acc in self.site.get("accordions", []):
            panels.append((acc["title"], "<p>%s</p>" % acc["body"]))

        details = ""
        if panels:
            items = "\n".join(f"""      <details>
        <summary>{title}</summary>
        <div class="faq__body">{body}</div>
      </details>""" for title, body in panels)
            details = f"""
<section class="section">
  <div class="container">
    <div class="section-head section-head--center" data-reveal>
      <span class="eyebrow eyebrow--center">Le détail qui compte</span>
      <h2>Ce qu'on ne voit pas<br>de loin</h2>
    </div>

    <div class="faq" data-reveal style="--reveal-delay:100ms">
{items}
    </div>
  </div>
</section>"""

        # appel à l'action : sur-mesure seul, ou panier + sur-mesure
        if product.get("bespoke_only"):
            actions = f"""        <a class="btn btn--full" href="{base}configurateur.html">
          Configurer sur mes mesures
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
        </button>
        <a class="btn btn--ghost btn--full" href="{base}configurateur.html"
           style="margin-top:var(--sp-3)">La version sur-mesure</a>"""

        related = [p for p in self.by_category(product["category"])
                   if p["slug"] != product["slug"]][:3]
        related_block = ""
        if related:
            related_block = f"""
<section class="section section--light">
  <div class="container">
    <div class="section-head section-head--split" data-reveal>
      <div>
        <span class="eyebrow">La même construction</span>
        <h2 style="margin-top:var(--sp-4)">Les autres formes</h2>
      </div>
      <a class="link-underline" href="{base}{cat['slug']}.html">
        Toute la collection
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
    </div>

{grid(related, base, klass='shop-grid')}
  </div>
</section>"""

        content = f"""{breadcrumb([("Accueil", base + "index.html"),
                                  (cat["name"], base + cat["slug"] + ".html"),
                                  (product["name"], None)])}

<section class="section section--top">
  <div class="container product">
    <div class="product__gallery" data-reveal>
      {main_shot}{thumbs}
    </div>

    <div class="product__info" data-reveal style="--reveal-delay:120ms">
      <span class="eyebrow">La ligne {escape(cat['name'])}</span>
      <h1 class="product__name">{escape(product['name'])}</h1>
      {badge(product['status'], long=True, slug=product['slug'])}
      <p class="product__price"><span data-prix="{product['slug']}">{price(product['price'])}</span>
        <small>FCFA · livraison 48 h Cotonou &amp; Abidjan</small></p>
      <p class="lede" data-court="{product['slug']}">{product['short']}</p>
      {origine_marque(product, long=True)}
      <p class="lede" style="margin-top:var(--sp-3)">{product['pitch']}</p>

      <div class="product__pickers">
{colors}
{sizes}
      </div>

      <div class="product__actions">
{actions}
      </div>

      <dl class="product__specs">
{specs}
      </dl>

      <ul class="product__reassure">
        <li><svg aria-hidden="true"><use href="#i-shield"></use></svg>1 retouche offerte, puis remboursement intégral</li>
        <li><svg aria-hidden="true"><use href="#i-card"></use></svg>Carte d'authenticité numérotée</li>
        <li><svg aria-hidden="true"><use href="#i-truck"></use></svg>Cotonou &amp; Abidjan en 48 h</li>
      </ul>
    </div>
  </div>
</section>
{details}{related_block}"""

        self.page(
            "produit/%s.html" % product["slug"],
            content=content,
            title="%s, %s | Yem's" % (product["name"], cat["name"]),
            description=product["short"],
            og_type="product",
            og_image=images[0]["file"] if images else None,
            current=cat["slug"],
            depth=1,
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
                return ('<span class="cfg-opt__shot pshot--empty">'
                        '<span class="pshot__note">Photo à venir</span></span>')
            return ('<span class="cfg-opt__shot"><img src="assets/img/%s.jpg" '
                    'width="400" height="275" loading="lazy" decoding="async" alt="%s"></span>'
                    % (o["image"], escape(o["name"], quote=True)))

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

        def line(key, label):
            return (f'          <div class="spec-row" data-line="{key}" data-empty>'
                    f'<dt>{label}</dt>'
                    f'<dd><em data-extra></em><span data-value>À choisir</span></dd></div>')

        content = f"""{breadcrumb([("Accueil", "index.html"), ("L'atelier sur-mesure", None)])}

<section class="section section--top">
  <div class="container">
    <div class="section-head" data-reveal style="max-width:44ch">
      <span class="eyebrow">L'atelier</span>
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
            <p class="cfg-step__hint">Pleine fleur, tannage végétal. Il foncera et se creusera avec les années, c'est voulu.</p>
          </div>
{leathers}

          <figure class="cfg-film">
            <video autoplay muted loop playsinline preload="none"
                   poster="assets/img/cuirs-poster.jpg">
              <source src="assets/video/cuirs.webm" type="video/webm">
              <source src="assets/video/cuirs.mp4" type="video/mp4">
            </video>
            <figcaption>Illustration&nbsp;: les quatre familles de grain, du plus marqué au velours. Le vrai cuir de l'atelier se voit mieux en main que sur un écran, demandez un échantillon sur WhatsApp avant de trancher.</figcaption>
          </figure>
        </section>

        <section class="cfg-step">
          <div class="cfg-step__head">
            <span class="cfg-step__num">03</span>
            <h2>Le fil</h2>
            <p class="cfg-step__hint">Lin ciré, quatre teintes. Ton sur ton, la couture se devine. Contrastée, elle se voit à trois mètres. L'atelier vous demandera votre choix au moment de confirmer.</p>
          </div>

          <figure class="cfg-film">
            <video autoplay muted loop playsinline preload="none"
                   poster="assets/img/fils-poster.jpg">
              <source src="assets/video/fils.webm" type="video/webm">
              <source src="assets/video/fils.mp4" type="video/mp4">
            </video>
            <figcaption>Illustration&nbsp;: espresso, cognac, noir, sable. Les quatre teintes proposées, sur du lin ciré.</figcaption>
          </figure>
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
{line("initials", "Initiales")}
          </dl>

          <div class="cfg-total">
            <span class="cfg-total__label">Total</span>
            <span class="cfg-total__value" data-total>…</span>
          </div>

          <button class="btn btn--full" type="button" data-cfg-add data-cart="panier.html" disabled>
            Ajouter au panier
            <svg aria-hidden="true"><use href="#i-bag"></use></svg>
          </button>

          <p class="cfg-card__foot">
            Rien à payer maintenant. L'atelier vous écrit dans la journée pour
            confirmer la date, puis vous versez un acompte de {cfg['deposit']}&nbsp;% :
            Mobile Money MTN ou Moov, Wave, ou en espèces. Le solde à la livraison.
          </p>

          <ul class="cfg-trust">
            <li><svg aria-hidden="true"><use href="#i-needle"></use></svg>Point sellier main, une retouche offerte</li>
            <li><svg aria-hidden="true"><use href="#i-card"></use></svg>Carte d'authenticité numérotée</li>
            <li><svg aria-hidden="true"><use href="#i-truck"></use></svg>Livraison 48&nbsp;h après sortie d'atelier</li>
          </ul>
        </div>
      </aside>
    </div>
  </div>

  <div class="cfg-bar">
    <span class="cfg-bar__total">
      <span data-total>…</span>
      <span class="cfg-bar__label">Cousue à la commande, {cfg['lead_days']}</span>
    </span>
    <button class="btn btn--sm" type="button" data-cfg-add data-cart="panier.html" disabled>Ajouter</button>
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
            title="Configurateur sur-mesure | Yem's",
            description="Composez votre paire sur-mesure : forme, cuir, semelle, pointure "
                        "et initiales. Prix en direct, %s, acompte %d %% à la commande."
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
      <div class="section-head" data-reveal>
        <span class="eyebrow">Votre sélection</span>
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
        <p class="summary__note">
          Livraison offerte au Bénin et en Côte d'Ivoire. Les frais pour les autres
          pays s'affichent à l'étape suivante.
        </p>
        <p class="summary__note" data-deposit-notice hidden>
          Votre panier contient une pièce sur-mesure : seul l'acompte de
          {self.site['bespoke']['deposit']}&nbsp;% est prélevé maintenant, le solde à la livraison.
        </p>
        <a class="btn btn--full" href="checkout.html">
          Passer commande
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
        <ul class="cfg-trust">
          <li><svg aria-hidden="true"><use href="#i-shield"></use></svg>1 retouche offerte, puis remboursement intégral</li>
          <li><svg aria-hidden="true"><use href="#i-card"></use></svg>Rien à payer maintenant, réglé à la remise</li>
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
        <span class="eyebrow">Dernière étape</span>
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
            <input name="phone" type="tel" required autocomplete="tel"
                   placeholder="97 00 00 00">
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
              L'atelier vous envoie son numéro MTN ou Moov sur WhatsApp.
              Nécessaire pour le sur-mesure, qui engage la matière.
            </span>
          </label>

          <p class="field__hint" data-bespoke-notice hidden>
            Votre panier contient une pièce sur-mesure : seul le transfert est
            possible, avec un acompte de {self.site['bespoke']['deposit']}&nbsp;%.
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
          <li><svg aria-hidden="true"><use href="#i-shield"></use></svg>Remboursement intégral si la paire ne va pas</li>
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
              + "numéro Mobile Money. Le travail commence dès que l'acompte "
              + "est arrivé."
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
        """
        atelier = sum(1 for p in self.a_venir if p.get("origine") == "atelier")

        content = f"""<section class="section section--top" id="a-venir">
  <div class="container container--narrow">
    <div class="section-head" data-reveal>
      <span class="eyebrow">L'atelier</span>
      <h1 class="page-title" style="margin-top:var(--sp-3)">Ce qui se prépare</h1>
      <p class="lede">
        La ligne cousue main n'est pas encore en ligne. Pas parce qu'elle
        n'existe pas, mais parce qu'on refuse de la montrer avec des images
        qui ne sont pas les nôtres.
      </p>
    </div>

    <div class="story__turn" data-reveal style="margin-top:var(--sp-6)">
      <p>
        {atelier} pièces sortent de l'atelier de Cotonou : des souliers cousus
        à la main, une ceinture et un portefeuille taillés dans les mêmes peaux.
        <strong>Elles seront en ligne dès qu'elles auront été photographiées
        chez nous, telles qu'elles sont.</strong>
      </p>
    </div>

    <div class="grid grid--3" style="margin-top:var(--sp-7)">
      <article class="card" data-reveal>
        <span class="card__num">01</span>
        <h2>Vous voulez voir avant</h2>
        <p>
          Passez à l'atelier. Les pièces existent, elles se prennent en main,
          et c'est de loin la meilleure façon de juger une couture.
        </p>
      </article>
      <article class="card" data-reveal style="--reveal-delay:90ms">
        <h2>Vous savez déjà ce que vous voulez</h2>
        <p>
          Écrivez-nous. On vous envoie des photos de ce qui est disponible
          aujourd'hui, avec le prix, sans passer par le site.
        </p>
      </article>
      <article class="card" data-reveal style="--reveal-delay:180ms">
        <h2>Vous préférez attendre</h2>
        <p>
          Laissez-nous votre numéro sur WhatsApp. Vous serez prévenu le jour
          de la mise en ligne, et pas un jour de plus.
        </p>
      </article>
    </div>

    <div class="cta__actions" data-reveal style="margin-top:var(--sp-7)">
      <a class="btn" href="https://wa.me/{self.site['whatsapp']}?text={
        'Bonjour%2C%20je%20voudrais%20voir%20les%20pi%C3%A8ces%20de%20l%27atelier.'}"
         target="_blank" rel="noopener">
        <svg aria-hidden="true"><use href="#i-whatsapp"></use></svg>
        Écrire à l'atelier
      </a>
      <a class="btn btn--ghost" href="selection.html">Voir ce qui est disponible</a>
    </div>
  </div>
</section>"""

        self.page(
            "a-venir.html", content=content, current="a-venir",
            title="Ce qui se prépare | Yem's",
            description="La ligne cousue main de l'atelier Yem's arrive. En attendant, "
                        "écrivez-nous pour voir les pièces disponibles à Cotonou.",
        )

    def build_shop(self):
        """
        La boutique entière, sur une page.

        Elle manquait : le hero promet « la boutique » et n'avait que des pages
        catégorie à offrir. Un visiteur qui ne cherche pas encore une forme
        précise doit pouvoir tout voir d'un coup — huit pièces tiennent
        largement sur un écran.
        """
        blocs = []
        for cat in self.categories:
            produits = self.by_category(cat["slug"])
            if not produits:
                continue   # rayon vide : il est annoncé sur a-venir.html
            blocs.append(f"""    <div class="rayon" id="{cat['slug']}">
      <div class="rayon__head" data-reveal>
        <h2>{cat['name']}</h2>
        <a class="link-underline" href="{cat['slug']}.html">
          Tout voir
          <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
        </a>
      </div>
{grid(produits, "", klass="shop-grid", level=3)}
    </div>""")

        content = f"""<section class="section section--top" id="boutique">
  <div class="container container--wide">
    <div class="section-head" data-reveal>
      <span class="eyebrow">La boutique</span>
      <h1 class="page-title" style="margin-top:var(--sp-3)">Tout ce qui sort de l'atelier</h1>
      <p class="lede">
        Huit pièces, une seule construction : cuir pleine fleur, point sellier,
        semelle remplaçable. Ce qui change, c'est la forme et l'usage.
      </p>
    </div>

{chr(10).join(blocs)}

    <div class="text-center" style="margin-top:var(--sp-8)">
      <p class="lede mx-auto text-center" style="margin-bottom:var(--sp-5)">
        Aucune pointure ne vous va&nbsp;? C'est fréquent, et ça se règle.
      </p>
      <a class="btn" href="configurateur.html">
        Composer ma paire sur mesure
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
      <a class="btn btn--ghost" href="a-venir.html" style="margin-left:var(--sp-3)">
        Voir ce qui se prépare
      </a>
    </div>
  </div>
</section>"""

        self.page(
            "boutique.html", content=content, current="boutique",
            title="La boutique | Yem's",
            description="Toutes les pièces Yem's : souliers, ceintures, portefeuilles "
                        "et entretien. Cousus main à Cotonou, livrés au Bénin et en "
                        "Côte d'Ivoire.",
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

        orphans = [c["slug"] for c in self.categories if not self.by_category(c["slug"])]
        if orphans:
            print("\n  note : catégories sans produit → %s" % ", ".join(orphans))
        todo = [p["slug"] for p in self.products if not p.get("images")]
        if todo:
            print("  note : produits sans photo → %s" % ", ".join(todo))


if __name__ == "__main__":
    Builder().run()
