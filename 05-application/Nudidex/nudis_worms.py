#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nudis_worms.py
Client WoRMS (marinespecies.org) partagé entre tous les scripts d'enrichissement.

Fonctions exposées :
  search_aphia(name)         → record WoRMS (dict) ou None
  get_record(aphia_id)       → record WoRMS par AphiaID
  get_classification(aphia_id) → arbre de classification
  extract_order(classif)     → nom de l'ordre le plus précis

P2 : extrait depuis nudis_enrich_all_aphia.py, nudis_verify_worms.py,
     nudis_check_3.py, nudis_fix_aphia.py pour éliminer les duplications.
"""
import requests

HEADERS     = {"User-Agent": "NudidexBot/1.0 (educational research)"}
ORDER_RANKS = {"order", "suborder", "superorder", "cohort", "subcohort"}

WORMS_BASE  = "https://www.marinespecies.org/rest"


def search_aphia(name):
    """Retourne le meilleur record WoRMS pour un nom scientifique (Mollusca uniquement)."""
    url = f"{WORMS_BASE}/AphiaRecordsByName/{requests.utils.quote(name)}"
    try:
        r = requests.get(url, headers=HEADERS,
                         params={"like": "false", "marine_only": "true"}, timeout=15)
        if r.status_code == 200:
            recs = r.json()
            # Préférer accepted + Mollusca
            for rec in recs:
                if rec.get("status") == "accepted" and rec.get("phylum") == "Mollusca":
                    return rec
            # Fallback : premier Mollusca
            for rec in recs:
                if rec.get("phylum") == "Mollusca":
                    return rec
    except Exception:
        pass
    return None


def get_record(aphia_id):
    """Retourne le record WoRMS pour un AphiaID donné."""
    url = f"{WORMS_BASE}/AphiaRecordByAphiaID/{aphia_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_classification(aphia_id):
    """Retourne la classification complète (arbre d'ancêtres) pour un AphiaID."""
    url = f"{WORMS_BASE}/AphiaClassificationByAphiaID/{aphia_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def extract_order(classif, depth=0):
    """Parcourt l'arbre de classification WoRMS.

    Retourne le rang le plus précis parmi order/suborder/cohort,
    en préférant un sous-ordre précis à 'Nudibranchia' générique.
    Implémentation de référence : nudis_enrich_all_aphia.py.
    """
    if not classif or depth > 20:
        return None
    rank  = classif.get("rank", "").lower()
    name  = classif.get("scientificname", "")
    child = classif.get("child")

    deeper = extract_order(child, depth + 1) if child else None
    if deeper:
        return deeper
    if rank in ORDER_RANKS and name and name.lower() != "nudibranchia":
        return name
    if rank in ORDER_RANKS and name == "Nudibranchia":
        return "Nudibranchia"
    return None
