# gui/settings_window.py
"""
Fenêtre de paramètres pour SnapMaster
Interface de configuration complète
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import SettingsManager
from core.hotkey_manager import HotkeyManager

class SettingsWindow:
    """Fenêtre de configuration de SnapMaster"""

    def __init__(self, parent, settings_manager: SettingsManager,
                 hotkey_manager: Optional[HotkeyManager] = None):
        self.parent = parent
        self.settings = settings_manager
        self.hotkey_manager = hotkey_manager
        self.logger = logging.getLogger(__name__)

        # Variables pour les paramètres
        self.vars = {}
        self.temp_settings = {}

        # Fenêtre
        self.window: Optional[tk.Toplevel] = None
        self.notebook: Optional[ttk.Notebook] = None

        # Flags de modifications
        self.modified = False

    def show(self):
        """Affiche la fenêtre de paramètres"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self._create_window()
        self._load_current_settings()

    def _create_window(self):
        """Crée la fenêtre de paramètres"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Paramètres - SnapMaster")
        self.window.geometry("700x600")
        self.window.resizable(True, True)
        self.window.transient(self.parent)
        self.window.grab_set()

        # Centre la fenêtre
        self._center_window()

        # Création du notebook
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Création des onglets
        self._create_general_tab()
        self._create_capture_tab()
        self._create_hotkeys_tab()
        self._create_folders_tab()
        self._create_memory_tab()
        self._create_advanced_tab()

        # Boutons de contrôle
        self._create_control_buttons()

        # Gestionnaire de fermeture
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_general_tab(self):
        """Crée l'onglet général"""
        general_frame = ttk.Frame(self.notebook)
        self.notebook.add(general_frame, text="Général")

        # Interface utilisateur
        ui_frame = ttk.LabelFrame(general_frame, text="Interface utilisateur")
        ui_frame.pack(fill=tk.X, padx=10, pady=5)

        # Thème
        theme_frame = ttk.Frame(ui_frame)
        theme_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(theme_frame, text="Thème:").pack(side=tk.LEFT)
        self.vars['theme'] = tk.StringVar()
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.vars['theme'],
                                   values=['light', 'dark'], state='readonly', width=10)
        theme_combo.pack(side=tk.LEFT, padx=5)

        # Langue
        lang_frame = ttk.Frame(ui_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(lang_frame, text="Langue:").pack(side=tk.LEFT)
        self.vars['language'] = tk.StringVar()
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.vars['language'],
                                  values=['fr', 'en', 'es'], state='readonly', width=10)
        lang_combo.pack(side=tk.LEFT, padx=5)

        # Options d'affichage
        display_frame = ttk.LabelFrame(general_frame, text="Affichage")
        display_frame.pack(fill=tk.X, padx=10, pady=5)

        self.vars['show_notifications'] = tk.BooleanVar()
        ttk.Checkbutton(display_frame, text="Afficher les notifications",
                        variable=self.vars['show_notifications']).pack(anchor=tk.W, padx=5, pady=2)

        self.vars['minimize_to_tray'] = tk.BooleanVar()
        ttk.Checkbutton(display_frame, text="Réduire dans la barre système",
                        variable=self.vars['minimize_to_tray']).pack(anchor=tk.W, padx=5, pady=2)

        self.vars['auto_start'] = tk.BooleanVar()
        ttk.Checkbutton(display_frame, text="Démarrer avec Windows",
                        variable=self.vars['auto_start']).pack(anchor=tk.W, padx=5, pady=2)

    def _create_capture_tab(self):
        """Crée l'onglet de capture"""
        capture_frame = ttk.Frame(self.notebook)
        self.notebook.add(capture_frame, text="Capture")

        # Format et qualité
        format_frame = ttk.LabelFrame(capture_frame, text="Format d'image")
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        # Format
        fmt_frame = ttk.Frame(format_frame)
        fmt_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(fmt_frame, text="Format par défaut:").pack(side=tk.LEFT)
        self.vars['image_format'] = tk.StringVar()
        fmt_combo = ttk.Combobox(fmt_frame, textvariable=self.vars['image_format'],
                                 values=['PNG', 'JPEG', 'BMP', 'GIF'], state='readonly', width=10)
        fmt_combo.pack(side=tk.LEFT, padx=5)

        # Qualité
        quality_frame = ttk.Frame(format_frame)
        quality_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(quality_frame, text="Qualité JPEG:").pack(side=tk.LEFT)
        self.vars['image_quality'] = tk.IntVar()
        quality_scale = ttk.Scale(quality_frame, from_=10, to=100,
                                  variable=self.vars['image_quality'], orient=tk.HORIZONTAL, length=200)
        quality_scale.pack(side=tk.LEFT, padx=5)
        quality_scale.bind('<Motion>', self._on_quality_change)

        self.quality_label = ttk.Label(quality_frame, text="95%")
        self.quality_label.pack(side=tk.LEFT, padx=5)

        # Options de capture
        options_frame = ttk.LabelFrame(capture_frame, text="Options de capture")
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        self.vars['include_cursor'] = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Inclure le curseur de souris",
                        variable=self.vars['include_cursor']).pack(anchor=tk.W, padx=5, pady=2)

        self.vars['auto_filename'] = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Nommage automatique des fichiers",
                        variable=self.vars['auto_filename']).pack(anchor=tk.W, padx=5, pady=2)

        # Délai de capture
        delay_frame = ttk.Frame(options_frame)
        delay_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(delay_frame, text="Délai de capture (secondes):").pack(side=tk.LEFT)
        self.vars['delay_seconds'] = tk.IntVar()
        delay_spin = ttk.Spinbox(delay_frame, from_=0, to=10, textvariable=self.vars['delay_seconds'],
                                 width=5)
        delay_spin.pack(side=tk.LEFT, padx=5)

        # Pattern de nom de fichier
        filename_frame = ttk.LabelFrame(capture_frame, text="Nommage des fichiers")
        filename_frame.pack(fill=tk.X, padx=10, pady=5)

        pattern_frame = ttk.Frame(filename_frame)
        pattern_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(pattern_frame, text="Pattern:").pack(side=tk.LEFT)
        self.vars['filename_pattern'] = tk.StringVar()
        pattern_entry = ttk.Entry(pattern_frame, textvariable=self.vars['filename_pattern'], width=30)
        pattern_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Aide pour le pattern
        help_label = ttk.Label(filename_frame,
                               text="Variables: %Y=année, %m=mois, %d=jour, %H=heure, %M=minute, %S=seconde",
                               font=('Arial', 8))
        help_label.pack(anchor=tk.W, padx=5, pady=2)

    def _create_hotkeys_tab(self):
        """Crée l'onglet des raccourcis clavier"""
        hotkeys_frame = ttk.Frame(self.notebook)
        self.notebook.add(hotkeys_frame, text="Raccourcis")

        # Liste des actions
        actions_frame = ttk.LabelFrame(hotkeys_frame, text="Raccourcis clavier")
        actions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview pour les hotkeys
        columns = ('action', 'hotkey', 'description')
        self.hotkeys_tree = ttk.Treeview(actions_frame, columns=columns, show='headings', height=8)
        self.hotkeys_tree.heading('action', text='Action')
        self.hotkeys_tree.heading('hotkey', text='Raccourci')
        self.hotkeys_tree.heading('description', text='Description')
        self.hotkeys_tree.column('action', width=150)
        self.hotkeys_tree.column('hotkey', width=120)
        self.hotkeys_tree.column('description', width=250)

        hotkeys_scrollbar = ttk.Scrollbar(actions_frame, orient=tk.VERTICAL,
                                          command=self.hotkeys_tree.yview)
        self.hotkeys_tree.configure(yscrollcommand=hotkeys_scrollbar.set)

        self.hotkeys_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        hotkeys_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # Bind double-click pour modification rapide
        self.hotkeys_tree.bind('<Double-1>', lambda e: self._edit_hotkey())

        # Boutons de gestion
        hotkeys_buttons_frame = ttk.Frame(actions_frame)
        hotkeys_buttons_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(hotkeys_buttons_frame, text="✏️ Modifier",
                   command=self._edit_hotkey).pack(side=tk.LEFT, padx=2)
        ttk.Button(hotkeys_buttons_frame, text="🔄 Réinitialiser",
                   command=self._reset_hotkey).pack(side=tk.LEFT, padx=2)
        ttk.Button(hotkeys_buttons_frame, text="🧪 Tester",
                   command=self._test_hotkey).pack(side=tk.LEFT, padx=2)

        # Informations
        info_frame = ttk.LabelFrame(hotkeys_frame, text="Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        info_text = ("Double-cliquez sur un raccourci pour le modifier.\n"
                     "Utilisez les modificateurs: Ctrl, Shift, Alt, Win\n"
                     "Exemple: Ctrl+Shift+S")
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(padx=5, pady=5)

        self._populate_hotkeys_tree()

    def _create_folders_tab(self):
        """Crée l'onglet des dossiers"""
        folders_frame = ttk.Frame(self.notebook)
        self.notebook.add(folders_frame, text="Dossiers")

        # Dossier par défaut
        default_frame = ttk.LabelFrame(folders_frame, text="Dossier par défaut")
        default_frame.pack(fill=tk.X, padx=10, pady=5)

        default_path_frame = ttk.Frame(default_frame)
        default_path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.vars['default_screenshots'] = tk.StringVar()
        default_entry = ttk.Entry(default_path_frame, textvariable=self.vars['default_screenshots'],
                                  state='readonly')
        default_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(default_path_frame, text="Parcourir",
                   command=self._browse_default_folder).pack(side=tk.RIGHT)

        # Dossiers personnalisés
        custom_frame = ttk.LabelFrame(folders_frame, text="Dossiers personnalisés")
        custom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Liste des dossiers
        folders_list_frame = ttk.Frame(custom_frame)
        folders_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('name', 'path')
        self.folders_tree = ttk.Treeview(folders_list_frame, columns=columns, show='headings', height=8)
        self.folders_tree.heading('name', text='Nom')
        self.folders_tree.heading('path', text='Chemin')
        self.folders_tree.column('name', width=150)
        self.folders_tree.column('path', width=350)

        folders_scrollbar = ttk.Scrollbar(folders_list_frame, orient=tk.VERTICAL,
                                          command=self.folders_tree.yview)
        self.folders_tree.configure(yscrollcommand=folders_scrollbar.set)

        self.folders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        folders_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Boutons de gestion des dossiers
        folders_buttons_frame = ttk.Frame(custom_frame)
        folders_buttons_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(folders_buttons_frame, text="➕ Ajouter",
                   command=self._add_custom_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(folders_buttons_frame, text="✏️ Modifier",
                   command=self._edit_custom_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(folders_buttons_frame, text="🗑️ Supprimer",
                   command=self._remove_custom_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(folders_buttons_frame, text="📂 Ouvrir",
                   command=self._open_custom_folder).pack(side=tk.LEFT, padx=2)

        self._populate_folders_tree()

    def _create_memory_tab(self):
        """Crée l'onglet de gestion mémoire"""
        memory_frame = ttk.Frame(self.notebook)
        self.notebook.add(memory_frame, text="Mémoire")

        # Paramètres de surveillance
        monitoring_frame = ttk.LabelFrame(memory_frame, text="Surveillance mémoire")
        monitoring_frame.pack(fill=tk.X, padx=10, pady=5)

        self.vars['auto_cleanup'] = tk.BooleanVar()
        ttk.Checkbutton(monitoring_frame, text="Nettoyage automatique de la mémoire",
                        variable=self.vars['auto_cleanup']).pack(anchor=tk.W, padx=5, pady=2)

        # Seuil mémoire
        threshold_frame = ttk.Frame(monitoring_frame)
        threshold_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(threshold_frame, text="Seuil de nettoyage (MB):").pack(side=tk.LEFT)
        self.vars['memory_threshold_mb'] = tk.IntVar()
        threshold_spin = ttk.Spinbox(threshold_frame, from_=100, to=2000, increment=50,
                                     textvariable=self.vars['memory_threshold_mb'], width=8)
        threshold_spin.pack(side=tk.LEFT, padx=5)

        # Intervalle de vérification
        interval_frame = ttk.Frame(monitoring_frame)
        interval_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(interval_frame, text="Intervalle de vérification (secondes):").pack(side=tk.LEFT)
        self.vars['cleanup_interval_seconds'] = tk.IntVar()
        interval_spin = ttk.Spinbox(interval_frame, from_=10, to=300, increment=10,
                                    textvariable=self.vars['cleanup_interval_seconds'], width=8)
        interval_spin.pack(side=tk.LEFT, padx=5)

        # Optimisations
        optimization_frame = ttk.LabelFrame(memory_frame, text="Optimisations")
        optimization_frame.pack(fill=tk.X, padx=10, pady=5)

        # Informations actuelles
        current_info_frame = ttk.LabelFrame(memory_frame, text="État actuel")
        current_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.memory_info_text = tk.Text(current_info_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        memory_info_scrollbar = ttk.Scrollbar(current_info_frame, orient=tk.VERTICAL,
                                              command=self.memory_info_text.yview)
        self.memory_info_text.configure(yscrollcommand=memory_info_scrollbar.set)

        self.memory_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        memory_info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # Boutons d'action
        memory_buttons_frame = ttk.Frame(current_info_frame)
        memory_buttons_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(memory_buttons_frame, text="🔄 Actualiser",
                   command=self._refresh_memory_info).pack(side=tk.LEFT, padx=2)
        ttk.Button(memory_buttons_frame, text="🧹 Nettoyer",
                   command=self._force_cleanup).pack(side=tk.LEFT, padx=2)

    def _create_advanced_tab(self):
        """Crée l'onglet avancé"""
        advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(advanced_frame, text="Avancé")

        # Debug et logs
        debug_frame = ttk.LabelFrame(advanced_frame, text="Debug et logs")
        debug_frame.pack(fill=tk.X, padx=10, pady=5)

        self.vars['debug_mode'] = tk.BooleanVar()
        ttk.Checkbutton(debug_frame, text="Mode debug",
                        variable=self.vars['debug_mode']).pack(anchor=tk.W, padx=5, pady=2)

        # Niveau de log
        log_level_frame = ttk.Frame(debug_frame)
        log_level_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(log_level_frame, text="Niveau de log:").pack(side=tk.LEFT)
        self.vars['log_level'] = tk.StringVar()
        log_combo = ttk.Combobox(log_level_frame, textvariable=self.vars['log_level'],
                                 values=['DEBUG', 'INFO', 'WARNING', 'ERROR'], state='readonly', width=10)
        log_combo.pack(side=tk.LEFT, padx=5)

        # Sauvegarde
        backup_frame = ttk.LabelFrame(advanced_frame, text="Sauvegarde")
        backup_frame.pack(fill=tk.X, padx=10, pady=5)

        self.vars['backup_settings'] = tk.BooleanVar()
        ttk.Checkbutton(backup_frame, text="Sauvegarder automatiquement les paramètres",
                        variable=self.vars['backup_settings']).pack(anchor=tk.W, padx=5, pady=2)

        # Boutons de gestion
        management_frame = ttk.LabelFrame(advanced_frame, text="Gestion")
        management_frame.pack(fill=tk.X, padx=10, pady=5)

        buttons_frame = ttk.Frame(management_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(buttons_frame, text="📤 Exporter configuration",
                   command=self._export_settings).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="📥 Importer configuration",
                   command=self._import_settings).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="🔄 Réinitialiser tout",
                   command=self._reset_all_settings).pack(side=tk.LEFT, padx=2)

    def _create_control_buttons(self):
        """Crée les boutons de contrôle"""
        buttons_frame = ttk.Frame(self.window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(buttons_frame, text="Annuler",
                   command=self._cancel).pack(side=tk.RIGHT, padx=2)
        ttk.Button(buttons_frame, text="Appliquer",
                   command=self._apply).pack(side=tk.RIGHT, padx=2)
        ttk.Button(buttons_frame, text="OK",
                   command=self._ok).pack(side=tk.RIGHT, padx=2)

    def _load_current_settings(self):
        """Charge les paramètres actuels dans l'interface"""
        try:
            # UI Settings
            ui_settings = self.settings.get_ui_settings()
            self.vars['theme'].set(ui_settings.get('theme', 'dark'))
            self.vars['language'].set(ui_settings.get('language', 'fr'))
            self.vars['show_notifications'].set(ui_settings.get('show_notifications', True))
            self.vars['minimize_to_tray'].set(ui_settings.get('minimize_to_tray', True))
            self.vars['auto_start'].set(ui_settings.get('auto_start', False))

            # Capture Settings
            capture_settings = self.settings.get_capture_settings()
            self.vars['image_format'].set(capture_settings.get('image_format', 'PNG'))
            self.vars['image_quality'].set(capture_settings.get('image_quality', 95))
            self.vars['include_cursor'].set(capture_settings.get('include_cursor', False))
            self.vars['auto_filename'].set(capture_settings.get('auto_filename', True))
            self.vars['delay_seconds'].set(capture_settings.get('delay_seconds', 0))
            self.vars['filename_pattern'].set(capture_settings.get('filename_pattern', 'Screenshot_%Y%m%d_%H%M%S'))

            # Folders
            self.vars['default_screenshots'].set(self.settings.get_default_folder())

            # Memory Settings
            memory_settings = self.settings.get_memory_settings()
            self.vars['auto_cleanup'].set(memory_settings.get('auto_cleanup', True))
            self.vars['memory_threshold_mb'].set(memory_settings.get('memory_threshold_mb', 500))
            self.vars['cleanup_interval_seconds'].set(memory_settings.get('cleanup_interval_seconds', 30))

            # Advanced Settings
            advanced = self.settings.config.get('advanced', {})
            self.vars['debug_mode'].set(advanced.get('debug_mode', False))
            self.vars['log_level'].set(advanced.get('log_level', 'INFO'))
            self.vars['backup_settings'].set(advanced.get('backup_settings', True))

            # Met à jour l'affichage de la qualité
            self._on_quality_change(None)

            # Actualise l'info mémoire
            self._refresh_memory_info()

        except Exception as e:
            self.logger.error(f"Erreur chargement paramètres: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du chargement des paramètres: {e}")

    def _save_settings(self):
        """Sauvegarde les paramètres"""
        try:
            # UI Settings
            self.settings.update_ui_setting('theme', self.vars['theme'].get())
            self.settings.update_ui_setting('language', self.vars['language'].get())
            self.settings.update_ui_setting('show_notifications', self.vars['show_notifications'].get())
            self.settings.update_ui_setting('minimize_to_tray', self.vars['minimize_to_tray'].get())
            self.settings.update_ui_setting('auto_start', self.vars['auto_start'].get())

            # Capture Settings
            self.settings.update_capture_setting('image_format', self.vars['image_format'].get())
            self.settings.update_capture_setting('image_quality', self.vars['image_quality'].get())
            self.settings.update_capture_setting('include_cursor', self.vars['include_cursor'].get())
            self.settings.update_capture_setting('auto_filename', self.vars['auto_filename'].get())
            self.settings.update_capture_setting('delay_seconds', self.vars['delay_seconds'].get())
            self.settings.update_capture_setting('filename_pattern', self.vars['filename_pattern'].get())

            # Memory Settings
            self.settings.config['memory_settings']['auto_cleanup'] = self.vars['auto_cleanup'].get()
            self.settings.config['memory_settings']['memory_threshold_mb'] = self.vars['memory_threshold_mb'].get()
            self.settings.config['memory_settings']['cleanup_interval_seconds'] = self.vars['cleanup_interval_seconds'].get()

            # Advanced Settings
            self.settings.config['advanced']['debug_mode'] = self.vars['debug_mode'].get()
            self.settings.config['advanced']['log_level'] = self.vars['log_level'].get()
            self.settings.config['advanced']['backup_settings'] = self.vars['backup_settings'].get()

            # Sauvegarde
            if self.settings.save_config():
                self.modified = False
                return True
            else:
                messagebox.showerror("Erreur", "Impossible de sauvegarder les paramètres")
                return False

        except Exception as e:
            self.logger.error(f"Erreur sauvegarde paramètres: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
            return False

    # Méthodes d'événements
    def _on_quality_change(self, event):
        """Callback changement de qualité"""
        if hasattr(self, 'quality_label'):
            quality = self.vars['image_quality'].get()
            self.quality_label.config(text=f"{quality}%")

    def _populate_hotkeys_tree(self):
        """Remplit l'arbre des raccourcis"""
        # Nettoie l'arbre
        for item in self.hotkeys_tree.get_children():
            self.hotkeys_tree.delete(item)

        # Actions et descriptions
        actions_desc = {
            'fullscreen_capture': 'Capture plein écran',
            'window_capture': 'Capture fenêtre active',
            'area_capture': 'Capture zone sélectionnée',
            'quick_capture': 'Capture rapide application'
        }

        # Ajoute les items
        for action, description in actions_desc.items():
            hotkey = self.settings.get_hotkey(action)
            self.hotkeys_tree.insert('', tk.END, values=(action, hotkey, description))

    def _populate_folders_tree(self):
        """Remplit l'arbre des dossiers"""
        # Nettoie l'arbre
        for item in self.folders_tree.get_children():
            self.folders_tree.delete(item)

        # Ajoute les dossiers personnalisés
        custom_folders = self.settings.get_custom_folders()
        for name, path in custom_folders.items():
            self.folders_tree.insert('', tk.END, values=(name, path))

    def _refresh_memory_info(self):
        """Actualise les informations mémoire"""
        try:
            # Obtient les stats mémoire (si disponible)
            info_text = "Informations mémoire:\n\n"
            info_text += f"Utilisation actuelle: -- MB\n"
            info_text += f"Seuil configuré: {self.vars['memory_threshold_mb'].get()} MB\n"
            info_text += f"Nettoyage auto: {'Activé' if self.vars['auto_cleanup'].get() else 'Désactivé'}\n"
            info_text += f"Intervalle: {self.vars['cleanup_interval_seconds'].get()}s\n\n"
            info_text += "Statistiques:\n"
            info_text += "- Nettoyages totaux: --\n"
            info_text += "- Mémoire libérée: -- MB\n"
            info_text += "- Dernière opération: --"

            self.memory_info_text.config(state=tk.NORMAL)
            self.memory_info_text.delete(1.0, tk.END)
            self.memory_info_text.insert(1.0, info_text)
            self.memory_info_text.config(state=tk.DISABLED)

        except Exception as e:
            self.logger.error(f"Erreur actualisation mémoire: {e}")

    # Gestionnaires d'événements des raccourcis clavier
    def _edit_hotkey(self):
        """Modifie un raccourci clavier sélectionné"""
        try:
            selection = self.hotkeys_tree.selection()
            if not selection:
                messagebox.showwarning("Sélection", "Veuillez sélectionner un raccourci à modifier")
                return

            item = self.hotkeys_tree.item(selection[0])
            action = item['values'][0]
            current_hotkey = item['values'][1]
            description = item['values'][2]

            # Dialogue pour capturer le nouveau raccourci
            dialog = HotkeyInputDialog(self.window, f"Modifier le raccourci pour: {description}", current_hotkey)
            new_hotkey = dialog.get_result()

            if new_hotkey and new_hotkey != current_hotkey:
                # Valide le nouveau raccourci
                if self._validate_new_hotkey(new_hotkey, action):
                    # Met à jour dans les settings
                    self.settings.set_hotkey(action, new_hotkey)

                    # Met à jour le hotkey manager si disponible
                    if self.hotkey_manager:
                        self.hotkey_manager.update_hotkey(action, new_hotkey)

                    # Actualise l'affichage
                    self._populate_hotkeys_tree()
                    self.modified = True

                    messagebox.showinfo("Succès", f"Raccourci modifié avec succès:\n{description}: {new_hotkey}")
                else:
                    messagebox.showerror("Erreur", "Raccourci invalide ou déjà utilisé")

        except Exception as e:
            self.logger.error(f"Erreur modification hotkey: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la modification: {e}")

    def _reset_hotkey(self):
        """Remet un raccourci à sa valeur par défaut"""
        try:
            selection = self.hotkeys_tree.selection()
            if not selection:
                messagebox.showwarning("Sélection", "Veuillez sélectionner un raccourci à réinitialiser")
                return

            item = self.hotkeys_tree.item(selection[0])
            action = item['values'][0]
            description = item['values'][2]

            # Raccourcis par défaut
            default_hotkeys = {
                'fullscreen_capture': 'ctrl+shift+f',
                'window_capture': 'ctrl+shift+w',
                'area_capture': 'ctrl+shift+a',
                'quick_capture': 'ctrl+shift+q'
            }

            default_hotkey = default_hotkeys.get(action)
            if not default_hotkey:
                messagebox.showerror("Erreur", "Pas de valeur par défaut pour ce raccourci")
                return

            if messagebox.askyesno("Confirmation",
                                   f"Remettre le raccourci à sa valeur par défaut?\n\n{description}: {default_hotkey}"):
                # Met à jour dans les settings
                self.settings.set_hotkey(action, default_hotkey)

                # Met à jour le hotkey manager si disponible
                if self.hotkey_manager:
                    self.hotkey_manager.update_hotkey(action, default_hotkey)

                # Actualise l'affichage
                self._populate_hotkeys_tree()
                self.modified = True

                messagebox.showinfo("Succès", "Raccourci réinitialisé avec succès")

        except Exception as e:
            self.logger.error(f"Erreur reset hotkey: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la réinitialisation: {e}")

    def _test_hotkey(self):
        """Teste un raccourci clavier"""
        try:
            selection = self.hotkeys_tree.selection()
            if not selection:
                messagebox.showwarning("Sélection", "Veuillez sélectionner un raccourci à tester")
                return

            item = self.hotkeys_tree.item(selection[0])
            action = item['values'][0]
            hotkey = item['values'][1]
            description = item['values'][2]

            # Teste la validité du raccourci
            if self.hotkey_manager:
                if self.hotkey_manager.test_hotkey(hotkey):
                    messagebox.showinfo("Test réussi",
                                        f"Le raccourci est valide:\n\n{description}: {hotkey}\n\n"
                                        f"Appuyez sur '{hotkey}' pour tester la fonctionnalité.")
                else:
                    messagebox.showerror("Test échoué", f"Le raccourci '{hotkey}' n'est pas valide")
            else:
                messagebox.showinfo("Test", f"Raccourci: {hotkey}\nAction: {description}\n\nGestionnaire non disponible pour le test")

        except Exception as e:
            self.logger.error(f"Erreur test hotkey: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du test: {e}")

    def _validate_new_hotkey(self, hotkey: str, current_action: str) -> bool:
        """Valide un nouveau raccourci clavier"""
        try:
            # Vérifie le format du raccourci
            if not hotkey or not hotkey.strip():
                return False

            # Vérifie qu'il n'est pas déjà utilisé par une autre action
            current_hotkeys = {}
            for action in ['fullscreen_capture', 'window_capture', 'area_capture', 'quick_capture']:
                if action != current_action:  # Ignore l'action courante
                    current_hotkeys[action] = self.settings.get_hotkey(action)

            if hotkey.lower() in [h.lower() for h in current_hotkeys.values() if h]:
                return False

            # Teste la validité avec le hotkey manager si disponible
            if self.hotkey_manager:
                return self.hotkey_manager.test_hotkey(hotkey)

            return True

        except Exception as e:
            self.logger.error(f"Erreur validation hotkey: {e}")
            return False

    # Gestionnaires d'événements (stubs pour éviter les erreurs)
    def _browse_default_folder(self): pass
    def _add_custom_folder(self): pass
    def _edit_custom_folder(self): pass
    def _remove_custom_folder(self): pass
    def _open_custom_folder(self): pass
    def _force_cleanup(self): pass
    def _export_settings(self): pass
    def _import_settings(self): pass
    def _reset_all_settings(self): pass

    def _center_window(self):
        """Centre la fenêtre"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _on_close(self):
        """Gestionnaire fermeture fenêtre"""
        if self.modified:
            result = messagebox.askyesnocancel(
                "Paramètres modifiés",
                "Des paramètres ont été modifiés. Voulez-vous les sauvegarder?"
            )
            if result is True:  # Oui
                if self._save_settings():
                    self.window.destroy()
            elif result is False:  # Non
                self.window.destroy()
            # Annuler = ne fait rien
        else:
            self.window.destroy()

    def _cancel(self):
        """Annule les modifications"""
        self._on_close()

    def _apply(self):
        """Applique les paramètres sans fermer"""
        if self._save_settings():
            messagebox.showinfo("Succès", "Paramètres sauvegardés avec succès")

    def _ok(self):
        """OK - sauvegarde et ferme"""
        if self._save_settings():
            self.window.destroy()


class HotkeyInputDialog:
    """Dialogue pour capturer un raccourci clavier"""

    def __init__(self, parent, title: str, current_hotkey: str = ""):
        self.parent = parent
        self.title = title
        self.current_hotkey = current_hotkey
        self.result = None
        self.window = None

        # Variables pour capturer les touches
        self.pressed_keys = set()
        self.modifier_keys = {'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R', 'Super_L', 'Super_R'}
        self.capturing = False

    def get_result(self):
        """Affiche le dialogue et retourne le résultat"""
        self._create_dialog()
        self.window.wait_window()
        return self.result

    def _create_dialog(self):
        """Crée le dialogue de capture"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Modifier le raccourci")
        self.window.geometry("400x200")
        self.window.resizable(False, False)
        self.window.transient(self.parent)
        self.window.grab_set()

        # Centre le dialogue
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

        # Titre
        title_label = tk.Label(self.window, text=self.title, font=('Arial', 12, 'bold'))
        title_label.pack(pady=10)

        # Affichage du raccourci actuel
        if self.current_hotkey:
            current_label = tk.Label(self.window, text=f"Raccourci actuel: {self.current_hotkey}",
                                     font=('Arial', 10))
            current_label.pack(pady=5)

        # Zone de capture
        self.capture_frame = tk.Frame(self.window, bg='#f0f0f0', relief='sunken', bd=2)
        self.capture_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.capture_label = tk.Label(self.capture_frame,
                                      text="Cliquez ici et appuyez sur votre nouveau raccourci\n\n"
                                           "Exemples: Ctrl+S, Ctrl+Shift+A, Alt+F4",
                                      font=('Arial', 10),
                                      bg='#f0f0f0',
                                      fg='#666666')
        self.capture_label.pack(expand=True)

        # Zone d'affichage du raccourci capturé
        self.result_label = tk.Label(self.window, text="", font=('Arial', 11, 'bold'), fg='blue')
        self.result_label.pack(pady=5)

        # Boutons
        buttons_frame = tk.Frame(self.window)
        buttons_frame.pack(pady=10)

        tk.Button(buttons_frame, text="OK", command=self._ok, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Annuler", command=self._cancel, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Effacer", command=self._clear, width=10).pack(side=tk.LEFT, padx=5)

        # Événements de capture
        self.capture_frame.bind("<Button-1>", self._start_capture)
        self.capture_frame.bind("<FocusIn>", self._start_capture)
        self.window.bind("<KeyPress>", self._on_key_press)
        self.window.bind("<KeyRelease>", self._on_key_release)

        # Focus sur la zone de capture
        self.capture_frame.focus_set()

    def _start_capture(self, event=None):
        """Démarre la capture de raccourci"""
        self.capturing = True
        self.pressed_keys.clear()
        self.capture_label.config(text="Appuyez sur votre raccourci...", fg='red')
        self.result_label.config(text="")
        self.window.focus_set()

    def _on_key_press(self, event):
        """Gère l'appui sur une touche"""
        if not self.capturing:
            return

        key = event.keysym
        self.pressed_keys.add(key)

        # Met à jour l'affichage en temps réel
        self._update_display()

    def _on_key_release(self, event):
        """Gère le relâchement d'une touche"""
        if not self.capturing:
            return

        key = event.keysym

        # Si c'est une touche modificatrice, on continue à capturer
        if key in self.modifier_keys:
            return

        # Sinon, on finit la capture
        self._finish_capture()

    def _update_display(self):
        """Met à jour l'affichage du raccourci en cours"""
        if not self.pressed_keys:
            return

        # Sépare les modificateurs des autres touches
        modifiers = []
        other_keys = []

        for key in self.pressed_keys:
            if key in self.modifier_keys:
                # Simplifie les noms des modificateurs
                if key.startswith('Control'):
                    if 'ctrl' not in [m.lower() for m in modifiers]:
                        modifiers.append('Ctrl')
                elif key.startswith('Alt'):
                    if 'alt' not in [m.lower() for m in modifiers]:
                        modifiers.append('Alt')
                elif key.startswith('Shift'):
                    if 'shift' not in [m.lower() for m in modifiers]:
                        modifiers.append('Shift')
                elif key.startswith('Super'):
                    if 'win' not in [m.lower() for m in modifiers]:
                        modifiers.append('Win')
            else:
                other_keys.append(key)

        # Construit la chaîne de raccourci
        if modifiers or other_keys:
            hotkey_parts = modifiers + other_keys
            hotkey_str = '+'.join(hotkey_parts)
            self.result_label.config(text=hotkey_str)

    def _finish_capture(self):
        """Termine la capture et génère le raccourci"""
        self.capturing = False

        if not self.pressed_keys:
            return

        # Génère le raccourci final
        modifiers = []
        main_key = None

        for key in self.pressed_keys:
            if key in self.modifier_keys:
                if key.startswith('Control'):
                    if 'ctrl' not in modifiers:
                        modifiers.append('ctrl')
                elif key.startswith('Alt'):
                    if 'alt' not in modifiers:
                        modifiers.append('alt')
                elif key.startswith('Shift'):
                    if 'shift' not in modifiers:
                        modifiers.append('shift')
                elif key.startswith('Super'):
                    if 'win' not in modifiers:
                        modifiers.append('win')
            else:
                main_key = key.lower()

        if main_key and modifiers:
            # Crée le raccourci au format standard
            hotkey = '+'.join(modifiers + [main_key])
            self.result_label.config(text=hotkey.title(), fg='green')
            self.capture_label.config(text="Raccourci capturé! Cliquez OK pour confirmer.", fg='green')
            self.result = hotkey
        else:
            self.capture_label.config(text="Raccourci invalide. Essayez de nouveau.", fg='red')
            self.result_label.config(text="")

    def _clear(self):
        """Efface la capture"""
        self.pressed_keys.clear()
        self.result = None
        self.capturing = False
        self.capture_label.config(text="Cliquez ici et appuyez sur votre nouveau raccourci", fg='#666666')
        self.result_label.config(text="")

    def _ok(self):
        """Confirme le raccourci"""
        if self.result:
            self.window.destroy()
        else:
            messagebox.showwarning("Aucun raccourci", "Veuillez d'abord capturer un raccourci")

    def _cancel(self):
        """Annule la modification"""
        self.result = None
        self.window.destroy()