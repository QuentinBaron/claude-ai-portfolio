"""
Launcher GUI — Agent Planning Matinal.

Double-cliquer pour ouvrir. Aucun terminal visible (.pyw).
Lance main.py avec les paramètres choisis et affiche les logs en temps réel.
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import font, scrolledtext

# ---------------------------------------------------------------------------
# Chemin vers le projet (sous-dossier contenant main.py + tools/ + prompts/)
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Couleurs
# ---------------------------------------------------------------------------
BG = "#1e1e2e"
SURFACE = "#2a2a3e"
ACCENT = "#7c6af7"
ACCENT_HOVER = "#6a58e0"
TEXT = "#cdd6f4"
TEXT_DIM = "#6c7086"
GREEN = "#a6e3a1"
ORANGE = "#fab387"
RED = "#f38ba8"
YELLOW = "#f9e2af"

FOCUS_OPTIONS = ["faible", "moyen", "bon", "élevé"]
FOCUS_COLORS = {
    "faible": RED,
    "moyen": YELLOW,
    "bon": GREEN,
    "élevé": ACCENT,
}


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class PlanningLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Planning Matinal")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._focus_var = tk.StringVar(value="bon")
        self._build_ui()
        self._center()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        pad = {"padx": 20, "pady": 8}

        # Titre
        header = tk.Frame(self, bg=ACCENT, height=4)
        header.pack(fill="x")

        tk.Label(
            self, text="🗓  Planning Matinal",
            font=("Segoe UI", 16, "bold"),
            bg=BG, fg=TEXT,
        ).pack(pady=(20, 4))

        tk.Label(
            self, text="Agent IA · Trello · Calendar · Gmail",
            font=("Segoe UI", 9),
            bg=BG, fg=TEXT_DIM,
        ).pack(pady=(0, 16))

        # Séparateur
        tk.Frame(self, bg=SURFACE, height=1).pack(fill="x", **{"padx": 20})

        # Focus
        tk.Label(
            self, text="Niveau de focus aujourd'hui",
            font=("Segoe UI", 10, "bold"),
            bg=BG, fg=TEXT,
        ).pack(**pad, anchor="w")

        focus_frame = tk.Frame(self, bg=BG)
        focus_frame.pack(padx=20, pady=(0, 12), anchor="w")

        for opt in FOCUS_OPTIONS:
            color = FOCUS_COLORS[opt]
            rb = tk.Radiobutton(
                focus_frame,
                text=opt.capitalize(),
                variable=self._focus_var,
                value=opt,
                bg=BG, fg=color,
                selectcolor=SURFACE,
                activebackground=BG,
                activeforeground=color,
                font=("Segoe UI", 10),
                indicatoron=True,
                cursor="hand2",
            )
            rb.pack(side="left", padx=(0, 16))

        # Contraintes
        tk.Label(
            self, text="Contraintes du jour  (optionnel)",
            font=("Segoe UI", 10, "bold"),
            bg=BG, fg=TEXT,
        ).pack(**pad, anchor="w")

        self._constraints_entry = tk.Entry(
            self, width=52,
            bg=SURFACE, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=("Segoe UI", 10),
        )
        self._constraints_entry.pack(padx=20, pady=(0, 12), ipady=6, anchor="w")

        # Tâches extra
        tk.Label(
            self, text="Tâches hors Trello  (optionnel)",
            font=("Segoe UI", 10, "bold"),
            bg=BG, fg=TEXT,
        ).pack(**pad, anchor="w")

        self._extra_entry = tk.Entry(
            self, width=52,
            bg=SURFACE, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=("Segoe UI", 10),
        )
        self._extra_entry.pack(padx=20, pady=(0, 20), ipady=6, anchor="w")

        # Bouton lancer
        self._btn = tk.Button(
            self,
            text="  Lancer le planning  ",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg="white",
            activebackground=ACCENT_HOVER, activeforeground="white",
            relief="flat", cursor="hand2",
            command=self._launch,
        )
        self._btn.pack(padx=20, pady=(0, 16), anchor="w", ipady=8, ipadx=4)

        # Zone de logs
        tk.Label(
            self, text="Logs",
            font=("Segoe UI", 9),
            bg=BG, fg=TEXT_DIM,
        ).pack(padx=20, anchor="w")

        self._log = scrolledtext.ScrolledText(
            self, width=72, height=18,
            bg=SURFACE, fg=TEXT,
            font=("Cascadia Code", 9) if self._font_exists("Cascadia Code") else ("Courier New", 9),
            relief="flat", state="disabled",
            wrap="word",
        )
        self._log.pack(padx=20, pady=(4, 20))

        # Tags couleur pour les logs
        self._log.tag_config("tool", foreground=ACCENT)
        self._log.tag_config("result", foreground=TEXT_DIM)
        self._log.tag_config("plan", foreground=GREEN)
        self._log.tag_config("error", foreground=RED)
        self._log.tag_config("info", foreground=YELLOW)

    # -------------------------------------------------------------- Helpers --

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    @staticmethod
    def _font_exists(name: str) -> bool:
        try:
            f = font.Font(family=name)
            return f.actual("family").lower() == name.lower()
        except Exception:
            return False

    def _log_write(self, text: str, tag: str = ""):
        self._log.configure(state="normal")
        if tag:
            self._log.insert("end", text, tag)
        else:
            self._log.insert("end", text)
        self._log.see("end")
        self._log.configure(state="disabled")

    # --------------------------------------------------------------- Launch --

    def _launch(self):
        self._btn.configure(state="disabled", text="  En cours…  ")
        # Masquer les boutons de validation s'ils existent
        if hasattr(self, "_apply_btn"):
            self._apply_btn.pack_forget()
        if hasattr(self, "_skip_btn"):
            self._skip_btn.pack_forget()

        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

        focus = self._focus_var.get()
        constraints = self._constraints_entry.get().strip()
        extra = self._extra_entry.get().strip()

        self._log_write(f"▶  Démarrage — focus {focus}\n\n", "info")

        threading.Thread(
            target=self._run_agent,
            args=(focus, constraints, extra),
            daemon=True,
        ).start()

    def _run_agent(self, focus: str, constraints: str, extra: str):
        cmd = [sys.executable, "-u", "main.py", "--focus", focus]
        if constraints:
            cmd += ["--constraints", constraints]
        if extra:
            cmd += ["--extra", extra]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
            )

            in_plan = False
            for line in proc.stdout:
                tag = ""
                stripped = line.strip()

                if stripped.startswith("[tool]"):
                    tag = "tool"
                elif stripped.startswith("→") or stripped.startswith("       →"):
                    tag = "result"
                elif "PLANNING DU JOUR" in stripped or stripped.startswith("==="):
                    in_plan = True
                    tag = "info"
                elif in_plan:
                    tag = "plan"
                elif stripped.startswith("[agent]"):
                    tag = "info"
                elif "error" in stripped.lower() or "erreur" in stripped.lower():
                    tag = "error"

                self.after(0, self._log_write, line, tag)

            proc.wait()
            if proc.returncode == 0:
                self.after(0, self._log_write, "\n✅  Planning généré et email envoyé.\n", "plan")
            else:
                self.after(0, self._log_write, f"\n⚠️  Processus terminé avec code {proc.returncode}\n", "error")

        except Exception as exc:
            self.after(0, self._log_write, f"\n❌  Erreur : {exc}\n", "error")

        finally:
            self.after(0, self._on_plan_complete)

    def _on_plan_complete(self):
        self._btn.configure(state="normal", text="  Relancer  ")

        # Vérifier si des cartes sont prêtes à labelliser
        plan_file = os.path.join(PROJECT_DIR, "today_plan.json")
        if not os.path.exists(plan_file):
            return
        try:
            with open(plan_file, encoding="utf-8") as f:
                data = json.load(f)
            card_count = len(data.get("cards_to_label", []))
        except Exception:
            return

        if card_count == 0:
            return

        self._log_write(
            f"\n─────────────────────────────────────────\n"
            f"  {card_count} carte(s) prête(s) pour le label TODAY\n"
            f"─────────────────────────────────────────\n",
            "info",
        )

        # Bouton valider
        if not hasattr(self, "_apply_btn"):
            self._apply_btn = tk.Button(
                self,
                text=f"  ✅  Appliquer les labels + envoyer l'email  ",
                font=("Segoe UI", 10, "bold"),
                bg=GREEN, fg="#1e1e2e",
                activebackground="#8fd09b", activeforeground="#1e1e2e",
                relief="flat", cursor="hand2",
                command=self._apply,
            )
            self._skip_btn = tk.Button(
                self,
                text="  Ignorer  ",
                font=("Segoe UI", 9),
                bg=SURFACE, fg=TEXT_DIM,
                activebackground=BG, activeforeground=TEXT_DIM,
                relief="flat", cursor="hand2",
                command=self._skip,
            )

        self._apply_btn.pack(padx=20, pady=(0, 6), anchor="w", ipady=6, ipadx=4,
                             before=self._log)
        self._skip_btn.pack(padx=20, pady=(0, 12), anchor="w",
                            before=self._log)

    def _apply(self):
        self._apply_btn.configure(state="disabled", text="  En cours…  ")
        self._skip_btn.configure(state="disabled")
        self._log_write("\n▶  Application des labels et envoi de l'email…\n", "info")
        threading.Thread(target=self._run_apply, daemon=True).start()

    def _skip(self):
        self._apply_btn.pack_forget()
        self._skip_btn.pack_forget()
        self._log_write("\n⏭  Labels ignorés.\n", "result")

    def _run_apply(self):
        cmd = [sys.executable, "-u", "main.py", "--mode", "apply"]
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
            )
            for line in proc.stdout:
                tag = "plan" if "✅" in line else ("error" if "❌" in line else "result")
                self.after(0, self._log_write, line, tag)
            proc.wait()
        except Exception as exc:
            self.after(0, self._log_write, f"\n❌  Erreur : {exc}\n", "error")
        finally:
            self.after(0, lambda: (
                self._apply_btn.pack_forget(),
                self._skip_btn.pack_forget(),
            ))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = PlanningLauncher()
    app.mainloop()
