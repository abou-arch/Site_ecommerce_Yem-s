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

    nuage = resoudre(d.get("--nuage", d["--bg"]), d)
    blanc = resoudre(d.get("--blanc", "#FFFFFF"), d)
    sombre = resoudre(d["--sombre-bg"], d)

    fautes = []
    total = 0
    for page in sorted(glob.glob(os.path.join(RACINE, "*.html"))):
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        for m in re.finditer(r'<section class="([^"]+)"', html):
            total += 1
            cls = set(m.group(1).split())
            est_sombre = bool(cls & sombres)
            fond = sombre if est_sombre else (blanc if "section--blanc" in cls else nuage)
            texte = d["--sombre-text"] if est_sombre else d["--text"]
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
