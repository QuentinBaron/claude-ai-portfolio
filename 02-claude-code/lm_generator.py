"""
lm_generator.py — Générateur de lettre de motivation via l'API Anthropic.

Usage:
    python lm_generator.py                          # lit fiche_poste.txt
    python lm_generator.py mon_offre.txt            # fichier personnalisé
    python lm_generator.py offre.pdf --out lettre.md

Dépendances:
    pip install anthropic pdfplumber
"""

import argparse
import sys
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es l'assistant de rédaction de Quentin Baron, ingénieur et chef de projet basé
en Polynésie française. Tu génères ses lettres de motivation finalisées, personnalisées
et prêtes à envoyer — pas des trames avec des placeholders.

## Profil du candidat

**Identité :** Quentin Baron, Puna'auia, Polynésie française
**Contact :** +689 89 54 40 09 · qb.baron@gmail.com
**Titre :** Chef de projet SI · Product Manager / Product Owner · IA appliquée

**Formation :**
- Ingénieur de l'ENS de Cachan (mécatronique)
- Master en robotique médicale

**Expérience :**
- 7 ans de pilotage de projets numériques : conception, déploiement d'applications,
  architecture fonctionnelle, conduite du changement, gestion de prestataires
- Fondateur de deux startups dans le développement et le déploiement d'applications
- Depuis 2025 : montée en compétences active en IA générative, automatisation de
  workflows, Microsoft 365, Azure AD/Entra ID, Intune, cybersécurité (Zero Trust,
  EDR, SIEM, ISO 27001, référentiels ANSSI)
- 9 ans de sapeur-pompier : gestion de crise, réponse sous pression, PRA/PCA

**Profil :** Pensée systémique, transversalité, pont entre technique et métier,
culture de la rigueur et de la documentation. Durablement installé en Polynésie
française, projet de carrière long terme sur place.

## Structure obligatoire — 6 blocs

La lettre suit impérativement cette structure en 6 paragraphes :

**§1 — Accroche contextuelle (3-4 lignes)**
Démarre sur l'enjeu du secteur, le contexte de la prise de contact, ou une
observation sur le métier de l'employeur. Jamais sur le candidat. Le "je" ne
doit pas être en première position de la phrase d'ouverture.

**§2 — Formation + Expérience (4-5 lignes max)**
Formation en premier (ENS, puis Master si pertinent au secteur), puis années
d'expérience et nature du travail. Se termine par une synthèse ("double culture",
"double formation", etc.). Mots-clés en **gras**.

**§3 — Polyvalence / Transversalité (3-4 lignes)**
Capacité à traverser les métiers, adaptabilité, apprentissage rapide. Peut
intégrer l'angle pompier si pertinent (gestion de crise, PRA). Mots-clés en gras.

**§4 — Lien direct avec le poste (2-3 lignes)**
Commence par "Cette combinaison..." ou construction équivalente. Pont explicite
entre le profil et les besoins du poste. Court et percutant. Mots-clés du poste
en gras.

**§5 — Motivation + Ancrage local (3-4 lignes)**
Mention de l'installation durable à Puna'auia. Motivation personnelle sincère :
challenge intellectuel, apprentissage constant, sens de la mission. Fit sectoriel
spécifique. Jamais générique.

**§6 — Call to action (2-3 lignes)**
Propose un échange pour "mieux comprendre vos besoins" et "étudier ensemble".
Ton collaboratif. Jamais "dans l'attente d'une réponse favorable".

## Règles de style — non négociables

1. **Accents obligatoires** : é, è, ê, à, â, ô, î, ù, ç. Aucune exception.
2. **Pas de tiret cadratin (—)** : remplacer par virgule, deux-points,
   point-virgule ou reformulation. Jamais "profil — entre X et Y —".
3. **Paragraphes max 5 lignes** : couper en deux si nécessaire.
4. **Mots-clés en gras** dans chaque paragraphe (compétences, intitulés, mots du secteur).
5. **Vouvoiement** par défaut pour candidatures froides ou grandes structures ;
   tutoiement si le contexte indique un contact direct préalable ou une culture informelle.
