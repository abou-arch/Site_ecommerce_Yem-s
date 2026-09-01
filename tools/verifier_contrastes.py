#!/usr/bin/env python3
"""
Yem's — Contrôle de lisibilité, section par section.

Pourquoi ce fichier existe
--------------------------
En passant le site du fond sombre au fond clair, j'ai vérifié les paires de
jetons une par une : toutes conformes, entre 4,5:1 et 17,9:1. Et le site est
quand même sorti illisible sur des sections entières, en texte beige sur fond
crème.

La raison : je vérifiais des COULEURS, jamais ce que la CASCADE produit. Une
règle « .section { background: transparent } » écrite après le bloc qui pose
les jetons sombres suffisait à retirer le fond en gardant le texte. Aucune
comparaison de jetons ne peut attraper ça.

Ce script rejoue donc la cascade sur les sections réellement générées : pour
chacune, quel fond, quelle couleur de texte, quel rapport. C'est le seul
contrôle qui aurait vu le problème.

Usage :  python3 tools/verifier_contrastes.py
Sortie :  code 1 si une section descend sous 4,5:1
"""

import glob
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEUIL = 4.5


def jetons():
    """Toutes les variables CSS du projet, première définition retenue."""
    d = {}
    for f in glob.glob(os.path.join(RACINE, "assets", "css", "*.css")):
        with open(f, encoding="utf-8") as fh:
            for m in re.finditer(r"^\s*(--[a-z0-9-]+):\s*([^;]+);", fh.read(), re.M):
                d.setdefault(m.group(1), m.group(2).strip())
    return d


def resoudre(valeur, d, n=0):
    valeur = valeur.strip()
    m = re.match(r"var\((--[a-z0-9-]+)\)$", valeur)
    if m and n < 8 and m.group(1) in d:
        return resoudre(d[m.group(1)], d, n + 1)
    return valeur


def luminance(hexa):
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def aplatir(valeur, fond, d):
    """Une couleur semi-transparente composée sur son fond."""
    v = resoudre(valeur, d)
    if v.startswith("#"):
        return v
    n = [float(x) for x in re.findall(r"[\d.]+", v)]
    if len(n) < 4:
        return "#%02X%02X%02X" % tuple(int(x) for x in n[:3])
    a = n[3]
    return "#%02X%02X%02X" % tuple(
        round(n[i] * a + int(fond[j:j + 2], 16) * (1 - a)) for i, j in ((0, 1), (1, 3), (2, 5)))


def rapport(texte, fond, d):
    l = sorted([luminance(aplatir(texte, fond, d)), luminance(fond)], reverse=True)
    return (l[0] + 0.05) / (l[1] + 0.05)


def declarations(css, propriete):
    """
    Toutes les règles qui posent une propriété, DANS L'ORDRE du fichier.

    L'ordre est le cœur du problème : à spécificité égale, c'est la dernière
    règle qui gagne. Un contrôle qui se contente de collecter les sélecteurs
    sans retenir leur position ne peut pas voir qu'une règle tardive annule
    une règle antérieure. C'était le défaut de la première version de ce
    script, et c'est précisément le bug qu'il devait détecter.
    """
    out = []
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        sels = [x.strip().split("*/")[-1].strip() for x in m.group(1).split(",")]
        # Un pseudo-élément (::before, ::after) peint une couche PAR-DESSUS
        # son parent ; il ne remplace pas le fond de l'élément. Les compter
        # revenait à croire qu'un voile décoratif était le fond de la section.
        sels = [x for x in sels if x.startswith(".") and "::" not in x]
        if not sels:
            continue
        d = re.search(r"(?<![-\w])%s\s*:\s*([^;]+)" % propriete, m.group(2))
        if d:
            out.append((m.start(), sels, d.group(1).strip()))
    return out


def fond_effectif(classes, regles_fond, defaut):
    """
    Le fond que ces classes reçoivent réellement, une fois la cascade jouée.

    On garde la DERNIÈRE règle qui s'applique, ce qui reproduit le
    comportement du navigateur pour des sélecteurs de même spécificité.
    """
    valeur = defaut
    for _, sels, v in regles_fond:
        for sel in sels:
            # Un sélecteur descendant (« .section--light .eyebrow ») vise un
            # ENFANT, pas la section. Les compter revenait à attribuer à la
            # section la couleur de sa dernière petite étiquette, et c'est ce
            # qui rendait ce contrôle aveugle au vrai défaut.
            if " " in sel or ">" in sel:
                continue
            base = sel.lstrip(".").split(":")[0].split("[")[0]
            if base in classes:
                valeur = v
    return valeur


