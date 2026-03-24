# main_window.py — Interface principale optimisée pour Secrétaire

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from widgets_communs import (BG, PANEL, CARD, HEADER, ACCENT, ACCENT2,
                              TEXT, MUTED, BORDER, G_BLUE, G_GREEN, G_ORANGE,
                              G_RED, G_PURPLE, configurer_style_ttk)


class MainWindow(tk.Tk):
    def __init__(self):
    super().__init__()
    self.title("🏫 Gestion Scolaire — Espace Secrétariat")
    self.configure(bg=BG)
    configurer_style_ttk()
    self._page_active = None
    self.user_info    = None

    # 1. Forcer la mise à jour pour obtenir les vraies dimensions
    self.update_idletasks()

    # 2. Calcul des dimensions
    sw = self.winfo_screenwidth()
    sh = self.winfo_screenheight()
    
    w = min(1440, int(sw * 0.95))
    h = min(860,  int(sh * 0.92))
    
    # 3. Calcul de la position centrée
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)

    # 4. Application de la géométrie
    self.geometry(f"{w}x{h}+{x}+{y}")
    self.minsize(900, 600)

    # 5. Gestion spécifique de l'état "Maximisé"
    if sw < 1400:
        try:
            # Sous Windows
            self.state("zoomed")
        except:
            # Sous Ubuntu/Linux (GNOME)
            self.attributes('-zoomed', True)

        self._build_ui()
        self._tick()

    # ═══════════════════════════════════════════════════════════════
    # CONSTRUCTION UI
    # ═══════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── Barre de titre ──────────────────────────────────────────
        self._build_topbar()

        # ── Barre d'accès rapide ────────────────────────────────────
        self._build_quickbar()

        # ── Corps principal (sidebar + contenu) ─────────────────────
        corps = tk.Frame(self, bg="#0F172A")
        corps.pack(fill="both", expand=True)

        self._build_sidebar(corps)

        # Séparateur vertical
        tk.Frame(corps, bg="#334155", width=1).pack(side="left", fill="y")

        self.contenu = tk.Frame(corps, bg="#0F172A")
        self.contenu.pack(side="left", fill="both", expand=True)

        # ── Barre de statut ─────────────────────────────────────────
        self._build_statusbar()

        # ── Pages ───────────────────────────────────────────────────
        self._creer_pages()

    def _build_topbar(self):
        """Barre de titre principale."""
        bar = tk.Frame(self, bg=HEADER, height=56)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Logo + titre
        tk.Label(bar, text="🏫", bg=HEADER,
                 font=("Helvetica", 22)).pack(side="left", padx=(14,4), pady=8)
        tk.Label(bar, text="GESTION SCOLAIRE",
                 bg=HEADER, fg="white",
                 font=("Helvetica", 15, "bold")).pack(side="left", pady=8)

        # Séparateur
        tk.Frame(bar, bg=ACCENT2, width=3).pack(side="left", fill="y",
                                                 padx=14, pady=8)

        # Infos établissement
        self.lbl_etab = tk.Label(bar, text="", bg=HEADER, fg="#94C8F0",
                                  font=("Helvetica", 10))
        self.lbl_etab.pack(side="left", padx=4)

        # Droite : horloge + année
        self.lbl_clock = tk.Label(bar, text="", bg=HEADER, fg="white",
                                   font=("Helvetica", 12, "bold"))
        self.lbl_clock.pack(side="right", padx=16)

        self.lbl_annee = tk.Label(bar, text="", bg=HEADER, fg="#94C8F0",
                                   font=("Helvetica", 10))
        self.lbl_annee.pack(side="right", padx=(0,4))

        # Compte à rebours licence (visible seulement si < 24h)
        self.lbl_countdown = tk.Label(bar, text="", bg="#7F1D1D", fg="#FCA5A5",
                                       font=("Helvetica", 10, "bold"),
                                       padx=10, pady=4)
        # Ne pas packer maintenant — visible seulement si nécessaire

        tk.Frame(bar, bg=ACCENT2, width=3).pack(side="right", fill="y",
                                                  padx=8, pady=8)

        # Bouton Mon Compte (côté droit)
        # Bouton Support
        self.btn_support = tk.Button(bar, text="💬  Support",
                                      command=self._ouvrir_support,
                                      bg="#166534", fg="white",
                                      font=("Helvetica", 10, "bold"),
                                      relief=tk.FLAT, cursor="hand2",
                                      padx=12)
        self.btn_support.pack(side="right", padx=(0,4), pady=10)

        self.btn_compte = tk.Button(bar, text="👤  Mon Compte",
                                     command=self._ouvrir_mon_compte,
                                     bg="#1E293B", fg="#93C5FD",
                                     font=("Helvetica", 9, "bold"),
                                     relief=tk.FLAT, cursor="hand2",
                                     padx=10, pady=4,
                                     activebackground="#2563EB",
                                     activeforeground="white")
        self.btn_compte.pack(side="right", padx=8, pady=10)

        tk.Frame(bar, bg=ACCENT2, width=3).pack(side="right", fill="y",
                                                  padx=4, pady=8)

    def _build_quickbar(self):
        """Barre d'accès rapide aux actions les plus fréquentes."""
        bar = tk.Frame(self, bg="#1E293B", relief=tk.FLAT)
        bar.pack(fill="x")

        tk.Label(bar, text="⚡ Accès rapide :", bg="#1E293B", fg="#93C5FD",
                 font=("Helvetica", 10, "bold")).pack(side="left", padx=(12,8), pady=6)

        # Boutons accès rapide — les tâches quotidiennes d'une secrétaire
        self._quick_btns = []
        raccourcis = [
            ("➕ Inscrire un Élève",    "⚡  Inscription Rapide",  "#16A34A"),
            ("📝 Saisir des Notes",     "📝  Saisie des Notes",    "#2563EB"),
            ("📊 Voir les Bilans",      "📊  Bilan & Moyennes",    "#D97706"),
            ("🖨️ Générer Bulletins",    "📊  Bilan & Moyennes",    "#7C3AED"),
            ("⚖️ Matières & Coeff.",   "⚖️  Matières & Coefficients","#059669"),
            ("📜 Historique Notes",     "📜  Historique Notes","#0891B2"),
            ("🚨 Discipline",           "🚨  Discipline",          "#DC2626"),
        ]
        for txt, page, clr in raccourcis:
            b = tk.Button(bar, text=txt,
                          bg=clr, fg="white",
                          font=("Helvetica", 10, "bold"),
                          relief=tk.FLAT, bd=0, cursor="hand2",
                          padx=14, pady=6,
                          command=lambda p=page: self._afficher_page(p))
            b.pack(side="left", padx=4, pady=6)
            b.bind("<Enter>", lambda e, btn=b, c=clr: btn.config(relief=tk.GROOVE,bd=1))
            b.bind("<Leave>", lambda e, btn=b, c=clr: btn.config(relief=tk.FLAT,bd=0))
            self._quick_btns.append(b)

        # Séparateur
        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y",
                                                padx=8, pady=4)
        tk.Label(bar, text="💡 Double-clic sur un élève = voir ses détails  |  F1–F8 = raccourcis clavier  |  Entrée = valider",
                 bg="#1E293B", fg="#64748B",
                 font=("Helvetica", 9, "italic")).pack(side="left", padx=8)

    def _build_sidebar(self, parent):
        """Barre latérale avec catégories et navigation claire."""
        self.sidebar = tk.Frame(parent, bg="#0F172A", width=260)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Titre sidebar
        titre_bar = tk.Frame(self.sidebar, bg=HEADER)
        titre_bar.pack(fill="x")
        tk.Label(titre_bar, text="📋  NAVIGATION", bg=HEADER, fg="white",
                 font=("Helvetica", 11, "bold")).pack(
            side="left", padx=12, pady=10)

        # Contenu scrollable
        canvas_sb = tk.Canvas(self.sidebar, bg="#0F172A", bd=0,
                               highlightthickness=0, width=258)
        canvas_sb.pack(fill="both", expand=True)

        vsb_sb = tk.Scrollbar(self.sidebar, orient="vertical",
                               command=canvas_sb.yview)
        canvas_sb.configure(yscrollcommand=vsb_sb.set)

        self._sb_inner = tk.Frame(canvas_sb, bg="#0F172A")
        canvas_sb.create_window((0,0), window=self._sb_inner, anchor="nw", width=258)
        self._sb_inner.bind("<Configure>",
                             lambda e: canvas_sb.configure(
                                 scrollregion=canvas_sb.bbox("all")))
        canvas_sb.bind("<MouseWheel>",
                        lambda e: canvas_sb.yview_scroll(
                            int(-1*(e.delta/120)), "units"))

    def _build_statusbar(self):
        """Barre de statut en bas."""
        bar = tk.Frame(self, bg="#1E293B", height=28, relief=tk.FLAT)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.barre_statut = tk.Label(bar, text="  ✅  Prêt — Bienvenue",
                                      bg="#1E293B", fg=G_GREEN,
                                      font=("Helvetica", 10, "bold"),
                                      anchor="w")
        self.barre_statut.pack(side="left", padx=8, fill="y")

        tk.Label(bar, text="🏫 Gestion Scolaire — © 2025",
                 bg="#1E293B", fg="#64748B",
                 font=("Helvetica", 9)).pack(side="right", padx=10)

    # ═══════════════════════════════════════════════════════════════
    # HORLOGE TEMPS RÉEL
    # ═══════════════════════════════════════════════════════════════

    def _tick(self):
        from datetime import datetime as _dt
        now = _dt.now()
        self.lbl_clock.config(text=now.strftime("%H:%M:%S"))
        self._check_licence_countdown()
        self.after(1000, self._tick)

    def _check_licence_countdown(self):
        """
        - < 24h  : bandeau orange avec temps restant
        - < 1h   : bandeau rouge clignotant + compte à rebours secondes
        - Expirée: bloque l'accès complètement
        """
        try:
            from licence_manager import charger_et_verifier
            from datetime import datetime as _dt
            lic = charger_et_verifier()

            # Pas d'expiration → rien à faire
            exp_str = lic.get("expiration","")
            if not exp_str or exp_str == "Illimitée":
                self.lbl_countdown.pack_forget()
                return

            exp_date = _dt.strptime(exp_str, "%Y-%m-%d")
            self._exp_str = exp_date.strftime("%d/%m/%Y")
            now      = _dt.now()
            secs     = int((exp_date - now).total_seconds())

            if secs <= 0:
                # ── EXPIRÉE → bloquer l'accès ─────────────────
                self.lbl_countdown.pack_forget()
                self._bloquer_acces_expire()
                return

            elif secs <= 3600:
                # ── MOINS D'1 HEURE → compte à rebours rouge ──
                m = secs // 60
                s = secs % 60
                # Clignotement : alterner rouge foncé / rouge vif
                if not hasattr(self, "_blink_state"):
                    self._blink_state = False
                self._blink_state = not self._blink_state
                bg = "#DC2626" if self._blink_state else "#7F1D1D"
                self.lbl_countdown.config(
                    text=f"🚨  Licence expire dans  {m:02d}m {s:02d}s  🚨",
                    bg=bg, fg="white",
                    font=("Helvetica", 11, "bold"))
                self.lbl_countdown.pack(side="right", padx=6)

            elif secs <= 86400:
                # ── MOINS DE 24H → bandeau orange ─────────────
                h = secs // 3600
                m = (secs % 3600) // 60
                self.lbl_countdown.config(
                    text=f"⏳  Licence expire dans  {h}h {m:02d}m",
                    bg="#92400E", fg="#FCD34D",
                    font=("Helvetica", 10, "bold"))
                self.lbl_countdown.pack(side="right", padx=6)

            else:
                self.lbl_countdown.pack_forget()

        except Exception:
            pass

    def _bloquer_acces_expire(self):
        """Bloque toute l'interface quand la licence est expirée."""
        if getattr(self, "_acces_bloque", False):
            return
        self._acces_bloque = True

        # Masquer tout le contenu
        for widget in self.winfo_children():
            try: widget.pack_forget()
            except Exception: pass

        # Écran de blocage
        bloc = tk.Frame(self, bg="#0F172A")
        bloc.pack(fill="both", expand=True)

        tk.Label(bloc, text="⛔", bg="#0F172A",
                 font=("Helvetica", 72)).pack(pady=(80, 10))

        tk.Label(bloc,
                 text="LICENCE EXPIRÉE",
                 bg="#0F172A", fg="#DC2626",
                 font=("Helvetica", 28, "bold")).pack()

        tk.Label(bloc,
                 text="Votre licence est expirée.\nLe logiciel est bloqué jusqu'au renouvellement.",
                 bg="#0F172A", fg="#94A3B8",
                 font=("Helvetica", 12),
                 justify="center").pack(pady=14)

        # Encart contact
        contact = tk.Frame(bloc, bg="#1E293B")
        contact.pack(padx=80, pady=10, fill="x")
        tk.Label(contact,
                 text="📞  Contactez votre revendeur pour renouveler",
                 bg="#1E293B", fg="#C8A951",
                 font=("Helvetica", 11, "bold")).pack(pady=12)

        # Bouton activer une nouvelle clé
        tk.Button(bloc,
                  text="🔑  Entrer une nouvelle clé de licence",
                  command=self._ouvrir_activation,
                  bg="#2563EB", fg="white",
                  font=("Helvetica", 12, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  padx=24, pady=12).pack(pady=16)

        # Date d'expiration
        tk.Label(bloc,
                 text=f"Licence expirée le : {getattr(self, '_exp_str', '—')}",
                 bg="#0F172A", fg="#475569",
                 font=("Helvetica", 9)).pack(pady=4)

    def _ouvrir_activation(self):
        """Rouvre la fenêtre d'activation pour entrer une nouvelle clé."""
        from licence_window import LicenceWindow
        def _on_success():
            # Relancer l'app après activation
            import os, sys
            os.execv(sys.executable, [sys.executable] + sys.argv)
        LicenceWindow(self, on_success=_on_success)

    # ═══════════════════════════════════════════════════════════════
    # CRÉATION DES PAGES
    # ═══════════════════════════════════════════════════════════════

    def _creer_pages(self):
        from accueil_page       import AccueilPage
        from eleve_manager      import EleveManager
        from classe_manager     import ClasseManager
        from matiere_manager    import MatiereManager
        from personnel_manager  import PersonnelManager
        from note_manager       import NoteManager
        from bilan_manager      import BilanManager
        from coeff_manager      import CoeffManager
        from discipline_manager import DisciplineManager
        from year_manager       import YearManager
        from archive_manager    import ArchiveManager
        from admin_manager      import AdminManager
        from aide_page          import AidePage
        from promotion_manager  import PromotionManager
        from historique_notes   import HistoriqueNotes
        from user_manager        import UserManager
        from inscription_rapide import InscriptionRapide

        self.accueil_page    = AccueilPage(self.contenu, self)
        self.eleve_mgr       = EleveManager(self.contenu)
        self.classe_mgr      = ClasseManager(self.contenu)
        self.matiere_mgr     = MatiereManager(self.contenu)
        self.personnel_mgr   = PersonnelManager(self.contenu)
        self.note_mgr        = NoteManager(self.contenu, main_window=self)
        self.bilan_mgr       = BilanManager(self.contenu)
        self.coeff_mgr       = CoeffManager(self.contenu)
        self.discipline_mgr  = DisciplineManager(self.contenu)
        self.year_mgr        = YearManager(self.contenu, evolution_callback=self._handle_evolution)
        self.archive_mgr     = ArchiveManager(self.contenu)
        self.admin_mgr       = AdminManager(self.contenu, main_window=self)
        self.aide_page       = AidePage(self.contenu, self)
        self.promotion_mgr   = PromotionManager(self.contenu)
        self.historique_mgr  = HistoriqueNotes(self.contenu, main_window=self)
        self.user_mgr        = UserManager(self.contenu)
        self.inscription_mgr = InscriptionRapide(self.contenu, main_window=self)

        # ── Menu avec catégories ──────────────────────────────────
        categories = [
            {
                "titre": "🏠  ACCUEIL",
                "couleur": HEADER,
                "items": [
                    ("🏠  Accueil",           self.accueil_page),
                ]
            },
            {
                "titre": "👥  ÉLÈVES",
                "couleur": "#1E6B3C",
                "items": [
                    ("👨‍🎓  Élèves",              self.eleve_mgr),
                    ("⚡  Inscription Rapide",   self.inscription_mgr),
                    ("🏫  Classes",              self.classe_mgr),
                    ("⚖️  Matières & Coefficients", self.coeff_mgr),
                    ("🚨  Discipline",           self.discipline_mgr),
                    ("📝  Examen Blanc",          self.promotion_mgr),
                ]
            },
            {
                "titre": "📚  NOTES & RÉSULTATS",
                "couleur": "#1A4FA8",
                "items": [
                    ("📝  Saisie des Notes",     self.note_mgr),
                    ("📜  Historique Notes",     self.historique_mgr),
                    ("📊  Bilan & Moyennes",     self.bilan_mgr),
                ]
            },
            {
                "titre": "⚙️  ADMINISTRATION",
                "couleur": "#6B3EC4",
                "items": [
                    ("📚  Matières",             self.matiere_mgr),
                    ("👨‍🏫  Personnel",            self.personnel_mgr),
                    ("⚙️  Configuration",         self.admin_mgr),
                    ("👤  Utilisateurs",            self.user_mgr),
                    ("📅  Année Scolaire",        self.year_mgr),
                    ("📂  Archivage",             self.archive_mgr),
                    ("❓  Aide",                 self.aide_page),
                ]
            },
        ]

        self.nav_boutons = {}

        for cat in categories:
            # En-tête catégorie
            cat_hdr = tk.Frame(self._sb_inner, bg=cat["couleur"])
            cat_hdr.pack(fill="x", pady=(6, 0))
            tk.Label(cat_hdr, text=cat["titre"],
                     bg=cat["couleur"], fg="white",
                     font=("Helvetica", 9, "bold"),
                     anchor="w").pack(side="left", padx=10, pady=5)

            # Boutons de la catégorie
            for label, page in cat["items"]:
                b = tk.Button(
                    self._sb_inner, text=f"  {label}",
                    command=lambda p=page, l=label: self._afficher_page(l),
                    bg="#0F172A", fg="#CBD5E1",
                    font=("Helvetica", 11),
                    relief=tk.FLAT, anchor="w",
                    padx=10, pady=9,
                    cursor="hand2",
                    activebackground="#1E293B",
                    activeforeground="#93C5FD", bd=0, width=28)
                b.pack(fill="x", padx=2, pady=1)

                # Hover effect
                def on_enter(e, btn=b, c=cat["couleur"]):
                    if btn.cget("bg") != "#1E3A5F":  # pas actif
                        btn.config(bg="#1E293B", fg="#93C5FD")
                def on_leave(e, btn=b):
                    if btn.cget("bg") != "#1E3A5F":  # pas actif
                        btn.config(bg="#0F172A", fg="#CBD5E1")

                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
                self.nav_boutons[label] = (b, page)

        # Pied de sidebar
        tk.Frame(self._sb_inner, bg="#334155", height=1).pack(fill="x", pady=8)
        tk.Label(self._sb_inner, text="© 2025 Gestion Scolaire",
                 bg="#0F172A", fg="#475569",
                 font=("Helvetica", 7)).pack(pady=4)

        # Afficher accueil
        self._afficher_page("🏠  Accueil")
        self._rafraichir_infos()

    def _est_bloque(self, module_nom):
        """Vérifie si un module est bloqué par l'administrateur distant."""
        try:
            import json
            from pathlib import Path
            bf = Path(__file__).parent / "modules_bloques.json"
            if bf.exists():
                return module_nom in json.loads(bf.read_text())
        except Exception:
            pass
        return False

    def _afficher_page(self, label_actif):
        # Vérifier si le module est bloqué
        if self._est_bloque(label_actif):
            from tkinter import messagebox
            messagebox.showerror("Module désactivé",
                f"Le module '{label_actif.strip()}' est temporairement\n"
                "désactivé par votre administrateur.\n"
                "Contactez le support pour plus d'informations.")
            return
        # Cacher toutes les pages
        for label, (b, page) in self.nav_boutons.items():
            page.pack_forget()
            if label == label_actif:
                # Bouton actif : fond bleu clair + texte bleu
                b.config(bg="#1E3A5F", fg="#93C5FD",
                         relief=tk.FLAT, bd=0,
                         font=("Helvetica", 11, "bold"))
            else:
                b.config(bg="#0F172A", fg="#CBD5E1",
                         relief=tk.FLAT, bd=0,
                         font=("Helvetica", 11))

        # Afficher la page active
        if label_actif in self.nav_boutons:
            _, page_active = self.nav_boutons[label_actif]
            page_active.pack(fill="both", expand=True)
            self._page_active = label_actif
            # Rafraîchir si possible
            if hasattr(page_active, "rafraichir"):
                page_active.rafraichir()
            # Mettre à jour la barre de statut
            self.afficher_statut(f"Module : {label_actif.strip()}")

    def _rafraichir_infos(self):
        """Charge le nom de l'établissement et l'année depuis la BDD."""
        try:
            from database import Session, ConfigurationGlobale
            s = Session()
            cfg = s.query(ConfigurationGlobale).first()
            s.close()
            if cfg:
                etab  = getattr(cfg, "nom_etablissement", "") or ""
                annee = getattr(cfg, "annee_academique_en_cours", "") or "—"
                self.lbl_etab.config(text=etab.upper())
                self.lbl_annee.config(text=f"Année {annee}")
        except Exception:
            pass

    def afficher_statut(self, message, duree=4000, ok=True):
        icone = "✅" if ok else "⚠️"
        couleur = G_GREEN if ok else G_ORANGE
        self.barre_statut.config(text=f"  {icone}  {message}", fg=couleur)
        self.after(duree, lambda: self.barre_statut.config(
            text="  ✅  Prêt", fg=G_GREEN))

    def _ouvrir_support(self):
        try:
            from support_chat import SupportChat
            SupportChat(self)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erreur", str(e))

    def _ouvrir_mon_compte(self):
        """Ouvre la fenêtre de gestion du compte connecté."""
        from mon_compte_dialog import MonCompteDialog
        dlg = MonCompteDialog(self, self.user_info)
        self.wait_window(dlg)
        # Mettre à jour le bouton si le nom a changé
        if self.user_info:
            self.btn_compte.config(
                text=f"👤  {self.user_info.get('nom') or self.user_info.get('login','')}"
            )

    def _handle_evolution(self, *a):
        pass


# Pseudo-constante pour les hover (défini après la palette)
C_BLUE_HOVER = "#EFF6FF"
