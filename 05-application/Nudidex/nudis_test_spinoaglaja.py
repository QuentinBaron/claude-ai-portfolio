import requests, json
from pathlib import Path
from bs4 import BeautifulSoup
import re

BASE_URL = "https://tahitinudi.jimdoweb.com/liste-des-espèces/"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; NudidexBot/1.0; educational research)"}
JSON_PATH = Path(__file__).parent / "nudis_scraped_full.json"

FIELD_LABELS = r'(?:Taille|Longueur|Profondeur|Prof|Lieu|Lieux|Localisation|Localit[eé]|Photo|Site|©)'

def extract_images(soup):
    content = soup.find(id="content_area") or soup
    imgs = []
    for img in content.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src: continue
        if "jimcdn.com" not in src and "jimdo" not in src: continue
        if any(x in src for x in ["logo","favicon","icon","sprite"]): continue
        src = re.sub(r"^http://", "https://", src)
        if src not in imgs: imgs.append(src)
    return (imgs[0] if imgs else ""), imgs

def extract_field(soup, labels):
    for el in soup.find_all(["p","li","td","div","span"]):
        t = el.get_text(" ", strip=True)
        for lbl in labels:
            m = re.search(rf'{lbl}\s*[:\-]\s*(.+)', t, re.I)
            if m:
                val = m.group(1).strip().split('\n')[0].strip()
                val = re.split(rf'\s+{FIELD_LABELS}\s*[:\-]', val, flags=re.I)[0].strip()
                val = val.rstrip(' .,;')
                if val and len(val) < 200: return val
    return ""

# URL correcte avec i-circumflex
slug_correct = "spînoaglaja-orientalis"
url = BASE_URL + slug_correct + "/"
print("Scraping :", url)

r = requests.get(url, headers=HEADERS, timeout=15)
print("Status :", r.status_code)

if r.status_code == 200:
    soup = BeautifulSoup(r.text, "lxml")
    name = ""
    for tag in ["h1","h2"]:
        el = soup.find(tag)
        if el:
            t = el.get_text(" ", strip=True)
            if 2 < len(t) < 120: name = t; break
    if not name: name = "Spinoaglaja orientalis"
    desc = ""
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) > 60 and "jimdo" not in t.lower(): desc = t; break
    desc = re.sub(r'Photo\s*:.*$', '', desc, flags=re.M).strip()
    photo, all_photos = extract_images(soup)
    print("Nom     :", name)
    print("Photo   :", photo[:80] if photo else "aucune")
    print("Desc    :", desc[:80] if desc else "aucune")

    # Mettre à jour le JSON
    with open(JSON_PATH, encoding="utf-8") as f:
        species = json.load(f)
    for sp in species:
        if sp.get("s") == "spinoaglaja-orientalis":
            sp["n"]  = name
            sp["p"]  = photo
            sp["ps"] = all_photos
            sp["d"]  = desc
            sp["t"]  = extract_field(soup, ["Taille","Longueur"])
            sp["pr"] = extract_field(soup, ["Profondeur","Prof"])
            sp["l"]  = extract_field(soup, ["Lieu","Lieux","Localisation"])
            print("JSON mis a jour.")
            break
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(species, f, ensure_ascii=False, indent=2)
    print("-> Lance maintenant : python deploy.py")
else:
    print("Echec.")
