# widgets_communs.py — Thème sombre professionnel — Optimisé Secrétaire

import tkinter as tk
from tkinter import ttk

# ─── PALETTE SOMBRE PROFESSIONNELLE ─────────────────────────
BG        = "#0F172A"        # fond général bleu nuit
PANEL     = "#1E293B"        # panneaux sombres
CARD      = "#1E293B"        # cartes sombres
HEADER    = "#1E3A5F"        # bleu marine (entêtes)
ACCENT    = "#2563EB"        # bleu principal (actions)
ACCENT2   = "#F59E0B"        # ambre (titres sections)
TEXT      = "#E2E8F0"        # texte clair
MUTED     = "#94A3B8"        # texte secondaire gris clair
BORDER    = "#334155"        # bordures discrètes
G_GREEN   = "#16A34A"        # vert succès
G_RED     = "#DC2626"        # rouge erreur
G_BLUE    = "#2563EB"        # bleu actions
G_ORANGE  = "#D97706"        # orange avertissement
G_PURPLE  = "#7C3AED"        # violet rapports

# Couleurs complémentaires
C_BLUELIGHT  = "#1E3A5F"     # fond bleu foncé
C_GREENLIGHT = "#14532D"     # fond vert foncé
C_ORANGELIGHT= "#7C2D12"     # fond orange foncé
C_REDLIGHT   = "#FEF2F2"     # fond rouge très clair


def configurer_style_ttk():
    s = ttk.Style()
    s.theme_use("clam")

    # Treeview sombre
    s.configure("App.Treeview",
        background=PANEL, foreground=TEXT,
        fieldbackground=PANEL, rowheight=28,
        font=("Helvetica", 10),
        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    s.configure("App.Treeview.Heading",
        background=HEADER, foreground="white",
        font=("Helvetica", 10, "bold"),
        relief="flat", padding=(8, 6))
    s.map("App.Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", "white")])

    # Combobox sombre
    s.configure("App.TCombobox",
        background=PANEL, foreground=TEXT,
        fieldbackground=PANEL, selectbackground=ACCENT,
        arrowcolor="#93C5FD", bordercolor=BORDER,
        lightcolor=BORDER, darkcolor=BORDER)
    s.map("App.TCombobox",
        fieldbackground=[("readonly", PANEL)],
        foreground=[("readonly", TEXT)],
        selectbackground=[("readonly", ACCENT)])

    # Notebook sombre
    s.configure("App.TNotebook",
        background=BG, borderwidth=0, tabmargins=[4, 4, 0, 0])
    s.configure("App.TNotebook.Tab",
        background="#0F172A", foreground=MUTED,
        padding=[14, 7], font=("Helvetica", 10, "bold"),
        borderwidth=0)
    s.map("App.TNotebook.Tab",
        background=[("selected", HEADER)],
        foreground=[("selected", "#93C5FD")])

    # Scrollbars sombres
    s.configure("App.Vertical.TScrollbar",
        background=BORDER, troughcolor=BG,
        arrowcolor=MUTED, relief="flat", width=10)
    s.configure("App.Horizontal.TScrollbar",
        background=BORDER, troughcolor=BG,
        arrowcolor=MUTED, relief="flat", width=10)

    # Spinbox sombre
    s.configure("TSpinbox",
        background=PANEL, foreground=TEXT,
        fieldbackground=PANEL, bordercolor=BORDER)

    # Progressbar
    s.configure("App.Horizontal.TProgressbar",
        background=ACCENT, troughcolor=BORDER)


def make_treeview(parent, colonnes, entetes, hauteur=14, selectmode='browse'):
    frame = tk.Frame(parent, bg="#334155", relief=tk.FLAT, bd=1)
    frame.pack(fill="both", expand=True, padx=5, pady=4)

    tree = ttk.Treeview(frame, columns=colonnes, show="headings",
                        style="App.Treeview", height=hauteur,
                        selectmode=selectmode)
    for col, head in zip(colonnes, entetes):
        tree.heading(col, text=head)
        tree.column(col, width=110, anchor="center", minwidth=60)

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview,
                        style="App.Vertical.TScrollbar")
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview,
                        style="App.Horizontal.TScrollbar")
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    tree.pack(fill="both", expand=True)

    tree.tag_configure("odd",  background="#1E293B", foreground="#E2E8F0")
    tree.tag_configure("even", background="#0F172A", foreground="#E2E8F0")
    return tree


def alterner_couleurs(tree):
    for i, item in enumerate(tree.get_children()):
        tree.item(item, tags=("odd" if i % 2 == 0 else "even",))


def btn(parent, texte, commande, couleur=None, largeur=14, width=None):
    """Bouton clair professionnel — plus grand et lisible."""
    if couleur is None:
        couleur = G_BLUE
    taille = width if width is not None else largeur

    # Calculer couleur hover (légèrement plus foncée)
    b = tk.Button(parent, text=texte, command=commande,
                  bg=couleur, fg="white",
                  font=("Helvetica", 10, "bold"),
                  relief=tk.FLAT, bd=0, cursor="hand2",
                  activebackground=HEADER, activeforeground="white",
                  width=taille, pady=6, padx=8)

    def on_enter(e):
        b.config(relief=tk.GROOVE, bd=1)
    def on_leave(e):
        b.config(relief=tk.FLAT, bd=0)

    b.bind("<Enter>", on_enter)
    b.bind("<Leave>", on_leave)
    return b


