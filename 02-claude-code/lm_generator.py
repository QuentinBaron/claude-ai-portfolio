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

SYSTEM_PROMPT = """Tu es un expert en rédaction de lettres de motivation professionnelles.
Tu rédiges des lettres percutantes, personnalisées et adaptées au secteur d'activité
décrit dans la fiche de poste. Ton style est direct, concis et valorisant sans être
excessif. Tu évites les formules creuses et les clichés."""

USER_PROMPT_TEMPLATE = """Voici une fiche de poste :

<fiche_poste>
{job_description}
</fiche_poste>

Génère une trame de lettre de motivation structurée en Markdown pour ce poste.
La lettre doit contenir :

1. **En-tête** : coordonnées fictives du candidat + destinataire (à compléter)
2. **Accroche** (1 paragraphe) : phrase d'entrée percutante liée au poste ou à l'entreprise
3. **Pourquoi ce poste** (1-2 paragraphes) : motivations alignées avec l'offre
4. **Ce que j'apporte** (1-2 paragraphes) : compétences clés tirées de la fiche de poste,
   avec des espaces [À COMPLÉTER] pour que le candidat insère ses expériences concrètes
5. **Conclusion** : appel à l'action + formule de politesse

Règles :
- Longueur : 300-400 mots corps de lettre
- Ton : professionnel et enthousiaste
- Chaque section est un titre Markdown (`##`)
- Les parties à personnaliser sont balisées `[À COMPLÉTER : ...]`
- Inclure à la fin une section `## Conseils de personnalisation` avec 3-4 tips
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
