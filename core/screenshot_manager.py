# core/screenshot_manager.py - VERSION CORRIGÉE CAPTURE ZONE FIGÉE
"""
Gestionnaire de captures d'écran pour SnapMaster - VERSION CORRIGÉE
Gère tous les types de captures avec optimisation mémoire et sélection de zone interactive
avec image figée assombrie et révélation de la sélection - CAPTURE SUR IMAGE FIGÉE
"""

import pyautogui
import time
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Callable, Any, Dict
from PIL import Image, ImageGrab, ImageTk, ImageEnhance
import logging
import threading
import tempfile
import weakref

from core.memory_manager import MemoryManager
from core.app_detector import AppDetector, AppInfo
from config.settings import SettingsManager

class AreaSelector:
    """Interface de sélection de zone avec effets visuels d'assombrissement et révélation"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.root = None
        self.canvas = None
        self.selected_area = None
        self.frozen_screenshot = None  # L'image PIL figée originale
        self.darkened_screenshot = None  # L'image assombrie
        self.tk_image_dark = None  # Image Tkinter assombrie
        self.tk_image_original = None  # Image Tkinter originale pour la révélation

        # Variables pour la sélection
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.selecting = False
        self.selection_confirmed = False

        # Effet visuel - assombrissement
        self.darken_factor = 0.3  # 30% de luminosité (70% d'assombrissement)

        # Style de l'interface
        self.selection_color = '#00FF00'  # Vert vif pour la sélection
        self.selection_width = 3
        self.corner_color = '#FFFFFF'  # Coins blancs

    def select_area(self) -> Optional[Tuple[int, int, int, int, Image.Image]]:
        """Lance l'interface de sélection et retourne les coordonnées + image figée (x, y, width, height, frozen_image)"""
        try:
            self.logger.info("Début sélection de zone avec effets visuels d'assombrissement")

            # 1. Capturer et préparer les images
            if not self._prepare_images():
                return None

            # 2. Créer l'interface de sélection avec effets
            if not self._create_selection_interface():
                return None

            # 3. Lancer la boucle d'événements pour la sélection
            self.root.mainloop()

            # 4. Nettoyer les ressources
            result = None
            if self.selected_area:
                # Retourne les coordonnées ET l'image figée
                x, y, width, height = self.selected_area
                result = (x, y, width, height, self.frozen_screenshot.copy())

            self._cleanup_selection_interface()

            # 5. Retourner les coordonnées sélectionnées + image figée
            return result

        except Exception as e:
            self.logger.error(f"Erreur sélection de zone: {e}")
            self._cleanup_selection_interface()
            return None

    def _prepare_images(self) -> bool:
        """Prépare les images : capture l'écran et crée la version assombrie"""
        try:
            self.logger.info("Capture et préparation des images avec effets...")

            # Capture l'écran complet
            self.frozen_screenshot = pyautogui.screenshot()
            self.logger.info(f"Écran capturé et figé: {self.frozen_screenshot.size}")

            # Crée la version assombrie
            enhancer = ImageEnhance.Brightness(self.frozen_screenshot)
            self.darkened_screenshot = enhancer.enhance(self.darken_factor)
            self.logger.info("Version assombrie créée")

            return True

        except Exception as e:
            self.logger.error(f"Erreur préparation images: {e}")
            return False

    def _create_selection_interface(self) -> bool:
        """Crée l'interface de sélection avec effets visuels"""
        try:
            if not self.frozen_screenshot or not self.darkened_screenshot:
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

            # Prépare les images Tkinter avec références fortes
            self.tk_image_dark = ImageTk.PhotoImage(self.darkened_screenshot, master=self.root)
            self.tk_image_original = ImageTk.PhotoImage(self.frozen_screenshot, master=self.root)

            # Maintient les références fortes pour éviter le garbage collection
            self.canvas.image_dark = self.tk_image_dark
            self.canvas.image_original = self.tk_image_original

            # Affiche l'image assombrie en arrière-plan
            self.canvas.create_image(0, 0, image=self.tk_image_dark, anchor=tk.NW, tags='background_dark')

            # Configuration des événements
            self._setup_event_bindings()

            # Instructions pour l'utilisateur
            self._show_instructions()

            self.logger.info("Interface de sélection créée avec effets visuels")
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
        """Affiche les instructions à l'utilisateur avec style moderne"""
        screen_width = self.frozen_screenshot.size[0]

        # Fond moderne pour les instructions avec bordure arrondie
        instructions_bg = self.canvas.create_rectangle(
            20, 20, screen_width - 20, 100,
            fill='#2C3E50', outline='#3498DB', width=2, tags='instructions'
        )

        # Texte principal avec style moderne
        self.canvas.create_text(
            screen_width // 2, 45,
            text="🎯 Cliquez et glissez pour révéler et sélectionner une zone à capturer",
            fill='#ECF0F1',
            font=('Segoe UI', 16, 'bold'),
            tags='instructions'
        )

        # Instructions supplémentaires
        self.canvas.create_text(
            screen_width // 2, 75,
            text="✨ Entrée/Espace = Capturer • Échap = Annuler • La zone sélectionnée révèle l'image figée",
            fill='#BDC3C7',
            font=('Segoe UI', 11),
            tags='instructions'
        )

    def _on_click(self, event):
        """Début de la sélection"""
        self.start_x = event.x
        self.start_y = event.y
        self.selecting = True

        # Supprime l'ancienne sélection
        self._clear_selection()

        # Supprime les instructions
        self.canvas.delete('instructions')

        self.logger.debug(f"Début sélection à ({event.x}, {event.y})")

    def _on_drag(self, event):
        """Pendant le glissement - révèle l'image originale dans la zone sélectionnée"""
        if not self.selecting:
            return

        # Supprime l'ancienne sélection
        self._clear_selection()

        # Calcule les coordonnées
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        # Assure l'ordre correct des coordonnées
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        width = max_x - min_x
        height = max_y - min_y

        if width > 5 and height > 5:
            # Révèle l'image originale dans la zone sélectionnée
            self._reveal_selection_area(min_x, min_y, width, height)

            # Crée le rectangle de sélection avec style moderne
            self.canvas.create_rectangle(
                min_x, min_y, max_x, max_y,
                outline=self.selection_color,
                width=self.selection_width,
                tags='selection_border'
            )

            # Affiche les dimensions avec style
            self._show_selection_info(min_x, min_y, width, height)

            # Coins de sélection modernes
            self._draw_selection_corners(min_x, min_y, max_x, max_y)

    def _reveal_selection_area(self, x: int, y: int, width: int, height: int):
        """Révèle l'image originale dans la zone sélectionnée"""
        try:
            # Crée un crop de l'image originale FIGÉE pour la zone sélectionnée
            selection_crop = self.frozen_screenshot.crop((x, y, x + width, y + height))

            # Convertit en image Tkinter
            tk_selection = ImageTk.PhotoImage(selection_crop, master=self.root)

            # Affiche la zone révélée par-dessus l'image assombrie
            self.canvas.create_image(x, y, image=tk_selection, anchor=tk.NW, tags='revealed_area')

            # Stocke la référence pour éviter le garbage collection
            self.canvas.current_selection_image = tk_selection

        except Exception as e:
            self.logger.error(f"Erreur révélation zone: {e}")

    def _show_selection_info(self, x: int, y: int, width: int, height: int):
        """Affiche les informations de la sélection avec style moderne"""
        # Fond pour les informations
        info_y = max(y - 40, 10)  # Au-dessus de la sélection ou en haut si pas de place

        info_bg = self.canvas.create_rectangle(
            x + width // 2 - 80, info_y - 5,
            x + width // 2 + 80, info_y + 25,
            fill='#34495E', outline='#3498DB', width=1,
            tags='selection_info'
        )

        # Texte des dimensions
        info_text = f"📐 {width} × {height} pixels"
        self.canvas.create_text(
            x + width // 2, info_y + 10,
            text=info_text,
            fill='#ECF0F1',
            font=('Segoe UI', 12, 'bold'),
            tags='selection_info'
        )

    def _draw_selection_corners(self, min_x: int, min_y: int, max_x: int, max_y: int):
        """Dessine les coins de sélection modernes"""
        corner_size = 8
        corner_thickness = 3

        # Coins avec style moderne
        corners = [
            (min_x, min_y),  # Coin supérieur gauche
            (max_x, min_y),  # Coin supérieur droit
            (min_x, max_y),  # Coin inférieur gauche
            (max_x, max_y),  # Coin inférieur droit
        ]

        for i, (cx, cy) in enumerate(corners):
            # Carré central du coin
            self.canvas.create_rectangle(
                cx - corner_size//2, cy - corner_size//2,
                cx + corner_size//2, cy + corner_size//2,
                fill=self.corner_color, outline=self.selection_color,
                width=corner_thickness, tags='selection_corners'
            )

    def _clear_selection(self):
        """Supprime tous les éléments de sélection"""
        self.canvas.delete('selection_border')
        self.canvas.delete('selection_info')
        self.canvas.delete('selection_corners')
        self.canvas.delete('revealed_area')
        self.canvas.delete('confirmation')

        # Libère l'image de sélection courante
        if hasattr(self.canvas, 'current_selection_image'):
            delattr(self.canvas, 'current_selection_image')

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
        if width > 10 and height > 10:
            self.selected_area = (min_x, min_y, width, height)
            self._show_confirmation()
            self.logger.info(f"Zone sélectionnée: {width}x{height} à ({min_x}, {min_y}) sur IMAGE FIGÉE")
        else:
            # Sélection trop petite, recommence
            self._clear_selection()
            self._show_instructions()

    def _on_mouse_move(self, event):
        """Mouvement de la souris sans clic - peut ajouter des effets de survol"""
        pass

    def _show_confirmation(self):
        """Affiche l'interface de confirmation moderne"""
        if not self.selected_area:
            return

        x, y, w, h = self.selected_area

        # Position pour la confirmation
        confirm_y = y + h + 20
        screen_height = self.frozen_screenshot.size[1]

        # Ajuste si trop proche du bord
        if confirm_y > screen_height - 80:
            confirm_y = max(y - 60, 10)

        # Fond moderne pour la confirmation
        self.canvas.create_rectangle(
            x + w//2 - 250, confirm_y - 15,
            x + w//2 + 250, confirm_y + 35,
            fill='#27AE60', outline='#2ECC71', width=2,
            tags='confirmation'
        )

        # Icône et texte de confirmation
        self.canvas.create_text(
            x + w//2, confirm_y + 10,
            text="✨ Zone révélée (IMAGE FIGÉE) ! Entrée = Capturer • Échap = Annuler • Clic = Nouvelle sélection",
            fill='white',
            font=('Segoe UI', 12, 'bold'),
            tags='confirmation'
        )

    def _confirm_selection(self, event=None):
        """Confirme la sélection"""
        if self.selected_area:
            self.selection_confirmed = True
            self.logger.info("Sélection confirmée par l'utilisateur - capture sur image figée")
            self.root.quit()

    def _cancel_selection(self, event=None):
        """Annule la sélection"""
        self.selected_area = None
        self.selection_confirmed = False
        self.logger.info("Sélection annulée par l'utilisateur")
        self.root.quit()

    def _cleanup_selection_interface(self):
        """Nettoie toutes les ressources de l'interface"""
        try:
            if self.root:
                self.root.destroy()
                self.root = None

            # Libère toutes les images Tkinter
            if self.tk_image_dark:
                if hasattr(self, 'canvas') and self.canvas:
                    if hasattr(self.canvas, 'image_dark'):
                        delattr(self.canvas, 'image_dark')
                    if hasattr(self.canvas, 'image_original'):
                        delattr(self.canvas, 'image_original')
                    if hasattr(self.canvas, 'current_selection_image'):
                        delattr(self.canvas, 'current_selection_image')

                del self.tk_image_dark
                self.tk_image_dark = None

            if self.tk_image_original:
                del self.tk_image_original
                self.tk_image_original = None

            # Libère les images PIL
            if self.darkened_screenshot:
                del self.darkened_screenshot
                self.darkened_screenshot = None

            # IMPORTANT: On garde self.frozen_screenshot pour la capture finale
            # Elle sera libérée après la capture finale dans ScreenshotManager

            self.logger.info("Ressources de sélection nettoyées (image figée conservée)")

        except Exception as e:
            self.logger.error(f"Erreur nettoyage interface sélection: {e}")


