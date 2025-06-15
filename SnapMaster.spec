# SnapMaster.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Chemin de base du projet
PROJECT_ROOT = os.path.dirname(os.path.abspath('.'))

# Données additionnelles à inclure
added_files = [
    # Configuration par défaut
    ('config', 'config'),
    # Assets si ils existent
    # ('assets', 'assets'),
    # README
    ('README.md', '.'),
]

# Modules cachés à inclure explicitement
hidden_imports = [
    'pystray._win32',
    'pystray._gtk',
    'pystray._osx',
    'PIL._tkinter_finder',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageEnhance',
    'pyautogui',
    'keyboard',
    'psutil',
    'win32gui',
    'win32ui',
    'win32con',
    'win32api',
    'win32process',
    'ctypes',
    'ctypes.wintypes',
    'threading',
    'logging.handlers',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'tkinter.simpledialog',
    'tkinter.colorchooser',
    'json',
    'subprocess',
    'time',
    'datetime',
    'pathlib',
    'weakref',
    'platform',
    'tempfile',
    'io',
    'hashlib',
    'unicodedata',
    're',
]

# Binaires à exclure pour réduire la taille
exclude_binaries = [
    'Qt5Core.dll',
    'Qt5Gui.dll',
    'Qt5Widgets.dll',
    'Qt5Svg.dll',
    'Qt5Network.dll',
    'libcrypto*.dll',
    'libssl*.dll',
    'VCRUNTIME140_1.dll',
]

# Modules à exclure
excludes = [
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'notebook',
    'tornado',
    'zmq',
    'ssl',
    'urllib3',
    'requests',
    'certifi',
    'chardet',
    'idna',
    'test',
    'unittest',
    'pydoc',
    'doctest',
    'xml',
    'xmlrpc',
    'email',
    'calendar',
    'pprint',
    'pickle',
    'mailbox',
    'distutils',
    'setuptools',
    'pip',
    'wheel',
]

# Configuration de l'analyse
a = Analysis(
    ['main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
    optimize=2,  # Optimisation Python niveau 2
)

# Filtrage des binaires pour réduire la taille
def filter_binaries(binaries):
    """Filtre les binaires non nécessaires"""
    filtered = []
    for binary in binaries:
        name = binary[0]
        exclude = False

        # Exclut les DLLs spécifiées
        for exclude_pattern in exclude_binaries:
            if exclude_pattern.replace('*', '') in name:
                exclude = True
                break

        if not exclude:
            filtered.append(binary)

    return filtered

# Application du filtre
a.binaries = filter_binaries(a.binaries)

# Configuration PYZ (archive Python)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None
)

# Configuration de l'exécutable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SnapMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compression UPX pour réduire la taille
    upx_exclude=[
        'vcruntime140.dll',
        'python39.dll',
        'python310.dll',
        'python311.dll',
        'python312.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # PAS DE CONSOLE !
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
    # version='version_info.txt' if os.path.exists('version_info.txt') else None,  # Désactivé temporairement
    uac_admin=False,  # Ne demande pas les privilèges admin
    uac_uiaccess=False,
    manifest=None,
)

# Configuration pour distribution (dossier)
# Décommentez si vous voulez aussi une version dossier
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='SnapMaster_folder'
# )