#!/usr/bin/env python3
"""
nudis_scraper_full.py
Scrape toutes les espÃ¨ces listÃ©es dans nudis_taxonomy.csv depuis tahitinudi.jimdoweb.com
et produit nudis_scraped_full.json.

PrÃ©requis :
    pip install requests beautifulsoup4 lxml

Usage :
    python nudis_scraper_full.py

ParamÃ¨tres :
    PAUSE   : secondes entre requÃªtes (politesse serveur)
    WORKERS : parallÃ©lisme (dÃ©conseillÃ© > 3 pour Jimdo)
"""
import json, csv, time, re, os, sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installe d'abord : pip install requests beautifulsoup4 lxml")
    sys.exit(1)

from nudis_scraper_utils import (
    normalize_slug, slug_variants, extract_images,
    extract_photographer, extract_field, scrape_species,
    FIELD_LABELS, BASE_URL, HEADERS,
)

# ââ Config ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
PAUSE       = 1.2          # secondes entre requÃªtes
CSV_PATH    = Path(__file__).parent / "nudis_taxonomy.csv"
OUT_JSON    = Path(__file__).parent / "nudis_scraped_full.json"
RESUME_JSON = Path(__file__).parent / "nudis_scrape_progress.json"


# ââ Main âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def main():
    # Supprimer le fichier de reprise potentiellement corrompu au premier lancement propre
    # (commenter ces 3 lignes si tu veux reprendre une session interrompue)
    # if RESUME_JSON.exists():
    #     RESUME_JSON.unlink()

    # Lire les slugs depuis le CSV
    slugs = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            s = row.get("slug", "").strip()
            if s:
                slugs.append(s)
    print(f"CSV : {len(slugs)} slugs Ã  scraper")

    # Reprise depuis sauvegarde
    done = {}
    if RESUME_JSON.exists():
        with open(RESUME_JSON, encoding="utf-8") as f:
            done = {sp["s"]: sp for sp in json.load(f)}
        print(f"Reprise : {len(done)} dÃ©jÃ  scrapÃ©s")

    results = list(done.values())
    done_slugs = set(done.keys())
    todo = [s for s in slugs if s not in done_slugs]
    print(f"Restant : {len(todo)} espÃ¨ces")

    for i, slug in enumerate(todo):
        print(f"[{i+1}/{len(todo)}] {slug}", end=" ... ", flush=True)
        sp = scrape_species(slug)
        if sp.get("_404"):
            print("404")
        elif sp.get("_error"):
            print(f"ERROR: {sp['_error']}")
        else:
            has_photo = "â" if sp.get("p") else "â"
            print(f"{sp['n'][:40]}  photo:{has_photo}")
        results.append(sp)

        # Sauvegarde intermÃ©diaire toutes les 10 espÃ¨ces
        if (i + 1) % 10 == 0:
            with open(RESUME_JSON, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(PAUSE)

    # Sauvegarde finale
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Stats
    total   = len(results)
    with_p  = sum(1 for s in results if s.get("p"))
    errors  = sum(1 for s in results if s.get("_error"))
    not_found = sum(1 for s in results if s.get("_404"))
    print(f"\n{'='*50}")
    print(f"Total    : {total}")
    print(f"Avec photo : {with_p}")
    print(f"404      : {not_found}")
    print(f"Erreurs  : {errors}")
    print(f"\nSortie â {OUT_JSON}")

    # Nettoyage fichier de reprise
    if RESUME_JSON.exists():
        RESUME_JSON.unlink()

if __name__ == "__main__":
    main()