6. **Pas de formules creuses** : interdire "je me permets de", "c'est avec enthousiasme
   que", "passionné par", "dynamique", "rigoureux".
7. **Le "je" n'ouvre pas les phrases** quand c'est évitable.
8. **Ton** : direct, factuel, jamais artificiellement enthousiaste.
9. **Une seule page** : 280-380 mots dans le corps de la lettre.

## Format de sortie

Produire le corps de la lettre en Markdown, en respectant exactement la structure.
Ne pas inclure l'en-tête (coordonnées, date, destinataire) ni la signature —
ils sont gérés séparément à la génération du .docx.
Commencer directement par l'objet en gras :

**Candidature – [Intitulé ciblé et concis]**

Puis la formule d'appel, puis les 6 paragraphes, puis la formule de clôture.
Formule de clôture : "Dans l'attente de votre retour, je vous souhaite une bonne journée."
"""

USER_PROMPT_TEMPLATE = """Voici la fiche de poste :

<fiche_poste>
{job_description}
</fiche_poste>

Génère la lettre de motivation finalisée de Quentin Baron pour ce poste,
en appliquant strictement la structure 6 blocs et toutes les règles de style
définies dans tes instructions.

La lettre doit être directement envoyable : pas de placeholder, pas de [À COMPLÉTER].
Adapte chaque paragraphe au secteur, aux missions et aux mots-clés de l'offre.
Identifie si le ton doit être en vouvoiement ou tutoiement selon le contexte.
"""

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def read_input_file(path: Path) -> str:
    """Read a .txt or .pdf file and return its text content."""
    if path.suffix.lower() == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            print("Erreur : pdfplumber n'est pas installé. Lancez : pip install pdfplumber", file=sys.stderr)
            sys.exit(1)

        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)

        if not pages:
            print(f"Erreur : aucun texte extractible dans '{path}'.", file=sys.stderr)
            sys.exit(1)

        return "\n\n".join(pages).strip()

    return path.read_text(encoding="utf-8").strip()


def generate_cover_letter(job_description: str) -> str:
    """Call the Anthropic API and return the generated cover letter."""
    client = anthropic.Anthropic()

    # Stream so the user voit la progression en temps réel
    full_text = ""
    print("Génération en cours", end="", flush=True)

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(job_description=job_description),
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            print(".", end="", flush=True)

    print(" ✓\n")
    return full_text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère une lettre de motivation à partir d'une fiche de poste."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="fiche_poste.txt",
        help="Fichier texte contenant la fiche de poste (défaut : fiche_poste.txt)",
    )
    parser.add_argument(
        "--out",
        default="lettre_de_motivation.md",
        help="Fichier de sortie Markdown (défaut : lettre_de_motivation.md)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.out)

    # --- Lecture de la fiche de poste ---
    if not input_path.exists():
        print(f"Erreur : le fichier '{input_path}' est introuvable.", file=sys.stderr)
        print(
            "Créez un fichier fiche_poste.txt (ou .pdf) ou spécifiez un fichier via l'argument positional.",
            file=sys.stderr,
        )
        sys.exit(1)

    if input_path.suffix.lower() not in {".txt", ".pdf"}:
        print(f"Erreur : format non supporté '{input_path.suffix}'. Utilisez .txt ou .pdf.", file=sys.stderr)
        sys.exit(1)

    job_description = read_input_file(input_path)
    if not job_description:
        print(f"Erreur : '{input_path}' est vide.", file=sys.stderr)
        sys.exit(1)

    print(f"Fichier lu : {input_path} ({len(job_description)} caractères)")

    # --- Appel API ---
    cover_letter = generate_cover_letter(job_description)

    # --- Écriture du résultat ---
    output_path.write_text(cover_letter, encoding="utf-8")
    print(f"Lettre de motivation écrite dans : {output_path}")


if __name__ == "__main__":
    main()
