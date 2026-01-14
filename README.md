# SimPy GUI - Éditeur de Flux de Production / Production Flow Editor

Interface graphique interactive pour modéliser et visualiser des flux de production avec SimPy.

*Interactive graphical interface for modeling and visualizing production flows with SimPy.*

## Caractéristiques / Features

### 🎨 Éditeur Graphique / Graphical Editor
- **Canvas interactif** pour créer des diagrammes de flux / **Interactive canvas** to create flow diagrams
- **Drag & drop** pour positionner les nœuds / **Drag & drop** to position nodes
- **Connexions visuelles** entre les étapes du processus / **Visual connections** between process steps
- **Buffers graphiques** visibles sur les connexions ET les nœuds en temps réel / **Graphical buffers** visible on connections AND nodes in real-time
- **Clic droit sur les connexions** pour configurer les buffers / **Right-click on connections** to configure buffers

### ⏱️ Gestion du Temps / Time Management
- **2 unités de temps disponibles** : secondes, centisecondes / **2 time units available**: seconds, centiseconds
- **Conversion automatique** lors du changement d'unité / **Automatic conversion** when changing units
- Toute l'interface s'adapte automatiquement / The entire interface adapts automatically

### 🔀 Flux Parallèles Avancés / Advanced Parallel Flows
Trois modes de synchronisation pour les nœuds avec plusieurs entrées : / Three synchronization modes for nodes with multiple inputs:
- **Premier disponible** : traite dès qu'un item arrive / **First available**: processes as soon as an item arrives
- **Attendre tous les flux** : attend un item de chaque branche / **Wait for all flows**: waits for an item from each branch
- **Attendre N unités par branche** : configuration personnalisée pour chaque entrée / **Wait for N units per branch**: custom configuration for each input

### 🌊 Nœuds Sources (Générateurs de Flux) / Source Nodes (Flow Generators)
Créez des points d'entrée dans votre système avec différentes lois d'arrivée : / Create entry points in your system with different arrival distributions:
- **Source Constante** : génération à intervalles réguliers / **Constant Source**: generation at regular intervals
- **Source Loi Normale** : intervalles suivant une distribution normale (moyenne + écart-type) / **Normal Distribution Source**: intervals following a normal distribution (mean + standard deviation)
- **Source Loi de Poisson** : arrivées selon un processus de Poisson (paramètre λ) / **Poisson Distribution Source**: arrivals following a Poisson process (λ parameter)
- **Source Loi Exponentielle** : intervalles exponentiels (paramètre λ) / **Exponential Distribution Source**: exponential intervals (λ parameter)

Les nœuds sources sont **visuellement distincts** (couleur verte) et affichent : / Source nodes are **visually distinct** (green color) and display:
- L'intervalle de génération / The generation interval
- **Le nombre d'items générés** (ex: 45/100 ou simplement 45 si illimité) / **The number of generated items** (e.g., 45/100 or just 45 if unlimited)
- Contrôle précis du nombre total d'items à injecter dans le système / Precise control of the total number of items to inject into the system
- **Taille des lots** : générez plusieurs unités à la fois (ex: 5 unités par arrivée) / **Batch size**: generate multiple units at once (e.g., 5 units per arrival)

### 🎯 Nœuds Sorties (Sinks) / Output Nodes (Sinks)
Créez des points de sortie pour visualiser les flux qui quittent le système : / Create exit points to visualize flows leaving the system:
- **Couleur rouge distinctive** pour identifier facilement les sorties / **Distinctive red color** to easily identify exits
- **Compteur d'items reçus** : affiche combien d'items ont terminé le processus / **Received items counter**: displays how many items have completed the process
- Permet de mesurer le débit et l'efficacité du système / Allows measuring throughput and system efficiency

### 🔀 Nœuds Splitter / Splitter Nodes
Divisez un flux en plusieurs branches : / Split a flow into multiple branches:
- **Distribution configurable** : définissez le pourcentage ou la proportion pour chaque sortie / **Configurable distribution**: define the percentage or proportion for each output
- **Couleur orange distinctive** / **Distinctive orange color**

### 🔗 Nœuds Merger / Merger Nodes
Combinez plusieurs flux en un seul : / Combine multiple flows into one:
- **Fusion automatique** des items de différentes sources / **Automatic merging** of items from different sources
- **Couleur cyan distinctive** / **Distinctive cyan color**

