#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige les ordres/familles/noms errones ou manquants dans
nudis_taxonomy.csv, nudis_scraped_full.json et nudis_enriched.json.
"""
import json, csv
from pathlib import Path

HERE = Path(__file__).parent

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read().replace("\r\n", "\n").replace("\r", "\n"))

# Corrections slug -> ordre
FIXES = {
    "embletonia-gracilis":    "Aeolida",
    "phylliroe-bucephalum":   "Dendronotida",
    "bullina-nobilis":        "Cephalaspidea",
    "bullina-sp.-1":          "Cephalaspidea",
    "cerberilla-albopuncata": "Aeolida",
    "marianina-rosea":        "Dendronotida",
    "scyllae-sp.-1":          "Dendronotida",
    "vayssierea-felis":       "Doridida",
    "mourgona-sp.1":          "Sacoglossa",
    "mourgona-sp.2":          "Sacoglossa",
    "madrella-ferruginosa":      "Aeolida",
    "pleurehdera-haraldi":       "Pleurobranchida",
    "phycophila-euchlora":       "Aplysiida",
    "cephalopyge-trematoides":   "Dendronotida",   # P4: depuis nudis_restore_csv.py
    "dermatobranchus-fortunatus": "Arminida",       # P4: depuis nudis_restore_csv.py
}

# Corrections slug -> nom scientifique
NAME_FIXES = {
    "thuridilla-carlsoni":      "Thuridilla carlsoni",
    "halgerda-sp.2":            "Halgerda berberiani",
    "ardeodoris-angustolutea":  "Ardeadoris angustolutea",
    "aegires-pruvotfolae":      "Aegires citrinus",
    "aegires-cf-incusus":       "Aegires cf. incusus",
    "cerberilla-albopuncata":   "Cerberilla albopunctata",
    "haloa-wallisi":            "Haloa wallisii",
    "doris-granulosa":          "Doriopsis granulosa",
    "thordisa-albomacula":      "Avaldesia albomacula",
    "thordisa-tahala":          "Avaldesia tahala",
    "flabellina-sp.-3":         "Flabellina sp.3",
    "peltodoris-fellowsi":      "Hiatodoris fellowsi",
}

# Corrections slug -> famille
FAMILY_FIXES = {
    "phycophila-euchlora": "Aplysiidae",
    "samla-bicolor":       "Samlidae",
    "halgerda-sp.2":       "Discodorididae",
    "mourgona-sp.1":       "Caliphyllidae",
    "mourgona-sp.2":       "Caliphyllidae",
    "murphydoris-puncticulata": "Goniodorididae",
    "pleurehdera-haraldi":      "Pleurobranchidae",
}

# Renames globaux d'ordre (toutes especes avec l'ancienne valeur)
# P3: fusionné depuis nudis_normalize_orders.py
ORDER_RENAMES = {
    "Anaspidea":    "Aplysiida",
    "Aeolidina":    "Aeolida",
    "Dendronotina": "Dendronotida",
    "Arminina":     "Arminida",
    "Janolina":     "Dendronotida",
}

# Renames globaux de famille (toutes especes avec l'ancienne valeur)
FAMILY_RENAMES = {
    "Cuthonidae": "Trinchesiidae",
}

# Slugs a supprimer entierement
DELETIONS = {
    "coriocella-nigra",
}

# ── Corrections de nudis_scraped_full.json
scraped_path = HERE / "nudis_scraped_full.json"
try:
    scraped = load_json(scraped_path)
    fixed_scraped = 0
    before = len(scraped)
    scraped = [sp for sp in scraped if sp.get("s","") not in DELETIONS]
    deleted = before - len(scraped)
    if deleted:
        print(f"  SCRAPED supprime : {deleted} espece(s)")
        fixed_scraped += deleted
    for sp in scraped:
        slug = sp.get("s","")
        if slug in NAME_FIXES and sp.get("n","") != NAME_FIXES[slug]:
            old_n = sp.get("n","")
            sp["n"] = NAME_FIXES[slug]
            print(f"  SCRAPED {slug:<45} nom: {old_n!r} -> {sp['n']!r}")
            fixed_scraped += 1
    with open(scraped_path, "w", encoding="utf-8") as f:
        json.dump(scraped, f, ensure_ascii=False, indent=2)
    print(f"OK nudis_scraped_full.json : {fixed_scraped} corrections")
except Exception as e:
    print(f"  WARN nudis_scraped_full.json non modifie ({e})")

# ── Corrections de nudis_enriched.json
json_path = HERE / "nudis_enriched.json"
species = load_json(json_path)

before = len(species)
species = [sp for sp in species if sp.get("s","") not in DELETIONS]
deleted = before - len(species)
if deleted:
    print(f"  JSON  supprime : {deleted} espece(s) {DELETIONS}")

fixed_json = 0
for sp in species:
    slug = sp.get("s","")
    if slug in FIXES:
        old = sp.get("o","")
        if old != FIXES[slug]:
            sp["o"] = FIXES[slug]
            print(f"  JSON  {slug:<45} ordre: {old!r} -> {sp['o']!r}")
            fixed_json += 1
    if sp.get("o","") in ORDER_RENAMES:
        old = sp["o"]
        sp["o"] = ORDER_RENAMES[old]
        print(f"  JSON  {slug:<45} ordre: {old!r} -> {sp['o']!r}")
        fixed_json += 1
    if slug in NAME_FIXES and sp.get("n","") != NAME_FIXES[slug]:
        old_n = sp.get("n","")
        sp["n"] = NAME_FIXES[slug]
        print(f"  JSON  {slug:<45} nom: {old_n!r} -> {sp['n']!r}")
        fixed_json += 1
    if slug in FAMILY_FIXES:
        old_f = sp.get("f","")
        if old_f != FAMILY_FIXES[slug]:
            sp["f"] = FAMILY_FIXES[slug]
            print(f"  JSON  {slug:<45} fam: {old_f!r} -> {sp['f']!r}")
            fixed_json += 1
    if sp.get("f","") in FAMILY_RENAMES:
        old_f = sp["f"]
        sp["f"] = FAMILY_RENAMES[old_f]
        print(f"  JSON  {slug:<45} fam: {old_f!r} -> {sp['f']!r}")
        fixed_json += 1

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(species, f, ensure_ascii=False, indent=2)
print(f"OK nudis_enriched.json : {fixed_json} corrections")

# ── Corrections de nudis_taxonomy.csv
csv_path = HERE / "nudis_taxonomy.csv"
rows = []
fieldnames = None
fixed_csv = 0
deleted_csv = 0

with open(csv_path, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = [k for k in reader.fieldnames if k]
    for row in reader:
        slug = row.get("slug","").strip()
        if slug in DELETIONS:
            print(f"  CSV   {slug:<45} SUPPRIME")
            deleted_csv += 1
            continue
        if slug in FIXES:
            old = row.get("ordre","")
            if old != FIXES[slug]:
                row["ordre"] = FIXES[slug]
                print(f"  CSV   {slug:<45} ordre: {old!r} -> {row['ordre']!r}")
                fixed_csv += 1
        if row.get("ordre","") in ORDER_RENAMES:
            old = row["ordre"]
            row["ordre"] = ORDER_RENAMES[old]
            print(f"  CSV   {slug:<45} ordre: {old!r} -> {row['ordre']!r}")
            fixed_csv += 1
        if slug in FAMILY_FIXES:
            old_f = row.get("famille","")
            if old_f != FAMILY_FIXES[slug]:
                row["famille"] = FAMILY_FIXES[slug]
                print(f"  CSV   {slug:<45} fam:   {old_f!r} -> {row['famille']!r}")
                fixed_csv += 1
        if row.get("famille","") in FAMILY_RENAMES:
            old_f = row["famille"]
            row["famille"] = FAMILY_RENAMES[old_f]
            print(f"  CSV   {slug:<45} fam:   {old_f!r} -> {row['famille']!r}")
            fixed_csv += 1
        rows.append({k: row.get(k,"") for k in fieldnames})

with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"OK nudis_taxonomy.csv : {fixed_csv} corrections, {deleted_csv} suppression(s)")
