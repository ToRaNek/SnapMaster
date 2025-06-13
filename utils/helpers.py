# utils/helpers.py
"""
Fonctions utilitaires pour SnapMaster
Fonctions communes et helpers
"""

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time
import hashlib
import json

def get_system_info() -> Dict[str, str]:
    """Retourne les informations système"""
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'architecture': platform.architecture()[0],
        'python_version': platform.python_version(),
        'hostname': platform.node()
    }

def ensure_directory(path: str) -> bool:
    """S'assure qu'un répertoire existe"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Erreur création répertoire {path}: {e}")
        return False

def safe_filename(filename: str) -> str:
    """Nettoie un nom de fichier pour qu'il soit valide"""
    # Caractères interdits sur Windows/Linux
    forbidden = '<>:"/\\|?*'
    
    # Remplace les caractères interdits
    for char in forbidden:
        filename = filename.replace(char, '_')
    
    # Supprime les espaces en début/fin
    filename = filename.strip()
    
    # Évite les noms réservés Windows
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in reserved_names:
        filename = f"_{filename}"
    
    # Limite la longueur
    if len(filename) > 200:
        name = Path(filename).stem[:190]
        ext = Path(filename).suffix
        filename = f"{name}{ext}"
    
    return filename

def format_file_size(size_bytes: int) -> str:
    """Formate une taille de fichier en format lisible"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"

def get_file_hash(filepath: str, algorithm: str = 'md5') -> Optional[str]:
    """Calcule le hash d'un fichier"""
    try:
        hash_obj = hashlib.new(algorithm)
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    except Exception as e:
        logging.error(f"Erreur calcul hash {filepath}: {e}")
        return None

def open_file_manager(path: str) -> bool:
    """Ouvre le gestionnaire de fichiers à l'emplacement spécifié"""
    try:
        path = Path(path)
        
        # S'assure que le chemin existe
        if not path.exists():
            if path.is_file():
                path = path.parent
            else:
                ensure_directory(str(path))
        
        system = platform.system()
        
        if system == "Windows":
            if path.is_file():
                subprocess.run(['explorer', '/select,', str(path)], check=True)
            else:
                subprocess.run(['explorer', str(path)], check=True)
                
        elif system == "Darwin":  # macOS
            if path.is_file():
                subprocess.run(['open', '-R', str(path)], check=True)
            else:
                subprocess.run(['open', str(path)], check=True)
                
        elif system == "Linux":
            # Essaie différents gestionnaires de fichiers
            file_managers = ['nautilus', 'dolphin', 'thunar', 'pcmanfm', 'xdg-open']
            
            for fm in file_managers:
                try:
                    if path.is_file() and fm == 'nautilus':
                        subprocess.run([fm, '--select', str(path)], check=True)
                    else:
                        subprocess.run([fm, str(path)], check=True)
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                return False
        
        return True
    
    except Exception as e:
        logging.error(f"Erreur ouverture gestionnaire fichiers: {e}")
        return False

def run_command(command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
    """Exécute une commande système avec timeout"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        return (
            result.returncode == 0,
            result.stdout,
            result.stderr
        )
    
    except subprocess.TimeoutExpired:
        return False, "", "Timeout dépassé"
    except Exception as e:
        return False, "", str(e)

def is_admin() -> bool:
    """Vérifie si le script s'exécute avec des privilèges administrateur"""
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False

def get_display_info() -> List[Dict]:
    """Récupère les informations sur les écrans"""
    displays = []
    
    try:
        if platform.system() == "Windows":
            try:
                import win32api
                import win32con
                
                def enum_display_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                    displays.append({
                        'index': len(displays),
                        'left': lprcMonitor[0],
                        'top': lprcMonitor[1], 
                        'right': lprcMonitor[2],
                        'bottom': lprcMonitor[3],
                        'width': lprcMonitor[2] - lprcMonitor[0],
                        'height': lprcMonitor[3] - lprcMonitor[1]
                    })
                    return True
                
                win32api.EnumDisplayMonitors(None, None, enum_display_proc, 0)
                
            except ImportError:
                # Fallback si pas de win32api
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                
                displays.append({
                    'index': 0,
                    'left': 0,
                    'top': 0,
                    'width': root.winfo_screenwidth(),
                    'height': root.winfo_screenheight(),
                    'right': root.winfo_screenwidth(),
                    'bottom': root.winfo_screenheight()
                })
                
                root.destroy()
        
        else:
            # Linux/macOS fallback
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            
            displays.append({
                'index': 0,
                'left': 0,
                'top': 0,
                'width': root.winfo_screenwidth(),
                'height': root.winfo_screenheight(),
                'right': root.winfo_screenwidth(),
                'bottom': root.winfo_screenheight()
            })
            
            root.destroy()
    
    except Exception as e:
        logging.error(f"Erreur récupération info écrans: {e}")
        # Fallback minimal
        displays.append({
            'index': 0,
            'left': 0,
            'top': 0,
            'width': 1920,
            'height': 1080,
            'right': 1920,
            'bottom': 1080
        })
    
    return displays

def create_backup(source_file: str, backup_dir: str = "backups", max_backups: int = 10) -> bool:
    """Crée une sauvegarde d'un fichier"""
    try:
        source_path = Path(source_file)
        if not source_path.exists():
            return False
        
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Nom de sauvegarde avec timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_path.stem}_backup_{timestamp}{source_path.suffix}"
        backup_file = backup_path / backup_name
        
        # Copie le fichier
        import shutil
        shutil.copy2(source_path, backup_file)
        
        # Nettoie les anciennes sauvegardes
        cleanup_old_backups(backup_path, source_path.stem, max_backups)
        
        return True
    
    except Exception as e:
        logging.error(f"Erreur création sauvegarde: {e}")
        return False

