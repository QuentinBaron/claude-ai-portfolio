#!/usr/bin/env python3
"""
nudis_enrich_all_aphia.py
Pour chaque espÃ¨ce sans AphiaID dans nudis_taxonomy.csv :
  1. Cherche l'AphiaID sur WoRMS par nom scientifique
  2. RÃ©cupÃ¨re l'ordre WoRMS
  3. Met Ã  jour le CSV

RelanÃ§able : saute les espÃ¨ces dÃ©jÃ  traitÃ©es.
PAUSE = 0.4s â ~3 min pour 350 espÃ¨ces.
"""
import csv, json, time, re, requests
from pathlib import Path
from nudis_worms import search_aphia, get_classification, extract_order

HERE     = Path(__file__).parent
CSV_PATH = HERE / "nudis_taxonomy.csv"
PROGRESS = HERE / "nudis_aphia_progress.json"
PAUSE    = 0.4

def get_order(aphia_id):
    """Retourne l'ordre le plus prÃ©cis depuis la classification WoRMS."""
    classif = get_classification(aphia_id)
    return extract_order(classif) if classif else None

def save_csv(rows, path, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def sci_name_from_slug(slug, csv_name):
    """Retourne le nom scientifique Ã  chercher."""
    if csv_name and len(csv_name) > 3:
        # Retirer les suffixes sp. indÃ©terminÃ©s pour une recherche par genre
        if re.search(r'\bsp[\.\-\s]', csv_name, re.I):
            return csv_name.split()[0]  # genre seulement
        return csv_name
    # Fallback : reconstruire depuis le slug
    return slug.replace("-", " ").title()

# ââ Charger le CSV âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
rows = []
fieldnames = None
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = [k for k in reader.fieldnames if k]
    for row in reader:
        rows.append({k: row.get(k, "") for k in fieldnames})

# Ajouter worms_aphia_id si colonne absente
if "worms_aphia_id" not in fieldnames:
    fieldnames.append("worms_aphia_id")
    for row in rows:
        row.setdefault("worms_aphia_id", "")

# ââ Charger la progression ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
progress = {}
if PROGRESS.exists():
    with open(PROGRESS, encoding="utf-8") as f:
        progress = json.load(f)
print(f"Reprise : {len(progress)} espÃ¨ces dÃ©jÃ  traitÃ©es")

# ââ Traiter les espÃ¨ces sans AphiaID âââââââââââââââââââââââââââââââââââââââââââ
to_process = [r for r in rows if not r.get("worms_aphia_id","").strip()]
print(f"Ã traiter : {len(to_process)} espÃ¨ces sans AphiaID\n")

changed = 0
for i, row in enumerate(to_process):
    slug = row.get("slug", "")
    if slug in progress:
        # Appliquer le rÃ©sultat sauvegardÃ©
        row["worms_aphia_id"] = progress[slug].get("aphia_id", "")
        if progress[slug].get("worms_order"):
            row["ordre"] = progress[slug]["worms_order"]
        continue

    name = sci_name_from_slug(slug, row.get("nom_scientifique", ""))
    csv_order = row.get("ordre", "")
    print(f"[{i+1}/{len(to_process)}] {slug:<45}", end=" ", flush=True)

    rec = search_aphia(name)
    time.sleep(PAUSE)

    if not rec:
        print("â non trouvÃ©")
        progress[slug] = {"aphia_id": "", "worms_order": ""}
        continue

    aphia_id  = str(rec.get("AphiaID", ""))
    worms_order = get_order(aphia_id)
    time.sleep(PAUSE)

    row["worms_aphia_id"] = aphia_id

    if worms_order and worms_order != csv_order:
        row["ordre"] = worms_order
        print(f"aphia={aphia_id}  â  {csv_order!r} â {worms_order!r}")
        changed += 1
    elif worms_order:
        print(f"aphia={aphia_id}  â {csv_order}")
    else:
        print(f"aphia={aphia_id}  ordre non trouvÃ©")

    progress[slug] = {"aphia_id": aphia_id, "worms_order": worms_order or ""}

    # Sauvegarde toutes les 10 espÃ¨ces
    if (i + 1) % 10 == 0:
        with open(PROGRESS, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False)
        save_csv(rows, CSV_PATH, fieldnames)

# Sauvegarde finale
with open(PROGRESS, "w", encoding="utf-8") as f:
    json.dump(progress, f, ensure_ascii=False)
save_csv(rows, CSV_PATH, fieldnames)

print(f"\n{'='*55}")
print(f"â {changed} ordres corrigÃ©s")
print(f"   CSV mis Ã  jour : {CSV_PATH.name}")
if PROGRESS.exists():
    PROGRESS.unlink()
