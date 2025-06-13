# core/hotkey_manager.py
"""
Gestionnaire de raccourcis clavier pour SnapMaster
Gère l'enregistrement et l'exécution des hotkeys globaux
"""

import keyboard
import threading
import logging
from typing import Dict, Callable, Optional, List, Tuple
import time
import weakref

from config.settings import SettingsManager

class HotkeyManager:
    """Gestionnaire de raccourcis clavier globaux"""

    def __init__(self, settings_manager: SettingsManager):
        self.logger = logging.getLogger(__name__)
        self.settings = settings_manager

        # Dictionnaire des callbacks enregistrés par action
        self.action_callbacks: Dict[str, List[Callable]] = {}

        # Dictionnaire des hotkeys actifs (keyboard hooks)
        self.active_hotkeys: Dict[str, str] = {}  # action -> hotkey string
        self.keyboard_hooks: List = []  # Liste des hooks keyboard

        # Thread de surveillance
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Protection contre les répétitions
        self.last_trigger_time: Dict[str, float] = {}
        self.min_interval = 0.3  # Minimum 300ms entre les déclenchements

        # Statistiques
        self.stats = {
            'total_triggers': 0,
            'successful_triggers': 0,
            'blocked_repeats': 0
        }

        # Flag pour éviter les réentrées
        self._processing_hotkey = False

        self.logger.info("HotkeyManager initialisé")

    def start_monitoring(self) -> bool:
        """Démarre la surveillance des hotkeys"""
        try:
            if self.monitoring:
                return True

            # Enregistre tous les hotkeys configurés
            success = self._register_default_hotkeys()

            if success:
                self.monitoring = True
                self.logger.info("Surveillance des hotkeys démarrée")
                return True
            else:
                self.logger.error("Échec de l'enregistrement des hotkeys")
                return False

        except Exception as e:
            self.logger.error(f"Erreur démarrage surveillance hotkeys: {e}")
            return False

    def stop_monitoring(self):
        """Arrête la surveillance des hotkeys"""
        try:
            self.monitoring = False

            # Supprime tous les hooks keyboard
            self._unregister_all_hotkeys()

            self.logger.info("Surveillance des hotkeys arrêtée")

        except Exception as e:
            self.logger.error(f"Erreur arrêt surveillance hotkeys: {e}")

    def add_action_callback(self, action: str, callback: Callable) -> bool:
        """Ajoute un callback à une action"""
        try:
            if action not in self.action_callbacks:
                self.action_callbacks[action] = []

            # Utilise une weak reference pour éviter les fuites mémoire
            if hasattr(callback, '__self__'):
                weak_callback = weakref.WeakMethod(callback)
            else:
                weak_callback = weakref.ref(callback)

            self.action_callbacks[action].append(weak_callback)
            self.logger.info(f"Callback ajouté pour l'action: {action}")
            return True

        except Exception as e:
            self.logger.error(f"Erreur ajout callback {action}: {e}")
            return False

    def remove_action_callback(self, action: str, callback: Callable) -> bool:
        """Supprime un callback d'une action"""
        try:
            if action in self.action_callbacks:
                for weak_callback in self.action_callbacks[action]:
                    if weak_callback() == callback:
                        self.action_callbacks[action].remove(weak_callback)
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Erreur suppression callback {action}: {e}")
            return False

    def _register_default_hotkeys(self) -> bool:
        """Enregistre les hotkeys par défaut depuis la configuration"""
        try:
            default_actions = [
                'fullscreen_capture',
                'window_capture',
                'area_capture',
                'quick_capture'
            ]

            success_count = 0

            for action in default_actions:
                hotkey = self.settings.get_hotkey(action)
                if hotkey and hotkey.strip():
                    if self._register_single_hotkey(action, hotkey):
                        success_count += 1
                        self.logger.info(f"Hotkey enregistré: {action} -> {hotkey}")
                    else:
                        self.logger.warning(f"Échec enregistrement hotkey: {action} -> {hotkey}")

            return success_count > 0

        except Exception as e:
            self.logger.error(f"Erreur enregistrement hotkeys par défaut: {e}")
            return False

    def _register_single_hotkey(self, action: str, hotkey: str) -> bool:
        """Enregistre un seul hotkey"""
        try:
            # Parse et valide le hotkey
            if not self._validate_hotkey(hotkey):
                self.logger.error(f"Format hotkey invalide: {hotkey}")
                return False

            # Supprime l'ancien hotkey si existe
            if action in self.active_hotkeys:
                self._unregister_single_hotkey(action)

            # Crée le callback pour cette action
            callback = self._create_action_callback(action)

            # Enregistre le hotkey avec keyboard
            try:
                # Normalise le hotkey pour keyboard
                normalized_hotkey = self._normalize_hotkey(hotkey)

                # Ajoute le hook
                hook = keyboard.add_hotkey(
                    normalized_hotkey,
                    callback,
                    suppress=True,
                    trigger_on_release=False
                )

                # Enregistre le hook pour pouvoir le supprimer plus tard
                self.keyboard_hooks.append(hook)
                self.active_hotkeys[action] = hotkey

                return True

            except Exception as e:
                self.logger.error(f"Erreur enregistrement keyboard pour {hotkey}: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Erreur enregistrement hotkey {action}: {e}")
            return False

    def _unregister_single_hotkey(self, action: str) -> bool:
        """Supprime un hotkey spécifique"""
        try:
            if action in self.active_hotkeys:
                # On ne peut pas supprimer un hook spécifique facilement avec keyboard
                # On doit supprimer tous les hooks et les ré-enregistrer
                self._unregister_all_hotkeys()

                # Supprime l'action de la liste
                del self.active_hotkeys[action]

                # Ré-enregistre tous les autres hotkeys
                temp_hotkeys = self.active_hotkeys.copy()
                self.active_hotkeys.clear()

                for remaining_action, remaining_hotkey in temp_hotkeys.items():
                    self._register_single_hotkey(remaining_action, remaining_hotkey)

                self.logger.info(f"Hotkey supprimé: {action}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Erreur suppression hotkey {action}: {e}")
            return False

    def _unregister_all_hotkeys(self):
        """Supprime tous les hotkeys enregistrés"""
        try:
            # Supprime tous les hooks keyboard
            keyboard.unhook_all()
            self.keyboard_hooks.clear()

        except Exception as e:
            self.logger.error(f"Erreur suppression tous hotkeys: {e}")

    def _create_action_callback(self, action: str) -> Callable:
        """Crée un callback pour une action avec protection anti-répétition"""
        def action_callback():
            # Protection contre les réentrées
            if self._processing_hotkey:
                return

            current_time = time.time()

            # Vérification anti-répétition
            if action in self.last_trigger_time:
                if current_time - self.last_trigger_time[action] < self.min_interval:
                    self.stats['blocked_repeats'] += 1
                    return

            self.last_trigger_time[action] = current_time
            self.stats['total_triggers'] += 1

            # Flag pour éviter les réentrées
            self._processing_hotkey = True

            try:
                self.logger.info(f"Hotkey déclenché: {action}")

                # Exécute tous les callbacks pour cette action
                if action in self.action_callbacks:
                    for weak_callback in self.action_callbacks[action].copy():
                        callback = weak_callback()
                        if callback:
                            try:
                                # Exécute le callback dans un thread séparé pour éviter les blocages
                                callback_thread = threading.Thread(
                                    target=callback,
                                    name=f"HotkeyCallback-{action}",
                                    daemon=True
                                )
                                callback_thread.start()

                                self.stats['successful_triggers'] += 1
                                self.logger.debug(f"Callback exécuté pour {action}")

                            except Exception as e:
                                self.logger.error(f"Erreur callback {action}: {e}")
                        else:
                            # Supprime les callbacks morts
                            self.action_callbacks[action].remove(weak_callback)
                else:
                    self.logger.warning(f"Aucun callback enregistré pour l'action: {action}")

            except Exception as e:
                self.logger.error(f"Erreur déclenchement hotkey {action}: {e}")

            finally:
                # Libère le flag après un petit délai
                def reset_flag():
                    time.sleep(0.1)
                    self._processing_hotkey = False

                threading.Thread(target=reset_flag, daemon=True).start()

        return action_callback

    def _validate_hotkey(self, hotkey: str) -> bool:
        """Valide un hotkey"""
        try:
            if not hotkey or not hotkey.strip():
                return False

            # Teste avec keyboard
            normalized = self._normalize_hotkey(hotkey)

            # Test d'enregistrement temporaire
            try:
                test_hook = keyboard.add_hotkey(normalized, lambda: None, suppress=False)
                keyboard.remove_hotkey(test_hook)
                return True
            except Exception:
                return False

        except Exception as e:
            self.logger.error(f"Erreur validation hotkey {hotkey}: {e}")
            return False

    def _normalize_hotkey(self, hotkey: str) -> str:
        """Normalise un hotkey pour la bibliothèque keyboard"""
        # Convertit en minuscules et supprime les espaces
        normalized = hotkey.lower().replace(' ', '')

        # Remplace les alias courants
        replacements = {
            'win': 'windows',
            'cmd': 'cmd',
            'super': 'windows'
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        return normalized

    def update_hotkey(self, action: str, new_hotkey: str) -> bool:
        """Met à jour un hotkey existant"""
        try:
            # Valide le nouveau hotkey
            if not self._validate_hotkey(new_hotkey):
                self.logger.error(f"Hotkey invalide: {new_hotkey}")
                return False

            # Met à jour dans les settings
            self.settings.set_hotkey(action, new_hotkey)

            # Ré-enregistre le hotkey
            success = self._register_single_hotkey(action, new_hotkey)

            if success:
                self.logger.info(f"Hotkey mis à jour: {action} -> {new_hotkey}")

            return success

        except Exception as e:
            self.logger.error(f"Erreur mise à jour hotkey {action}: {e}")
            return False

    def get_active_hotkeys(self) -> Dict[str, str]:
        """Retourne la liste des hotkeys actifs"""
        return self.active_hotkeys.copy()

    def is_hotkey_available(self, hotkey: str) -> bool:
        """Vérifie si un hotkey est disponible"""
        if not self._validate_hotkey(hotkey):
            return False

        # Vérifie s'il n'est pas déjà utilisé
        for existing_hotkey in self.active_hotkeys.values():
            if existing_hotkey.lower() == hotkey.lower():
                return False

        return True

    def test_hotkey(self, hotkey: str) -> bool:
        """Teste si un hotkey peut être enregistré"""
        return self._validate_hotkey(hotkey)

    def get_stats(self) -> Dict:
        """Retourne les statistiques des hotkeys"""
        return {
            **self.stats,
            'active_hotkeys': len(self.active_hotkeys),
            'monitoring': self.monitoring,
            'registered_callbacks': sum(len(callbacks) for callbacks in self.action_callbacks.values())
        }

    def force_refresh_hotkeys(self) -> bool:
        """Force le rechargement de tous les hotkeys"""
        try:
            self.logger.info("Rechargement forcé des hotkeys...")

            # Sauvegarde les actions actuelles
            actions_to_restore = list(self.active_hotkeys.keys())

            # Supprime tous les hotkeys
            self._unregister_all_hotkeys()
            self.active_hotkeys.clear()

            # Ré-enregistre tous les hotkeys
            success = self._register_default_hotkeys()

            self.logger.info(f"Rechargement terminé. Succès: {success}")
            return success

        except Exception as e:
            self.logger.error(f"Erreur rechargement hotkeys: {e}")
            return False

    def get_suggested_hotkeys(self) -> Dict[str, List[str]]:
        """Retourne des suggestions de hotkeys pour différentes actions"""
        suggestions = {
            'fullscreen_capture': [
                'ctrl+shift+f', 'ctrl+alt+f', 'f11', 'ctrl+f11'
            ],
            'window_capture': [
                'ctrl+shift+w', 'ctrl+alt+w', 'alt+f4', 'ctrl+f12'
            ],
            'area_capture': [
                'ctrl+shift+a', 'ctrl+alt+a', 'ctrl+shift+s', 'ctrl+shift+x'
            ],
            'quick_capture': [
                'ctrl+shift+q', 'ctrl+alt+q', 'f12', 'ctrl+shift+c'
            ]
        }

        # Filtre les suggestions déjà utilisées
        used_hotkeys = set(hotkey.lower() for hotkey in self.active_hotkeys.values())

        for action, hotkey_list in suggestions.items():
            suggestions[action] = [
                hk for hk in hotkey_list
                if hk.lower() not in used_hotkeys and self.is_hotkey_available(hk)
            ]

        return suggestions

    def __del__(self):
        """Nettoyage final"""
        try:
            self.stop_monitoring()
        except Exception:
            pass