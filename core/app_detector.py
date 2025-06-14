# core/app_detector.py
"""
Détecteur d'applications au premier plan pour SnapMaster - VERSION AMÉLIORÉE
Détecte quelle application est active et récupère ses informations avec précision
AMÉLIORATION : Coordonnées de fenêtre plus précises pour toutes les applications
"""

import psutil
import time
import logging
import threading
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import platform

# Import spécifique selon l'OS
if platform.system() == "Windows":
    try:
        import win32gui
        import win32process
        import win32con
        import win32api
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
        logging.warning("Modules Windows non disponibles, fonctionnalités limitées")

elif platform.system() == "Linux":
    try:
        import subprocess
        LINUX_AVAILABLE = True
    except ImportError:
        LINUX_AVAILABLE = False

else:  # macOS et autres
    try:
        import subprocess
        MACOS_AVAILABLE = True
    except ImportError:
        MACOS_AVAILABLE = False

@dataclass
class AppInfo:
    """Informations sur une application"""
    name: str
    pid: int
    window_title: str
    executable_path: str
    is_fullscreen: bool
    window_rect: Tuple[int, int, int, int]  # x, y, width, height
    is_game: bool = False
    is_browser: bool = False
    window_handle: int = 0  # Handle de fenêtre Windows
    window_class: str = ""  # Classe de fenêtre Windows

