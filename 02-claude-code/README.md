# 02 — LM Generator

A Python script that reads a job description file and generates a structured cover letter template via the Anthropic API.

## Features

- Streams the response in real time (progress dots while generating)
- Outputs a Markdown cover letter with `[À COMPLÉTER : ...]` placeholders for candidate-specific content
- Includes a **Conseils de personnalisation** section at the end
- Accepts any input file and output path via CLI arguments

## Setup

### 1. Install dependencies

```bash
pip install anthropic
```

### 2. Set the API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

On Windows (PowerShell):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

### 3. Prepare your job description

Create a plain-text file named `fiche_poste.txt` in the same directory and paste the job posting into it:

```
Intitulé du poste : Développeur Python Senior
Entreprise : Acme Corp
...
```

## Usage

```bash
# Default: reads fiche_poste.txt, writes lettre_de_motivation.md
python lm_generator.py

# Custom input file
python lm_generator.py mon_offre.txt

# Custom input and output
python lm_generator.py mon_offre.txt --out lettre.md
```

## Output structure

The generated Markdown file contains:

| Section | Description |
|---|---|
| `## En-tête` | Fictional candidate details + recipient (to be filled in) |
| `## Accroche` | Opening hook tied to the role or company |
| `## Pourquoi ce poste` | Motivations aligned with the job offer |
| `## Ce que j'apporte` | Key skills extracted from the posting, with `[À COMPLÉTER]` slots |
| `## Conclusion` | Call to action + closing formula |
| `## Conseils de personnalisation` | 3–4 tips for tailoring the letter |

## Example run

```
$ python lm_generator.py fiche_poste.txt
Fichier lu : fiche_poste.txt (842 caractères)
Génération en cours....................... ✓

Lettre de motivation écrite dans : lettre_de_motivation.md
```

Then open `lettre_de_motivation.md` in any Markdown editor and fill in the `[À COMPLÉTER : ...]` placeholders with your own experience.
