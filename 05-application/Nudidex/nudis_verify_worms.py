#!/usr/bin/env python3
"""
nudis_verify_worms.py
VÃ©rifie l'ordre taxonomique de chaque espÃ¨ce via l'API WoRMS (AphiaID).
Produit un rapport des incohÃ©rences entre le CSV et WoRMS.

Usage : python nudis_verify_worms.py
"""
import csv, json, time, requests
from pathlib import Path
from nudis_worms import get_record as get_worms_record, get_classification as get_worms_classification, extract_order as extract_order_from_classification

CSV_PATH = Path(__file__).parent / "nudis_taxonomy.csv"
OUT_PATH = Path(__file__).parent / "nudis_worms_errors.json"
PAUSE    = 0.5   # secondes entre requÃªtes API

# Charger le CSV
rows = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if row.get("worms_aphia_id","").strip():
            rows.append(row)

print(f"{len(rows)} espÃ¨ces avec AphiaID Ã  vÃ©rifier\n")

errors   = []
ok_count = 0
skip     = 0

for i, row in enumerate(rows):
    slug     = row.get("slug","").strip()
    aphia_id = row.get("worms_aphia_id","").strip()
    csv_order = row.get("ordre","").strip()

    print(f"[{i+1}/{len(rows)}] {slug:<45} CSV:{csv_order:<20}", end=" ... ", flush=True)

    try:
        classif = get_worms_classification(aphia_id)
        worms_order = extract_order_from_classification(classif)
    except Exception as e:
        print(f"ERREUR: {e}")
        skip += 1
        time.sleep(PAUSE)
        continue

    if not worms_order:
        print("ordre non trouvÃ© dans WoRMS")
        skip += 1
    elif worms_order.lower() == csv_order.lower():
        print("â")
        ok_count += 1
    else:
        print(f"â  WoRMS:{worms_order}")
        errors.append({
            "slug":       slug,
            "aphia_id":   aphia_id,
            "csv_order":  csv_order,
            "worms_order": worms_order,
            "famille":    row.get("famille",""),
        })

    time.sleep(PAUSE)

# Rapport
print(f"\n{'='*55}")
print(f"â Corrects   : {ok_count}")
print(f"â  Erreurs    : {len(errors)}")
print(f"? Non trouvÃ©s: {skip}")

if errors:
    print(f"\nEspÃ¨ces avec ordre incorrect dans le CSV :")
    for e in errors:
        print(f"  {e['slug']:<45} CSV:{e['csv_order']:<20} â WoRMS:{e['worms_order']}")
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)
    print(f"\nâ DÃ©tails sauvegardÃ©s dans {OUT_PATH.name}")