def cleanup_old_backups(backup_dir: Path, file_prefix: str, max_backups: int):
    """Nettoie les anciennes sauvegardes"""
    try:
        # Trouve tous les fichiers de sauvegarde pour ce préfixe
        pattern = f"{file_prefix}_backup_*"
        backup_files = list(backup_dir.glob(pattern))
        
        # Trie par date de modification (plus récent en premier)
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Supprime les sauvegardes excédentaires
        for old_backup in backup_files[max_backups:]:
            old_backup.unlink()
            logging.info(f"Ancienne sauvegarde supprimée: {old_backup.name}")
    
    except Exception as e:
        logging.error(f"Erreur nettoyage sauvegardes: {e}")

def validate_hotkey(hotkey: str) -> Tuple[bool, str]:
    """Valide un raccourci clavier"""
    if not hotkey or not hotkey.strip():
        return False, "Raccourci vide"
    
    hotkey = hotkey.lower().strip()
    
    # Sépare les modificateurs de la touche principale
    parts = hotkey.split('+')
    
    if len(parts) < 2:
        return False, "Un raccourci doit contenir au moins un modificateur"
    
    modifiers = parts[:-1]
    main_key = parts[-1]
    
    # Modificateurs valides
    valid_modifiers = {'ctrl', 'shift', 'alt', 'win', 'cmd', 'super'}
    
    # Vérifie les modificateurs
    for mod in modifiers:
        if mod not in valid_modifiers:
            return False, f"Modificateur invalide: {mod}"
    
    # Vérifie la touche principale
    if not main_key:
        return False, "Touche principale manquante"
    
    # Touches interdites comme touche principale
    forbidden_main_keys = valid_modifiers
    if main_key in forbidden_main_keys:
        return False, f"Impossible d'utiliser '{main_key}' comme touche principale"
    
    return True, "Raccourci valide"

def load_json_file(filepath: str) -> Optional[Dict]:
    """Charge un fichier JSON en sécurité"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erreur chargement JSON {filepath}: {e}")
        return None

def save_json_file(filepath: str, data: Dict) -> bool:
    """Sauvegarde un dictionnaire en JSON"""
    try:
        # Crée une sauvegarde si le fichier existe
        if Path(filepath).exists():
            create_backup(filepath)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return True
    
    except Exception as e:
        logging.error(f"Erreur sauvegarde JSON {filepath}: {e}")
        return False

def setup_logging(log_file: str = "logs/snapmaster.log", level: str = "INFO") -> bool:
    """Configure le système de logging"""
    try:
        # Crée le répertoire de logs
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configuration du logging
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Format des messages
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Handler pour fichier
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        
        # Handler pour console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        
        # Configuration du logger racine
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        return True
    
    except Exception as e:
        print(f"Erreur configuration logging: {e}")
        return False

def get_app_data_dir(app_name: str = "SnapMaster") -> Path:
    """Retourne le répertoire de données de l'application"""
    system = platform.system()
    
    if system == "Windows":
        base_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif system == "Darwin":  # macOS
        base_dir = Path.home() / 'Library' / 'Application Support'
    else:  # Linux et autres
        base_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    
    app_dir = base_dir / app_name
    app_dir.mkdir(parents=True, exist_ok=True)
    
    return app_dir

def is_process_running(process_name: str) -> bool:
    """Vérifie si un processus est en cours d'exécution"""
    try:
        import psutil
        
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                return True
        
        return False
    
    except Exception as e:
        logging.error(f"Erreur vérification processus {process_name}: {e}")
        return False

def debounce(wait_time: float):
    """Décorateur pour éviter les appels répétés d'une fonction"""
    def decorator(func):
        last_called = [0.0]
        
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if current_time - last_called[0] >= wait_time:
                last_called[0] = current_time
                return func(*args, **kwargs)
        
        return wrapper
    return decorator