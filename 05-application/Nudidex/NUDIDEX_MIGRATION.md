# NUDIDEX — Document de migration de session
*Généré le 2026-06-02 — Reprendre exactement ici dans la nouvelle session*

---

## 1. CONTEXTE PROJET

**Nudidex** : PWA single-file d'identification des nudibranches de Polynésie Française.  
**URL live** : https://quentinbaron.github.io/claude-ai-portfolio/05-application/Nudidex/  
**Repo** : `D:\Documents\Claude\Projects\Project management\Code_test\claude-ai-portfolio\`  
**Dossier de travail** : `05-application\Nudidex\`  

**Stack** : HTML5 + CSS3 + JavaScript vanilla (single-file) · Python pipeline · GitHub Pages  
**Utilisateur** : Quentin Baron, ingénieur/scientifique/psychologue, Tahiti  
**Préférence exécution** : Claude écrit le code, Quentin exécute en local via `cmd`  
**Syntaxe cmd Windows** : `cd /d "D:\..."` (pas `cd d/ "..."`)

---

## 2. ARCHITECTURE FICHIERS

```
05-application/Nudidex/
├── nudis_template_v2.html      # Template source (4604 lignes) — NE PAS modifier index.html
├── index.html                  # Build généré — ne pas éditer
├── nudis_traits_editor.html    # Éditeur local traits morpho (135KB, photos embarquées)
├── nudis_enriched.json         # BDD espèces enrichie (308KB, 423 espèces)
├── nudis_taxonomy.csv          # CSV taxonomique (slug, ordre, famille, nom_commun, worms_aphia_id)
├── nudis_scraped_full.json     # Source scraping
├── nudis_colors.json           # BDD couleurs par espèce
├── nudis_traits.json           # ABSENT — à générer via l'éditeur puis exporter
├── run_pipeline.py             # Pipeline : merge CSV+JSON → index.html + inject traits + inject photos éditeur
├── deploy.py                   # Pipeline complet + git push
└── nudis_fix_orders.py         # Corrections taxonomiques (FIXES / FAMILY_FIXES / NAME_FIXES)
```

**Protocole de déploiement** :
```cmd
cd /d "D:\Documents\Claude\Projects\Project management\Code_test\claude-ai-portfolio\05-application\Nudidex"
python deploy.py
```
`deploy.py` appelle dans l'ordre : `nudis_fix_orders.py` → `nudis_clean_fields.py` → `run_pipeline.py` → `nudis_build_colors.py` → vérification → git push.

**`run_pipeline.py` — placeholders injectés** :
- `__SPECIES__` → `nudis_enriched.json` (données espèces)
- `__TRAITS__` → `nudis_traits.json` si présent, sinon `{}`
- `__BUILD__` → timestamp version
- `__EDITOR_PHOTOS__` → dans `nudis_traits_editor.html` (dict famille→photos)

---

## 3. ARCHITECTURE TEMPLATE (nudis_template_v2.html)

### Vues principales
- **Liste** (`view-table`) : tableau filtrable avec colonnes nom/famille/ordre/notes
- **Nudidex** (`view-cards`) : cartes pokémon-style avec photos
- **Jouer** : jeu progressif de devinettes
- **Identifier** : identificateur par questions binaires progressives
- **Observer** : formulaire d'observation terrain (mode simple + mode expert)

### Données globales JS
```js
var SPECIES = JSON.parse(document.getElementById('sd').textContent);
var TRAITS  = JSON.parse(document.getElementById('td').textContent) || {};
```

### Lightbox
- `openLb(slug)` → ouvre la fiche espèce
- Navigation inter-espèce : flèches latérales (`lbNavSp`), swipe, clavier
- `object-fit: contain` pour les photos (pas de crop)

### Lexique taxonomique (bottom sheet)
- Bouton 📖 dans obs-header → `openLex(tabId)` → bottom sheet 4 onglets (Couleurs, Textures, Motifs, Template)
- Liens contextuels dans l'Observer : `lexLink(tabId)` génère un mini-bouton 📖 next au label

---

## 4. MODULE OBSERVER — ÉTAT ACTUEL

### Mode simple (7 étapes)
Steps : Contexte → Morphologie → Coloration → Rhinophores → Branchies → Photos&notes → Récapitulatif  
Stepper horizontal cliquable en haut de chaque step (comme mode expert).  
Fonctionnalités actives : date/heure selects, tentacules oraux, liens lexique contextuels, nuancier SWATCH_COLORS (13 teintes basiques).

**OBS_FLAGS** (refait) — tableau d'objets `{val, hint}` :
- "Deux appendices en 'oreilles' sur la tête" → Thecacera
- "Queue en fourche (bifide)" → Aglajidae
- "Voiles natatoires latéraux" → Gastropteridae
- "Tubercules bicolores fermes sur le dos" → Phyllidiidae
- "Nage activement en pleine eau" → pélagiques
- Ponte, accouplement, groupe (sans hint)

### Mode Expert (11 étapes Gosliner)
Steps : Contexte → Dimensions → Forme → Notum → Marges → Rhinophores → Branchies → Tentacules → Pied → Variations → Récapitulatif

**État obsExpertState** — structure imbriquée :
```js
{
  date, site, depth, substrats[], proie, eclairage,
  taille_mm, taille_range, forme, manteau_debord, structure,
  notum: { zones[], texture[], motif[], translucidite },
  marge: { largeur, zones[], bord },
  rhino: { forme, nb_lamelles, gaine, zones[] },
  branchie: { nb_branches, zones[], pointes, bipennatees },
  cerates: { dispo, forme, zones[], cnidosacs },
  dos: { branchie_lat, cretes_type, papilles_inter, coquille_pos, coquille_transp, coquille_taille, couleur_dessous },
  tentacules: { present, zones[] },
  pied: { zones[], texture },
  variations, flags[], photos[]
}
```

**Zone builder** — chaque zone a 4 champs : `zone_label` / `motif` / `couleur` / `translucidite`  
Couleurs : picker custom avec swatches colorés (`expColPickerHtml(key, idx, currentColor)`)  
Résumé auto-généré : emplacement → motif → couleur → translucidité

**Etape Branchies (step 6)** — dynamique selon `structure` :
- `panache` → questions panache
- `cerates` → questions cérates
- `dos_lisse` → branchie latérale (Pleurobranchidae)
- `dos_cretes` → type crêtes (continues/discontinues/parapodes), pas de branchie lat.
- `coquille` → position (externe/semi/interne/limpet), transparence, taille relative

**Export** : FR (vert) affiché avant EN (neutre gris). Bouton "📄 Exporter PDF" → HTML blob → print dialog.  
Email → `mailto:baroncube@gmail.com` pré-rempli FR+EN.

**EXP_NESTED** — mapping clés plates → chemins dans obsExpertState :
Inclut `dos_cretes_type`, `dos_papilles_inter`, `coquille_pos`, `coquille_transp`, `coquille_taille`.

**Espèces candidates** — fonction `expCandidates()` :
Lit `TRAITS` (format tri-state v2) → `traitScore(sp, obs)` → tri par score décroissant.  
Scores : structure=+40/-999, tentacules=+30/-999, rhinophore=±15, texture=±10.  
Pélagiques exclus si "Nage en pleine eau" non sélectionné.  
Fallback si TRAITS vide → filtre basique par ordre.

---

## 5. SYSTÈME TRAITS MORPHOLOGIQUES — CHANTIER EN COURS

### Architecture
**Éditeur local** : `nudis_traits_editor.html` (standalone, file://)  
**BDD** : `nudis_traits.json` (à générer via export dans l'éditeur) → embarqué dans index.html via `__TRAITS__`  
**Photos** : embarquées dans l'éditeur via `__EDITOR_PHOTOS__` (injecté par `run_pipeline.py`)

### Format tri-state v2 (format actuel dans l'éditeur)
```json
{
  "Chromodorididae": {
    "_validated": false,
    "_order": "Doridida",
    "_n": 46,
    "structure":  {"panache":1, "cerates":2, "dos_lisse":2, "dos_cretes":2, "coquille":2, "aucune":2},
    "tentacules": {"oui":1, "non":2, "variable":0},
    "pelagique":  false,
    "rhinophore": {"Lamellé perfolié":1, "Lamellé annulé":0, ...},
    "texture":    {"Lisse":1, "Tuberculé":0, ...},
    "cerates_dispo": {},
    "cerates_forme": {},
    "branchie_lat": false,
    "taille": "petit-moyen",
    "notes": "..."
  }
}
```
États : `0` = neutre, `1` = inclure (+score), `2` = exclure (-999)

**Rétrocompatibilité** : `traitScore()` dans le template gère AUSSI l'ancien format (`excl` array + string pour structure/tentacules).

### État actuel du pipeline d'injection photos
`run_pipeline.py` — Étape 3 ajoutée :
1. Lit `nudis_enriched.json` après enrichissement
2. Construit `photos_db = {famille: [{u:url, n:nom, f:1|0}]}`
3. Injecte dans `nudis_traits_editor.html` en remplaçant `__EDITOR_PHOTOS__`

**Problème connu** : Le placeholder `__EDITOR_PHOTOS__` est **déjà remplacé** dans le fichier actuel (grep retourne 0 occurrences, PHOTOS_DB présent 5 fois). Cela signifie soit :
- Le pipeline a été exécuté avec succès et les photos sont déjà embarquées, OR
- Le placeholder a été remplacé par la chaîne littérale `__EDITOR_PHOTOS__` disparaissant sans données réelles.

**Action requise à la reprise** :
1. Vérifier l'état du volet photos dans l'éditeur (ouvrir `nudis_traits_editor.html`)
2. Si les photos ne s'affichent pas → relancer `python run_pipeline.py`
3. Si `nudis_traits.json` est absent → utiliser l'éditeur pour valider les familles et exporter

### Familles pré-remplies dans l'éditeur
52 familles encodées depuis Gosliner (toutes les familles de PF). Données dans `KNOWN` JS constant dans l'éditeur. Chaque famille a structure/tentacules/rhinophore/texture/notes pré-remplis.

### Workflow utilisateur cible
1. Ouvrir `nudis_traits_editor.html` → photos auto-chargées
2. Naviguer famille par famille (ou cliquer en-tête d'ordre pour tout sélectionner)
3. Valider/corriger les traits pré-remplis (tri-state : neutre→vert→rouge)
4. Cocher "Validée" pour chaque famille traitée
5. "Exporter nudis_traits.json" → placer dans le dossier Nudidex
6. `python deploy.py` → traits embarqués dans index.html → filtre amélioré en prod

---

## 6. SCORING ET FILTRAGE

### `traitScore(sp, obs)` dans nudis_template_v2.html
```js
// obs = {structure, tentacules, nage, rhinophore, texture[]}
// Retourne score (>=0 = candidat) ou -999 (exclusion absolue)
```

### `expCandidates()` — logique complète
1. Score chaque espèce avec photo (`sp.p` requis)
2. Trie par score décroissant
3. Si TRAITS disponibles : garde score ≥ 0, max 25 espèces
4. Si TRAITS vides : fallback filtre par ordre selon structure sélectionnée

### Cas Costasiella (bug résolu)
Costasiella = Sacoglossa, famille Costasiellidae. Structure = cérates MAIS tentacules = non.  
Dans TRAITS : `structure.cerates=1`, `tentacules.non=1` → score +70.  
Aeolidida avec tentacules : `tentacules.oui=1` → si obs.tentacules=non → score -999 pour Aeolidida.  
Résultat : Costasiella apparaît en tête quand structure=cérates + tentacules=non.

---

## 7. CORRECTIONS TAXONOMIQUES EN ATTENTE

À encoder dans `nudis_fix_orders.py` avant prochain déploiement :

| Slug | Correction |
|---|---|
| samla-bicolor | famille: Haminoeidae → Samlidae |
| halgerda-sp.2 | nom: → Halgerda berberiani · famille: → Discodorididae |
| phycophila-euchlora | famille: Oxynoidae → Aplysiidae |
| madrella-ferruginosa | ordre: Janolina → Aeolida |
| toutes Anaspidea | ordre: Anaspidea → Aplysiida |
| toutes Cuthonidae | famille: Cuthonidae → Trinchesiidae |
| coriocella-nigra | SUPPRIMER (pas un opisthobranch) |
| mourgona-sp.1/sp.2 | famille: Philinidae → Caliphyllidae |

---

## 8. BACKLOG FEATURES (priorités)

### Immédiates (prochaine session)
1. **Valider que les photos s'affichent dans l'éditeur** — voir §5
2. **Exporter nudis_traits.json** depuis l'éditeur après validation de quelques familles clés (Chromodorididae, Phyllidiidae, Costasiellidae, Phylliroidae en priorité)
3. **Vérifier que le filtre fonctionne** en prod après deploy avec traits

### Observer — backlog validé
- Localisation GPS (pertinence à confirmer, utile pour iNaturalist)
- Nuancier colorimétrique interactif Option A (grille swatches → nom Gosliner) — intégration lexique + mode expert
- Substrat : aide visuelle pour non-expert (basse priorité)

### Autres features Nudidex
- Clé dichotomique morphologique (nouveau jeu)
- Mode expert Observer : nuancier complet en saisie (après nuancier lexique)
- Élargir la recherche (mode relaxé) — pertinent une fois TRAITS bien couvert

---

## 9. DÉCISIONS TECHNIQUES NON-ÉVIDENTES

**Single-file HTML** : Tout dans `nudis_template_v2.html`. `index.html` = build généré. Ne jamais éditer `index.html` directement.

**Variables JS définies après `init()`** : Pattern `(window.VAR||{})` pour accès sécurisé. Appeler `buildCards()` après dict si nécessaire.

**obsDateSelects() / obsUpdateDate()** : Les selects date ne re-renderisent pas le step entier au changement — ils mettent à jour `obsState.date` via `obsUpdateDate()` directement.

**expZoneSet()** : Ne re-render PAS le step entier — met à jour le DOM du résumé `#exp-sum-{key}` et le trigger couleur `#ect-{key}-{idx}` directement. Cela évite la perte de focus sur les selects.

