# integration.py
"""
Script d'intégration pour SnapMaster
Intègre les méthodes manquantes dans la classe principale
"""

# Import des classes principales
from gui.main_window import SnapMasterGUI
from gui.main_window_methods import add_methods_to_gui

def integrate_methods():
    """Intègre toutes les méthodes manquantes"""
    # Ajoute les méthodes à la classe SnapMasterGUI
    add_methods_to_gui(SnapMasterGUI)
    
    print("✅ Méthodes intégrées avec succès dans SnapMasterGUI")

if __name__ == "__main__":
    integrate_methods()