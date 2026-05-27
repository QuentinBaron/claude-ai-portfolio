#!/usr/bin/env python3
"""
Construit nudis_colors.json : base de données couleurs/motifs/morpho par espèce.
Sources : CLADE_HINTS (nudis_template_v2.html) + nudis_enriched.json + nudis_taxonomy.csv

Usage : python nudis_build_colors.py
Sortie : nudis_colors.json dans le même dossier
"""
import json, csv, re
from pathlib import Path

HERE = Path(__file__).parent

# ── Mapping ordre → morphologie (fallback si famille non mappée) ──────────────
MORPHO_MAP = {
    "Aeolida":        "filaments",
    "Dendronotida":   "filaments",
    "Janolina":       "filaments",
    "Sacoglossa":     "inconnu",           # hétérogène → priorité au mapping famille
    "Pleurobranchida":"filaments",
    "Doridida":       "panache_branchial",
    "Arminida":       "dos_lisse",
    "Aplysiida":      "gros_animal",
    "Anaspidea":      "gros_animal",
    "Cephalaspidea":  "coquille_visible",  # fallback si famille non listée
    "Umbraculida":    "coquille_visible",
    "Runcinida":      "limace_compacte",
    "Littorinimorpha":"limace_compacte",
}

# ── Mapping famille → morphologie (prioritaire sur l'ordre) ───────────────────
FAMILY_MORPHO_MAP = {
    # Sacoglossa — classement par famille (ordre trop varié)
    "Costasiellidae":  "filaments",        # cérates feuillus verts
    "Hermaeidae":      "filaments",        # cérates simples
    "Caliphyllidae":   "filaments",
    "Elysiidae":       "limace_compacte",  # corps plat aplati, pas de coquille
    "Plakobranchidae": "limace_compacte",
    "Limapontiidae":   "limace_compacte",
    "Oxynoidae":       "coquille_visible", # coquille fragile visible
    "Volvatellidae":   "coquille_visible",
    "Juliidae":        "coquille_visible",
    # Cephalaspidea — tous ont une coquille sauf Aglajidae et Gastropteridae
    "Aglajidae":       "limace_compacte",  # pas de coquille, queue fourchue
    "Gastropteridae":  "limace_compacte",  # voiles natatoires, pas de coquille
    "Haminoeidae":     "coquille_visible",
    "Bullidae":        "coquille_visible",
    "Aplustridae":     "coquille_visible",
    "Ringiculidae":    "coquille_visible",
    "Architectonicidae":"coquille_visible",
    # Pleurobranchida — branchie latérale, dos lisse (pas de panache dorsal)
    "Pleurobranchidae":"dos_lisse",
    "Berthellidae":    "dos_lisse",
    "Berthelliniidae": "dos_lisse",
    # Phyllidiidae — branchies sous le manteau (invisibles d'en haut), dos bosselé/lisse
    # Ne doit pas hériter panache_branchial de Doridida
    "Phyllidiidae":    "dos_lisse",
    "Phyllididae":     "dos_lisse",
}

# ── Adjacences couleur (miroir du template JS, blanc+bleu ajouté) ────────────
COLOR_ADJACENT_PY = {
    'rouge':       ['orange', 'rose', 'brun'],
    'orange':      ['rouge', 'jaune', 'rose', 'brun'],
    'bleu':        ['violet', 'vert', 'gris'],
    'violet':      ['rose', 'bleu', 'noir'],
    'rose':        ['rouge', 'violet', 'blanc'],
    'jaune':       ['orange', 'vert', 'blanc'],
    'vert':        ['jaune', 'bleu', 'brun'],
    'brun':        ['rouge', 'orange', 'gris', 'noir'],
    'gris':        ['blanc', 'noir', 'bleu'],
    'blanc':       ['gris', 'rose', 'jaune', 'bleu'],
    'noir':        ['brun', 'gris', 'violet'],
    'translucide': ['blanc', 'gris'],
    'irise':       ['blanc', 'bleu', 'violet'],
}

def auto_couleurs_adj(couleurs):
    """Derive couleurs_adj automatically from adjacency (excludes couleurs themselves)."""
    adj_set = set()
    for c in couleurs:
        for a in COLOR_ADJACENT_PY.get(c, []):
            if a not in couleurs:
                adj_set.add(a)
    return sorted(adj_set)

