# SimPy GUI - Production Flow Editor

Interactive graphical interface for modeling and visualizing production flows with SimPy.

## Features

- 🎨 **Graphical Editor** - Interactive canvas with drag & drop, visual connections, real-time buffers
- ⏱️ **Time Management** - Seconds/centiseconds with automatic conversion
- 🌊 **Source Nodes** - Constant, Normal, Poisson, Exponential distributions with batch support
- 🎯 **Sink Nodes** - Track items exiting the system
- 🔀 **Splitter/Merger** - Split flows or combine multiple inputs
- 📏 **Measurement Probes** - Throughput, cycle time, WIP with real-time graphs
- 🔍 **Time Probes** - Processing time, waiting time, total time with statistics
- 📈 **Analysis Window** - Detailed graphs, utilization rates, CSV export
- 🏷️ **Item Types** - Custom colors and type-specific processing times
- 🎮 **Simulation** - SimPy-based with animated flows and adjustable speed (0.1x-10x)

## Installation

**Prerequisites:** Python 3.8+, tkinter

```powershell
pip install -r requirements.txt
python main.py
```

## Quick Start

1. **Add nodes** via "Add Node ▼" menu (sources, processing, sinks, splitter, merger)
2. **Connect nodes** using "Add Connection" tool
3. **Configure** by double-clicking nodes or right-clicking connections
4. **Run simulation** with ▶ Start, ⏸ Pause, ⏹ Stop

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S/O/N` | Save / Open / New |
| `Ctrl+Z/Y` | Undo / Redo |
| `Delete` | Delete selection |
| `Space` | Start/Pause simulation |
| `Escape` | Selection mode |

## Project Structure

```
Simpy_GUI/
├── main.py              # Entry point
├── gui/                 # User interface
├── models/              # Data models
└── simulation/          # SimPy integration
```

## License

MIT License

---

# SimPy GUI - Éditeur de Flux de Production

Interface graphique interactive pour modéliser et visualiser des flux de production avec SimPy.

## Fonctionnalités

- 🎨 **Éditeur Graphique** - Canvas interactif avec drag & drop, connexions visuelles, buffers en temps réel
- ⏱️ **Gestion du Temps** - Secondes/centisecondes avec conversion automatique
- 🌊 **Nœuds Sources** - Distributions constante, normale, Poisson, exponentielle avec lots
- 🎯 **Nœuds Sorties** - Suivi des items quittant le système
- 🔀 **Splitter/Merger** - Diviser ou fusionner des flux
- 📏 **Pipettes de Mesure** - Débit, temps de cycle, WIP avec graphiques temps réel
- 🔍 **Loupes de Temps** - Temps de traitement, attente, total avec statistiques
- 📈 **Fenêtre d'Analyse** - Graphiques détaillés, taux d'utilisation, export CSV
- 🏷️ **Types d'Items** - Couleurs personnalisées et temps spécifiques par type
- 🎮 **Simulation** - Basée sur SimPy avec animation et vitesse réglable (0.1x-10x)

## Installation

**Prérequis :** Python 3.8+, tkinter

```powershell
pip install -r requirements.txt
python main.py
```

## Démarrage Rapide

1. **Ajouter des nœuds** via le menu "Ajouter nœud ▼" (sources, traitement, sorties, splitter, merger)
2. **Connecter les nœuds** avec l'outil "Ajouter connexion"
3. **Configurer** en double-cliquant sur les nœuds ou clic droit sur les connexions
4. **Lancer la simulation** avec ▶ Démarrer, ⏸ Pause, ⏹ Arrêter

## Raccourcis Clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+S/O/N` | Sauvegarder / Ouvrir / Nouveau |
| `Ctrl+Z/Y` | Annuler / Refaire |
| `Suppr` | Supprimer la sélection |
| `Espace` | Démarrer/Pause simulation |
| `Echap` | Mode sélection |

## Structure du Projet

```
Simpy_GUI/
├── main.py              # Point d'entrée
├── gui/                 # Interface utilisateur
├── models/              # Modèles de données
└── simulation/          # Intégration SimPy
```

## Licence

MIT License

