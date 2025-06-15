# build_exe.py
"""
Script de build pour créer l'exécutable SnapMaster
Automatise la création de l'exécutable sans console qui reste en arrière-plan
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
import time

def print_step(message):
    """Affiche une étape avec formatage"""
    print(f"\n{'='*60}")
    print(f"🔧 {message}")
    print(f"{'='*60}")

def print_info(message):
    """Affiche une information"""
    print(f"ℹ️  {message}")

def print_success(message):
    """Affiche un succès"""
    print(f"✅ {message}")

def print_error(message):
    """Affiche une erreur"""
    print(f"❌ {message}")

def print_warning(message):
    """Affiche un avertissement"""
    print(f"⚠️  {message}")

def check_requirements():
    """Vérifie que tous les prérequis sont installés"""
    print_step("Vérification des prérequis")

    # Vérifie Python
    python_version = sys.version_info
    print_info(f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    if python_version < (3, 8):
        print_error("Python 3.8+ requis")
        return False

    # Vérifie PyInstaller
    try:
        import PyInstaller
        print_info(f"PyInstaller {PyInstaller.__version__} détecté")
    except ImportError:
        print_error("PyInstaller non installé")
        print_info("Installation: pip install pyinstaller")
        return False

    # Vérifie les


    return True

def prepare_build_environment():
    """Prépare l'environnement de build"""
    print_step("Préparation de l'environnement de build")

    # Nettoie les anciens builds
    build_dirs = ['build', 'dist', '__pycache__']
    for build_dir in build_dirs:
        if Path(build_dir).exists():
            print_info(f"Nettoyage de {build_dir}/")
            shutil.rmtree(build_dir)

    # Crée le dossier assets s'il n'existe pas
    assets_dir = Path('assets')
    if not assets_dir.exists():
        assets_dir.mkdir()
        print_info("Dossier assets/ créé")

    # Crée une icône par défaut si elle n'existe pas
    icon_path = assets_dir / 'icon.ico'
    if not icon_path.exists():
        create_default_icon(icon_path)

    # Crée le fichier de version
    create_version_file()

    print_success("Environnement préparé")

def create_default_icon(icon_path):
    """Crée une icône par défaut"""
    try:
        from PIL import Image, ImageDraw

        # Crée une image 64x64 avec un design simple
        img = Image.new('RGBA', (64, 64), (30, 58, 138, 255))  # Bleu SnapMaster
        draw = ImageDraw.Draw(img)

        # Dessine un "S" stylisé
        # Fond circle bleu clair
        draw.ellipse([8, 8, 56, 56], fill=(59, 130, 246, 255), outline=(255, 255, 255, 255), width=2)

        # Dessine le "S"
        s_coords = [
            # Partie haute du S
            [(20, 16), (44, 24)],
            [(20, 24), (28, 32)],
            # Partie milieu du S
            [(20, 32), (44, 40)],
            [(36, 40), (44, 48)],
            # Partie basse du S
            [(20, 48), (44, 56)]
        ]

        for coords in s_coords:
            draw.rectangle([coords[0], coords[1]], fill=(255, 255, 255, 255))

        # Sauvegarde en ICO
        img.save(icon_path, format='ICO', sizes=[(64, 64), (32, 32), (16, 16)])
        print_info(f"Icône par défaut créée: {icon_path}")

    except Exception as e:
        print_warning(f"Impossible de créer l'icône par défaut: {e}")

def create_version_file():
    """Crée le fichier de version pour Windows"""
    version_content = """
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'SnapMaster'),
          StringStruct(u'FileDescription', u'SnapMaster - Capture d\'écran avancée'),
          StringStruct(u'FileVersion', u'1.0.0.0'),
          StringStruct(u'InternalName', u'SnapMaster'),
          StringStruct(u'LegalCopyright', u'Copyright © 2024'),
          StringStruct(u'OriginalFilename', u'SnapMaster.exe'),
          StringStruct(u'ProductName', u'SnapMaster'),
          StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_content.strip())

    print_info("Fichier de version créé")

def build_executable():
    """Build l'exécutable avec PyInstaller"""
    print_step("Construction de l'exécutable")

    # Commande PyInstaller avec python -m pour éviter les problèmes de PATH
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',  # Nettoie le cache
        '--noconfirm',  # Pas de confirmation
        'SnapMaster.spec'  # Utilise le fichier spec personnalisé
    ]

    print_info(f"Commande: {' '.join(cmd)}")

    try:
        # Exécute PyInstaller
        process = subprocess.run(
            cmd,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )

        if process.returncode == 0:
            print_success("Build réussi !")
            return True
        else:
            print_error("Erreur lors du build")
            print("STDOUT:", process.stdout[-1000:])  # Dernières 1000 caractères
            print("STDERR:", process.stderr[-1000:])
            return False

    except subprocess.TimeoutExpired:
        print_error("Timeout lors du build (5 minutes)")
        return False
    except Exception as e:
        print_error(f"Erreur lors du build: {e}")
        return False

def post_build_operations():
    """Opérations post-build"""
    print_step("Opérations post-build")

    exe_path = Path('dist/SnapMaster.exe')

    if not exe_path.exists():
        print_error("Exécutable introuvable dans dist/")
        return False

    # Vérifie la taille
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print_info(f"Taille de l'exécutable: {size_mb:.1f} MB")

    if size_mb > 100:
        print_warning("Exécutable volumineux (>100MB)")

    # Crée un dossier de release
    release_dir = Path('release')
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()

    # Copie l'exécutable
    release_exe = release_dir / 'SnapMaster.exe'
    shutil.copy2(exe_path, release_exe)

    # Copie les fichiers de documentation
    docs_to_copy = ['README.md', 'requirements.txt']
    for doc in docs_to_copy:
        if Path(doc).exists():
            shutil.copy2(doc, release_dir / doc)

    # Crée un script de démarrage
    create_startup_script(release_dir)

    print_success(f"Release créée dans: {release_dir.absolute()}")
    return True

