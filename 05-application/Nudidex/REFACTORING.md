# Nudidex — Problèmes structurels à corriger

> Généré par analyse de graphe de connaissance (graphify) sur les 42 fichiers du projet.  
> À utiliser comme brief de refactoring dans une session de développement.

---

## Contexte projet (pour Claude sans contexte)

Nudidex est une PWA single-file (index.html, 441 KB) qui répertorie 423 espèces de nudibranches de Polynésie française. Le projet a deux parties :

1. **Pipeline Python** (scripts nudis_*.py) : scraping → nettoyage → enrichissement taxonomique → déploiement
2. **Frontend** (nudis_template_v2.html → index.html généré) : JavaScript vanilla, zéro dépendance

Le pipeline de déploiement est : `python deploy.py` → appelle dans l'ordre :
```
nudis_fix_orders.py → nudis_clean_fields.py → run_pipeline.py → nudis_build_colors.py → git push
```

---

## Problèmes prioritaires

---

### P1 — Duplication du scraper entre deux fichiers (critique)

**Fichiers concernés :** `nudis_scraper_full.py` et `nudis_fix_slugs.py`

Ces deux fichiers contiennent les mêmes fonctions copiées-collées :

| Fonction dupliquée | Divergence connue |
|---|---|
| `normalize_slug()` | Aucune |
| `slug_variants()` | fix_slugs a une variante accentuée (`spíno`) en plus |
| `extract_images()` | Aucune |
| `extract_photographer()` | Aucune |
| `extract_field()` | fix_slugs a `©` dans FIELD_LABELS en plus |
| `scrape_species()` | Légères différences dans la gestion des soft-404 |
| `FIELD_LABELS` (regex) | Définie aussi dans `nudis_clean_fields.py` — 3 copies au total |

**Correction à faire :**
- Créer `nudis_scraper_utils.py` contenant : `normalize_slug`, `slug_variants`, `extract_images`, `extract_photographer`, `extract_field`, `FIELD_LABELS`
- Remplacer les définitions locales dans scraper_full et fix_slugs par `from nudis_scraper_utils import ...`
- Résoudre les divergences : garder la variante accentuée de slug_variants, garder `©` dans FIELD_LABELS

---

### P2 — 4 clients WoRMS indépendants (critique)

**Fichiers concernés :** `nudis_enrich_all_aphia.py`, `nudis_verify_worms.py`, `nudis_check_3.py`, `nudis_fix_aphia.py`

La fonction `extract_order()` qui parcourt l'arbre de classification WoRMS est copiée-collée **3 fois** sous 3 noms différents (`extract_order`, `extract_order_from_classification`, `extract_order`). Logique identique dans les trois.

| Script | Fonctions WoRMS qu'il définit |
|---|---|
| `nudis_enrich_all_aphia.py` | `search_aphia()`, `get_order()`, `extract_order()` |
| `nudis_verify_worms.py` | `get_worms_record()`, `get_worms_classification()`, `extract_order_from_classification()` |
| `nudis_check_3.py` | `search_worms()`, `get_classification()`, `extract_order()` |
| `nudis_fix_aphia.py` | `search_worms()` |

**Correction à faire :**
- Créer `nudis_worms.py` avec : `search_aphia(name)`, `get_record(aphia_id)`, `get_classification(aphia_id)`, `extract_order(classif)`
- Les 4 scripts importent depuis `nudis_worms`
- L'implémentation de référence pour `extract_order` est dans `nudis_enrich_all_aphia.py` (la plus complète, avec gestion "Nudibranchia" générique)

---

### P3 — nudis_normalize_orders.py absent du pipeline de déploiement (bug silencieux)

**Fichier concerné :** `nudis_normalize_orders.py`

Ce script normalise les noms d'ordres WoRMS vers les conventions Nudidex :
```python
NORM = {
    "Aeolidina":    "Aeolida",
    "Dendronotina": "Dendronotida",
    "Arminina":     "Arminida",
    "Janolina":     "Dendronotida",
}
```
**Il n'est jamais appelé par deploy.py.** Ces normalisations ne s'appliquent que si on le lance manuellement, et sont écrasées au prochain merge CSV+JSON.

`nudis_fix_orders.py` a déjà `ORDER_RENAMES = {"Anaspidea": "Aplysiida"}` — même pattern, dict incomplet.

**Correction à faire :**
- Fusionner `NORM` de nudis_normalize_orders.py dans `ORDER_RENAMES` de `nudis_fix_orders.py`
- Vérifier le conflit potentiel : `Janolina` est dans NORM (→ Dendronotida) ET dans FIXES de fix_orders (espèces individuelles → Janolina). Pas de conflit direct car FIXES cible des slugs, ORDER_RENAMES cible des valeurs d'ordre.
- Supprimer `nudis_normalize_orders.py`

---

### P4 — Corrections d'urgence hors pipeline (données incorrectes sur deploy propre)

**Fichiers concernés :** `nudis_restore_csv.py`, `nudis_fix_aphia.py`

