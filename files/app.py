# app.py — Lanceur Principal de l'Application

import sys
import os
import shutil

# ── DPI Awareness Windows (évite flou + mauvais centrage sur écrans HD) ──
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Windows 10+
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()   # Windows 7/8
    except Exception:
        pass
from datetime import datetime

# ─── Assurer que le répertoire courant est dans le path ─────────
# Critique quand lancé depuis un raccourci bureau (working dir != app dir)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
# Forcer le répertoire de travail sur le dossier de l'application
os.chdir(BASE_DIR)

APP_VERSION = "1.0.1"
BACKUP_DIR  = "backups_db"
PHOTOS_DIR  = "photos_eleves"


def sauvegarde_initiale():
    """Crée une copie horodatée de la BDD au démarrage."""
    from database import DB_PATH
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom = f"DB_{os.path.basename(DB_PATH).replace('.db', '')}_{ts}.db"
    dest = os.path.join(BACKUP_DIR, nom)
    try:
        shutil.copy2(DB_PATH, dest)
        print(f"✅ Sauvegarde initiale : {dest}")
    except Exception as e:
        print(f"⚠️  Sauvegarde échouée : {e}")


def creer_periodes_initiales(session):
    """Crée les périodes académiques de base si elles n'existent pas."""
    from database import PeriodeAcademique
    periodes = [
        ("Trimestre 1", "Collège", 1), ("Trimestre 2", "Collège", 2),
        ("Trimestre 3", "Collège", 3), ("Semestre 1", "Lycée", 1),
        ("Semestre 2", "Lycée", 2), ("Annuel", "Collège", 4), ("Annuel", "Lycée", 3),
    ]
    crees = 0
    for nom, niveau, ordre in periodes:
        ex = session.query(PeriodeAcademique).filter_by(nom=nom, niveau_scolaire=niveau).first()
        if not ex:
            session.add(PeriodeAcademique(nom=nom, niveau_scolaire=niveau, ordre=ordre))
            crees += 1
    if crees:
        session.flush()
        print(f"✅ {crees} périodes académiques créées.")


def setup_initial_data(session):
    """Insère des données de test si la base est vide."""
    from database import (ConfigurationGlobale, Classe, Professeur, Matiere,
                           MatiereClasse, Eleve, Faute)

    # 0. Configuration Globale
    cfg = session.query(ConfigurationGlobale).filter_by(id=1).one_or_none()
    annee_courante = "2025-2026"
    if not cfg:
        # Lire le nom depuis la licence si disponible
        try:
            from licence_manager import get_infos_licence as _gli
            _li2 = _gli()
            _nom_etab = _li2.get("etablissement","") or "Mon Établissement"
        except Exception:
            _nom_etab = "Mon Établissement"
        cfg = ConfigurationGlobale(id=1, annee_academique_en_cours=annee_courante,
                                   annee_verrouillee=False,
                                   nom_etablissement=_nom_etab)
        session.add(cfg)
        session.flush()
        print("✅ Configuration Globale initialisée.")
    else:
        annee_courante = cfg.annee_academique_en_cours
        print(f"✅ Année en cours : {annee_courante}")

    # Si des classes existent déjà, on ne repeuple pas
    if session.query(Classe).count() > 0:
        print("ℹ️  Base de données déjà peuplée. Skipping.")
        return

    os.makedirs(PHOTOS_DIR, exist_ok=True)
    print("📝 Peuplement initial de la base de données…")

    creer_periodes_initiales(session)
    session.commit()

    # Professeurs
    p1 = Professeur(nom="Dubois", prenom="Sophie", contact="sophie@ecole.tg",
                    niveau_enseignement="Collège, Lycée", role="Professeur")
    p2 = Professeur(nom="Leroy",  prenom="Marc",   contact="marc@ecole.tg",
                    niveau_enseignement="Collège", role="Professeur")
    session.add_all([p1, p2])

    # Matières
    m1 = Matiere(nom="Mathématiques")
    m2 = Matiere(nom="Français")
    m3 = Matiere(nom="Histoire-Géo")
    m4 = Matiere(nom="Anglais")
    session.add_all([m1, m2, m3, m4])
    session.commit()

    p1.matieres.extend([m2, m3, m4])
    p2.matieres.extend([m1, m4])
    session.flush()

    # Classes
    c1 = Classe(nom="6ème A", annee_scolaire=annee_courante,
                type_etablissement="Collège", niveau=1)
    c2 = Classe(nom="5ème B", annee_scolaire=annee_courante,
                type_etablissement="Collège", niveau=2)
    c3 = Classe(nom="Terminale S", annee_scolaire=annee_courante,
                type_etablissement="Lycée", niveau=3)
    session.add_all([c1, c2, c3])
    session.flush()

    # Coefficients
    session.add_all([
        MatiereClasse(classe_id=c1.id, matiere_id=m1.id, coefficient=4),
        MatiereClasse(classe_id=c1.id, matiere_id=m2.id, coefficient=3),
        MatiereClasse(classe_id=c1.id, matiere_id=m3.id, coefficient=2),
        MatiereClasse(classe_id=c1.id, matiere_id=m4.id, coefficient=2),
        MatiereClasse(classe_id=c2.id, matiere_id=m1.id, coefficient=3),
        MatiereClasse(classe_id=c2.id, matiere_id=m2.id, coefficient=3),
        MatiereClasse(classe_id=c2.id, matiere_id=m3.id, coefficient=3),
        MatiereClasse(classe_id=c2.id, matiere_id=m4.id, coefficient=2),
        MatiereClasse(classe_id=c3.id, matiere_id=m1.id, coefficient=5),
        MatiereClasse(classe_id=c3.id, matiere_id=m2.id, coefficient=3),
        MatiereClasse(classe_id=c3.id, matiere_id=m3.id, coefficient=2),
        MatiereClasse(classe_id=c3.id, matiere_id=m4.id, coefficient=4),
    ])
    session.commit()

    # Élèves
    def parse_date(s):
        from datetime import datetime as dt
        try: return dt.strptime(s, "%d/%m/%Y").date()
        except: return None

    eleves = [
        Eleve(nom="Durand",  prenom="Alice",  date_naissance=parse_date("10/05/2012"),
              contact="0601020304", classe_id=c1.id, est_actif=True, sexe="F",  statut="Nouveau"),
        Eleve(nom="Martin",  prenom="Hugo",   date_naissance=parse_date("20/01/2013"),
              contact="0604050607", classe_id=c1.id, est_actif=True, sexe="M",  statut="Ancien"),
        Eleve(nom="Petit",   prenom="Chloé",  date_naissance=parse_date("05/11/2011"),
              contact="0608091011", classe_id=c2.id, est_actif=True, sexe="F",  statut="Ancien"),
        Eleve(nom="Rousseau",prenom="Lucas",  date_naissance=parse_date("15/09/2012"),
              contact="0612131415", classe_id=c2.id, est_actif=True, sexe="M",  statut="Nouveau"),
        Eleve(nom="Dupont",  prenom="Marie",  date_naissance=parse_date("01/01/2008"),
              contact="0616171819", classe_id=c3.id, est_actif=True, sexe="F",  statut="Ancien"),
    ]
    session.add_all(eleves)

    # Fautes de discipline
    session.add_all([
        Faute(nom="Retard non justifié", gravite="Mineure"),
        Faute(nom="Injure/Insolence",    gravite="Grave"),
        Faute(nom="Matériel oublié",     gravite="Mineure"),
    ])
    session.commit()
    print("✅ Données de test insérées avec succès !")


