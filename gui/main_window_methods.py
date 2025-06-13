# gui/main_window_methods.py
"""
Méthodes supplémentaires pour SnapMasterGUI
Complément à main_window.py
"""

import os
import subprocess
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import threading
import time

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
                result_text = "Résultats des tests de capacités:\n\n"
                result_text += "📸 Captures d'écran:\n"
                result_text += f"  • Plein écran: {'✅' if capabilities.get('fullscreen') else '❌'}\n"
                result_text += f"  • Fenêtre: {'✅' if capabilities.get('window') else '❌'}\n"
                result_text += f"  • Zone sélectionnée: {'✅' if capabilities.get('area_selection') else '❌'}\n"
                result_text += f"  • Détection d'app: {'✅' if capabilities.get('app_detection') else '❌'}\n\n"

                result_text += "🔍 Détection d'applications:\n"
                result_text += f"  • Détection fenêtre: {'✅' if app_caps.get('window_detection') else '❌'}\n"
                result_text += f"  • Détection plein écran: {'✅' if app_caps.get('fullscreen_detection') else '❌'}\n"
                result_text += f"  • Géométrie fenêtre: {'✅' if app_caps.get('window_geometry') else '❌'}\n"
                result_text += f"  • Classification app: {'✅' if app_caps.get('app_classification') else '❌'}\n\n"

                # Test hotkeys
                hotkey_stats = self.hotkey_manager.get_stats()
                result_text += "⌨️ Raccourcis clavier:\n"
                result_text += f"  • Surveillance active: {'✅' if hotkey_stats.get('monitoring') else '❌'}\n"
                result_text += f"  • Raccourcis actifs: {hotkey_stats.get('active_hotkeys', 0)}\n"

                messagebox.showinfo("Test des capacités", result_text)
                self._update_status("Test terminé")

            self.root.after(0, show_results)

        threading.Thread(target=test_thread, daemon=True).start()

    def _open_settings(self):
        """Ouvre la fenêtre de paramètres"""
        if not self.settings_window:
            from gui.settings_window import SettingsWindow
            self.settings_window = SettingsWindow(self.root, self.settings, self.hotkey_manager)

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
                message = f"Nettoyage terminé:\n"
                message += f"• Objets nettoyés: {cleaned_objects}\n"
                message += f"• Mémoire libérée: {freed_memory:.1f} MB\n"
                message += f"• Mémoire actuelle: {after_memory:.1f} MB"

                messagebox.showinfo("Nettoyage mémoire", message)
                self._update_status("Nettoyage terminé")

            self.root.after(0, show_result)

        threading.Thread(target=cleanup_thread, daemon=True).start()

    def _show_statistics(self):
        """Affiche les statistiques détaillées"""
        try:
            # Collecte les statistiques
            screenshot_stats = self.screenshot_manager.get_stats()
            memory_stats = self.memory_manager.get_stats()
            hotkey_stats = self.hotkey_manager.get_stats()

            stats_text = "📊 Statistiques SnapMaster\n\n"

            # Stats captures
            stats_text += "📸 Captures d'écran:\n"
            stats_text += f"  • Total: {screenshot_stats.get('total_captures', 0)}\n"
            stats_text += f"  • Réussies: {screenshot_stats.get('successful_captures', 0)}\n"
            stats_text += f"  • Échouées: {screenshot_stats.get('failed_captures', 0)}\n"
            stats_text += f"  • Taux de réussite: {self._calculate_success_rate(screenshot_stats):.1f}%\n\n"

            # Stats mémoire
            stats_text += "🧠 Gestion mémoire:\n"
            stats_text += f"  • Usage actuel: {memory_stats.get('current_memory_mb', 0):.1f} MB\n"
            stats_text += f"  • Nettoyages: {memory_stats.get('total_cleanups', 0)}\n"
            stats_text += f"  • Mémoire libérée: {memory_stats.get('memory_saved_mb', 0):.1f} MB\n"
            stats_text += f"  • Surveillance: {'Activée' if memory_stats.get('monitoring') else 'Désactivée'}\n\n"

            # Stats hotkeys
            stats_text += "⌨️ Raccourcis clavier:\n"
            stats_text += f"  • Déclenchements: {hotkey_stats.get('total_triggers', 0)}\n"
            stats_text += f"  • Réussis: {hotkey_stats.get('successful_triggers', 0)}\n"
            stats_text += f"  • Répétitions bloquées: {hotkey_stats.get('blocked_repeats', 0)}\n"
            stats_text += f"  • Raccourcis actifs: {hotkey_stats.get('active_hotkeys', 0)}\n"

            # Fenêtre de statistiques
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Statistiques - SnapMaster")
            stats_window.geometry("500x400")
            stats_window.resizable(False, False)
            stats_window.transient(self.root)

            # Texte des statistiques
            text_widget = tk.Text(stats_window, wrap=tk.WORD, padx=10, pady=10,
                                  font=('Courier', 10))
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert(1.0, stats_text)
            text_widget.config(state=tk.DISABLED)

            # Bouton fermer
            ttk.Button(stats_window, text="Fermer",
                       command=stats_window.destroy).pack(pady=5)

        except Exception as e:
            self.logger.error(f"Erreur affichage statistiques: {e}")
            self._show_error("Erreur", str(e))

    def _calculate_success_rate(self, stats):
        """Calcule le taux de réussite"""
        total = stats.get('total_captures', 0)
        if total == 0:
            return 0.0
        successful = stats.get('successful_captures', 0)
        return (successful / total) * 100

    def _show_hotkeys(self):
        """Affiche les raccourcis clavier"""
        try:
            active_hotkeys = self.hotkey_manager.get_active_hotkeys()

            hotkeys_text = "⌨️ Raccourcis clavier actifs:\n\n"

            descriptions = {
                'fullscreen_capture': 'Capture plein écran',
                'window_capture': 'Capture fenêtre active',
                'area_capture': 'Capture zone sélectionnée',
                'quick_capture': 'Capture rapide application'
            }

            for action, hotkey in active_hotkeys.items():
                desc = descriptions.get(action, action)
                hotkeys_text += f"• {desc}: {hotkey}\n"

            if not active_hotkeys:
                hotkeys_text += "Aucun raccourci configuré.\n"

            hotkeys_text += "\n💡 Conseils:\n"
            hotkeys_text += "• Utilisez les modificateurs Ctrl, Shift, Alt\n"
            hotkeys_text += "• Évitez les conflits avec d'autres applications\n"
            hotkeys_text += "• Modifiez les raccourcis dans les Paramètres"

            messagebox.showinfo("Raccourcis clavier", hotkeys_text)

        except Exception as e:
            self.logger.error(f"Erreur affichage hotkeys: {e}")
            self._show_error("Erreur", str(e))

    def _show_about(self):
        """Affiche la fenêtre À propos"""
        about_text = """
🎯 SnapMaster v1.0.0

Application de capture d'écran avancée avec:
• Gestion automatique de la mémoire
• Détection d'applications au premier plan
• Raccourcis clavier configurables
• Organisation par dossiers
• Formats multiples (PNG, JPEG, BMP)

Développé avec Python et amour ❤️

© 2024 - Tous droits réservés
        """.strip()

        messagebox.showinfo("À propos de SnapMaster", about_text)

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

    def _add_association(self):
        """Ajoute une association application/dossier"""
        dialog = AssociationDialog(self.root, self.settings)
        result = dialog.show()

        if result:
            app_name, folder_name = result
            if self.settings.link_app_to_folder(app_name, folder_name):
                self._update_associations_list()
                self._update_status(f"Association ajoutée: {app_name} → {folder_name}")
            else:
                self._show_error("Erreur", "Impossible d'ajouter l'association")

    def _edit_association(self):
        """Modifie une association existante"""
        selection = self.associations_tree.selection()
        if not selection:
            self._show_warning("Sélection", "Veuillez sélectionner une association à modifier")
            return

        item = self.associations_tree.item(selection[0])
        app_name = item['values'][0]
        current_folder = item['values'][1]

        dialog = AssociationDialog(self.root, self.settings, app_name, current_folder)
        result = dialog.show()

        if result:
            new_app_name, new_folder_name = result
            if self.settings.link_app_to_folder(new_app_name, new_folder_name):
                self._update_associations_list()
                self._update_status(f"Association modifiée: {new_app_name} → {new_folder_name}")

    def _remove_association(self):
        """Supprime une association"""
        selection = self.associations_tree.selection()
        if not selection:
            self._show_warning("Sélection", "Veuillez sélectionner une association à supprimer")
            return

        item = self.associations_tree.item(selection[0])
        app_name = item['values'][0]

        if messagebox.askyesno("Confirmation", f"Supprimer l'association pour {app_name}?"):
            # Supprime de la configuration
            if app_name in self.settings.config['applications']['app_folder_mapping']:
                del self.settings.config['applications']['app_folder_mapping'][app_name]
                self.settings.save_config()
                self._update_associations_list()
                self._update_status(f"Association supprimée: {app_name}")

    def _update_associations_list(self):
        """Met à jour la liste des associations"""
        if not hasattr(self, 'associations_tree'):
            return

        # Nettoie l'arbre
        for item in self.associations_tree.get_children():
            self.associations_tree.delete(item)

        # Ajoute les associations
        app_mappings = self.settings.config['applications']['app_folder_mapping']
        custom_folders = self.settings.get_custom_folders()

        for app_name, folder_name in app_mappings.items():
            if folder_name == "default":
                folder_display = "Dossier par défaut"
            else:
                folder_display = custom_folders.get(folder_name, folder_name)

            self.associations_tree.insert('', tk.END, values=(app_name, folder_display))

    def _show_memory_stats(self):
        """Affiche les statistiques mémoire détaillées"""
        stats = self.memory_manager.get_stats()

        stats_text = f"""
📊 Statistiques mémoire détaillées:

💾 Usage actuel: {stats.get('current_memory_mb', 0):.1f} MB
🧹 Nettoyages effectués: {stats.get('total_cleanups', 0)}
💨 Mémoire libérée: {stats.get('memory_saved_mb', 0):.1f} MB
📈 Objets trackés: {len(stats.get('tracked_objects', {}))}
⚡ Surveillance: {'Active' if stats.get('monitoring') else 'Inactive'}

🔧 Configuration:
• Seuil de nettoyage: {self.memory_manager.memory_threshold_mb} MB
• Intervalle de vérification: {self.memory_manager.check_interval}s

💡 Conseils:
• Le nettoyage automatique optimise les performances
• Un usage élevé peut indiquer une fuite mémoire
• Les captures fréquentes augmentent temporairement l'usage
        """.strip()

        messagebox.showinfo("Statistiques mémoire", stats_text)

    def _update_hotkeys_display(self):
        """Met à jour l'affichage des hotkeys"""
        if not hasattr(self, 'hotkeys_text'):
            return

        active_hotkeys = self.hotkey_manager.get_active_hotkeys()

        display_text = "Raccourcis clavier actifs:\n\n"

        descriptions = {
            'fullscreen_capture': 'Capture plein écran',
            'window_capture': 'Capture fenêtre active',
            'area_capture': 'Capture zone sélectionnée',
            'quick_capture': 'Capture rapide application'
        }

        for action, hotkey in active_hotkeys.items():
            desc = descriptions.get(action, action)
            display_text += f"• {desc}:\n  {hotkey}\n\n"

        if not active_hotkeys:
            display_text += "Aucun raccourci configuré.\n\n"
            display_text += "Configurez vos raccourcis dans les Paramètres."

        self.hotkeys_text.config(state=tk.NORMAL)
        self.hotkeys_text.delete(1.0, tk.END)
        self.hotkeys_text.insert(1.0, display_text)
        self.hotkeys_text.config(state=tk.DISABLED)

    # Ajoute toutes les méthodes à la classe
    gui_class._open_screenshots_folder = _open_screenshots_folder
    gui_class._export_config = _export_config
    gui_class._import_config = _import_config
    gui_class._test_capabilities = _test_capabilities
    gui_class._open_settings = _open_settings
    gui_class._open_folder_manager = _open_folder_manager
    gui_class._force_memory_cleanup = _force_memory_cleanup
    gui_class._show_statistics = _show_statistics
    gui_class._show_hotkeys = _show_hotkeys
    gui_class._show_about = _show_about
    gui_class._on_format_change = _on_format_change
    gui_class._on_quality_change = _on_quality_change
    gui_class._browse_folder = _browse_folder
    gui_class._select_custom_folder = _select_custom_folder
    gui_class._update_folders_list = _update_folders_list
    gui_class._add_association = _add_association
    gui_class._edit_association = _edit_association
    gui_class._remove_association = _remove_association
    gui_class._update_associations_list = _update_associations_list
    gui_class._show_memory_stats = _show_memory_stats
    gui_class._update_hotkeys_display = _update_hotkeys_display
    gui_class._calculate_success_rate = _calculate_success_rate


