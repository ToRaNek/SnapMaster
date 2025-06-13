# gui/main_window.py
"""
Interface graphique principale pour SnapMaster avec thème bleu moderne
Fenêtre principale avec tous les contrôles et paramètres - Version avec associations améliorées
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import sys
import os
import psutil
import subprocess
import platform

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
    """Interface graphique principale de SnapMaster avec thème bleu moderne"""

    def __init__(self, settings_manager: SettingsManager, memory_manager: MemoryManager):
        self.logger = logging.getLogger(__name__)
        self.settings = settings_manager
        self.memory_manager = memory_manager

        # Palette de couleurs bleues modernes
        self.colors = {
            # Bleus principaux
            'primary_blue': '#1e3a8a',      # Bleu profond
            'secondary_blue': '#3b82f6',    # Bleu vif
            'light_blue': '#60a5fa',        # Bleu clair
            'accent_blue': '#0ea5e9',       # Bleu accent
            'sky_blue': '#0284c7',          # Bleu ciel

            # Arrière-plans
            'bg_dark': '#0f1419',           # Fond sombre
            'bg_medium': '#1a202c',         # Fond moyen
            'bg_light': '#2d3748',          # Fond clair
            'bg_card': '#374151',           # Fond carte

            # Textes
            'text_primary': '#ffffff',      # Texte principal
            'text_secondary': '#e2e8f0',    # Texte secondaire
            'text_muted': '#94a3b8',        # Texte atténué

            # États
            'success': '#10b981',           # Succès vert
            'warning': '#f59e0b',           # Avertissement orange
            'error': '#ef4444',             # Erreur rouge
            'info': '#06b6d4',              # Info cyan

            # Effets
            'hover': '#4f46e5',             # Survol violet-bleu
            'focus': '#8b5cf6',             # Focus violet
            'border': '#475569',            # Bordure
            'shadow': '#0f172a',            # Ombre
        }

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

        self.logger.info("SnapMasterGUI initialisé avec thème bleu moderne")

    def run(self):
        """Lance l'interface graphique"""
        try:
            self.logger.info("Initialisation de l'interface SnapMaster...")

            # 1. Crée la fenêtre principale
            self._create_main_window()

            # 2. Démarre tous les services (qui configure aussi les callbacks)
            self._start_services()

            # 3. Démarre les mises à jour de l'interface
            self._start_ui_updates()

            self.logger.info("Interface graphique démarrée avec succès")
            self.logger.info("Raccourcis clavier disponibles:")
            active_hotkeys = self.hotkey_manager.get_active_hotkeys()
            for action, hotkey in active_hotkeys.items():
                self.logger.info(f"  • {action.replace('_', ' ').title()}: {hotkey}")

            # 4. Lance la boucle principale
            self.root.mainloop()

        except Exception as e:
            self.logger.error(f"Erreur lancement GUI: {e}")
            self._show_error("Erreur de démarrage",
                             f"Une erreur critique s'est produite:\n{str(e)}")
        finally:
            self._cleanup()

    def _create_main_window(self):
        """Crée la fenêtre principale avec thème bleu moderne"""
        self.root = tk.Tk()
        self.root.title("🎯 SnapMaster - Capture d'écran avancée")
        self.root.geometry("900x700")
        self.root.minsize(700, 500)

        # Fond principal bleu dégradé
        self.root.configure(bg=self.colors['bg_dark'])

        # Configuration du style moderne
        self.style = ttk.Style()
        self._apply_modern_blue_theme()

        # Icône (si disponible)
        self._set_window_icon()

        # Création des widgets
        self._create_menu_bar()
        self._create_header()
        self._create_main_frame()
        self._create_status_bar()

        # Gestionnaire de fermeture
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Centre la fenêtre
        self._center_window()

    def _apply_modern_blue_theme(self):
        """Applique le thème bleu moderne avancé avec coins arrondis"""
        try:
            # Utilise le thème de base
            self.style.theme_use('clam')

            # Configuration générale avec effets arrondis
            self.style.configure('.',
                                 background=self.colors['bg_medium'],
                                 foreground=self.colors['text_primary'],
                                 fieldbackground=self.colors['bg_light'],
                                 bordercolor=self.colors['border'],
                                 focuscolor=self.colors['focus'],
                                 selectbackground=self.colors['secondary_blue'],
                                 selectforeground=self.colors['text_primary'],
                                 relief='flat',
                                 borderwidth=0)

            # Labels avec styles variés
            self.style.configure('TLabel',
                                 background=self.colors['bg_medium'],
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 10),
                                 relief='flat')

            self.style.configure('Header.TLabel',
                                 background=self.colors['primary_blue'],
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 14, 'bold'),
                                 relief='flat',
                                 borderwidth=0)

            self.style.configure('Title.TLabel',
                                 background=self.colors['bg_medium'],
                                 foreground=self.colors['secondary_blue'],
                                 font=('Segoe UI', 12, 'bold'),
                                 relief='flat')

            self.style.configure('Status.TLabel',
                                 background=self.colors['bg_card'],
                                 foreground=self.colors['light_blue'],
                                 font=('Segoe UI', 9),
                                 relief='flat',
                                 borderwidth=0)

            # Boutons modernes avec coins arrondis et dégradés
            self.style.configure('Modern.TButton',
                                 background=self.colors['secondary_blue'],
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 10, 'bold'),
                                 relief='flat',
                                 borderwidth=0,
                                 focuscolor='none',
                                 padding=(15, 8))

            self.style.map('Modern.TButton',
                           background=[('active', self.colors['light_blue']),
                                       ('pressed', self.colors['primary_blue']),
                                       ('disabled', self.colors['bg_light'])])

            # Boutons d'action spéciaux avec effets
            self.style.configure('Action.TButton',
                                 background=self.colors['accent_blue'],
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 11, 'bold'),
                                 relief='flat',
                                 borderwidth=0,
                                 padding=(20, 10))

            self.style.map('Action.TButton',
                           background=[('active', self.colors['sky_blue']),
                                       ('pressed', self.colors['primary_blue'])])

            # Boutons de succès arrondis
            self.style.configure('Success.TButton',
                                 background=self.colors['success'],
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 11, 'bold'),
                                 relief='flat',
                                 borderwidth=0,
                                 padding=(15, 8))

            self.style.map('Success.TButton',
                           background=[('active', '#059669'),
                                       ('pressed', '#047857')])

            # Boutons de gestion avec couleurs distinctes
            self.style.configure('Add.TButton',
                                 background='#10b981',
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 10, 'bold'),
                                 relief='flat',
                                 borderwidth=0,
                                 padding=(12, 6))

            self.style.map('Add.TButton',
                           background=[('active', '#059669'),
                                       ('pressed', '#047857')])

            self.style.configure('Edit.TButton',
                                 background='#f59e0b',
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 10, 'bold'),
                                 relief='flat',
                                 borderwidth=0,
                                 padding=(12, 6))

            self.style.map('Edit.TButton',
                           background=[('active', '#d97706'),
                                       ('pressed', '#b45309')])

            self.style.configure('Delete.TButton',
                                 background='#ef4444',
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 10, 'bold'),
                                 relief='flat',
                                 borderwidth=0,
                                 padding=(12, 6))

            self.style.map('Delete.TButton',
                           background=[('active', '#dc2626'),
                                       ('pressed', '#b91c1c')])

            # Frames avec bordures arrondies
            self.style.configure('TFrame',
                                 background=self.colors['bg_medium'],
                                 relief='flat',
                                 borderwidth=0)

            self.style.configure('Card.TFrame',
                                 background=self.colors['bg_card'],
                                 relief='flat',
                                 borderwidth=1)

            self.style.configure('Highlight.TFrame',
                                 background=self.colors['bg_light'],
                                 relief='flat',
                                 borderwidth=1)

            # LabelFrames modernes avec bordures arrondies
            self.style.configure('TLabelframe',
                                 background=self.colors['bg_medium'],
                                 foreground=self.colors['secondary_blue'],
                                 font=('Segoe UI', 11, 'bold'),
                                 relief='flat',
                                 borderwidth=1,
                                 bordercolor=self.colors['border'])

            self.style.configure('TLabelframe.Label',
                                 background=self.colors['bg_medium'],
                                 foreground=self.colors['light_blue'],
                                 font=('Segoe UI', 11, 'bold'))

            # Notebook (onglets) avec style arrondi
            self.style.configure('TNotebook',
                                 background=self.colors['bg_medium'],
                                 borderwidth=0,
                                 tabposition='n')

            self.style.configure('TNotebook.Tab',
                                 background=self.colors['bg_light'],
                                 foreground=self.colors['text_secondary'],
                                 font=('Segoe UI', 11, 'bold'),
                                 padding=[25, 12],
                                 borderwidth=0)

            self.style.map('TNotebook.Tab',
                           background=[('selected', self.colors['secondary_blue']),
                                       ('active', self.colors['light_blue'])],
                           foreground=[('selected', self.colors['text_primary']),
                                       ('active', self.colors['text_primary'])])

            # Entrées de texte arrondies
            self.style.configure('TEntry',
                                 fieldbackground=self.colors['bg_light'],
                                 background=self.colors['bg_light'],
                                 foreground=self.colors['text_primary'],
                                 bordercolor=self.colors['secondary_blue'],
                                 focuscolor=self.colors['focus'],
                                 insertcolor=self.colors['text_primary'],
                                 font=('Segoe UI', 10),
                                 relief='flat',
                                 borderwidth=2)

            # Combobox arrondie
            self.style.configure('TCombobox',
                                 fieldbackground=self.colors['bg_light'],
                                 background=self.colors['bg_card'],
                                 foreground=self.colors['text_primary'],
                                 bordercolor=self.colors['secondary_blue'],
                                 arrowcolor=self.colors['secondary_blue'],
                                 font=('Segoe UI', 10),
                                 relief='flat',
                                 borderwidth=2)

            # Checkbuttons et Radiobuttons
            self.style.configure('TCheckbutton',
                                 background=self.colors['bg_medium'],
                                 foreground=self.colors['text_primary'],
                                 focuscolor=self.colors['focus'],
                                 font=('Segoe UI', 10))

            # Scales (curseurs) arrondis
            self.style.configure('TScale',
                                 background=self.colors['bg_medium'],
                                 sliderrelief='flat',
                                 borderwidth=0,
                                 troughcolor=self.colors['bg_light'],
                                 darkcolor=self.colors['secondary_blue'],
                                 lightcolor=self.colors['light_blue'])

            # Treeview (listes) avec bordures arrondies
            self.style.configure('Treeview',
                                 background=self.colors['bg_light'],
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 10),
                                 fieldbackground=self.colors['bg_light'],
                                 borderwidth=1,
                                 relief='flat')

            self.style.configure('Treeview.Heading',
                                 background=self.colors['primary_blue'],
                                 foreground=self.colors['text_primary'],
                                 font=('Segoe UI', 11, 'bold'),
                                 relief='flat',
                                 borderwidth=0)

            self.style.map('Treeview.Heading',
                           background=[('active', self.colors['secondary_blue'])])

            # Listbox personnalisé avec bordures arrondies
            self.style.configure('Custom.Listbox',
                                 background=self.colors['bg_light'],
                                 foreground=self.colors['text_primary'],
                                 selectbackground=self.colors['secondary_blue'],
                                 font=('Segoe UI', 10))

        except Exception as e:
            self.logger.warning(f"Impossible d'appliquer le thème bleu: {e}")

    def _create_header(self):
        """Crée un en-tête coloré moderne avec coins arrondis"""
        header_frame = tk.Frame(self.root, bg=self.colors['primary_blue'], height=90)
        header_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        header_frame.pack_propagate(False)

        # Container interne avec effet d'arrondi
        inner_header = tk.Frame(header_frame, bg=self.colors['primary_blue'])
        inner_header.pack(expand=True, fill=tk.BOTH, padx=8, pady=8)

        # Titre principal avec gradient effet
        title_frame = tk.Frame(inner_header, bg=self.colors['primary_blue'])
        title_frame.pack(expand=True, fill=tk.BOTH)

        title_label = tk.Label(title_frame,
                               text="🎯 SnapMaster",
                               bg=self.colors['primary_blue'],
                               fg=self.colors['text_primary'],
                               font=('Segoe UI', 26, 'bold'),
                               relief='flat')
        title_label.pack(side=tk.LEFT, padx=25, pady=20)

        subtitle_label = tk.Label(title_frame,
                                  text="Capture d'écran avancée",
                                  bg=self.colors['primary_blue'],
                                  fg=self.colors['light_blue'],
                                  font=('Segoe UI', 13),
                                  relief='flat')
        subtitle_label.pack(side=tk.LEFT, padx=(0, 25), pady=20)

        # Indicateurs de statut colorés dans l'en-tête avec bordure arrondie
        status_frame = tk.Frame(title_frame, bg=self.colors['bg_light'], relief='flat')
        status_frame.pack(side=tk.RIGHT, padx=25, pady=20)

        # Indicateur de surveillance avec padding
        self.monitoring_indicator = tk.Label(status_frame,
                                             text="🔴 Arrêté",
                                             bg=self.colors['bg_light'],
                                             fg=self.colors['error'],
                                             font=('Segoe UI', 11, 'bold'),
                                             relief='flat')
        self.monitoring_indicator.pack(padx=15, pady=8)

    def _create_menu_bar(self):
        """Crée la barre de menu avec style moderne"""
        menubar = tk.Menu(self.root,
                          bg=self.colors['bg_card'],
                          fg=self.colors['text_primary'],
                          activebackground=self.colors['secondary_blue'],
                          activeforeground=self.colors['text_primary'],
                          font=('Segoe UI', 10))
        self.root.config(menu=menubar)

        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0,
                            bg=self.colors['bg_card'],
                            fg=self.colors['text_primary'],
                            activebackground=self.colors['secondary_blue'])
        menubar.add_cascade(label="📁 Fichier", menu=file_menu)
        file_menu.add_command(label="📂 Ouvrir dossier captures", command=self._open_screenshots_folder)
        file_menu.add_separator()
        file_menu.add_command(label="📤 Exporter configuration", command=self._export_config)
        file_menu.add_command(label="📥 Importer configuration", command=self._import_config)
        file_menu.add_separator()
        file_menu.add_command(label="❌ Quitter", command=self._on_window_close)

        # Menu Capture
        capture_menu = tk.Menu(menubar, tearoff=0,
                               bg=self.colors['bg_card'],
                               fg=self.colors['text_primary'],
                               activebackground=self.colors['secondary_blue'])
        menubar.add_cascade(label="📸 Capture", menu=capture_menu)
        capture_menu.add_command(label="🖥️ Plein écran", command=self._capture_fullscreen)
        capture_menu.add_command(label="🪟 Fenêtre active", command=self._capture_active_window)
        capture_menu.add_command(label="✂️ Zone sélectionnée", command=self._capture_area)
        capture_menu.add_separator()
        capture_menu.add_command(label="🧪 Test des capacités", command=self._test_capabilities)

        # Menu Outils
        tools_menu = tk.Menu(menubar, tearoff=0,
                             bg=self.colors['bg_card'],
                             fg=self.colors['text_primary'],
                             activebackground=self.colors['secondary_blue'])
        menubar.add_cascade(label="🔧 Outils", menu=tools_menu)
        tools_menu.add_command(label="⚙️ Paramètres", command=self._open_settings)
        tools_menu.add_command(label="📁 Gestionnaire de dossiers", command=self._open_folder_manager)
        tools_menu.add_separator()
        tools_menu.add_command(label="🧹 Nettoyage mémoire", command=self._force_memory_cleanup)
        tools_menu.add_command(label="📊 Statistiques", command=self._show_statistics)

        # Menu Aide
        help_menu = tk.Menu(menubar, tearoff=0,
                            bg=self.colors['bg_card'],
                            fg=self.colors['text_primary'],
                            activebackground=self.colors['secondary_blue'])
        menubar.add_cascade(label="❓ Aide", menu=help_menu)
        help_menu.add_command(label="⌨️ Raccourcis clavier", command=self._show_hotkeys)
        help_menu.add_command(label="ℹ️ À propos", command=self._show_about)

    def _create_main_frame(self):
        """Crée le frame principal avec onglets colorés"""
        # Container principal avec marge
        main_container = tk.Frame(self.root, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Notebook pour les onglets avec style moderne
        self.notebook = ttk.Notebook(main_container, style='TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Onglet Capture avec icônes colorées
        self._create_capture_tab(self.notebook)

        # Onglet Applications
        self._create_apps_tab(self.notebook)

        # Onglet Surveillance
        self._create_monitoring_tab(self.notebook)

    def _create_capture_tab(self, parent):
        """Crée l'onglet de capture avec design moderne"""
        capture_frame = ttk.Frame(parent, style='TFrame')
        parent.add(capture_frame, text="📸 Capture")

        # Section boutons de capture avec design coloré
        buttons_frame = ttk.LabelFrame(capture_frame, text="🎯 Actions de capture", style='TLabelframe')
        buttons_frame.pack(fill=tk.X, padx=15, pady=10)

        # Grid pour les boutons principaux
        btn_grid = ttk.Frame(buttons_frame, style='TFrame')
        btn_grid.pack(fill=tk.X, padx=10, pady=15)

        # Boutons de capture avec couleurs distinctes
        btn1 = ttk.Button(btn_grid, text="🖥️ Plein écran",
                          command=self._capture_fullscreen,
                          style='Action.TButton',
                          width=20)
        btn1.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        btn2 = ttk.Button(btn_grid, text="🪟 Fenêtre active",
                          command=self._capture_active_window,
                          style='Action.TButton',
                          width=20)
        btn2.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        btn3 = ttk.Button(btn_grid, text="✂️ Zone sélectionnée",
                          command=self._capture_area,
                          style='Action.TButton',
                          width=20)
        btn3.grid(row=0, column=2, padx=5, pady=5, sticky='ew')

        # Configuration du grid
        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)
        btn_grid.columnconfigure(2, weight=1)

        # Section paramètres rapides avec style moderne
        quick_settings_frame = ttk.LabelFrame(capture_frame, text="⚡ Paramètres rapides", style='TLabelframe')
        quick_settings_frame.pack(fill=tk.X, padx=15, pady=10)

        # Grid pour les paramètres
        settings_grid = ttk.Frame(quick_settings_frame, style='TFrame')
        settings_grid.pack(fill=tk.X, padx=10, pady=10)

        # Format d'image avec style coloré
        ttk.Label(settings_grid, text="🎨 Format:", style='TLabel').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.format_var = tk.StringVar(value=self.settings.get_capture_settings().get('image_format', 'PNG'))
        format_combo = ttk.Combobox(settings_grid, textvariable=self.format_var,
                                    values=['PNG', 'JPEG', 'BMP'], state='readonly', width=10,
                                    style='TCombobox')
        format_combo.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        format_combo.bind('<<ComboboxSelected>>', self._on_format_change)

        # Qualité avec curseur coloré
        ttk.Label(settings_grid, text="💎 Qualité:", style='TLabel').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.quality_var = tk.IntVar(value=self.settings.get_capture_settings().get('image_quality', 95))
        quality_scale = ttk.Scale(settings_grid, from_=10, to=100, variable=self.quality_var,
                                  orient=tk.HORIZONTAL, length=200, style='TScale')
        quality_scale.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        quality_scale.bind('<ButtonRelease-1>', self._on_quality_change)

        self.quality_label = ttk.Label(settings_grid, text=f"{self.quality_var.get()}%", style='Title.TLabel')
        self.quality_label.grid(row=1, column=2, sticky='w', padx=5, pady=5)

        # Section dossier avec design moderne
        folder_frame = ttk.LabelFrame(capture_frame, text="📁 Dossier de destination", style='TLabelframe')
        folder_frame.pack(fill=tk.X, padx=15, pady=10)

        folder_content = ttk.Frame(folder_frame, style='TFrame')
        folder_content.pack(fill=tk.X, padx=10, pady=10)

        self.folder_var = tk.StringVar(value=self.settings.get_default_folder())
        folder_entry = ttk.Entry(folder_content, textvariable=self.folder_var, state='readonly',
                                 style='TEntry', font=('Segoe UI', 10))
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = ttk.Button(folder_content, text="📂 Parcourir",
                                command=self._browse_folder, style='Modern.TButton')
        browse_btn.pack(side=tk.RIGHT)

        # Liste des dossiers personnalisés avec style
        folders_label = ttk.Label(folder_frame, text="📋 Dossiers personnalisés:", style='Title.TLabel')
        folders_label.pack(anchor=tk.W, padx=10, pady=(10, 5))

        # Listbox avec scrollbar colorée
        listbox_frame = ttk.Frame(folder_frame, style='TFrame')
        listbox_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.folders_listbox = tk.Listbox(listbox_frame, height=3,
                                          bg=self.colors['bg_light'],
                                          fg=self.colors['text_primary'],
                                          selectbackground=self.colors['secondary_blue'],
                                          selectforeground=self.colors['text_primary'],
                                          font=('Segoe UI', 10),
                                          relief='flat',
                                          borderwidth=1)
        self.folders_listbox.pack(fill=tk.X)
        self.folders_listbox.bind('<Double-1>', self._select_custom_folder)

        self._update_folders_list()

    def _create_apps_tab(self, parent):
        """Crée l'onglet des applications avec design coloré"""
        apps_frame = ttk.Frame(parent, style='TFrame')
        parent.add(apps_frame, text="🎮 Applications")

        # Application actuelle avec design moderne
        current_app_frame = ttk.LabelFrame(apps_frame, text="🎯 Application actuelle", style='TLabelframe')
        current_app_frame.pack(fill=tk.X, padx=15, pady=10)

        # Container pour l'application actuelle avec bordure arrondie
        app_container = tk.Frame(current_app_frame,
                                 bg=self.colors['bg_card'],
                                 relief='flat',
                                 bd=2,
                                 highlightbackground=self.colors['secondary_blue'],
                                 highlightthickness=2)
        app_container.pack(fill=tk.X, padx=15, pady=15)

        self.app_label = tk.Label(app_container,
                                  text="❌ Aucune application détectée",
                                  bg=self.colors['bg_card'],
                                  fg=self.colors['warning'],
                                  font=('Segoe UI', 16, 'bold'),
                                  relief='flat')
        self.app_label.pack(padx=20, pady=15)

        self.app_details_label = tk.Label(app_container,
                                          text="",
                                          bg=self.colors['bg_card'],
                                          fg=self.colors['text_secondary'],
                                          font=('Segoe UI', 11),
                                          justify=tk.LEFT,
                                          relief='flat')
        self.app_details_label.pack(padx=20, pady=(0, 15))

        # Bouton capture directe coloré avec padding
        button_frame = tk.Frame(app_container, bg=self.colors['bg_card'])
        button_frame.pack(pady=(0, 15))

        self.direct_capture_btn = ttk.Button(button_frame,
                                             text="📸 Capturer cette application",
                                             command=self._capture_current_app,
                                             style='Success.TButton',
                                             state=tk.DISABLED)
        self.direct_capture_btn.pack()

        # Associations avec design moderne
        associations_frame = ttk.LabelFrame(apps_frame, text="🔗 Associations application → dossier", style='TLabelframe')
        associations_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Treeview pour les associations avec bordure arrondie
        tree_container = tk.Frame(associations_frame,
                                  bg=self.colors['bg_light'],
                                  relief='flat',
                                  bd=2,
                                  highlightbackground=self.colors['secondary_blue'],
                                  highlightthickness=1)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        columns = ('app', 'folder')
        self.associations_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=8,
                                              style='Treeview')
        self.associations_tree.heading('app', text='🎮 Application')
        self.associations_tree.heading('folder', text='📁 Dossier')
        self.associations_tree.column('app', width=280)
        self.associations_tree.column('folder', width=320)

        # Scrollbar colorée avec style
        assoc_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.associations_tree.yview)
        self.associations_tree.configure(yscrollcommand=assoc_scrollbar.set)

        self.associations_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        assoc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

        # Container pour les boutons avec fond visible
        buttons_container = tk.Frame(associations_frame, bg=self.colors['bg_medium'], height=60)
        buttons_container.pack(fill=tk.X, padx=15, pady=15)
        buttons_container.pack_propagate(False)

        # Frame interne pour les boutons
        assoc_buttons_frame = tk.Frame(buttons_container, bg=self.colors['bg_medium'])
        assoc_buttons_frame.pack(expand=True, fill=tk.BOTH, pady=10)

        # Bouton Ajouter en vert
        add_btn = ttk.Button(assoc_buttons_frame, text="➕ Ajouter",
                             command=self._add_association, style='Add.TButton')
        add_btn.pack(side=tk.LEFT, padx=10)

        # Bouton Modifier en orange
        edit_btn = ttk.Button(assoc_buttons_frame, text="✏️ Modifier",
                              command=self._edit_association, style='Edit.TButton')
        edit_btn.pack(side=tk.LEFT, padx=10)

        # Bouton Supprimer en rouge
        delete_btn = ttk.Button(assoc_buttons_frame, text="🗑️ Supprimer",
                                command=self._remove_association, style='Delete.TButton')
        delete_btn.pack(side=tk.LEFT, padx=10)

        # Bouton Actualiser en bleu
        refresh_btn = ttk.Button(assoc_buttons_frame, text="🔄 Actualiser",
                                 command=self._update_associations_list, style='Modern.TButton')
        refresh_btn.pack(side=tk.RIGHT, padx=10)

        self._update_associations_list()

    def _create_monitoring_tab(self, parent):
        """Crée l'onglet de surveillance avec indicateurs colorés"""
        monitoring_frame = ttk.Frame(parent, style='TFrame')
        parent.add(monitoring_frame, text="📊 Surveillance")

        # État du système avec indicateurs colorés et bordures arrondies
        status_frame = ttk.LabelFrame(monitoring_frame, text="🔍 État du système", style='TLabelframe')
        status_frame.pack(fill=tk.X, padx=15, pady=10)

        status_container = tk.Frame(status_frame,
                                    bg=self.colors['bg_card'],
                                    relief='flat',
                                    bd=2,
                                    highlightbackground=self.colors['info'],
                                    highlightthickness=2)
        status_container.pack(fill=tk.X, padx=15, pady=15)

        self.status_label = tk.Label(status_container,
                                     text="🔴 Services arrêtés",
                                     bg=self.colors['bg_card'],
                                     fg=self.colors['error'],
                                     font=('Segoe UI', 16, 'bold'),
                                     relief='flat')
        self.status_label.pack(padx=20, pady=15)

        # Informations mémoire avec graphiques colorés et bordures arrondies
        memory_frame = ttk.LabelFrame(monitoring_frame, text="💾 Utilisation mémoire", style='TLabelframe')
        memory_frame.pack(fill=tk.X, padx=15, pady=10)

        memory_container = tk.Frame(memory_frame,
                                    bg=self.colors['bg_card'],
                                    relief='flat',
                                    bd=2,
                                    highlightbackground=self.colors['info'],
                                    highlightthickness=2)
        memory_container.pack(fill=tk.X, padx=15, pady=15)

        self.memory_label = tk.Label(memory_container,
                                     text="Mémoire: -- MB",
                                     bg=self.colors['bg_card'],
                                     fg=self.colors['info'],
                                     font=('Segoe UI', 14, 'bold'),
                                     relief='flat')
        self.memory_label.pack(padx=20, pady=15)

        # Boutons de gestion mémoire avec espacement
        memory_buttons_frame = tk.Frame(memory_container, bg=self.colors['bg_card'])
        memory_buttons_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

        ttk.Button(memory_buttons_frame, text="🧹 Nettoyer maintenant",
                   command=self._force_memory_cleanup, style='Modern.TButton').pack(side=tk.LEFT, padx=8)
        ttk.Button(memory_buttons_frame, text="📊 Statistiques détaillées",
                   command=self._show_memory_stats, style='Modern.TButton').pack(side=tk.LEFT, padx=8)

        # Raccourcis clavier avec style moderne et bordures arrondies
        hotkeys_frame = ttk.LabelFrame(monitoring_frame, text="⌨️ Raccourcis clavier", style='TLabelframe')
        hotkeys_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        hotkeys_container = tk.Frame(hotkeys_frame,
                                     bg=self.colors['bg_light'],
                                     relief='flat',
                                     bd=2,
                                     highlightbackground=self.colors['secondary_blue'],
                                     highlightthickness=1)
        hotkeys_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.hotkeys_text = tk.Text(hotkeys_container, height=8, state=tk.DISABLED, wrap=tk.WORD,
                                    bg=self.colors['bg_light'],
                                    fg=self.colors['text_primary'],
                                    font=('Segoe UI', 11),
                                    relief='flat',
                                    borderwidth=0,
                                    insertbackground=self.colors['text_primary'])

        hotkeys_scrollbar = ttk.Scrollbar(hotkeys_container, orient=tk.VERTICAL, command=self.hotkeys_text.yview)
        self.hotkeys_text.configure(yscrollcommand=hotkeys_scrollbar.set)

        self.hotkeys_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        hotkeys_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

        self._update_hotkeys_display()

    def _create_status_bar(self):
        """Crée la barre de statut colorée avec coins arrondis"""
        status_bar = tk.Frame(self.root, bg=self.colors['bg_card'], height=35,
                              relief='flat',
                              bd=2,
                              highlightbackground=self.colors['border'],
                              highlightthickness=1)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=(0, 5))
        status_bar.pack_propagate(False)

        # Container interne avec padding
        inner_status = tk.Frame(status_bar, bg=self.colors['bg_card'])
        inner_status.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)

        # Message de statut avec icône
        status_container = tk.Frame(inner_status, bg=self.colors['bg_card'])
        status_container.pack(side=tk.LEFT, fill=tk.Y)

        self.status_text = tk.StringVar(value="✅ Prêt")
        status_label = tk.Label(status_container,
                                textvariable=self.status_text,
                                bg=self.colors['bg_card'],
                                fg=self.colors['text_primary'],
                                font=('Segoe UI', 10, 'bold'),
                                relief='flat')
        status_label.pack(side=tk.LEFT, padx=12, pady=5)

        # Version info
        version_label = tk.Label(inner_status,
                                 text="v1.0.0",
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['text_muted'],
                                 font=('Segoe UI', 9),
                                 relief='flat')
        version_label.pack(side=tk.LEFT, padx=20)

        # Container pour indicateurs de droite
        right_status = tk.Frame(inner_status, bg=self.colors['bg_card'])
        right_status.pack(side=tk.RIGHT, fill=tk.Y)

        # Indicateur de surveillance dans la barre de statut avec style
        monitoring_label = tk.Label(right_status,
                                    text="Surveillance:",
                                    bg=self.colors['bg_card'],
                                    fg=self.colors['text_muted'],
                                    font=('Segoe UI', 9),
                                    relief='flat')
        monitoring_label.pack(side=tk.RIGHT, padx=(8, 0), pady=5)

        self.monitoring_status = tk.Label(right_status,
                                          text="🔴 Arrêtée",
                                          bg=self.colors['bg_card'],
                                          fg=self.colors['error'],
                                          font=('Segoe UI', 10, 'bold'),
                                          relief='flat')
        self.monitoring_status.pack(side=tk.RIGHT, padx=(0, 12), pady=5)

    def _setup_callbacks(self):
        """Configure les callbacks des différents gestionnaires"""
        try:
            # Callbacks du gestionnaire de captures
            self.screenshot_manager.add_capture_callback(self._on_capture_complete)
            self.screenshot_manager.add_error_callback(self._on_capture_error)

            # Callbacks du détecteur d'applications
            self.app_detector.add_update_callback(self._on_app_change)

            # IMPORTANT: Ajouter les callbacks AVANT de démarrer la surveillance des hotkeys
            # Callbacks des hotkeys - lie les actions aux méthodes de capture
            self.hotkey_manager.add_action_callback('fullscreen_capture', self._capture_fullscreen)
            self.hotkey_manager.add_action_callback('window_capture', self._capture_active_window)
            self.hotkey_manager.add_action_callback('area_capture', self._capture_area)
            self.hotkey_manager.add_action_callback('quick_capture', self._capture_current_app)

            self.logger.info("Callbacks configurés avec succès")

        except Exception as e:
            self.logger.error(f"Erreur configuration callbacks: {e}")

    def _start_services(self):
        """Démarre tous les services"""
        try:
            self.logger.info("Démarrage des services SnapMaster...")

            # 1. D'abord configurer tous les callbacks
            self._setup_callbacks()

            # 2. Démarre la détection d'applications
            self.app_detector.start_monitoring(interval=2.0)
            self.logger.info("Détection d'applications démarrée")

            # 3. Démarre les hotkeys (APRÈS avoir configuré les callbacks)
            if self.hotkey_manager.start_monitoring():
                self.logger.info("Hotkeys activés avec succès")
                hotkeys = self.hotkey_manager.get_active_hotkeys()
                for action, hotkey in hotkeys.items():
                    self.logger.info(f"  • {action}: {hotkey}")
            else:
                self.logger.warning("Impossible d'activer les hotkeys")
                self._show_warning("Raccourcis clavier",
                                   "Les raccourcis clavier n'ont pas pu être activés.\n"
                                   "Vérifiez les permissions de l'application.")

            # 4. Démarre la surveillance mémoire
            self.memory_manager.start_monitoring()
            self.logger.info("Surveillance mémoire démarrée")

            self.monitoring_active = True
            self._update_status("🟢 Services actifs")
            self.monitoring_indicator.config(text="🟢")

            # Test des capacités
            capabilities = self.screenshot_manager.test_capture_capability()
            if not capabilities.get('fullscreen', False):
                self.logger.warning("Capacités de capture limitées")
                self._show_warning("Capacités limitées",
                                   "Certaines fonctionnalités de capture peuvent ne pas fonctionner.\n"
                                   "Vérifiez les permissions de l'application.")

        except Exception as e:
            self.logger.error(f"Erreur démarrage services: {e}")
            self._update_status("🔴 Erreur services")
            self.monitoring_indicator.config(text="🔴")
            self._show_error("Erreur de démarrage",
                             f"Impossible de démarrer tous les services:\n{str(e)}")

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

    # Méthodes de callback avec couleurs
    def _on_capture_complete(self, capture_type: str, save_path: str, app_info: Optional[AppInfo] = None):
        """Callback appelé après une capture réussie"""
        def update_ui():
            message = f"✅ Capture {capture_type} sauvegardée: {Path(save_path).name}"
            self._update_status(message, self.colors['success'])

            if self.settings.get_ui_settings().get('show_notifications', True):
                self._show_notification("Capture réussie", message)

        self.root.after(0, update_ui)

    def _on_capture_error(self, capture_type: str, error_message: str):
        """Callback appelé en cas d'erreur de capture"""
        def update_ui():
            message = f"❌ Erreur capture {capture_type}: {error_message}"
            self._update_status(message, self.colors['error'])
            self._show_error("Erreur de capture", error_message)

        self.root.after(0, update_ui)

    def _on_app_change(self, app_info: AppInfo):
        """Callback appelé lors du changement d'application"""
        self.current_app = app_info
        self.root.after(0, self._update_current_app_display, app_info)

    # Méthodes de mise à jour avec couleurs
    def _update_status(self, message: str, color: str = None):
        """Met à jour le message de statut avec couleur"""
        if self.status_text:
            self.status_text.set(message)

    def _update_monitoring_status(self, active: bool):
        """Met à jour l'état de surveillance avec couleurs"""
        if active:
            self.monitoring_indicator.config(text="🟢 Actif", fg=self.colors['success'])
            self.monitoring_status.config(text="🟢 Active", fg=self.colors['success'])
        else:
            self.monitoring_indicator.config(text="🔴 Arrêté", fg=self.colors['error'])
            self.monitoring_status.config(text="🔴 Arrêtée", fg=self.colors['error'])

    def _update_memory_display(self, memory_mb: float):
        """Met à jour l'affichage de la mémoire avec couleurs"""
        if self.memory_label:
            if memory_mb > 500:
                color = self.colors['error']
                icon = "🔴"
            elif memory_mb > 250:
                color = self.colors['warning']
                icon = "🟡"
            else:
                color = self.colors['success']
                icon = "🟢"

            self.memory_label.config(text=f"{icon} Mémoire: {memory_mb:.1f} MB", fg=color)

    def _update_current_app_display(self, app_info: Optional[AppInfo]):
        """Met à jour l'affichage de l'application actuelle avec couleurs"""
        if not self.app_label:
            return

        if app_info:
            # Icône selon le type d'application
            if app_info.is_game:
                icon = "🎮"
                color = self.colors['info']
            elif app_info.is_browser:
                icon = "🌐"
                color = self.colors['accent_blue']
            else:
                icon = "💼"
                color = self.colors['secondary_blue']

            self.app_label.config(text=f"{icon} {app_info.name}", fg=color)

            details = f"📝 Titre: {app_info.window_title}\n"
            details += f"🆔 PID: {app_info.pid}\n"
            details += f"📺 Plein écran: {'✅ Oui' if app_info.is_fullscreen else '❌ Non'}\n"
            if app_info.is_game:
                details += f"🎯 Type: 🎮 Jeu"
            elif app_info.is_browser:
                details += f"🎯 Type: 🌐 Navigateur"
            else:
                details += f"🎯 Type: 💼 Application"

            if self.app_details_label:
                self.app_details_label.config(text=details)

            if self.direct_capture_btn:
                self.direct_capture_btn.config(state=tk.NORMAL)
        else:
            self.app_label.config(text="❌ Aucune application détectée", fg=self.colors['warning'])
            if self.app_details_label:
                self.app_details_label.config(text="")
            if self.direct_capture_btn:
                self.direct_capture_btn.config(state=tk.DISABLED)

    # Méthodes de capture
    def _capture_fullscreen(self):
        """Lance une capture plein écran"""
        def capture():
            self._update_status("📱 Capture plein écran en cours...", self.colors['info'])
            self.screenshot_manager.capture_fullscreen()

        threading.Thread(target=capture, daemon=True).start()

    def _capture_active_window(self):
        """Lance une capture de la fenêtre active"""
        def capture():
            self._update_status("🪟 Capture fenêtre active en cours...", self.colors['info'])
            self.screenshot_manager.capture_active_window()

        threading.Thread(target=capture, daemon=True).start()

    def _capture_area(self):
        """Lance une capture de zone sélectionnée"""
        def capture():
            self._update_status("✂️ Sélectionnez la zone à capturer...", self.colors['info'])
            self.screenshot_manager.capture_area_selection()

        threading.Thread(target=capture, daemon=True).start()

    def _capture_current_app(self):
        """Lance une capture de l'application actuelle"""
        if not self.current_app:
            self._show_warning("Aucune application", "Aucune application détectée")
            return

        def capture():
            self._update_status(f"📸 Capture de {self.current_app.name}...", self.colors['info'])
            self.screenshot_manager.capture_app_direct(self.current_app.name)

        threading.Thread(target=capture, daemon=True).start()

    # Méthodes utilitaires avec couleurs
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
        if messagebox.askokcancel("Quitter SnapMaster", "Voulez-vous vraiment quitter SnapMaster?"):
            self._cleanup()
            self.root.destroy()

    # MÉTHODES D'ASSOCIATION AMÉLIORÉES
    def _add_association(self):
        """Ajoute une association application/dossier avec interface améliorée"""
        try:
            # Crée la fenêtre de dialogue pour l'association
            dialog = AdvancedAssociationDialog(self.root, self.settings)
            result = dialog.show()

            if result:
                app_name, folder_path = result

                # Détermine le nom du dossier pour les paramètres
                folder_name = self._get_folder_name_from_path(folder_path)

                # Ajoute le dossier personnalisé s'il n'existe pas déjà
                if folder_path != self.settings.get_default_folder():
                    self.settings.add_custom_folder(folder_name, folder_path)

                # Crée l'association
                if self.settings.link_app_to_folder(app_name, folder_name):
                    self._update_associations_list()
                    self._update_status(f"✅ Association ajoutée: {app_name} → {folder_name}", self.colors['success'])
                    messagebox.showinfo("Succès",
                                        f"Association créée avec succès !\n\n"
                                        f"🎮 Application: {app_name}\n"
                                        f"📁 Dossier: {folder_path}")
                else:
                    self._show_error("Erreur", "Impossible d'ajouter l'association")

        except Exception as e:
            self.logger.error(f"Erreur ajout association: {e}")
            self._show_error("Erreur", f"Erreur lors de l'ajout: {str(e)}")

    def _edit_association(self):
        """Modifie une association existante avec interface améliorée"""
        try:
            selection = self.associations_tree.selection()
            if not selection:
                self._show_warning("Sélection", "Veuillez sélectionner une association à modifier")
                return

            item = self.associations_tree.item(selection[0])
            current_app = item['values'][0]
            current_folder_display = item['values'][1]

            # Récupère le chemin réel du dossier
            current_folder_path = self._get_folder_path_from_display(current_folder_display)

            # Crée la fenêtre de dialogue avec les valeurs actuelles
            dialog = AdvancedAssociationDialog(self.root, self.settings, current_app, current_folder_path)
            result = dialog.show()

            if result:
                new_app_name, new_folder_path = result

                # Détermine le nom du dossier pour les paramètres
                new_folder_name = self._get_folder_name_from_path(new_folder_path)

                # Ajoute le dossier personnalisé s'il n'existe pas déjà
                if new_folder_path != self.settings.get_default_folder():
                    self.settings.add_custom_folder(new_folder_name, new_folder_path)

                # Supprime l'ancienne association si le nom d'app a changé
                if new_app_name != current_app:
                    if current_app in self.settings.config['applications']['app_folder_mapping']:
                        del self.settings.config['applications']['app_folder_mapping'][current_app]

                # Met à jour l'association
                if self.settings.link_app_to_folder(new_app_name, new_folder_name):
                    self._update_associations_list()
                    self._update_status(f"✅ Association modifiée: {new_app_name} → {new_folder_name}", self.colors['success'])
                    messagebox.showinfo("Succès",
                                        f"Association modifiée avec succès !\n\n"
                                        f"🎮 Application: {new_app_name}\n"
                                        f"📁 Dossier: {new_folder_path}")
                else:
                    self._show_error("Erreur", "Impossible de modifier l'association")

        except Exception as e:
            self.logger.error(f"Erreur modification association: {e}")
            self._show_error("Erreur", f"Erreur lors de la modification: {str(e)}")

    def _remove_association(self):
        """Supprime une association"""
        try:
            selection = self.associations_tree.selection()
            if not selection:
                self._show_warning("Sélection", "Veuillez sélectionner une association à supprimer")
                return

            item = self.associations_tree.item(selection[0])
            app_name = item['values'][0]

            # Confirmation
            if messagebox.askyesno("Confirmation",
                                   f"Supprimer l'association pour '{app_name}' ?\n\nCette action est irréversible.",
                                   parent=self.root):
                # Supprime de la configuration
                if app_name in self.settings.config['applications']['app_folder_mapping']:
                    del self.settings.config['applications']['app_folder_mapping'][app_name]

                    # Supprime aussi des apps surveillées
                    if app_name in self.settings.config['applications']['monitored_apps']:
                        self.settings.config['applications']['monitored_apps'].remove(app_name)

                    self.settings.save_config()
                    self._update_associations_list()
                    self._update_status(f"✅ Association supprimée: {app_name}", self.colors['success'])
                    messagebox.showinfo("Succès", f"Association supprimée avec succès !\n\n{app_name}")
                else:
                    self._show_warning("Erreur", "Association introuvable")

        except Exception as e:
            self.logger.error(f"Erreur suppression association: {e}")
            self._show_error("Erreur", f"Erreur lors de la suppression: {str(e)}")

    def _update_associations_list(self):
        """Met à jour la liste des associations"""
        try:
            if not hasattr(self, 'associations_tree'):
                return

            # Nettoie l'arbre
            for item in self.associations_tree.get_children():
                self.associations_tree.delete(item)

            # Récupère les associations
            app_mappings = self.settings.config.get('applications', {}).get('app_folder_mapping', {})
            custom_folders = self.settings.get_custom_folders()

            # Ajoute les associations
            for app_name, folder_name in app_mappings.items():
                if folder_name == "default":
                    folder_display = "📁 Dossier par défaut"
                else:
                    folder_path = custom_folders.get(folder_name, folder_name)
                    folder_display = f"📁 {folder_name}" if folder_name in custom_folders else f"📁 {folder_name} (introuvable)"

                self.associations_tree.insert('', tk.END, values=(app_name, folder_display))

            # Message si aucune association
            if not app_mappings:
                self.associations_tree.insert('', tk.END, values=("Aucune association configurée", "Cliquez sur 'Ajouter' pour créer une association"))

        except Exception as e:
            self.logger.error(f"Erreur mise à jour associations: {e}")

    def _get_folder_name_from_path(self, folder_path: str) -> str:
        """Récupère le nom du dossier à partir du chemin"""
        if folder_path == self.settings.get_default_folder():
            return "default"

        # Utilise le nom du dossier comme nom
        folder_name = Path(folder_path).name
        if not folder_name:
            folder_name = "CustomFolder"

        return folder_name

    def _get_folder_path_from_display(self, folder_display: str) -> str:
        """Récupère le chemin réel à partir de l'affichage"""
        if "par défaut" in folder_display:
            return self.settings.get_default_folder()

        # Extrait le nom du dossier de l'affichage
        folder_name = folder_display.replace("📁 ", "").split(" (")[0]
        custom_folders = self.settings.get_custom_folders()

        return custom_folders.get(folder_name, self.settings.get_default_folder())

    # Méthodes à implémenter (stubs pour éviter les erreurs)
    def _open_screenshots_folder(self):
        """Ouvre le dossier de captures"""
        try:
            folder_path = self.settings.get_default_folder()
            import os
            import subprocess
            import platform

            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            self._show_error("Erreur", f"Impossible d'ouvrir le dossier: {e}")

    def _export_config(self):
        """Exporte la configuration"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Exporter la configuration",
                defaultextension=".json",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
            )
            if filename and self.settings.export_config(filename):
                messagebox.showinfo("Succès", "Configuration exportée avec succès")
        except Exception as e:
            self._show_error("Erreur", str(e))

    def _import_config(self):
        """Importe une configuration"""
        try:
            filename = filedialog.askopenfilename(
                title="Importer une configuration",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
            )
            if filename and messagebox.askyesno("Confirmation", "Remplacer la configuration actuelle?"):
                if self.settings.import_config(filename):
                    messagebox.showinfo("Succès", "Configuration importée. Redémarrez l'application.")
        except Exception as e:
            self._show_error("Erreur", str(e))

    def _test_capabilities(self):
        messagebox.showinfo("Test", "Fonctionnalité de test à implémenter")

    def _open_settings(self):
        messagebox.showinfo("Paramètres", "Fenêtre de paramètres à implémenter")

    def _open_folder_manager(self):
        messagebox.showinfo("Gestionnaire", "Gestionnaire de dossiers à implémenter")

    def _force_memory_cleanup(self):
        """Force le nettoyage mémoire"""
        try:
            self.memory_manager.force_cleanup()
            messagebox.showinfo("Nettoyage", "Nettoyage mémoire effectué")
        except Exception as e:
            self._show_error("Erreur", str(e))

    def _show_statistics(self):
        messagebox.showinfo("Statistiques", "Statistiques à implémenter")

    def _show_hotkeys(self):
        """Affiche les raccourcis clavier"""
        hotkeys = self.hotkey_manager.get_active_hotkeys() if self.hotkey_manager else {}

        message = "⌨️ Raccourcis clavier actifs:\n\n"
        if hotkeys:
            for action, key in hotkeys.items():
                message += f"• {action}: {key}\n"
        else:
            message += "Aucun raccourci configuré"

        messagebox.showinfo("Raccourcis clavier", message)

    def _show_about(self):
        messagebox.showinfo("À propos", "🎯 SnapMaster v1.0.0\n\nCapture d'écran avancée\nAvec thème bleu moderne")

    def _on_format_change(self, event):
        """Change le format d'image"""
        try:
            format_value = self.format_var.get()
            self.settings.update_capture_setting('image_format', format_value)
            self._update_status(f"Format changé: {format_value}", self.colors['info'])
        except Exception as e:
            self.logger.error(f"Erreur changement format: {e}")

    def _on_quality_change(self, event):
        """Change la qualité d'image"""
        try:
            quality = self.quality_var.get()
            self.quality_label.config(text=f"{quality}%")
            self.settings.update_capture_setting('image_quality', quality)
        except Exception as e:
            self.logger.error(f"Erreur changement qualité: {e}")

    def _browse_folder(self):
        """Parcourt pour sélectionner un dossier"""
        try:
            folder = filedialog.askdirectory(title="Sélectionner le dossier de captures")
            if folder:
                self.folder_var.set(folder)
                self.settings.config['folders']['default_screenshots'] = folder
                self.settings.save_config()
        except Exception as e:
            self._show_error("Erreur", str(e))

    def _select_custom_folder(self, event):
        """Sélectionne un dossier personnalisé"""
        try:
            selection = self.folders_listbox.curselection()
            if selection:
                folder_name = self.folders_listbox.get(selection[0])
                custom_folders = self.settings.get_custom_folders()
                if folder_name in custom_folders:
                    self.folder_var.set(custom_folders[folder_name])
        except Exception as e:
            self.logger.error(f"Erreur sélection dossier: {e}")

    def _update_folders_list(self):
        """Met à jour la liste des dossiers"""
        try:
            if hasattr(self, 'folders_listbox'):
                self.folders_listbox.delete(0, tk.END)
                custom_folders = self.settings.get_custom_folders()
                for folder_name in custom_folders.keys():
                    self.folders_listbox.insert(tk.END, folder_name)
        except Exception as e:
            self.logger.error(f"Erreur mise à jour dossiers: {e}")

    def _show_memory_stats(self):
        """Affiche les stats mémoire"""
        try:
            memory_usage = self.memory_manager.get_current_memory_usage()
            messagebox.showinfo("Mémoire", f"Utilisation actuelle: {memory_usage:.1f} MB")
        except Exception as e:
            self._show_error("Erreur", str(e))

    def _update_hotkeys_display(self):
        """Met à jour l'affichage des raccourcis"""
        try:
            if hasattr(self, 'hotkeys_text'):
                hotkeys = self.hotkey_manager.get_active_hotkeys() if self.hotkey_manager else {}

                text = "⌨️ Raccourcis clavier actifs:\n\n"
                if hotkeys:
                    for action, key in hotkeys.items():
                        text += f"• {action}: {key}\n"
                else:
                    text += "Aucun raccourci configuré"

                self.hotkeys_text.config(state=tk.NORMAL)
                self.hotkeys_text.delete(1.0, tk.END)
                self.hotkeys_text.insert(1.0, text)
                self.hotkeys_text.config(state=tk.DISABLED)
        except Exception as e:
            self.logger.error(f"Erreur mise à jour hotkeys: {e}")

    def _set_window_icon(self):
        """Définit l'icône de la fenêtre"""
        try:
            icon_path = Path("assets/icon.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass


class AdvancedAssociationDialog:
    """Dialogue avancé pour ajouter/modifier une association avec liste d'applications et explorateur"""

    def __init__(self, parent, settings_manager: SettingsManager, app_name: str = "", folder_path: str = ""):
        self.parent = parent
        self.settings = settings_manager
        self.initial_app_name = app_name
        self.initial_folder_path = folder_path or settings_manager.get_default_folder()

        self.result = None
        self.window = None

        # Variables d'interface
        self.selected_app_name = tk.StringVar(value=app_name)
        self.selected_folder_path = tk.StringVar(value=self.initial_folder_path)

        # Liste des applications
        self.running_apps = []
        self.all_processes = []

        # Widgets
        self.apps_listbox = None
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._filter_apps)

    def show(self):
        """Affiche le dialogue et retourne le résultat"""
        self._create_dialog()
        self._load_applications()
        self.window.wait_window()
        return self.result

    def _create_dialog(self):
        """Crée la fenêtre de dialogue avancée"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("🔗 Nouvelle association Application → Dossier")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        self.window.transient(self.parent)
        self.window.grab_set()

        # Configuration de la fenêtre
        self.window.configure(bg='#1a202c')

        # Centre le dialogue
        self._center_dialog()

        # Création de l'interface
        self._create_header()
        self._create_app_selection_section()
        self._create_folder_selection_section()
        self._create_buttons()

    def _center_dialog(self):
        """Centre le dialogue sur l'écran parent"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()

        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)

        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _create_header(self):
        """Crée l'en-tête du dialogue"""
        header_frame = tk.Frame(self.window, bg='#1e3a8a', height=80)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        header_frame.pack_propagate(False)

        # Titre principal
        title_label = tk.Label(header_frame,
                               text="🔗 Association Application → Dossier",
                               bg='#1e3a8a',
                               fg='white',
                               font=('Segoe UI', 18, 'bold'))
        title_label.pack(expand=True, pady=15)

        # Sous-titre
        subtitle = "Modifiez" if self.initial_app_name else "Créez une nouvelle"
        subtitle_label = tk.Label(header_frame,
                                  text=f"{subtitle} association pour capturer automatiquement dans le bon dossier",
                                  bg='#1e3a8a',
                                  fg='#60a5fa',
                                  font=('Segoe UI', 11))
        subtitle_label.pack()

    def _create_app_selection_section(self):
        """Crée la section de sélection d'application"""
        # Frame principal pour la sélection d'app
        app_frame = tk.LabelFrame(self.window,
                                  text="🎮 Sélection de l'application",
                                  bg='#1a202c',
                                  fg='#3b82f6',
                                  font=('Segoe UI', 12, 'bold'),
                                  relief='flat',
                                  bd=2)
        app_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Zone de recherche
        search_frame = tk.Frame(app_frame, bg='#1a202c')
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(search_frame,
                 text="🔍 Rechercher une application:",
                 bg='#1a202c',
                 fg='white',
                 font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

        search_entry = tk.Entry(search_frame,
                                textvariable=self.search_var,
                                bg='#2d3748',
                                fg='white',
                                font=('Segoe UI', 11),
                                relief='flat',
                                bd=5)
        search_entry.pack(fill=tk.X, pady=(5, 0))

        # Liste des applications avec onglets
        apps_notebook = ttk.Notebook(app_frame)
        apps_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Onglet applications en cours
        running_frame = tk.Frame(apps_notebook, bg='#1a202c')
        apps_notebook.add(running_frame, text="🔴 Applications en cours")

        self.running_listbox = tk.Listbox(running_frame,
                                          bg='#2d3748',
                                          fg='white',
                                          selectbackground='#3b82f6',
                                          font=('Segoe UI', 10),
                                          relief='flat',
                                          bd=0)

        running_scrollbar = tk.Scrollbar(running_frame, orient=tk.VERTICAL)
        self.running_listbox.configure(yscrollcommand=running_scrollbar.set)
        running_scrollbar.configure(command=self.running_listbox.yview)

        self.running_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        running_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Onglet tous les processus
        all_frame = tk.Frame(apps_notebook, bg='#1a202c')
        apps_notebook.add(all_frame, text="📋 Tous les processus")

        self.all_listbox = tk.Listbox(all_frame,
                                      bg='#2d3748',
                                      fg='white',
                                      selectbackground='#3b82f6',
                                      font=('Segoe UI', 10),
                                      relief='flat',
                                      bd=0)

        all_scrollbar = tk.Scrollbar(all_frame, orient=tk.VERTICAL)
        self.all_listbox.configure(yscrollcommand=all_scrollbar.set)
        all_scrollbar.configure(command=self.all_listbox.yview)

        self.all_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        all_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Boutons pour sélection alternative
        alt_buttons_frame = tk.Frame(app_frame, bg='#1a202c')
        alt_buttons_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Bouton pour parcourir un exécutable
        browse_exe_btn = tk.Button(alt_buttons_frame,
                                   text="📂 Parcourir un exécutable...",
                                   command=self._browse_executable,
                                   bg='#f59e0b',
                                   fg='white',
                                   font=('Segoe UI', 10, 'bold'),
                                   relief='flat',
                                   bd=0,
                                   padx=15,
                                   pady=8)
        browse_exe_btn.pack(side=tk.LEFT, padx=5)

        # Bouton pour saisie manuelle
        manual_btn = tk.Button(alt_buttons_frame,
                               text="✏️ Saisie manuelle...",
                               command=self._manual_entry,
                               bg='#6b7280',
                               fg='white',
                               font=('Segoe UI', 10, 'bold'),
                               relief='flat',
                               bd=0,
                               padx=15,
                               pady=8)
        manual_btn.pack(side=tk.LEFT, padx=5)

        # Affichage de l'application sélectionnée
        selection_frame = tk.Frame(app_frame, bg='#374151', relief='flat', bd=2)
        selection_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(selection_frame,
                 text="🎯 Application sélectionnée:",
                 bg='#374151',
                 fg='#10b981',
                 font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.selected_app_label = tk.Label(selection_frame,
                                           textvariable=self.selected_app_name,
                                           bg='#374151',
                                           fg='white',
                                           font=('Segoe UI', 12, 'bold'))
        self.selected_app_label.pack(anchor=tk.W, padx=10, pady=(0, 10))

        # Bind des événements de sélection
        self.running_listbox.bind('<<ListboxSelect>>', self._on_running_app_select)
        self.all_listbox.bind('<<ListboxSelect>>', self._on_all_app_select)

    def _create_folder_selection_section(self):
        """Crée la section de sélection de dossier"""
        folder_frame = tk.LabelFrame(self.window,
                                     text="📁 Dossier de destination",
                                     bg='#1a202c',
                                     fg='#3b82f6',
                                     font=('Segoe UI', 12, 'bold'),
                                     relief='flat',
                                     bd=2)
        folder_frame.pack(fill=tk.X, padx=15, pady=10)

        # Dossier sélectionné
        folder_display_frame = tk.Frame(folder_frame, bg='#1a202c')
        folder_display_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(folder_display_frame,
                 text="📂 Dossier sélectionné:",
                 bg='#1a202c',
                 fg='white',
                 font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

        folder_entry = tk.Entry(folder_display_frame,
                                textvariable=self.selected_folder_path,
                                state='readonly',
                                bg='#2d3748',
                                fg='white',
                                font=('Segoe UI', 11),
                                relief='flat',
                                bd=5)
        folder_entry.pack(fill=tk.X, pady=(5, 0))

        # Boutons de sélection de dossier
        folder_buttons_frame = tk.Frame(folder_frame, bg='#1a202c')
        folder_buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        # Bouton par défaut
        default_btn = tk.Button(folder_buttons_frame,
                                text="🏠 Dossier par défaut",
                                command=self._select_default_folder,
                                bg='#3b82f6',
                                fg='white',
                                font=('Segoe UI', 10, 'bold'),
                                relief='flat',
                                bd=0,
                                padx=15,
                                pady=8)
        default_btn.pack(side=tk.LEFT, padx=5)

        # Bouton parcourir
        browse_folder_btn = tk.Button(folder_buttons_frame,
                                      text="📂 Parcourir...",
                                      command=self._browse_folder,
                                      bg='#10b981',
                                      fg='white',
                                      font=('Segoe UI', 11, 'bold'),
                                      relief='flat',
                                      bd=0,
                                      padx=20,
                                      pady=8)
        browse_folder_btn.pack(side=tk.RIGHT, padx=5)

    def _create_buttons(self):
        """Crée les boutons de contrôle"""
        buttons_frame = tk.Frame(self.window, bg='#1a202c')
        buttons_frame.pack(fill=tk.X, padx=15, pady=15)

        # Bouton Annuler
        cancel_btn = tk.Button(buttons_frame,
                               text="❌ Annuler",
                               command=self._cancel,
                               bg='#ef4444',
                               fg='white',
                               font=('Segoe UI', 11, 'bold'),
                               relief='flat',
                               bd=0,
                               padx=20,
                               pady=10)
        cancel_btn.pack(side=tk.RIGHT, padx=5)

        # Bouton OK
        ok_btn = tk.Button(buttons_frame,
                           text="✅ Créer l'association",
                           command=self._ok,
                           bg='#10b981',
                           fg='white',
                           font=('Segoe UI', 11, 'bold'),
                           relief='flat',
                           bd=0,
                           padx=20,
                           pady=10)
        ok_btn.pack(side=tk.RIGHT, padx=5)

    def _load_applications(self):
        """Charge la liste des applications en cours d'exécution"""
        try:
            # Applications en cours avec fenêtres (comme dans le gestionnaire des tâches)
            self.running_apps = self._get_running_applications()

            # Tous les processus
            self.all_processes = self._get_all_processes()

            # Remplit les listes
            self._populate_running_list()
            self._populate_all_list()

            # Sélectionne l'app initiale si fournie
            if self.initial_app_name:
                self._select_initial_app()

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des applications: {e}")

    def _get_running_applications(self):
        """Récupère les applications en cours avec fenêtres (équivalent Apps du gestionnaire des tâches)"""
        running_apps = []

        try:
            if platform.system() == "Windows":
                # Méthode Windows pour obtenir les apps avec fenêtres
                running_apps = self._get_windows_applications()
            else:
                # Méthode générique pour Linux/macOS
                running_apps = self._get_generic_applications()

        except Exception as e:
            print(f"Erreur récupération applications en cours: {e}")

        return running_apps

    def _get_windows_applications(self):
        """Récupère les applications Windows avec fenêtres visibles"""
        apps = []
        seen_names = set()

        try:
            # Utilise PowerShell pour obtenir les processus avec fenêtres
            cmd = ['powershell', '-Command',
                   'Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | Select-Object ProcessName, Id, MainWindowTitle, Path | ConvertTo-Json']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout:
                import json
                try:
                    processes = json.loads(result.stdout)
                    if not isinstance(processes, list):
                        processes = [processes]

                    for proc in processes:
                        name = proc.get('ProcessName', '')
                        if name and name not in seen_names:
                            apps.append({
                                'name': name + '.exe' if not name.endswith('.exe') else name,
                                'pid': proc.get('Id', 0),
                                'title': proc.get('MainWindowTitle', ''),
                                'path': proc.get('Path', ''),
                                'is_running': True
                            })
                            seen_names.add(name)

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"Erreur PowerShell: {e}")

        # Fallback avec psutil
        if not apps:
            apps = self._get_psutil_applications()

        return sorted(apps, key=lambda x: x['name'].lower())

    def _get_psutil_applications(self):
        """Récupère les applications avec psutil (fallback)"""
        apps = []
        seen_names = set()

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    name = proc_info['name']

                    if name and name not in seen_names:
                        # Filtre les processus système courants
                        if not self._is_system_process(name):
                            apps.append({
                                'name': name,
                                'pid': proc_info['pid'],
                                'title': '',
                                'path': proc_info.get('exe', ''),
                                'is_running': True
                            })
                            seen_names.add(name)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            print(f"Erreur psutil: {e}")

        return sorted(apps, key=lambda x: x['name'].lower())

    def _get_generic_applications(self):
        """Récupère les applications génériques (Linux/macOS)"""
        apps = []
        seen_names = set()

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    name = proc_info['name']

                    if name and name not in seen_names and not self._is_system_process(name):
                        apps.append({
                            'name': name,
                            'pid': proc_info['pid'],
                            'title': '',
                            'path': proc_info.get('exe', ''),
                            'is_running': True
                        })
                        seen_names.add(name)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            print(f"Erreur applications génériques: {e}")

        return sorted(apps, key=lambda x: x['name'].lower())

    def _get_all_processes(self):
        """Récupère tous les processus système"""
        processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    name = proc_info['name']

                    if name:
                        processes.append({
                            'name': name,
                            'pid': proc_info['pid'],
                            'title': '',
                            'path': proc_info.get('exe', ''),
                            'is_running': True
                        })

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            print(f"Erreur récupération processus: {e}")

        return sorted(processes, key=lambda x: x['name'].lower())

    def _is_system_process(self, process_name: str) -> bool:
        """Vérifie si un processus est un processus système à exclure"""
        system_processes = {
            'system', 'registry', 'smss.exe', 'csrss.exe', 'wininit.exe',
            'winlogon.exe', 'services.exe', 'lsass.exe', 'svchost.exe',
            'dllhost.exe', 'conhost.exe', 'dwm.exe', 'explorer.exe',
            'spoolsv.exe', 'taskhostw.exe', 'runtimebroker.exe',
            'searchindexer.exe', 'audiodg.exe', 'fontdrvhost.exe',
            'kthreadd', 'ksoftirqd', 'migration', 'rcu_gp', 'rcu_par_gp',
            'systemd', 'kernel', 'init'
        }

        return process_name.lower() in system_processes

    def _populate_running_list(self):
        """Remplit la liste des applications en cours"""
        self.running_listbox.delete(0, tk.END)

        for app in self.running_apps:
            display_text = f"🎮 {app['name']}"
            if app['title']:
                display_text += f" - {app['title'][:50]}"

            self.running_listbox.insert(tk.END, display_text)

    def _populate_all_list(self):
        """Remplit la liste de tous les processus"""
        self.all_listbox.delete(0, tk.END)

        for proc in self.all_processes:
            display_text = f"⚙️ {proc['name']} (PID: {proc['pid']})"
            self.all_listbox.insert(tk.END, display_text)

    def _filter_apps(self, *args):
        """Filtre les applications selon la recherche"""
        search_term = self.search_var.get().lower()

        # Filtre les applications en cours
        self.running_listbox.delete(0, tk.END)
        for app in self.running_apps:
            if search_term in app['name'].lower() or search_term in app.get('title', '').lower():
                display_text = f"🎮 {app['name']}"
                if app['title']:
                    display_text += f" - {app['title'][:50]}"
                self.running_listbox.insert(tk.END, display_text)

        # Filtre tous les processus
        self.all_listbox.delete(0, tk.END)
        for proc in self.all_processes:
            if search_term in proc['name'].lower():
                display_text = f"⚙️ {proc['name']} (PID: {proc['pid']})"
                self.all_listbox.insert(tk.END, display_text)

    def _on_running_app_select(self, event):
        """Gère la sélection d'une application en cours"""
        selection = self.running_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.running_apps):
                app = self.running_apps[index]
                self.selected_app_name.set(app['name'])
                # Désélectionne l'autre liste
                self.all_listbox.selection_clear(0, tk.END)

    def _on_all_app_select(self, event):
        """Gère la sélection d'un processus"""
        selection = self.all_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.all_processes):
                proc = self.all_processes[index]
                self.selected_app_name.set(proc['name'])
                # Désélectionne l'autre liste
                self.running_listbox.selection_clear(0, tk.END)

    def _browse_executable(self):
        """Parcourt pour sélectionner un fichier exécutable"""
        try:
            file_types = [
                ("Fichiers exécutables", "*.exe"),
                ("Tous les fichiers", "*.*")
            ]

            if platform.system() != "Windows":
                file_types = [
                    ("Fichiers exécutables", "*"),
                    ("Tous les fichiers", "*.*")
                ]

            filename = filedialog.askopenfilename(
                title="Sélectionner un fichier exécutable",
                filetypes=file_types,
                parent=self.window
            )

            if filename:
                app_name = Path(filename).name
                self.selected_app_name.set(app_name)
                # Désélectionne les listes
                self.running_listbox.selection_clear(0, tk.END)
                self.all_listbox.selection_clear(0, tk.END)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sélection: {e}", parent=self.window)

    def _manual_entry(self):
        """Permet la saisie manuelle du nom d'application"""
        try:
            from tkinter import simpledialog

            app_name = simpledialog.askstring(
                "Saisie manuelle",
                "Nom de l'application (ex: notepad.exe, chrome.exe):",
                initialvalue=self.selected_app_name.get(),
                parent=self.window
            )

            if app_name and app_name.strip():
                self.selected_app_name.set(app_name.strip())
                # Désélectionne les listes
                self.running_listbox.selection_clear(0, tk.END)
                self.all_listbox.selection_clear(0, tk.END)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la saisie: {e}", parent=self.window)

    def _select_default_folder(self):
        """Sélectionne le dossier par défaut"""
        default_folder = self.settings.get_default_folder()
        self.selected_folder_path.set(default_folder)

    def _browse_folder(self):
        """Parcourt pour sélectionner un dossier"""
        try:
            folder = filedialog.askdirectory(
                title="Sélectionner le dossier de destination",
                initialdir=self.selected_folder_path.get(),
                parent=self.window
            )

            if folder:
                self.selected_folder_path.set(folder)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sélection du dossier: {e}", parent=self.window)

    def _select_initial_app(self):
        """Sélectionne l'application initiale dans les listes"""
        try:
            # Cherche dans les applications en cours
            for i, app in enumerate(self.running_apps):
                if app['name'] == self.initial_app_name:
                    self.running_listbox.selection_set(i)
                    self.running_listbox.see(i)
                    return

            # Cherche dans tous les processus
            for i, proc in enumerate(self.all_processes):
                if proc['name'] == self.initial_app_name:
                    self.all_listbox.selection_set(i)
                    self.all_listbox.see(i)
                    return

        except Exception as e:
            print(f"Erreur sélection app initiale: {e}")

    def _validate_selection(self):
        """Valide la sélection actuelle"""
        app_name = self.selected_app_name.get().strip()
        folder_path = self.selected_folder_path.get().strip()

        if not app_name:
            messagebox.showerror("Erreur", "Veuillez sélectionner une application", parent=self.window)
            return False

        if not folder_path:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier", parent=self.window)
            return False

        if not Path(folder_path).exists():
            # Demande confirmation pour créer le dossier
            if messagebox.askyesno("Dossier introuvable",
                                   f"Le dossier n'existe pas:\n{folder_path}\n\nVoulez-vous le créer?",
                                   parent=self.window):
                try:
                    Path(folder_path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    messagebox.showerror("Erreur", f"Impossible de créer le dossier:\n{e}", parent=self.window)
                    return False
            else:
                return False

        return True

    def _ok(self):
        """Confirme la sélection"""
        if self._validate_selection():
            self.result = (self.selected_app_name.get().strip(), self.selected_folder_path.get().strip())
            self.window.destroy()

    def _cancel(self):
        """Annule la sélection"""
        self.result = None
        self.window.destroy()