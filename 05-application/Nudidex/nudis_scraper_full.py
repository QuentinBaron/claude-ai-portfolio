#!/usr/bin/env python3
"""
nudis_scraper_full.py
Scrape toutes les espèces listées dans nudis_taxonomy.csv depuis tahitinudi.jimdoweb.com
et produit nudis_scraped_full.json.

Prérequis :
    pip install requests beautifulsoup4 lxml

Usage :
    python nudis_scraper_full.py

Paramètres :
    PAUSE   : secondes entre requêtes (politesse serveur)
    WORKERS : parallélisme (déconseillé > 3 pour Jimdo)
"""
import json, csv, time, re, os, sys
import unicodedata
import urllib.parse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installe d'abord : pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL   = "https://tahitinudi.jimdoweb.com/liste-des-espèces/"
PAUSE      = 1.2          # secondes entre requêtes
CSV_PATH   = Path(__file__).parent / "nudis_taxonomy.csv"
OUT_JSON   = Path(__file__).parent / "nudis_scraped_full.json"
RESUME_JSON = Path(__file__).parent / "nudis_scrape_progress.json"  # reprise en cas d'interruption

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NudidexBot/1.0; educational research)"
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def normalize_slug(s):
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")

def extract_images(soup):
    """Retourne (photo_principale, [toutes_photos])"""
    # Sur Jimdo, les photos d'espèces sont dans id='content_area'
    # Le bandeau du site est dans id='cc-website-logo' — à exclure
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
    # Dans les légendes / figcaption
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

FIELD_LABELS = r'(?:Taille|Longueur|Profondeur|Prof|Lieu|Lieux|Localisation|Localit[eé]|Photo|Site)'

def extract_field(soup, labels):
    """Cherche un champ (Taille, Profondeur, Lieu…) dans les balises de texte."""
    for el in soup.find_all(["p", "li", "td", "div", "span"]):
        t = el.get_text(" ", strip=True)
        for lbl in labels:
            m = re.search(rf'{lbl}\s*[:\-]\s*(.+)', t, re.I)
            if m:
                val = m.group(1).strip().split('\n')[0].strip()
                # Tronquer avant le prochain label connu (ex: "2 m Taille : 30 cm" → "2 m")
                val = re.split(rf'\s+{FIELD_LABELS}\s*[:\-]', val, flags=re.I)[0].strip()
                val = val.rstrip(' .,;')
                if val and len(val) < 200:
                    return val
    return ""

def slug_variants(slug):
    """Génère les variantes d'URL à essayer pour un slug donné."""
    def clean(s):
        """Points → tirets, puis supprime les tirets doubles."""
        s = s.replace(".", "-")
        s = re.sub(r"-+", "-", s)
        return s.strip("-")

    # Variante 1 : slug tel quel
    v1 = slug
    # Variante 2 : points → tirets, tirets doubles supprimés (sp.-1 → sp-1)
    v2 = clean(slug)
    # Variante 3 : suppression des accents + même nettoyage
    v3_base = unicodedata.normalize("NFD", slug)
    v3_base = "".join(c for c in v3_base if unicodedata.category(c) != "Mn")
    v3 = clean(v3_base)
    # Variante 4 : sans accents, slug brut (sans toucher aux points)
    v4 = v3_base.strip()
    # Dédoublonner en gardant l'ordre
    seen, variants = set(), []
    for v in [v1, v2, v3, v4]:
        if v not in seen:
            seen.add(v)
            variants.append(v)
    return variants

