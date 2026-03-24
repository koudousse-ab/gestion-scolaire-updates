# maintenance_client.py — Client de télémaintenance
"""
Tourne en arrière-plan dans l'app cliente.
Envoie un heartbeat au serveur toutes les 10 minutes.
Reçoit et exécute les commandes du serveur.
"""
import threading, time, json, sys, os, platform
import urllib.request, urllib.error
from pathlib import Path

# ── URL de votre serveur ─────────────────────────────────────
# Remplacez par l'URL de votre serveur en ligne (ex: ngrok, VPS...)
# Lire l'URL depuis server_url.txt si disponible
try:
    _url_file = Path(__file__).parent / "server_url.txt"
    SERVER_URL = _url_file.read_text().strip() if _url_file.exists() else "http://localhost:5000"
except Exception:
    SERVER_URL = "http://localhost:5000"

HEARTBEAT_INTERVAL = 120   # 2 minutes (plus réactif)
APP_DIR = Path(__file__).parent

def _get_version():
    vf = APP_DIR / "version.txt"
    return vf.read_text().strip() if vf.exists() else "2.0.0"

def _get_machine_id():
    try:
        from licence_manager import get_machine_id
        return get_machine_id()
    except Exception:
        return "UNKNOWN"

def _send_heartbeat():
    """Envoie un ping au serveur et reçoit les commandes."""
    try:
        payload = json.dumps({
            "machine_id":    _get_machine_id(),
            "version":       _get_version(),
            "os":            platform.system() + " " + platform.release(),
            "licence_valide": True,
        }).encode()
        req = urllib.request.Request(
            f"{SERVER_URL}/api/heartbeat",
            data=payload,
            headers={"Content-Type": "application/json",
                     "User-Agent": "GestionScolaire-Client/2.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return data.get("commandes", [])
    except Exception:
        return []

def _envoyer_rapport(type_msg, message):
    """Envoie un rapport d'erreur ou info au serveur."""
    try:
        payload = json.dumps({
            "machine_id": _get_machine_id(),
            "type":       type_msg,
            "message":    message,
        }).encode()
        req = urllib.request.Request(
            f"{SERVER_URL}/api/rapport",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def _executer_commande(cmd, app_ref=None):
    """Exécute une commande reçue du serveur."""
    action = cmd.get("action","")
    param  = cmd.get("param","")

    if action == "forcer_maj":
        # Lancer la mise à jour puis redémarrer
        try:
            from updater import verifier_mise_a_jour_silencieuse, appliquer_mise_a_jour, redemarrer
            info = verifier_mise_a_jour_silencieuse()
            if info:
                ok = appliquer_mise_a_jour(info)
                if ok and app_ref:
                    app_ref.after(0, lambda: redemarrer())
        except Exception as e:
            _envoyer_rapport("erreur", f"Erreur MAJ forcée : {e}")

    elif action == "message":
        # Afficher un popup
        if param and app_ref:
            def show():
                import tkinter.messagebox as mb
                mb.showinfo("📢 Message de votre administrateur", param)
            app_ref.after(0, show)

    elif action == "redemarrer":
        if app_ref:
            from updater import redemarrer
            app_ref.after(2000, redemarrer)

    elif action == "demander_rapport":
        # Envoyer les infos système
        infos = (f"Version: {_get_version()} | "
                 f"OS: {platform.system()} {platform.release()} | "
                 f"Python: {sys.version[:20]}")
        _envoyer_rapport("info", f"Rapport demandé : {infos}")

    elif action == "desactiver_module":
        # Désactiver un module — l'ajouter dans modules_bloques.json
        if param:
            try:
                import json
                blocked_file = APP_DIR / "modules_bloques.json"
                blocked = json.loads(blocked_file.read_text()) if blocked_file.exists() else []
                if param not in blocked:
                    blocked.append(param)
                    blocked_file.write_text(json.dumps(blocked))
                if app_ref:
                    def notif_desact(p=param):
                        import tkinter.messagebox as mb
                        mb.showwarning("Module désactivé",
                            f"Le module '{p}' a été désactivé\n"
                            "par votre administrateur.")
                    app_ref.after(0, notif_desact)
            except Exception as e:
                _envoyer_rapport("erreur", f"Erreur désactivation {param}: {e}")

    elif action == "activer_module":
        # Réactiver un module bloqué
        if param:
            try:
                import json
                blocked_file = APP_DIR / "modules_bloques.json"
                if blocked_file.exists():
                    blocked = json.loads(blocked_file.read_text())
                    blocked = [b for b in blocked if b != param]
                    blocked_file.write_text(json.dumps(blocked))
                if app_ref:
                    def notif_act(p=param):
                        import tkinter.messagebox as mb
                        mb.showinfo("Module réactivé",
                            f"Le module '{p}' a été réactivé.")
                    app_ref.after(0, notif_act)
            except Exception as e:
                _envoyer_rapport("erreur", f"Erreur activation {param}: {e}")

    elif action == "revoquer":
        # Supprimer la licence locale
        lic = APP_DIR / "licence.key"
        if lic.exists():
            lic.rename(APP_DIR / "licence.key.revoquee")
        if app_ref:
            def quit_app():
                import tkinter.messagebox as mb
                mb.showerror("Licence révoquée",
                    "Votre licence a été révoquée.\n"
                    "Contactez votre revendeur.")
                app_ref.quit()
            app_ref.after(0, quit_app)

def demarrer(app_ref=None):
    """Démarre le client de maintenance en arrière-plan."""
    def _loop():
        # Premier ping après 10 secondes
        time.sleep(10)
        while True:
            try:
                commandes = _send_heartbeat()
                for cmd in commandes:
                    _executer_commande(cmd, app_ref)
            except Exception:
                pass
            time.sleep(HEARTBEAT_INTERVAL)

    t = threading.Thread(target=_loop, daemon=True, name="MaintenanceClient")
    t.start()
    return t
