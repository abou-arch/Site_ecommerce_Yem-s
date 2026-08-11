#!/usr/bin/env python3
"""
Yem's — Normalisation des photos produits.

Détoure chaque photo de son fond d'origine et la recompose sur le dégradé
beige de la charte, avec une ombre de contact douce. Sortie en JPEG + WebP.

Usage :  python3 tools/process_images.py
"""

import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from scipy import ndimage

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(SRC, "assets", "img")
os.makedirs(OUT, exist_ok=True)

# Charte : dégradé beige (base.css → --beige-50 / --beige-200 / --beige-300)
BEIGE_TOP = (251, 247, 241)
BEIGE_MID = (233, 222, 203)
BEIGE_BOT = (206, 189, 164)

# ---------------------------------------------------------------- recettes
JOBS = [
    dict(src="WhatsApp Image 2026-08-10 at 11.02.54 PM.jpeg",
         out="loafer-ouidah",       crop=None,                  tol=42, ratio=(4, 5)),
    dict(src="WhatsApp Image 2026-08-10 at 11.02.55 PM.jpeg",
         out="derby-cotonou-alt",   crop=(0, 715, 1080, 1690),  tol=56, ratio=(4, 5)),
    dict(src="WhatsApp Image 2026-08-10 at 11.02.59 PM.jpeg",
         out="derby-cotonou",       crop=None,                  tol=72, ratio=(4, 5)),
    dict(src="WhatsApp Image 2026-08-10 at 11.03.01 PM.jpeg",
         out="loafer-ouidah-alt",   crop=None,                  tol=72, ratio=(4, 5)),
    dict(src="WhatsApp Image 2026-08-10 at 11.03.02 PM.jpeg",
         out="boot-atakora",        crop=None,                  tol=72, ratio=(4, 5)),
    dict(src="WhatsApp Image 2026-08-10 at 11.03.03 PM.jpeg",
         out="richelieu-abidjan",   crop=None,                  tol=72, ratio=(4, 5)),
]

# Fond texturé (béton) : pas de détourage fiable → recadrage + étalonnage beige
GRADED = dict(src="WhatsApp Image 2026-08-10 at 11.02.56 PM.jpeg",
              out="atelier-bicolore", crop=(0, 60, 744, 800), ratio=(16, 10))


def beige_backdrop(w, h):
    """Dégradé beige vertical + halo radial clair, cohérent avec .pshot."""
    y = np.linspace(0, 1, h)[:, None]
    top, mid, bot = (np.array(c, float) for c in (BEIGE_TOP, BEIGE_MID, BEIGE_BOT))
    ramp = np.where(y < 0.55,
                    top + (mid - top) * (y / 0.55),
                    mid + (bot - mid) * ((y - 0.55) / 0.45))
    bg = np.repeat(ramp[:, None, :], w, axis=1)

    # halo radial centré en haut, comme le radial-gradient CSS
    xx, yy = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-0.35, 1.65, h))
    halo = np.clip(1 - np.sqrt((xx / 1.15) ** 2 + (yy / 1.25) ** 2), 0, 1) ** 1.7
    bg += halo[:, :, None] * 16
    return Image.fromarray(np.clip(bg, 0, 255).astype("uint8"), "RGB")


def _largest_parts(mask, min_frac=0.004):
    lab, n = ndimage.label(mask)
    if not n:
        return mask
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s > min_frac * mask.size]
    return np.isin(lab, keep)


