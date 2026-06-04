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

CSV_PATH    = HERE / "nudis_taxonomy.csv"
TMPL_PATH   = HERE / "nudis_template_v2.html"
ENRICHED    = HERE / "nudis_enriched.json"
EDITOR_PATH = HERE / "nudis_traits_editor.html"

FULL_JSON   = HERE / "nudis_scraped_full.json"
BASE_JSON   = HERE / "nudis_scraped.json"
JSON_PATH   = FULL_JSON if FULL_JSON.exists() else BASE_JSON
TRAITS_PATH = HERE / "nudis_traits.json"

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

# Traits morphologiques (optionnel — si nudis_traits.json existe)
traits_json = '{}'
if TRAITS_PATH.exists():
    with open(TRAITS_PATH, encoding="utf-8") as f:
        traits_data = json.load(f)
    traits_json = json.dumps(traits_data.get("families", traits_data), ensure_ascii=False, separators=(',', ':'))
    print(f"  Traits     : {len(json.loads(traits_json))} familles chargées")
else:
    print(f"  Traits     : nudis_traits.json absent — filtre basique")

html = (template
    .replace('__SPECIES__', data_json)
    .replace('__TRAITS__', traits_json)
    .replace('__BUILD__', build_str))

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = OUT_HTML.stat().st_size // 1024
print(f"  → index.html généré ({size_kb} KB, {len(species)} espèces)")

# ════════════════════════════════════════
# ÉTAPE 3 — Injecter photos dans l'éditeur
# ════════════════════════════════════════
if EDITOR_PATH.exists():
    print(f"\nÉTAPE 3 — Injection photos dans l'éditeur")

    # Construire photos_db : {famille: [{u:url, n:nom, f:1(premiere)/0}]}
    from collections import defaultdict
    photos_db = defaultdict(list)
    for sp in species:
        fam = sp.get("f", "")
        if not fam:
            continue
        name = sp.get("n", sp.get("s", ""))
        raw_p = sp.get("p", [])
        if isinstance(raw_p, str):
            raw_p = [raw_p] if raw_p else []
        for idx, url in enumerate(raw_p):
            if url:
                photos_db[fam].append({"u": url, "n": name, "f": 1 if idx == 0 else 0})

    photos_json = json.dumps(dict(photos_db), ensure_ascii=False, separators=(',', ':'))
    total_photos = sum(len(v) for v in photos_db.values())
    print(f"  Photos     : {total_photos} URLs · {len(photos_db)} familles")

    with open(EDITOR_PATH, encoding="utf-8") as f:
        editor_src = f.read()

    if '__EDITOR_PHOTOS__' in editor_src:
        editor_updated = editor_src.replace('__EDITOR_PHOTOS__', photos_json)
        with open(EDITOR_PATH, "w", encoding="utf-8") as f:
            f.write(editor_updated)
        print(f"  → {EDITOR_PATH.name} mis à jour")
    else:
        print(f"  ⚠ Placeholder __EDITOR_PHOTOS__ absent — éditeur non mis à jour")
else:
    print(f"\nÉTAPE 3 — {EDITOR_PATH.name} absent, ignoré")

print(f"\n{'='*50}")
print(f"✅ Nudidex prêt !")
print(f"{'='*50}\n")
