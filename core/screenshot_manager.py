# core/screenshot_manager.py
"""
Gestionnaire de captures d'écran pour SnapMaster - VERSION CORRIGÉE
Gère tous les types de captures avec optimisation mémoire et sélection de zone interactive FIGÉE
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
    """Interface de sélection de zone interactive avec arrière-plan FIGÉ comme Windows Snipping Tool"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.root = None
        self.canvas = None
        self.selected_area = None
        self.frozen_screenshot = None  # L'image figée de l'écran
        self.tk_image = None

        # Variables pour la sélection
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.selecting = False
        self.selection_confirmed = False

        # Style de l'interface
        self.overlay_color = '#000000'
        self.selection_color = '#FF0000'  # Rouge pour la sélection
        self.selection_width = 2

    def select_area(self) -> Optional[Tuple[int, int, int, int]]:
        """Lance l'interface de sélection et retourne les coordonnées (x, y, width, height)"""
        try:
            self.logger.info("Début sélection de zone avec arrière-plan figé")

            # 1. ÉTAPE CRITIQUE : Prendre une capture d'écran COMPLÈTE pour la figer
            self._capture_screen_for_selection()

            if not self.frozen_screenshot:
                self.logger.error("Impossible de capturer l'écran pour la sélection")
                return None

            # 2. Créer l'interface de sélection avec l'image figée
            if not self._create_selection_interface():
                return None

            # 3. Lancer la boucle d'événements pour la sélection
            self.root.mainloop()

            # 4. Nettoyer les ressources
            self._cleanup_selection_interface()

            # 5. Retourner les coordonnées sélectionnées
            return self.selected_area

        except Exception as e:
            self.logger.error(f"Erreur sélection de zone: {e}")
            self._cleanup_selection_interface()
            return None

    def _capture_screen_for_selection(self):
        """Capture l'écran complet pour créer l'arrière-plan figé"""
        try:
            self.logger.info("Capture de l'écran pour créer l'arrière-plan figé...")

            # Prend une capture d'écran complète avec pyautogui
            self.frozen_screenshot = pyautogui.screenshot()

            self.logger.info(f"Écran capturé: {self.frozen_screenshot.size}")

        except Exception as e:
            self.logger.error(f"Erreur capture écran pour sélection: {e}")
            self.frozen_screenshot = None

    def _create_selection_interface(self) -> bool:
        """Crée l'interface de sélection avec l'arrière-plan figé"""
        try:
            if not self.frozen_screenshot:
                return False

            # Obtient les dimensions de l'écran
            screen_width, screen_height = self.frozen_screenshot.size

            # Crée la fenêtre principale
            self.root = tk.Tk()
            self.root.title("Sélection de zone - SnapMaster")

            # Configuration de la fenêtre pour couvrir tout l'écran
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")
            self.root.overrideredirect(True)  # Pas de barre de titre
            self.root.attributes('-topmost', True)  # Au-dessus de tout
            self.root.configure(bg='black')
            self.root.focus_force()

            # Crée le canvas
            self.canvas = tk.Canvas(
                self.root,
                width=screen_width,
                height=screen_height,
                bg='black',
                highlightthickness=0,
                cursor='crosshair'
            )
            self.canvas.pack(fill=tk.BOTH, expand=True)

            # Convertit l'image PIL en format Tkinter
            self.tk_image = ImageTk.PhotoImage(self.frozen_screenshot)

            # Affiche l'image figée en arrière-plan
            self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW, tags='background')

            # Configuration des événements
            self._setup_event_bindings()

            # Instructions pour l'utilisateur
            self._show_instructions()

            self.logger.info("Interface de sélection créée avec arrière-plan figé")
            return True

        except Exception as e:
            self.logger.error(f"Erreur création interface sélection: {e}")
            return False

    def _setup_event_bindings(self):
        """Configure les événements de souris et clavier"""
        # Événements de souris
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<B1-Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self.canvas.bind('<Motion>', self._on_mouse_move)

        # Événements de clavier
        self.root.bind('<Escape>', self._cancel_selection)
        self.root.bind('<Return>', self._confirm_selection)
        self.root.bind('<space>', self._confirm_selection)

        # Focus sur le canvas
        self.canvas.focus_set()

    def _show_instructions(self):
        """Affiche les instructions à l'utilisateur"""
        # Instructions en haut de l'écran
        screen_width = self.frozen_screenshot.size[0]

        # Fond semi-transparent pour les instructions
        instructions_bg = self.canvas.create_rectangle(
            0, 0, screen_width, 80,
            fill='black', stipple='gray50', tags='instructions'
        )

        # Texte principal
        self.canvas.create_text(
            screen_width // 2, 25,
            text="Cliquez et glissez pour sélectionner une zone à capturer",
            fill='white',
            font=('Segoe UI', 16, 'bold'),
            tags='instructions'
        )

        # Instructions supplémentaires
        self.canvas.create_text(
            screen_width // 2, 55,
            text="Entrée/Espace = Capturer • Échap = Annuler",
            fill='lightgray',
            font=('Segoe UI', 12),
            tags='instructions'
        )

    def _on_click(self, event):
        """Début de la sélection"""
        self.start_x = event.x
        self.start_y = event.y
        self.selecting = True

        # Supprime l'ancien rectangle s'il existe
        self.canvas.delete('selection')

        # Supprime les instructions
        self.canvas.delete('instructions')

    def _on_drag(self, event):
        """Pendant le glissement de la souris"""
        if not self.selecting:
            return

        # Supprime l'ancien rectangle
        self.canvas.delete('selection')

        # Calcule les coordonnées
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        # Assure l'ordre correct des coordonnées
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        # Crée le rectangle de sélection
        self.canvas.create_rectangle(
            min_x, min_y, max_x, max_y,
            outline=self.selection_color,
            width=self.selection_width,
            tags='selection'
        )

        # Affiche les dimensions
        width = max_x - min_x
        height = max_y - min_y

        if width > 10 and height > 10:  # Seulement si assez grand
            # Info sur les dimensions
            info_text = f"{width} × {height} pixels"
            self.canvas.create_text(
                min_x + width // 2, min_y - 20,
                text=info_text,
                fill='white',
                font=('Segoe UI', 12, 'bold'),
                tags='selection'
            )

            # Coins de sélection pour clarté
            corner_size = 6
            # Coin supérieur gauche
            self.canvas.create_rectangle(
                min_x - corner_size, min_y - corner_size,
                min_x + corner_size, min_y + corner_size,
                fill='white', outline=self.selection_color, width=1,
                tags='selection'
            )
            # Coin inférieur droit
            self.canvas.create_rectangle(
                max_x - corner_size, max_y - corner_size,
                max_x + corner_size, max_y + corner_size,
                fill='white', outline=self.selection_color, width=1,
                tags='selection'
            )

    def _on_release(self, event):
        """Fin de la sélection"""
        if not self.selecting:
            return

        self.selecting = False

        # Calcule les coordonnées finales
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        # Assure l'ordre correct
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        width = max_x - min_x
        height = max_y - min_y

        # Vérifie que la sélection est valide
        if width > 5 and height > 5:
            self.selected_area = (min_x, min_y, width, height)
            self._show_confirmation()
        else:
            # Sélection trop petite, recommence
            self.canvas.delete('selection')
            self._show_instructions()

    def _on_mouse_move(self, event):
        """Mouvement de la souris sans clic"""
        pass  # Peut être étendu pour afficher des infos supplémentaires

    def _show_confirmation(self):
        """Affiche l'interface de confirmation"""
        if not self.selected_area:
            return

        x, y, w, h = self.selected_area

        # Supprime les éléments de sélection précédents
        self.canvas.delete('confirmation')

        # Cadre de confirmation en bas de la sélection
        confirm_y = y + h + 10
        screen_height = self.frozen_screenshot.size[1]

        # Ajuste si trop proche du bord
        if confirm_y > screen_height - 60:
            confirm_y = y - 40

        # Fond pour les boutons
        self.canvas.create_rectangle(
            x + w//2 - 120, confirm_y - 10,
            x + w//2 + 120, confirm_y + 30,
            fill='black', outline='white', width=1,
            stipple='gray75', tags='confirmation'
        )

        # Instructions de confirmation
        self.canvas.create_text(
            x + w//2, confirm_y + 10,
            text="Entrée = Capturer • Échap = Annuler • Clic = Nouvelle sélection",
            fill='white',
            font=('Segoe UI', 11, 'bold'),
            tags='confirmation'
        )

    def _confirm_selection(self, event=None):
        """Confirme la sélection"""
        if self.selected_area:
            self.selection_confirmed = True
            self.root.quit()

    def _cancel_selection(self, event=None):
        """Annule la sélection"""
        self.selected_area = None
        self.selection_confirmed = False
        self.root.quit()

    def _cleanup_selection_interface(self):
        """Nettoie les ressources de l'interface"""
        try:
            if self.root:
                self.root.destroy()
                self.root = None

            # Libère l'image Tkinter
            if self.tk_image:
                del self.tk_image
                self.tk_image = None

            # Libère l'image figée
            if self.frozen_screenshot:
                del self.frozen_screenshot
                self.frozen_screenshot = None

        except Exception as e:
            self.logger.error(f"Erreur nettoyage interface sélection: {e}")


