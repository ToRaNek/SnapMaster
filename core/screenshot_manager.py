# core/screenshot_manager.py
"""
Gestionnaire de captures d'écran pour SnapMaster
Gère tous les types de captures avec optimisation mémoire et sélection de zone interactive
"""

import pyautogui
import time
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Callable, Any, Dict
from PIL import Image, ImageGrab, ImageTk
import logging
import threading
import tempfile
import weakref

from core.memory_manager import MemoryManager
from core.app_detector import AppDetector, AppInfo
from config.settings import SettingsManager

class AreaSelector:
    """Interface de sélection de zone interactive comme l'outil de capture Windows"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.root = None
        self.canvas = None
        self.selected_area = None
        self.screenshot_image = None
        self.tk_image = None

        # Variables pour la sélection
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.selecting = False

        # Overlay semi-transparent
        self.overlay_color = '#000000'
        self.overlay_alpha = 0.6
        self.selection_alpha = 0.2

    def select_area(self) -> Optional[Tuple[int, int, int, int]]:
        """Lance l'interface de sélection et retourne les coordonnées (x, y, width, height)"""
        try:
            # 1. Obtient les dimensions de l'écran
            import tkinter as tk
            temp_root = tk.Tk()
            temp_root.withdraw()
            screen_width = temp_root.winfo_screenwidth()
            screen_height = temp_root.winfo_screenheight()
            temp_root.destroy()

            # 2. Crée la fenêtre overlay
            self.root = tk.Tk()
            self.root.withdraw()  # Cache temporairement

            # Configuration de la fenêtre overlay
            self.root.overrideredirect(True)  # Pas de barre de titre
            self.root.attributes('-topmost', True)  # Au-dessus de tout
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")  # Couvre tout l'écran
            self.root.configure(bg='#000000')  # Fond noir

            # Rend la fenêtre semi-transparente
            try:
                self.root.attributes('-alpha', 0.3)  # 30% d'opacité = 70% de transparence
            except:
                # Fallback si alpha n'est pas supporté
                pass

            # Curseur en croix
            self.root.configure(cursor='crosshair')

            # 3. Crée le canvas
            self.canvas = tk.Canvas(
                self.root,
                width=screen_width,
                height=screen_height,
                bg='#000000',
                highlightthickness=0,
                cursor='crosshair'
            )
            self.canvas.pack(fill=tk.BOTH, expand=True)

            # 4. Bind les événements de souris
            self.canvas.bind('<Button-1>', self._on_click)
            self.canvas.bind('<B1-Motion>', self._on_drag)
            self.canvas.bind('<ButtonRelease-1>', self._on_release)
            self.canvas.bind('<Motion>', self._on_mouse_move)

            # 5. Bind les touches d'échappement
            self.root.bind('<Escape>', self._cancel_selection)
            self.root.bind('<Return>', self._confirm_selection)

            # 6. Instructions à l'utilisateur
            instruction_text = self.canvas.create_text(
                screen_width // 2, 50,
                text="Cliquez et glissez pour sélectionner une zone - Échap pour annuler",
                fill='white',
                font=('Arial', 16, 'bold'),
                tags='instructions'
            )

            # Instructions supplémentaires
            self.canvas.create_text(
                screen_width // 2, 80,
                text="Relâchez la souris pour capturer la zone sélectionnée",
                fill='#CCCCCC',
                font=('Arial', 12),
                tags='instructions'
            )

            # 7. Focus sur le canvas
            self.canvas.focus_set()

            # 8. Affiche la fenêtre
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

            # 9. Lance la boucle d'événements
            self.root.mainloop()

            # 10. Retourne la zone sélectionnée
            return self.selected_area

        except Exception as e:
            self.logger.error(f"Erreur sélection de zone: {e}")
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
            return None

    def _on_click(self, event):
        """Début de la sélection"""
        self.start_x = event.x
        self.start_y = event.y
        self.selecting = True

        # Supprime le rectangle précédent s'il existe
        if self.current_rect:
            self.canvas.delete(self.current_rect)

        # Créé un nouveau rectangle de sélection
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='#00FF00',  # Bordure verte
            width=2,
            fill='',
            tags='selection'
        )

    def _on_drag(self, event):
        """Pendant le glissement de la souris"""
        if not self.selecting or not self.current_rect:
            return

        # Met à jour le rectangle de sélection
        self.canvas.coords(
            self.current_rect,
            self.start_x, self.start_y,
            event.x, event.y
        )

        # Efface l'overlay dans la zone sélectionnée pour la "désassombrir"
        self._update_selection_area(self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event):
        """Fin de la sélection"""
        if not self.selecting:
            return

        self.selecting = False

        # Calcule les coordonnées finales
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        # Assure que x1,y1 est le coin supérieur gauche
        min_x = min(x1, x2)
        max_x = max(x1, x2)
        min_y = min(y1, y2)
        max_y = max(y1, y2)

        width = max_x - min_x
        height = max_y - min_y

        # Vérifie que la sélection est assez grande (minimum 10x10 pixels)
        if width > 10 and height > 10:
            self.selected_area = (min_x, min_y, width, height)
            self._show_confirmation_ui()
        else:
            # Sélection trop petite, continue
            if self.current_rect:
                self.canvas.delete(self.current_rect)
                self.current_rect = None

    def _on_mouse_move(self, event):
        """Mouvement de la souris (sans clic)"""
        # Affiche les coordonnées dans le titre si nécessaire
        pass

    def _update_selection_area(self, x1, y1, x2, y2):
        """Met à jour la zone de sélection pour la rendre plus visible"""
        # Supprime l'ancien rectangle de sélection
        self.canvas.delete('clear_area')

        # Assure l'ordre correct des coordonnées
        min_x = min(x1, x2)
        max_x = max(x1, x2)
        min_y = min(y1, y2)
        max_y = max(y1, y2)

        # Crée un rectangle de surbrillance pour la zone sélectionnée
        self.canvas.create_rectangle(
            min_x, min_y, max_x, max_y,
            fill='',  # Pas de remplissage
            outline='#00FF00',  # Bordure verte brillante
            width=3,
            tags='clear_area'
        )

        # Ajoute des coins pour marquer la sélection
        corner_size = 10
        corner_color = '#FFFF00'  # Jaune

        # Coin supérieur gauche
        self.canvas.create_rectangle(
            min_x - corner_size//2, min_y - corner_size//2,
            min_x + corner_size//2, min_y + corner_size//2,
            fill=corner_color, outline=corner_color,
            tags='clear_area'
        )

        # Coin supérieur droit
        self.canvas.create_rectangle(
            max_x - corner_size//2, min_y - corner_size//2,
            max_x + corner_size//2, min_y + corner_size//2,
            fill=corner_color, outline=corner_color,
            tags='clear_area'
        )

        # Coin inférieur gauche
        self.canvas.create_rectangle(
            min_x - corner_size//2, max_y - corner_size//2,
            min_x + corner_size//2, max_y + corner_size//2,
            fill=corner_color, outline=corner_color,
            tags='clear_area'
        )

        # Coin inférieur droit
        self.canvas.create_rectangle(
            max_x - corner_size//2, max_y - corner_size//2,
            max_x + corner_size//2, max_y + corner_size//2,
            fill=corner_color, outline=corner_color,
            tags='clear_area'
        )

    def _show_confirmation_ui(self):
        """Affiche l'interface de confirmation"""
        if not self.selected_area:
            return

        # Crée les boutons de confirmation
        x, y, w, h = self.selected_area
        center_x = x + w // 2
        center_y = y + h + 20  # Juste en dessous de la sélection

        # Cadre pour les boutons
        button_frame_id = self.canvas.create_rectangle(
            center_x - 80, center_y - 15,
            center_x + 80, center_y + 15,
            fill='#333333',
            outline='#666666',
            width=1,
            tags='confirm_ui'
        )

        # Texte de confirmation
        confirm_text = self.canvas.create_text(
            center_x, center_y,
            text="Entrée=Capturer  Échap=Annuler",
            fill='white',
            font=('Arial', 10),
            tags='confirm_ui'
        )

        # Instructions
        info_text = self.canvas.create_text(
            center_x, y - 20,
            text=f"Zone: {w}x{h} pixels",
            fill='#00FF00',
            font=('Arial', 12, 'bold'),
            tags='confirm_ui'
        )

    def _confirm_selection(self, event=None):
        """Confirme la sélection actuelle"""
        if self.selected_area:
            self.root.quit()
            self.root.destroy()

    def _cancel_selection(self, event=None):
        """Annule la sélection"""
        self.selected_area = None
        self.root.quit()
        self.root.destroy()

