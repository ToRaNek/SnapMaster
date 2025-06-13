# core/memory_manager.py
"""
Gestionnaire de mémoire pour SnapMaster
Gère automatiquement la RAM et évite les fuites mémoire
"""

import gc
import psutil
import threading
import time
import logging
import weakref
from typing import Dict, List, Optional, Any

class MemoryManager:
    """Gestionnaire de mémoire automatique avec nettoyage proactif"""
    
    def __init__(self, memory_threshold_mb: int = 500, check_interval: int = 30):
        self.logger = logging.getLogger(__name__)
        self.memory_threshold_mb = memory_threshold_mb
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Collections pour tracking des objets
        self._tracked_objects: Dict[str, List[weakref.ref]] = {}
        self._cleanup_callbacks: List[callable] = []
        self._lock = threading.RLock()
        
        # Statistiques
        self.stats = {
            'total_cleanups': 0,
            'memory_saved_mb': 0,
            'last_cleanup': None
        }
        
        self.logger.info(f"MemoryManager initialisé - Seuil: {memory_threshold_mb}MB")
    
    def start_monitoring(self):
        """Démarre la surveillance mémoire en arrière-plan"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MemoryMonitor"
        )
        self.monitor_thread.start()
        self.logger.info("Surveillance mémoire démarrée")
    
    def stop_monitoring(self):
        """Arrête la surveillance mémoire"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Surveillance mémoire arrêtée")
    
    def _monitor_loop(self):
        """Boucle principale de surveillance mémoire"""
        while self.monitoring:
            try:
                current_memory = self.get_current_memory_usage()
                
                if current_memory > self.memory_threshold_mb:
                    self.logger.warning(
                        f"Seuil mémoire dépassé: {current_memory:.1f}MB > {self.memory_threshold_mb}MB"
                    )
                    self.force_cleanup()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Erreur dans la surveillance mémoire: {e}")
                time.sleep(self.check_interval)
    
    def get_current_memory_usage(self) -> float:
        """Retourne l'usage mémoire actuel en MB"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Conversion en MB
        except Exception as e:
            self.logger.error(f"Erreur lecture mémoire: {e}")
            return 0.0
    
    def track_object(self, obj: Any, category: str = "default") -> weakref.ref:
        """Ajoute un objet au tracking avec weak reference"""
        with self._lock:
            if category not in self._tracked_objects:
                self._tracked_objects[category] = []
            
            # Callback de nettoyage automatique quand l'objet est détruit
            def cleanup_callback(ref):
                with self._lock:
                    if category in self._tracked_objects:
                        try:
                            self._tracked_objects[category].remove(ref)
                        except ValueError:
                            pass
            
            weak_ref = weakref.ref(obj, cleanup_callback)
            self._tracked_objects[category].append(weak_ref)
            
            return weak_ref
    
    def add_cleanup_callback(self, callback: callable):
        """Ajoute un callback de nettoyage personnalisé"""
        with self._lock:
            self._cleanup_callbacks.append(callback)
    
    def force_cleanup(self) -> int:
        """Force un nettoyage mémoire complet"""
        memory_before = self.get_current_memory_usage()
        
        with self._lock:
            # Exécute les callbacks de nettoyage personnalisés
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Erreur callback nettoyage: {e}")
            
            # Nettoie les références mortes
            self._cleanup_dead_references()
            
            # Force le garbage collection
            collected = gc.collect()
            
            # Force la libération mémoire Python
            self._force_memory_release()
        
        memory_after = self.get_current_memory_usage()
        memory_saved = memory_before - memory_after
        
        # Mise à jour des statistiques
        self.stats['total_cleanups'] += 1
        self.stats['memory_saved_mb'] += max(0, memory_saved)
        self.stats['last_cleanup'] = time.time()
        
        self.logger.info(
            f"Nettoyage terminé - Objets GC: {collected}, "
            f"Mémoire libérée: {memory_saved:.1f}MB"
        )
        
        return collected
    
    def _cleanup_dead_references(self):
        """Nettoie les weak references mortes"""
        for category in list(self._tracked_objects.keys()):
            alive_refs = []
            for ref in self._tracked_objects[category]:
                if ref() is not None:
                    alive_refs.append(ref)
            self._tracked_objects[category] = alive_refs
    
    def _force_memory_release(self):
        """Force la libération mémoire avec techniques avancées"""
        try:
            # Force plusieurs passes de garbage collection
            for generation in range(3):
                gc.collect(generation)
            
            # Nettoie le cache des modules
            if hasattr(gc, 'get_objects'):
                for obj in gc.get_objects():
                    if hasattr(obj, '__dict__') and hasattr(obj, 'cache_clear'):
                        try:
                            obj.cache_clear()
                        except (AttributeError, TypeError):
                            pass
            
        except Exception as e:
            self.logger.error(f"Erreur libération mémoire: {e}")
    
    def get_tracked_objects_count(self) -> Dict[str, int]:
        """Retourne le nombre d'objets trackés par catégorie"""
        with self._lock:
            return {
                category: len([ref for ref in refs if ref() is not None])
                for category, refs in self._tracked_objects.items()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire mémoire"""
        return {
            **self.stats,
            'current_memory_mb': self.get_current_memory_usage(),
            'tracked_objects': self.get_tracked_objects_count(),
            'monitoring': self.monitoring
        }
    
    def optimize_for_screenshots(self):
        """Optimisation spécifique pour les captures d'écran"""
        # Ajuste les paramètres pour les opérations de capture
        original_threshold = self.memory_threshold_mb
        self.memory_threshold_mb = min(300, original_threshold * 0.6)
        
        # Force un nettoyage préventif
        self.force_cleanup()
        
        self.logger.info("Optimisation mémoire pour captures activée")
        
        # Restaure le seuil original après 60 secondes
        def restore_threshold():
            time.sleep(60)
            self.memory_threshold_mb = original_threshold
            self.logger.info("Seuil mémoire restauré")
        
        threading.Thread(target=restore_threshold, daemon=True).start()
    
    def __del__(self):
        """Nettoyage final du gestionnaire"""
        try:
            self.stop_monitoring()
            self.force_cleanup()
        except Exception:
            pass