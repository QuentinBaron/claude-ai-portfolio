#!/usr/bin/env python3
"""Génère les icônes PNG pour le manifest PWA depuis l'image uploadée."""
from PIL import Image, ImageOps
import glob, os, sys
from pathlib import Path

OUT     = Path(__file__).parent / "NUDIS_pokedex"
# Chercher le PNG source dans NUDIS_pokedex (excluant les icônes déjà générées)
pngs = [p for p in OUT.glob("*.png") if not p.name.startswith("icon-")]
if not pngs:
    print("Aucun PNG source trouvé dans NUDIS_pokedex")
    sys.exit(1)
src = sorted(pngs, key=os.path.getmtime, reverse=True)[0]
print(f"Source : {src.name}")

img = Image.open(src).convert("RGBA")

for size in [192, 512]:
    canvas = Image.new("RGBA", (size, size), (15, 23, 42, 255))  # fond bleu nuit

    # Redimensionner le nudibranche en gardant les proportions, avec padding
    pad = int(size * 0.08)
    max_dim = size - pad * 2
    thumb = img.copy()
    thumb.thumbnail((max_dim, max_dim), Image.LANCZOS)

    # Centrer sur le canvas
    x = (size - thumb.width) // 2
    y = (size - thumb.height) // 2
    canvas.paste(thumb, (x, y), thumb)

    # Coins arrondis
    from PIL import ImageDraw
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size-1, size-1], radius=size//5, fill=255)
    canvas.putalpha(mask)

    out_path = OUT / f"icon-{size}.png"
    canvas.save(out_path, "PNG")
    print(f"✅ {out_path.name}")
