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

import json
import os
import re
import shutil
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "products.json")
TPL = os.path.join(ROOT, "templates")
OUT_PRODUCTS = os.path.join(ROOT, "produit")

STATUS = {
    "green": ("badge--green", "Au Bénin"),
    "amber": ("badge--amber", "En route"),
    "red":   ("badge--red",   "Indisponible"),
}


# ─────────────────────────────────────────────────────────── utilitaires

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


def badge(status, extra=""):
    cls, label = STATUS[status]
    return ('<span class="badge %s %s"><span class="badge__dot"></span>%s</span>'
            % (cls, extra, label))


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


def product_card(product, base, delay=0):
    """Carte produit, telle qu'elle apparaît dans une grille."""
    href = "%sproduit/%s.html" % (base, product["slug"])
    style = ' style="--reveal-delay:%dms"' % delay if delay else ""
    empty = "" if product.get("images") else " pshot--empty"
    return f"""      <article class="pcard" data-reveal{style}>
        <a href="{href}" aria-label="Découvrir {escape(product['name'])}">
          <div class="pshot{empty}" data-shot>
            {badge(product['status'], 'pshot__badge')}
            {picture(product, base)}
          </div>
        </a>
        <div class="pcard__body">
          <div class="pcard__row">
            <h3 class="pcard__name">{escape(product['name'])}</h3>
            <span class="pcard__price">{price(product['price'])}</span>
          </div>
          <p class="pcard__desc">{product['short']}</p>
        </div>
      </article>"""


def grid(products, base, klass="collections__grid"):
    if not products:
        return """      <div class="empty-state">
        <p class="display">Cette ligne arrive bientôt.</p>
        <p class="text-muted">Écrivez-nous sur WhatsApp pour être prévenu du lancement.</p>
      </div>"""
    cards = [product_card(p, base, delay=i * 90) for i, p in enumerate(products)]
    return '    <div class="%s">\n%s\n    </div>' % (klass, "\n\n".join(cards))


def nav_links(categories, base, current=None, mobile=False):
    out = []
    for c in categories:
        aria = ' aria-current="page"' if c["slug"] == current else ""
        href = "%s%s.html" % (base, c["slug"])
        if mobile:
            out.append('  <a href="%s"%s>%s</a>' % (href, aria, c["nav"]))
        else:
            out.append('      <a class="nav__link" href="%s"%s>%s</a>'
                       % (href, aria, c["nav"]))
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


# ─────────────────────────────────────────────────────────── assemblage