class ScreenshotManager:
    """Gestionnaire principal des captures d'écran - VERSION CORRIGÉE"""

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

        # Flag pour vérifier si l'application est active
        self._app_active = True

        # Statistiques
        self.stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'memory_usage_mb': 0
        }

        self.logger.info("ScreenshotManager initialisé (version corrigée)")

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
        """Capture une zone sélectionnée par l'utilisateur avec interface FIGÉE"""
        try:
            self.logger.info("Début capture zone sélectionnée avec arrière-plan figé")
            self._prepare_capture()

            # Interface de sélection avec arrière-plan figé
            selector = AreaSelector()
            region = selector.select_area()

            if not region:
                self.logger.info("Sélection de zone annulée par l'utilisateur")
                return None

            x, y, width, height = region
            self.logger.info(f"Zone sélectionnée: {x},{y} {width}x{height}")

            # IMPORTANT: Petit délai pour que l'interface de sélection disparaisse complètement
            time.sleep(0.5)

            # Délai configurable additionnel
            delay = self.settings.get_capture_settings().get('delay_seconds', 0)
            if delay > 0:
                time.sleep(delay)

            # Capture de la région sélectionnée sur l'écran RÉEL (pas l'image figée)
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
        """Notifie la completion d'une capture - VERSION SÉCURISÉE"""
        # Vérifie si l'application est encore active avant les callbacks
        if not self._app_active:
            self.logger.warning("Application fermée, callbacks ignorés")
            return

        for callback in self.capture_callbacks:
            try:
                # Exécute le callback dans un thread séparé pour éviter les blocages
                def safe_callback():
                    try:
                        if self._app_active:  # Double vérification
                            callback(capture_type, save_path, app_info)
                    except Exception as e:
                        self.logger.error(f"Erreur callback capture sécurisé: {e}")

                threading.Thread(target=safe_callback, daemon=True).start()

            except Exception as e:
                self.logger.error(f"Erreur callback capture: {e}")

    def _notify_error(self, capture_type: str, error_message: str):
        """Notifie une erreur de capture - VERSION SÉCURISÉE"""
        # Vérifie si l'application est encore active avant les callbacks
        if not self._app_active:
            self.logger.warning("Application fermée, callbacks d'erreur ignorés")
            return

        for callback in self.error_callbacks:
            try:
                # Exécute le callback dans un thread séparé pour éviter les blocages
                def safe_error_callback():
                    try:
                        if self._app_active:  # Double vérification
                            callback(capture_type, error_message)
                    except Exception as e:
                        self.logger.error(f"Erreur callback erreur sécurisé: {e}")

                threading.Thread(target=safe_error_callback, daemon=True).start()

            except Exception as e:
                self.logger.error(f"Erreur callback erreur: {e}")

    # Méthodes de callback
    def add_capture_callback(self, callback: Callable):
        """Ajoute un callback de capture terminée"""
        self.capture_callbacks.append(callback)

    def add_error_callback(self, callback: Callable):
        """Ajoute un callback d'erreur"""
        self.error_callbacks.append(callback)

    # Méthodes de contrôle du cycle de vie
    def set_app_active(self, active: bool):
        """Définit si l'application est active pour les callbacks"""
        self._app_active = active
        if not active:
            self.logger.info("Application marquée comme inactive, callbacks désactivés")

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
            self.set_app_active(False)  # Désactive les callbacks
            self.clear_cache()
        except Exception:
            pass