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
# Lire l'URL depuis config.py (chemin permanent)
try:
    from config import get_server_url
    SERVER_URL = get_server_url()
except ImportError:
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
    """Envoie un ping au serveur, reçoit les commandes et synchronise les révocations."""
    try:
        # Synchroniser la liste de révocation en même temps
        try:
            from licence_manager import synchroniser_revocation
            rev = synchroniser_revocation(SERVER_URL)
            if rev.get("revoquee") and app_ref:
                # La licence a été révoquée depuis le serveur → bloquer
                def _block():
                    import tkinter.messagebox as mb
                    mb.showerror("Licence révoquée",
                        "Votre licence a été révoquée.\n"
                        "Contactez votre revendeur.")
                    if app_ref: app_ref.quit()
                try: app_ref.after(0, _block)
                except Exception: pass
        except Exception:
            pass

        lic_valide = False
        try:
            from licence_manager import charger_et_verifier
            lic_valide = charger_et_verifier().get("valide", False)
        except Exception:
            pass

        payload = json.dumps({
            "machine_id":    _get_machine_id(),
            "version":       _get_version(),
            "os":            platform.system() + " " + platform.release(),
            "licence_valide": lic_valide,
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
        # Révoquer + mettre à jour la liste noire locale
        try:
            from licence_manager import revoquer_localement, LICENCE_FILE
            if LICENCE_FILE.exists():
                cle = LICENCE_FILE.read_text().strip()
                revoquer_localement(cle)
            # Forcer téléchargement liste révocation
            from licence_manager import telecharger_liste_revocation
            telecharger_liste_revocation(SERVER_URL)
        except Exception:
            lic = APP_DIR / "licence.key"
            if lic.exists():
                lic.rename(APP_DIR / "licence.key.revoquee")
        if app_ref:
            def quit_app():
                import tkinter.messagebox as mb
                mb.showerror("Licence révoquée",
                    "Votre licence a été révoquée par l'administrateur.\n"
                    "Contactez votre revendeur pour plus d'informations.")
                app_ref.quit()
            app_ref.after(0, quit_app)

def demarrer(app_ref=None):
    """Démarre le client de maintenance en arrière-plan."""
    def _loop():
        # Premier ping après 10 secondes
        time.sleep(10)
        # Télécharger la liste de révocation au démarrage
        try:
            from licence_manager import telecharger_liste_revocation
            telecharger_liste_revocation(SERVER_URL)
        except Exception:
            pass

        cycle = 0
        while True:
            try:
                commandes = _send_heartbeat()
                for cmd in commandes:
                    _executer_commande(cmd, app_ref)
            except Exception:
                pass

            # Télécharger la liste de révocation toutes les 10 cycles (20 min)
            cycle += 1
            if cycle % 10 == 0:
                try:
                    from licence_manager import telecharger_liste_revocation, charger_et_verifier
                    telecharger_liste_revocation(SERVER_URL)
                    # Vérifier si la licence a été révoquée
                    lic = charger_et_verifier()
                    if not lic.get("valide") and app_ref:
                        def _block():
                            from main_window import MainWindow
                            if isinstance(app_ref, MainWindow):
                                app_ref.after(0, app_ref._bloquer_acces_expire)
                        _block()
                except Exception:
                    pass

            time.sleep(HEARTBEAT_INTERVAL)

    t = threading.Thread(target=_loop, daemon=True, name="MaintenanceClient")
    t.start()
    return t
