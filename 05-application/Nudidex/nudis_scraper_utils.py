#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nudis_scraper_utils.py
Module commun pour le scraping de tahitinudi.jimdoweb.com.

Fonctions partagées entre :
  - nudis_scraper_full.py
  - nudis_fix_slugs.py
  - nudis_clean_fields.py (FIELD_LABELS uniquement)

P1 : extrait depuis les fichiers ci-dessus pour éliminer les duplications.
"""
import re, time, unicodedata
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    _requests_available = True
except ImportError:
    _requests_available = False

BASE_URL = "https://tahitinudi.jimdoweb.com/liste-des-espèces/"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; NudidexBot/1.0; educational research)"}

# Regex des labels de champs connus — version complète (avec © de fix_slugs)
FIELD_LABELS = r'(?:Taille|Longueur|Profondeur|Prof|Lieu|Lieux|Localisation|Localit[eé]|Photo|Site|©)'


def normalize_slug(s):
    """Normalise un slug : minuscules, sans accents, espaces → tirets."""
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def slug_variants(slug):
    """Génère les variantes d'URL à essayer pour un slug donné.

    Inclut la variante accentuée spíno (pour spinoaglaja-orientalis sur Jimdo).
    """
    def clean(s):
        s = s.replace(".", "-")
        return re.sub(r"-+", "-", s).strip("-")

    v1 = slug
    v2 = clean(slug)
    v3_base = unicodedata.normalize("NFD", slug)
    v3_base = "".join(c for c in v3_base if unicodedata.category(c) != "Mn")
    v3 = clean(v3_base)
    v4 = v3_base.strip()
    # Variante accentuée pour spinoaglaja (í = U+00ED, spécifique à Jimdo)
    v_accent = slug.replace("spino", "spíno")

    seen, variants = set(), []
    for v in [v1, v2, v3, v4, v_accent]:
        if v not in seen:
            seen.add(v)
            variants.append(v)
    return variants


def extract_images(soup):
    """Retourne (photo_principale, [toutes_photos]).

    Filtre le bandeau du site (id='cc-website-logo').
    """
    content = soup.find(id="content_area") or soup
    imgs = []
    for img in content.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        if "jimcdn.com" not in src and "jimdo" not in src:
            continue
        if any(x in src for x in ["logo", "favicon", "icon", "sprite"]):
            continue
        src = re.sub(r"^http://", "https://", src)
        if src not in imgs:
            imgs.append(src)
    return (imgs[0] if imgs else ""), imgs


def extract_photographer(soup, desc):
    """Cherche 'Photo : Nom' dans la page ou dans la description."""
    for cap in soup.find_all(["figcaption", "p", "span", "div"]):
        t = cap.get_text(" ", strip=True)
        m = re.search(r'Photo\s*[:\-]\s*([^\d\n]{3,60})', t, re.I)
        if m:
            raw = re.sub(r'\s+', ' ', m.group(1)).strip().rstrip('.,;')
            if re.search(r'jean.?marc', raw, re.I):
                return "Jean-Marc Levy"
            return raw
    if desc:
        m = re.search(r'Photo\s*[:\-]\s*([^\d\n]{3,60})', desc, re.I)
        if m:
            return re.sub(r'\s+', ' ', m.group(1)).strip().rstrip('.,;')
    return ""


def extract_field(soup, labels):
    """Cherche un champ (Taille, Profondeur, Lieu…) dans les balises de texte."""
    for el in soup.find_all(["p", "li", "td", "div", "span"]):
        t = el.get_text(" ", strip=True)
        for lbl in labels:
            m = re.search(rf'{lbl}\s*[:\-]\s*(.+)', t, re.I)
            if m:
                val = m.group(1).strip().split('\n')[0].strip()
                val = re.split(rf'\s+{FIELD_LABELS}\s*[:\-]', val, flags=re.I)[0].strip()
                val = val.rstrip(' .,;')
                if val and len(val) < 200:
                    return val
    return ""


def scrape_species(slug):
    """Scrape une page espèce et retourne un dict.

    Inclut la détection soft-404 (page sans contenu utile).
    Prérequis : pip install requests beautifulsoup4 lxml
    """
    if not _requests_available:
        raise ImportError("pip install requests beautifulsoup4 lxml")

    r = None
    for url_slug in slug_variants(slug):
        url = BASE_URL + url_slug + "/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except Exception as e:
            return {"s": slug, "n": slug, "_error": str(e)}
        if resp.status_code != 404:
            r = resp
            break

    if r is None or r.status_code == 404:
        return {"s": slug, "n": slug, "_404": True, "p": "", "ps": [], "d": ""}

    soup = BeautifulSoup(r.text, "lxml")

    name = ""
    for tag in ["h1", "h2"]:
        el = soup.find(tag)
        if el:
            t = el.get_text(" ", strip=True)
            if 2 < len(t) < 120:
                name = t
                break
    if not name:
        name = slug.replace("-", " ").title()

    desc = ""
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) > 60 and "jimdo" not in t.lower():
            desc = t
            break

    desc = re.sub(r'Photo\s*:.*$', '', desc, flags=re.M).strip()
    desc = re.sub(r'\.?\s*jimdo\.com\s*$', '', desc).strip()

    photo, all_photos = extract_images(soup)

    # Soft-404 : page sans contenu utile
    if ("n'existe malheureusement pas" in desc
            or (not photo and not desc and name == slug.replace('-', ' ').title())):
        return {"s": slug, "n": name, "_404": True, "p": "", "ps": [], "d": ""}

    ph = extract_photographer(soup, desc)

    return {
        "n":  name,
        "s":  slug,
        "p":  photo,
        "ps": all_photos,
        "ph": ph,
        "t":  extract_field(soup, ["Taille", "Longueur", "Taille maximale"]),
        "pr": extract_field(soup, ["Profondeur", "Prof"]),
        "l":  extract_field(soup, ["Lieu", "Lieux", "Localisation", "Localité"]),
        "d":  desc,
    }
