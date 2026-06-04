#!/usr/bin/env python3
"""
Normalise les noms d'ordres dans nudis_taxonomy.csv et nudis_enriched.json
vers les noms traditionnels (-ida), plus lisibles et cohérents avec la littérature.

Mappings WoRMS → convention Nudidex :
  Aeolidina     → Aeolida
  Dendronotina  → Dendronotida
  Arminina      → Arminida
  Janolina      → Dendronotida  (sous-ordre de Dendronotida, trop obscur seul)
"""
import json, csv
from pathlib import Path
from collections import Counter

HERE = Path(__file__).parent

NORM = {
    "Aeolidina":    "Aeolida",
    "Dendronotina": "Dendronotida",
    "Arminina":     "Arminida",
    "Janolina":     "Dendronotida",
}

def normalize(ordre):
    return NORM.get(ordre, ordre)

# ── CSV ───────────────────────────────────────────────────────────────────────
csv_path = HERE / "nudis_taxonomy.csv"
rows, fieldnames = [], None
with open(csv_path, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = [k for k in reader.fieldnames if k]
    for row in reader:
        rows.append({k: row.get(k, "") for k in fieldnames})

csv_fixed = 0
for row in rows:
    n = normalize(row.get("ordre", ""))
    if n != row.get("ordre", ""):
        csv_fixed += 1
    row["ordre"] = n

with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f"✅ CSV : {csv_fixed} normalisations")

# ── JSON enriched ─────────────────────────────────────────────────────────────
json_path = HERE / "nudis_enriched.json"
with open(json_path, encoding="utf-8") as f:
    species = json.load(f)

json_fixed = 0
for sp in species:
    n = normalize(sp.get("o", ""))
    if n != sp.get("o", ""):
        json_fixed += 1
    sp["o"] = n

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(species, f, ensure_ascii=False, indent=2)
print(f"✅ JSON : {json_fixed} normalisations")

# ── Distribution finale ───────────────────────────────────────────────────────
counts = Counter(sp.get("o", "") for sp in species)
print("\nDistribution des ordres après normalisation :")
for ordre, n in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {n:3d}  {ordre}")
