#!/usr/bin/env python3
"""
Yem's — Déclinaisons web des visuels générés (ambiance et hero).

Les PNG sortent des outils de génération à 2 Mo et plus. Servis tels quels,
ils avaient fait passer l'accueil de 0,7 à 7,6 Mo. Ce script en tire les
fichiers que le site référence réellement :

  <nom>.webp / <nom>.jpg          1000 px de large
  <nom>-500.webp / <nom>-500.jpg  500 px, pour les téléphones

Le ratio d'origine est conservé : il doit être reporté tel quel (w, h) dans
data/products.json, sinon le navigateur réserve la mauvaise place.

Les visuels de campagne (hero d'accueil, bloc de marque, hero « About us »)
sortent eux aussi en 1,7 Mo de PNG. Ils sont déclinés par CAMPAGNE, en
plusieurs largeurs, parce qu'ils sont servis en pleine largeur : un téléphone
de 390 px n'a aucune raison de télécharger 1536 px de large.

Usage :  python tools/images_ia.py
"""

import glob
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")

# Visuels de campagne : source PNG → nom servi + largeurs à produire.
#
# La largeur la plus grande est celle du PNG d'origine (1536 px) : au-delà on
# agrandirait du vide. La plus petite est calée sur un téléphone à 2x
# (390 px × 2 ≈ 780), arrondie à 800.
#
# Le nom servi ne porte PAS le numéro de version du PNG. Une v8 remplacera la
# v7 ici, et ni le CSS ni les gabarits n'auront à bouger.
CAMPAGNE = {
    "hero-yems-avatar-v7.png":      ("hero-accueil",   (1536, 1200, 800)),
    "atelier-yems-couture-v1.png":  ("atelier-couture", (1200, 800, 500)),
    "hero-yems-atelier-v1.png":     ("atelier-etabli",  (1200, 800, 500)),
}


def export(img, name, width):
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    jpg = os.path.join(IMG, name + ".jpg")
    webp = os.path.join(IMG, name + ".webp")
    img.save(jpg, "JPEG", quality=82, optimize=True, progressive=True)
    img.save(webp, "WEBP", quality=78, method=6)
    print(f"  {name:26} {img.width}x{img.height}  "
          f"jpg {os.path.getsize(jpg)//1024} Ko / webp {os.path.getsize(webp)//1024} Ko")


def main():
    print("Visuels d'ambiance :")
    for src in sorted(glob.glob(os.path.join(IMG, "*-ai.png"))):
        name = os.path.splitext(os.path.basename(src))[0]
        img = Image.open(src).convert("RGB")
        export(img, name, 1000)
        export(img, name + "-500", 500)

    # Le hero d'accueil ne vient plus de hero.png : il est produit par la
    # table CAMPAGNE ci-dessous, à partir du visuel validé (avatar v7). Les
    # fichiers hero.*/hero-900.* et hero-portrait.* qu'on fabriquait ici
    # n'étaient plus lus par aucune feuille de style ; ils ont été supprimés.
    # hero.png reste au dépôt comme image source.

    print("Visuels de campagne :")
    for src, (nom, largeurs) in CAMPAGNE.items():
        chemin = os.path.join(IMG, src)
        if not os.path.exists(chemin):
            print(f"  {src} absent — ignoré")
            continue
        img = Image.open(chemin).convert("RGB")
        for i, w in enumerate(sorted(largeurs, reverse=True)):
            # La plus grande largeur garde le nom nu ; les suivantes portent
            # leur largeur, comme le reste du dossier (« -500 »).
            export(img, nom if i == 0 else f"{nom}-{w}", w)


if __name__ == "__main__":
    main()