def separate(img, tol):
    """
    Sépare la photo en trois : le sujet plein, son ombre portée, le fond.

    L'ombre d'origine ne peut pas être découpée comme le sujet — recollée telle
    quelle sur du beige elle formerait une tache grise. On la conserve donc sous
    forme de facteur d'assombrissement, à multiplier sur le nouveau fond.
    """
    a = np.asarray(img, float)
    h, w = a.shape[:2]

    # couleur de fond = médiane d'une bande le long des 4 bords
    b = max(4, min(h, w) // 60)
    border = np.concatenate([
        a[:b].reshape(-1, 3), a[-b:].reshape(-1, 3),
        a[:, :b].reshape(-1, 3), a[:, -b:].reshape(-1, 3)])
    bg_color = np.median(border, axis=0)

    near_bg = np.sqrt(((a - bg_color) ** 2).sum(axis=2)) < tol

    # seules les zones near_bg reliées au bord de l'image sont du vrai fond
    lab, _ = ndimage.label(near_bg)
    edge_ids = set(np.unique(np.concatenate([
        lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    foreground = ~np.isin(lab, list(edge_ids))
    foreground = _largest_parts(ndimage.binary_fill_holes(foreground))

    # le sujet = la part franchement plus sombre que le fond ;
    # remplir les trous récupère les zones claires internes (doublure, semelle)
    lum = a.mean(axis=2)
    bg_lum = float(bg_color.mean())
    solid = foreground & (lum < 0.45 * bg_lum)
    solid = _largest_parts(ndimage.binary_fill_holes(solid))
    solid = ndimage.binary_opening(solid, np.ones((5, 5)))
    solid = ndimage.binary_fill_holes(solid)
    solid = ndimage.binary_erosion(solid, np.ones((3, 3)), iterations=2)

    # l'ombre portée : tout le reste du premier plan, en facteur multiplicatif
    shade = np.clip(lum / max(bg_lum, 1), 0, 1)
    shade = np.where(foreground & ~solid, shade, 1.0)
    shade = np.clip(1 - (1 - shade) * 0.80, 0.60, 1.0)   # ombre adoucie
    return solid, shade


def compose(img, solid, shade, ratio):
    """Sujet cadré sur le dégradé beige, ombre portée d'origine reconstituée."""
    ys, xs = np.where(solid)
    if len(xs) == 0:
        raise RuntimeError("masque vide")
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()

    alpha = Image.fromarray((solid * 255).astype("uint8"), "L") \
                 .filter(ImageFilter.GaussianBlur(1.1))
    cut = img.convert("RGBA")
    cut.putalpha(alpha)
    cut = cut.crop((x0, y0, x1 + 1, y1 + 1))

    shade_img = Image.fromarray((shade * 255).astype("uint8"), "L") \
                     .crop((x0, y0, x1 + 1, y1 + 1)) \
                     .filter(ImageFilter.GaussianBlur(2.5))

    # toile au ratio demandé, sujet à ~84 % de la largeur
    sw, sh = cut.size
    target_w = int(sw / 0.84)
    target_h = int(target_w * ratio[1] / ratio[0])
    if target_h < sh / 0.80:
        target_h = int(sh / 0.80)
        target_w = int(target_h * ratio[0] / ratio[1])

    canvas = beige_backdrop(target_w, target_h)
    px = (target_w - sw) // 2
    py = int((target_h - sh) * 0.50)

    # ombre portée : on assombrit le fond beige au lieu d'y coller du gris
    full_shade = Image.new("L", (target_w, target_h), 255)
    full_shade.paste(shade_img, (px, py))
    c = np.asarray(canvas, float) * (np.asarray(full_shade, float)[:, :, None] / 255)

    # ombre de contact supplémentaire, très douce, pour asseoir le sujet
    contact = Image.new("L", (target_w, target_h), 0)
    ImageDraw.Draw(contact).ellipse(
        [px + sw * 0.10, py + sh * 0.93, px + sw * 0.90, py + sh * 1.03], fill=54)
    contact = np.asarray(contact.filter(
        ImageFilter.GaussianBlur(target_w * 0.03)), float)[:, :, None] / 255
    c = c * (1 - contact * 0.42)

    canvas = Image.fromarray(np.clip(c, 0, 255).astype("uint8"), "RGB")
    canvas.paste(cut, (px, py), cut)
    return canvas


def export(img, name, width=1200):
    img = img.convert("RGB")
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    jpg = os.path.join(OUT, name + ".jpg")
    webp = os.path.join(OUT, name + ".webp")
    img.save(jpg, "JPEG", quality=84, optimize=True, progressive=True)
    img.save(webp, "WEBP", quality=80, method=6)
    print(f"  {name:22} {img.width}x{img.height}  "
          f"jpg {os.path.getsize(jpg)//1024} Ko / webp {os.path.getsize(webp)//1024} Ko")


def main():
    print("Détourage + fond beige :")
    for job in JOBS:
        img = Image.open(os.path.join(SRC, job["src"])).convert("RGB")
        if job["crop"]:
            img = img.crop(job["crop"])
        solid, shade = separate(img, job["tol"])
        cover = solid.mean()
        if not 0.05 < cover < 0.85:
            print(f"  !! {job['out']} : couverture suspecte {cover:.0%}")
        export(compose(img, solid, shade, job["ratio"]), job["out"])

    # image d'ambiance : pas de détourage, étalonnage vers le beige
    print("Étalonnage beige (fond texturé) :")
    img = Image.open(os.path.join(SRC, GRADED["src"])).convert("RGB")
    img = img.crop(GRADED["crop"])
    a = np.asarray(img, float)
    lum = a.mean(axis=2, keepdims=True) / 255
    warm = np.array(BEIGE_MID, float) - np.array([210, 210, 210])
    a = np.clip(a + warm * lum * 1.15, 0, 255)          # réchauffe les clairs
    a = np.clip((a - 128) * 1.06 + 128, 0, 255)          # léger contraste
    export(Image.fromarray(a.astype("uint8"), "RGB"), GRADED["out"], width=1400)


if __name__ == "__main__":
    main()
