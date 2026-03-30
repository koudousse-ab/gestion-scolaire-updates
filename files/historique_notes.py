# historique_notes.py — Historique des Notes & Modifications

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from widgets_communs import (BG, PANEL, CARD, HEADER, ACCENT, ACCENT2, TEXT, MUTED,
                              G_GREEN, G_BLUE, G_RED, G_ORANGE, G_PURPLE,
                              make_treeview, btn, entete_module,
                              popup_info, popup_erreur, popup_confirmation)
from signals import db_signals

# Clés BDD → libellé affiché
KEY_TO_PERIODE = {
    "T1": "Trimestre 1", "T2": "Trimestre 2", "T3": "Trimestre 3",
    "S1": "Semestre 1",  "S2": "Semestre 2",  "Annuel": "Annuel",
}


class HistoriqueNotes(tk.Frame):

    def __init__(self, parent, main_window=None):
        super().__init__(parent, bg=BG)
        self.main_window = main_window
        self._classes_dict  = {}
        self._matieres_dict = {}
        self._data_rows     = []   # données brutes pour édition

        self._build_ui()
        db_signals.notes_updated.connect(self.charger)
        db_signals.classes_updated.connect(self._charger_filtres)
        self._charger_filtres()

    # ═══════════════════════════════════════════════════════════════
    # CONSTRUCTION UI
    # ═══════════════════════════════════════════════════════════════

    def _build_ui(self):
        entete_module(self, "📜  HISTORIQUE DES NOTES")

        # ── Filtres ───────────────────────────────────────────────────
        flt = tk.LabelFrame(self,
                            text="  🔍  Filtres  ",
                            bg=CARD, fg=ACCENT2, font=("Helvetica", 11, "bold"),
                            relief=tk.GROOVE, bd=4)
        flt.pack(fill="x", padx=8, pady=4)

        ligne = tk.Frame(flt, bg=CARD)
        ligne.pack(fill="x", padx=6, pady=6)

        def lbl(t):
            return tk.Label(ligne, text=t, bg=CARD, fg=MUTED,
                            font=("Helvetica", 9, "bold"))

        lbl("Classe :").pack(side="left", padx=(6, 2))
        self.cb_classe = ttk.Combobox(ligne, font=("Helvetica", 10), width=18,
                                      style="App.TCombobox", state="readonly")
        self.cb_classe.pack(side="left", padx=(0, 10))
        self.cb_classe.bind("<<ComboboxSelected>>", lambda e: self._on_classe_filtre())

        lbl("Matière :").pack(side="left", padx=(0, 2))
        self.cb_matiere = ttk.Combobox(ligne, font=("Helvetica", 10), width=18,
                                       style="App.TCombobox", state="readonly")
        self.cb_matiere.pack(side="left", padx=(0, 10))

        lbl("Période :").pack(side="left", padx=(0, 2))
        self.cb_periode = ttk.Combobox(ligne, font=("Helvetica", 10), width=14,
                                       style="App.TCombobox", state="readonly",
                                       values=["Toutes", "Trimestre 1", "Trimestre 2",
                                               "Trimestre 3", "Semestre 1", "Semestre 2",
                                               "Annuel"])
        self.cb_periode.set("Toutes")
        self.cb_periode.pack(side="left", padx=(0, 10))

        lbl("Élève :").pack(side="left", padx=(0, 2))
        self.var_search = tk.StringVar()
        e_search = tk.Entry(ligne, textvariable=self.var_search,
                            bg=HEADER, fg=TEXT, insertbackground=ACCENT,
                            font=("Helvetica", 10), width=16, relief=tk.SUNKEN)
        e_search.pack(side="left", padx=(0, 10))

        btn(ligne, "🔄 Actualiser", self.charger, G_BLUE, width=12).pack(side="left", padx=4)
        btn(ligne, "🧹 Réinitialiser", self._reinit_filtres, MUTED, width=13).pack(side="left", padx=4)

        self.lbl_count = tk.Label(flt, text="",
                                  bg=CARD, fg=MUTED, font=("Helvetica", 9, "italic"))
        self.lbl_count.pack(anchor="w", padx=10, pady=(0, 4))

        # ── Onglets Notes courantes / Historique modifications ────────
        nb = ttk.Notebook(self, style="App.TNotebook")
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        # Tab 1 : Notes actuelles
        self.tab_notes = tk.Frame(nb, bg=BG)
        nb.add(self.tab_notes, text="  📋  Notes Actuelles  ")
        self._build_tab_notes(self.tab_notes)

        # Tab 2 : Journal des modifications
        self.tab_histo = tk.Frame(nb, bg=BG)
        nb.add(self.tab_histo, text="  🕑  Journal des Modifications  ")
        self._build_tab_histo(self.tab_histo)

    # ── Onglet Notes actuelles ────────────────────────────────────────

    def _build_tab_notes(self, parent):
        cols  = ("id", "eleve", "classe", "matiere", "periode",
                 "nom_eval", "type_eval", "note", "coeff", "prof", "date_eval", "date_saisie")
        heads = ("ID", "Élève", "Classe", "Matière", "Période",
                 "Nom Évaluation", "Type", "Note", "Coeff.", "Professeur", "Date Éval.", "Date Saisie")
        self.tree_notes = make_treeview(parent, cols, heads, hauteur=18)
        self.tree_notes.column("id",         width=40,  anchor="center")
        self.tree_notes.column("eleve",      width=160, anchor="w")
        self.tree_notes.column("classe",     width=80,  anchor="center")
        self.tree_notes.column("matiere",    width=120, anchor="w")
        self.tree_notes.column("periode",    width=90,  anchor="center")
        self.tree_notes.column("nom_eval",   width=160, anchor="w")
        self.tree_notes.column("type_eval",  width=90,  anchor="center")
        self.tree_notes.column("note",       width=65,  anchor="center")
        self.tree_notes.column("coeff",      width=50,  anchor="center")
        self.tree_notes.column("prof",       width=140, anchor="w")
        self.tree_notes.column("date_eval",  width=90,  anchor="center")
        self.tree_notes.column("date_saisie",width=120, anchor="center")

        self.tree_notes.tag_configure("devoir",      foreground=G_BLUE)
        self.tree_notes.tag_configure("composition", foreground=G_ORANGE)

        self.tree_notes.tag_configure("bien",    foreground=G_GREEN)
        self.tree_notes.tag_configure("moyen",   foreground=G_ORANGE)
        self.tree_notes.tag_configure("mauvais", foreground=G_RED)
        self.tree_notes.tag_configure("special", foreground=G_PURPLE)

        self.tree_notes.bind("<Double-Button-1>", self._modifier_note_dialog)
        self.tree_notes.bind("<<TreeviewSelect>>", self._on_notes_sel)

        # Barre boutons
        bb = tk.Frame(parent, bg=BG)
        bb.pack(fill="x", padx=6, pady=4)
        btn(bb, "✏️ Modifier la sélection",
            self._modifier_note_dialog, G_BLUE, width=22).pack(side="left", padx=4)
        btn(bb, "🗑️ Supprimer la sélection",
            self._supprimer_note, G_RED, width=22).pack(side="left", padx=4)
        btn(bb, "☑ Tout sélectionner",
            lambda: self.tree_notes.selection_set(self.tree_notes.get_children()),
            MUTED, width=18).pack(side="left", padx=4)
        btn(bb, "☐ Désélectionner",
            lambda: self.tree_notes.selection_remove(self.tree_notes.get_children()),
            MUTED, width=14).pack(side="left", padx=4)
        self.lbl_sel_notes = tk.Label(bb, text="", bg=BG, fg=G_ORANGE,
                                       font=("Helvetica", 9, "italic"))
        self.lbl_sel_notes.pack(side="left", padx=8)
        btn(bb, "📥 Exporter CSV",
            self._exporter_csv_notes, G_GREEN, width=14).pack(side="right", padx=4)

    # ── Onglet Historique des modifications ───────────────────────────

    def _build_tab_histo(self, parent):
        cols  = ("id", "eleve", "matiere", "periode", "ancienne_val",
                 "nouvelle_val", "prof", "date_modif")
        heads = ("ID", "Élève", "Matière", "Période", "Ancienne Note",
                 "Nouvelle Note", "Modifié par", "Date Modification")
        self.tree_histo = make_treeview(parent, cols, heads, hauteur=18,
                                          selectmode="extended")
        self.tree_histo.column("id",           width=45,  anchor="center")
        self.tree_histo.column("eleve",        width=180, anchor="w")
        self.tree_histo.column("matiere",      width=130, anchor="w")
        self.tree_histo.column("periode",      width=100, anchor="center")
        self.tree_histo.column("ancienne_val", width=110, anchor="center")
        self.tree_histo.column("nouvelle_val", width=110, anchor="center")
        self.tree_histo.column("prof",         width=160, anchor="w")
        self.tree_histo.column("date_modif",   width=150, anchor="center")

        self.tree_histo.tag_configure("hausse", foreground=G_GREEN)
        self.tree_histo.tag_configure("baisse", foreground=G_RED)
        self.tree_histo.tag_configure("neutre", foreground=MUTED)
        self.tree_histo.bind("<<TreeviewSelect>>", self._on_histo_sel)

        bb2 = tk.Frame(parent, bg=BG)
        bb2.pack(fill="x", padx=6, pady=4)
        btn(bb2, "📥 CSV",
            self._exporter_csv_histo, G_GREEN, width=8).pack(side="left", padx=4)
        btn(bb2, "☑ Tout",
            lambda: self.tree_histo.selection_set(self.tree_histo.get_children()),
            MUTED, width=8).pack(side="left", padx=2)
        btn(bb2, "☐ Aucun",
            lambda: self.tree_histo.selection_remove(self.tree_histo.get_children()),
            MUTED, width=8).pack(side="left", padx=2)
        btn(bb2, "🗑️ Supprimer sélection",
            self._supprimer_histo_selection, G_ORANGE, width=20).pack(side="left", padx=4)
        btn(bb2, "💣 Vider tout",
            self._vider_historique, G_RED, width=14).pack(side="left", padx=4)
        self.lbl_sel_histo = tk.Label(bb2, text="", bg=BG, fg=G_ORANGE,
                                       font=("Helvetica", 9, "italic"))
        self.lbl_sel_histo.pack(side="left", padx=8)
        self.lbl_taille_histo = tk.Label(bb2, text="", bg=BG, fg=MUTED,
                                          font=("Helvetica", 8, "italic"))
        self.lbl_taille_histo.pack(side="right", padx=8)

    # ═══════════════════════════════════════════════════════════════
    # CHARGEMENTS
    # ═══════════════════════════════════════════════════════════════

    def _charger_filtres(self, *a):
        from database import Session, Classe, Matiere
        s = Session()
        classes  = s.query(Classe).order_by(Classe.nom).all()
        matieres = s.query(Matiere).order_by(Matiere.nom).all()
        s.close()

        self._classes_dict = {"Toutes": None, **{c.nom: c.id for c in classes}}
        self.cb_classe["values"] = list(self._classes_dict.keys())
        if not self.cb_classe.get():
            self.cb_classe.set("Toutes")

        self._matieres_dict = {"Toutes": None, **{m.nom: m.id for m in matieres}}
        self.cb_matiere["values"] = list(self._matieres_dict.keys())
        if not self.cb_matiere.get():
            self.cb_matiere.set("Toutes")

        self.charger()

    def _on_classe_filtre(self):
        """Quand on filtre par classe, mettre à jour les matières disponibles."""
        classe_id = self._classes_dict.get(self.cb_classe.get())
        if classe_id:
            from database import Session, MatiereClasse, Matiere
            from sqlalchemy.orm import joinedload
            s = Session()
            mcs = s.query(MatiereClasse).options(
                joinedload(MatiereClasse.matiere_obj)).filter_by(classe_id=classe_id).all()
            mats = [mc.matiere_obj for mc in mcs if mc.matiere_obj]
            s.close()
            self._matieres_dict = {"Toutes": None, **{m.nom: m.id for m in mats}}
        else:
            from database import Session, Matiere
            s = Session()
            mats = s.query(Matiere).order_by(Matiere.nom).all()
            s.close()
            self._matieres_dict = {"Toutes": None, **{m.nom: m.id for m in mats}}

        self.cb_matiere["values"] = list(self._matieres_dict.keys())
        self.cb_matiere.set("Toutes")
        self.charger()

    def _reinit_filtres(self):
        self.cb_classe.set("Toutes")
        self.cb_matiere.set("Toutes")
        self.cb_periode.set("Toutes")
        self.var_search.set("")
        self._charger_filtres()

    def charger(self, *a):
        self._charger_notes()
        self._charger_historique()

    def _charger_notes(self):
        from database import Session, Note, Evaluation, Eleve, Matiere, Classe, Professeur

        # Filtres UI
        classe_id   = self._classes_dict.get(self.cb_classe.get())
        matiere_id  = self._matieres_dict.get(self.cb_matiere.get())
        periode_nom = self.cb_periode.get()
        periode_key = {
            "Trimestre 1": "T1", "Trimestre 2": "T2", "Trimestre 3": "T3",
            "Semestre 1": "S1",  "Semestre 2": "S2",  "Annuel": "Annuel",
        }.get(periode_nom)
        search = self.var_search.get().strip().lower()

        s = Session()
        rows = []
        try:
            # Requête SQL directe avec JOIN explicites — pas de joinedload
            # pour éviter le bug SQLAlchemy DISTINCT qui masque les compositions
            q = (s.query(
                     Note.id,
                     Note.valeur,
                     Note.date_enregistrement,
                     Eleve.nom.label("e_nom"),
                     Eleve.prenom.label("e_prenom"),
                     Classe.nom.label("c_nom"),
                     Matiere.nom.label("m_nom"),
                     Evaluation.nom.label("ev_nom"),
                     Evaluation.type_evaluation,
                     Evaluation.coefficient,
                     Evaluation.periode,
                     Evaluation.date_evaluation,
                     Professeur.nom.label("p_nom"),
                     Professeur.prenom.label("p_prenom"),
                 )
                 .join(Evaluation, Note.evaluation_id == Evaluation.id)
                 .join(Eleve,      Note.eleve_id      == Eleve.id)
                 .outerjoin(Classe,      Eleve.classe_id      == Classe.id)
                 .outerjoin(Matiere,     Note.matiere_id      == Matiere.id)
                 .outerjoin(Professeur,  Note.professeur_id   == Professeur.id)
            )

            # Filtres
            if matiere_id:
                q = q.filter(Note.matiere_id == matiere_id)
            if classe_id:
                q = q.filter(Eleve.classe_id == classe_id)
            if periode_key:
                q = q.filter(Evaluation.periode == periode_key)

            resultats = q.order_by(Note.date_enregistrement.desc()).all()

            for r in resultats:
                eleve_nom  = f"{r.e_nom} {r.e_prenom}" if r.e_nom else "?"
                classe_nom = r.c_nom or "—"
                mat_nom    = r.m_nom or "?"
                periode    = KEY_TO_PERIODE.get(r.periode, r.periode or "—")
                nom_eval   = r.ev_nom or "—"
                type_eval  = r.type_evaluation or "—"
                coeff      = str(r.coefficient) if r.coefficient else "—"
                date_eval  = r.date_evaluation or "—"
                prof_nom   = (f"{r.p_nom} {r.p_prenom}"
                              if r.p_nom else "—")
                date_s     = (r.date_enregistrement.strftime("%d/%m/%Y %H:%M")
                              if r.date_enregistrement else "—")
                rows.append({
                    "note_id":   r.id,
                    "eleve_nom": eleve_nom,
                    "classe":    classe_nom,
                    "matiere":   mat_nom,
                    "periode":   periode,
                    "nom_eval":  nom_eval,
                    "type_eval": type_eval,
                    "valeur":    r.valeur,
                    "coeff":     coeff,
                    "prof":      prof_nom,
                    "date_eval": date_eval,
                    "date_s":    date_s,
                })
        finally:
            s.close()

        # Filtre texte élève
        if search:
            rows = [r for r in rows if search in r["eleve_nom"].lower()]

        self._data_rows = rows

        # Remplir le tableau
        self.tree_notes.delete(*self.tree_notes.get_children())
        for i, r in enumerate(rows):
            tag_alt = "odd" if i % 2 == 0 else "even"
            tag_note = self._tag_note(r["valeur"])
            # Tag couleur selon type devoir/composition
            te = (r["type_eval"] or "").lower()
            if any(k in te for k in ("devoir","dev","interro","tp","controle")):
                tag_type = "devoir"
            elif any(k in te for k in ("compo","composition","exam","examen")):
                tag_type = "composition"
            else:
                tag_type = tag_alt
            self.tree_notes.insert("", "end", iid=str(r["note_id"]),
                                   values=(r["note_id"], r["eleve_nom"], r["classe"],
                                           r["matiere"], r["periode"], r["nom_eval"],
                                           r["type_eval"], r["valeur"], r["coeff"],
                                           r["prof"], r["date_eval"], r["date_s"]),
                                   tags=(tag_type, tag_note))

        self.lbl_count.config(
            text=f"📊 {len(rows)} note(s) affichée(s)")

    def _charger_historique(self):
        from database import Session, HistoriqueNote, Note, Eleve, Matiere, Evaluation, Professeur
        from sqlalchemy.orm import joinedload

        s = Session()
        try:
            classe_id  = self._classes_dict.get(self.cb_classe.get())
            matiere_id = self._matieres_dict.get(self.cb_matiere.get())
            search     = self.var_search.get().strip().lower()

            q = (s.query(HistoriqueNote)
                 .options(
                     joinedload(HistoriqueNote.eleve),
                     joinedload(HistoriqueNote.matiere_obj),
                     joinedload(HistoriqueNote.evaluation_obj),
                     joinedload(HistoriqueNote.professeur_obj),
                     joinedload(HistoriqueNote.note_obj),
                 ))

            if matiere_id:
                q = q.filter(HistoriqueNote.matiere_id == matiere_id)
            if classe_id:
                q = q.join(HistoriqueNote.eleve).filter(Eleve.classe_id == classe_id)

            historiques = q.order_by(HistoriqueNote.date_modification.desc()).all()

            rows_h = []
            for h in historiques:
                eleve_nom = f"{h.eleve.nom} {h.eleve.prenom}" if h.eleve else "?"
                mat_nom   = h.matiere_obj.nom if h.matiere_obj else "?"
                ev        = h.evaluation_obj
                periode   = KEY_TO_PERIODE.get(ev.periode, ev.periode) if ev else "—"
                prof_nom  = (f"{h.professeur_obj.nom} {h.professeur_obj.prenom}"
                             if h.professeur_obj else "Système")
                date_m    = (h.date_modification.strftime("%d/%m/%Y %H:%M")
                             if h.date_modification else "—")
                nouvelle_val = h.note_obj.valeur if h.note_obj else "Supprimée"

                rows_h.append({
                    "id":           h.id,
                    "eleve_nom":    eleve_nom,
                    "matiere":      mat_nom,
                    "periode":      periode,
                    "ancienne":     h.ancienne_valeur,
                    "nouvelle":     nouvelle_val,
                    "prof":         prof_nom,
                    "date_m":       date_m,
                })

        finally:
            s.close()

        if search:
            rows_h = [r for r in rows_h if search in r["eleve_nom"].lower()]

        self.tree_histo.delete(*self.tree_histo.get_children())
        for i, r in enumerate(rows_h):
            tag_alt = "odd" if i % 2 == 0 else "even"
            # Comparer ancienne vs nouvelle pour tag couleur
            try:
                a = float(r["ancienne"])
                n = float(r["nouvelle"])
                tag_c = "hausse" if n > a else ("baisse" if n < a else "neutre")
            except Exception:
                tag_c = "neutre"

            self.tree_histo.insert("", "end", iid=str(r["id"]),
                                   values=(r["id"], r["eleve_nom"], r["matiere"],
                                           r["periode"], r["ancienne"], r["nouvelle"],
                                           r["prof"], r["date_m"]),
                                   tags=(tag_alt, tag_c))
        self._maj_taille_histo()

    def _maj_taille_histo(self):
        """Affiche le nombre total d'entrées dans l'historique."""
        try:
            from database import Session, HistoriqueNote
            s = Session()
            nb = s.query(HistoriqueNote).count()
            s.close()
            if hasattr(self, "lbl_taille_histo"):
                self.lbl_taille_histo.config(
                    text=f"📋 {nb} entrée(s) au total")
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════
    # MODIFICATION NOTE
    # ═══════════════════════════════════════════════════════════════

    def _modifier_note_dialog(self, event=None):
        sel = self.tree_notes.selection()
        if not sel:
            messagebox.showwarning("Attention", "Sélectionnez une note à modifier.")
            return

        note_id = int(sel[0])
        row = next((r for r in self._data_rows if r["note_id"] == note_id), None)
        if not row:
            return

        # ── Fenêtre de modification ───────────────────────────────────
        win = tk.Toplevel(self)
        win.title(f"Modifier la note — {row['eleve_nom']}")
        win.configure(bg=BG)
        win.resizable(False, False)

        # Centrer
        win.update_idletasks()
        w, h = 420, 320
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.update()      # rendre la fenêtre visible AVANT grab_set()
        win.grab_set()    # modal

        # Titre
        tk.Label(win, text="✏️  Modifier la Note",
                 bg=BG, fg=ACCENT, font=("Helvetica", 13, "bold")).pack(pady=(14, 4))

        # Infos
        info = tk.Frame(win, bg=CARD, relief=tk.GROOVE, bd=2)
        info.pack(fill="x", padx=16, pady=6)

        def info_ligne(label, valeur):
            f = tk.Frame(info, bg=CARD)
            f.pack(fill="x", padx=10, pady=2)
            tk.Label(f, text=label, bg=CARD, fg=MUTED,
                     font=("Helvetica", 9, "bold"), width=12, anchor="w").pack(side="left")
            tk.Label(f, text=valeur, bg=CARD, fg=TEXT,
                     font=("Helvetica", 10), anchor="w").pack(side="left")

        info_ligne("Élève :",   row["eleve_nom"])
        info_ligne("Matière :", row["matiere"])
        info_ligne("Période :", row["periode"])
        info_ligne("Type :",    row["type_eval"])

        # Note actuelle
        note_f = tk.Frame(win, bg=BG)
        note_f.pack(pady=10)

        tk.Label(note_f, text=f"Note actuelle :  ",
                 bg=BG, fg=MUTED, font=("Helvetica", 11)).pack(side="left")
        tk.Label(note_f, text=row["valeur"],
                 bg=BG, fg=G_ORANGE, font=("Helvetica", 14, "bold")).pack(side="left")

        # Nouvelle note
        saisie_f = tk.Frame(win, bg=BG)
        saisie_f.pack(pady=6)
        tk.Label(saisie_f, text="Nouvelle note :",
                 bg=BG, fg=TEXT, font=("Helvetica", 11, "bold")).pack(side="left", padx=(0, 10))
        e_note = tk.Entry(saisie_f, width=10, bg=HEADER, fg=TEXT,
                          insertbackground=ACCENT,
                          font=("Helvetica", 14, "bold"),
                          justify="center", relief=tk.SUNKEN, bd=3)
        e_note.pack(side="left")
        e_note.insert(0, row["valeur"])
        e_note.select_range(0, tk.END)
        e_note.focus_set()

        tk.Label(win, text="(0–20  |  ABS = absent  |  DISP = dispensé)",
                 bg=BG, fg=MUTED, font=("Helvetica", 8, "italic")).pack()

        lbl_err = tk.Label(win, text="", bg=BG, fg=G_RED,
                           font=("Helvetica", 9, "bold"))
        lbl_err.pack()

        def valider():
            val = e_note.get().strip().upper()
            if val not in ("ABS", "DISP"):
                try:
                    v = float(val.replace(",", "."))
                    if not 0 <= v <= 20:
                        raise ValueError
                    val = str(round(v, 2))
                except ValueError:
                    lbl_err.config(text="❌ Note invalide (0–20, ABS ou DISP)")
                    return

            if val == row["valeur"]:
                win.destroy()
                return

            try:
                from database import Session, Note, HistoriqueNote
                s = Session()
                n = s.get(Note, note_id)
                if n:
                    # Enregistrer dans l'historique
                    s.add(HistoriqueNote(
                        ancienne_valeur=n.valeur,
                        note_id=n.id,
                        eleve_id=n.eleve_id,
                        matiere_id=n.matiere_id,
                        evaluation_id=n.evaluation_id,
                        professeur_id=n.professeur_id,
                    ))
                    n.valeur = val
                    s.commit()
                s.close()
                win.destroy()
                popup_info("Succès", f"Note modifiée : {row['valeur']} → {val} ✅")
                db_signals.notes_updated.emit()
            except Exception as e:
                messagebox.showerror("Erreur BDD", str(e))

        # Boutons
        bb = tk.Frame(win, bg=BG)
        bb.pack(pady=8)
        btn(bb, "✅ Enregistrer", valider, G_GREEN, width=16).pack(side="left", padx=6)
        btn(bb, "✖ Annuler", win.destroy, MUTED, width=12).pack(side="left", padx=6)
        e_note.bind("<Return>",   lambda e: valider())
        e_note.bind("<KP_Enter>", lambda e: valider())
        e_note.bind("<Escape>",   lambda e: win.destroy())

    # ═══════════════════════════════════════════════════════════════
    # SUPPRESSION NOTE
    # ═══════════════════════════════════════════════════════════════

    def _on_notes_sel(self, event=None):
        nb = len(self.tree_notes.selection())
        if hasattr(self, "lbl_sel_notes"):
            if nb > 0:
                self.lbl_sel_notes.config(text=f"{nb} note(s) sélectionnée(s)")
            else:
                self.lbl_sel_notes.config(text="")

    def _supprimer_note(self):
        sel = self.tree_notes.selection()
        if not sel:
            messagebox.showwarning("Attention", "Sélectionnez une ou plusieurs notes.")
            return

        nb = len(sel)
        if nb == 1:
            note_id = int(sel[0])
            row = next((r for r in self._data_rows if r["note_id"] == note_id), None)
            msg = (f"Supprimer la note de {row['eleve_nom']} ?\n"
                   f"Matière : {row['matiere']} — Note : {row['valeur']}"
                   if row else f"Supprimer la note #{note_id} ?")
        else:
            msg = f"Supprimer {nb} note(s) sélectionnée(s) ?\nCette action est irréversible."

        if not popup_confirmation("Supprimer les notes", msg + "\n\nCette action est irréversible."):
            return

        try:
            from database import Session, Note
            s = Session()
            nb_ok = 0
            for iid in sel:
                n = s.get(Note, int(iid))
                if n:
                    s.delete(n)
                    nb_ok += 1
            s.commit(); s.close()
            popup_info("Supprimé", f"✅  {nb_ok} note(s) supprimée(s)")
            db_signals.notes_updated.emit()
        except Exception as e:
            messagebox.showerror("Erreur BDD", str(e))

    # ═══════════════════════════════════════════════════════════════
    # HISTORIQUE
    # ═══════════════════════════════════════════════════════════════

    def _on_histo_sel(self, event=None):
        nb = len(self.tree_histo.selection())
        if hasattr(self, "lbl_sel_histo"):
            self.lbl_sel_histo.config(
                text=f"{nb} ligne(s) sélectionnée(s)" if nb else "")

    def _supprimer_histo_selection(self):
        """Supprime uniquement les lignes sélectionnées dans l'historique."""
        sel = self.tree_histo.selection()
        if not sel:
            messagebox.showwarning("Attention",
                "Sélectionnez des lignes à supprimer.\n"
                "Utilisez Ctrl+clic pour sélectionner plusieurs lignes.")
            return
        nb = len(sel)
        if not popup_confirmation("Supprimer la sélection",
                f"Supprimer {nb} ligne(s) de l'historique ?\n"
                "Cette action est irréversible."):
            return
        try:
            from database import Session, HistoriqueNote
            s = Session()
            nb_ok = 0
            for iid in sel:
                vals = self.tree_histo.item(iid)["values"]
                hid = int(vals[0])   # colonne id
                h = s.get(HistoriqueNote, hid)
                if h:
                    s.delete(h)
                    nb_ok += 1
            s.commit(); s.close()
            for iid in sel:
                self.tree_histo.delete(iid)
            if hasattr(self, "lbl_sel_histo"):
                self.lbl_sel_histo.config(text="")
            popup_info("Succès", f"✅ {nb_ok} ligne(s) supprimée(s)")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _vider_historique(self):
        """Vide tout l'historique avec option par période."""
        from tkinter import simpledialog

        # Proposer de vider par période ou tout vider
        win = tk.Toplevel(self)
        win.title("🗑️ Vider l'historique")
        win.configure(bg="#0F172A")
        win.resizable(False, False)
        win.grab_set()
        w, h = 420, 280
        win.geometry(f"{w}x{h}+{self.winfo_rootx()+(self.winfo_width()-w)//2}"
                     f"+{self.winfo_rooty()+(self.winfo_height()-h)//2}")

        tk.Label(win, text="🗑️  Vider l'historique des modifications",
                 bg="#0F172A", fg="#E2E8F0",
                 font=("Helvetica", 12, "bold")).pack(pady=(20, 6))
        tk.Label(win, text="Choisissez ce que vous souhaitez supprimer :",
                 bg="#0F172A", fg="#94A3B8",
                 font=("Helvetica", 10)).pack(pady=(0, 16))

        def action(mode):
            win.destroy()
            try:
                from database import Session, HistoriqueNote
                s = Session()
                if mode == "tout":
                    if not popup_confirmation("Confirmer",
                            "Supprimer TOUT l'historique ?\nCette action est irréversible."):
                        s.close(); return
                    s.query(HistoriqueNote).delete()
                    msg = "Tout l'historique a été supprimé ✅"
                elif mode == "30":
                    from datetime import datetime, timedelta
                    limite = datetime.now() - timedelta(days=30)
                    nb = s.query(HistoriqueNote).filter(
                        HistoriqueNote.date_modification <= limite).delete()
                    msg = f"✅ {nb} entrée(s) supprimée(s) (plus de 30 jours)"
                elif mode == "90":
                    from datetime import datetime, timedelta
                    limite = datetime.now() - timedelta(days=90)
                    nb = s.query(HistoriqueNote).filter(
                        HistoriqueNote.date_modification <= limite).delete()
                    msg = f"✅ {nb} entrée(s) supprimée(s) (plus de 90 jours)"
                s.commit(); s.close()
                self.tree_histo.delete(*self.tree_histo.get_children())
                self._charger_historique()
                popup_info("Succès", msg)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

        for label, mode, clr in [
            ("🗑️  Supprimer les entrées de plus de 30 jours", "30",  "#D97706"),
            ("🗑️  Supprimer les entrées de plus de 90 jours", "90",  "#D97706"),
            ("💣  Vider TOUT l'historique",                   "tout","#DC2626"),
        ]:
            tk.Button(win, text=label, command=lambda m=mode: action(m),
                      bg=clr, fg="white",
                      font=("Helvetica", 10, "bold"),
                      relief=tk.FLAT, cursor="hand2",
                      padx=14, pady=8).pack(fill="x", padx=28, pady=4)

        tk.Button(win, text="Annuler", command=win.destroy,
                  bg="#334155", fg="#E2E8F0",
                  font=("Helvetica", 10),
                  relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6).pack(pady=(4, 16))

    # ═══════════════════════════════════════════════════════════════
    # EXPORTS CSV
    # ═══════════════════════════════════════════════════════════════

    def _exporter_csv_notes(self):
        from tkinter import filedialog
        import csv
        if not self._data_rows:
            messagebox.showwarning("Vide", "Aucune note à exporter.")
            return
        f = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="historique_notes.csv")
        if not f:
            return
        with open(f, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["ID", "Élève", "Classe", "Matière", "Période",
                        "Type", "Note", "Coeff", "Prof", "Date Éval", "Date Saisie"])
            for r in self._data_rows:
                w.writerow([r["note_id"], r["eleve_nom"], r["classe"], r["matiere"],
                            r["periode"], r["type_eval"], r["valeur"], r["coeff"],
                            r["prof"], r["date_eval"], r["date_s"]])
        popup_info("Export", f"Exporté :\n{f}")

    def _exporter_csv_histo(self):
        from tkinter import filedialog
        import csv
        items = self.tree_histo.get_children()
        if not items:
            messagebox.showwarning("Vide", "Aucun historique à exporter.")
            return
        f = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="journal_modifications.csv")
        if not f:
            return
        with open(f, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["ID", "Élève", "Matière", "Période",
                        "Ancienne Note", "Nouvelle Note", "Modifié par", "Date"])
            for iid in items:
                w.writerow(self.tree_histo.item(iid)["values"])
        popup_info("Export", f"Exporté :\n{f}")

    # ═══════════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════════

    def _tag_note(self, val):
        v = (val or "").strip().upper()
        if v in ("ABS", "DISP"): return "special"
        try:
            n = float(v)
            return "bien" if n >= 14 else ("moyen" if n >= 10 else "mauvais")
        except Exception:
            return "neutre"

    def rafraichir(self):
        self._charger_filtres()