**Lexique bottom sheet** : `openLex(tabId)` accepte un paramètre optionnel pour naviguer directement sur le bon onglet. Appelle `lexTab(tabId, btn)` en trouvant le bon bouton via son attribut `onclick`.

**Format TRAITS** : L'éditeur génère le format tri-state v2 (objets `{val:0|1|2}`). Le template gère les deux formats (v1 avec `excl[]` + v2) pour rétrocompatibilité.

**Photos dans l'éditeur** : Embarquées par `run_pipeline.py` via placeholder `__EDITOR_PHOTOS__`. Le placeholder disparaît après la première injection — donc si on modifie le template de l'éditeur après injection, il faudra réinjecter manuellement ou relancer le pipeline.

**deploy.py** — Vérification post-merge git : si le merge écrase `index.html`, le pipeline se relance automatiquement.

---

## 10. CONTRAINTES IMPLICITES

- **Pas de couleurs complexes dans TRAITS** : SWATCH_COLORS (13 teintes basiques) pour mode simple uniquement. Les couleurs Gosliner précises sont dans le lexique T5.1 + le mode expert. La BDD couleurs par espèce (`nudis_colors.json`) est séparée et déjà alimentée.
- **L'éditeur traits n'est pas déployé** : local uniquement, jamais sur GitHub Pages.
- **Tolérance null dans les traits** : Un trait non rempli (état 0 = neutre) ne pénalise pas le score. Seul l'état 2 (rouge) entraîne l'exclusion absolue.
- **Photos dans l'éditeur** : Sources depuis tahitinudi.jimdoweb.com (URLs dans `sp.p`). Pas de proxy, chargement direct depuis le HTML local.
- **Structure `sp.p`** : Peut être string ou array. Le pipeline gère les deux.

---

## 11. COMMANDES DE RÉFÉRENCE

```cmd
:: Déploiement complet
cd /d "D:\Documents\Claude\Projects\Project management\Code_test\claude-ai-portfolio\05-application\Nudidex"
python deploy.py

:: Pipeline seul (sans git)
python run_pipeline.py

:: Dry-run (build sans push)
python deploy.py --dry-run

:: Vérifier les photos dans l'éditeur
:: → Double-clic sur nudis_traits_editor.html dans l'Explorateur
:: → Si photos absentes : relancer python run_pipeline.py
```

**Repo GitHub** : https://github.com/quentinbaron/claude-ai-portfolio  
**App live** : https://quentinbaron.github.io/claude-ai-portfolio/05-application/Nudidex/
