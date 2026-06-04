#!/usr/bin/env python3
"""Vérifie les 3 espèces sans AphiaID sur WoRMS par nom scientifique."""
import requests, time

HEADERS = {"User-Agent": "NudidexBot/1.0 (educational research)"}

SPECIES = [
    ("vayssierea-felis",  "Vayssierea felis",  "Onchidoridida"),
    ("janolus-mirabilis", "Janolus mirabilis",  "Proctonotida"),
    ("runcina-sp.-1",     "Runcina",            "Runcinida"),
]

def search_worms(name):
    url = f"https://www.marinespecies.org/rest/AphiaRecordsByName/{requests.utils.quote(name)}"
    r = requests.get(url, headers=HEADERS, params={"like":"false","marine_only":"true"}, timeout=15)
    return r.json() if r.status_code == 200 else []

def get_classification(aphia_id):
    url = f"https://www.marinespecies.org/rest/AphiaClassificationByAphiaID/{aphia_id}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    return r.json() if r.status_code == 200 else None

ORDER_RANKS = {"order","suborder","superorder","cohort","subcohort"}

def extract_order(classif, depth=0):
    if not classif or depth > 20: return None
    rank = classif.get("rank","").lower()
    name = classif.get("scientificname","")
    child = classif.get("child")
    deeper = extract_order(child, depth+1) if child else None
    if deeper: return deeper
    if rank in ORDER_RANKS and name and name.lower() != "nudibranchia":
        return name
    if rank in ORDER_RANKS and name == "Nudibranchia":
        return "Nudibranchia"
    return None

for slug, sci_name, csv_order in SPECIES:
    print(f"\n{sci_name} (CSV: {csv_order})")
    results = search_worms(sci_name.split()[0] if "sp." in sci_name else sci_name)
    time.sleep(0.5)
    if not results:
        print("  → Aucun résultat WoRMS")
        continue
    for rec in results[:2]:
        aphia = rec.get("AphiaID")
        status = rec.get("status","")
        kingdom = rec.get("kingdom","")
        phylum  = rec.get("phylum","")
        print(f"  AphiaID={aphia}  status={status}  {kingdom} > {phylum}")
        if phylum == "Mollusca":
            classif = get_classification(aphia)
            worms_order = extract_order(classif)
            match = "✓" if (worms_order or "").lower() == csv_order.lower() else "⚠"
            print(f"  {match} Ordre WoRMS : {worms_order}  (CSV : {csv_order})")
            time.sleep(0.5)
