# main.py
"""
SnapMaster - Application de capture d'écran avancée
Point d'entrée principal de l'application
"""

import sys
import os
import logging
from pathlib import Path
import platform

# Gestion des privilèges administrateur uniquement sur Windows si nécessaire
if platform.system() == "Windows":
    try:
        import ctypes
        def is_admin():
            try:
                return ctypes.windll.shell32.IsUserAnAdmin()
            except:
                return False
    except ImportError:
        def is_admin():
            return False
else:
    def is_admin():
        return True  # Pas besoin de privilèges spéciaux sur Linux/macOS

# Ajouter le répertoire racine au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import SnapMasterGUI
from core.memory_manager import MemoryManager
from config.settings import SettingsManager

def setup_logging():
    """Configure le système de logging"""
    #log_dir = Path("logs")
    #log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            #logging.FileHandler('logs/snapmaster.log', encoding='utf-8'),
            #logging.StreamHandler(sys.stdout)
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

        # Test des dépendances Windows
        if platform.system() == "Windows":
            test_windows_dependencies()

        # Initialisation du gestionnaire de mémoire
        memory_manager = MemoryManager()
        memory_manager.start_monitoring()

        # Initialisation des paramètres
        settings_manager = SettingsManager()

        # Lancement de l'interface graphique
        app = SnapMasterGUI(settings_manager, memory_manager)
        logger.info("Interface graphique initialisée")

        # Démarrage de l'application
        app.run()

    except Exception as e:
        logger.error(f"Erreur fatale: {e}")

        # Affiche une boîte de dialogue d'erreur si possible
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("Erreur SnapMaster", f"Une erreur fatale s'est produite:\n\n{str(e)}")
        except:
            pass

        sys.exit(1)

    finally:
        # Nettoyage final
        try:
            if 'memory_manager' in locals():
                memory_manager.stop_monitoring()
            logger.info("SnapMaster fermé proprement")
        except:
            pass


def test_windows_dependencies():
    """Teste la disponibilité des dépendances Windows"""
    logger = logging.getLogger(__name__)

    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        import win32process
        logger.info("Dépendances Windows disponibles - Capture avancée activée")
        return True
    except ImportError as e:
        logger.warning(f"Dépendances Windows manquantes: {e}")
        logger.warning("Fonctionnalités de capture avancée limitées")
        logger.info("Pour activer la capture avancée, installez: pip install pywin32")
        return False

if __name__ == "__main__":
    main()