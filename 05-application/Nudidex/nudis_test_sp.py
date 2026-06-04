#!/usr/bin/env python3
"""Test des variantes d'URL pour les espèces sp.X"""
import requests
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://tahitinudi.jimdoweb.com/liste-des-espèces/"

tests = [
    "aegires-sp.1",
    "aegires-sp-1",
    "aegires-sp1",
    "anteaeolidiella-sp.1",
    "anteaeolidiella-sp-1",
    "aeolid-non-identifie-sp.4",
    "aeolid-non-identifié-sp.4",
]
for slug in tests:
    try:
        r = requests.get(BASE + slug + "/", headers=HEADERS, timeout=10)
        has_jimcdn = "jimcdn.com" in r.text
        print(f"  {r.status_code}  jimcdn:{has_jimcdn}  {slug}")
    except Exception as e:
        print(f"  ERROR  {slug}  {e}")