class Builder:
    def __init__(self):
        self.data = json.loads(read(DATA))
        self.site = self.data["site"]
        self.categories = self.data["categories"]
        self.products = self.data["products"]
        self.base_tpl = read(os.path.join(TPL, "base.html"))
        self.svg_defs = read(os.path.join(TPL, "partials", "svg-defs.html")).strip()
        self.header_tpl = read(os.path.join(TPL, "partials", "header.html"))
        self.footer_tpl = read(os.path.join(TPL, "partials", "footer.html"))
        self.written = []

    def by_category(self, slug):
        return [p for p in self.products if p["category"] == slug]

    def chrome(self, base, home, current):
        """Header et footer, résolus pour la profondeur de la page."""
        header = fill(
            self.header_tpl,
            base=base,
            nav=nav_links(self.categories, base, current),
            nav_mobile=nav_links(self.categories, base, current, mobile=True),
        )
        footer_cats = "\n".join(
            '          <li><a href="%s%s.html">%s</a></li>' % (base, c["slug"], c["name"])
            for c in self.categories
        )
        footer = fill(
            self.footer_tpl,
            base=base, home=home,
            footer_categories=footer_cats,
            whatsapp=self.site["whatsapp"],
            email=self.site["email"],
        )
        return header, footer

    def page(self, path, *, content, title, description,
             og_title=None, og_type="website", og_image=None,
             current=None, depth=0, structured=None):
        base = "../" * depth
        home = "%sindex.html" % base if path != "index.html" else ""
        header, footer = self.chrome(base, home, current)

        html = fill(
            self.base_tpl,
            # contenu de <title> : c'est du texte, pas un attribut — les
            # apostrophes n'ont pas à être échappées (html.escape échappe par défaut)
            title=escape(title, quote=False),
            description=escape(description, quote=True),
            og_title=escape(og_title or title, quote=True),
            og_type=og_type,
            og_image=('<meta property="og:image" content="%sassets/img/%s.jpg">\n'
                      % (base, og_image)) if og_image else "",
            structured_data=json_ld(structured) if structured else "",
            base=base,
            svg_defs=self.svg_defs,
            header=header,
            footer=footer,
            content=content,
        )
        write(os.path.join(ROOT, path), html)
        self.written.append((path, len(html.encode())))

    # ── les trois types de page ──────────────────────────────────────

    def build_home(self):
        body = read(os.path.join(TPL, "pages", "index.html"))
        featured = [p for p in self.products if p.get("featured")]
        body = fill(body, base="", whatsapp=self.site["whatsapp"],
                    featured_grid=grid(featured, ""))
        self.page(
            "index.html",
            content=body,
            title="Yem's — Souliers et maroquinerie cousus main | Différents par les détails",
            description=("Yem's — souliers, ceintures et portefeuilles cousus à la main à "
                         "Cotonou. Point sellier, cuir pleine fleur, semelle ressemelable. "
                         "Sur-mesure en 14 à 20 jours, livré au Bénin et en Côte d'Ivoire."),
            og_title="Yem's — Personne ne verra la couture. Tout le monde verra la différence.",
            og_image="loafer-ouidah",
            structured={
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Yem's",
                "slogan": self.site["slogan"],
                "areaServed": self.site["cities"],
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

{grid(products, "")}
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
            title="%s — Yem's" % cat["title"],
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
        </div>"""

        specs = "\n".join(
            '          <div class="spec-row"><dt>%s</dt><dd>%s</dd></div>'
            % (escape(s["label"]), s["value"]) for s in product["specs"])

        details = ""
        if product.get("details"):
            blocks = "\n".join(f"""      <div class="card" data-reveal style="--reveal-delay:{i*90}ms">
        <span class="card__num">0{i+1}</span>
        <h3>{escape(d['title'])}</h3>
        <p>{d['text']}</p>
      </div>""" for i, d in enumerate(product["details"]))
            details = f"""
<section class="section">
  <div class="container">
    <div class="section-head" data-reveal>
      <span class="eyebrow">Le détail qui compte</span>
    </div>
    <div class="grid grid--2">
{blocks}
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
          Ce modèle n'existe qu'en sur-mesure. Délai de production : 14 à 20 jours.
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
           style="margin-top:var(--sp-3)">Le vouloir sur-mesure</a>"""

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
        <h2 style="margin-top:var(--sp-4)">Dans la même ligne</h2>
      </div>
      <a class="link-underline" href="{base}{cat['slug']}.html">
        Voir toute la ligne
        <svg aria-hidden="true"><use href="#i-arrow"></use></svg>
      </a>
    </div>

{grid(related, base, klass='grid grid--3')}
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
      <span class="eyebrow">{cat['name']}</span>
      <h1 class="product__name">{escape(product['name'])}</h1>
      <p class="product__price">{price(product['price'])}</p>
      <p class="lede">{product['pitch']}</p>

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
            title="%s — %s | Yem's" % (product["name"], cat["name"]),
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
      <a class="btn" href="chaussures.html">
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

    def run(self):
        if os.path.isdir(OUT_PRODUCTS):
            shutil.rmtree(OUT_PRODUCTS)

        self.build_home()
        for cat in self.categories:
            self.build_category(cat)
        for product in self.products:
            self.build_product(product)

        self.build_stub(
            "configurateur.html",
            title="Configurateur sur-mesure — Yem's",
            description="Composez votre paire sur-mesure : modèle, cuir, doublure, "
                        "semelle, fil et initiales. Production en 14 à 20 jours.",
            eyebrow="Bientôt en ligne",
            heading="Le configurateur<br>arrive",
            text="En attendant, l'atelier prend les commandes sur-mesure directement sur "
                 "WhatsApp : vous décrivez ce que vous voulez, il vous chiffre la pièce "
                 "dans la journée.",
        )
        self.build_stub(
            "panier.html",
            title="Panier — Yem's",
            description="Votre panier Yem's. Paiement Mobile Money MTN et Moov, "
                        "Wave ou carte bancaire, sécurisé par KkiaPay.",
            eyebrow="Bientôt en ligne",
            heading="Le paiement en ligne<br>arrive",
            text="Vos articles sont bien enregistrés sur cet appareil. Le règlement par "
                 "Mobile Money, Wave et carte arrive avec l'intégration KkiaPay — d'ici là, "
                 "l'atelier finalise la commande sur WhatsApp.",
        )

        print("%d pages générées :\n" % len(self.written))
        for path, size in self.written:
            print("  %-42s %5d Ko" % (path, size // 1024 or 1))

        orphans = [c["slug"] for c in self.categories if not self.by_category(c["slug"])]
        if orphans:
            print("\n  note : catégories sans produit → %s" % ", ".join(orphans))
        todo = [p["slug"] for p in self.products if not p.get("images")]
        if todo:
            print("  note : produits sans photo → %s" % ", ".join(todo))


if __name__ == "__main__":
    Builder().run()
