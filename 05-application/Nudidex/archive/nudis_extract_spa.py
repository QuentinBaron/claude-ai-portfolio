#!/usr/bin/env python3
"""
nudis_extract_spa.py
Tahitinudi est une SPA Jimdo : le contenu est embarqué en JSON dans le HTML.
Ce script extrait toutes les données directement depuis la page d'accueil
et/ou depuis les blobs JSON embarqués dans chaque page.
"""
import json, re, requests
from pathlib import Path
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HERE    = Path(__file__).parent

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    return r.text

def find_json_blobs(html):
    """Cherche tous les JSON significatifs embarqués dans le HTML."""
    found = []
    # Pattern 1 : window.__X__ = {...}
    for m in re.finditer(r'window\.__(\w+)__\s*=\s*(\{.*?\});', html, re.S):
        try:
            found.append((m.group(1), json.loads(m.group(2))))
        except: pass
    # Pattern 2 : window.X = {...} ou var X = {...}
    for m in re.finditer(r'(?:window\.(\w+)|var\s+(\w+))\s*=\s*(\{.{50,}\});', html, re.S):
        name = m.group(1) or m.group(2)
        try:
            obj = json.loads(m.group(3))
            found.append((name, obj))
        except: pass
    # Pattern 3 : <script type="application/json">
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("script", type="application/json"):
        try:
            found.append(("script_json", json.loads(tag.string)))
        except: pass
    # Pattern 4 : __NEXT_DATA__ / __NUXT__ / initialState
    for pat in [r'"initialState"\s*:\s*(\{.+?\})\s*[,}]',
                r'__NEXT_DATA__[^{]+(\{.+\})',
                r'__NUXT__[^(]+\((.+)\)']:
        for m in re.finditer(pat, html, re.S):
            try: found.append(("nuxt_next", json.loads(m.group(1))))
            except: pass
    return found

def search_species_data(obj, depth=0, path=""):
    """Cherche récursivement des données d'espèces dans un objet JSON."""
    if depth > 8: return []
    results = []
    if isinstance(obj, dict):
        # Check si ce dict ressemble à une fiche espèce
        keys = set(obj.keys())
        if any(k in keys for k in ["slug", "scientificName", "name", "image", "description"]):
            if any(k in str(obj).lower() for k in ["nudibranch", "dorid", "aeolid", "phyllidia",
                                                     "chromodoris", "hypselodoris", "flabellina"]):
                results.append((path, obj))
        for k, v in obj.items():
            results.extend(search_species_data(v, depth+1, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):  # limiter pour éviter les boucles
            results.extend(search_species_data(v, depth+1, f"{path}[{i}]"))
    return results

print("=" * 60)
print("ÉTAPE 1 — Analyse de la page d'accueil")
print("=" * 60)
home_html = fetch("https://tahitinudi.jimdoweb.com/")
print(f"Taille : {len(home_html):,} chars")

blobs = find_json_blobs(home_html)
print(f"JSON embarqués trouvés : {len(blobs)}")
for name, obj in blobs:
    size = len(str(obj))
    print(f"  [{name}] taille={size:,}")
    if size > 5000:
        # Sauvegarder pour inspection
        with open(HERE / f"spa_blob_{name}.json", "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"    → Sauvegardé dans spa_blob_{name}.json")
        # Chercher des données d'espèces
        matches = search_species_data(obj)
        if matches:
            print(f"    → {len(matches)} fiches espèces potentielles !")

print()
print("=" * 60)
print("ÉTAPE 2 — Analyse d'une page espèce (abronica-cf-payaso)")
print("=" * 60)
sp_html = fetch("https://tahitinudi.jimdoweb.com/abronica-cf-payaso")
print(f"Taille : {len(sp_html):,} chars")

# Chercher les URLs jimcdn directement dans le HTML brut
imgs = re.findall(r'https?://(?:image\.)?jimcdn\.com/[^\s"\'<>]+', sp_html)
imgs_unique = list(dict.fromkeys(imgs))
print(f"URLs jimcdn trouvées : {len(imgs_unique)}")
for u in imgs_unique[:5]:
    print(f"  {u[:100]}")

# Chercher "abronica" dans la page
idx = sp_html.lower().find("abronica")
if idx >= 0:
    print(f"\nContexte autour de 'abronica' (pos {idx}):")
    print(repr(sp_html[max(0,idx-50):idx+200]))
else:
    print("\n'abronica' non trouvé dans la page espèce")

# Chercher des JSON blobs dans la page espèce
sp_blobs = find_json_blobs(sp_html)
print(f"\nJSON embarqués : {len(sp_blobs)}")
for name, obj in sp_blobs:
    size = len(str(obj))
    print(f"  [{name}] taille={size:,}")
    if size > 2000:
        with open(HERE / f"spa_sp_{name}.json", "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"    → Sauvegardé dans spa_sp_{name}.json")

# Sauvegarder aussi le HTML brut pour inspection manuelle
with open(HERE / "spa_debug_home.html", "w", encoding="utf-8") as f:
    f.write(home_html)
with open(HERE / "spa_debug_species.html", "w", encoding="utf-8") as f:
    f.write(sp_html)
print("\nHTML bruts sauvegardés : spa_debug_home.html / spa_debug_species.html")
print("\nOuvre ces fichiers dans un éditeur de texte et cherche 'abronica' pour")
print("trouver comment les données sont structurées.")
