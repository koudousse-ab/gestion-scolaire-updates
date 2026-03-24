# support_chat.py — Chat support client ↔ éditeur

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, json, time
import urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

BG    = "#0F172A"
CARD  = "#1E293B"
CB    = "#2563EB"
GREEN = "#16A34A"
TEXT  = "#E2E8F0"
MUTED = "#94A3B8"
GOLD  = "#C8A951"
BDR   = "#334155"
MINE  = "#1D4ED8"   # bulle client
THEIR = "#166534"   # bulle support

SERVER_URL_FILE = Path(__file__).parent / "server_url.txt"

def _server_url():
    if SERVER_URL_FILE.exists():
        return SERVER_URL_FILE.read_text().strip().rstrip("/")
    return "http://localhost:5000"

def _machine_id():
    try:
        from licence_manager import get_machine_id
        return get_machine_id()
    except Exception:
        return "UNKNOWN"

def _get_licence_infos():
    try:
        from licence_manager import get_infos_licence
        return get_infos_licence()
    except Exception:
        return {}


class SupportChat(tk.Toplevel):

    def __init__(self, master):
        super().__init__(master)
        self.title("💬  Support — Gestion Scolaire")
        self.configure(bg=BG)
        self.resizable(True, True)

        w, h = 520, 580
        px = master.winfo_rootx() + (master.winfo_width()  - w) // 2
        py = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{px}+{py}")
        self.minsize(400, 400)

        self._mid       = _machine_id()
        self._infos     = _get_licence_infos()
        self._messages  = []
        self._running   = True
        self._last_id   = 0

        self._build()
        self._charger_messages()
        self._start_polling()

    # ─── UI ──────────────────────────────────────────────────

    def _build(self):
        # Titre
        header = tk.Frame(self, bg="#1A3A5C")
        header.pack(fill="x")
        tk.Label(header, text="💬  Support Technique",
                 bg="#1A3A5C", fg=GOLD,
                 font=("Helvetica", 12, "bold")).pack(side="left", padx=14, pady=10)
        self._lbl_statut = tk.Label(header, text="● Connexion...",
                                     bg="#1A3A5C", fg=MUTED,
                                     font=("Helvetica", 9))
        self._lbl_statut.pack(side="right", padx=14)

        # Info établissement
        etab = self._infos.get("etablissement","") or "Non activé"
        tk.Label(self, text=f"🏫  {etab}  —  ID : {self._mid[:12]}...",
                 bg=CARD, fg=MUTED,
                 font=("Helvetica", 8)).pack(fill="x", padx=0)

        # Zone messages
        msg_frame = tk.Frame(self, bg=BG)
        msg_frame.pack(fill="both", expand=True, padx=10, pady=8)

        vsb = ttk.Scrollbar(msg_frame, orient="vertical",
                             style="App.Vertical.TScrollbar")
        vsb.pack(side="right", fill="y")

        self.canvas = tk.Canvas(msg_frame, bg=BG, bd=0,
                                 highlightthickness=0,
                                 yscrollcommand=vsb.set)
        self.canvas.pack(fill="both", expand=True)
        vsb.config(command=self.canvas.yview)

        self._msg_inner = tk.Frame(self.canvas, bg=BG)
        self._win_id = self.canvas.create_window(
            (0,0), window=self._msg_inner, anchor="nw")
        self._msg_inner.bind("<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self._win_id, width=e.width))

        # Message vide
        self._lbl_vide = tk.Label(self._msg_inner,
                                   text="Aucun message pour l'instant.\n"
                                        "Écrivez votre question ci-dessous 👇",
                                   bg=BG, fg=MUTED,
                                   font=("Helvetica", 10, "italic"),
                                   justify="center")
        self._lbl_vide.pack(pady=40)

        # Zone saisie
        saisie = tk.Frame(self, bg=CARD)
        saisie.pack(fill="x", padx=10, pady=(0,10))

        self.e_msg = tk.Text(saisie, height=3,
                              bg=BDR, fg=TEXT,
                              insertbackground=CB,
                              font=("Helvetica", 10),
                              relief=tk.FLAT, bd=0,
                              wrap=tk.WORD)
        self.e_msg.pack(side="left", fill="x", expand=True,
                         padx=(8,6), pady=8, ipady=4)
        self.e_msg.bind("<Return>",    self._on_enter)
        self.e_msg.bind("<Shift-Return>", lambda e: None)

        btn_send = tk.Button(saisie, text="📤",
                              command=self._envoyer,
                              bg=CB, fg="white",
                              font=("Helvetica", 14),
                              relief=tk.FLAT, cursor="hand2",
                              padx=10, pady=6)
        btn_send.pack(side="right", padx=(0,8), pady=8)

        tk.Label(self, text="Entrée = envoyer  ·  Shift+Entrée = nouvelle ligne",
                 bg=BG, fg=MUTED,
                 font=("Helvetica", 7, "italic")).pack(pady=(0,6))

    # ─── Messages ────────────────────────────────────────────

    def _ajouter_bulle(self, texte, auteur, date_str, is_mine):
        """Ajoute une bulle de message dans le canvas."""
        if self._lbl_vide.winfo_exists():
            self._lbl_vide.destroy()

        align  = "e" if is_mine else "w"
        bg_bul = MINE if is_mine else THEIR
        nom    = "Vous" if is_mine else "Support"
        anc    = "ne" if not is_mine else "nw"

        outer = tk.Frame(self._msg_inner, bg=BG)
        outer.pack(fill="x", pady=3, padx=8)

        # Nom + date
        info_lbl = tk.Label(outer,
                             text=f"{nom}  {date_str[:16]}",
                             bg=BG, fg=MUTED,
                             font=("Helvetica", 7, "italic"))
        info_lbl.pack(anchor=align)

        # Bulle
        bulle = tk.Frame(outer, bg=bg_bul)
        bulle.pack(anchor=align)
        tk.Label(bulle, text=texte, bg=bg_bul, fg="white",
                 font=("Helvetica", 10),
                 wraplength=340, justify="left",
                 padx=12, pady=8).pack()

    def _scroll_bas(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    # ─── API ─────────────────────────────────────────────────

    def _envoyer(self):
        texte = self.e_msg.get("1.0", tk.END).strip()
        if not texte: return
        self.e_msg.delete("1.0", tk.END)

        def _send():
            try:
                # Lire la clé de licence pour authentifier le message
                try:
                    from pathlib import Path
                    _lk = (Path(__file__).parent / "licence.key")
                    _cle = _lk.read_text().strip() if _lk.exists() else ""
                except Exception:
                    _cle = ""
                payload = json.dumps({
                    "machine_id":    self._mid,
                    "licence_key":   _cle,          # authentification
                    "etablissement": self._infos.get("etablissement",""),
                    "ville":         self._infos.get("ville",""),
                    "texte":         texte,
                    "direction":     "client_vers_support",
                }).encode()
                req = urllib.request.Request(
                    f"{_server_url()}/api/chat/envoyer",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                urllib.request.urlopen(req, timeout=8)
                now = datetime.now().isoformat()
                self.after(0, lambda: [
                    self._ajouter_bulle(texte, "vous", now, True),
                    self._scroll_bas()
                ])
            except Exception as e:
                self.after(0, lambda: self._lbl_statut.config(
                    text=f"❌ Erreur envoi", fg="#DC2626"))

        threading.Thread(target=_send, daemon=True).start()

    def _on_enter(self, event):
        if not event.state & 0x1:   # pas Shift
            self._envoyer()
            return "break"

    def _charger_messages(self):
        """Charge l'historique des messages depuis le serveur."""
        def _fetch():
            try:
                url = f"{_server_url()}/api/chat/historique?mid={self._mid}"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=8) as r:
                    msgs = json.loads(r.read().decode())
                self.after(0, lambda: self._afficher_historique(msgs))
                self.after(0, lambda: self._lbl_statut.config(
                    text="● Connecté", fg=GREEN))
            except Exception:
                self.after(0, lambda: self._lbl_statut.config(
                    text="● Hors ligne", fg=MUTED))
        threading.Thread(target=_fetch, daemon=True).start()

    def _afficher_historique(self, msgs):
        for m in reversed(msgs):
            is_mine = m.get("direction") == "client_vers_support"
            self._ajouter_bulle(m["texte"], m.get("auteur",""),
                                 m.get("date",""), is_mine)
            self._last_id = max(self._last_id, m.get("id", 0))
        self._scroll_bas()

    def _start_polling(self):
        """Vérifie les nouveaux messages toutes les 10 secondes."""
        def _poll():
            while self._running:
                time.sleep(10)
                try:
                    url = (f"{_server_url()}/api/chat/nouveaux"
                           f"?mid={self._mid}&depuis={self._last_id}")
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=6) as r:
                        msgs = json.loads(r.read().decode())
                    if msgs:
                        for m in msgs:
                            if m.get("direction") == "support_vers_client":
                                self._last_id = max(self._last_id, m.get("id",0))
                                txt = m["texte"]; d = m.get("date","")
                                self.after(0, lambda t=txt, dd=d: [
                                    self._ajouter_bulle(t,"support",dd,False),
                                    self._scroll_bas()
                                ])
                    self.after(0, lambda: self._lbl_statut.config(
                        text="● Connecté", fg=GREEN))
                except Exception:
                    self.after(0, lambda: self._lbl_statut.config(
                        text="● Hors ligne", fg=MUTED))
        threading.Thread(target=_poll, daemon=True).start()

    def destroy(self):
        self._running = False
        super().destroy()
