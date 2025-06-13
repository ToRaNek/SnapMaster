# core/__init__.py
"""
Module core de SnapMaster
Contient les gestionnaires principaux
"""

from .memory_manager import MemoryManager
from .screenshot_manager import ScreenshotManager
from .hotkey_manager import HotkeyManager
from .app_detector import AppDetector, AppInfo

__all__ = [
    'MemoryManager',
    'ScreenshotManager',
    'HotkeyManager',
    'AppDetector',
    'AppInfo'
]