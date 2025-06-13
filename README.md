# 🎯 SnapMaster - Application de Capture d'Écran Avancée

**SnapMaster** est une application de capture d'écran intelligente avec gestion automatique de la mémoire, détection d'applications au premier plan, et organisation par dossiers.

## ✨ Fonctionnalités

### 📸 Captures Multiples
- **Plein écran** : Capture l'écran complet
- **Fenêtre active** : Capture uniquement la fenêtre au premier plan
- **Zone sélectionnée** : Sélection manuelle de la zone à capturer
- **Capture directe d'application** : Capture automatique basée sur l'app active

### 🧠 Gestion Mémoire Intelligente
- Nettoyage automatique de la RAM
- Surveillance continue de l'usage mémoire
- Optimisation lors des captures
- Prévention des fuites mémoire

### 🎮 Détection d'Applications
- Reconnaissance automatique des applications au premier plan
- Distinction entre jeux, navigateurs et applications standard
- Association application → dossier personnalisée
- Historique des applications utilisées

### ⌨️ Raccourcis Clavier Globaux
- Raccourcis configurables pour chaque type de capture
- Fonctionnement en arrière-plan
- Protection contre les répétitions accidentelles
- Support des modificateurs Ctrl, Shift, Alt, Win

### 📁 Organisation par Dossiers
- Dossiers personnalisés configurables
- Association automatique application → dossier
- Nommage automatique des fichiers avec patterns personnalisables
- Support des formats PNG, JPEG, BMP, GIF

## 🔧 Installation

### Prérequis
- Python 3.9 ou supérieur
- Windows, Linux ou macOS

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Dépendances système supplémentaires

#### Windows
```bash
pip install pywin32
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk xdotool

# Fedora/CentOS
sudo dnf install python3-tkinter xdotool
```

#### macOS
```bash
# Avec Homebrew
brew install python-tk
```

## 🚀 Utilisation

### Démarrage de l'application

```bash
python main.py
```

### Intégration des méthodes (première utilisation)

```bash
python integration.py
```

### Structure du projet

```
SnapMaster/
├── main.py                    # Point d'entrée principal
├── requirements.txt           # Dépendances Python
├── integration.py            # Script d'intégration
├── config/
│   ├── __init__.py
│   └── settings.py           # Gestionnaire de configuration
├── core/
│   ├── __init__.py
│   ├── memory_manager.py     # Gestion automatique mémoire
│   ├── screenshot_manager.py # Gestionnaire de captures
│   ├── hotkey_manager.py     # Raccourcis clavier globaux
│   └── app_detector.py       # Détection d'applications
├── gui/
│   ├── __init__.py
│   ├── main_window.py        # Interface principale
│   ├── main_window_methods.py # Méthodes supplémentaires
│   └── settings_window.py    # Fenêtre de paramètres
├── utils/
│   ├── __init__.py
│   └── helpers.py            # Fonctions utilitaires
└── logs/                     # Fichiers de log
```

## ⚙️ Configuration

### Raccourcis clavier par défaut
- **Ctrl+Shift+F** : Capture plein écran
- **Ctrl+Shift+W** : Capture fenêtre active
- **Ctrl+Shift+A** : Capture zone sélectionnée
- **Ctrl+Shift+Q** : Capture rapide application

### Formats supportés
- **PNG** (par défaut) - Sans perte, idéal pour les captures
- **JPEG** - Compressé, plus petit
- **BMP** - Non compressé, très volumineux
- **GIF** - Limité à 256 couleurs

### Paramètres de mémoire
- **Seuil de nettoyage** : 500 MB par défaut
- **Intervalle de surveillance** : 30 secondes
- **Nettoyage automatique** : Activé par défaut

## 🎮 Utilisation Avancée

### Association Application → Dossier

1. Ouvrez l'onglet **Applications**
2. Cliquez sur **➕ Ajouter** dans la section associations
3. Saisissez le nom de l'application (ex: "chrome.exe")
4. Choisissez le dossier de destination
5. Les captures de cette application iront automatiquement dans ce dossier

### Création de dossiers personnalisés

1. Onglet **Capture** → Section "Dossier de destination"
2. Ajoutez vos dossiers personnalisés
3. Associez-les à des applications spécifiques

### Optimisation des performances

