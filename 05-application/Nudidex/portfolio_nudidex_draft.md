# Nudidex — Case Study

**Type de projet** : Application web progressive (PWA) · Données · Biologie marine  
**Période** : 2025 – en cours  
**URL** : https://quentinbaron.github.io/claude-ai-portfolio/05-application/Nudidex/  
**Stack** : Python · HTML/CSS/JS vanilla · GitHub Pages · WoRMS API

---

## Contexte

La Polynésie française abrite une biodiversité exceptionnelle en nudibranches (mollusques opisthobranches), documentée par une communauté de plongeurs locaux sur le site tahitinudi.jimdoweb.com. Cette base de données informelle, riche de 424 espèces répertoriées, n'existait sous aucune forme consultable, filtrable ou pédagogique.

**Objectif** : concevoir un outil de terrain permettant d'identifier, d'explorer et d'apprendre à reconnaître les espèces de la région — utilisable sans connexion, depuis un téléphone, en plongée ou après.

---

## Approche : gestion de projet assistée par IA

Le projet a été conduit selon un modèle de collaboration humain/IA itératif, où chaque composant a été co-construit par cycles courts de spécification → implémentation → test → correction.

**Répartition des rôles :**

| Quentin (pilote) | Claude (exécutant) |
|---|---|
| Définition des objectifs et priorités | Génération et correction du code |
| Expertise domaine (biologie marine, taxonomie) | Pipeline de données et scraping |
| Validation des résultats et décisions finales | Diagnostic de bugs et proposition de solutions |
| Tests terrain et retours d'usage | Vérification taxonomique (protocole WoRMS) |
| Déploiement | Documentation et mémoire de projet |

Le pilotage humain reste central : Claude ne prend aucune décision de fond sans validation. Les corrections taxonomiques, les choix d'architecture et les arbitrages fonctionnels sont systématiquement soumis à Quentin avant implémentation.

---

## Architecture technique

### Pipeline de données (Python)

```
tahitinudi.jimdoweb.com
        ↓ nudis_scraper_full.py      (scraping HTML → nudis_scraped_full.json)
        ↓ run_pipeline.py            (orchestration)
        ↓ nudis_fix_orders.py        (corrections taxonomiques : ordre, famille, nom)
        ↓ nudis_clean_fields.py      (nettoyage champs : emojis, valeurs parasites)
        ↓ nudis_enriched.json        (données finales)
        ↓ deploy.py                  (build template + push GitHub Pages)
```

Le pipeline est entièrement reproductible : une commande (`python deploy.py`) reconstruit et déploie l'application complète à partir des sources brutes.

### Application (HTML/CSS/JS vanilla)

Architecture single-file sans framework ni dépendance externe. Choix délibéré pour la portabilité et la lisibilité. Fonctionnalités principales :

- **Nudidex** : vue cartes avec photo, nom, famille, ordre, description morphologique
- **Liste** : tableau filtrable avec description et observations de terrain
- **Jeu** : classification progressive ordre → famille → genre → espèce, avec indices morphologiques
- **Filtres hiérarchiques** : ordre → famille → genre, avec mode "Grouper"
- **CLADE_HINTS** : dictionnaire de ~340 descriptions visuelles (ordres, familles, genres, espèces), couverture effective ~90 % des 424 espèces via fallback genre
- **PWA** : installable sur Android, fonctionne hors connexion

---

## Problèmes résolus

### Qualité des données taxonomiques

Les données source contiennent des erreurs de nomenclature (noms non acceptés par WoRMS, orthographes incorrectes, classements obsolètes). Un protocole de vérification a été établi : croisement systématique avec l'API WoRMS pour chaque correction, avec distinction entre erreurs bloquantes (mauvais binôme) et tolérées (auteurs/dates non affichés).

Un lot de descriptions morphologiques généré par LLM (ChatGPT) a été soumis au même protocole : détection d'hallucinations (espèces inexistantes, genres invalides), corrections de reclassifications récentes (ex. Thordisa → Avaldesia, WoRMS 2007).

### Bug d'ordre d'exécution JavaScript

L'ajout des descriptions morphologiques dans les cartes a introduit un bug critique : le dictionnaire `CLADE_HINTS` est défini en bas du fichier HTML, après l'IIFE d'initialisation qui appelle `buildCards()`. Au chargement, `CLADE_HINTS` est `undefined` → TypeError → le script s'arrête → jeu et nudidex cassés.

**Solution** : garde `(window.CLADE_HINTS||{})` dans les fonctions appelées à l'init, puis appel explicite de `buildTable()` et `buildCards()` immédiatement après la définition du dictionnaire.

### Couverture des descriptions morphologiques

Évaluation quantitative de la couverture : croisement des clés du dictionnaire avec les valeurs uniques du CSV taxonomique (ordres, familles, genres, espèces). Résultat : 100 % des ordres et familles, 91 % des genres, 33 % des espèces en entrée directe — mais ~90 % de couverture effective grâce au mécanisme de fallback genre.

---

## État actuel

- 424 espèces · 145 genres · 54 familles · 13 ordres
- ~340 descriptions morphologiques intégrées
- Pipeline de mise à jour fonctionnel et documenté
- Déployé et testé sur terrain (Polynésie française)

---

## Compétences démontrées

**Pilotage de projet IA** : définition d'objectifs, spécification fonctionnelle, validation des outputs, gestion des itérations — sans déléguer les décisions de fond au modèle.

**Pensée systémique** : conception d'un pipeline de données complet (scraping → nettoyage → correction → enrichissement → déploiement), architecture applicative sans dépendance, gestion de la cohérence des données sur la durée.

**Rigueur épistémique** : protocole de vérification des données LLM-générées, distinction entre erreurs bloquantes et tolérées, croisement avec une source externe autoritaire (WoRMS).

**Maîtrise technique transversale** : Python (scraping, traitement JSON/CSV, orchestration), JavaScript (architecture single-file, debug, optimisation), CI/CD léger (GitHub Pages), API REST (WoRMS).

**Domaine expert** : biologie marine, taxonomie des opisthobranches, écologie corallienne de Polynésie française.
