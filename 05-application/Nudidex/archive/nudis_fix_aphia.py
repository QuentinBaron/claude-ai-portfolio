#!/usr/bin/env python3
"""
Cherche les AphiaIDs corrects pour les espèces mal identifiées,
puis met à jour nudis_taxonomy.csv.
"""
import csv, requests, time
from pathlib import Path

HEADERS  = {"User-Agent": "NudidexBot/1.0 (educational research)"}
CSV_PATH = Path(__file__).parent / "nudis_taxonomy.csv"

TO_FIX = [
    "elysia-nealae",
    "embletonia-gracilis",
    "julia-exquisita",
    "julia-zebra",
]

# Correspondance slug → nom scientifique
NAMES = {
    "elysia-nealae":      "Elysia nealae",
    "embletonia-gracilis": "Embletonia gracilis",
    "julia-exquisita":    "Julia exquisita",
    "julia-zebra":        "Julia zebra",
}

def search_worms(name):
    """Retourne les records WoRMS correspondant à un nom scientifique."""
    url = f"https://www.marinespecies.org/rest/AphiaRecordsByName/{requests.utils.quote(name)}"
    params = {"like": "false", "marine_only": "true", "offset": 1}
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    if r.status_code == 200:
        return r.json()
    return []

print("Recherche des AphiaIDs corrects sur WoRMS...\n")
fixes = {}

for slug in TO_FIX:
    name = NAMES[slug]
    print(f"{name}:")
    results = search_worms(name)
    time.sleep(0.5)

    if not results:
        print("  → Aucun résultat\n")
        continue

    for rec in results[:3]:
        aphia = rec.get("AphiaID","")
        status = rec.get("status","")
        kingdom = rec.get("kingdom","")
        phylum  = rec.get("phylum","")
        classname = rec.get("class","")
        order   = rec.get("order","")
        print(f"  AphiaID={aphia}  status={status}  {kingdom} > {phylum} > {classname} > {order}")

    # Prendre le premier résultat "accepted" dans Mollusca
    best = None
    for rec in results:
        if rec.get("status") == "accepted" and rec.get("phylum","") in ("Mollusca",""):
            best = rec
            break
    if not best:
        best = results[0]

    fixes[slug] = str(best.get("AphiaID",""))
    print(f"  → Correction : AphiaID={fixes[slug]}\n")

# Mettre à jour le CSV
if fixes:
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [k for k in reader.fieldnames if k]  # exclure clés None/vides
        for row in reader:
            slug = row.get("slug","").strip()
            if slug in fixes:
                old = row.get("worms_aphia_id","")
                row["worms_aphia_id"] = fixes[slug]
                print(f"CSV mis à jour : {slug}  {old} → {fixes[slug]}")
            rows.append(row)

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ {CSV_PATH.name} mis à jour.")
else:
    print("Aucune correction appliquée.")
