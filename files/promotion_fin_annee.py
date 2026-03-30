# promotion_fin_annee.py — Migration élèves fin d'année

import tkinter as tk
from tkinter import ttk, messagebox
from widgets_communs import (BG, PANEL, CARD, HEADER, ACCENT, ACCENT2,
                              TEXT, MUTED, BORDER, G_GREEN, G_BLUE, G_RED,
                              G_ORANGE, G_PURPLE, btn, entete_module,
                              make_treeview, popup_info, popup_erreur,
                              popup_confirmation)
from signals import db_signals


class PromotionFinAnnee(tk.Toplevel):
    """
    Migration de fin d'année :
    - Élèves ayant la moyenne → classe supérieure (ignore A/B/C)
    - Élèves en dessous → redoublent
    - Résumé avant confirmation
    """
    def __init__(self, master):
        super().__init__(master)
        self.title("🎓  Migration de Fin d'Année")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.grab_set()

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = min(900, sw-40), min(680, sh-80)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(700, 500)

        self._resultats   = []   # liste des élèves et leur décision
        self._classe_map  = {}   # {id_classe: classe_obj}
        self._build()
        self._charger_classes()

    # ── UI ──────────────────────────────────────────────────────

    def _build(self):
        entete_module(self, "🎓  MIGRATION DE FIN D'ANNÉE")

        # Config
        cfg = tk.LabelFrame(self, text="  ⚙️  Paramètres  ",
                             bg=CARD, fg=ACCENT2,
                             font=("Helvetica", 11, "bold"),
                             relief=tk.GROOVE, bd=2)
        cfg.pack(fill="x", padx=8, pady=8)

        r = tk.Frame(cfg, bg=CARD)
        r.pack(fill="x", padx=10, pady=10)

        def lbl(t): return tk.Label(r, text=t, bg=CARD, fg=MUTED,
                                     font=("Helvetica", 10, "bold"))

        lbl("Classe à migrer :").pack(side="left", padx=(0,6))
        self.cb_classe = ttk.Combobox(r, font=("Helvetica", 11),
                                       width=22, style="App.TCombobox",
                                       state="readonly")
        self.cb_classe.pack(side="left", padx=(0,16))

        lbl("Année scolaire :").pack(side="left", padx=(0,6))
        self.cb_annee = ttk.Combobox(r, font=("Helvetica", 11),
                                      width=14, style="App.TCombobox")
        self.cb_annee.pack(side="left", padx=(0,16))

        lbl("Note de passage :").pack(side="left", padx=(0,6))
        self.e_seuil = tk.Entry(r, bg=BORDER, fg=TEXT,
                                 insertbackground=ACCENT,
                                 font=("Helvetica", 11), width=6,
                                 relief=tk.SUNKEN, bd=2)
        self.e_seuil.insert(0, "10")
        self.e_seuil.pack(side="left", padx=(0,16))

        btn(r, "🔍 Analyser", self._analyser, G_BLUE, width=14).pack(side="left")

        # Info
        self.lbl_info = tk.Label(self, text="Sélectionnez une classe et cliquez Analyser",
                                  bg=BG, fg=MUTED, font=("Helvetica", 9, "italic"))
        self.lbl_info.pack(pady=4)

        # Tableau résultats
        res_f = tk.LabelFrame(self, text="  📋  Résultats de l'analyse  ",
                               bg=CARD, fg=ACCENT2,
                               font=("Helvetica", 11, "bold"),
                               relief=tk.GROOVE, bd=2)
        res_f.pack(fill="both", expand=True, padx=8, pady=4)

        cols  = ("nom", "prenom", "moy", "decision", "vers_classe")
        heads = ("Nom", "Prénom", "Moy. Générale", "Décision", "Nouvelle Classe")
        self.tree = make_treeview(res_f, cols, heads, hauteur=16)
        self.tree.column("nom",       width=160, anchor="w")
        self.tree.column("prenom",    width=130, anchor="w")
        self.tree.column("moy",       width=100, anchor="center")
        self.tree.column("decision",  width=120, anchor="center")
        self.tree.column("vers_classe", width=150, anchor="center")
        self.tree.tag_configure("admis",   background="#1A4A2A", foreground="#2ECC71")
        self.tree.tag_configure("redouble",background="#4A2A1A", foreground="#E67E22")

        # Boutons action
        bb = tk.Frame(self, bg=PANEL)
        bb.pack(fill="x", padx=8, pady=6)

        self.lbl_resume = tk.Label(bb, text="", bg=PANEL, fg=TEXT,
                                    font=("Helvetica", 10, "bold"))
        self.lbl_resume.pack(side="left", padx=12)

        btn(bb, "❌  Annuler", self.destroy, MUTED, width=12).pack(side="right", padx=4)
        self.btn_appliquer = btn(bb, "✅  Appliquer la migration",
                                  self._appliquer, G_GREEN, width=24)
        self.btn_appliquer.pack(side="right", padx=4)
        self.btn_appliquer.config(state="disabled")

    # ── Chargement ──────────────────────────────────────────────

    def _charger_classes(self):
        from database import Session, Classe, ConfigurationGlobale
        s = Session()
        try:
            classes = s.query(Classe).order_by(Classe.niveau, Classe.nom).all()
            self._classe_map = {c.nom: c for c in classes}
            self.cb_classe["values"] = list(self._classe_map.keys())

            cfg = s.query(ConfigurationGlobale).first()
            annee = cfg.annee_academique_en_cours if cfg else "2025-2026"
            self.cb_annee["values"] = [annee]
            self.cb_annee.set(annee)
        finally:
            s.close()

    # ── Analyse ─────────────────────────────────────────────────

    def _analyser(self):
        classe_nom = self.cb_classe.get()
        annee      = self.cb_annee.get().strip()
        try:
            seuil = float(self.e_seuil.get().replace(",", "."))
        except ValueError:
            popup_erreur("Erreur", "La note de passage doit être un nombre.")
            return

        classe = self._classe_map.get(classe_nom)
        if not classe:
            popup_erreur("Erreur", "Sélectionnez une classe.")
            return

        from database import Session, Eleve, Note, Evaluation, MatiereClasse, Classe
        from utils_notes import calculate_moyenne_matiere
        from sqlalchemy.orm import joinedload

        s = Session()
        try:
            # Coefficients de la classe
            mcs = s.query(MatiereClasse).filter_by(classe_id=classe.id).all()
            coeffs = {mc.matiere_id: mc.coefficient or 1 for mc in mcs}
            total_c = sum(coeffs.values()) or 1

            # Trouver la classe supérieure (même nom sans lettre)
            # Ex: 6ème A → 5ème B, 5ème → 4ème
            classe_sup = self._trouver_classe_sup(classe, s)

            eleves = s.query(Eleve).filter_by(
                classe_id=classe.id, est_actif=True
            ).order_by(Eleve.nom, Eleve.prenom).all()

            self._resultats = []
            self.tree.delete(*self.tree.get_children())

            for i, e in enumerate(eleves):
                # Calculer la moyenne générale annuelle
                total_pts, total_coef = 0.0, 0.0
                for mat_id, coeff in coeffs.items():
                    notes = (s.query(Note)
                               .join(Note.evaluation)
                               .filter(Note.eleve_id == e.id,
                                       Note.matiere_id == mat_id,
                                       Evaluation.annee_academique == annee)
                               .all())
                    if notes:
                        moy, _, _ = calculate_moyenne_matiere(notes)
                        if moy is not None:
                            total_pts  += moy * coeff
                            total_coef += coeff

                moy_gen = round(total_pts / total_coef, 2) if total_coef > 0 else None
                admis   = moy_gen is not None and moy_gen >= seuil

                decision   = "✅ ADMIS"     if admis else "🔄 REDOUBLANT"
                vers_classe = classe_sup.nom if (admis and classe_sup) else classe_nom
                tag        = "admis" if admis else "redouble"
                moy_str    = f"{moy_gen:.2f}/20" if moy_gen is not None else "—"

                self._resultats.append({
                    "eleve_id":        e.id,
                    "nom":             e.nom,
                    "prenom":          e.prenom,
                    "moy_gen":         moy_gen,
                    "admis":           admis,
                    "classe_actuelle": classe.id,
                    "classe_cible":    classe_sup.id if (admis and classe_sup) else classe.id,
                })

                self.tree.insert("", "end", values=(
                    e.nom, e.prenom, moy_str, decision, vers_classe
                ), tags=(tag,))

            nb_admis   = sum(1 for r in self._resultats if r["admis"])
            nb_redoub  = len(self._resultats) - nb_admis
            cls_sup_nom = classe_sup.nom if classe_sup else "Inconnue"

            self.lbl_info.config(
                text=f"Analyse terminée — {len(self._resultats)} élève(s) | "
                     f"Seuil : {seuil}/20",
                fg=G_GREEN)
            self.lbl_resume.config(
                text=f"✅ {nb_admis} admis → {cls_sup_nom}   |   "
                     f"🔄 {nb_redoub} redoublant(s)")

            self.btn_appliquer.config(
                state="normal" if self._resultats else "disabled")

        finally:
            s.close()

    def _trouver_classe_sup(self, classe, session):
        """
        Trouve la classe supérieure en cherchant niveau+1.
        Ignore les suffixes A, B, C — prend la première classe du niveau suivant.
        """
        from database import Classe
        classes_sup = (session.query(Classe)
                       .filter(Classe.niveau == classe.niveau + 1,
                               Classe.type_etablissement == classe.type_etablissement)
                       .order_by(Classe.nom).all())
        return classes_sup[0] if classes_sup else None

    # ── Application ─────────────────────────────────────────────

    def _appliquer(self):
        if not self._resultats:
            return

        nb_admis  = sum(1 for r in self._resultats if r["admis"])
        nb_redoub = len(self._resultats) - nb_admis

        if not popup_confirmation("Confirmer la migration",
                f"Cette action va :\n\n"
                f"  • Transférer {nb_admis} élève(s) en classe supérieure\n"
                f"  • Garder {nb_redoub} élève(s) en redoublement\n\n"
                "Cette action est irréversible. Continuer ?"):
            return

        from database import Session, Eleve, DecisionJury, ConfigurationGlobale
        s = Session()
        try:
            cfg = s.query(ConfigurationGlobale).first()
            annee = cfg.annee_academique_en_cours if cfg else "2025-2026"
            nb_ok = 0

            for r in self._resultats:
                eleve = s.get(Eleve, r["eleve_id"])
                if not eleve:
                    continue

                # Changer la classe
                eleve.classe_id = r["classe_cible"]

                # Enregistrer la décision
                dec = DecisionJury(
                    eleve_id=r["eleve_id"],
                    decision="ADMIS" if r["admis"] else "REDOUBLANT",
                    periode="ANNUEL",
                    annee_academique=annee,
                )
                s.add(dec)
                nb_ok += 1

            s.commit()
            db_signals.eleves_updated.emit()

            popup_info("✅ Migration terminée",
                       f"{nb_ok} élève(s) traité(s) avec succès !\n\n"
                       f"• {nb_admis} transféré(s) en classe supérieure\n"
                       f"• {nb_redoub} conservé(s) en redoublement")
            self.destroy()

        except Exception as e:
            s.rollback()
            popup_erreur("Erreur", str(e))
        finally:
            s.close()
