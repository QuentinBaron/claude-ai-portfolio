# claude-ai-portfolio — Quentin Baron

![Claude AI](https://img.shields.io/badge/Claude%20AI-assisted-8b5cf6?logo=anthropic)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Status](https://img.shields.io/badge/statut-en%20cours-orange)

Portfolio de projets développés en **développement IA-assisté** avec Claude (Anthropic).  
Chaque projet couvre un cycle complet : problème réel → conception → implémentation → déploiement.

---

## Approche

Ces projets ne sont pas des exercices. Ils répondent à des besoins concrets, personnels ou professionnels, et ont été construits en collaboration avec l'IA comme partenaire de conception, d'implémentation et de débogage.

L'objectif est de démontrer une capacité à **concevoir et livrer des systèmes fonctionnels** en tirant parti des outils IA modernes — pas à générer du code isolé.

---

## Projets

### 🐚 [Nudidex — PWA d'identification des nudibranches de Polynésie française](./05-application/Nudidex/)

Application web progressive couvrant 423 espèces, déployée sur GitHub Pages.  
Identificateur interactif par questions binaires progressives, filtres taxonomiques hiérarchiques, vues tableau et cartes, fonctionnement offline.

**Angle** : conception produit de bout en bout — pipeline de données Python → enrichissement IA → PWA single-file  
**Stack** : HTML5 · CSS3 · JavaScript vanilla · Python · Claude API · GitHub Pages  
🌐 [Application live](https://quentinbaron.github.io/claude-ai-portfolio/05-application/Nudidex/)

---

### 🤖 [Agent Planning — Assistant quotidien avec boucle agentique](./06-agent/planning/) *(à venir)*

Agent Python autonome qui génère un planning journalier à partir du calendrier, des tâches Trello et du niveau d'énergie déclaré. Envoie le planning par email, applique des labels Trello, s'ajuste en cours de journée.

**Angle** : architecture agentique multi-outils — boucle autonome avec mémoire et jugement  
**Stack** : Python · Claude API · Trello API · Google Calendar API · Gmail API  

---

## Structure du repo

```
claude-ai-portfolio/
├── 05-application/
│   └── Nudidex/          # PWA nudibranches Polynésie
└── 03-agent/
    └── planning/         # Agent planning quotidien (WIP)
```

---

## Contact

**Quentin Baron**  
📍 Tahiti  
📧 qb.baron@gmail.com  
🔗 [LinkedIn](https://www.linkedin.com/in/quentinbaron)
