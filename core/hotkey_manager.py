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
        
        # Dictionnaire des callbacks enregistrés
        self.hotkey_callbacks: Dict[str, List[Callable]] = {}
        
        # Dictionnaire des hotkeys actifs (keyboard hooks)
        self.active_hotkeys: Dict[str, object] = {}
        
        # Thread de surveillance
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Protection contre les répétitions
        self.last_trigger_time: Dict[str, float] = {}
        self.min_interval = 0.5  # Minimum 500ms entre les déclenchements
        
        # État des modificateurs pour détection complexe
        self.modifier_state = {
            'ctrl': False,
            'shift': False,
            'alt': False,
            'win': False
        }
        
        # Statistiques
        self.stats = {
            'total_triggers': 0,
            'successful_triggers': 0,
            'blocked_repeats': 0
        }
        
        self.logger.info("HotkeyManager initialisé")
    
    def start_monitoring(self) -> bool:
        """Démarre la surveillance des hotkeys"""
        try:
            if self.monitoring:
                return True
            
            # Enregistre tous les hotkeys configurés
            self._register_default_hotkeys()
            
            # Démarre la surveillance des modificateurs
            self._start_modifier_monitoring()
            
            self.monitoring = True
            self.logger.info("Surveillance des hotkeys démarrée")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur démarrage surveillance hotkeys: {e}")
            return False
    
    def stop_monitoring(self):
        """Arrête la surveillance des hotkeys"""
        try:
            self.monitoring = False
            
            # Supprime tous les hooks keyboard
            self._unregister_all_hotkeys()
            
            # Arrête la surveillance des modificateurs
            keyboard.unhook_all()
            
            self.logger.info("Surveillance des hotkeys arrêtée")
        
        except Exception as e:
            self.logger.error(f"Erreur arrêt surveillance hotkeys: {e}")
    
    def register_hotkey(self, action: str, hotkey: str, 
                       callback: Callable, override: bool = False) -> bool:
        """Enregistre un nouveau hotkey"""
        try:
            # Vérifie si le hotkey est déjà utilisé
            if not override and action in self.active_hotkeys:
                self.logger.warning(f"Hotkey {action} déjà enregistré")
                return False
            
            # Parse et valide le hotkey
            parsed_hotkey = self._parse_hotkey(hotkey)
            if not parsed_hotkey:
                self.logger.error(f"Format hotkey invalide: {hotkey}")
                return False
            
            # Supprime l'ancien hotkey si existe
            if action in self.active_hotkeys:
                self.unregister_hotkey(action)
            
            # Ajoute le callback à la liste
            if action not in self.hotkey_callbacks:
                self.hotkey_callbacks[action] = []
            
            # Utilise une weak reference pour éviter les fuites mémoire
            if hasattr(callback, '__self__'):
                weak_callback = weakref.WeakMethod(callback)
            else:
                weak_callback = weakref.ref(callback)
            
            self.hotkey_callbacks[action].append(weak_callback)
            
            # Enregistre le hotkey avec keyboard
            try:
                hook = keyboard.add_hotkey(
                    hotkey,
                    self._create_trigger_wrapper(action),
                    suppress=True
                )
                self.active_hotkeys[action] = hook
                
                self.logger.info(f"Hotkey enregistré: {action} -> {hotkey}")
                return True
                
            except Exception as e:
                self.logger.error(f"Erreur enregistrement keyboard pour {hotkey}: {e}")
                return False
        
        except Exception as e:
            self.logger.error(f"Erreur enregistrement hotkey {action}: {e}")
            return False
    
    def unregister_hotkey(self, action: str) -> bool:
        """Supprime un hotkey"""
        try:
            if action in self.active_hotkeys:
                # Supprime le hook keyboard
                keyboard.remove_hotkey(self.active_hotkeys[action])
                del self.active_hotkeys[action]
                
                # Supprime les callbacks
                if action in self.hotkey_callbacks:
                    del self.hotkey_callbacks[action]
                
                self.logger.info(f"Hotkey supprimé: {action}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Erreur suppression hotkey {action}: {e}")
            return False
    
    def update_hotkey(self, action: str, new_hotkey: str) -> bool:
        """Met à jour un hotkey existant"""
        if action in self.hotkey_callbacks:
            callbacks = self.hotkey_callbacks[action].copy()
            self.unregister_hotkey(action)
            
            # Ré-enregistre avec le nouveau hotkey
            success = True
            for weak_callback in callbacks:
                callback = weak_callback()
                if callback:
                    if not self.register_hotkey(action, new_hotkey, callback, override=True):
                        success = False
            
            # Met à jour dans les settings
            self.settings.set_hotkey(action, new_hotkey)
            
            return success
        
        return False
    
    def _register_default_hotkeys(self):
        """Enregistre les hotkeys par défaut depuis la configuration"""
        default_actions = [
            'fullscreen_capture',
            'window_capture', 
            'area_capture',
            'quick_capture'
        ]
        
        for action in default_actions:
            hotkey = self.settings.get_hotkey(action)
            if hotkey:
                # Callback par défaut qui émet un événement
                callback = self._create_default_callback(action)
                self.register_hotkey(action, hotkey, callback)
    
    def _create_default_callback(self, action: str) -> Callable:
        """Crée un callback par défaut pour une action"""
        def default_callback():
            self.logger.info(f"Hotkey déclenché: {action}")
            self._trigger_action(action)
        return default_callback
    
    def _create_trigger_wrapper(self, action: str) -> Callable:
        """Crée un wrapper pour le déclenchement avec protection anti-répétition"""
        def trigger_wrapper():
            current_time = time.time()
            
            # Vérification anti-répétition
            if action in self.last_trigger_time:
                if current_time - self.last_trigger_time[action] < self.min_interval:
                    self.stats['blocked_repeats'] += 1
                    return
            
            self.last_trigger_time[action] = current_time
            self.stats['total_triggers'] += 1
            
            try:
                # Exécute tous les callbacks pour cette action
                if action in self.hotkey_callbacks:
                    for weak_callback in self.hotkey_callbacks[action].copy():
                        callback = weak_callback()
                        if callback:
                            try:
                                callback()
                                self.stats['successful_triggers'] += 1
                            except Exception as e:
                                self.logger.error(f"Erreur callback {action}: {e}")
                        else:
                            # Supprime les callbacks morts
                            self.hotkey_callbacks[action].remove(weak_callback)
            
            except Exception as e:
                self.logger.error(f"Erreur déclenchement hotkey {action}: {e}")
        
        return trigger_wrapper
    
    def _trigger_action(self, action: str):
        """Déclenche une action spécifique (peut être étendu)"""
        # Ici on peut ajouter la logique pour déclencher les actions
        # Par exemple, émettre des signaux vers l'interface principale
        self.logger.debug(f"Action déclenchée: {action}")
    
    def _parse_hotkey(self, hotkey: str) -> Optional[Dict]:
        """Parse et valide un hotkey"""
        try:
            # Normalise le format
            hotkey = hotkey.lower().replace(' ', '')
            
            # Vérifie le format basique
            if not hotkey:
                return None
            
            # Sépare les modificateurs de la touche principale
            parts = hotkey.split('+')
            if len(parts) < 2:
                # Hotkey simple (pas de modificateur)
                if len(parts) == 1 and parts[0]:
                    return {'modifiers': [], 'key': parts[0]}
                return None
            
            modifiers = parts[:-1]
            main_key = parts[-1]
            
            # Valide les modificateurs
            valid_modifiers = ['ctrl', 'shift', 'alt', 'win', 'cmd']
            for mod in modifiers:
                if mod not in valid_modifiers:
                    return None
            
            # Valide la touche principale
            if not main_key:
                return None
            
            return {
                'modifiers': modifiers,
                'key': main_key,
                'original': hotkey
            }
        
        except Exception as e:
            self.logger.error(f"Erreur parsing hotkey {hotkey}: {e}")
            return None
    
    def _start_modifier_monitoring(self):
        """Démarre la surveillance des touches modificatrices"""
        try:
            # Surveillance des modificateurs pour des combinaisons complexes
            modifier_keys = {
                'ctrl': ['ctrl', 'right ctrl'],
                'shift': ['shift', 'right shift'], 
                'alt': ['alt', 'right alt'],
                'win': ['win', 'right win']
            }
            
            for modifier, keys in modifier_keys.items():
                for key in keys:
                    keyboard.on_press_key(key, self._create_modifier_handler(modifier, True))
                    keyboard.on_release_key(key, self._create_modifier_handler(modifier, False))
            
        except Exception as e:
            self.logger.error(f"Erreur surveillance modificateurs: {e}")
    
    def _create_modifier_handler(self, modifier: str, pressed: bool) -> Callable:
        """Crée un handler pour les touches modificatrices"""
        def handler(e):
            self.modifier_state[modifier] = pressed
        return handler
    
    def _unregister_all_hotkeys(self):
        """Supprime tous les hotkeys enregistrés"""
        for action in list(self.active_hotkeys.keys()):
            self.unregister_hotkey(action)
    
    def get_active_hotkeys(self) -> Dict[str, str]:
        """Retourne la liste des hotkeys actifs"""
        result = {}
        for action in self.active_hotkeys.keys():
            hotkey = self.settings.get_hotkey(action)
            if hotkey:
                result[action] = hotkey
        return result
    
    def is_hotkey_available(self, hotkey: str) -> bool:
        """Vérifie si un hotkey est disponible"""
        # Parse le hotkey
        parsed = self._parse_hotkey(hotkey)
        if not parsed:
            return False
        
        # Vérifie s'il n'est pas déjà utilisé
        for action, active_hotkey in self.get_active_hotkeys().items():
            if active_hotkey.lower() == hotkey.lower():
                return False
        
        return True
    
    def get_modifier_state(self) -> Dict[str, bool]:
        """Retourne l'état actuel des modificateurs"""
        return self.modifier_state.copy()
    
    def test_hotkey(self, hotkey: str) -> bool:
        """Teste si un hotkey peut être enregistré"""
        try:
            # Test d'enregistrement temporaire
            def test_callback():
                pass
            
            test_hook = keyboard.add_hotkey(hotkey, test_callback, suppress=False)
            keyboard.remove_hotkey(test_hook)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Test hotkey {hotkey} échoué: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques des hotkeys"""
        return {
            **self.stats,
            'active_hotkeys': len(self.active_hotkeys),
            'monitoring': self.monitoring
        }
    
    def add_action_callback(self, action: str, callback: Callable) -> bool:
        """Ajoute un callback à une action existante"""
        if action in self.hotkey_callbacks:
            if hasattr(callback, '__self__'):
                weak_callback = weakref.WeakMethod(callback)
            else:
                weak_callback = weakref.ref(callback)
            
            self.hotkey_callbacks[action].append(weak_callback)
            return True
        
        return False
    
    def remove_action_callback(self, action: str, callback: Callable) -> bool:
        """Supprime un callback d'une action"""
        if action in self.hotkey_callbacks:
            for weak_callback in self.hotkey_callbacks[action]:
                if weak_callback() == callback:
                    self.hotkey_callbacks[action].remove(weak_callback)
                    return True
        
        return False
    
    def get_suggested_hotkeys(self) -> Dict[str, List[str]]:
        """Retourne des suggestions de hotkeys pour différentes actions"""
        suggestions = {
            'fullscreen_capture': [
                'ctrl+shift+f', 'ctrl+alt+f', 'f11', 'print screen'
            ],
            'window_capture': [
                'ctrl+shift+w', 'ctrl+alt+w', 'alt+print screen'
            ],
            'area_capture': [
                'ctrl+shift+a', 'ctrl+alt+a', 'ctrl+shift+s'
            ],
            'quick_capture': [
                'ctrl+shift+q', 'ctrl+alt+q', 'f12'
            ]
        }
        
        # Filtre les suggestions déjà utilisées
        used_hotkeys = set(self.get_active_hotkeys().values())
        
        for action, hotkey_list in suggestions.items():
            suggestions[action] = [
                hk for hk in hotkey_list 
                if hk not in used_hotkeys and self.is_hotkey_available(hk)
            ]
        
        return suggestions
    
    def __del__(self):
        """Nettoyage final"""
        try:
            self.stop_monitoring()
        except Exception:
            pass