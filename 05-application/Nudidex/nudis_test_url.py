#!/usr/bin/env python3
"""
Diagnostic : teste plusieurs variantes d'URL pour comprendre la structure du site.
"""
import requests, json
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Espèce dont on sait qu'elle existe (présente dans l'ancien scrape)
KNOWN_SLUG = "abronica-cf-payaso"

# Variantes à tester
variants = [
    f"https://tahitinudi.jimdoweb.com/{KNOWN_SLUG}",
    f"https://tahitinudi.jimdofree.com/{KNOWN_SLUG}",
    f"https://tahitinudi.jimdoweb.com/{KNOWN_SLUG}/",
    f"https://www.tahitinudi.jimdoweb.com/{KNOWN_SLUG}",
    f"https://tahitinudi.jimdoweb.com/",         # page d'accueil
]

print("Test des URLs...\n")
for url in variants:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        size = len(r.text)
        final_url = r.url
        print(f"  {r.status_code}  {size:>7} chars  {final_url}")
        if r.status_code == 200 and size > 5000:
            # Chercher des indices dans le HTML
            if "abronica" in r.text.lower():
                print("    ✓ Contient 'abronica'")
            if "jimcdn" in r.text:
                print("    ✓ Contient des images jimcdn")
    except Exception as e:
        print(f"  ERROR  {url}  →  {e}")

# Vérifier aussi une URL connue de l'ancien scrape
print("\nVérification de l'URL d'accueil actuelle...")
try:
    r = requests.get("https://tahitinudi.jimdoweb.com/", headers=HEADERS, timeout=10)
    print(f"  Accueil : {r.status_code}, URL finale : {r.url}")
    # Chercher des liens vers des espèces
    import re
    links = re.findall(r'href="(/[a-z][a-z0-9-]+)"', r.text)
    links = [l for l in links if len(l) > 3][:20]
    if links:
        print(f"  Exemples de liens trouvés : {links[:10]}")
except Exception as e:
    print(f"  ERROR : {e}")
