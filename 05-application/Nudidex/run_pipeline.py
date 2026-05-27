#!/usr/bin/env python3
"""
run_pipeline.py  —  Nudidex : pipeline complet
================================================
Ce script fait tout d'un coup :
  1. Fusionne nudis_taxonomy.csv + nudis_scraped_full.json → nudis_enriched.json
  2. Génère index.html depuis le template

Doit être lancé depuis 05-application/Nudidex/ :
    python run_pipeline.py
"""
import json, csv, re, unicodedata
from datetime import datetime
from pathlib import Path

HERE     = Path(__file__).parent   # = 05-application/Nudidex/
OUT_HTML = HERE / "index.html"

CSV_PATH  = HERE / "nudis_taxonomy.csv"
TMPL_PATH = HERE / "nudis_template_v2.html"
ENRICHED  = HERE / "nudis_enriched.json"

FULL_JSON = HERE / "nudis_scraped_full.json"
BASE_JSON = HERE / "nudis_scraped.json"
JSON_PATH = FULL_JSON if FULL_JSON.exists() else BASE_JSON

# ════════════════════════════════════════
# ÉTAPE 1 — Merge CSV + JSON
# ════════════════════════════════════════

def normalize_slug(s):
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")

def clean_desc(d):
    if not d:
        return ""
    d = d.strip()
    if "La page souhait" in d:
        return ""
    d = re.sub(r'\.\s*jimdo\.com\s*$', '', d).strip()
    return d

def extract_ph(sp):
    if sp.get("ph"):
        return sp["ph"]
    d = sp.get("d", "")
    m = re.search(r'Photo\s*:\s*([^\d\n]+)', d, re.I)
    if m:
        raw = re.sub(r'\s+', ' ', m.group(1)).strip()
        if re.search(r'jean.?marc', raw, re.I):
            return "Jean-Marc Levy"
        return raw
    return ""

def clean_name(n):
    if not n:
        return n
    n = re.sub(r'^[^\wÀ-ɏ]+', '', n, flags=re.UNICODE).strip()
    return n

print(f"\n{'='*50}")
print(f"ÉTAPE 1 — Fusion CSV + JSON")
print(f"  Source : {JSON_PATH.name}")
print(f"  CSV    : {CSV_PATH.name}")

taxonomy = {}
with open(CSV_PATH, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        raw_slug = row.get("slug", "").strip()
        if not raw_slug:
            continue
        taxonomy[normalize_slug(raw_slug)] = {
            "o":             row.get("ordre", "").strip(),
            "f":             row.get("famille", "").strip(),
            "nc":            row.get("nom_commun", "").strip(),
            "worms_aphia_id": row.get("worms_aphia_id", "").strip(),
        }
print(f"  CSV chargé : {len(taxonomy)} entrées")

with open(JSON_PATH, encoding="utf-8") as f:
    scraped = json.load(f)
print(f"  JSON chargé : {len(scraped)} espèces")

matched, unmatched, enriched = [], [], []

for sp in scraped:
    ph = extract_ph(sp)
    d  = clean_desc(sp.get("d", ""))
    d  = re.sub(r'Photo\s*:.*$', '', d, flags=re.M).strip()
    sp["ph"] = ph
    sp["d"]  = d
    sp["n"]  = clean_name(sp.get("n", ""))

    row = taxonomy.get(normalize_slug(sp.get("s", "")))
    if row:
        matched.append(sp["s"])
        sp.update(row)
    else:
        unmatched.append(sp["s"])
        for k in ("o", "f", "nc", "worms_aphia_id"):
            sp.setdefault(k, "")
    enriched.append(sp)

with open(ENRICHED, "w", encoding="utf-8") as f:
    json.dump(enriched, f, ensure_ascii=False, indent=2)

print(f"  Matchés    : {len(matched)}/{len(scraped)}")
if unmatched:
    print(f"  Non matchés : {len(unmatched)}")
print(f"  → {ENRICHED.name} généré")

# ════════════════════════════════════════
# ÉTAPE 2 — Générer index.html
# ════════════════════════════════════════
print(f"\nÉTAPE 2 — Génération du Nudidex")
print(f"  Template : {TMPL_PATH.name}")

with open(ENRICHED, encoding="utf-8") as f:
    species = json.load(f)

data_json = json.dumps(species, ensure_ascii=False, separators=(',', ':'))

with open(TMPL_PATH, encoding="utf-8") as f:
    template = f.read()

build_str = "v" + datetime.now().strftime("%Y.%m.%d-%H%M")
html = template.replace('__SPECIES__', data_json).replace('__BUILD__', build_str)

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = OUT_HTML.stat().st_size // 1024
print(f"  → index.html généré ({size_kb} KB, {len(species)} espèces)")

print(f"\n{'='*50}")
print(f"✅ Nudidex prêt !")
print(f"{'='*50}\n")
