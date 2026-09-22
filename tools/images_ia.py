#!/usr/bin/env python3
"""
Yem's — Déclinaisons web des visuels générés (ambiance et hero).

Les PNG sortent des outils de génération à 2 Mo et plus. Servis tels quels,
ils avaient fait passer l'accueil de 0,7 à 7,6 Mo. Ce script en tire les
fichiers que le site référence réellement :

  <nom>.webp / <nom>.jpg          1000 px de large
  <nom>-500.webp / <nom>-500.jpg  500 px, pour les téléphones
  hero.webp / hero.jpg            1600 px, et hero-900.* pour les téléphones

Le ratio d'origine est conservé : il doit être reporté tel quel (w, h) dans
data/products.json, sinon le navigateur réserve la mauvaise place.

Usage :  python tools/images_ia.py
"""

import glob
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")


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

    print("Hero :")
    img = Image.open(os.path.join(IMG, "hero.png")).convert("RGB")
    export(img, "hero", 1600)
    export(img, "hero-900", 900)


if __name__ == "__main__":
    main()