- Surveillez l'utilisation mémoire dans l'onglet **Surveillance**
- Ajustez le seuil de nettoyage selon votre système
- Utilisez le nettoyage manuel si nécessaire

## 🐛 Dépannage

### Problèmes courants

#### Les raccourcis clavier ne fonctionnent pas
- Vérifiez que l'application a les permissions nécessaires
- Sous Linux, installez `xdotool`
- Évitez les conflits avec d'autres applications

#### Usage mémoire élevé
- Augmentez la fréquence de nettoyage automatique
- Vérifiez les applications qui monopolisent la mémoire
- Redémarrez l'application si nécessaire

#### Détection d'applications défaillante
- Sous Linux, vérifiez que `xdotool` est installé
- Sous Windows, vérifiez les permissions d'accès aux processus
- Certaines applications peuvent être protégées

### Logs et débogage

Les logs sont sauvegardés dans le dossier `logs/`:
- `snapmaster.log` : Log principal
- Niveau de log configurable dans les paramètres avancés

## 🔒 Sécurité et Permissions

### Permissions requises
- **Capture d'écran** : Accès aux données d'affichage
- **Hotkeys globaux** : Surveillance du clavier système
- **Détection d'applications** : Accès aux informations des processus
- **Écriture fichiers** : Sauvegarde des captures et configuration

### Confidentialité
- Aucune donnée n'est envoyée sur Internet
- Les captures restent locales sur votre système
- Les logs ne contiennent pas d'informations sensibles

## 🛠️ Développement

### Architecture modulaire
- **core/** : Logique métier et gestionnaires principaux
- **gui/** : Interface utilisateur Tkinter
- **config/** : Gestion de la configuration
- **utils/** : Fonctions utilitaires communes

### Extension et personnalisation
- Ajout de nouveaux formats d'image
- Personnalisation des raccourcis clavier
- Intégration de nouveaux gestionnaires de fichiers
- Amélioration de la détection d'applications

## 📝 Configuration JSON

Le fichier de configuration `config/snapmaster_config.json` contient tous les paramètres :

```json
{
  "version": "1.0.0",
  "folders": {
    "default_screenshots": "C:/Users/User/Pictures/SnapMaster",
    "custom_folders": {
      "Gaming": "C:/GameScreenshots",
      "Work": "D:/WorkCaptures"
    }
  },
  "applications": {
    "app_folder_mapping": {
      "chrome.exe": "Work",
      "notepad.exe": "default"
    }
  },
  "hotkeys": {
    "fullscreen_capture": "ctrl+shift+f",
    "window_capture": "ctrl+shift+w",
    "area_capture": "ctrl+shift+a",
    "quick_capture": "ctrl+shift+q"
  }
}
```

## 🚀 Fonctionnalités Avancées

### Nettoyage Automatique Mémoire
- Surveillance continue en arrière-plan
- Nettoyage proactif avant les captures
- Statistiques détaillées disponibles
- Configuration fine des seuils

### Optimisation Multi-écrans
- Détection automatique des écrans multiples
- Capture spécifique par écran
- Gestion des résolutions différentes

### Mode Gaming
- Détection automatique des jeux
- Optimisation des performances
- Capture sans interruption du jeu

## ❓ FAQ

**Q: L'application consomme-t-elle beaucoup de ressources ?**
R: Non, SnapMaster est conçu pour une utilisation minimale des ressources avec nettoyage automatique de la mémoire.

**Q: Peut-on utiliser SnapMaster avec plusieurs écrans ?**
R: Oui, la détection multi-écrans est supportée automatiquement.

**Q: Les raccourcis fonctionnent-ils dans les jeux ?**
R: Oui, les raccourcis globaux fonctionnent même quand les jeux sont au premier plan.

**Q: Comment sauvegarder ma configuration ?**
R: Utilisez Menu → Fichier → Exporter configuration pour créer une sauvegarde.

## 📞 Support

Pour tout problème ou suggestion :
1. Consultez les logs dans le dossier `logs/`
2. Vérifiez la configuration dans les Paramètres
3. Testez les capacités avec Menu → Capture → Test des capacités

---

## 🎖️ Crédits

**SnapMaster** - Application de capture d'écran avancée
Développé avec Python, Tkinter, PyAutoGUI et beaucoup de café ☕

*Optimisé pour la performance, conçu pour la simplicité.*