# ── Couleurs détectées (ordre = priorité si ambiguïté) ────────────────────────
COLOR_PATTERNS = [
    ("blanc",       r'\bblanc(?:he|s|hes)?\b|crèm[e]?\b|ivoire\b|pâle\b'),
    ("noir",        r'\bnoir(?:e|s|es)?\b|sombr[e]?\b|foncé[e]?\b'),
    ("rouge",       r'\brouge(?:s|âtre)?\b|rougeâtr\w*|écarlate\b|sang\b'),
    ("orange",      r'\borang[eé](?:s|é|ée|âtre)?\b|orangé\w*'),
    ("jaune",       r'\bjaune(?:s|âtre)?\b|jaunâtr\w*|doré[e]?\b|or\b'),
    ("vert",        r'\bvert(?:e|s|es|âtre)?\b|verdâtr\w*|émeraude\b'),
    ("bleu",        r'\bbleu(?:e|s|es|âtre|té)?\b|bleutée?\b|azur\b|cyan\b'),
    ("violet",      r'\bviolet(?:te|s|tes)?\b|violacé\w*|mauve\b|pourpre\b|lilas\b'),
    ("rose",        r'\brose(?:s|âtre)?\b|rosé[e]?\b|rosâtr\w*'),
    ("brun",        r'\bbrun(?:e|s|es|âtre)?\b|brunâtr\w*|marron\b|chocolat\b|beige\b'),
    ("gris",        r'\bgris(?:e|s|es|âtre)?\b|grisâtr\w*|argenté[e]?\b'),
    ("translucide", r'\btransluci\w+|transparent\w*'),
    ("irisé",       r'\birisé\w*|nacré[e]?\b|iridescent\w*'),
]

# ── Motifs détectés ───────────────────────────────────────────────────────────
MOTIF_PATTERNS = [
    ("lignes",   r'\bligne[s]?\b|bande[s]?\b|longitudinal\w*|transversal\w*|strié\w*|rayé\w*|raie[s]?\b'),
    ("points",   r'\bpoint[s]?\b|tache[s]?\b|ponctuation[s]?\b|moucheture[s]?\b|pustule[s]?\b'),
    ("bordure",  r'\bbordure[s]?\b|marge[s]?\b|liseré[s]?\b|périphériqu\w*|marginal\w*|contour\b'),
    ("cercles",  r'\bcercle[s]?\b|concentrique[s]?\b|anneau[x]?\b|annelé\w*'),
    ("tubercules",r'\btubercu\w+|bosse[s]?\b|proéminence[s]?\b|relief[s]?\b|épineux\b|épine[s]?\b'),
    ("uni",      r'\buni(?:forme)?\b|homogène\b|uniforme\b|monochrome\b'),
]

# ── Parsing taille ────────────────────────────────────────────────────────────
def parse_taille(txt):
    if not txt:
        return None
    txt = txt.replace(',', '.')
    # "X-Y cm" ou "X à Y cm"
    m = re.search(r'(\d+(?:\.\d+)?)\s*[-–à]\s*(\d+(?:\.\d+)?)\s*cm', txt)
    if m:
        return [float(m.group(1)), float(m.group(2))]
    # "jusqu'à X cm" ou "environ X cm" ou "X cm"
    m = re.search(r'(?:jusqu\'?à|environ|max\.?|≤)?\s*(\d+(?:\.\d+)?)\s*cm', txt)
    if m:
        v = float(m.group(1))
        return [None, v]
    return None

def extract_features(text):
    """Extrait couleurs et motifs d'un texte descriptif."""
    if not text:
        return [], []
    text_l = text.lower()
    couleurs = [name for name, pat in COLOR_PATTERNS if re.search(pat, text_l)]
    motifs   = [name for name, pat in MOTIF_PATTERNS  if re.search(pat, text_l)]
    return couleurs, motifs

# ── Extraction CLADE_HINTS depuis le HTML ─────────────────────────────────────
def load_clade_hints(html_path):
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    start = content.find("var CLADE_HINTS = {")
    end   = content.find("\n};", start) + 3
    block = content[start:end]
    hints = {}
    for m in re.finditer(r"'([^']+)'\s*:\s*'((?:[^'\\]|\\.)*)'", block):
        key = m.group(1)
        val = m.group(2).replace("\\'", "'")
        hints[key] = val
    print(f"  CLADE_HINTS chargés : {len(hints)} entrées")
    return hints

# ── Chargement des sources ────────────────────────────────────────────────────
html_path     = HERE / "nudis_template_v2.html"
enriched_path = HERE / "nudis_enriched.json"
csv_path      = HERE / "nudis_taxonomy.csv"

clade_hints = load_clade_hints(html_path)

with open(enriched_path, encoding="utf-8") as f:
    enriched = json.load(f)
enrich_by_slug = {sp["s"]: sp for sp in enriched}