### 📊 Configuration des Nœuds / Node Configuration
Pour chaque nœud, vous pouvez configurer : / For each node, you can configure:
- Nom personnalisé / Custom name
- Temps de traitement (dans l'unité de votre choix) / Processing time (in your chosen unit)
- Capacité du buffer (illimitée ou fixe) / Buffer capacity (unlimited or fixed)
- Mode de synchronisation pour les flux multiples / Synchronization mode for multiple flows
- Nombre d'unités requises par branche / Number of units required per branch

### 📏 Pipettes de Mesure / Measurement Probes
Placez des pipettes sur les connexions pour mesurer : / Place probes on connections to measure:
- **Débit** : nombre d'items passant par seconde / **Throughput**: number of items passing per second
- **Temps de cycle** : temps entre deux passages / **Cycle time**: time between two passes
- **WIP (Work In Progress)** : items en cours dans une section / **WIP (Work In Progress)**: items in progress in a section
- Graphiques en temps réel pendant la simulation / Real-time graphs during simulation

### 🔍 Loupes de Temps (Time Probes) / Time Probes (Magnifying Glass)
Mesurez les temps de traversée entre deux points : / Measure transit times between two points:
- **Temps de traitement** : durée dans les nœuds de traitement / **Processing time**: duration in processing nodes
- **Temps d'attente** : durée dans les buffers / **Waiting time**: duration in buffers
- **Temps total** : de l'entrée à la sortie / **Total time**: from entry to exit
- Statistiques détaillées (min, max, moyenne, écart-type) / Detailed statistics (min, max, mean, standard deviation)

### 📈 Fenêtre d'Analyse / Analysis Window
Après simulation, visualisez des graphiques détaillés : / After simulation, view detailed graphs:
- **Débit par intervalle** pour chaque pipette / **Throughput per interval** for each probe
- **Taux d'utilisation** des opérateurs / **Utilization rate** of operators
- **WIP au fil du temps** / **WIP over time**
- **Temps de cycle** par type d'item / **Cycle time** by item type
- Export CSV des données / CSV data export

### 🏷️ Types d'Items / Item Types
Définissez différents types d'items avec : / Define different item types with:
- **Couleurs personnalisées** pour visualisation / **Custom colors** for visualization
- **Temps de traitement spécifiques** par type et par opérateur / **Specific processing times** per type and operator
- **Statistiques séparées** par type / **Separate statistics** per type

### 🎮 Simulation
- Exécution basée sur **SimPy** / **SimPy-based** execution
- **Mise à jour automatique en temps réel** : le canvas se rafraîchit automatiquement pendant la simulation / **Automatic real-time update**: canvas refreshes automatically during simulation
- **Animation des flux** : points colorés animés montrant les items en transit le long des connexions / **Flow animation**: colored animated dots showing items in transit along connections
- Visualisation en temps réel des buffers et compteurs / Real-time visualization of buffers and counters
- Contrôles : Démarrer, Pause, Arrêter / Controls: Start, Pause, Stop
- Vitesse de simulation réglable (0.1x à 10x) / Adjustable simulation speed (0.1x to 10x)

## Installation

### Prérequis / Prerequisites
- Python 3.8 ou supérieur / Python 3.8 or higher
- tkinter (généralement inclus avec Python) / tkinter (usually included with Python)

### Installation des dépendances / Installing Dependencies

```powershell
pip install -r requirements.txt
```

Les dépendances incluent : / Dependencies include:
- `simpy` : Moteur de simulation d'événements discrets / Discrete event simulation engine
- `matplotlib` : Pour les visualisations et graphiques / For visualizations and graphs
- `numpy` : Pour les calculs statistiques / For statistical calculations
- `tkinter-tooltip` : Pour les info-bulles / For tooltips

## Utilisation / Usage

### Démarrer l'application / Start the Application

```powershell
python main.py
```

### Utilisation de l'éditeur / Using the Editor

#### 1. Ajouter des nœuds sources (flux entrant) / Add Source Nodes (Incoming Flow)
1. Cliquez sur **"Ajouter nœud ▼"** dans la barre d'outils / Click **"Add Node ▼"** in the toolbar
2. Choisissez un type de source dans le sous-menu : / Choose a source type from the submenu:
   - Source Constante / Constant Source
   - Source Loi Normale / Normal Distribution Source
   - Source Loi de Poisson / Poisson Distribution Source
3. Cliquez sur le canvas pour placer le nœud / Click on the canvas to place the node
4. Double-cliquez pour configurer l'intervalle et les paramètres / Double-click to configure interval and parameters

#### 2. Ajouter des nœuds de traitement / Add Processing Nodes
1. Cliquez sur **"Ajouter nœud ▼"** → **"Nœud de traitement"** / Click **"Add Node ▼"** → **"Processing Node"**
2. Cliquez sur le canvas pour placer un nœud / Click on the canvas to place a node
3. Double-cliquez sur le nœud pour le configurer / Double-click on the node to configure it

#### 3. Ajouter des sorties (Sinks) / Add Outputs (Sinks)
1. Cliquez sur **"Ajouter nœud ▼"** → **"Sortie (Sink)"** / Click **"Add Node ▼"** → **"Output (Sink)"**
2. Placez-le à la fin de votre flux / Place it at the end of your flow
3. Les items qui arrivent à ce nœud sont comptabilisés et "sortent" du système / Items arriving at this node are counted and "exit" the system

#### 4. Créer des connexions / Create Connections
1. Cliquez sur **"Ajouter connexion"** dans la barre d'outils / Click **"Add Connection"** in the toolbar
2. Cliquez sur le nœud source / Click on the source node
3. Cliquez sur le nœud destination / Click on the destination node
4. La connexion est créée avec un buffer visible / The connection is created with a visible buffer
5. **Clic droit sur le buffer de la connexion** pour configurer sa capacité / **Right-click on the connection buffer** to configure its capacity

#### 5. Configurer un nœud / Configure a Node
Double-cliquez sur un nœud pour ouvrir la fenêtre de configuration : / Double-click on a node to open the configuration window:

**Pour les nœuds sources : / For source nodes:**
- **Nom** : Identifiant du nœud / **Name**: Node identifier
- **Nombre d'items** : Quantité totale à générer (0 = illimité) / **Number of items**: Total quantity to generate (0 = unlimited)
- **Unités par lot** : Nombre d'items générés simultanément / **Units per batch**: Number of items generated simultaneously
- **Intervalle moyen** : Temps entre deux générations de lots / **Mean interval**: Time between batch generations
- **Paramètres spécifiques** : Écart-type (Normale) ou λ (Poisson/Exponentielle) / **Specific parameters**: Standard deviation (Normal) or λ (Poisson/Exponential)

**Pour les nœuds de traitement : / For processing nodes:**
- **Nom** : Identifiant du nœud / **Name**: Node identifier
- **Temps de traitement** : Durée pour traiter un item / **Processing time**: Duration to process an item
- **Buffer** : Capacité de stockage / **Buffer**: Storage capacity
- **Flux multiples** : Configuration de la synchronisation / **Multiple flows**: Synchronization configuration

**Pour les nœuds sorties : / For output nodes:**
- Pas de configuration nécessaire, ils comptent automatiquement les items reçus / No configuration needed, they automatically count received items

#### 6. Changer l'unité de temps / Change Time Unit
Utilisez le menu déroulant "Afficher en" dans la barre d'outils : / Use the "Display in" dropdown in the toolbar:
- Toutes les valeurs sont automatiquement converties / All values are automatically converted
- Les nœuds affichent les temps dans la nouvelle unité / Nodes display times in the new unit

#### 7. Configurer les buffers sur les connexions / Configure Buffers on Connections
1. **Clic droit sur le buffer** au milieu d'une connexion / **Right-click on the buffer** in the middle of a connection
2. Configurez : / Configure:
   - Visibilité du buffer / Buffer visibility
   - Capacité (illimitée ou fixe) / Capacity (unlimited or fixed)
   - Taille visuelle de l'indicateur / Visual size of the indicator

#### 8. Lancer une simulation / Run a Simulation
1. Créez votre flux de production (sources → traitement → sorties) / Create your production flow (sources → processing → outputs)
2. Cliquez sur **"▶ Démarrer"** / Click **"▶ Start"**
3. **Le canvas se met à jour automatiquement** pour afficher : / **The canvas updates automatically** to display:
   - **Points colorés animés** se déplaçant le long des connexions (items en transit) / **Colored animated dots** moving along connections (items in transit)
   - Les buffers qui se remplent et se vident / Buffers filling and emptying
   - Les compteurs d'items (sources et sorties) / Item counters (sources and outputs)
   - L'état en temps réel du système / Real-time system state
4. Utilisez **"⏸ Pause"** ou **"⏹ Arrêter"** pour contrôler / Use **"⏸ Pause"** or **"⏹ Stop"** to control

### Raccourcis Clavier / Keyboard Shortcuts

| Raccourci / Shortcut | Action |
|---------------------|--------|
| `Ctrl+S` | Sauvegarder / Save |
| `Ctrl+O` | Ouvrir / Open |
| `Ctrl+N` | Nouveau / New |
| `Ctrl+Z` | Annuler / Undo |
| `Ctrl+Y` | Refaire / Redo |
| `Suppr` / `Delete` | Supprimer la sélection / Delete selection |
| `Espace` / `Space` | Démarrer/Pause simulation / Start/Pause simulation |
| `Echap` / `Escape` | Mode sélection / Selection mode |
| `Q` | Quitter / Quit |

### Modes d'édition / Editing Modes

- **Sélection** (par défaut) : Sélectionner et déplacer les nœuds / **Selection** (default): Select and move nodes
- **Ajouter nœud** : Menu déroulant pour choisir le type de nœud / **Add node**: Dropdown menu to choose node type
- **Ajouter connexion** : Relier deux nœuds / **Add connection**: Link two nodes
- **Ajouter pipette** : Placer une pipette de mesure / **Add probe**: Place a measurement probe

### Interactions

- **Double-clic sur un nœud** : Configurer le nœud / **Double-click on a node**: Configure the node
- **Clic droit sur une connexion** : Configurer le buffer de la connexion / **Right-click on a connection**: Configure the connection buffer
- **Clic droit sur une pipette** : Configurer ou supprimer la pipette / **Right-click on a probe**: Configure or delete the probe
- `Suppr` : Supprimer le nœud sélectionné / `Delete`: Delete selected node

## Architecture du Projet / Project Architecture

```
Simpy_GUI/
│
├── main.py                 # Point d'entrée / Entry point
├── requirements.txt        # Dépendances Python / Python dependencies
├── README.md               # Documentation
│
├── gui/                    # Interface graphique / Graphical interface
│   ├── __init__.py
│   ├── main_window.py      # Fenêtre principale / Main window
│   ├── flow_canvas.py      # Canvas de dessin / Drawing canvas
│   ├── node_config_dialog.py       # Configuration des nœuds / Node configuration
│   ├── connection_config_dialog.py # Configuration des connexions / Connection configuration
│   ├── analysis_panel.py           # Panneau d'analyse / Analysis panel
│   ├── analysis_graph_window.py    # Fenêtre des graphiques / Graph window
│   ├── measurement_graphs_panel.py # Panneau des pipettes / Probes panel
│   ├── time_probe_panel.py         # Panneau des loupes / Time probes panel
│   ├── translations.py             # Traductions FR/EN / FR/EN translations
│   └── ...
│
├── models/                 # Modèles de données / Data models
│   ├── __init__.py
│   ├── flow_model.py       # Modèle du flux / Flow model
│   ├── time_converter.py   # Gestion des unités de temps / Time unit management
│   ├── measurement_probe.py # Pipettes de mesure / Measurement probes
│   └── time_probe.py       # Loupes de temps / Time probes
│
└── simulation/             # Moteur de simulation / Simulation engine
    ├── __init__.py
    └── simulator.py        # Intégration SimPy / SimPy integration
```

## Fonctionnalités Implémentées / Implemented Features

- ✅ Sauvegarde/Chargement de modèles (.simpy) / Save/Load models (.simpy)
- ✅ Export de statistiques (CSV) / Statistics export (CSV)
- ✅ Graphiques de performance / Performance graphs
- ✅ Animation des items en transit / Item transit animation
- ✅ Pipettes de mesure / Measurement probes
- ✅ Loupes de temps / Time probes
- ✅ Types d'items personnalisés / Custom item types
- ✅ Interface bilingue FR/EN / Bilingual FR/EN interface
- ✅ Nœuds Splitter et Merger / Splitter and Merger nodes

## Contribution

Ce projet est en développement actif. N'hésitez pas à proposer des améliorations !

*This project is under active development. Feel free to suggest improvements!*

## Licence / License

MIT License - Libre d'utilisation et de modification / Free to use and modify

## Support

Pour toute question ou problème, créez une issue sur le dépôt du projet.

*For any questions or issues, create an issue on the project repository.*

