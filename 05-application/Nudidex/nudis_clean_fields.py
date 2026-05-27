#!/usr/bin/env python3
"""
Nettoie les champs t, pr, l, ph dans nudis_scraped_full.json :
tronque avant le prochain label connu sur la même ligne.
"""
import json, re
from pathlib import Path

HERE = Path(__file__).parent
JSON_PATH = HERE / "nudis_scraped_full.json"

FIELD_LABELS = r'(?:Taille|Longueur|Profondeur|Prof|Lieu|Lieux|Localisation|Localit[eé]|Photo|Site|©)'

def clean(val):
    if not val:
        return val
    val = re.split(rf'\s+{FIELD_LABELS}\s*[:\-]', val, flags=re.I)[0]
    return val.strip().rstrip(' .,;')

with open(JSON_PATH, encoding="utf-8") as f:
    species = json.load(f)

fixed = 0
for sp in species:
    for key in ["t", "pr", "l", "ph"]:
        old = sp.get(key, "")
        new = clean(old)
        if new != old:
            sp[key] = new
            fixed += 1

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(species, f, ensure_ascii=False, indent=2)

print(f"✅ {fixed} champs nettoyés dans {JSON_PATH.name}")
