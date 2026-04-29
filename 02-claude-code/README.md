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
pip install anthropic pdfplumber
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

Create a plain-text file named `fiche_poste.txt` (or a PDF) in the same directory.

Supported formats: `.txt` (UTF-8) and `.pdf` (text-based — scanned images are not supported).

## Usage

```bash
# Default: reads fiche_poste.txt, writes lettre_de_motivation.md
python lm_generator.py

# Custom text file
python lm_generator.py mon_offre.txt

# PDF input
python lm_generator.py offre.pdf

# Custom input and output
python lm_generator.py offre.pdf --out lettre.md
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