# ── Construction de la base ───────────────────────────────────────────────────
# Coloration par defaut par famille (miroir de COLORATION_FAMILY du template JS)
COLORATION_FAMILY_PY = {
    # VIVES
    'Chromodorididae':'vives','Hexabranchidae':'vives','Facelinidae':'vives',
    'Flabellinidae':'vives','Polyceridae':'vives','Goniodorididae':'vives',
    'Vayssiereidae':'vives','Costasiellidae':'vives','Elysiidae':'vives',
    'Eubranchidae':'vives','Samlidae':'vives',
    # MOTIFS
    'Phyllidiidae':'motifs','Dorididae':'motifs','Discodorididae':'motifs',
    'Aegiridae':'motifs','Arminidae':'motifs','Aplustridae':'motifs',
    'Aglajidae':'motifs',
    # CAMOUFLAGE
    'Aeolidiidae':'camouflage','Pleurobranchidae':'camouflage','Aplysiidae':'camouflage',
    'Dolabriferidae':'camouflage','Dendrodorididae':'camouflage','Bornellidae':'camouflage',
    'Dotidae':'camouflage','Trinchesiidae':'camouflage',
    'Scyllaeidae':'camouflage','Tethydidae':'camouflage','Actinocyclidae':'camouflage',
    'Tritoniidae':'camouflage','Runcinidae':'camouflage','Limapontiidae':'camouflage',
    'Haminoeidae':'camouflage','Velutinidae':'camouflage','Bullidae':'camouflage',
    'Gastropteridae':'camouflage','Janolidae':'camouflage','Madrellidae':'camouflage',
}

output = {}
stats  = {"espece": 0, "genre": 0, "famille": 0, "ordre": 0, "aucune": 0}

strip_re = re.compile(r'^[\s▪️◽▫️🔴🟠🟡🟢🔵🟣⚫⚪🔶🔷▪▫]+')

with open(csv_path, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        slug  = row.get("slug", "").strip()
        ordre = row.get("ordre", "").strip()
        fam   = row.get("famille", "").strip()
        nom_raw = row.get("nom_scientifique", "").strip()
        nom   = strip_re.sub("", nom_raw).strip()
        genre = nom.split()[0] if nom else ""

        sp_data = enrich_by_slug.get(slug, {})
        desc    = sp_data.get("d", "") or ""
        taille_txt = sp_data.get("t", "") or ""

        # Cherche les textes disponibles par priorité
        hint_espece  = clade_hints.get(nom, "")
        hint_genre   = clade_hints.get(genre, "")
        hint_famille = clade_hints.get(fam, "")
        hint_ordre   = clade_hints.get(ordre, "")

        # Combine tous les textes disponibles pour extraire features
        # Source principale : espèce > genre > famille > ordre
        # Description de terrain s'ajoute en bonus
        if hint_espece:
            source = "espece"
            primary_text = hint_espece
        elif hint_genre:
            source = "genre"
            primary_text = hint_genre
        elif hint_famille:
            source = "famille"
            primary_text = hint_famille
        elif hint_ordre:
            source = "ordre"
            primary_text = hint_ordre
        else:
            source = "aucune"
            primary_text = ""

        stats[source] += 1

        # Extraction features (texte principal + description terrain)
        combined = " ".join(filter(None, [primary_text, desc]))
        couleurs, motifs = extract_features(combined)

        # Taille
        taille = parse_taille(taille_txt)

        output[slug] = {
            "nom":       nom,
            "ordre":     ordre,
            "famille":   fam,
            "genre":     genre,
            "morpho":    FAMILY_MORPHO_MAP.get(fam) or MORPHO_MAP.get(ordre, "inconnu"),
            "taille":    taille,
            "couleurs":     couleurs,
            "couleurs_adj": auto_couleurs_adj(couleurs),
            "motifs":       motifs,
            "coloration":   COLORATION_FAMILY_PY.get(fam, ""),
            "source":       source,
        }

# ── Fusion avec overrides manuels (nudis_species_overrides.json) ──────────────
overrides_path = HERE / "nudis_species_overrides.json"
if overrides_path.exists():
    manual = json.loads(overrides_path.read_text(encoding="utf-8"))
    applied = 0
    for slug, data in manual.items():
        if slug in output:
            if "couleurs"     in data: output[slug]["couleurs"]     = data["couleurs"]
            if "couleurs_adj" in data:
                output[slug]["couleurs_adj"] = data["couleurs_adj"]
            elif "couleurs" in data:
                # recalcule les adj si couleurs manuelles mais pas adj manuelles
                output[slug]["couleurs_adj"] = auto_couleurs_adj(data["couleurs"])
            if "coloration"  in data: output[slug]["coloration"]  = data["coloration"]
            if "l1_override" in data: output[slug]["l1_override"] = data["l1_override"]
            applied += 1
    print(f"  Overrides manuels appliques : {applied}/{len(manual)}")

# ── Sortie ────────────────────────────────────────────────────────────────────
out_path = HERE / "nudis_colors.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

total = len(output)
print(f"\nOK nudis_colors.json : {total} espèces")
print(f"\nSources :")
for k, v in stats.items():
    print(f"  {k:<10} : {v:>3} ({100*v//total}%)")

# Couverture couleurs et taille
avec_couleurs = sum(1 for v in output.values() if v["couleurs"])
avec_taille   = sum(1 for v in output.values() if v["taille"])
print(f"\nCouverture :")
print(f"  Couleurs : {avec_couleurs}/{total} ({100*avec_couleurs//total}%)")
print(f"  Taille   : {avec_taille}/{total}  ({100*avec_taille//total}%)")