def classes_sombres(css):
    """Les sélecteurs qui redéfinissent --text sur la série sombre."""
    out = set()
    for m in re.finditer(r"([^{}]+)\{[^}]*--text:\s*var\(--sombre-text\)", css):
        for s in m.group(1).split(","):
            s = s.strip().split("*/")[-1].strip()
            if s.startswith("."):
                out.add(s.lstrip(".").split(":")[0].split("[")[0])
    return out


def main():
    d = jetons()
    css = "".join(open(f, encoding="utf-8").read()
                  for f in glob.glob(os.path.join(RACINE, "assets", "css", "*.css")))
    sombres = classes_sombres(css)
    regles_fond = declarations(css, "background-color") + declarations(css, "background")
    regles_fond.sort()
    # Une section peut poser sa couleur de texte directement, sans passer par
    # --text. C'est ce que faisait .section--light, et c'est ce que la première
    # version de ce contrôle ne regardait pas.
    regles_texte = declarations(css, "color")
    regles_texte.sort()

    nuage = resoudre(d.get("--nuage", d["--bg"]), d)
    blanc = resoudre(d.get("--blanc", "#FFFFFF"), d)
    sombre = resoudre(d["--sombre-bg"], d)

    fautes = []
    total = 0
    for page in sorted(glob.glob(os.path.join(RACINE, "*.html"))):
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        for m in re.finditer(r'<section class="([^"]+)"([^>]*)>', html):
            total += 1
            cls = set(m.group(1).split())
            # Un fond posé en STYLE EN LIGNE échappe totalement au CSS. C'est
            # exactement ce qui rendait la section « garantie » illisible :
            # fond espresso dans le HTML, texte clair hérité du corps.
            en_ligne = re.search(r'style="[^"]*background(?:-color)?:\s*([^;"]+)', m.group(2))
            est_sombre = bool(cls & sombres)
            defaut = blanc if "section--blanc" in cls else nuage
            # Le fond n'est plus déduit de la classe : il est lu dans la
            # cascade. Un bloc « sombre » à qui une règle postérieure retire
            # son fond retombe donc sur le fond clair, et le contraste chute.
            brut = (en_ligne.group(1).strip() if en_ligne
                    else fond_effectif(cls, regles_fond, sombre if est_sombre else defaut))
            fond = resoudre(brut, d)
            if not fond.startswith("#"):
                # « background: dégradé, var(--espresso-900) » : la dernière
                # couche est la couleur de fond réelle.
                # On coupe sur les virgules de PREMIER niveau seulement :
                # un dégradé contient ses propres virgules, et un rstrip(")")
                # naïf mangeait la parenthèse de « var(--espresso-900) ».
                niveau, debut, couches = 0, 0, []
                for i, c in enumerate(brut):
                    if c == "(":
                        niveau += 1
                    elif c == ")":
                        niveau -= 1
                    elif c == "," and niveau == 0:
                        couches.append(brut[debut:i]); debut = i + 1
                couches.append(brut[debut:])
                dernier = resoudre(couches[-1].strip(), d)
                fond = dernier if dernier.startswith("#") else defaut
            texte = fond_effectif(cls, regles_texte,
                                  d["--sombre-text"] if est_sombre else d["--text"])
            r = rapport(texte, fond, d)
            if r < SEUIL:
                fautes.append((os.path.basename(page), m.group(1)[:40], fond,
                               aplatir(texte, fond, d), round(r, 2)))

    print("%d sections analysées sur %d pages" % (total, len(glob.glob(os.path.join(RACINE, "*.html")))))
    if fautes:
        print("\n!! Sections illisibles :\n")
        for f in fautes:
            print("   %-24s %-42s texte %s sur fond %s  %.2f:1" % (f[0], f[1], f[3], f[2], f[4]))
        print("\n   Cause la plus fréquente : un bloc reçoit les jetons sombres")
        print("   sans le fond sombre, ou une règle postérieure lui retire son fond.")
        return 1

    print("Toutes les sections dépassent %s:1." % SEUIL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
