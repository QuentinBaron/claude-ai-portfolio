#!/usr/bin/env python3
"""deploy.py - Pipeline complet Nudidex + push GitHub

Doit être lancé depuis 05-application/Nudidex/ :
    python deploy.py           # build + push
    python deploy.py --dry-run # build sans push
"""
import subprocess, sys, os, re
from pathlib import Path

HERE      = Path(__file__).parent              # 05-application/Nudidex/
REPO_DIR  = HERE.parent.parent                 # claude-ai-portfolio/
OUT_HTML  = HERE / "index.html"
COLORS    = HERE / "nudis_colors.json"
DRY_RUN   = "--dry-run" in sys.argv

def run(cmd, cwd=None, check=True):
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(cmd, shell=True, cwd=str(cwd or HERE), text=True,
                            capture_output=True, encoding="utf-8", env=env)
    if result.stdout.strip(): print(result.stdout.strip())
    if result.stderr.strip(): print(result.stderr.strip())
    if check and result.returncode != 0:
        print(f"\n!! Commande echouee : {cmd}")
        sys.exit(1)
    return result

def count_species(path):
    if not path.exists(): return 0, "absent"
    content = path.read_text(encoding="utf-8")
    count = len(re.findall(r'"s":"[^"]+?"', content))
    size_kb = path.stat().st_size // 1024
    return count, f"{size_kb} KB"

print("\n" + "="*55)
print("  NUDIDEX DEPLOY")
print("="*55)

print("\n[1/4] Corrections taxonomiques...")
run("python nudis_fix_orders.py")

print("\n[2/4] Nettoyage champs...")
run("python nudis_clean_fields.py")

print("\n[3/4] Pipeline (merge CSV+JSON -> index.html)...")
run("python run_pipeline.py")

print("\n[3b/4] Base couleurs/morpho...")
run("python nudis_build_colors.py")

print("\n[4/4] Verification...")
count, info = count_species(OUT_HTML)
print(f"  index.html : {count} especes ({info})")

if count == 0:
    print("ERREUR : index.html vide ou absent — arret.")
    sys.exit(1)

if DRY_RUN:
    print("\n[dry-run] Git skippe.")
    print("OK Pipeline OK -- aucun push effectue.")
    sys.exit(0)

print("\n[5/4] Git...")
run("git fetch origin", cwd=REPO_DIR)
run("git merge origin/main --no-edit", cwd=REPO_DIR)

# Vérifier que le merge n'a pas écrasé index.html
count_post, _ = count_species(OUT_HTML)
if count_post != count:
    print(f"  Merge a ecrase index.html ({count_post} especes) -- relance pipeline...")
    run("python run_pipeline.py")

run("git add 05-application/Nudidex/index.html 05-application/Nudidex/nudis_colors.json 05-application/Nudidex/nudis_taxonomy.csv", cwd=REPO_DIR)

status = run("git status --porcelain", cwd=REPO_DIR, check=False)
if not status.stdout.strip():
    print("  Aucun changement a committer.")
else:
    msg = input("\n  Message de commit (Entree = 'update: nudidex') : ").strip()
    if not msg: msg = "update: nudidex"
    run(f'git commit -m "{msg}"', cwd=REPO_DIR)
    print("  push...")
    run("git push", cwd=REPO_DIR)

print("\n" + "="*55)
print("OK Deploye ! https://quentinbaron.github.io/claude-ai-portfolio/05-application/Nudidex/")
print("="*55 + "\n")