class ScreenshotManager:
    """Gestionnaire principal des captures d'écran"""

    def __init__(self, settings_manager: SettingsManager, memory_manager: MemoryManager):
        self.logger = logging.getLogger(__name__)
        self.settings = settings_manager
        self.memory_manager = memory_manager
        self.app_detector = AppDetector()

        # Configuration PyAutoGUI
        pyautogui.PAUSE = 0.1
        pyautogui.FAILSAFE = True

        # Cache pour optimisation
        self._image_cache: Dict[str, weakref.ref] = {}
        self._temp_files: set = set()

        # Callbacks pour les événements
        self.capture_callbacks: list = []
        self.error_callbacks: list = []

        # Statistiques
        self.stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'memory_usage_mb': 0
        }

        self.logger.info("ScreenshotManager initialisé")

    def capture_fullscreen(self, save_path: Optional[str] = None,
                           folder_override: Optional[str] = None) -> Optional[str]:
        """Capture l'écran entier"""
        try:
            self.logger.info("Début capture plein écran")
            self._prepare_capture()

            # Délai configurable
            delay = self.settings.get_capture_settings().get('delay_seconds', 0)
            if delay > 0:
                time.sleep(delay)

            # Capture avec optimisation mémoire
            with self._memory_optimized_capture():
                screenshot = pyautogui.screenshot()

                # Conversion et sauvegarde
                save_path = self._process_and_save_image(
                    screenshot, save_path, folder_override, "fullscreen"
                )

            self._update_stats(True)
            self._notify_capture_complete("fullscreen", save_path)

            return save_path

        except Exception as e:
            self.logger.error(f"Erreur capture plein écran: {e}")
            self._update_stats(False)
            self._notify_error("fullscreen", str(e))
            return None

    def capture_active_window(self, save_path: Optional[str] = None,
                              folder_override: Optional[str] = None) -> Optional[str]:
        """Capture la fenêtre active"""
        try:
            self.logger.info("Début capture fenêtre active")
            self._prepare_capture()

            # Récupère l'application active
            current_app = self.app_detector.get_current_app()
            if not current_app:
                raise Exception("Impossible de détecter l'application active")

            # Délai configurable
            delay = self.settings.get_capture_settings().get('delay_seconds', 0)
            if delay > 0:
                time.sleep(delay)

            # Détermine le dossier de sauvegarde basé sur l'app
            if not folder_override:
                folder_override = self.settings.get_app_folder(current_app.name)

            # Capture selon le type de fenêtre
            with self._memory_optimized_capture():
                if current_app.is_fullscreen:
                    screenshot = pyautogui.screenshot()
                else:
                    # Capture de la région de la fenêtre
                    x, y, width, height = current_app.window_rect
                    if width > 0 and height > 0:
                        screenshot = pyautogui.screenshot(region=(x, y, width, height))
                    else:
                        # Fallback sur capture plein écran
                        screenshot = pyautogui.screenshot()

                # Sauvegarde avec nom incluant l'app
                filename_prefix = f"{current_app.name}_{current_app.window_title}"
                filename_prefix = self._sanitize_filename(filename_prefix)

                save_path = self._process_and_save_image(
                    screenshot, save_path, folder_override, filename_prefix
                )

            self._update_stats(True)
            self._notify_capture_complete("window", save_path, current_app)

            return save_path

        except Exception as e:
            self.logger.error(f"Erreur capture fenêtre: {e}")
            self._update_stats(False)
            self._notify_error("window", str(e))
            return None

    def capture_area_selection(self, save_path: Optional[str] = None,
                               folder_override: Optional[str] = None) -> Optional[str]:
        """Capture une zone sélectionnée par l'utilisateur avec interface interactive"""
        try:
            self.logger.info("Début capture zone sélectionnée")
            self._prepare_capture()

            # Interface de sélection interactive
            selector = AreaSelector()
            region = selector.select_area()

            if not region:
                self.logger.info("Sélection de zone annulée par l'utilisateur")
                return None

            x, y, width, height = region
            self.logger.info(f"Zone sélectionnée: {x},{y} {width}x{height}")

            # Délai configurable
            delay = self.settings.get_capture_settings().get('delay_seconds', 0)
            if delay > 0:
                time.sleep(delay)

            # Capture de la région sélectionnée
            with self._memory_optimized_capture():
                screenshot = pyautogui.screenshot(region=(x, y, width, height))

                save_path = self._process_and_save_image(
                    screenshot, save_path, folder_override, "area_selection"
                )

            self._update_stats(True)
            self._notify_capture_complete("area", save_path)

            return save_path

        except Exception as e:
            self.logger.error(f"Erreur capture zone: {e}")
            self._update_stats(False)
            self._notify_error("area", str(e))
            return None

    def capture_app_direct(self, app_name: str, save_path: Optional[str] = None) -> Optional[str]:
        """Capture directe d'une application spécifique"""
        try:
            self.logger.info(f"Début capture directe app: {app_name}")
            self._prepare_capture()

            # Vérifie si l'app est active
            current_app = self.app_detector.get_current_app()
            if not current_app or current_app.name.lower() != app_name.lower():
                raise Exception(f"Application {app_name} non active")

            # Récupère le dossier configuré pour cette app
            folder_override = self.settings.get_app_folder(app_name)

            # Utilise la capture de fenêtre active
            return self.capture_active_window(save_path, folder_override)

        except Exception as e:
            self.logger.error(f"Erreur capture directe {app_name}: {e}")
            self._update_stats(False)
            self._notify_error("direct", str(e))
            return None

    def _prepare_capture(self):
        """Prépare l'environnement pour la capture"""
        # Optimisation mémoire préventive
        self.memory_manager.optimize_for_screenshots()

        # Nettoyage du cache d'images
        self._cleanup_image_cache()

        # Nettoyage des fichiers temporaires
        self._cleanup_temp_files()

    def _memory_optimized_capture(self):
        """Context manager pour optimiser la mémoire durant la capture"""
        class MemoryOptimizedContext:
            def __init__(self, manager):
                self.manager = manager
                self.initial_memory = manager.memory_manager.get_current_memory_usage()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Force le nettoyage après capture
                self.manager.memory_manager.force_cleanup()

                final_memory = self.manager.memory_manager.get_current_memory_usage()
                self.manager.stats['memory_usage_mb'] = final_memory

                if final_memory > self.initial_memory + 100:  # Seuil de 100MB
                    self.manager.logger.warning(
                        f"Consommation mémoire élevée après capture: {final_memory:.1f}MB"
                    )

        return MemoryOptimizedContext(self)

    def _process_and_save_image(self, image: Image.Image, save_path: Optional[str],
                                folder_override: Optional[str], prefix: str) -> str:
        """Traite et sauvegarde l'image avec optimisations"""
        try:
            # Détermine le chemin de sauvegarde
            if not save_path:
                save_path = self._generate_filename(folder_override, prefix)

            # S'assure que le dossier existe
            save_dir = Path(save_path).parent
            save_dir.mkdir(parents=True, exist_ok=True)

            # Configuration de la sauvegarde
            capture_settings = self.settings.get_capture_settings()
            image_format = capture_settings.get('image_format', 'PNG')
            quality = capture_settings.get('image_quality', 95)

            # Sauvegarde optimisée
            save_kwargs = {}
            if image_format.upper() == 'JPEG':
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif image_format.upper() == 'PNG':
                save_kwargs['optimize'] = True

            # Sauvegarde avec gestion d'erreur
            try:
                image.save(save_path, format=image_format, **save_kwargs)
            except Exception as save_error:
                # Fallback en PNG
                self.logger.warning(f"Erreur sauvegarde {image_format}, fallback PNG: {save_error}")
                save_path = save_path.rsplit('.', 1)[0] + '.png'
                image.save(save_path, format='PNG', optimize=True)

            # Enregistre dans le cache avec weak reference
            cache_key = f"{prefix}_{int(time.time())}"
            self._image_cache[cache_key] = weakref.ref(image)

            self.logger.info(f"Image sauvegardée: {save_path}")
            return save_path

        except Exception as e:
            self.logger.error(f"Erreur traitement image: {e}")
            raise
        finally:
            # Libère l'image de la mémoire
            del image

    def _generate_filename(self, folder_override: Optional[str], prefix: str) -> str:
        """Génère un nom de fichier automatique"""
        # Dossier de destination
        if folder_override:
            base_folder = folder_override
        else:
            base_folder = self.settings.get_default_folder()

        # Pattern de nom de fichier
        capture_settings = self.settings.get_capture_settings()
        pattern = capture_settings.get('filename_pattern', 'Screenshot_%Y%m%d_%H%M%S')

        # Génère le nom avec timestamp
        timestamp = datetime.now()
        filename = timestamp.strftime(pattern)

        # Ajoute le préfixe si fourni
        if prefix and prefix != "Screenshot":
            filename = f"{prefix}_{filename}"

        # Extension selon le format
        image_format = capture_settings.get('image_format', 'PNG')
        extension = image_format.lower()
        if extension == 'jpeg':
            extension = 'jpg'

        # Chemin complet
        full_path = Path(base_folder) / f"{filename}.{extension}"

        # Évite les conflits de noms
        counter = 1
        while full_path.exists():
            name_without_ext = full_path.stem
            full_path = full_path.parent / f"{name_without_ext}_{counter}.{extension}"
            counter += 1

        return str(full_path)

    def _sanitize_filename(self, filename: str) -> str:
        """Nettoie un nom de fichier pour éviter les caractères invalides"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Limite la longueur
        return filename[:50] if len(filename) > 50 else filename

    def _cleanup_image_cache(self):
        """Nettoie le cache d'images"""
        dead_keys = []
        for key, weak_ref in self._image_cache.items():
            if weak_ref() is None:
                dead_keys.append(key)

        for key in dead_keys:
            del self._image_cache[key]

    def _cleanup_temp_files(self):
        """Nettoie les fichiers temporaires"""
        for temp_file in list(self._temp_files):
            try:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
                self._temp_files.remove(temp_file)
            except Exception as e:
                self.logger.error(f"Erreur nettoyage fichier temp {temp_file}: {e}")

    def _update_stats(self, success: bool):
        """Met à jour les statistiques"""
        self.stats['total_captures'] += 1
        if success:
            self.stats['successful_captures'] += 1
        else:
            self.stats['failed_captures'] += 1

    def _notify_capture_complete(self, capture_type: str, save_path: str,
                                 app_info: Optional[AppInfo] = None):
        """Notifie la completion d'une capture"""
        for callback in self.capture_callbacks:
            try:
                callback(capture_type, save_path, app_info)
            except Exception as e:
                self.logger.error(f"Erreur callback capture: {e}")

    def _notify_error(self, capture_type: str, error_message: str):
        """Notifie une erreur de capture"""
        for callback in self.error_callbacks:
            try:
                callback(capture_type, error_message)
            except Exception as e:
                self.logger.error(f"Erreur callback erreur: {e}")

    # Méthodes de callback
    def add_capture_callback(self, callback: Callable):
        """Ajoute un callback de capture terminée"""
        self.capture_callbacks.append(callback)

    def add_error_callback(self, callback: Callable):
        """Ajoute un callback d'erreur"""
        self.error_callbacks.append(callback)

    # Méthodes utilitaires
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return self.stats.copy()

    def clear_cache(self):
        """Vide tous les caches"""
        self._cleanup_image_cache()
        self._cleanup_temp_files()
        self.memory_manager.force_cleanup()

    def get_supported_formats(self) -> list:
        """Retourne les formats d'image supportés"""
        return ['PNG', 'JPEG', 'BMP', 'GIF']

    def test_capture_capability(self) -> Dict[str, bool]:
        """Teste les capacités de capture"""
        capabilities = {
            'fullscreen': True,
            'window': True,
            'area_selection': True,
            'app_detection': False
        }

        try:
            # Test capture simple
            test_img = pyautogui.screenshot()
            test_img.thumbnail((1, 1))  # Réduit pour économiser la mémoire
            del test_img

            # Test détection d'app
            current_app = self.app_detector.get_current_app()
            capabilities['app_detection'] = current_app is not None

        except Exception as e:
            self.logger.error(f"Erreur test capacités: {e}")
            capabilities['fullscreen'] = False

        return capabilities

    def __del__(self):
        """Nettoyage final"""
        try:
            self.clear_cache()
        except Exception:
            pass