class AppDetector:
    """Détecteur d'applications au premier plan multi-plateforme avec précision améliorée"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_app: Optional[AppInfo] = None
        self.app_history: List[AppInfo] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.update_callbacks: List[Callable[[AppInfo], None]] = []

        # Cache pour éviter les détections répétitives
        self.cache_duration = 1.0  # secondes
        self.last_detection_time = 0
        self.cached_app: Optional[AppInfo] = None

        # Détection des capacités selon l'OS
        self.os_type = platform.system()
        self.capabilities = self._detect_capabilities()

        self.logger.info(f"AppDetector initialisé pour {self.os_type} avec détection améliorée")

    def _detect_capabilities(self) -> Dict[str, bool]:
        """Détecte les capacités disponibles selon l'OS"""
        caps = {
            "window_detection": False,
            "fullscreen_detection": False,
            "window_geometry": False,
            "app_classification": False,
            "precise_coordinates": False
        }

        if self.os_type == "Windows" and WINDOWS_AVAILABLE:
            caps.update({
                "window_detection": True,
                "fullscreen_detection": True,
                "window_geometry": True,
                "app_classification": True,
                "precise_coordinates": True
            })
        elif self.os_type == "Linux" and LINUX_AVAILABLE:
            caps.update({
                "window_detection": True,
                "fullscreen_detection": True,
                "window_geometry": True,
                "app_classification": False,
                "precise_coordinates": False
            })
        elif self.os_type == "Darwin" and MACOS_AVAILABLE:  # macOS
            caps.update({
                "window_detection": True,
                "fullscreen_detection": False,
                "window_geometry": False,
                "app_classification": False,
                "precise_coordinates": False
            })

        return caps

    def get_current_app(self, use_cache: bool = True) -> Optional[AppInfo]:
        """Récupère l'application actuellement au premier plan avec coordonnées précises"""
        current_time = time.time()

        # Utilise le cache si disponible et récent
        if (use_cache and self.cached_app and
                current_time - self.last_detection_time < self.cache_duration):
            return self.cached_app

        try:
            app_info = None

            if self.os_type == "Windows":
                app_info = self._get_windows_app_improved()
            elif self.os_type == "Linux":
                app_info = self._get_linux_app()
            elif self.os_type == "Darwin":
                app_info = self._get_macos_app()

            if app_info:
                # Enrichit les informations
                app_info = self._enrich_app_info(app_info)

                # Met à jour le cache
                self.cached_app = app_info
                self.last_detection_time = current_time

                # Met à jour l'historique
                self._update_history(app_info)

            return app_info

        except Exception as e:
            self.logger.error(f"Erreur détection application: {e}")
            return None

    def _get_windows_app_improved(self) -> Optional[AppInfo]:
        """Récupère l'application Windows au premier plan avec coordonnées améliorées"""
        if not WINDOWS_AVAILABLE:
            return None

        try:
            # Récupère la fenêtre au premier plan
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            # Titre de la fenêtre
            window_title = win32gui.GetWindowText(hwnd)

            # Classe de la fenêtre
            window_class = win32gui.GetClassName(hwnd)

            # PID du processus
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # Informations du processus
            try:
                process = psutil.Process(pid)
                app_name = process.name()
                executable_path = process.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "Unknown"
                executable_path = ""

            # COORDONNÉES AMÉLIORÉES
            window_rect = self._get_precise_window_coordinates(hwnd)

            # Détection plein écran améliorée
            is_fullscreen = self._is_window_fullscreen(hwnd, window_rect)

            return AppInfo(
                name=app_name,
                pid=pid,
                window_title=window_title,
                executable_path=executable_path,
                is_fullscreen=is_fullscreen,
                window_rect=window_rect,
                window_handle=hwnd,
                window_class=window_class
            )

        except Exception as e:
            self.logger.error(f"Erreur détection Windows améliorée: {e}")
            return None

    def _get_precise_window_coordinates(self, hwnd: int) -> Tuple[int, int, int, int]:
        """Obtient les coordonnées précises d'une fenêtre Windows"""
        try:
            # Méthode 1: GetWindowRect (coordonnées écran)
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y

            # Méthode 2: Vérification avec GetClientRect pour la zone cliente
            client_rect = win32gui.GetClientRect(hwnd)
            client_width = client_rect[2] - client_rect[0]
            client_height = client_rect[3] - client_rect[1]

            # Calcul des bordures de fenêtre
            border_width = (width - client_width) // 2
            title_height = height - client_height - border_width

            # Ajuste selon le style de fenêtre
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

            # Fenêtre sans bordure (applications fullscreen, jeux)
            if not (style & win32con.WS_BORDER) or (style & win32con.WS_POPUP):
                self.logger.debug(f"Fenêtre sans bordure détectée: {win32gui.GetWindowText(hwnd)}")
                return (x, y, width, height)

            # Fenêtre maximisée - coordonnées spéciales
            if style & win32con.WS_MAXIMIZE:
                # Windows ajoute des bordures invisibles quand maximisé
                invisible_border = 8  # pixels typiques Windows 10/11
                return (x + invisible_border, y, width - 2 * invisible_border, height - invisible_border)

            # Fenêtre normale avec bordures et titre
            if style & win32con.WS_CAPTION:
                # Utilise les coordonnées de la zone cliente
                client_point = (0, 0)
                try:
                    # Convertit les coordonnées client en coordonnées écran
                    screen_point = win32gui.ClientToScreen(hwnd, client_point)
                    return (screen_point[0], screen_point[1], client_width, client_height)
                except:
                    # Fallback avec estimation des bordures
                    estimated_border = max(border_width, 2)
                    estimated_title = max(title_height, 30)
                    return (x + estimated_border, y + estimated_title,
                            width - 2 * estimated_border, height - estimated_title - estimated_border)

            # Par défaut, retourne les coordonnées brutes
            return (x, y, width, height)

        except Exception as e:
            self.logger.error(f"Erreur coordonnées précises: {e}")
            # Fallback sur GetWindowRect basique
            try:
                rect = win32gui.GetWindowRect(hwnd)
                return (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
            except:
                return (0, 0, 800, 600)  # Fallback par défaut

    def _is_window_fullscreen(self, hwnd: int, window_rect: Tuple[int, int, int, int]) -> bool:
        """Détection améliorée du mode plein écran"""
        try:
            x, y, width, height = window_rect

            # Obtient les dimensions de l'écran principal
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

            # Obtient les informations de l'écran où se trouve la fenêtre
            monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            monitor_info = win32api.GetMonitorInfo(monitor)
            monitor_rect = monitor_info['Monitor']
            monitor_width = monitor_rect[2] - monitor_rect[0]
            monitor_height = monitor_rect[3] - monitor_rect[1]

            # Vérifie si la fenêtre couvre tout l'écran (avec tolérance)
            tolerance = 10  # pixels de tolérance

            covers_width = width >= monitor_width - tolerance
            covers_height = height >= monitor_height - tolerance

            # Position proche des bords de l'écran
            near_left = abs(x - monitor_rect[0]) <= tolerance
            near_top = abs(y - monitor_rect[1]) <= tolerance

            # Style de fenêtre sans bordure
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            is_popup = bool(style & win32con.WS_POPUP)
            has_no_border = not bool(style & win32con.WS_BORDER)

            # Combine les critères
            size_match = covers_width and covers_height
            position_match = near_left and near_top
            style_match = is_popup or has_no_border

            is_fullscreen = size_match and (position_match or style_match)

            if is_fullscreen:
                self.logger.debug(f"Plein écran détecté: {win32gui.GetWindowText(hwnd)} - {width}x{height}")

            return is_fullscreen

        except Exception as e:
            self.logger.error(f"Erreur détection plein écran: {e}")
            # Fallback simple
            x, y, width, height = window_rect
            return width > 1800 and height > 1000 and x <= 10 and y <= 10

    def _get_linux_app(self) -> Optional[AppInfo]:
        """Récupère l'application Linux au premier plan"""
        try:
            # Utilise xdotool pour récupérer la fenêtre active
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode != 0:
                return None

            window_id = result.stdout.strip()

            # Récupère le PID de la fenêtre
            pid_result = subprocess.run(
                ['xdotool', 'getwindowpid', window_id],
                capture_output=True,
                text=True,
                timeout=2
            )

            if pid_result.returncode != 0:
                return None

            pid = int(pid_result.stdout.strip())

            # Récupère le titre de la fenêtre
            title_result = subprocess.run(
                ['xdotool', 'getwindowname', window_id],
                capture_output=True,
                text=True,
                timeout=2
            )

            window_title = title_result.stdout.strip() if title_result.returncode == 0 else ""

            # Informations du processus
            try:
                process = psutil.Process(pid)
                app_name = process.name()
                executable_path = process.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "Unknown"
                executable_path = ""

            # Géométrie de la fenêtre
            geom_result = subprocess.run(
                ['xdotool', 'getwindowgeometry', window_id],
                capture_output=True,
                text=True,
                timeout=2
            )

            window_rect = (0, 0, 0, 0)
            is_fullscreen = False

            if geom_result.returncode == 0:
                # Parse la géométrie (format: "Geometry: WIDTHxHEIGHT+X+Y")
                lines = geom_result.stdout.strip().split('\n')
                for line in lines:
                    if 'Geometry:' in line:
                        geom_part = line.split('Geometry:')[1].strip()
                        # Extraction basique des dimensions
                        try:
                            if 'x' in geom_part and '+' in geom_part:
                                size_part = geom_part.split('+')[0]
                                width, height = map(int, size_part.split('x'))

                                # Détection plein écran approximative
                                if width > 1800 and height > 1000:
                                    is_fullscreen = True

                                window_rect = (0, 0, width, height)
                        except:
                            pass

            return AppInfo(
                name=app_name,
                pid=pid,
                window_title=window_title,
                executable_path=executable_path,
                is_fullscreen=is_fullscreen,
                window_rect=window_rect
            )

        except Exception as e:
            self.logger.error(f"Erreur détection Linux: {e}")
            return None

    def _get_macos_app(self) -> Optional[AppInfo]:
        """Récupère l'application macOS au premier plan"""
        try:
            # Utilise AppleScript pour récupérer l'app active
            script = '''
                tell application "System Events"
                    set frontApp to first application process whose frontmost is true
                    set appName to name of frontApp
                    set appPID to unix id of frontApp
                    return appName & "|" & appPID
                end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            app_data = result.stdout.strip().split('|')
            if len(app_data) != 2:
                return None

            app_name = app_data[0]
            pid = int(app_data[1])

            # Récupère le titre de la fenêtre (si possible)
            window_title = app_name  # Par défaut

            # Informations du processus
            try:
                process = psutil.Process(pid)
                executable_path = process.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                executable_path = ""

            return AppInfo(
                name=app_name,
                pid=pid,
                window_title=window_title,
                executable_path=executable_path,
                is_fullscreen=False,  # Difficile à détecter sur macOS
                window_rect=(0, 0, 0, 0)
            )

        except Exception as e:
            self.logger.error(f"Erreur détection macOS: {e}")
            return None

    def _enrich_app_info(self, app_info: AppInfo) -> AppInfo:
        """Enrichit les informations de l'application"""
        try:
            # Détection du type d'application
            app_name_lower = app_info.name.lower()
            executable_lower = app_info.executable_path.lower()
            title_lower = app_info.window_title.lower()

            # Détection des jeux améliorée
            game_indicators = [
                'game', 'steam', 'unity', 'unreal', 'gameoverlay',
                'origin', 'uplay', 'epicgames', 'gog', 'minecraft',
                'directx', 'opengl', 'vulkan', '.exe'
            ]

            # Indicateurs spécifiques dans le titre
            game_title_indicators = [
                'game', 'level', 'score', 'player', 'fps'
            ]

            app_info.is_game = any(indicator in app_name_lower or indicator in executable_lower
                                   for indicator in game_indicators)

            if not app_info.is_game:
                app_info.is_game = any(indicator in title_lower for indicator in game_title_indicators)

            # Détection des navigateurs améliorée
            browser_indicators = [
                'chrome', 'firefox', 'safari', 'edge', 'opera', 'brave',
                'webkit', 'browser', 'msedge', 'chromium'
            ]
            app_info.is_browser = any(indicator in app_name_lower or indicator in executable_lower
                                      for indicator in browser_indicators)

            # Log du type détecté
            if app_info.is_game:
                self.logger.debug(f"Jeu détecté: {app_info.name}")
            elif app_info.is_browser:
                self.logger.debug(f"Navigateur détecté: {app_info.name}")

        except Exception as e:
            self.logger.error(f"Erreur enrichissement app info: {e}")

        return app_info

    def _update_history(self, app_info: AppInfo):
        """Met à jour l'historique des applications"""
        # Évite les doublons consécutifs
        if not self.app_history or self.app_history[-1].name != app_info.name:
            self.app_history.append(app_info)

            # Limite la taille de l'historique
            if len(self.app_history) > 50:
                self.app_history = self.app_history[-25:]

    def add_update_callback(self, callback: Callable[[AppInfo], None]):
        """Ajoute un callback appelé lors des changements d'application"""
        self.update_callbacks.append(callback)

    def start_monitoring(self, interval: float = 1.0):
        """Démarre la surveillance continue des applications"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True,
            name="AppMonitor"
        )
        self.monitor_thread.start()
        self.logger.info("Surveillance des applications démarrée")

    def stop_monitoring(self):
        """Arrête la surveillance des applications"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=3.0)
        self.logger.info("Surveillance des applications arrêtée")

    def _monitor_loop(self, interval: float):
        """Boucle de surveillance des applications"""
        last_app_name = None

        while self.monitoring:
            try:
                current_app = self.get_current_app(use_cache=False)

                if current_app and current_app.name != last_app_name:
                    self.current_app = current_app
                    last_app_name = current_app.name

                    # Log des informations détaillées
                    self.logger.debug(f"App changée: {current_app.name} - "
                                      f"Fenêtre: {current_app.window_rect} - "
                                      f"Plein écran: {current_app.is_fullscreen}")

                    # Notifie les callbacks
                    for callback in self.update_callbacks:
                        try:
                            callback(current_app)
                        except Exception as e:
                            self.logger.error(f"Erreur callback: {e}")

                time.sleep(interval)

            except Exception as e:
                self.logger.error(f"Erreur surveillance: {e}")
                time.sleep(interval)

    def get_app_list(self) -> List[str]:
        """Récupère la liste des applications en cours d'exécution"""
        try:
            apps = []
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    app_name = proc.info['name']
                    if app_name and app_name not in apps:
                        apps.append(app_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return sorted(apps)

        except Exception as e:
            self.logger.error(f"Erreur liste applications: {e}")
            return []

    def get_history(self) -> List[AppInfo]:
        """Récupère l'historique des applications"""
        return self.app_history.copy()

    def clear_history(self):
        """Vide l'historique des applications"""
        self.app_history.clear()

    def get_capabilities(self) -> Dict[str, bool]:
        """Retourne les capacités de détection disponibles"""
        return self.capabilities.copy()

    def get_window_by_pid(self, pid: int) -> Optional[AppInfo]:
        """Récupère les informations de fenêtre pour un PID spécifique"""
        if not WINDOWS_AVAILABLE:
            return None

        try:
            # Trouve toutes les fenêtres du processus
            windows = []

            def enum_windows_proc(hwnd, lParam):
                try:
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid == pid and win32gui.IsWindowVisible(hwnd):
                        windows.append(hwnd)
                except:
                    pass
                return True

            win32gui.EnumWindows(enum_windows_proc, 0)

            if not windows:
                return None

            # Prend la fenêtre principale (la plus grande)
            main_hwnd = max(windows, key=lambda hwnd: self._get_window_size(hwnd))

            # Construit AppInfo
            window_title = win32gui.GetWindowText(main_hwnd)
            window_class = win32gui.GetClassName(main_hwnd)

            try:
                process = psutil.Process(pid)
                app_name = process.name()
                executable_path = process.exe()
            except:
                app_name = "Unknown"
                executable_path = ""

            window_rect = self._get_precise_window_coordinates(main_hwnd)
            is_fullscreen = self._is_window_fullscreen(main_hwnd, window_rect)

            app_info = AppInfo(
                name=app_name,
                pid=pid,
                window_title=window_title,
                executable_path=executable_path,
                is_fullscreen=is_fullscreen,
                window_rect=window_rect,
                window_handle=main_hwnd,
                window_class=window_class
            )

            return self._enrich_app_info(app_info)

        except Exception as e:
            self.logger.error(f"Erreur récupération fenêtre par PID {pid}: {e}")
            return None

    def _get_window_size(self, hwnd: int) -> int:
        """Retourne la taille d'une fenêtre"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return (rect[2] - rect[0]) * (rect[3] - rect[1])
        except:
            return 0