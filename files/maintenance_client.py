# maintenance_client.py — Client de télémaintenance (corrigé)
import threading, time, json, sys, os, platform
import urllib.request, urllib.error
from pathlib import Path

# ── Dossier de données permanent (PyInstaller + Python normal) ──
if getattr(sys, "frozen", False):
    if sys.platform == "win32":
        _DATA = Path(os.environ.get("APPDATA","")) / "GestionScolaire"
    else:
        _DATA = Path.home() / ".local" / "share" / "GestionScolaire"
else:
    _DATA = Path(__file__).parent

_DATA.mkdir(parents=True, exist_ok=True)

# ── URL serveur ─────────────────────────────────────────────────
_url_file = _DATA / "server_url.txt"
SERVER_URL = (_url_file.read_text().strip()
              if _url_file.exists()
              else "https://areological-demonstratively-extreme.ngrok-free.app")

HEARTBEAT_INTERVAL = 120   # 2 minutes

# ── Référence à l'app Tkinter (remplie au démarrage) ───────────
_app_ref = None

# ── Helpers ─────────────────────────────────────────────────────
def _get_version():
    for f in [_DATA / "version.txt", Path(__file__).parent / "version.txt"]:
        if f.exists():
            return f.read_text().strip()
    return "2.0.0"

def _get_machine_id():
    try:
        from licence_manager import get_machine_id
        return get_machine_id()
    except Exception:
        return "UNKNOWN"

def _ui(fn):
    """Exécute fn() dans le thread Tkinter de façon sûre."""
    if _app_ref:
        try:
            _app_ref.after(0, fn)
        except Exception:
            pass

def _rapport(typ, msg):
    """Envoie un rapport au serveur (silencieux si hors ligne)."""
    try:
        payload = json.dumps({
            "machine_id": _get_machine_id(),
            "type": typ, "message": msg,
        }).encode()
        req = urllib.request.Request(
            f"{SERVER_URL}/api/rapport", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

# ── Heartbeat ────────────────────────────────────────────────────
def _send_heartbeat():
    """Ping le serveur, reçoit les commandes, synchronise les révocations."""
    # 1. Synchroniser la liste de révocation
    try:
        from licence_manager import synchroniser_revocation
        rev = synchroniser_revocation(SERVER_URL)
        if rev.get("revoquee"):
            def _bloquer():
                import tkinter.messagebox as mb
                mb.showerror("Licence révoquée",
                             "Votre licence a été révoquée.\n"
                             "Contactez votre revendeur.")
                if _app_ref:
                    _app_ref.quit()
            _ui(_bloquer)
            return []
    except Exception:
        pass

    # 2. Vérifier validité locale
    lic_valide = False
    try:
        from licence_manager import charger_et_verifier
        lic_valide = charger_et_verifier().get("valide", False)
    except Exception:
        pass

    # 3. Envoyer heartbeat
    try:
        payload = json.dumps({
            "machine_id":    _get_machine_id(),
            "version":       _get_version(),
            "os":            platform.system() + " " + platform.release(),
            "licence_valide": lic_valide,
        }).encode()
        req = urllib.request.Request(
            f"{SERVER_URL}/api/heartbeat", data=payload,
            headers={"Content-Type": "application/json",
                     "User-Agent": "GestionScolaire-Client/2.0"},
            method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return data.get("commandes", [])
    except Exception:
        return []

# ── Exécution des commandes reçues ───────────────────────────────
def _executer(cmd):
    action = cmd.get("action", "")
    param  = cmd.get("param", "")

    # ── Forcer mise à jour ──────────────────────────────────────
    if action == "forcer_maj":
        try:
            from updater import verifier_mise_a_jour_silencieuse, appliquer_mise_a_jour, redemarrer
            info = verifier_mise_a_jour_silencieuse()
            if info:
                ok = appliquer_mise_a_jour(info)
                if ok:
                    _ui(redemarrer)
        except Exception as e:
            _rapport("erreur", f"MAJ forcée : {e}")

    # ── Message popup ───────────────────────────────────────────
    elif action == "message" and param:
        def _show(p=param):
            import tkinter.messagebox as mb
            mb.showinfo("📢 Message administrateur", p)
        _ui(_show)

    # ── Redémarrer ──────────────────────────────────────────────
    elif action == "redemarrer":
        try:
            from updater import redemarrer
            if _app_ref:
                _app_ref.after(2000, redemarrer)
        except Exception:
            pass

    # ── Rapport système ─────────────────────────────────────────
    elif action == "demander_rapport":
        infos = (f"Version:{_get_version()} | "
                 f"OS:{platform.system()} {platform.release()} | "
                 f"Python:{sys.version[:20]}")
        _rapport("info", infos)

    # ── Désactiver module ───────────────────────────────────────
    elif action == "desactiver_module" and param:
        try:
            bf = _DATA / "modules_bloques.json"
            blocked = json.loads(bf.read_text()) if bf.exists() else []
            if param not in blocked:
                blocked.append(param)
                bf.write_text(json.dumps(blocked))
            def _notif(p=param):
                import tkinter.messagebox as mb
                mb.showwarning("Module désactivé",
                               f"Le module '{p}' a été désactivé\n"
                               "par votre administrateur.")
            _ui(_notif)
        except Exception as e:
            _rapport("erreur", f"Désactivation {param}: {e}")

    # ── Réactiver module ────────────────────────────────────────
    elif action == "activer_module" and param:
        try:
            bf = _DATA / "modules_bloques.json"
            if bf.exists():
                blocked = [b for b in json.loads(bf.read_text()) if b != param]
                bf.write_text(json.dumps(blocked))
            def _notif2(p=param):
                import tkinter.messagebox as mb
                mb.showinfo("Module réactivé", f"Le module '{p}' a été réactivé.")
            _ui(_notif2)
        except Exception as e:
            _rapport("erreur", f"Activation {param}: {e}")

    # ── Révoquer la licence ─────────────────────────────────────
    elif action == "revoquer":
        try:
            from licence_manager import revoquer_localement, LICENCE_FILE
            if LICENCE_FILE.exists():
                cle = LICENCE_FILE.read_text().strip()
                revoquer_localement(cle)
        except Exception:
            # Fallback si import échoue
            lic = _DATA / "licence.key"
            revoke = _DATA / "licence.key.revoquee"
            if lic.exists() and not revoke.exists():
                lic.rename(revoke)
        def _quit():
            import tkinter.messagebox as mb
            mb.showerror("Licence révoquée",
                         "Votre licence a été révoquée.\n"
                         "Contactez votre revendeur.")
            if _app_ref:
                _app_ref.quit()
        _ui(_quit)

# ── Boucle principale ────────────────────────────────────────────
def demarrer(app_ref=None):
    """Démarre le client de maintenance en arrière-plan."""
    global _app_ref
    _app_ref = app_ref

    def _loop():
        # Premier ping après 10 secondes
        time.sleep(10)

        cycle = 0
        while True:
            try:
                commandes = _send_heartbeat()
                for cmd in commandes:
                    _executer(cmd)
            except Exception:
                pass

            cycle += 1
            time.sleep(HEARTBEAT_INTERVAL)

    t = threading.Thread(target=_loop, daemon=True, name="MaintenanceClient")
    t.start()
    return t
