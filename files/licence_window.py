# licence_window.py — Fenêtre d'activation de la licence

import tkinter as tk
from tkinter import messagebox
from licence_manager import (get_machine_id, verifier_licence,
                              sauvegarder_cle, charger_et_verifier)

BG    = "#0F172A"
CARD  = "#1E293B"
ACCT  = "#2563EB"
TEXT  = "#E2E8F0"
MUTED = "#94A3B8"
GREEN = "#16A34A"
RED   = "#DC2626"
GOLD  = "#C8A951"
BDR   = "#334155"


class LicenceWindow(tk.Toplevel):

    def __init__(self, master, on_success=None):
        super().__init__(master)
        self.title("🔑  Activation du Logiciel")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self.on_success = on_success
        self.activated  = False

        # Centrage robuste sur l'écran (pas sur le parent)
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(620, sw - 40)
        h  = min(580, sh - 80)
        x  = (sw - w) // 2
        y  = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(480, 460)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._fermer)
        self._build()

    def _build(self):
        # ── Titre ─────────────────────────────────────────────
        tk.Label(self, text="🔑  ACTIVATION DU LOGICIEL",
                 bg=BG, fg=GOLD,
                 font=("Helvetica", 15, "bold")).pack(pady=(22, 4))
        tk.Label(self,
                 text="Logiciel de Gestion Scolaire",
                 bg=BG, fg=MUTED,
                 font=("Helvetica", 10)).pack(pady=(0, 18))

        # ── ID Machine ────────────────────────────────────────
        mid_frame = tk.LabelFrame(self,
                                   text="  📋  Identifiant de votre machine  ",
                                   bg=CARD, fg=ACCT,
                                   font=("Helvetica", 10, "bold"),
                                   relief=tk.GROOVE, bd=2)
        mid_frame.pack(fill="x", padx=28, pady=(0, 14))

        mid = get_machine_id()
        tk.Label(mid_frame,
                 text="Communiquez cet identifiant à votre fournisseur "
                      "pour obtenir votre clé d'activation :",
                 bg=CARD, fg=MUTED,
                 font=("Helvetica", 9),
                 wraplength=520, justify="left").pack(anchor="w", padx=14, pady=(10, 4))

        mid_display = tk.Frame(mid_frame, bg=BDR)
        mid_display.pack(fill="x", padx=14, pady=(0, 12))
        self.lbl_mid = tk.Label(mid_display, text=mid,
                                 bg=BDR, fg="#93C5FD",
                                 font=("Courier", 13, "bold"),
                                 padx=10, pady=8)
        self.lbl_mid.pack(side="left", fill="x", expand=True)
        tk.Button(mid_display, text="📋 Copier",
                  command=lambda: self._copier(mid),
                  bg=ACCT, fg="white",
                  font=("Helvetica", 9, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  padx=10, pady=6).pack(side="right")

        # ── Saisie clé ────────────────────────────────────────
        key_frame = tk.LabelFrame(self,
                                   text="  🔑  Entrez votre clé d'activation  ",
                                   bg=CARD, fg=ACCT,
                                   font=("Helvetica", 10, "bold"),
                                   relief=tk.GROOVE, bd=2)
        key_frame.pack(fill="x", padx=28, pady=(0, 14))

        tk.Label(key_frame,
                 text="Collez ici la clé fournie par votre revendeur :",
                 bg=CARD, fg=MUTED,
                 font=("Helvetica", 9)).pack(anchor="w", padx=14, pady=(10, 4))

        self.e_cle = tk.Text(key_frame, height=5,
                              bg=BDR, fg=TEXT,
                              insertbackground=ACCT,
                              font=("Courier", 9),
                              relief=tk.FLAT, bd=0,
                              wrap=tk.WORD)
        self.e_cle.pack(fill="x", padx=14, pady=(0, 12), ipady=6)

        # ── Message résultat ──────────────────────────────────
        self.lbl_result = tk.Label(self, text="",
                                    bg=BG, fg=MUTED,
                                    font=("Helvetica", 9, "bold"),
                                    wraplength=520, justify="center")
        self.lbl_result.pack(pady=4)

        # ── Boutons ───────────────────────────────────────────
        bb = tk.Frame(self, bg=BG)
        bb.pack(pady=14)
        tk.Button(bb, text="✅  ACTIVER",
                  command=self._activer,
                  bg=GREEN, fg="white",
                  font=("Helvetica", 12, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  padx=24, pady=10,
                  activebackground="#166534",
                  activeforeground="white").pack(side="left", padx=8)
        tk.Button(bb, text="❌  Quitter",
                  command=self._fermer,
                  bg=BDR, fg=TEXT,
                  font=("Helvetica", 10),
                  relief=tk.FLAT, cursor="hand2",
                  padx=16, pady=10).pack(side="left", padx=8)

        tk.Label(self,
                 text="Pour obtenir votre clé, contactez votre revendeur "
                      "en lui communiquant l'identifiant machine ci-dessus.",
                 bg=BG, fg=MUTED,
                 font=("Helvetica", 8, "italic"),
                 wraplength=520).pack(pady=(0, 12))

    def _copier(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copié", "Identifiant copié dans le presse-papiers ✅")

    def _activer(self):
        cle = self.e_cle.get("1.0", tk.END).strip()
        if not cle:
            self.lbl_result.config(
                text="⚠️  Veuillez coller votre clé d'activation.", fg="#D97706")
            return
        result = verifier_licence(cle)
        if result["valide"]:
            sauvegarder_cle(cle)
            self.lbl_result.config(
                text=f"✅  Activation réussie !\n"
                     f"Établissement : {result['etablissement']}\n"
                     f"Expiration : {result['expiration']}",
                fg=GREEN)
            self.activated = True
            self.after(1500, self._succes)
        else:
            self.lbl_result.config(
                text=f"❌  {result['message']}", fg=RED)

    def _succes(self):
        self.destroy()
        if self.on_success:
            self.on_success()

    def _fermer(self):
        self.destroy()


class LicenceExpireBientot(tk.Toplevel):
    """Avertissement si la licence expire dans moins de 30 jours."""

    def __init__(self, master, jours):
        super().__init__(master)
        self.title("⚠️  Licence bientôt expirée")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(440, sw - 40)
        h  = min(240, sh - 80)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(self, text="⚠️", bg=BG,
                 font=("Helvetica", 36)).pack(pady=(20, 4))
        tk.Label(self,
                 text=f"Votre licence expire dans {jours} jour(s) !",
                 bg=BG, fg="#F59E0B",
                 font=("Helvetica", 13, "bold")).pack()
        tk.Label(self,
                 text="Contactez votre revendeur pour renouveler\nvotre licence avant l'expiration.",
                 bg=BG, fg=MUTED,
                 font=("Helvetica", 10),
                 justify="center").pack(pady=8)
        tk.Button(self, text="  OK, compris  ",
                  command=self.destroy,
                  bg=ACCT, fg="white",
                  font=("Helvetica", 11, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  padx=20, pady=8).pack(pady=10)
