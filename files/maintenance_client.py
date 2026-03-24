import threading
import time
import json
import platform
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
HEARTBEAT_INTERVAL = 120  # 2 minutes
APP_DIR = Path(__file__).parent
URL_FILE = APP_DIR / "server_url.txt"

# Lecture sécurisée de l'URL serveur
try:
    SERVER_URL = URL_FILE.read_text().strip() if URL_FILE.exists() else "http://votre-vps-ou-ngrok.com"
except Exception:
    SERVER_URL = "http://localhost:5000"

def _get_machine_id():
    try:
        from licence_manager import get_machine_id
        return get_machine_id()
    except ImportError:
        return "UNKNOWN_ID"

def _send_heartbeat():
    """Envoie le ping et récupère les commandes + l'heure serveur."""
    try:
        from licence_manager import charger_et_verifier
        info_licence = charger_et_verifier()
        
        payload = json.dumps({
            "machine_id": _get_machine_id(),
            "os": f"{platform.system()} {platform.release()}",
            "licence_valide": info_licence.get("valide", False),
            "version": "2.0.1"
        }).encode()

        req = urllib.request.Request(
            f"{SERVER_URL}/api/heartbeat",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GestionScolaire-Core/2.1"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            # On peut utiliser data.get("server_time") pour synchroniser la licence
            return data.get("commandes", [])
    except Exception:
        return []

def _executer_commande(cmd, app_ref=None):
    """Logique d'exécution des ordres distants."""
    action = cmd.get("action", "")
    param = cmd.get("param", "")

    if action == "revoquer":
        # 1. Créer le marqueur de révocation
        (APP_DIR / "licence.key.revoquee").touch()
        # 2. Supprimer la clé actuelle
        lic_file = APP_DIR / "licence.key"
        if lic_file.exists():
            lic_file.unlink()
        
        # 3. Fermer l'application avec un message
        if app_ref:
            def force_quit():
                import tkinter.messagebox as mb
                mb.showerror("Sécurité", "Cette licence a été révoquée par l'administrateur.")
                app_ref.destroy()
            app_ref.after(0, force_quit)

    elif action == "message":
        if param and app_ref:
            import tkinter.messagebox as mb
            app_ref.after(0, lambda: mb.showinfo("Notification Serveur", param))

    elif action == "activer_module" or action == "desactiver_module":
        _gerer_modules(action, param)

def _gerer_modules(action, module_name):
    """Gère le blocage dynamique de fonctionnalités."""
    blocked_file = APP_DIR / "modules_bloques.json"
    try:
        blocked = json.loads(blocked_file.read_text()) if blocked_file.exists() else []
        if action == "desactiver_module" and module_name not in blocked:
            blocked.append(module_name)
        elif action == "activer_module":
            blocked = [b for b in blocked if b != module_name]
        blocked_file.write_text(json.dumps(blocked))
    except Exception:
        pass

def demarrer(app_ref=None):
    """Lancement du thread de maintenance."""
    def _main_loop():
        # Vérification immédiate au démarrage si on est révoqué "offline"
        if (APP_DIR / "licence.key.revoquee").exists():
            _executer_commande({"action": "revoquer"}, app_ref)
            return

        time.sleep(5) # Attendre que l'UI soit prête
        while True:
            cmds = _send_heartbeat()
            for c in cmds:
                _executer_commande(c, app_ref)
            time.sleep(HEARTBEAT_INTERVAL)

    thread = threading.Thread(target=_main_loop, daemon=True, name="MaintenanceService")
    thread.start()
    return thread