# ─── Point d'entrée ─────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Initialiser la BDD
    try:
        from database import init_db, DB_PATH, Session
        init_db()
        print(f"✅ Base de données : {DB_PATH}")
    except Exception as e:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Erreur Critique BDD", f"Impossible d'initialiser la base :\n{e}")
        sys.exit(1)

    # 2. Sauvegarde automatique
    sauvegarde_initiale()

    # 3. Données initiales
    session = Session()
    try:
        setup_initial_data(session)
    except Exception as e:
        print(f"⚠️  Erreur peuplement initial : {e}")
        session.rollback()
    finally:
        session.close()

    # 4. Vérification de la licence
    import tkinter as _tk_tmp
    _root_lic = _tk_tmp.Tk(); _root_lic.withdraw()
    try:
        from licence_manager import charger_et_verifier
        lic = charger_et_verifier()
        if not lic["valide"]:
            from licence_window import LicenceWindow
            _activated = [False]
            def _on_act(): _activated[0] = True
            lw = LicenceWindow(_root_lic, on_success=_on_act)
            _root_lic.wait_window(lw)
            if not _activated[0]:
                _root_lic.destroy()
                print("❌ Logiciel non activé."); sys.exit(0)
            # Recharger après activation
            lic = charger_et_verifier()
        # Avertissement expiration proche
        if 0 < lic.get("jours_restants", -1) <= 30:
            from licence_window import LicenceExpireBientot
            leb = LicenceExpireBientot(_root_lic, lic["jours_restants"])
            _root_lic.wait_window(leb)
    except ImportError:
        pass  # Module licence absent → mode développement
    _root_lic.destroy()

    # 5. Authentification — fenêtre racine cachée + Toplevel login
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()   # Masquer la fenêtre racine

    from login_window import LoginWindow
    login = LoginWindow(root)
    login.grab_set()
    root.wait_window(login)  # Attendre que le login se ferme

    if not login.user_info:
        print("❌ Connexion annulée.")
        root.destroy()
        sys.exit(0)

    user = login.user_info
    print(f"✅ Connecté : {user['login']} ({user['role']})")

    # 6. Lancer l'interface principale
    root.destroy()   # Détruire la fenêtre racine cachée

    from main_window import MainWindow
    app = MainWindow()

    # Démarrer le client de télémaintenance en arrière-plan
    try:
        from maintenance_client import demarrer as demarrer_maintenance
        demarrer_maintenance(app)
    except Exception:
        pass

    # Vérifier les mises à jour en arrière-plan (sans bloquer)
    def _check_update_bg():
        try:
            from updater import verifier_mise_a_jour_silencieuse
            info = verifier_mise_a_jour_silencieuse()
            if info:
                # Afficher la proposition après 3 secondes
                def _show():
                    from update_dialog import UpdateDialog
                    UpdateDialog(app, info)
                app.after(3000, _show)
        except Exception:
            pass
    import threading
    threading.Thread(target=_check_update_bg, daemon=True).start()
    app.user_info = user
    app.title(f"🏫 Gestion Scolaire — {user['nom'] or user['login']}  [{user['role'].upper()}]")
    try:
        nom_affiche = user['nom'] or user['login']
        app.btn_compte.config(text=f"👤  {nom_affiche}")
    except Exception:
        pass
    app.mainloop()
