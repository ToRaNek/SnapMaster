# gui/main_window.py
"""
Interface graphique principale pour SnapMaster
Fenêtre principale avec tous les contrôles et paramètres
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import sys
import os

# Imports des modules SnapMaster
from config.settings import SettingsManager
from core.memory_manager import MemoryManager
from core.screenshot_manager import ScreenshotManager
from core.hotkey_manager import HotkeyManager
from core.app_detector import AppDetector, AppInfo
import time

# Import conditionnel pour éviter les erreurs circulaires
SettingsWindow = None

class SnapMasterGUI:
    """Interface graphique principale de SnapMaster"""
    
    def __init__(self, settings_manager: SettingsManager, memory_manager: MemoryManager):
        self.logger = logging.getLogger(__name__)
        self.settings = settings_manager
        self.memory_manager = memory_manager
        
        # Initialisation des gestionnaires
        self.screenshot_manager = ScreenshotManager(settings_manager, memory_manager)
        self.hotkey_manager = HotkeyManager(settings_manager)
        self.app_detector = AppDetector()
        
        # Variables d'état
        self.current_app: Optional[AppInfo] = None
        self.monitoring_active = False
        
        # Interface utilisateur
        self.root: Optional[tk.Tk] = None
        self.settings_window: Optional[SettingsWindow] = None
        
        # Widgets principaux
        self.status_label: Optional[tk.Label] = None
        self.app_label: Optional[tk.Label] = None
        self.memory_label: Optional[tk.Label] = None
        self.stats_frame: Optional[tk.Frame] = None
        
        # Thread de mise à jour de l'interface
        self.ui_update_thread: Optional[threading.Thread] = None
        self.ui_update_running = False
        
        self.logger.info("SnapMasterGUI initialisé")
    
    def run(self):
        """Lance l'interface graphique"""
        try:
            self._create_main_window()
            self._setup_callbacks()
            self._start_services()
            self._start_ui_updates()
            
            self.logger.info("Interface graphique démarrée")
            self.root.mainloop()
            
        except Exception as e:
            self.logger.error(f"Erreur lancement GUI: {e}")
            self._show_error("Erreur de démarrage", str(e))
        finally:
            self._cleanup()
    
    def _create_main_window(self):
        """Crée la fenêtre principale"""
        self.root = tk.Tk()
        self.root.title("SnapMaster - Capture d'écran avancée")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Configuration du style
        style = ttk.Style()
        if self.settings.get_ui_settings().get('theme') == 'dark':
            self._apply_dark_theme(style)
        
        # Icône (si disponible)
        self._set_window_icon()
        
        # Création des widgets
        self._create_menu_bar()
        self._create_main_frame()
        self._create_status_bar()
        
        # Gestionnaire de fermeture
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Centre la fenêtre
        self._center_window()
    
    def _apply_dark_theme(self, style: ttk.Style):
        """Applique le thème sombre"""
        try:
            style.theme_use('clam')
            style.configure('.', background='#2e2e2e', foreground='white')
            style.configure('TLabel', background='#2e2e2e', foreground='white')
            style.configure('TButton', background='#404040', foreground='white')
            style.configure('TFrame', background='#2e2e2e')
            style.configure('TNotebook', background='#2e2e2e')
            style.configure('TNotebook.Tab', background='#404040', foreground='white')
        except Exception as e:
            self.logger.warning(f"Impossible d'appliquer le thème sombre: {e}")
    
    def _set_window_icon(self):
        """Définit l'icône de la fenêtre"""
        try:
            icon_path = Path("assets/icon.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass  # Ignore si pas d'icône
    
    def _create_menu_bar(self):
        """Crée la barre de menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Ouvrir dossier captures", command=self._open_screenshots_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exporter configuration", command=self._export_config)
        file_menu.add_command(label="Importer configuration", command=self._import_config)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self._on_window_close)
        
        # Menu Capture
        capture_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Capture", menu=capture_menu)
        capture_menu.add_command(label="Plein écran", command=self._capture_fullscreen)
        capture_menu.add_command(label="Fenêtre active", command=self._capture_active_window)
        capture_menu.add_command(label="Zone sélectionnée", command=self._capture_area)
        capture_menu.add_separator()
        capture_menu.add_command(label="Test des capacités", command=self._test_capabilities)
        
        # Menu Outils
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Outils", menu=tools_menu)
        tools_menu.add_command(label="Paramètres", command=self._open_settings)
        tools_menu.add_command(label="Gestionnaire de dossiers", command=self._open_folder_manager)
        tools_menu.add_separator()
        tools_menu.add_command(label="Nettoyage mémoire", command=self._force_memory_cleanup)
        tools_menu.add_command(label="Statistiques", command=self._show_statistics)
        
        # Menu Aide
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="Raccourcis clavier", command=self._show_hotkeys)
        help_menu.add_command(label="À propos", command=self._show_about)
    
    def _create_main_frame(self):
        """Crée le frame principal avec onglets"""
        # Notebook pour les onglets
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Onglet Capture
        self._create_capture_tab(notebook)
        
        # Onglet Applications
        self._create_apps_tab(notebook)
        
        # Onglet Surveillance
        self._create_monitoring_tab(notebook)
    
    def _create_capture_tab(self, parent):
        """Crée l'onglet de capture"""
        capture_frame = ttk.Frame(parent)
        parent.add(capture_frame, text="Capture")
        
        # Section boutons de capture
        buttons_frame = ttk.LabelFrame(capture_frame, text="Actions de capture")
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Boutons principaux
        btn_frame = ttk.Frame(buttons_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="📱 Plein écran", 
                  command=self._capture_fullscreen, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🪟 Fenêtre active", 
                  command=self._capture_active_window, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✂️ Zone sélectionnée", 
                  command=self._capture_area, width=20).pack(side=tk.LEFT, padx=5)
        
        # Section paramètres rapides
        quick_settings_frame = ttk.LabelFrame(capture_frame, text="Paramètres rapides")
        quick_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Format d'image
        format_frame = ttk.Frame(quick_settings_frame)
        format_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(format_frame, text="Format:").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value=self.settings.get_capture_settings().get('image_format', 'PNG'))
        format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, 
                                   values=['PNG', 'JPEG', 'BMP'], state='readonly', width=10)
        format_combo.pack(side=tk.LEFT, padx=5)
        format_combo.bind('<<ComboboxSelected>>', self._on_format_change)
        
        # Qualité
        quality_frame = ttk.Frame(quick_settings_frame)
        quality_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(quality_frame, text="Qualité:").pack(side=tk.LEFT)
        self.quality_var = tk.IntVar(value=self.settings.get_capture_settings().get('image_quality', 95))
        quality_scale = ttk.Scale(quality_frame, from_=10, to=100, variable=self.quality_var, 
                                 orient=tk.HORIZONTAL, length=200)
        quality_scale.pack(side=tk.LEFT, padx=5)
        quality_scale.bind('<ButtonRelease-1>', self._on_quality_change)
        
        self.quality_label = ttk.Label(quality_frame, text=f"{self.quality_var.get()}%")
        self.quality_label.pack(side=tk.LEFT, padx=5)
        
        # Section dossier de destination
        folder_frame = ttk.LabelFrame(capture_frame, text="Dossier de destination")
        folder_frame.pack(fill=tk.X, padx=10, pady=5)
        
        folder_select_frame = ttk.Frame(folder_frame)
        folder_select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.folder_var = tk.StringVar(value=self.settings.get_default_folder())
        folder_entry = ttk.Entry(folder_select_frame, textvariable=self.folder_var, state='readonly')
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(folder_select_frame, text="Parcourir", 
                  command=self._browse_folder).pack(side=tk.RIGHT)
        
        # Liste des dossiers personnalisés
        custom_folders_frame = ttk.Frame(folder_frame)
        custom_folders_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(custom_folders_frame, text="Dossiers personnalisés:").pack(anchor=tk.W)
        
        self.folders_listbox = tk.Listbox(custom_folders_frame, height=3)
        self.folders_listbox.pack(fill=tk.X, pady=2)
        self.folders_listbox.bind('<Double-1>', self._select_custom_folder)
        
        self._update_folders_list()
    
    def _create_apps_tab(self, parent):
        """Crée l'onglet des applications"""
        apps_frame = ttk.Frame(parent)
        parent.add(apps_frame, text="Applications")
        
        # Application actuelle
        current_app_frame = ttk.LabelFrame(apps_frame, text="Application actuelle")
        current_app_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.app_label = ttk.Label(current_app_frame, text="Aucune application détectée", 
                                  font=('Arial', 12, 'bold'))
        self.app_label.pack(padx=10, pady=5)
        
        app_details_frame = ttk.Frame(current_app_frame)
        app_details_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.app_details_label = ttk.Label(app_details_frame, text="", font=('Arial', 9))
        self.app_details_label.pack(anchor=tk.W)
        
        # Bouton capture directe
        direct_capture_frame = ttk.Frame(current_app_frame)
        direct_capture_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.direct_capture_btn = ttk.Button(direct_capture_frame, 
                                           text="📸 Capturer cette application", 
                                           command=self._capture_current_app,
                                           state=tk.DISABLED)
        self.direct_capture_btn.pack(side=tk.LEFT)
        
        # Associations application/dossier
        associations_frame = ttk.LabelFrame(apps_frame, text="Associations application → dossier")
        associations_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Liste des associations
        assoc_list_frame = ttk.Frame(associations_frame)
        assoc_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview pour les associations
        columns = ('app', 'folder')
        self.associations_tree = ttk.Treeview(assoc_list_frame, columns=columns, show='headings', height=6)
        self.associations_tree.heading('app', text='Application')
        self.associations_tree.heading('folder', text='Dossier')
        self.associations_tree.column('app', width=200)
        self.associations_tree.column('folder', width=300)
        
        assoc_scrollbar = ttk.Scrollbar(assoc_list_frame, orient=tk.VERTICAL, command=self.associations_tree.yview)
        self.associations_tree.configure(yscrollcommand=assoc_scrollbar.set)
        
        self.associations_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        assoc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Boutons de gestion des associations
        assoc_buttons_frame = ttk.Frame(associations_frame)
        assoc_buttons_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(assoc_buttons_frame, text="➕ Ajouter", 
                  command=self._add_association).pack(side=tk.LEFT, padx=2)
        ttk.Button(assoc_buttons_frame, text="✏️ Modifier", 
                  command=self._edit_association).pack(side=tk.LEFT, padx=2)
        ttk.Button(assoc_buttons_frame, text="🗑️ Supprimer", 
                  command=self._remove_association).pack(side=tk.LEFT, padx=2)
        
        self._update_associations_list()
    
    def _create_monitoring_tab(self, parent):
        """Crée l'onglet de surveillance"""
        monitoring_frame = ttk.Frame(parent)
        parent.add(monitoring_frame, text="Surveillance")
        
        # État de la surveillance
        status_frame = ttk.LabelFrame(monitoring_frame, text="État du système")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="🔴 Services arrêtés", 
                                     font=('Arial', 12, 'bold'))
        self.status_label.pack(padx=10, pady=5)
        
        # Informations mémoire
        memory_frame = ttk.LabelFrame(monitoring_frame, text="Utilisation mémoire")
        memory_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.memory_label = ttk.Label(memory_frame, text="Mémoire: -- MB")
        self.memory_label.pack(padx=10, pady=5)
        
        memory_buttons_frame = ttk.Frame(memory_frame)
        memory_buttons_frame.pack(fill=tk.X, padx=10, pady=2)
        
        ttk.Button(memory_buttons_frame, text="🧹 Nettoyer maintenant", 
                  command=self._force_memory_cleanup).pack(side=tk.LEFT, padx=5)
        ttk.Button(memory_buttons_frame, text="📊 Statistiques détaillées", 
                  command=self._show_memory_stats).pack(side=tk.LEFT, padx=5)
        
        # Raccourcis clavier actifs
        hotkeys_frame = ttk.LabelFrame(monitoring_frame, text="Raccourcis clavier")
        hotkeys_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.hotkeys_text = tk.Text(hotkeys_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        hotkeys_scrollbar = ttk.Scrollbar(hotkeys_frame, orient=tk.VERTICAL, command=self.hotkeys_text.yview)
        self.hotkeys_text.configure(yscrollcommand=hotkeys_scrollbar.set)
        
        self.hotkeys_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        hotkeys_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        self._update_hotkeys_display()
    
    def _create_status_bar(self):
        """Crée la barre de statut"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_text = tk.StringVar(value="Prêt")
        ttk.Label(status_frame, textvariable=self.status_text).pack(side=tk.LEFT, padx=5)
        
        # Indicateur de surveillance
        self.monitoring_indicator = ttk.Label(status_frame, text="🔴")
        self.monitoring_indicator.pack(side=tk.RIGHT, padx=5)
    
    def _setup_callbacks(self):
        """Configure les callbacks des différents gestionnaires"""
        # Callbacks du gestionnaire de captures
        self.screenshot_manager.add_capture_callback(self._on_capture_complete)
        self.screenshot_manager.add_error_callback(self._on_capture_error)
        
        # Callbacks du détecteur d'applications
        self.app_detector.add_update_callback(self._on_app_change)
        
        # Callbacks des hotkeys
        self.hotkey_manager.add_action_callback('fullscreen_capture', self._capture_fullscreen)
        self.hotkey_manager.add_action_callback('window_capture', self._capture_active_window)
        self.hotkey_manager.add_action_callback('area_capture', self._capture_area)
        self.hotkey_manager.add_action_callback('quick_capture', self._capture_current_app)
    
    def _start_services(self):
        """Démarre tous les services"""
        try:
            # Démarre la détection d'applications
            self.app_detector.start_monitoring(interval=2.0)
            
            # Démarre les hotkeys
            if self.hotkey_manager.start_monitoring():
                self.logger.info("Hotkeys activés")
            else:
                self.logger.warning("Impossible d'activer les hotkeys")
            
            self.monitoring_active = True
            self._update_status("🟢 Services actifs")
            
        except Exception as e:
            self.logger.error(f"Erreur démarrage services: {e}")
            self._update_status("🔴 Erreur services")
    
    def _start_ui_updates(self):
        """Démarre les mises à jour périodiques de l'interface"""
        self.ui_update_running = True
        self.ui_update_thread = threading.Thread(target=self._ui_update_loop, daemon=True)
        self.ui_update_thread.start()
    
    def _ui_update_loop(self):
        """Boucle de mise à jour de l'interface"""
        while self.ui_update_running:
            try:
                # Met à jour les informations mémoire
                memory_usage = self.memory_manager.get_current_memory_usage()
                self.root.after(0, self._update_memory_display, memory_usage)
                
                # Met à jour l'application actuelle
                current_app = self.app_detector.current_app
                if current_app != self.current_app:
                    self.current_app = current_app
                    self.root.after(0, self._update_current_app_display, current_app)
                
                time.sleep(5)  # Mise à jour toutes les 5 secondes
                
            except Exception as e:
                self.logger.error(f"Erreur mise à jour UI: {e}")
                time.sleep(5)
    
    # Méthodes de callback
    def _on_capture_complete(self, capture_type: str, save_path: str, app_info: Optional[AppInfo] = None):
        """Callback appelé après une capture réussie"""
        def update_ui():
            message = f"Capture {capture_type} sauvegardée: {Path(save_path).name}"
            self._update_status(message)
            
            if self.settings.get_ui_settings().get('show_notifications', True):
                self._show_notification("Capture réussie", message)
        
        self.root.after(0, update_ui)
    
    def _on_capture_error(self, capture_type: str, error_message: str):
        """Callback appelé en cas d'erreur de capture"""
        def update_ui():
            message = f"Erreur capture {capture_type}: {error_message}"
            self._update_status(message)
            self._show_error("Erreur de capture", error_message)
        
        self.root.after(0, update_ui)
    
    def _on_app_change(self, app_info: AppInfo):
        """Callback appelé lors du changement d'application"""
        self.current_app = app_info
        self.root.after(0, self._update_current_app_display, app_info)
    
    # Méthodes de capture
    def _capture_fullscreen(self):
        """Lance une capture plein écran"""
        def capture():
            self._update_status("📱 Capture plein écran en cours...")
            self.screenshot_manager.capture_fullscreen()
        
        threading.Thread(target=capture, daemon=True).start()
    
    def _capture_active_window(self):
        """Lance une capture de la fenêtre active"""
        def capture():
            self._update_status("🪟 Capture fenêtre active en cours...")
            self.screenshot_manager.capture_active_window()
        
        threading.Thread(target=capture, daemon=True).start()
    
    def _capture_area(self):
        """Lance une capture de zone sélectionnée"""
        def capture():
            self._update_status("✂️ Sélectionnez la zone à capturer...")
            self.screenshot_manager.capture_area_selection()
        
        threading.Thread(target=capture, daemon=True).start()
    
    def _capture_current_app(self):
        """Lance une capture de l'application actuelle"""
        if not self.current_app:
            self._show_warning("Aucune application", "Aucune application détectée")
            return
        
        def capture():
            self._update_status(f"📸 Capture de {self.current_app.name}...")
            self.screenshot_manager.capture_app_direct(self.current_app.name)
        
        threading.Thread(target=capture, daemon=True).start()
    
    # Méthodes utilitaires UI
    def _update_status(self, message: str):
        """Met à jour le message de statut"""
        if self.status_text:
            self.status_text.set(message)
    
    def _update_memory_display(self, memory_mb: float):
        """Met à jour l'affichage de la mémoire"""
        if self.memory_label:
            color = "red" if memory_mb > 400 else "orange" if memory_mb > 200 else "green"
            self.memory_label.config(text=f"Mémoire: {memory_mb:.1f} MB", foreground=color)
    
    def _update_current_app_display(self, app_info: Optional[AppInfo]):
        """Met à jour l'affichage de l'application actuelle"""
        if not self.app_label:
            return
        
        if app_info:
            self.app_label.config(text=f"🎯 {app_info.name}")
            
            details = f"Titre: {app_info.window_title}\n"
            details += f"PID: {app_info.pid}\n"
            details += f"Plein écran: {'Oui' if app_info.is_fullscreen else 'Non'}\n"
            details += f"Type: {'Jeu' if app_info.is_game else 'Navigateur' if app_info.is_browser else 'Application'}"
            
            if self.app_details_label:
                self.app_details_label.config(text=details)
            
            if self.direct_capture_btn:
                self.direct_capture_btn.config(state=tk.NORMAL)
        else:
            self.app_label.config(text="Aucune application détectée")
            if self.app_details_label:
                self.app_details_label.config(text="")
            if self.direct_capture_btn:
                self.direct_capture_btn.config(state=tk.DISABLED)
    
    def _show_notification(self, title: str, message: str):
        """Affiche une notification"""
        try:
            # Utilise la notification système si disponible
            if sys.platform == "win32":
                import win32api
                win32api.MessageBox(0, message, title, 0x40)  # INFO
        except:
            # Fallback vers messagebox tkinter
            messagebox.showinfo(title, message)
    
    def _show_error(self, title: str, message: str):
        """Affiche une erreur"""
        messagebox.showerror(title, message)
    
    def _show_warning(self, title: str, message: str):
        """Affiche un avertissement"""
        messagebox.showwarning(title, message)
    
    def _center_window(self):
        """Centre la fenêtre sur l'écran"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _cleanup(self):
        """Nettoyage lors de la fermeture"""
        try:
            self.ui_update_running = False
            
            if self.hotkey_manager:
                self.hotkey_manager.stop_monitoring()
            
            if self.app_detector:
                self.app_detector.stop_monitoring()
            
            if self.memory_manager:
                self.memory_manager.force_cleanup()
            
            self.logger.info("Nettoyage terminé")
        except Exception as e:
            self.logger.error(f"Erreur nettoyage: {e}")
    
    def _on_window_close(self):
        """Gestionnaire de fermeture de fenêtre"""
        if messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter SnapMaster?"):
            self._cleanup()
            self.root.destroy()

# Méthodes à implémenter (stubs pour éviter les erreurs)
    def _open_screenshots_folder(self): pass
    def _export_config(self): pass
    def _import_config(self): pass
    def _test_capabilities(self): pass
    def _open_settings(self): pass
    def _open_folder_manager(self): pass
    def _force_memory_cleanup(self): pass
    def _show_statistics(self): pass
    def _show_hotkeys(self): pass
    def _show_about(self): pass
    def _on_format_change(self, event): pass
    def _on_quality_change(self, event): pass
    def _browse_folder(self): pass
    def _select_custom_folder(self, event): pass
    def _update_folders_list(self): pass
    def _add_association(self): pass
    def _edit_association(self): pass
    def _remove_association(self): pass
    def _update_associations_list(self): pass
    def _show_memory_stats(self): pass
    def _update_hotkeys_display(self): pass