Ces scripts contiennent des corrections hard-codées qui n'ont **jamais été intégrées** dans le pipeline principal :

`nudis_restore_csv.py` :
```python
ORDER_FIXES = {
    "cephalopyge-trematoides":    "Dendronotida",   # absent de fix_orders.py
    "dermatobranchus-fortunatus": "Arminida",        # absent de fix_orders.py
}
```

`nudis_fix_aphia.py` + `nudis_restore_csv.py` :
```python
# AphiaIDs corrects — absents de nudis_taxonomy.csv en tant que données permanentes
"elysia-nealae":       "494460"
"embletonia-gracilis": "534076"
"julia-exquisita":     "215227"
"julia-zebra":         "492585"
```

**Correction à faire :**
- Ajouter `"cephalopyge-trematoides"` et `"dermatobranchus-fortunatus"` dans `FIXES` de `nudis_fix_orders.py`
- Vérifier que ces AphiaIDs sont bien présents dans `nudis_taxonomy.csv` (colonne `worms_aphia_id`)
- Une fois intégré, ces scripts n'ont plus de raison d'être (voir P5)

---

### P5 — Scripts orphelins à archiver

**Fichiers à déplacer dans `archive/` ou à supprimer :**

| Fichier | Raison |
|---|---|
| `nudis_check_3.py` | Vérification ponctuelle de 3 espèces hardcodées, objectif atteint |
| `nudis_fix_aphia.py` | Fix one-shot de 4 AphiaIDs — à intégrer dans fix_orders (P4) |
| `nudis_extract_spa.py` | Investigation de l'architecture SPA Jimdo — objectif atteint, script inutile |
| `nudis_restore_csv.py` | Outil d'urgence — corrections à intégrer dans pipeline (P4), conserver en archive |
| `spa_debug_home.html` | Output de nudis_extract_spa.py — fichier de debug |
| `spa_debug_species.html` | Output de nudis_extract_spa.py — fichier de debug |
| `nudis_normalize_orders.py` | À supprimer après fusion dans fix_orders (P3) |

---

### P6 — nudis_taxonomy.csv modifié en place sans backup (risque de corruption)

**Fichier concerné :** `nudis_taxonomy.csv`

C'est le fichier le plus référencé du projet (6 scripts le lisent/modifient). Il est modifié en place par fix_orders, enrich_all_aphia, fix_slugs, normalize_orders — sans sauvegarde préalable. Une corruption est déjà arrivée (d'où nudis_restore_csv.py).

`deploy.py` fait déjà un `git add` et `git commit` à la fin — mais uniquement pour `index.html` et `nudis_colors.json`.

**Correction à faire :**
- Dans `deploy.py`, ajouter `nudis_taxonomy.csv` à la ligne `git add` :
  ```python
  run("git add 05-application/Nudidex/index.html 05-application/Nudidex/nudis_colors.json 05-application/Nudidex/nudis_taxonomy.csv", cwd=REPO_DIR)
  ```
- Ou ajouter un backup automatique en début de deploy : `shutil.copy(CSV_PATH, CSV_PATH.with_suffix('.csv.bak'))`

---

## Ordre d'exécution recommandé

```
1. P3  — fusionner nudis_normalize_orders dans fix_orders        (5 min, zéro risque)
2. P4  — intégrer corrections d'urgence dans fix_orders + CSV    (10 min, vérifier CSV après)
3. P6  — ajouter CSV dans git add de deploy.py                   (2 min, zéro risque)
4. P1  — créer nudis_scraper_utils.py                            (30 min, tester avec deploy --dry-run)
5. P2  — créer nudis_worms.py                                    (30 min, tester enrich_all_aphia)
6. P5  — archiver les scripts orphelins                          (5 min après P1/P2/P4 validés)
```

---

## Fichiers à créer

| Fichier | Contient |
|---|---|
| `nudis_scraper_utils.py` | `FIELD_LABELS`, `normalize_slug`, `slug_variants`, `extract_images`, `extract_photographer`, `extract_field`, `scrape_species` |
| `nudis_worms.py` | `search_aphia`, `get_record`, `get_classification`, `extract_order` |

## Fichiers à modifier

| Fichier | Modification |
|---|---|
| `nudis_fix_orders.py` | Fusionner NORM + ajouter 2 corrections ORDER_FIXES |
| `nudis_scraper_full.py` | Importer depuis nudis_scraper_utils |
| `nudis_fix_slugs.py` | Importer depuis nudis_scraper_utils |
| `nudis_clean_fields.py` | Importer FIELD_LABELS depuis nudis_scraper_utils |
| `nudis_enrich_all_aphia.py` | Importer depuis nudis_worms |
| `nudis_verify_worms.py` | Importer depuis nudis_worms |
| `deploy.py` | Ajouter CSV dans git add |

## Fichiers à supprimer / archiver

`nudis_normalize_orders.py`, `nudis_check_3.py`, `nudis_fix_aphia.py`, `nudis_extract_spa.py`, `spa_debug_home.html`, `spa_debug_species.html`