def scrape_species(slug):
    """Scrape une page espèce et retourne un dict."""
    r = None
    used_slug = slug
    for url_slug in slug_variants(slug):
        url = BASE_URL + url_slug + "/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except Exception as e:
            return {"s": slug, "n": slug, "_error": str(e)}
        if resp.status_code != 404:
            r = resp
            used_slug = url_slug
            break

    if r is None or r.status_code == 404:
        return {"s": slug, "n": slug, "_404": True, "p": "", "ps": [], "d": ""}

    soup = BeautifulSoup(r.text, "lxml")

    # Nom scientifique : h1 ou h2 de la page
    name = ""
    for tag in ["h1", "h2"]:
        el = soup.find(tag)
        if el:
            t = el.get_text(" ", strip=True)
            if len(t) > 2 and len(t) < 120:
                name = t; break
    if not name:
        name = slug.replace("-", " ").title()

    # Description : premier gros paragraphe
    desc = ""
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) > 60 and "jimdo" not in t.lower():
            desc = t; break

    # Nettoyage description
    desc = re.sub(r'Photo\s*:.*$', '', desc, flags=re.M).strip()
    desc = re.sub(r'\.?\s*jimdo\.com\s*$', '', desc).strip()

    photo, all_photos = extract_images(soup)
    # Soft-404 : page sans contenu utile
    if "n'existe malheureusement pas" in desc or (not photo and not desc and name == slug.replace('-',' ').title()):
        return {"s": slug, "n": name, "_404": True, "p": "", "ps": [], "d": ""}
    ph = extract_photographer(soup, desc)
    taille    = extract_field(soup, ["Taille", "Longueur", "Taille maximale"])
    profondeur = extract_field(soup, ["Profondeur", "Prof"])
    lieu      = extract_field(soup, ["Lieu", "Lieux", "Localisation", "Localité"])

    return {
        "n":  name,
        "s":  slug,
        "p":  photo,
        "ps": all_photos,
        "ph": ph,
        "t":  taille,
        "pr": profondeur,
        "l":  lieu,
        "d":  desc,
    }


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    # Supprimer le fichier de reprise potentiellement corrompu au premier lancement propre
    # (commenter ces 3 lignes si tu veux reprendre une session interrompue)
    # if RESUME_JSON.exists():
    #     RESUME_JSON.unlink()

    # Lire les slugs depuis le CSV
    slugs = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            s = row.get("slug", "").strip()
            if s:
                slugs.append(s)
    print(f"CSV : {len(slugs)} slugs à scraper")

    # Reprise depuis sauvegarde
    done = {}
    if RESUME_JSON.exists():
        with open(RESUME_JSON, encoding="utf-8") as f:
            done = {sp["s"]: sp for sp in json.load(f)}
        print(f"Reprise : {len(done)} déjà scrapés")

    results = list(done.values())
    done_slugs = set(done.keys())
    todo = [s for s in slugs if s not in done_slugs]
    print(f"Restant : {len(todo)} espèces")

    for i, slug in enumerate(todo):
        print(f"[{i+1}/{len(todo)}] {slug}", end=" ... ", flush=True)
        sp = scrape_species(slug)
        if sp.get("_404"):
            print("404")
        elif sp.get("_error"):
            print(f"ERROR: {sp['_error']}")
        else:
            has_photo = "✓" if sp.get("p") else "✗"
            print(f"{sp['n'][:40]}  photo:{has_photo}")
        results.append(sp)

        # Sauvegarde intermédiaire toutes les 10 espèces
        if (i + 1) % 10 == 0:
            with open(RESUME_JSON, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(PAUSE)

    # Sauvegarde finale
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Stats
    total   = len(results)
    with_p  = sum(1 for s in results if s.get("p"))
    errors  = sum(1 for s in results if s.get("_error"))
    not_found = sum(1 for s in results if s.get("_404"))
    print(f"\n{'='*50}")
    print(f"Total    : {total}")
    print(f"Avec photo : {with_p}")
    print(f"404      : {not_found}")
    print(f"Erreurs  : {errors}")
    print(f"\nSortie → {OUT_JSON}")

    # Nettoyage fichier de reprise
    if RESUME_JSON.exists():
        RESUME_JSON.unlink()

if __name__ == "__main__":
    main()
