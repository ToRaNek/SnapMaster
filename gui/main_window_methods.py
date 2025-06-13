# gui/main_window_methods.py
"""
Méthodes supplémentaires pour SnapMasterGUI - Version améliorée
Complément à main_window.py avec support des associations avancées
"""

import os
import subprocess
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import threading
import time
import platform
import psutil

def add_methods_to_gui(gui_class):
    """Ajoute les méthodes manquantes à la classe SnapMasterGUI"""

    def _open_screenshots_folder(self):
        """Ouvre le dossier de captures d'écran"""
        try:
            folder_path = self.settings.get_default_folder()
            if not Path(folder_path).exists():
                Path(folder_path).mkdir(parents=True, exist_ok=True)

            # Ouvre le dossier selon l'OS
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # Linux/macOS
                if platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', folder_path])
                else:  # Linux
                    subprocess.run(['xdg-open', folder_path])

        except Exception as e:
            self.logger.error(f"Erreur ouverture dossier: {e}")
            self._show_error("Erreur", f"Impossible d'ouvrir le dossier: {e}")

    def _export_config(self):
        """Exporte la configuration"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Exporter la configuration",
                defaultextension=".json",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
            )

            if filename:
                if self.settings.export_config(filename):
                    messagebox.showinfo("Succès", "Configuration exportée avec succès")
                else:
                    messagebox.showerror("Erreur", "Erreur lors de l'export")

        except Exception as e:
            self.logger.error(f"Erreur export config: {e}")
            self._show_error("Erreur", str(e))

    def _import_config(self):
        """Importe une configuration"""
        try:
            filename = filedialog.askopenfilename(
                title="Importer une configuration",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
            )

            if filename:
                if messagebox.askyesno("Confirmation",
                                       "Cela remplacera la configuration actuelle. Continuer?"):
                    if self.settings.import_config(filename):
                        messagebox.showinfo("Succès",
                                            "Configuration importée. Redémarrez l'application.")
                    else:
                        messagebox.showerror("Erreur", "Erreur lors de l'import")

        except Exception as e:
            self.logger.error(f"Erreur import config: {e}")
            self._show_error("Erreur", str(e))

    def _test_capabilities(self):
        """Teste les capacités de capture"""
        def test_thread():
            self._update_status("🧪 Test des capacités en cours...")

            capabilities = self.screenshot_manager.test_capture_capability()
            app_caps = self.app_detector.get_capabilities()

            def show_results():
                result_text = "🧪 Résultats des tests de capacités:\n\n"
                result_text += "📸 Captures d'écran:\n"
                result_text += f"  • Plein écran: {'✅ Disponible' if capabilities.get('fullscreen') else '❌ Indisponible'}\n"
                result_text += f"  • Fenêtre: {'✅ Disponible' if capabilities.get('window') else '❌ Indisponible'}\n"
                result_text += f"  • Zone sélectionnée: {'✅ Disponible' if capabilities.get('area_selection') else '❌ Indisponible'}\n"
                result_text += f"  • Détection d'app: {'✅ Disponible' if capabilities.get('app_detection') else '❌ Indisponible'}\n\n"

                result_text += "🔍 Détection d'applications:\n"
                result_text += f"  • Détection fenêtre: {'✅ Disponible' if app_caps.get('window_detection') else '❌ Indisponible'}\n"
                result_text += f"  • Détection plein écran: {'✅ Disponible' if app_caps.get('fullscreen_detection') else '❌ Indisponible'}\n"
                result_text += f"  • Géométrie fenêtre: {'✅ Disponible' if app_caps.get('window_geometry') else '❌ Indisponible'}\n"
                result_text += f"  • Classification app: {'✅ Disponible' if app_caps.get('app_classification') else '❌ Indisponible'}\n\n"

                # Test hotkeys
                hotkey_stats = self.hotkey_manager.get_stats()
                result_text += "⌨️ Raccourcis clavier:\n"
                result_text += f"  • Surveillance active: {'✅ Active' if hotkey_stats.get('monitoring') else '❌ Inactive'}\n"
                result_text += f"  • Raccourcis actifs: {hotkey_stats.get('active_hotkeys', 0)}\n"
                result_text += f"  • Déclenchements: {hotkey_stats.get('total_triggers', 0)}\n"

                # Test des permissions
                result_text += f"\n🔐 Permissions système:\n"
                result_text += f"  • Lecture processus: {'✅ OK' if self._test_process_access() else '❌ Limitée'}\n"
                result_text += f"  • Capture écran: {'✅ OK' if self._test_screen_access() else '❌ Limitée'}\n"

                messagebox.showinfo("Test des capacités", result_text)
                self._update_status("✅ Test terminé")

            self.root.after(0, show_results)

        threading.Thread(target=test_thread, daemon=True).start()

    def _test_process_access(self):
        """Teste l'accès aux informations des processus"""
        try:
            process_count = len(list(psutil.process_iter()))
            return process_count > 10  # Au moins 10 processus détectés
        except:
            return False

    def _test_screen_access(self):
        """Teste l'accès à la capture d'écran"""
        try:
            import pyautogui
            test_screenshot = pyautogui.screenshot()
            return test_screenshot.size[0] > 0 and test_screenshot.size[1] > 0
        except:
            return False

    def _open_settings(self):
        """Ouvre la fenêtre de paramètres"""
        if not self.settings_window:
            try:
                from gui.settings_window import SettingsWindow
                self.settings_window = SettingsWindow(self.root, self.settings, self.hotkey_manager)
            except ImportError:
                messagebox.showinfo("Paramètres", "Fenêtre de paramètres non disponible")
                return

        self.settings_window.show()

    def _open_folder_manager(self):
        """Ouvre le gestionnaire de dossiers"""
        dialog = FolderManagerDialog(self.root, self.settings)
        dialog.show()

    def _force_memory_cleanup(self):
        """Force le nettoyage mémoire"""
        def cleanup_thread():
            self._update_status("🧹 Nettoyage mémoire en cours...")

            before_memory = self.memory_manager.get_current_memory_usage()
            cleaned_objects = self.memory_manager.force_cleanup()
            after_memory = self.memory_manager.get_current_memory_usage()

            freed_memory = max(0, before_memory - after_memory)

            def show_result():
                message = f"🧹 Nettoyage mémoire terminé:\n\n"
                message += f"💾 Mémoire avant: {before_memory:.1f} MB\n"
                message += f"💾 Mémoire après: {after_memory:.1f} MB\n"
                message += f"🗑️ Objets nettoyés: {cleaned_objects}\n"
                message += f"💨 Mémoire libérée: {freed_memory:.1f} MB"

                if freed_memory > 10:
                    message += f"\n\n✅ Nettoyage efficace!"
                elif freed_memory > 0:
                    message += f"\n\n🔄 Nettoyage partiel"
                else:
                    message += f"\n\n💡 Aucune mémoire à libérer"

                messagebox.showinfo("Nettoyage mémoire", message)
                self._update_status("✅ Nettoyage terminé")

            self.root.after(0, show_result)

        threading.Thread(target=cleanup_thread, daemon=True).start()

    def _show_statistics(self):
        """Affiche les statistiques détaillées"""
        try:
            # Collecte les statistiques
            screenshot_stats = self.screenshot_manager.get_stats()
            memory_stats = self.memory_manager.get_stats()
            hotkey_stats = self.hotkey_manager.get_stats()

            # Crée la fenêtre de statistiques
            stats_window = tk.Toplevel(self.root)
            stats_window.title("📊 Statistiques SnapMaster")
            stats_window.geometry("600x500")
            stats_window.resizable(False, False)
            stats_window.transient(self.root)
            stats_window.configure(bg='#1a202c')

            # Centre la fenêtre
            stats_window.update_idletasks()
            x = (stats_window.winfo_screenwidth() // 2) - (stats_window.winfo_width() // 2)
            y = (stats_window.winfo_screenheight() // 2) - (stats_window.winfo_height() // 2)
            stats_window.geometry(f"+{x}+{y}")

            # En-tête
            header_frame = tk.Frame(stats_window, bg='#1e3a8a', height=60)
            header_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
            header_frame.pack_propagate(False)

            tk.Label(header_frame,
                     text="📊 Statistiques détaillées",
                     bg='#1e3a8a',
                     fg='white',
                     font=('Segoe UI', 16, 'bold')).pack(expand=True, pady=15)

            # Contenu avec scrollbar
            content_frame = tk.Frame(stats_window, bg='#1a202c')
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Zone de texte avec scrollbar
            text_frame = tk.Frame(content_frame, bg='#1a202c')
            text_frame.pack(fill=tk.BOTH, expand=True)

            text_widget = tk.Text(text_frame,
                                  wrap=tk.WORD,
                                  padx=15,
                                  pady=15,
                                  bg='#2d3748',
                                  fg='white',
                                  font=('Consolas', 10),
                                  relief='flat',
                                  bd=0)

            scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)

            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Contenu des statistiques
            stats_text = self._generate_stats_text(screenshot_stats, memory_stats, hotkey_stats)
            text_widget.insert(1.0, stats_text)
            text_widget.config(state=tk.DISABLED)

            # Boutons
            buttons_frame = tk.Frame(stats_window, bg='#1a202c')
            buttons_frame.pack(fill=tk.X, padx=10, pady=10)

            tk.Button(buttons_frame,
                      text="🔄 Actualiser",
                      command=lambda: self._refresh_statistics(text_widget),
                      bg='#3b82f6',
                      fg='white',
                      font=('Segoe UI', 10, 'bold'),
                      relief='flat',
                      padx=15,
                      pady=8).pack(side=tk.LEFT, padx=5)

            tk.Button(buttons_frame,
                      text="📋 Copier",
                      command=lambda: self._copy_statistics(stats_text),
                      bg='#10b981',
                      fg='white',
                      font=('Segoe UI', 10, 'bold'),
                      relief='flat',
                      padx=15,
                      pady=8).pack(side=tk.LEFT, padx=5)

            tk.Button(buttons_frame,
                      text="❌ Fermer",
                      command=stats_window.destroy,
                      bg='#ef4444',
                      fg='white',
                      font=('Segoe UI', 10, 'bold'),
                      relief='flat',
                      padx=15,
                      pady=8).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            self.logger.error(f"Erreur affichage statistiques: {e}")
            self._show_error("Erreur", str(e))

    def _generate_stats_text(self, screenshot_stats, memory_stats, hotkey_stats):
        """Génère le texte des statistiques"""
        stats_text = "📊 STATISTIQUES SNAPMASTER\n"
        stats_text += "=" * 50 + "\n\n"

        # Stats captures
        stats_text += "📸 CAPTURES D'ÉCRAN\n"
        stats_text += "-" * 30 + "\n"
        stats_text += f"Total des captures      : {screenshot_stats.get('total_captures', 0)}\n"
        stats_text += f"Captures réussies       : {screenshot_stats.get('successful_captures', 0)}\n"
        stats_text += f"Captures échouées       : {screenshot_stats.get('failed_captures', 0)}\n"
        stats_text += f"Taux de réussite        : {self._calculate_success_rate(screenshot_stats):.1f}%\n"
        stats_text += f"Utilisation mémoire     : {screenshot_stats.get('memory_usage_mb', 0):.1f} MB\n\n"

        # Stats mémoire
        stats_text += "🧠 GESTION MÉMOIRE\n"
        stats_text += "-" * 30 + "\n"
        stats_text += f"Usage actuel            : {memory_stats.get('current_memory_mb', 0):.1f} MB\n"
        stats_text += f"Nettoyages effectués    : {memory_stats.get('total_cleanups', 0)}\n"
        stats_text += f"Mémoire libérée (total) : {memory_stats.get('memory_saved_mb', 0):.1f} MB\n"
        stats_text += f"Surveillance active     : {'✅ Oui' if memory_stats.get('monitoring') else '❌ Non'}\n"

        # Objets trackés
        tracked_objects = memory_stats.get('tracked_objects', {})
        if tracked_objects:
            stats_text += f"Objets trackés          :\n"
            for category, count in tracked_objects.items():
                stats_text += f"  - {category}: {count}\n"
        stats_text += "\n"

        # Stats hotkeys
        stats_text += "⌨️ RACCOURCIS CLAVIER\n"
        stats_text += "-" * 30 + "\n"
        stats_text += f"Raccourcis actifs       : {hotkey_stats.get('active_hotkeys', 0)}\n"
        stats_text += f"Déclenchements totaux   : {hotkey_stats.get('total_triggers', 0)}\n"
        stats_text += f"Déclenchements réussis  : {hotkey_stats.get('successful_triggers', 0)}\n"
        stats_text += f"Répétitions bloquées    : {hotkey_stats.get('blocked_repeats', 0)}\n"
        stats_text += f"Surveillance active     : {'✅ Oui' if hotkey_stats.get('monitoring') else '❌ Non'}\n"
        stats_text += f"Callbacks enregistrés   : {hotkey_stats.get('registered_callbacks', 0)}\n\n"

        # Informations système
        stats_text += "🖥️ SYSTÈME\n"
        stats_text += "-" * 30 + "\n"
        stats_text += f"Système d'exploitation  : {platform.system()} {platform.release()}\n"
        stats_text += f"Architecture            : {platform.architecture()[0]}\n"
        stats_text += f"Processeur              : {platform.processor()}\n"
        stats_text += f"Nom de la machine       : {platform.node()}\n"
        stats_text += f"Python                  : {platform.python_version()}\n"

        # Informations de performance
        try:
            import psutil
            stats_text += f"Processus actifs        : {len(list(psutil.process_iter()))}\n"
            stats_text += f"Utilisation CPU         : {psutil.cpu_percent()}%\n"
            stats_text += f"Mémoire système         : {psutil.virtual_memory().percent}%\n"
        except:
            pass

        stats_text += "\n"

        # Configuration actuelle
        stats_text += "⚙️ CONFIGURATION\n"
        stats_text += "-" * 30 + "\n"
        capture_settings = self.settings.get_capture_settings()
        stats_text += f"Format d'image          : {capture_settings.get('image_format', 'PNG')}\n"
        stats_text += f"Qualité d'image         : {capture_settings.get('image_quality', 95)}%\n"
        stats_text += f"Inclure curseur         : {'✅ Oui' if capture_settings.get('include_cursor') else '❌ Non'}\n"
        stats_text += f"Délai de capture        : {capture_settings.get('delay_seconds', 0)}s\n"
        stats_text += f"Dossier par défaut      : {self.settings.get_default_folder()}\n"
        stats_text += f"Dossiers personnalisés  : {len(self.settings.get_custom_folders())}\n"
        stats_text += f"Associations d'apps     : {len(self.settings.config.get('applications', {}).get('app_folder_mapping', {}))}\n"

        return stats_text

    def _refresh_statistics(self, text_widget):
        """Actualise les statistiques"""
        try:
            screenshot_stats = self.screenshot_manager.get_stats()
            memory_stats = self.memory_manager.get_stats()
            hotkey_stats = self.hotkey_manager.get_stats()

            stats_text = self._generate_stats_text(screenshot_stats, memory_stats, hotkey_stats)

            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.insert(1.0, stats_text)
            text_widget.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'actualisation: {e}")

    def _copy_statistics(self, stats_text):
        """Copie les statistiques dans le presse-papier"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(stats_text)
            messagebox.showinfo("Copié", "Statistiques copiées dans le presse-papier")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la copie: {e}")

    def _calculate_success_rate(self, stats):
        """Calcule le taux de réussite"""
        total = stats.get('total_captures', 0)
        if total == 0:
            return 0.0
        successful = stats.get('successful_captures', 0)
        return (successful / total) * 100

    def _show_hotkeys(self):
        """Affiche les raccourcis clavier dans une fenêtre moderne"""
        try:
            active_hotkeys = self.hotkey_manager.get_active_hotkeys()

            # Crée la fenêtre
            hotkeys_window = tk.Toplevel(self.root)
            hotkeys_window.title("⌨️ Raccourcis clavier")
            hotkeys_window.geometry("500x400")
            hotkeys_window.resizable(False, False)
            hotkeys_window.transient(self.root)
            hotkeys_window.configure(bg='#1a202c')

            # Centre la fenêtre
            hotkeys_window.update_idletasks()
            x = (hotkeys_window.winfo_screenwidth() // 2) - (hotkeys_window.winfo_width() // 2)
            y = (hotkeys_window.winfo_screenheight() // 2) - (hotkeys_window.winfo_height() // 2)
            hotkeys_window.geometry(f"+{x}+{y}")

            # En-tête
            header_frame = tk.Frame(hotkeys_window, bg='#1e3a8a', height=60)
            header_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
            header_frame.pack_propagate(False)

            tk.Label(header_frame,
                     text="⌨️ Raccourcis clavier actifs",
                     bg='#1e3a8a',
                     fg='white',
                     font=('Segoe UI', 16, 'bold')).pack(expand=True, pady=15)

            # Contenu
            content_frame = tk.Frame(hotkeys_window, bg='#2d3748', relief='flat', bd=2)
            content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

            descriptions = {
                'fullscreen_capture': '🖥️ Capture plein écran',
                'window_capture': '🪟 Capture fenêtre active',
                'area_capture': '✂️ Capture zone sélectionnée',
                'quick_capture': '⚡ Capture rapide application'
            }

            if active_hotkeys:
                for i, (action, hotkey) in enumerate(active_hotkeys.items()):
                    desc = descriptions.get(action, action)

                    # Frame pour chaque raccourci
                    hotkey_frame = tk.Frame(content_frame, bg='#374151', relief='flat', bd=1)
                    hotkey_frame.pack(fill=tk.X, padx=10, pady=5)

                    # Description
                    tk.Label(hotkey_frame,
                             text=desc,
                             bg='#374151',
                             fg='white',
                             font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT, padx=15, pady=10)

                    # Raccourci
                    tk.Label(hotkey_frame,
                             text=hotkey.upper(),
                             bg='#3b82f6',
                             fg='white',
                             font=('Segoe UI', 11, 'bold'),
                             relief='flat',
                             padx=10,
                             pady=5).pack(side=tk.RIGHT, padx=15, pady=10)
            else:
                tk.Label(content_frame,
                         text="❌ Aucun raccourci configuré",
                         bg='#2d3748',
                         fg='#ef4444',
                         font=('Segoe UI', 14, 'bold')).pack(expand=True, pady=20)

            # Informations
            info_frame = tk.Frame(hotkeys_window, bg='#1a202c')
            info_frame.pack(fill=tk.X, padx=15, pady=10)

            info_text = "💡 Conseils :\n• Utilisez les modificateurs Ctrl, Shift, Alt, Win\n• Évitez les conflits avec d'autres applications\n• Modifiez les raccourcis dans les Paramètres"
            tk.Label(info_frame,
                     text=info_text,
                     bg='#1a202c',
                     fg='#94a3b8',
                     font=('Segoe UI', 10),
                     justify=tk.LEFT).pack(anchor=tk.W)

            # Bouton fermer
            tk.Button(hotkeys_window,
                      text="❌ Fermer",
                      command=hotkeys_window.destroy,
                      bg='#ef4444',
                      fg='white',
                      font=('Segoe UI', 11, 'bold'),
                      relief='flat',
                      padx=20,
                      pady=10).pack(pady=15)

        except Exception as e:
            self.logger.error(f"Erreur affichage hotkeys: {e}")
            self._show_error("Erreur", str(e))

    def _show_about(self):
        """Affiche la fenêtre À propos moderne"""
        about_window = tk.Toplevel(self.root)
        about_window.title("ℹ️ À propos de SnapMaster")
        about_window.geometry("500x400")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.configure(bg='#1a202c')

        # Centre la fenêtre
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (about_window.winfo_width() // 2)
        y = (about_window.winfo_screenheight() // 2) - (about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")

        # Logo et titre
        header_frame = tk.Frame(about_window, bg='#1e3a8a', height=100)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        header_frame.pack_propagate(False)

        tk.Label(header_frame,
                 text="🎯 SnapMaster",
                 bg='#1e3a8a',
                 fg='white',
                 font=('Segoe UI', 24, 'bold')).pack(expand=True, pady=10)

        tk.Label(header_frame,
                 text="v1.0.0",
                 bg='#1e3a8a',
                 fg='#60a5fa',
                 font=('Segoe UI', 12)).pack()

        # Contenu
        content_frame = tk.Frame(about_window, bg='#2d3748', relief='flat', bd=2)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        about_text = """
Application de capture d'écran avancée

✨ Fonctionnalités :
• Gestion automatique de la mémoire
• Détection d'applications au premier plan
• Raccourcis clavier configurables
• Organisation par dossiers
• Formats multiples (PNG, JPEG, BMP)
• Interface moderne avec thème bleu

🛠️ Développé avec :
• Python 3.9+
• Tkinter (Interface utilisateur)
• PyAutoGUI (Captures d'écran)
• psutil (Gestion des processus)
• keyboard (Raccourcis globaux)

© 2024 - Tous droits réservés
        """.strip()

        tk.Label(content_frame,
                 text=about_text,
                 bg='#2d3748',
                 fg='white',
                 font=('Segoe UI', 11),
                 justify=tk.LEFT).pack(padx=20, pady=20)

        # Bouton fermer
        tk.Button(about_window,
                  text="❌ Fermer",
                  command=about_window.destroy,
                  bg='#ef4444',
                  fg='white',
                  font=('Segoe UI', 11, 'bold'),
                  relief='flat',
                  padx=20,
                  pady=10).pack(pady=15)

    def _on_format_change(self, event):
        """Callback changement de format"""
        format_value = self.format_var.get()
        self.settings.update_capture_setting('image_format', format_value)
        self._update_status(f"Format changé: {format_value}")

    def _on_quality_change(self, event):
        """Callback changement de qualité"""
        quality = self.quality_var.get()
        self.quality_label.config(text=f"{quality}%")
        self.settings.update_capture_setting('image_quality', quality)

    def _browse_folder(self):
        """Parcourt pour sélectionner un dossier"""
        folder = filedialog.askdirectory(
            title="Sélectionner le dossier de captures",
            initialdir=self.folder_var.get()
        )

        if folder:
            self.folder_var.set(folder)
            # Met à jour dans les settings
            self.settings.config['folders']['default_screenshots'] = folder
            self.settings.save_config()
            self._update_status(f"Dossier par défaut: {Path(folder).name}")

    def _select_custom_folder(self, event):
        """Sélectionne un dossier personnalisé"""
        selection = self.folders_listbox.curselection()
        if selection:
            folder_name = self.folders_listbox.get(selection[0])
            custom_folders = self.settings.get_custom_folders()
            if folder_name in custom_folders:
                folder_path = custom_folders[folder_name]
                self.folder_var.set(folder_path)
                self._update_status(f"Dossier sélectionné: {folder_name}")

    def _update_folders_list(self):
        """Met à jour la liste des dossiers personnalisés"""
        if not hasattr(self, 'folders_listbox'):
            return

        self.folders_listbox.delete(0, tk.END)

        custom_folders = self.settings.get_custom_folders()
        for folder_name in custom_folders.keys():
            self.folders_listbox.insert(tk.END, folder_name)

    def _show_memory_stats(self):
        """Affiche les statistiques mémoire détaillées"""
        stats = self.memory_manager.get_stats()

        stats_text = f"""
💾 Statistiques mémoire détaillées:

📊 Utilisation actuelle: {stats.get('current_memory_mb', 0):.1f} MB
🧹 Nettoyages effectués: {stats.get('total_cleanups', 0)}
💨 Mémoire libérée (total): {stats.get('memory_saved_mb', 0):.1f} MB
📈 Objets trackés: {len(stats.get('tracked_objects', {}))}
⚡ Surveillance: {'✅ Active' if stats.get('monitoring') else '❌ Inactive'}

🔧 Configuration actuelle:
• Seuil de nettoyage: {self.memory_manager.memory_threshold_mb} MB
• Intervalle de vérification: {self.memory_manager.check_interval}s

💡 Conseils d'optimisation:
• Le nettoyage automatique optimise les performances
• Un usage élevé peut indiquer une fuite mémoire
• Les captures fréquentes augmentent temporairement l'usage
• Redémarrez l'application si l'usage reste élevé
        """.strip()

        messagebox.showinfo("Statistiques mémoire", stats_text)

    def _update_hotkeys_display(self):
        """Met à jour l'affichage des hotkeys"""
        if not hasattr(self, 'hotkeys_text'):
            return

        active_hotkeys = self.hotkey_manager.get_active_hotkeys()

        display_text = "⌨️ Raccourcis clavier actifs:\n\n"

        descriptions = {
            'fullscreen_capture': '🖥️ Capture plein écran',
            'window_capture': '🪟 Capture fenêtre active',
            'area_capture': '✂️ Capture zone sélectionnée',
            'quick_capture': '⚡ Capture rapide application'
        }

        for action, hotkey in active_hotkeys.items():
            desc = descriptions.get(action, action)
            display_text += f"• {desc}:\n  {hotkey.upper()}\n\n"

        if not active_hotkeys:
            display_text += "❌ Aucun raccourci configuré.\n\n"
            display_text += "💡 Configurez vos raccourcis dans les Paramètres."

        self.hotkeys_text.config(state=tk.NORMAL)
        self.hotkeys_text.delete(1.0, tk.END)
        self.hotkeys_text.insert(1.0, display_text)
        self.hotkeys_text.config(state=tk.DISABLED)

    # Ajoute toutes les méthodes à la classe
    gui_class._open_screenshots_folder = _open_screenshots_folder
    gui_class._export_config = _export_config
    gui_class._import_config = _import_config
    gui_class._test_capabilities = _test_capabilities
    gui_class._test_process_access = _test_process_access
    gui_class._test_screen_access = _test_screen_access
    gui_class._open_settings = _open_settings
    gui_class._open_folder_manager = _open_folder_manager
    gui_class._force_memory_cleanup = _force_memory_cleanup
    gui_class._show_statistics = _show_statistics
    gui_class._generate_stats_text = _generate_stats_text
    gui_class._refresh_statistics = _refresh_statistics
    gui_class._copy_statistics = _copy_statistics
    gui_class._show_hotkeys = _show_hotkeys
    gui_class._show_about = _show_about
    gui_class._on_format_change = _on_format_change
    gui_class._on_quality_change = _on_quality_change
    gui_class._browse_folder = _browse_folder
    gui_class._select_custom_folder = _select_custom_folder
    gui_class._update_folders_list = _update_folders_list
    gui_class._show_memory_stats = _show_memory_stats
    gui_class._update_hotkeys_display = _update_hotkeys_display
    gui_class._calculate_success_rate = _calculate_success_rate


# Classes de dialogue helper
class FolderManagerDialog:
    """Gestionnaire de dossiers personnalisés moderne"""

    def __init__(self, parent, settings_manager):
        self.parent = parent
        self.settings = settings_manager
        self.window = None

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("📁 Gestionnaire de dossiers")
        self.window.geometry("700x500")
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.configure(bg='#1a202c')

        # Centre la fenêtre
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

        # En-tête
        header_frame = tk.Frame(self.window, bg='#1e3a8a', height=80)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        header_frame.pack_propagate(False)

        tk.Label(header_frame,
                 text="📁 Gestionnaire de dossiers personnalisés",
                 bg='#1e3a8a',
                 fg='white',
                 font=('Segoe UI', 16, 'bold')).pack(expand=True, pady=20)

        # Contenu
        content_frame = tk.Frame(self.window, bg='#2d3748', relief='flat', bd=2)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Liste des dossiers
        folders_frame = tk.Frame(content_frame, bg='#2d3748')
        folders_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(folders_frame,
                 text="📋 Dossiers personnalisés configurés:",
                 bg='#2d3748',
                 fg='white',
                 font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        # Treeview pour les dossiers
        columns = ('name', 'path', 'exists')
        tree = ttk.Treeview(folders_frame, columns=columns, show='headings', height=12)
        tree.heading('name', text='Nom du dossier')
        tree.heading('path', text='Chemin')
        tree.heading('exists', text='Statut')
        tree.column('name', width=150)
        tree.column('path', width=350)
        tree.column('exists', width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(folders_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Remplit la liste
        custom_folders = self.settings.get_custom_folders()
        for name, path in custom_folders.items():
            status = "✅ Existe" if Path(path).exists() else "❌ Introuvable"
            tree.insert('', tk.END, values=(name, path, status))

        if not custom_folders:
            tree.insert('', tk.END, values=("Aucun dossier configuré", "Utilisez le bouton Ajouter", ""))

        # Boutons
        buttons_frame = tk.Frame(self.window, bg='#1a202c')
        buttons_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Button(buttons_frame,
                  text="➕ Ajouter un dossier",
                  command=self._add_folder,
                  bg='#10b981',
                  fg='white',
                  font=('Segoe UI', 10, 'bold'),
                  relief='flat',
                  padx=15,
                  pady=8).pack(side=tk.LEFT, padx=5)

        tk.Button(buttons_frame,
                  text="📂 Ouvrir le dossier par défaut",
                  command=self._open_default_folder,
                  bg='#3b82f6',
                  fg='white',
                  font=('Segoe UI', 10, 'bold'),
                  relief='flat',
                  padx=15,
                  pady=8).pack(side=tk.LEFT, padx=5)

        tk.Button(buttons_frame,
                  text="❌ Fermer",
                  command=self.window.destroy,
                  bg='#ef4444',
                  fg='white',
                  font=('Segoe UI', 10, 'bold'),
                  relief='flat',
                  padx=15,
                  pady=8).pack(side=tk.RIGHT, padx=5)

    def _add_folder(self):
        """Ajoute un nouveau dossier personnalisé"""
        name = simpledialog.askstring("Nouveau dossier", "Nom du dossier:", parent=self.window)
        if not name:
            return

        folder = filedialog.askdirectory(title="Sélectionner le dossier", parent=self.window)
        if not folder:
            return

        if self.settings.add_custom_folder(name, folder):
            messagebox.showinfo("Succès", f"Dossier '{name}' ajouté avec succès!", parent=self.window)
            # Recrée la fenêtre pour actualiser
            self.window.destroy()
            self.show()
        else:
            messagebox.showerror("Erreur", "Impossible d'ajouter le dossier", parent=self.window)

    def _open_default_folder(self):
        """Ouvre le dossier par défaut"""
        try:
            folder_path = self.settings.get_default_folder()
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier: {e}", parent=self.window)