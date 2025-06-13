# main.py
"""
SnapMaster - Application de capture d'écran avancée
Point d'entrée principal de l'application
"""

import sys
import os
import logging
from pathlib import Path

# Ajouter le répertoire racine au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import SnapMasterGUI
from core.memory_manager import MemoryManager
from config.settings import SettingsManager

def setup_logging():
    """Configure le système de logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/snapmaster.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Point d'entrée principal de l'application"""
    try:
        # Configuration du logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Démarrage de SnapMaster...")

        # Intégration des méthodes manquantes
        try:
            from gui.main_window_methods import add_methods_to_gui
            from gui.main_window import SnapMasterGUI
            add_methods_to_gui(SnapMasterGUI)
            logger.info("Méthodes intégrées avec succès")
        except ImportError as e:
            logger.error(f"Erreur intégration méthodes: {e}")

        # Initialisation du gestionnaire de mémoire
        memory_manager = MemoryManager()
        memory_manager.start_monitoring()

        # Initialisation des paramètres
        settings_manager = SettingsManager()

        # Vérification des permissions
        if not check_permissions():
            logger.error("Permissions insuffisantes pour l'exécution")
            sys.exit(1)

        # Lancement de l'interface graphique
        app = SnapMasterGUI(settings_manager, memory_manager)
        logger.info("Interface graphique initialisée")

        # Démarrage de l'application
        app.run()

    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)

    finally:
        # Nettoyage final
        if 'memory_manager' in locals():
            memory_manager.stop_monitoring()
        logger.info("SnapMaster fermé proprement")

def check_permissions():
    """Vérifie les permissions nécessaires"""
    try:
        # Test d'accès au répertoire de travail
        Path("temp").mkdir(exist_ok=True)
        test_file = Path("temp/test.txt")
        test_file.write_text("test")
        test_file.unlink()

        return True
    except Exception:
        return False

if __name__ == "__main__":
    main()