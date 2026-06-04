#!/usr/bin/env python3
"""
Reconstruit nudis_taxonomy.csv depuis nudis_enriched.json
(utilisé après corruption du CSV par un script interrompu).
Applique aussi les 4 corrections d'AphiaID connues.
"""
import json, csv
from pathlib import Path

JSON_PATH = Path(__file__).parent / "nudis_enriched.json"
CSV_PATH  = Path(__file__).parent / "nudis_taxonomy.csv"

APHIA_FIXES = {
    "elysia-nealae":       "494460",
    "embletonia-gracilis": "534076",
    "julia-exquisita":     "215227",
    "julia-zebra":         "492585",
}

ORDER_FIXES = {
    "cephalopyge-trematoides":  "Dendronotida",
    "dermatobranchus-fortunatus": "Arminida",
}

with open(JSON_PATH, encoding="utf-8") as f:
    species = json.load(f)

fieldnames = ["slug", "nom_scientifique", "ordre", "famille", "nom_commun", "worms_aphia_id"]

rows = []
for sp in species:
    slug     = sp.get("s","")
    ordre    = ORDER_FIXES.get(slug, sp.get("o",""))
    aphia_id = APHIA_FIXES.get(slug, sp.get("worms_aphia_id",""))
    rows.append({
        "slug":             slug,
        "nom_scientifique": sp.get("n",""),
        "ordre":            ordre,
        "famille":          sp.get("f",""),
        "nom_commun":       sp.get("nc",""),
        "worms_aphia_id":   aphia_id,
    })

with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ {len(rows)} espèces restaurées dans {CSV_PATH.name}")
print(f"   Corrections AphiaID appliquées : {list(APHIA_FIXES.keys())}")
print(f"   Corrections ordre appliquées   : {list(ORDER_FIXES.keys())}")