# Classes de dialogue helper
class FolderManagerDialog:
    """Gestionnaire de dossiers personnalisés"""

    def __init__(self, parent, settings_manager):
        self.parent = parent
        self.settings = settings_manager
        self.window = None

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Gestionnaire de dossiers")
        self.window.geometry("600x400")
        self.window.transient(self.parent)
        self.window.grab_set()

        # Interface simplifiée
        label = ttk.Label(self.window, text="Gestionnaire de dossiers - À implémenter")
        label.pack(expand=True)

        ttk.Button(self.window, text="Fermer",
                   command=self.window.destroy).pack(pady=10)


class AssociationDialog:
    """Dialogue pour ajouter/modifier une association"""

    def __init__(self, parent, settings_manager, app_name="", folder_name=""):
        self.parent = parent
        self.settings = settings_manager
        self.app_name = app_name
        self.folder_name = folder_name
        self.result = None

    def show(self):
        """Affiche le dialogue et retourne le résultat"""
        app = simpledialog.askstring("Application",
                                     "Nom de l'application:",
                                     initialvalue=self.app_name)
        if not app:
            return None

        # Liste des dossiers disponibles
        folders = ["default"] + list(self.settings.get_custom_folders().keys())

        # Pour l'instant, dialogue simple
        folder = simpledialog.askstring("Dossier",
                                        f"Dossier pour {app} (disponibles: {', '.join(folders)}):",
                                        initialvalue=self.folder_name)
        if not folder:
            return None

        return (app, folder)