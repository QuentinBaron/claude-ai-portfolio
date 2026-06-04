#!/usr/bin/env python3
"""Affiche la structure HTML autour de chaque image jimcdn trouvée sur une page espèce."""
import requests, re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
URL = "https://tahitinudi.jimdoweb.com/liste-des-espèces/atys-semistriatus/"

r = requests.get(URL, headers=HEADERS, timeout=15)
soup = BeautifulSoup(r.text, "lxml")

imgs = soup.find_all("img")
print(f"Total images trouvées : {len(imgs)}\n")

for i, img in enumerate(imgs):
    src = img.get("src") or img.get("data-src") or ""
    if "jimcdn.com" not in src:
        continue
    # Remonter les 4 parents et afficher leurs tags + classes
    parents = []
    node = img.parent
    for _ in range(5):
        if node is None or node.name is None:
            break
        cls = " ".join(node.get("class", []))
        nid = node.get("id", "")
        parents.append(f"<{node.name} class='{cls}' id='{nid}'>")
        node = node.parent
    print(f"[img {i}] {src[:80]}")
    print(f"  Parents: {' > '.join(reversed(parents))}")
    print()
