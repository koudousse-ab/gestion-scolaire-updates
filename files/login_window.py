# login_window.py — Fenêtre d'authentification

import tkinter as tk
from tkinter import messagebox
import hashlib
import os

# ── Couleurs ─────────────────────────────────────────────────────
BG      = "#0F172A"
CARD    = "#1E293B"
ACCENT  = "#2563EB"
TEXT    = "#E2E8F0"
MUTED   = "#94A3B8"
G_GREEN = "#16A34A"
G_RED   = "#DC2626"
BORDER  = "#334155"

def _hash(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def _get_db_path():
    from database import DB_PATH
    return DB_PATH

def _verifier_identifiants(login, password):
    """Vérifie les identifiants dans la table utilisateurs."""
    import sqlite3
    db = sqlite3.connect(_get_db_path())
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    # Créer la table si elle n'existe pas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id       INTEGER PRIMARY KEY,
            login    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT DEFAULT 'secretaire',
            nom      TEXT DEFAULT ''
        )
    """)
    db.commit()
    # Vérifier
    cur.execute("SELECT * FROM utilisateurs WHERE login=?", (login,))
    row = cur.fetchone()
    db.close()
    if not row:
        return None
    if row["password"] == _hash(password):
        return {"login": row["login"], "role": row["role"], "nom": row["nom"]}
    return None

def _creer_admin_si_absent():
    """Crée le compte admin par défaut si aucun utilisateur n'existe."""
    import sqlite3
    db = sqlite3.connect(_get_db_path())
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id       INTEGER PRIMARY KEY,
            login    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT DEFAULT 'secretaire',
            nom      TEXT DEFAULT ''
        )
    """)
    db.commit()
    cur.execute("SELECT COUNT(*) FROM utilisateurs")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute("""
            INSERT INTO utilisateurs (login, password, role, nom)
            VALUES (?, ?, ?, ?)
        """, ("admin", _hash("admin123"), "admin", "Administrateur"))
        db.commit()
        print("✅ Compte admin créé : login=admin / mot de passe=admin123")
    db.close()


class LoginWindow(tk.Toplevel):
    """Fenêtre de connexion — s'affiche avant l'application principale."""

    def __init__(self, master):
        super().__init__(master)
        self.title("🏫 Gestion Scolaire — Connexion")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._quitter)

        # Centrage robuste (Windows + Linux + DPI)
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(500, sw - 40)
        h  = min(560, sh - 80)
        x  = (sw - w) // 2
        y  = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.user_info  = None   # rempli si connexion OK
        self._tentatives = 0

        _creer_admin_si_absent()
        self._build_ui()
        self.after(100, lambda: self.e_login.focus_set())

    # ─── UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Logo / Titre ──────────────────────────────────────────
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", pady=(40, 0))

        tk.Label(top, text="🏫", bg=BG,
                 font=("Helvetica", 52)).pack()
        tk.Label(top, text="GESTION SCOLAIRE",
                 bg=BG, fg=TEXT,
                 font=("Helvetica", 18, "bold")).pack()
        # Sous-titre dynamique depuis la licence
        try:
            from licence_manager import get_infos_licence
            li = get_infos_licence()
            etab = li.get("etablissement","")
            ville = li.get("ville","")
            sous = f"{etab}" if etab else "Logiciel de Gestion Scolaire"
            if ville: sous += f" — {ville}"
        except Exception:
            sous = "Logiciel de Gestion Scolaire"
        tk.Label(top, text=sous,
                 bg=BG, fg=MUTED,
                 font=("Helvetica", 10)).pack(pady=(2, 0))

        # ── Formulaire ────────────────────────────────────────────
        card = tk.Frame(self, bg=CARD, relief=tk.FLAT)
        card.pack(padx=50, pady=30, fill="x")

        tk.Label(card, text="  Identifiant",
                 bg=CARD, fg=MUTED,
                 font=("Helvetica", 9, "bold"),
                 anchor="w").pack(fill="x", padx=20, pady=(20, 2))
        self.e_login = tk.Entry(card,
                                bg=BORDER, fg=TEXT,
                                insertbackground=ACCENT,
                                font=("Helvetica", 12),
                                relief=tk.FLAT, bd=0)
        self.e_login.pack(fill="x", padx=20, ipady=10)
        tk.Frame(card, bg=ACCENT, height=2).pack(fill="x", padx=20)

        tk.Label(card, text="  Mot de passe",
                 bg=CARD, fg=MUTED,
                 font=("Helvetica", 9, "bold"),
                 anchor="w").pack(fill="x", padx=20, pady=(16, 2))

        pwd_frame = tk.Frame(card, bg=BORDER)
        pwd_frame.pack(fill="x", padx=20)
        self.e_pwd = tk.Entry(pwd_frame,
                              bg=BORDER, fg=TEXT,
                              insertbackground=ACCENT,
                              font=("Helvetica", 12),
                              show="●", relief=tk.FLAT, bd=0)
        self.e_pwd.pack(side="left", fill="x", expand=True, ipady=10)

        # Bouton œil pour voir/masquer
        self._pwd_visible = False
        self.btn_eye = tk.Label(pwd_frame, text="👁", bg=BORDER, fg=MUTED,
                                 font=("Helvetica", 12), cursor="hand2", padx=8)
        self.btn_eye.pack(side="right")
        self.btn_eye.bind("<Button-1>", self._toggle_pwd)

        tk.Frame(card, bg=ACCENT, height=2).pack(fill="x", padx=20)

        # Message d'erreur
        self.lbl_err = tk.Label(card, text="",
                                 bg=CARD, fg=G_RED,
                                 font=("Helvetica", 9, "bold"))
        self.lbl_err.pack(pady=(8, 0))

        # Bouton connexion
        self.btn_connect = tk.Button(card,
                                      text="  🔓  SE CONNECTER  ",
                                      command=self._connecter,
                                      bg=ACCENT, fg="white",
                                      font=("Helvetica", 12, "bold"),
                                      relief=tk.FLAT, cursor="hand2",
                                      padx=20, pady=12,
                                      activebackground="#1D4ED8",
                                      activeforeground="white")
        self.btn_connect.pack(fill="x", padx=20, pady=(12, 24))

        # Navigation clavier
        self.e_login.bind("<Return>", lambda e: self.e_pwd.focus_set())
        self.e_pwd.bind("<Return>",   lambda e: self._connecter())

        # ── Pied de page ──────────────────────────────────────────
        tk.Label(self,
                 text="Compte par défaut : admin / admin123",
                 bg=BG, fg=BORDER,
                 font=("Helvetica", 8)).pack(pady=(0, 6))
        tk.Label(self,
                 text="v2.0 — © 2025 Gestion Scolaire",
                 bg=BG, fg=BORDER,
                 font=("Helvetica", 8)).pack()

    def _quitter(self):
        self.user_info = None
        self.destroy()

    def _toggle_pwd(self, event=None):
        self._pwd_visible = not self._pwd_visible
        self.e_pwd.config(show="" if self._pwd_visible else "●")
        self.btn_eye.config(fg=TEXT if self._pwd_visible else MUTED)

    # ─── Connexion ───────────────────────────────────────────────

    def _connecter(self):
        login = self.e_login.get().strip()
        pwd   = self.e_pwd.get()

        if not login or not pwd:
            self._erreur("Remplissez tous les champs.")
            return

        if self._tentatives >= 5:
            self._erreur("Trop de tentatives. Redémarrez l'application.")
            self.btn_connect.config(state="disabled")
            return

        user = _verifier_identifiants(login, pwd)
        if user:
            self.user_info = user
            self.lbl_err.config(text="✅  Connexion réussie !", fg=G_GREEN)
            self.update()
            self.after(500, self.destroy)
        else:
            self._tentatives += 1
            reste = 5 - self._tentatives
            self._erreur(f"Identifiant ou mot de passe incorrect.  ({reste} essai(s) restant(s))")
            self.e_pwd.delete(0, tk.END)
            self.e_pwd.focus_set()
            # Effet shake
            self._shake()

    def _erreur(self, msg):
        self.lbl_err.config(text=f"⚠  {msg}", fg=G_RED)

    def _shake(self):
        """Effet de tremblement de la fenêtre."""
        x0 = self.winfo_x()
        y0 = self.winfo_y()
        for dx in [8, -8, 6, -6, 4, -4, 0]:
            self.after(30, lambda d=dx: self.geometry(f"+{x0+d}+{y0}"))
