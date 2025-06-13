# config/settings.py
"""
Gestionnaire de configuration pour SnapMaster
Gère les paramètres utilisateur et les associations application/dossier
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

class SettingsManager:
    """Gestionnaire de configuration centralisé"""
    
    def __init__(self, config_file: str = "config/snapmaster_config.json"):
        self.logger = logging.getLogger(__name__)
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configuration par défaut
        self.default_config = {
            "version": "1.0.0",
            "folders": {
                "default_screenshots": str(Path.home() / "Pictures" / "SnapMaster"),
                "custom_folders": {}
            },
            "applications": {
                "app_folder_mapping": {},
                "monitored_apps": []
            },
            "hotkeys": {
                "fullscreen_capture": "ctrl+shift+f",
                "window_capture": "ctrl+shift+w", 
                "area_capture": "ctrl+shift+a",
                "quick_capture": "ctrl+shift+q"
            },
            "capture_settings": {
                "image_format": "PNG",
                "image_quality": 95,
                "include_cursor": False,
                "auto_filename": True,
                "filename_pattern": "Screenshot_%Y%m%d_%H%M%S",
                "delay_seconds": 0
            },
            "ui_settings": {
                "theme": "dark",
                "show_notifications": True,
                "minimize_to_tray": True,
                "auto_start": False,
                "language": "fr"
            },
            "memory_settings": {
                "auto_cleanup": True,
                "memory_threshold_mb": 500,
                "cleanup_interval_seconds": 30
            },
            "advanced": {
                "debug_mode": False,
                "log_level": "INFO",
                "backup_settings": True
            }
        }
        
        self.config = self.load_config()
        self.ensure_folders_exist()
    
    def load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Fusion avec la config par défaut pour les nouvelles clés
                config = self.merge_config(self.default_config, loaded_config)
                self.logger.info("Configuration chargée avec succès")
                return config
            else:
                self.logger.info("Fichier de configuration introuvable, utilisation des valeurs par défaut")
                return self.default_config.copy()
                
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la configuration: {e}")
            return self.default_config.copy()
    
    def save_config(self) -> bool:
        """Sauvegarde la configuration dans le fichier"""
        try:
            # Créer une sauvegarde si demandé
            if self.config.get("advanced", {}).get("backup_settings", True):
                self.create_backup()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            self.logger.info("Configuration sauvegardée avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
            return False
    
    def merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """Fusionne la configuration chargée avec les valeurs par défaut"""
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def ensure_folders_exist(self):
        """S'assure que les dossiers de configuration existent"""
        try:
            # Dossier principal de captures
            default_folder = Path(self.config["folders"]["default_screenshots"])
            default_folder.mkdir(parents=True, exist_ok=True)
            
            # Dossiers personnalisés
            for folder_path in self.config["folders"]["custom_folders"].values():
                Path(folder_path).mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            self.logger.error(f"Erreur création des dossiers: {e}")
    
    def create_backup(self):
        """Crée une sauvegarde de la configuration"""
        try:
            backup_dir = Path("config/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"snapmaster_config_backup_{timestamp}.json"
            
            if self.config_file.exists():
                import shutil
                shutil.copy2(self.config_file, backup_file)
                
                # Garde seulement les 10 dernières sauvegardes
                backups = list(backup_dir.glob("snapmaster_config_backup_*.json"))
                if len(backups) > 10:
                    backups.sort(key=lambda x: x.stat().st_mtime)
                    for old_backup in backups[:-10]:
                        old_backup.unlink()
                        
        except Exception as e:
            self.logger.error(f"Erreur création sauvegarde: {e}")
    
    # Méthodes d'accès aux paramètres
    def get_hotkey(self, action: str) -> str:
        """Récupère un raccourci clavier"""
        return self.config.get("hotkeys", {}).get(action, "")
    
    def set_hotkey(self, action: str, hotkey: str):
        """Définit un raccourci clavier"""
        if "hotkeys" not in self.config:
            self.config["hotkeys"] = {}
        self.config["hotkeys"][action] = hotkey
        self.save_config()
    
    def get_default_folder(self) -> str:
        """Récupère le dossier par défaut pour les captures"""
        return self.config["folders"]["default_screenshots"]
    
    def add_custom_folder(self, name: str, path: str) -> bool:
        """Ajoute un dossier personnalisé"""
        try:
            folder_path = Path(path)
            folder_path.mkdir(parents=True, exist_ok=True)
            
            self.config["folders"]["custom_folders"][name] = str(folder_path)
            self.save_config()
            return True
        except Exception as e:
            self.logger.error(f"Erreur ajout dossier {name}: {e}")
            return False
    
    def get_custom_folders(self) -> Dict[str, str]:
        """Récupère tous les dossiers personnalisés"""
        return self.config["folders"]["custom_folders"]
    
    def remove_custom_folder(self, name: str) -> bool:
        """Supprime un dossier personnalisé"""
        try:
            if name in self.config["folders"]["custom_folders"]:
                del self.config["folders"]["custom_folders"][name]
                self.save_config()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erreur suppression dossier {name}: {e}")
            return False
    
    def link_app_to_folder(self, app_name: str, folder_name: str) -> bool:
        """Lie une application à un dossier"""
        try:
            self.config["applications"]["app_folder_mapping"][app_name] = folder_name
            
            # Ajoute l'app aux apps moniturées si pas déjà présente
            if app_name not in self.config["applications"]["monitored_apps"]:
                self.config["applications"]["monitored_apps"].append(app_name)
            
            self.save_config()
            return True
        except Exception as e:
            self.logger.error(f"Erreur liaison app {app_name}: {e}")
            return False
    
    def get_app_folder(self, app_name: str) -> Optional[str]:
        """Récupère le dossier associé à une application"""
        folder_name = self.config["applications"]["app_folder_mapping"].get(app_name)
        if folder_name:
            # Retourne le chemin du dossier
            if folder_name == "default":
                return self.get_default_folder()
            else:
                return self.config["folders"]["custom_folders"].get(folder_name)
        return None
    
    def get_monitored_apps(self) -> List[str]:
        """Récupère la liste des applications surveillées"""
        return self.config["applications"]["monitored_apps"]
    
    def get_capture_settings(self) -> Dict[str, Any]:
        """Récupère les paramètres de capture"""
        return self.config["capture_settings"]
    
    def update_capture_setting(self, key: str, value: Any):
        """Met à jour un paramètre de capture"""
        self.config["capture_settings"][key] = value
        self.save_config()
    
    def get_memory_settings(self) -> Dict[str, Any]:
        """Récupère les paramètres mémoire"""
        return self.config["memory_settings"]
    
    def get_ui_settings(self) -> Dict[str, Any]:
        """Récupère les paramètres d'interface"""
        return self.config["ui_settings"]
    
    def update_ui_setting(self, key: str, value: Any):
        """Met à jour un paramètre d'interface"""
        self.config["ui_settings"][key] = value
        self.save_config()
    
    def export_config(self, export_path: str) -> bool:
        """Exporte la configuration vers un fichier"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Erreur export configuration: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """Importe une configuration depuis un fichier"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Validation basique
            if "version" not in imported_config:
                raise ValueError("Fichier de configuration invalide")
            
            self.config = self.merge_config(self.default_config, imported_config)
            self.save_config()
            self.ensure_folders_exist()
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur import configuration: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Remet la configuration aux valeurs par défaut"""
        try:
            self.config = self.default_config.copy()
            self.save_config()
            self.ensure_folders_exist()
            return True
        except Exception as e:
            self.logger.error(f"Erreur reset configuration: {e}")
            return False