def btn_icone(parent, texte, commande, couleur=None, taille=11):
    """Bouton compact avec icône pour barres d'outils."""
    if couleur is None:
        couleur = G_BLUE
    b = tk.Button(parent, text=texte, command=commande,
                  bg=couleur, fg="white",
                  font=("Helvetica", taille, "bold"),
                  relief=tk.FLAT, bd=0, cursor="hand2",
                  activebackground=HEADER, activeforeground="white",
                  padx=10, pady=5)
    b.bind("<Enter>", lambda e: b.config(relief=tk.GROOVE, bd=1))
    b.bind("<Leave>", lambda e: b.config(relief=tk.FLAT, bd=0))
    return b


def label_champ(parent, etiquette, ligne, colonne=0, largeur=22, width=None):
    """Label + Entry avec style clair."""
    taille = width if width is not None else largeur
    tk.Label(parent, text=etiquette, bg=CARD, fg=TEXT,
             font=("Helvetica", 10, "bold")).grid(
        row=ligne, column=colonne, sticky="w", padx=10, pady=5)
    e = tk.Entry(parent, width=taille, bg=BG, fg=TEXT,
                 insertbackground=ACCENT, relief=tk.SOLID, bd=1,
                 font=("Helvetica", 10),
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER)
    e.grid(row=ligne, column=colonne+1, padx=10, pady=5, sticky="ew")
    return e


def label_combo(parent, etiquette, valeurs, ligne, colonne=0, largeur=22, width=None):
    """Label + Combobox avec style clair."""
    taille = width if width is not None else largeur
    tk.Label(parent, text=etiquette, bg=CARD, fg=TEXT,
             font=("Helvetica", 10, "bold")).grid(
        row=ligne, column=colonne, sticky="w", padx=10, pady=5)
    cb = ttk.Combobox(parent, values=valeurs, font=("Helvetica", 10),
                      width=taille, style="App.TCombobox")
    cb.grid(row=ligne, column=colonne+1, padx=10, pady=5, sticky="ew")
    return cb


def entete_module(parent, titre, couleur=None):
    """Entête de module — bleu marine avec titre blanc."""
    if couleur is None:
        couleur = "white"
    h = tk.Frame(parent, bg=HEADER, relief=tk.FLAT)
    h.pack(fill="x", padx=0, pady=(0, 6))

    # Barre colorée à gauche
    accent_bar = tk.Frame(h, bg=ACCENT2, width=5)
    accent_bar.pack(side="left", fill="y")

    tk.Label(h, text=titre, bg=HEADER, fg=couleur,
             font=("Helvetica", 14, "bold")).pack(
        side="left", padx=16, pady=10)
    return h


def formulaire_group(parent, titre):
    """Groupe de formulaire — fond blanc, titre bleu."""
    f = tk.LabelFrame(parent,
                      text=f"  {titre}  ",
                      bg=CARD, fg=HEADER,
                      font=("Helvetica", 10, "bold"),
                      relief=tk.GROOVE, bd=2,
                      labelanchor="nw")
    f.pack(fill="x", padx=8, pady=4)
    return f


def barre_boutons(parent):
    b = tk.Frame(parent, bg=BG)
    b.pack(fill="x", padx=8, pady=4)
    return b


def barre_recherche(parent, var_texte, placeholder="Rechercher..."):
    f = tk.Frame(parent, bg=BG, pady=3)
    f.pack(fill="x", padx=8, pady=2)

    tk.Label(f, text="🔍", bg=BG, fg=MUTED,
             font=("Helvetica", 12)).pack(side="left", padx=(4, 2))
    tk.Label(f, text="Recherche :", bg=BG, fg=MUTED,
             font=("Helvetica", 10, "bold")).pack(side="left", padx=(0, 6))

    e = tk.Entry(f, textvariable=var_texte, bg=PANEL, fg=TEXT,
                 insertbackground=ACCENT, width=30,
                 relief=tk.SOLID, bd=1, font=("Helvetica", 10),
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER)
    e.pack(side="left", padx=4, pady=2)
    return f


def popup_info(titre, message):
    from tkinter import messagebox
    messagebox.showinfo(titre, message)

def popup_erreur(titre, message):
    from tkinter import messagebox
    messagebox.showerror(titre, message)

def popup_confirmation(titre, message):
    from tkinter import messagebox
    return messagebox.askyesno(titre, message)

def popup_avertissement(titre, message):
    from tkinter import messagebox
    messagebox.showwarning(titre, message)


# ── Utilitaires fenêtres ─────────────────────────────────────────

def centrer_fenetre(win, largeur=None, hauteur=None):
    """
    Centre une fenêtre sur l'écran de façon robuste.
    Fonctionne sur Linux, Windows et macOS avec DPI scaling.
    Si largeur/hauteur sont None, utilise les dimensions actuelles.
    """
    win.update_idletasks()   # forcer le calcul des dimensions

    # Résolution écran réelle
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()

    # Dimensions de la fenêtre
    w = largeur  or win.winfo_reqwidth()
    h = hauteur or win.winfo_reqheight()

    # Ne pas dépasser l'écran
    w = min(w, sw - 40)
    h = min(h, sh - 80)

    # Position centrée
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)

    win.geometry(f"{w}x{h}+{x}+{y}")
    return w, h

def centrer_sur_parent(win, parent, largeur, hauteur):
    """Centre une fenêtre fille sur son parent."""
    win.update_idletasks()
    parent.update_idletasks()

    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()

    w = min(largeur,  sw - 40)
    h = min(hauteur, sh - 80)

    # Position du parent
    try:
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
    except Exception:
        px, py, pw, ph = 0, 0, sw, sh

    x = max(0, min(px + (pw - w) // 2, sw - w))
    y = max(0, min(py + (ph - h) // 2, sh - h))

    win.geometry(f"{w}x{h}+{x}+{y}")
    return w, h
