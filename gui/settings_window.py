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
    
    # Gestionnaires d'événements (stubs pour éviter les erreurs)
    def _edit_hotkey(self): pass
    def _reset_hotkey(self): pass  
    def _test_hotkey(self): pass
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