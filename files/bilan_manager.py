# bilan_manager.py — Bilan des Notes, Moyennes et Génération de Bulletins PDF

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import os

from widgets_communs import (BG, PANEL, CARD, HEADER, ACCENT, ACCENT2, TEXT, MUTED,
                              G_GREEN, G_BLUE, G_RED, G_ORANGE, G_PURPLE,
                              make_treeview, btn, entete_module,
                              popup_info, popup_erreur, popup_confirmation)
from signals import db_signals
from utils_notes import calculate_moyenne_matiere, get_mention

# Mappage période nom → clé BDD
PERIODE_TO_KEY = {
    "Trimestre 1": "T1", "Trimestre 2": "T2", "Trimestre 3": "T3",
    "Semestre 1": "S1", "Semestre 2": "S2",
    "Annuel": "Annuel", "Toutes": None,
}


class BilanManager(tk.Frame):
    def __init__(self, parent, main_window=None):
        super().__init__(parent, bg=BG)
        self.main_window       = main_window
        self._classes_dict     = {}
        self._coefficients_db  = {}
        self._matieres_liste   = []
        self._data_export      = []
        self._data_rows        = []  # [(eleve, moyennes_mat, moy_gen), ...]

        self._build_ui()
        db_signals.notes_updated.connect(self.charger_bilan)
        db_signals.classes_updated.connect(self._charger_dependances)
        db_signals.matieres_updated.connect(self._charger_dependances)
        db_signals.coefficients_updated.connect(self._charger_dependances)
        self._charger_dependances()

    # ─── Construction UI ─────────────────────────────────────────────

    def _build_ui(self):
        entete_module(self, "📊  BILAN DES NOTES & MOYENNES")

        # ── Filtres communs (haut) ─────────────────────────────────────
        filtre = tk.LabelFrame(self, text="  🔍  Classe & Période  ",
                               bg=CARD, fg=ACCENT2, font=("Helvetica", 11, "bold"),
                               relief=tk.GROOVE, bd=3)
        filtre.pack(fill="x", padx=8, pady=(8, 4))

        ligne = tk.Frame(filtre, bg=CARD)
        ligne.pack(fill="x", padx=6, pady=8)

        def lbl(t):
            return tk.Label(ligne, text=t, bg=CARD, fg=MUTED, font=("Helvetica", 10, "bold"))

        lbl("Classe :").pack(side="left", padx=(6, 4))
        self.cb_classe = ttk.Combobox(ligne, font=("Helvetica", 11), width=22,
                                      style="App.TCombobox")
        self.cb_classe.pack(side="left", padx=(0, 14))
        self.cb_classe.bind("<<ComboboxSelected>>", lambda e: self.charger_bilan())

        lbl("Période :").pack(side="left", padx=(0, 4))
        self.cb_periode = ttk.Combobox(ligne, font=("Helvetica", 11), width=16,
                                       style="App.TCombobox",
                                       values=["Toutes", "Trimestre 1", "Trimestre 2",
                                               "Trimestre 3", "Semestre 1", "Semestre 2", "Annuel"])
        self.cb_periode.pack(side="left", padx=(0, 14))
        self.cb_periode.set("Toutes")
        self.cb_periode.bind("<<ComboboxSelected>>", lambda e: self.charger_bilan())

        btn(ligne, "🔄 Calculer", self.charger_bilan, G_BLUE, width=12).pack(side="left", padx=4)

        self.lbl_statut = tk.Label(filtre, text="",
                                   bg=CARD, fg=G_GREEN, font=("Helvetica", 9, "italic"))
        self.lbl_statut.pack(anchor="w", padx=10, pady=(0, 6))

        # ── Notebook : 2 onglets ───────────────────────────────────────
        nb = ttk.Notebook(self, style="App.TNotebook")
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        # ── Onglet 1 : Bilan général (stats + PDF) ─────────────────────
        tab_bilan = tk.Frame(nb, bg=BG)
        nb.add(tab_bilan, text="  📊  Bilan Général & PDF  ")
        self._build_tab_bilan(tab_bilan)

        # ── Onglet 2 : Liste des élèves avec moyennes ──────────────────
        tab_eleves = tk.Frame(nb, bg=BG)
        nb.add(tab_eleves, text="  📋  Liste des Élèves & Moyennes  ")
        self._build_tab_eleves(tab_eleves)

    def _build_tab_bilan(self, parent):
        """Onglet 1 — statistiques de classe et génération des PDF."""

        # ── Stats de classe (calculées après charger_bilan) ───────────
        stats_lf = tk.LabelFrame(parent,
                                  text="  📈  Statistiques de la Classe  ",
                                  bg=CARD, fg=ACCENT2,
                                  font=("Helvetica", 11, "bold"),
                                  relief=tk.GROOVE, bd=3)
        stats_lf.pack(fill="x", padx=8, pady=(8, 4))

        self._stats_frame = tk.Frame(stats_lf, bg=CARD)
        self._stats_frame.pack(fill="x", padx=10, pady=10)

        # Placeholder avant calcul
        tk.Label(self._stats_frame,
                 text="Sélectionnez une classe et une période, puis cliquez 🔄 Calculer",
                 bg=CARD, fg=MUTED,
                 font=("Helvetica", 10, "italic")).pack(pady=20)

        # ── Boutons PDF ────────────────────────────────────────────────
        pdf_lf = tk.LabelFrame(parent,
                                text="  🖨️  Générer des Documents PDF  ",
                                bg=CARD, fg=ACCENT2,
                                font=("Helvetica", 11, "bold"),
                                relief=tk.GROOVE, bd=3)
        pdf_lf.pack(fill="x", padx=8, pady=4)

        row1 = tk.Frame(pdf_lf, bg=CARD)
        row1.pack(fill="x", padx=10, pady=8)

        btn(row1, "🖨️ Bulletins Classe (PDF)",
            self._generer_bulletins_classe, G_PURPLE, width=26).pack(side="left", padx=4)
        btn(row1, "🖨️ Bulletin Élève sélectionné",
            self._generer_bulletin_eleve,   ACCENT,   width=26).pack(side="left", padx=4)
        btn(row1, "📄 Fiche Notes Classe",
            self._generer_fiche_notes,      G_ORANGE, width=22).pack(side="left", padx=4)

        row2 = tk.Frame(pdf_lf, bg=CARD)
        row2.pack(fill="x", padx=10, pady=(0, 8))

        btn(row2, "📊 Bilan Annuel — Cette Classe",
            self._generer_bilan_annuel,        G_GREEN,  width=30).pack(side="left", padx=4)
        btn(row2, "📊 Bilan Annuel — Toutes les Classes",
            self._generer_bilan_annuel_global,  G_PURPLE, width=34).pack(side="left", padx=4)

        btn(row2, "🎓 Migration Fin d'Année",
            self._ouvrir_migration, G_ORANGE, width=24).pack(side="left", padx=4)

        btn(row2, "📥 Export CSV",
            self._exporter_csv, MUTED, width=14).pack(side="right", padx=4)

    def _build_tab_eleves(self, parent):
        """Onglet 2 — tableau des élèves avec leurs moyennes par matière."""

        # Barre d'info
        info = tk.Frame(parent, bg=BG)
        info.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(info,
                 text="Double-clic sur un élève pour voir le détail de ses notes",
                 bg=BG, fg=MUTED,
                 font=("Helvetica", 9, "italic")).pack(side="left")

        # Tableau
        self.tree_frame = tk.Frame(parent, bg=PANEL, relief=tk.SUNKEN, bd=2)
        self.tree_frame.pack(fill="both", expand=True, padx=8, pady=4)

        style = ttk.Style()
        style.configure("Bilan.Treeview",
            background="#1E293B", foreground="#E2E8F0",
            fieldbackground="#1E293B",
            rowheight=26, font=("Helvetica", 9))
        style.configure("Bilan.Treeview.Heading",
            background="#1A3A5C", foreground="white",
            font=("Helvetica", 9, "bold"))
        style.map("Bilan.Treeview",
            background=[("selected", "#2563EB")],
            foreground=[("selected", "white")])

        self.tree = ttk.Treeview(self.tree_frame, show="headings",
                                 style="Bilan.Treeview", height=18)
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview,
                            style="App.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview,
                            style="App.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-Button-1>", self._voir_detail_eleve)

        self.tree.tag_configure("admis", background="#1A4A2A", foreground="#2ECC71")
        self.tree.tag_configure("echec", background="#4A1A1A", foreground="#E74C3C")
        self.tree.tag_configure("moyen", background="#3A3A1A", foreground="#F39C12")
        self.tree.tag_configure("odd",   background="#0D2137", foreground="#E2E8F0")
        self.tree.tag_configure("even",  background="#16213E", foreground="#E2E8F0")

        # Boutons sous le tableau
        bb2 = tk.Frame(parent, bg=BG)
        bb2.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(bb2, text="Élève sélectionné :", bg=BG, fg=MUTED,
                 font=("Helvetica", 9, "bold")).pack(side="left", padx=(4, 4))
        btn(bb2, "📋 Détail & Notes",
            self._voir_detail_eleve_btn, G_BLUE, width=18).pack(side="left", padx=4)
        btn(bb2, "📊 Courbe d'évolution",
            self._voir_graphique_direct,  G_PURPLE, width=20).pack(side="left", padx=4)
        tk.Label(bb2, text="(ou double-clic sur l'élève)",
                 bg=BG, fg=MUTED,
                 font=("Helvetica", 8, "italic")).pack(side="left", padx=6)

    # ─── Chargements ─────────────────────────────────────────────────

    def _charger_dependances(self, *a):
        from database import Session, Classe, MatiereClasse, Matiere
        from sqlalchemy.orm import joinedload
        s = Session()
        classes = s.query(Classe).order_by(Classe.nom).all()
        self._classes_dict = {"— Toutes les Classes —": None}
        self._classes_dict.update({c.nom: c.id for c in classes})
        self.cb_classe["values"] = list(self._classes_dict.keys())
        if not self.cb_classe.get():
            self.cb_classe.set("— Toutes les Classes —")

        # Coefficients et matières
        self._coefficients_db = {}
        mcs = s.query(MatiereClasse).options(
            joinedload(MatiereClasse.matiere_obj),
            joinedload(MatiereClasse.classe_obj)).all()
        for mc in mcs:
            cid  = mc.classe_id
            mnom = mc.matiere_obj.nom if mc.matiere_obj else ""
            coef = mc.coefficient or 1
            self._coefficients_db.setdefault(cid, {})[mnom] = coef

        self._matieres_liste = s.query(Matiere).order_by(Matiere.nom).all()
        s.close()
        self.charger_bilan()

    def charger_bilan(self, *a):
        from database import Session, Eleve, Matiere, Note, Evaluation
        from sqlalchemy.orm import joinedload
        from sqlalchemy import func

        s = Session()
        try:
            classe_nom   = self.cb_classe.get()
            classe_id    = self._classes_dict.get(classe_nom)
            periode_nom  = self.cb_periode.get()
            periode_key  = PERIODE_TO_KEY.get(periode_nom)  # None = toutes

            # Élèves
            q = s.query(Eleve).options(joinedload(Eleve.classe))
            if classe_id:
                q = q.filter(Eleve.classe_id == classe_id)
            eleves = q.filter(Eleve.est_actif == True).order_by(Eleve.nom).all()

            # Toutes les matières (si filtre classe → seulement celles de la classe)
            if classe_id:
                from database import MatiereClasse
                mcs = s.query(MatiereClasse).options(
                    joinedload(MatiereClasse.matiere_obj)).filter_by(classe_id=classe_id).all()
                matieres = [mc.matiere_obj for mc in mcs if mc.matiere_obj]
            else:
                matieres = s.query(Matiere).order_by(Matiere.nom).all()

            # Colonnes dynamiques
            cols  = ["rang", "nom_prenom", "classe", "moy_gen", "mention"] + [m.nom for m in matieres]
            heads = ["Rang", "Élève", "Classe", "Moy. Gén.", "Mention"] + [m.nom for m in matieres]
            self.tree["columns"] = cols
            for col, head in zip(cols, heads):
                w = 50 if col == "rang" else (180 if col == "nom_prenom" else
                    120 if col == "classe" else 90 if col in ("moy_gen","mention") else 80)
                self.tree.heading(col, text=head)
                self.tree.column(col, width=w, anchor="center" if col != "nom_prenom" else "w",
                                 minwidth=50)

            self.tree.delete(*self.tree.get_children())
            self._data_export = [heads]
            self._data_rows   = []

            for eleve in eleves:
                moyennes_mat = {}
                notes_brutes = {}  # {mat_nom: [Note]}

                for mat in matieres:
                    q_notes = (s.query(Note)
                               .join(Note.evaluation)
                               .options(joinedload(Note.evaluation))
                               .filter(Note.eleve_id == eleve.id,
                                       Note.matiere_id == mat.id))
                    if periode_key:
                        q_notes = q_notes.filter(Evaluation.periode == periode_key)
                    notes = q_notes.all()
                    notes_brutes[mat.nom] = notes
                    if notes:
                        moy, _, _ = calculate_moyenne_matiere(notes)
                        moyennes_mat[mat.nom] = moy
                    else:
                        moyennes_mat[mat.nom] = None

                # Moyenne générale pondérée
                coeffs      = self._coefficients_db.get(eleve.classe_id, {})
                total_pts   = 0.0
                total_coeff = 0.0
                for mat_nom, moy in moyennes_mat.items():
                    if moy is not None:
                        coeff = coeffs.get(mat_nom, 1)
                        total_pts   += moy * coeff
                        total_coeff += coeff
                moy_gen = round(total_pts / total_coeff, 2) if total_coeff > 0 else None

                self._data_rows.append({
                    "eleve": eleve, "moyennes_mat": moyennes_mat,
                    "notes_brutes": notes_brutes, "moy_gen": moy_gen
                })

            # Calcul du rang
            rows_avec = [r for r in self._data_rows if r["moy_gen"] is not None]
            rows_avec.sort(key=lambda r: r["moy_gen"], reverse=True)
            rang = 1
            for i, r in enumerate(rows_avec):
                r["rang"] = rang
                if i + 1 < len(rows_avec) and rows_avec[i+1]["moy_gen"] != r["moy_gen"]:
                    rang += 1
                elif i + 1 < len(rows_avec):
                    pass  # ex-aequo
                else:
                    rang += 1
            for r in self._data_rows:
                if "rang" not in r:
                    r["rang"] = "—"

            # Trier et afficher
            sorted_rows = sorted(self._data_rows,
                                  key=lambda r: r["moy_gen"] if r["moy_gen"] else -1,
                                  reverse=True)

            for i, r in enumerate(sorted_rows):
                eleve   = r["eleve"]
                moy_gen = r["moy_gen"]
                rang_v  = r.get("rang", "—")

                classe_nom_e = eleve.classe.nom if eleve.classe else "—"
                moy_gen_str  = f"{moy_gen:.2f}" if moy_gen is not None else "—"
                mention      = get_mention(moy_gen) if moy_gen is not None else "—"

                row = [rang_v, f"{eleve.nom} {eleve.prenom}", classe_nom_e,
                       moy_gen_str, mention]
                row += [f"{r['moyennes_mat'].get(m.nom):.2f}"
                        if r['moyennes_mat'].get(m.nom) is not None else "—"
                        for m in matieres]
                self._data_export.append(row)

                if moy_gen is None:
                    tag = "odd" if i % 2 == 0 else "even"
                elif moy_gen >= 14:
                    tag = "admis"
                elif moy_gen >= 10:
                    tag = "moyen"
                else:
                    tag = "echec"

                self.tree.insert("", "end", iid=str(eleve.id), values=row, tags=(tag,))

            # Mettre à jour les statistiques dans l'onglet Bilan Général
            self._afficher_stats_bilan()

        finally:
            s.close()

    # ─── Stats onglet Bilan Général ──────────────────────────────────

    def _afficher_stats_bilan(self):
        """Affiche les statistiques de la classe dans l'onglet Bilan Général."""
        for w in self._stats_frame.winfo_children():
            w.destroy()

        rows = self._data_rows
        if not rows:
            tk.Label(self._stats_frame,
                     text="Aucune donnée — cliquez 🔄 Calculer",
                     bg=CARD, fg=MUTED,
                     font=("Helvetica", 10, "italic")).pack(pady=20)
            return

        valides = [r for r in rows if r["moy_gen"] is not None]
        admis   = [r for r in valides if r["moy_gen"] >= 10]
        nb_tot  = len(rows)
        nb_val  = len(valides)
        taux    = round(len(admis) / nb_val * 100, 1) if nb_val else 0
        moy_cl  = round(sum(r["moy_gen"] for r in valides) / nb_val, 2) if nb_val else 0
        moy_max = max((r["moy_gen"] for r in valides), default=0)
        moy_min = min((r["moy_gen"] for r in valides), default=0)
        premier = next((r for r in sorted(valides, key=lambda x: x["moy_gen"], reverse=True)), None)
        dernier = next((r for r in sorted(valides, key=lambda x: x["moy_gen"])), None)

        # Cartes statistiques
        row_cards = tk.Frame(self._stats_frame, bg=CARD)
        row_cards.pack(fill="x", pady=8)

        stats = [
            ("👥", "Effectif",      str(nb_tot),          "#1E3A5F", "#93C5FD"),
            ("✅", "Admis",         f"{len(admis)}/{nb_val}", "#14532D", "#86EFAC"),
            ("📊", "Taux réussite", f"{taux}%",            "#7C2D12" if taux < 50 else "#14532D",
                                                             "#FCA5A5" if taux < 50 else "#86EFAC"),
            ("📈", "Moy. classe",   f"{moy_cl}/20",        "#1A3A5C", "#93C5FD"),
            ("🥇", "1er de classe", f"{moy_max}/20",       "#14532D", "#86EFAC"),
            ("🔻", "Dernier",       f"{moy_min}/20",       "#7F1D1D", "#FCA5A5"),
        ]

        for col, (ico, titre, val, bg_c, clr) in enumerate(stats):
            c = tk.Frame(row_cards, bg=bg_c, relief=tk.FLAT)
            c.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
            row_cards.columnconfigure(col, weight=1)
            tk.Label(c, text=ico, bg=bg_c,
                     font=("Helvetica", 20)).pack(pady=(10, 2))
            tk.Label(c, text=val, bg=bg_c, fg=clr,
                     font=("Helvetica", 16, "bold")).pack()
            tk.Label(c, text=titre, bg=bg_c, fg="#CBD5E1",
                     font=("Helvetica", 9)).pack(pady=(2, 10))

        # Ligne meilleur/dernier élève
        if premier and dernier:
            info_row = tk.Frame(self._stats_frame, bg=CARD)
            info_row.pack(fill="x", padx=6, pady=(0, 8))
            e_prem = premier["eleve"]
            e_dern = dernier["eleve"]
            tk.Label(info_row,
                     text=f"🥇  1er  :  {e_prem.nom} {e_prem.prenom}  —  {premier['moy_gen']:.2f}/20",
                     bg="#14532D", fg="#86EFAC",
                     font=("Helvetica", 10, "bold"),
                     padx=12, pady=6).pack(side="left", padx=(0, 8), fill="x", expand=True)
            tk.Label(info_row,
                     text=f"🔻  Dernier :  {e_dern.nom} {e_dern.prenom}  —  {dernier['moy_gen']:.2f}/20",
                     bg="#7F1D1D", fg="#FCA5A5",
                     font=("Helvetica", 10, "bold"),
                     padx=12, pady=6).pack(side="left", fill="x", expand=True)

    # ─── Détail élève ─────────────────────────────────────────────────

    def _voir_detail_eleve(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        eleve_id = int(sel[0])
        row_data = next((r for r in self._data_rows if r["eleve"].id == eleve_id), None)
        if not row_data:
            return

        eleve       = row_data["eleve"]
        moys        = {k: v for k, v in row_data["moyennes_mat"].items() if v is not None}
        notes_brutes = row_data.get("notes_brutes", {})

        from detail_eleve_dialog import DetailEleveDialog
        DetailEleveDialog(self, f"{eleve.nom} {eleve.prenom}", moys, notes_brutes)

    # ─── Détail et graphique ──────────────────────────────────────

    def _voir_detail_eleve_btn(self):
        """Bouton direct : ouvre le détail de l'élève sélectionné."""
        class FakeEvent: pass
        self._voir_detail_eleve(FakeEvent())

    def _voir_graphique_direct(self):
        """Ouvre directement la fenêtre de choix de matière pour le graphique."""
        sel = self.tree.selection()
        if not sel:
            from tkinter import messagebox
            messagebox.showwarning("Attention", "Sélectionnez d'abord un élève.")
            return
        eleve_id = int(sel[0])
        row_data = next((r for r in self._data_rows if r["eleve"].id == eleve_id), None)
        if not row_data:
            return

        eleve        = row_data["eleve"]
        notes_brutes = row_data.get("notes_brutes", {})
        matieres     = [m for m, notes in notes_brutes.items() if notes]

        if not matieres:
            from tkinter import messagebox
            messagebox.showinfo("Info", f"Aucune note trouvée pour {eleve.nom} {eleve.prenom}.")
            return

        # Si une seule matière → ouvrir directement le graphe
        if len(matieres) == 1:
            self._ouvrir_graphe(eleve, matieres[0], notes_brutes[matieres[0]])
            return

        # Sinon → popup de sélection de matière
        win = tk.Toplevel(self)
        win.title(f"Choisir une matière — {eleve.nom} {eleve.prenom}")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.update_idletasks()
        win.grab_set()

        tk.Label(win, text=f"📊 Courbe d'évolution pour :",
                 bg=BG, fg=ACCENT, font=("Helvetica", 12, "bold")).pack(pady=(12,4))
        tk.Label(win, text=f"{eleve.nom} {eleve.prenom}",
                 bg=BG, fg=TEXT, font=("Helvetica", 11)).pack(pady=(0,10))

        from tkinter import ttk as _ttk
        lb = tk.Listbox(win, bg=CARD, fg=TEXT, font=("Helvetica", 11),
                        selectbackground=ACCENT, selectforeground="white",
                        height=min(len(matieres), 12), width=30,
                        relief=tk.SUNKEN, bd=2)
        lb.pack(padx=20, pady=6)
        for m in matieres:
            lb.insert(tk.END, m)
        lb.selection_set(0)

        def ouvrir():
            sel_mat = lb.curselection()
            if not sel_mat:
                return
            mat_nom = lb.get(sel_mat[0])
            win.destroy()
            self._ouvrir_graphe(eleve, mat_nom, notes_brutes[mat_nom])

        btn(win, "📊 Voir le graphique", ouvrir, G_PURPLE, width=22).pack(pady=6)
        btn(win, "✖ Annuler", win.destroy, MUTED, width=10).pack(pady=(0,10))
        lb.bind("<Double-Button-1>", lambda e: ouvrir())

    def _ouvrir_graphe(self, eleve, mat_nom, notes_brutes):
        """Ouvre GraphDialog pour une matière donnée."""
        data_graph = []
        for n in notes_brutes:
            try:
                v = float(n.valeur)
                data_graph.append((v, n.date_enregistrement, getattr(n, "coefficient", 1)))
            except Exception:
                pass
        if not data_graph:
            from tkinter import messagebox
            messagebox.showinfo("Info", f"Aucune note numérique pour {mat_nom}.")
            return
        from graph_dialog import GraphDialog
        GraphDialog(self, f"{eleve.nom} {eleve.prenom}", mat_nom, data_graph)

    # ─── Exports CSV ──────────────────────────────────────────────────

    def _exporter_csv(self):
        if not self._data_export:
            popup_erreur("Erreur", "Calculez le bilan d'abord.")
            return
        fichier = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichiers CSV", "*.csv")],
            initialfile="bilan_notes.csv")
        if not fichier:
            return
        with open(fichier, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerows(self._data_export)
        popup_info("Succès", f"Bilan exporté :\n{fichier}")

    # ─── Génération PDF ───────────────────────────────────────────────

    def _get_classe_periode(self):
        """Vérifie et retourne (classe_id, periode_label) ou None si invalide."""
        classe_nom  = self.cb_classe.get()
        classe_id   = self._classes_dict.get(classe_nom)
        periode_nom = self.cb_periode.get()

        if not classe_id:
            popup_erreur("Erreur", "Sélectionnez une classe (pas 'Toutes') pour générer un PDF.")
            return None, None
        if periode_nom == "Toutes" or not periode_nom:
            popup_erreur("Erreur", "Sélectionnez une période spécifique pour générer un PDF.")
            return None, None
        return classe_id, periode_nom

    def _generer_bulletins_classe(self):
        classe_id, periode_nom = self._get_classe_periode()
        if not classe_id:
            return

        fichier = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
            initialfile=f"bulletins_{self.cb_classe.get().replace(' ','_')}_{periode_nom.replace(' ','_')}.pdf")
        if not fichier:
            return

        self.lbl_statut.config(text="⏳ Génération en cours...", fg=G_ORANGE)
        self.update()
        try:
            from html_exporter import export_bulletin_pdf
            export_bulletin_pdf(None, None, classe_id, periode_nom, fichier, is_class_export=True)
            self.lbl_statut.config(text=f"✅ Bulletins générés : {os.path.basename(fichier)}", fg=G_GREEN)
            popup_info("Succès", f"Bulletins PDF générés !\n{fichier}")
            try:
                import subprocess, sys
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", fichier])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", fichier])
                else:
                    os.startfile(fichier)
            except Exception:
                pass
        except Exception as e:
            self.lbl_statut.config(text=f"❌ Erreur : {e}", fg=G_RED)
            popup_erreur("Erreur PDF", str(e))

    def _generer_fiche_notes(self):
        classe_id, periode_nom = self._get_classe_periode()
        if not classe_id:
            return

        fichier = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
            initialfile=f"fiche_notes_{self.cb_classe.get().replace(' ','_')}_{periode_nom.replace(' ','_')}.pdf")
        if not fichier:
            return

        self.lbl_statut.config(text="⏳ Génération en cours...", fg=G_ORANGE)
        self.update()
        try:
            from html_exporter import export_fiche_notes_pdf
            export_fiche_notes_pdf(None, classe_id, periode_nom, fichier)
            self.lbl_statut.config(text=f"✅ Fiche générée : {os.path.basename(fichier)}", fg=G_GREEN)
            popup_info("Succès", f"Fiche de notes PDF générée !\n{fichier}")
            try:
                import subprocess, sys
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", fichier])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", fichier])
                else:
                    os.startfile(fichier)
            except Exception:
                pass
        except Exception as e:
            self.lbl_statut.config(text=f"❌ Erreur : {e}", fg=G_RED)
            popup_erreur("Erreur PDF", str(e))

    def _generer_bulletin_eleve(self):
        sel = self.tree.selection()
        if not sel:
            popup_erreur("Erreur", "Sélectionnez un élève dans le tableau.")
            return

        eleve_id   = int(sel[0])
        _, periode_nom = self._get_classe_periode()
        if not periode_nom:
            return

        row_data = next((r for r in self._data_rows if r["eleve"].id == eleve_id), None)
        if not row_data:
            return
        eleve = row_data["eleve"]

        fichier = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
            initialfile=f"bulletin_{eleve.nom}_{eleve.prenom}_{periode_nom.replace(' ','_')}.pdf")
        if not fichier:
            return

        self.lbl_statut.config(text="⏳ Génération en cours...", fg=G_ORANGE)
        self.update()
        try:
            from html_exporter import export_bulletin_pdf
            export_bulletin_pdf(None, eleve_id, None, periode_nom, fichier, is_class_export=False)
            self.lbl_statut.config(text=f"✅ Bulletin généré : {os.path.basename(fichier)}", fg=G_GREEN)
            popup_info("Succès", f"Bulletin de {eleve.nom} {eleve.prenom} généré !\n{fichier}")
            try:
                import subprocess, sys
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", fichier])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", fichier])
                else:
                    os.startfile(fichier)
            except Exception:
                pass
        except Exception as e:
            self.lbl_statut.config(text=f"❌ Erreur : {e}", fg=G_RED)
            popup_erreur("Erreur PDF", str(e))

    def _ouvrir_migration(self):
        """Ouvre la fenêtre de migration de fin d'année."""
        try:
            from promotion_fin_annee import PromotionFinAnnee
            PromotionFinAnnee(self)
        except Exception as e:
            from widgets_communs import popup_erreur
            popup_erreur("Erreur", str(e))

    def rafraichir(self):
        self._charger_dependances()

    def _generer_bilan_annuel(self):
        """Génère le bilan annuel complet d'UNE classe en PDF."""
        classe_nom = self.cb_classe.get()
        classe_id  = self._classes_dict.get(classe_nom)
        if not classe_id:
            popup_erreur("Erreur",
                "Sélectionnez une classe précise dans la liste\n"
                "(pas 'Toutes les Classes').")
            return

        import tkinter.filedialog as fd
        fichier = fd.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=f"bilan_annuel_{classe_nom.replace(' ','_')}.pdf")
        if not fichier:
            return

        self.lbl_statut.config(text="⏳ Génération bilan annuel...", fg=G_ORANGE)
        self.update_idletasks()
        try:
            from pdf_reports import generer_bilan_annuel, _ouvrir
            generer_bilan_annuel(fichier, classe_id=classe_id,
                                  classe_nom=classe_nom, toutes_classes=False)
            self.lbl_statut.config(
                text=f"✅ Bilan généré : {os.path.basename(fichier)}", fg=G_GREEN)
            popup_info("Succès", f"✅ Bilan annuel généré !\n{fichier}")
            _ouvrir(fichier)
        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            self.lbl_statut.config(text=f"❌ Erreur : {e}", fg=G_RED)
            popup_erreur("Erreur Bilan Annuel",
                f"Erreur :\n{e}\n\nDétail :\n{detail[-400:]}")

    def _generer_bilan_annuel_global(self):
        """Génère le bilan annuel de TOUTES les classes en un seul PDF."""
        import tkinter.filedialog as fd
        fichier = fd.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile="bilan_annuel_toutes_classes.pdf")
        if not fichier:
            return

        self.lbl_statut.config(text="⏳ Génération bilan toutes classes...", fg=G_ORANGE)
        self.update_idletasks()
        try:
            from pdf_reports import generer_bilan_annuel, _ouvrir
            generer_bilan_annuel(fichier, toutes_classes=True)
            self.lbl_statut.config(
                text=f"✅ Bilan global généré : {os.path.basename(fichier)}", fg=G_GREEN)
            popup_info("Succès", f"✅ Bilan toutes classes généré !\n{fichier}")
            _ouvrir(fichier)
        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            self.lbl_statut.config(text=f"❌ Erreur : {e}", fg=G_RED)
            popup_erreur("Erreur Bilan Global",
                f"Erreur :\n{e}\n\nDétail :\n{detail[-400:]}")