def create_startup_script(release_dir):
    """Crée un script de démarrage automatique"""
    if platform.system() == "Windows":
        # Script batch pour Windows
        bat_content = '''@echo off
echo Démarrage de SnapMaster...
start "" "%~dp0SnapMaster.exe"
echo SnapMaster démarré en arrière-plan
timeout /t 2 /nobreak >nul
'''
        with open(release_dir / 'Démarrer_SnapMaster.bat', 'w', encoding='cp1252') as f:
            f.write(bat_content)

        print_info("Script de démarrage Windows créé")

    # Script shell pour Linux/macOS
    sh_content = '''#!/bin/bash
echo "Démarrage de SnapMaster..."
./SnapMaster &
echo "SnapMaster démarré en arrière-plan"
sleep 2
'''
    sh_path = release_dir / 'start_snapmaster.sh'
    with open(sh_path, 'w') as f:
        f.write(sh_content)

    # Rend exécutable sur Unix
    if platform.system() != "Windows":
        os.chmod(sh_path, 0o755)

    print_info("Script de démarrage Unix créé")

def create_installer_info():
    """Crée des informations d'installation"""
    print_step("Création des informations d'installation")

    install_info = """
🎯 SnapMaster - Installation

INSTALLATION:
1. Extraire tous les fichiers dans un dossier de votre choix
2. Double-cliquer sur SnapMaster.exe pour lancer l'application
3. L'application se minimise automatiquement dans la barre système

DÉMARRAGE AUTOMATIQUE:
- Windows: Utiliser Démarrer_SnapMaster.bat
- Linux/macOS: Utiliser start_snapmaster.sh

UTILISATION:
- L'application reste en arrière-plan (icône dans la barre système)
- Clic droit sur l'icône pour accéder aux fonctions
- Utilisation des raccourcis clavier configurés

RACCOURCIS PAR DÉFAUT:
- Ctrl+Shift+F : Capture plein écran
- Ctrl+Shift+W : Capture fenêtre active
- Ctrl+Shift+A : Capture zone sélectionnée
- Ctrl+Shift+Q : Capture rapide

CONFIGURATION:
- Clic droit sur l'icône système → Paramètres
- Ou double-clic sur l'icône pour afficher la fenêtre principale

DÉSINSTALLATION:
- Supprimer simplement le dossier d'installation
- Aucune trace laissée dans le registre

Pour plus d'informations, consultez README.md
"""

    with open('release/INSTALLATION.txt', 'w', encoding='utf-8') as f:
        f.write(install_info.strip())

    print_success("Informations d'installation créées")

def test_executable():
    """Teste l'exécutable créé"""
    print_step("Test de l'exécutable")

    exe_path = Path('release/SnapMaster.exe')

    if not exe_path.exists():
        print_error("Exécutable introuvable pour le test")
        return False

    print_info("Lancement du test (l'app se fermera automatiquement)...")

    try:
        # Lance l'exe en mode test
        process = subprocess.Popen(
            [str(exe_path)],
            cwd=str(exe_path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Attend un peu
        time.sleep(3)

        # Vérifie si le processus tourne
        if process.poll() is None:
            print_success("Exécutable démarré avec succès")
            # Termine le processus de test
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
            return True
        else:
            print_error("L'exécutable s'est fermé immédiatement")
            return False

    except Exception as e:
        print_error(f"Erreur lors du test: {e}")
        return False

def cleanup_build_files():
    """Nettoie les fichiers de build temporaires"""
    print_step("Nettoyage des fichiers temporaires")

    temp_files = [
        'build',
        'SnapMaster.spec.bak',
        'version_info.txt',
        '__pycache__'
    ]

    for temp_file in temp_files:
        path = Path(temp_file)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print_info(f"Supprimé: {temp_file}")

    print_success("Nettoyage terminé")

def main():
    """Fonction principale de build"""
    print("🚀 Build SnapMaster - Exécutable sans console")
    print(f"Plateforme: {platform.system()} {platform.architecture()[0]}")

    start_time = time.time()

    try:
        # 1. Vérification des prérequis
        if not check_requirements():
            sys.exit(1)

        # 2. Préparation de l'environnement
        prepare_build_environment()

        # 3. Build de l'exécutable
        if not build_executable():
            sys.exit(1)

        # 4. Opérations post-build
        if not post_build_operations():
            sys.exit(1)

        # 5. Informations d'installation
        create_installer_info()

        # 6. Test de l'exécutable
        test_executable()

        # 7. Nettoyage
        cleanup_build_files()

        # Temps total
        build_time = time.time() - start_time

        print_step("Build terminé avec succès !")
        print_success(f"Temps de build: {build_time:.1f} secondes")
        print_success("Exécutable prêt dans le dossier 'release/'")
        print("\n📁 Contenu de la release:")
        for file in Path('release').iterdir():
            size = file.stat().st_size
            if size > 1024*1024:
                size_str = f"{size/(1024*1024):.1f} MB"
            elif size > 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size} B"
            print(f"   📄 {file.name} ({size_str})")

        print(f"\n🎯 Pour utiliser SnapMaster:")
        print(f"   1. Aller dans le dossier 'release/'")
        print(f"   2. Double-cliquer sur SnapMaster.exe")
        print(f"   3. L'application se minimise automatiquement dans la barre système")
        print(f"   4. Utiliser les raccourcis clavier ou clic droit sur l'icône système")

    except KeyboardInterrupt:
        print("\n❌ Build interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()