class ScreenshotManager:
    """Gestionnaire principal des captures d'écran avec protection contre les lancements multiples"""

    def __init__(self, settings_manager: SettingsManager, memory_manager: MemoryManager):
        self.logger = logging.getLogger(__name__)
        self.settings = settings_manager
        self.memory_manager = memory_manager
        self.app_detector = AppDetector()

        # Protection contre les lancements multiples
        self._area_selection_active = False
        self._area_selection_lock = threading.Lock()

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

        self.logger.info("ScreenshotManager initialisé avec capture sur image figée")

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
        """Capture une zone sélectionnée avec protection contre les lancements multiples - CORRIGÉ"""
        # Protection contre les lancements multiples
        with self._area_selection_lock:
            if self._area_selection_active:
                self.logger.warning("Sélection de zone déjà active, lancement ignoré")
                self._notify_error("area", "Une sélection de zone est déjà en cours")
                return None

            self._area_selection_active = True

        try:
            self.logger.info("Début capture zone sélectionnée avec effets visuels - VERSION CORRIGÉE")
            self._prepare_capture()

            # Interface de sélection avec effets visuels
            selector = AreaSelector()
            selection_result = selector.select_area()

            if not selection_result:
                self.logger.info("Sélection de zone annulée par l'utilisateur")
                return None

            # Décompose le résultat (coordonnées + image figée)
            x, y, width, height, frozen_image = selection_result
            self.logger.info(f"Zone sélectionnée: {x},{y} {width}x{height} sur image figée")

            # Délai pour que l'interface disparaisse complètement
            time.sleep(0.5)

            # Délai configurable additionnel
            delay = self.settings.get_capture_settings().get('delay_seconds', 0)
            if delay > 0:
                time.sleep(delay)

            # CORRECTION : Capture de la région sélectionnée sur l'IMAGE FIGÉE
            with self._memory_optimized_capture():
                # Découpe la zone sélectionnée directement dans l'image figée
                screenshot = frozen_image.crop((x, y, x + width, y + height))
                self.logger.info(f"Zone découpée dans l'image figée: {screenshot.size}")

                save_path = self._process_and_save_image(
                    screenshot, save_path, folder_override, "area_selection"
                )

            # Libère l'image figée
            del frozen_image

            self._update_stats(True)
            self._notify_capture_complete("area", save_path)

            return save_path

        except Exception as e:
            self.logger.error(f"Erreur capture zone: {e}")
            self._update_stats(False)
            self._notify_error("area", str(e))
            return None

        finally:
            # Libère le verrou dans tous les cas
            with self._area_selection_lock:
                self._area_selection_active = False
            self.logger.debug("Verrou de sélection de zone libéré")

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

    def is_area_selection_active(self) -> bool:
        """Vérifie si une sélection de zone est active"""
        return self._area_selection_active

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
        if not self._app_active:
            self.logger.warning("Application fermée, callbacks ignorés")
            return

        for callback in self.capture_callbacks:
            try:
                def safe_callback():
                    try:
                        if self._app_active:
                            callback(capture_type, save_path, app_info)
                    except Exception as e:
                        self.logger.error(f"Erreur callback capture: {e}")

                threading.Thread(target=safe_callback, daemon=True).start()

            except Exception as e:
                self.logger.error(f"Erreur callback capture: {e}")

    def _notify_error(self, capture_type: str, error_message: str):
        """Notifie une erreur de capture"""
        if not self._app_active:
            self.logger.warning("Application fermée, callbacks d'erreur ignorés")
            return

        for callback in self.error_callbacks:
            try:
                def safe_error_callback():
                    try:
                        if self._app_active:
                            callback(capture_type, error_message)
                    except Exception as e:
                        self.logger.error(f"Erreur callback erreur: {e}")

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