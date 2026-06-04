#!/usr/bin/env python3
"""
nudis_fix_slugs.py
Corrige les slugs malformÃ©s (# â .), re-scrape les espÃ¨ces concernÃ©es,
met Ã  jour nudis_scraped_full.json et nudis_taxonomy.csv.
"""
import json, csv, time, re, sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests beautifulsoup4 lxml"); sys.exit(1)

from nudis_scraper_utils import (
    normalize_slug, slug_variants, extract_images,
    extract_photographer, extract_field, scrape_species,
    FIELD_LABELS, BASE_URL, HEADERS,
)

HERE      = Path(__file__).parent
CSV_PATH  = HERE / "nudis_taxonomy.csv"
JSON_PATH = HERE / "nudis_scraped_full.json"

PAUSE = 1.5

# ââ Mapping : ancien slug â nouveau slug corrigÃ© ââââââââââââââââââââââââââââââ
SLUG_FIXES = {
    "biuve-sp#1":         "biuve-sp.1",
    "tylodina-sp#1":      "tylodina-sp.1",
    # spinoaglaja-orientalis : slug OK mais nom non capitalisÃ© â re-scrape seulement
}
# EspÃ¨ces Ã  re-scraper (avec leur nouveau slug si applicable)
RESCRAPE = {
    "biuve-sp.1":             None,   # sera dÃ©duit aprÃ¨s renommage
    "spinoaglaja-orientalis": None,
    "tylodina-sp.1":          None,
}

# ââ 1. Corriger nudis_taxonomy.csv ââââââââââââââââââââââââââââââââââââââââââââ
print("=== Correction des slugs dans nudis_taxonomy.csv ===")
rows, fieldnames = [], None
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = [k for k in reader.fieldnames if k]
    for row in reader:
        old_slug = row.get("slug", "").strip()
        if old_slug in SLUG_FIXES:
            new_slug = SLUG_FIXES[old_slug]
            print(f"  CSV  {old_slug!r} â {new_slug!r}")
            row["slug"] = new_slug
            # Corriger aussi le nom s'il est identique au slug
            if row.get("nom_commun", "").strip() == old_slug:
                row["nom_commun"] = new_slug
        rows.append({k: row.get(k, "") for k in fieldnames})

with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f"â CSV mis Ã  jour\n")

# ââ 2. Corriger nudis_scraped_full.json âââââââââââââââââââââââââââââââââââââââ
print("=== Correction des slugs dans nudis_scraped_full.json ===")
with open(JSON_PATH, encoding="utf-8") as f:
    species = json.load(f)

for sp in species:
    old = sp.get("s", "")
    if old in SLUG_FIXES:
        new = SLUG_FIXES[old]
        print(f"  JSON {old!r} â {new!r}")
        sp["s"] = new
        if sp.get("n", "") == old:
            sp["n"] = new

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(species, f, ensure_ascii=False, indent=2)
print(f"â JSON slugs corrigÃ©s\n")

# ââ 3. Re-scraper les 3 espÃ¨ces âââââââââââââââââââââââââââââââââââââââââââââââ
print("=== Re-scraping des 3 espÃ¨ces ===")
new_data = {}
for slug in RESCRAPE:
    print(f"  [{slug}] ...", end=" ", flush=True)
    result = scrape_species(slug)
    if result.get("_404"):
        print("404 â page introuvable")
    elif result.get("_error"):
        print(f"ERREUR : {result['_error']}")
    else:
        has_photo = "â" if result.get("p") else "â"
        print(f"{result['n'][:50]}  photo:{has_photo}")
    new_data[slug] = result
    time.sleep(PAUSE)

# ââ 4. Mettre Ã  jour le JSON avec les nouvelles donnÃ©es âââââââââââââââââââââââ
print("\n=== Mise Ã  jour nudis_scraped_full.json ===")
with open(JSON_PATH, encoding="utf-8") as f:
    species = json.load(f)

updated = 0
for sp in species:
    s = sp.get("s", "")
    if s in new_data and not new_data[s].get("_404") and not new_data[s].get("_error"):
        # Conserver les champs taxonomiques existants (o, f, nc, worms_aphia_id)
        for key in ["n", "p", "ps", "ph", "t", "pr", "l", "d"]:
            sp[key] = new_data[s].get(key, sp.get(key, ""))
        print(f"  Mis Ã  jour : {s} â nom: {sp['n'][:40]}, photo: {'oui' if sp.get('p') else 'non'}")
        updated += 1

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(species, f, ensure_ascii=False, indent=2)
print(f"\nâ {updated} espÃ¨ce(s) mise(s) Ã  jour dans nudis_scraped_full.json")
print("\nâ Lance maintenant : python deploy.py")
