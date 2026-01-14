"""Fenêtre principale de l'application / Main application window"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from gui.flow_canvas import FlowCanvas
from gui.node_config_dialog import NodeConfigDialog
from gui.translations import tr, set_language, get_language
from models.flow_model import FlowModel, NodeType
from models.time_converter import TimeUnit, TimeConverter
from simulation.simulator import FlowSimulator

# Fichier de configuration utilisateur (dans le dossier de l'application) / User config file (in application folder)
USER_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_config.json')

def load_user_config() -> dict:
    """Charge la configuration utilisateur depuis le fichier JSON / Load user config from JSON file"""
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def save_user_config(config: dict):
    """Sauvegarde la configuration utilisateur dans le fichier JSON / Save user config to JSON file"""
    try:
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError:
        pass

class AppConfig:
    """Configuration globale de l'application / Global application configuration"""
    def __init__(self):
        # Valeurs par défaut / Default values
        self.DEBUG_MODE = False
        self.OPERATOR_MOVEMENT_THRESHOLD = 2.0
        self.NODE_POSITION_CACHE_VALIDITY_MS = 50
        self.OPERATOR_PROBE_MAX_MEASUREMENTS = 1000
        self.PROBE_ANALYSIS_MAX_POINTS = 500000  # Limite de points pour pipettes en mode analyse / Point limit for probes in analysis mode
        self.UI_UPDATE_INTERVAL = 0.2
        self.OPERATOR_ANIMATION_STEPS = 7
        self.ENABLE_ANIMATIONS = True
        self.LANGUAGE = 'fr'  # Langue de l'interface (fr ou en) / Interface language (fr or en)
        
        # Charger la configuration utilisateur (notamment la langue) / Load user config (especially language)
        user_config = load_user_config()
        if 'language' in user_config:
            self.LANGUAGE = user_config['language']
        # Appliquer la langue immédiatement (avant création des widgets) / Apply language immediately (before widget creation)
        set_language(self.LANGUAGE)
    
    def update_from_dict(self, params: dict):
        """Met à jour la configuration depuis un dictionnaire / Update configuration from dictionary"""
        self.DEBUG_MODE = params.get('debug_mode', self.DEBUG_MODE)
        self.OPERATOR_MOVEMENT_THRESHOLD = params.get('movement_threshold', self.OPERATOR_MOVEMENT_THRESHOLD)
        self.NODE_POSITION_CACHE_VALIDITY_MS = params.get('cache_validity', self.NODE_POSITION_CACHE_VALIDITY_MS)
        self.OPERATOR_PROBE_MAX_MEASUREMENTS = params.get('probe_max_measurements', self.OPERATOR_PROBE_MAX_MEASUREMENTS)
        self.PROBE_ANALYSIS_MAX_POINTS = params.get('probe_analysis_max_points', self.PROBE_ANALYSIS_MAX_POINTS)
        self.UI_UPDATE_INTERVAL = params.get('ui_update_interval', self.UI_UPDATE_INTERVAL)
        self.OPERATOR_ANIMATION_STEPS = params.get('animation_steps', self.OPERATOR_ANIMATION_STEPS)
        self.ENABLE_ANIMATIONS = params.get('enable_animations', self.ENABLE_ANIMATIONS)
        # Mise à jour de la langue / Language update
        if 'language' in params:
            self.LANGUAGE = params['language']
            set_language(self.LANGUAGE)
            # Sauvegarder la langue dans la config utilisateur pour le prochain démarrage / Save language in user config for next startup
            save_user_config({'language': self.LANGUAGE})
    
    def to_dict(self) -> dict:
        """Convertit la configuration en dictionnaire pour la sauvegarde / Convert configuration to dictionary for saving"""
        return {
            'debug_mode': self.DEBUG_MODE,
            'movement_threshold': self.OPERATOR_MOVEMENT_THRESHOLD,
            'cache_validity': self.NODE_POSITION_CACHE_VALIDITY_MS,
            'probe_max_measurements': self.OPERATOR_PROBE_MAX_MEASUREMENTS,
            'probe_analysis_max_points': self.PROBE_ANALYSIS_MAX_POINTS,
            'ui_update_interval': self.UI_UPDATE_INTERVAL,
            'animation_steps': self.OPERATOR_ANIMATION_STEPS,
            'enable_animations': self.ENABLE_ANIMATIONS,
            'language': self.LANGUAGE
        }

class MainWindow:
    """Fenêtre principale de l'application SimPy GUI / Main window for SimPy GUI application"""
    
    def __init__(self, root):
        self.root = root
        self.flow_model = FlowModel()
        self.simulator: FlowSimulator = None
        self.selected_node_type = None  # Type de noeud à ajouter / Node type to add
        self.is_analysis_mode = False  # Flag pour distinguer simulation manuelle vs analyse / Flag to distinguish manual simulation vs analysis
        self.current_filename = None  # Fichier actuellement ouvert / Currently open file
        self.is_initializing = True  # Flag pour bloquer les resize pendant le chargement / Flag to block resize during loading
        
        # Paramètres configurables / Configurable parameters
        self.analysis_timeout = 600  # Timeout en secondes pour l'analyse / Timeout in seconds for analysis
        self.canvas_width = 2000  # Largeur du canvas en pixels / Canvas width in pixels
        self.canvas_height = 2000  # Hauteur du canvas en pixels / Canvas height in pixels
        
        # Configuration globale de l'application (charge et applique la langue automatiquement) / Global app config (loads and applies language automatically)
        self.app_config = AppConfig()
        
        # Paramètres de performance (synchronisés avec app_config) / Performance parameters (synced with app_config)
        self.performance_params = self.app_config.to_dict()
        
        self._create_menu()
        self._create_toolbar()
        self._create_status_bar()
        self._create_main_area()
        self._setup_keyboard_shortcuts()
        
        # Mise à jour initiale / Initial update
        self._update_status()
        
        # Fin du chargement - activer les resize handlers APRÈS que mainloop ait stabilisé le layout
        # End of loading - enable resize handlers AFTER mainloop has stabilized layout
        self.root.after(200, lambda: setattr(self, 'is_initializing', False))
    
    def _create_menu(self):
        """Crée la barre de menu / Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu Fichier / File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=tr('file'), menu=file_menu)
        file_menu.add_command(label=tr('new'), command=self._new_flow)
        file_menu.add_command(label=tr('open') + "...", command=self._open_flow)
        file_menu.add_command(label=tr('import') + "...", command=self._import_flow)
        file_menu.add_command(label=tr('save'), command=self._save_flow)
        file_menu.add_separator()
        file_menu.add_command(label=tr('exit'), command=self.root.quit)
        
        # Menu Édition / Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=tr('edit'), menu=edit_menu)
        edit_menu.add_command(label=tr('delete'), command=self._delete_selected)
        edit_menu.add_separator()
        edit_menu.add_command(label=tr('clear_all'), command=self._clear_all)
        
        # Menu Simulation / Simulation Menu
        sim_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=tr('simulation'), menu=sim_menu)
        sim_menu.add_command(label=tr('start'), command=self._start_simulation)
        sim_menu.add_command(label=tr('pause'), command=self._pause_simulation)
        sim_menu.add_command(label=tr('stop'), command=self._stop_simulation)
        sim_menu.add_separator()
        sim_menu.add_command(label=tr('reset'), command=self._reset_simulation)
        sim_menu.add_separator()
        
        # Menu Paramètres / Settings Menu
        params_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=tr('settings'), menu=params_menu)
        
        # Paramètres généraux / General settings
        params_menu.add_command(label=tr('general_settings'), command=self._configure_general)
        params_menu.add_command(label=tr('canvas_settings'), command=self._configure_canvas)
        params_menu.add_separator()
        # Paramètres des pipettes / Probe settings
        params_menu.add_command(label=tr('probes') + "...", command=self._show_pipettes_settings_dialog)
        params_menu.add_command(label=tr('time_probes') + "...", command=self._show_time_probes_settings_dialog)
        
        # Menu Aide / Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=tr('help'), menu=help_menu)
        help_menu.add_command(label=tr('keyboard_shortcuts'), command=self._show_keyboard_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label=tr('about'), command=self._show_about)
    
    def _create_toolbar(self):
        """Crée la barre d'outils / Create the toolbar"""
        # Créer un conteneur avec boutons de navigation / Create container with navigation buttons
        toolbar_container = ttk.Frame(self.root)
        toolbar_container.pack(side=tk.TOP, fill=tk.X)
        
        # Bouton flèche gauche / Left arrow button
        self.toolbar_scroll_left = ttk.Button(toolbar_container, text="◀", width=2, command=lambda: self._scroll_toolbar(-1))
        self.toolbar_scroll_left.pack(side=tk.LEFT)
        
        # Canvas pour permettre le scroll horizontal / Canvas to allow horizontal scrolling
        self.toolbar_canvas = tk.Canvas(toolbar_container, height=80, highlightthickness=0)
        self.toolbar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bouton flèche droite / Right arrow button
        self.toolbar_scroll_right = ttk.Button(toolbar_container, text="▶", width=2, command=lambda: self._scroll_toolbar(1))
        self.toolbar_scroll_right.pack(side=tk.RIGHT)
        
        # Frame pour les boutons / Frame for buttons
        toolbar = ttk.Frame(self.toolbar_canvas, relief=tk.RAISED, borderwidth=1)
        self.toolbar_canvas.create_window((0, 0), window=toolbar, anchor=tk.NW)
        
        # Mettre à jour la scrollregion quand la toolbar change de taille / Update scrollregion when toolbar changes size
        def configure_scroll_region(event=None):
            self.toolbar_canvas.configure(scrollregion=self.toolbar_canvas.bbox("all"))
        
        toolbar.bind("<Configure>", configure_scroll_region)
        
        # Boutons de mode / Mode buttons
        mode_frame = ttk.LabelFrame(toolbar, text=tr('mode'), padding="5")
        mode_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.mode_var = tk.StringVar(value="select")
        
        ttk.Radiobutton(
            mode_frame, text=tr('select_mode'), variable=self.mode_var,
            value="select", command=self._change_mode
        ).pack(side=tk.LEFT, padx=2)
        
        # Menu pour ajouter des nœuds / Menu to add nodes
        add_node_btn = ttk.Menubutton(mode_frame, text=tr('add_node_menu'))
        add_node_btn.pack(side=tk.LEFT, padx=2)
        
        add_node_menu = tk.Menu(add_node_btn, tearoff=0)
        add_node_btn.config(menu=add_node_menu)
        
        from models.flow_model import NodeType
        add_node_menu.add_command(
            label=tr('source_node'),
            command=lambda: self._set_add_node_type(NodeType.SOURCE)
        )
        
        add_node_menu.add_separator()
        add_node_menu.add_command(
            label=tr('processing_node'),
            command=lambda: self._set_add_node_type(NodeType.CUSTOM)
        )
        add_node_menu.add_separator()
        add_node_menu.add_command(
            label=tr('splitter_node'),
            command=lambda: self._set_add_node_type(NodeType.SPLITTER)
        )
        add_node_menu.add_command(
            label=tr('merger_node'),
            command=lambda: self._set_add_node_type(NodeType.MERGER)
        )
        add_node_menu.add_separator()
        add_node_menu.add_command(
            label=tr('sink_node'),
            command=lambda: self._set_add_node_type(NodeType.SINK)
        )
        
        ttk.Radiobutton(
            mode_frame, text=tr('add_connection'), variable=self.mode_var,
            value="add_connection", command=self._change_mode
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Radiobutton(
            mode_frame, text=tr('add_probe'), variable=self.mode_var,
            value="add_probe", command=self._change_mode
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Radiobutton(
            mode_frame, text=tr('add_time_probe'), variable=self.mode_var,
            value="add_time_probe", command=self._change_mode
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Radiobutton(
            mode_frame, text=tr('add_legend'), variable=self.mode_var,
            value="add_annotation", command=self._change_mode
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Radiobutton(
            mode_frame, text=tr('add_operator'), variable=self.mode_var,
            value="add_operator", command=self._change_mode
        ).pack(side=tk.LEFT, padx=2)
        
        # Bouton pour éditer les items / Button to edit items
        ttk.Button(
            mode_frame, text=tr('edit_items'), command=self._edit_all_item_types
        ).pack(side=tk.LEFT, padx=2)
        
        # Unité de temps / Time unit
        time_frame = ttk.LabelFrame(toolbar, text=tr('time_unit'), padding="5")
        time_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(time_frame, text=tr('display_in')).pack(side=tk.LEFT, padx=5)
        
        self.time_unit_var = tk.StringVar(value=TimeUnit.SECONDS.name)
        time_combo = ttk.Combobox(
            time_frame,
            textvariable=self.time_unit_var,
            values=[unit.name for unit in TimeUnit],
            state="readonly",
            width=15
        )
        time_combo.pack(side=tk.LEFT, padx=5)
        time_combo.bind("<<ComboboxSelected>>", self._change_time_unit)
        
        # Déclencher la mise à jour des labels dans le panneau d'analyse / Trigger label update in analysis panel
        self.time_unit_var.trace_add("write", lambda *args: self._update_analysis_time_unit())
        
        # Boutons de simulation / Simulation buttons
        sim_frame = ttk.LabelFrame(toolbar, text=tr('simulation'), padding="5")
        sim_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.btn_start = ttk.Button(sim_frame, text=tr('start_btn'), command=self._start_simulation)
        self.btn_start.pack(side=tk.LEFT, padx=2)
        
        self.btn_pause = ttk.Button(sim_frame, text=tr('pause_btn'), command=self._pause_simulation, state="disabled")
        self.btn_pause.pack(side=tk.LEFT, padx=2)
        
        self.btn_stop = ttk.Button(sim_frame, text=tr('stop_btn'), command=self._stop_simulation, state="disabled")
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(sim_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        self.btn_edit_analysis = ttk.Button(sim_frame, text=tr('edit_analysis'), command=self._edit_analysis)
        self.btn_edit_analysis.pack(side=tk.LEFT, padx=2)
        
        self.btn_analyze = ttk.Button(sim_frame, text=tr('analyze_btn'), command=self._run_analysis)
        self.btn_analyze.pack(side=tk.LEFT, padx=2)
        
        # Boutons de zoom / Zoom buttons
        zoom_frame = ttk.Frame(toolbar)
        zoom_frame.pack(side=tk.LEFT, padx=15, pady=5)
        
        ttk.Label(zoom_frame, text=tr('zoom')).pack(side=tk.LEFT, padx=5)
        
        self.btn_zoom_out = ttk.Button(zoom_frame, text="➖", command=self._zoom_out, width=3)
        self.btn_zoom_out.pack(side=tk.LEFT, padx=2)
        
        self.btn_zoom_in = ttk.Button(zoom_frame, text="➕", command=self._zoom_in, width=3)
        self.btn_zoom_in.pack(side=tk.LEFT, padx=2)
        
        # Vitesse de simulation / Simulation speed
        speed_frame = ttk.Frame(toolbar)
        speed_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(speed_frame, text=tr('speed')).pack(side=tk.LEFT, padx=5)
        
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = ttk.Scale(
            speed_frame, from_=0.1, to=5.0,
            variable=self.speed_var, orient=tk.HORIZONTAL, length=100
        )
        self.speed_scale.pack(side=tk.LEFT, padx=5)
        
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.pack(side=tk.LEFT, padx=5)
        self.speed_var.trace_add("write", self._update_speed_label)
    
    def _create_main_area(self):
        """Crée la zone principale avec le canvas et le panneau latéral / Create the main area with canvas and side panel"""
        # Conteneur principal avec PanedWindow pour redimensionnement / Main container with PanedWindow for resizing
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas à gauche / Canvas on the left
        canvas_frame = ttk.Frame(main_container)
        main_container.add(canvas_frame, weight=15)  # Poids plus élevé pour canvas / Higher weight for canvas
        
        self.canvas = FlowCanvas(canvas_frame, self.flow_model, self.app_config)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Connecter le callback pour la modification d'opérateurs / Connect callback for operator modification
        self.canvas.on_operator_modified = self._stop_simulation_if_running
        
        # Rate limiting pour les updates - 20 FPS (50ms) pour meilleures performances
        # Réduit de 30 FPS pour diminuer la charge CPU sans impact visible
        # Rate limiting for updates - 20 FPS (50ms) for better performance
        # Reduced from 30 FPS to lower CPU load without visible impact
        self.last_canvas_update_time = 0
        self.min_update_interval = 1.0 / 20.0  # 50ms entre chaque frame (20 FPS) / 50ms between each frame (20 FPS)
        
        # Événements personnalisés / Custom events
        self.canvas.bind("<<NodeDoubleClick>>", self._on_node_double_click)
        self.canvas.bind("<<ConnectionRightClick>>", self._on_connection_right_click)
        self.canvas.bind("<<ConnectionDoubleClick>>", self._on_connection_double_click)
        self.canvas.bind("<<ModeChanged>>", self._on_mode_changed)
        self.canvas.bind("<Button-1>", self._on_canvas_click, add="+")
        
        # Afficher les limites du canvas dès le départ / Display canvas limits from the start
        self._draw_canvas_border()
        
        # Panneau d'information à droite (redimensionnable via PanedWindow) / Info panel on the right (resizable via PanedWindow)
        info_frame = ttk.Frame(main_container, relief=tk.RAISED, borderwidth=2)
        main_container.add(info_frame, weight=1)
        
        ttk.Label(info_frame, text=tr('informations'), font=("Arial", 12, "bold")).pack(pady=10)
        
        # Créer le style pour fond gris AVANT les onglets / Create style for gray background BEFORE tabs
        style = ttk.Style()
        style.configure('Gray.TFrame', background='#f0f0f0')
        
        # Notebook avec onglets / Notebook with tabs
        self.info_notebook = ttk.Notebook(info_frame)
        self.info_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglet 1: Pipettes de mesure / Tab 1: Measurement probes
        graphs_tab = ttk.Frame(self.info_notebook, style='Gray.TFrame')
        self.info_notebook.add(graphs_tab, text=tr('tab_probes'))
        
        from gui.measurement_graphs_panel import MeasurementGraphsPanel
        self.graphs_panel = MeasurementGraphsPanel(graphs_tab, self.flow_model, self.canvas, main_window=self)
        self.graphs_panel.pack(fill=tk.BOTH, expand=True)
        
        # Onglet 2: Loupes (Time Probes) / Tab 2: Time Probes (Magnifying glass)
        time_probes_tab = ttk.Frame(self.info_notebook, style='Gray.TFrame')
        self.info_notebook.add(time_probes_tab, text=tr('tab_time_probes'))
        
        from gui.time_probe_panel import TimeProbePanel
        self.time_probe_panel = TimeProbePanel(time_probes_tab, self.flow_model, main_window=self)
        self.time_probe_panel.pack(fill=tk.BOTH, expand=True)
        
        # Onglet 3: Statistiques Types d'Items / Tab 3: Item Types Statistics
        item_types_stats_tab = ttk.Frame(self.info_notebook, style='Gray.TFrame')
        self.info_notebook.add(item_types_stats_tab, text=tr('tab_item_types'))
        
        from gui.item_types_stats_panel import ItemTypesStatsPanel
        self.item_types_stats_panel = ItemTypesStatsPanel(item_types_stats_tab, self.flow_model, main_window=self)
        self.item_types_stats_panel.pack(fill=tk.BOTH, expand=True)
        
        # Onglet 4: Temps de déplacement (Opérateurs) / Tab 4: Travel time (Operators)
        operator_travel_tab = ttk.Frame(self.info_notebook, style='Gray.TFrame')
        self.info_notebook.add(operator_travel_tab, text=tr('tab_movements'))
        
        from gui.operator_travel_panel import OperatorTravelPanel
        self.operator_travel_panel = OperatorTravelPanel(operator_travel_tab, self.flow_model, main_window=self)
        self.operator_travel_panel.pack(fill=tk.BOTH, expand=True)
        
        # Onglet 5: Analyse / Tab 5: Analysis
        analysis_tab = ttk.Frame(self.info_notebook, style='Gray.TFrame')
        self.info_notebook.add(analysis_tab, text=tr('tab_analysis'))
        
        from gui.analysis_panel import AnalysisPanel
        self.analysis_panel = AnalysisPanel(analysis_tab, self.flow_model, self.time_unit_var, main_window=self)
        self.analysis_panel.pack(fill=tk.BOTH, expand=True)
        self.analysis_panel.update_time_unit_labels()
        
        # Connecter les callbacks pour les pipettes et loupes / Connect callbacks for probes and time probes
        self.canvas.on_probe_added = self._on_probe_added
        self.canvas.on_probe_removed = self._on_probe_removed
        self.canvas.on_add_time_probe_callback = self._add_time_probe
    
    def _scroll_toolbar(self, direction):
        """Fait défiler la toolbar horizontalement / Scroll the toolbar horizontally"""
        # Défilement de 100 pixels / Scroll by 100 pixels
        current_x = self.toolbar_canvas.xview()[0]
        canvas_width = self.toolbar_canvas.winfo_width()
        scrollregion_width = self.toolbar_canvas.bbox("all")[2] if self.toolbar_canvas.bbox("all") else canvas_width
        
        if scrollregion_width > canvas_width:
            scroll_amount = 100 / scrollregion_width
            new_x = current_x + (direction * scroll_amount)
            self.toolbar_canvas.xview_moveto(max(0, min(1, new_x)))
    
    def _draw_canvas_border(self):
        """Dessine la bordure du canvas pour montrer les limites / Draw canvas border to show limits"""
        if hasattr(self, 'canvas'):
            self.canvas.delete("canvas_border")
            self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
            self.canvas.create_rectangle(
                0, 0, self.canvas_width, self.canvas_height,
                outline="red", dash=(10, 5), width=2,
                tags="canvas_border"
            )
    
    def _configure_canvas(self):
        """Ouvre le dialogue de configuration du canvas / Open canvas configuration dialog"""
        from gui.canvas_config_dialog import CanvasConfigDialog
        
        current_width = getattr(self, 'canvas_width', 2000)
        current_height = getattr(self, 'canvas_height', 2000)
        
        dialog = CanvasConfigDialog(self.root, current_width, current_height)
        
        if dialog.result:
            self.canvas_width = dialog.result['width']
            self.canvas_height = dialog.result['height']
            
            # Redessiner la bordure avec les nouvelles dimensions / Redraw border with new dimensions
            self._draw_canvas_border()
            self._update_status()
    
    def _configure_general(self):
        """Ouvre le dialogue de configuration générale / Open general configuration dialog"""
        from gui.general_config_dialog import GeneralConfigDialog
        
        current_timeout = getattr(self, 'analysis_timeout', 600)
        
        dialog = GeneralConfigDialog(self.root, current_timeout, self.performance_params)
        
        if dialog.result:
            self.analysis_timeout = dialog.result['timeout']
            
            # Mettre à jour les paramètres de performance (inclure la langue) / Update performance parameters (including language)
            self.performance_params = {
                'debug_mode': dialog.result['debug_mode'],
                'movement_threshold': dialog.result['movement_threshold'],
                'probe_max_measurements': dialog.result['probe_max_measurements'],
                'probe_analysis_max_points': dialog.result['probe_analysis_max_points'],
                'cache_validity': dialog.result['cache_validity'],
                'ui_update_interval': dialog.result['ui_update_interval'],
                'enable_animations': dialog.result['enable_animations'],
                'animation_steps': dialog.result['animation_steps'],
                'language': dialog.result.get('language', 'fr')
            }
            
            # Appliquer immédiatement les changements à la configuration globale / Apply changes to global config immediately
            self.app_config.update_from_dict(self.performance_params)
            
            # Appliquer immédiatement la langue / Apply language immediately
            set_language(self.performance_params['language'])
            
            # Mettre à jour le titre de la fenêtre avec la nouvelle langue / Update window title with new language
            self.root.title(tr('app_title'))
            
            self._update_status()
    
    def _edit_all_item_types(self):
        """Ouvre un dialogue pour éditer tous les types d'items du graphe / Open dialog to edit all item types of the graph"""
        # Chercher toutes les sources qui ont des types configurés / Find all sources that have configured types
        sources_with_types = [node for node in self.flow_model.nodes.values() 
                             if node.is_source and hasattr(node, 'item_type_config')]
        
        if not sources_with_types:
            messagebox.showinfo(
                tr('information'),
                f"{tr('no_source_configured')}\n\n{tr('add_source_msg')}",
                parent=self.root
            )
            return
        
        # Utiliser la première source comme référence / Use first source as reference
        source = sources_with_types[0]
        
        # Ouvrir le dialogue simplifié (uniquement édition des types, pas de modes) / Open simplified dialog (edit types only, no modes)
        from gui.simple_item_types_editor import SimpleItemTypesEditor
        dialog = SimpleItemTypesEditor(self.root, source.item_type_config)
        
        # Après fermeture, propager les changements à toutes les sources / After closing, propagate changes to all sources
        if dialog.result:
            # Synchroniser tous les types d'items entre les sources / Synchronize all item types between sources
            # Mettre à jour la liste des types tout en conservant / Update type list while keeping
            # le mode de génération et séquence propres à chaque source / generation mode and sequence specific to each source
            for node in sources_with_types:
                node.item_type_config.item_types = source.item_type_config.item_types.copy()
            
            # Rafraîchir les affichages / Refresh displays
            if hasattr(self, 'item_types_stats_panel'):
                self.item_types_stats_panel._update_types_reference_content()
    
    def _create_status_bar(self):
        """Crée la barre de statut / Create the status bar"""
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.status_bar, text=tr('ready'), anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.node_count_label = ttk.Label(self.status_bar, text=f"{tr('nodes')}: 0", anchor=tk.E)
        self.node_count_label.pack(side=tk.RIGHT, padx=10)
        
        self.connection_count_label = ttk.Label(self.status_bar, text=f"{tr('connections')}: 0", anchor=tk.E)
        self.connection_count_label.pack(side=tk.RIGHT, padx=10)

    def _setup_keyboard_shortcuts(self):
        """Configure les raccourcis clavier / Configure keyboard shortcuts"""
        # Ctrl+S : Enregistrer / Ctrl+S : Save
        self.root.bind('<Control-s>', lambda e: self._quick_save())
        self.root.bind('<Control-S>', lambda e: self._quick_save())
        
        # W : Mode Sélection / W : Selection mode
        self.root.bind('w', lambda e: self._shortcut_select_mode())
        self.root.bind('W', lambda e: self._shortcut_select_mode())
        
        # A : Ajouter nœud flux entrant / A : Add incoming flow node
        self.root.bind('a', lambda e: self._set_add_node_type(NodeType.SOURCE))
        self.root.bind('A', lambda e: self._set_add_node_type(NodeType.SOURCE))
        
        # S : Ajouter nœud traitement / S : Add processing node
        self.root.bind('s', lambda e: self._set_add_node_type(NodeType.CUSTOM))
        self.root.bind('S', lambda e: self._set_add_node_type(NodeType.CUSTOM))
        
        # D : Ajouter Nœud de sortie / D : Add exit node
        self.root.bind('d', lambda e: self._set_add_node_type(NodeType.SINK))
        self.root.bind('D', lambda e: self._set_add_node_type(NodeType.SINK))
        
        # X : Ajouter Diviseur / X : Add splitter
        self.root.bind('x', lambda e: self._set_add_node_type(NodeType.SPLITTER))
        self.root.bind('X', lambda e: self._set_add_node_type(NodeType.SPLITTER))
        
        # C : Ajouter Concatenateur / C : Add merger
        self.root.bind('c', lambda e: self._set_add_node_type(NodeType.MERGER))
        self.root.bind('C', lambda e: self._set_add_node_type(NodeType.MERGER))
        
        # E : Ajouter Pipette / E : Add probe
        self.root.bind('e', lambda e: self._shortcut_add_probe())
        self.root.bind('E', lambda e: self._shortcut_add_probe())
        
        # R : Ajouter Loupe / R : Add time probe
        self.root.bind('r', lambda e: self._shortcut_add_time_probe())
        self.root.bind('R', lambda e: self._shortcut_add_time_probe())
        
        # Q : Ajouter Connexion / Q : Add connection
        self.root.bind('q', lambda e: self._shortcut_add_connection())
        self.root.bind('Q', lambda e: self._shortcut_add_connection())
        
        # Z : Ajouter Opérateur / Z : Add operator
        self.root.bind('z', lambda e: self._set_add_operator_mode())
        self.root.bind('Z', lambda e: self._set_add_operator_mode())
        
        # Espace : Démarrer/Pause simulation / Space : Start/Pause simulation
        self.root.bind('<space>', lambda e: self._shortcut_toggle_simulation())
        
        # V : Arrêter simulation / V : Stop simulation
        self.root.bind('v', lambda e: self._stop_simulation())
        self.root.bind('V', lambda e: self._stop_simulation())
    
    def _shortcut_select_mode(self):
        """Raccourci pour passer en mode sélection / Shortcut to switch to selection mode"""
        self.mode_var.set("select")
        self._change_mode()
    
    def _shortcut_add_probe(self):
        """Raccourci pour passer en mode ajout pipette / Shortcut to switch to add probe mode"""
        self.mode_var.set("add_probe")
        self._change_mode()
    
    def _shortcut_add_time_probe(self):
        """Raccourci pour passer en mode ajout loupe / Shortcut to switch to add time probe mode"""
        self.mode_var.set("add_time_probe")
        self._change_mode()
    
    def _shortcut_add_connection(self):
        """Raccourci pour passer en mode ajout connexion / Shortcut to switch to add connection mode"""
        self.mode_var.set("add_connection")
        self._change_mode()
    
    def _set_add_operator_mode(self):
        """Raccourci pour passer en mode ajout opérateur / Shortcut to switch to add operator mode"""
        self.mode_var.set("add_operator")
        self._change_mode()
    
    def _shortcut_toggle_simulation(self):
        """Raccourci pour démarrer/pause la simulation / Shortcut to start/pause simulation"""
        if not self.simulator:
            # Pas de simulateur, démarrer / No simulator, start
            self._start_simulation()
        elif hasattr(self.simulator, 'is_paused') and self.simulator.is_paused:
            # En pause, reprendre / Paused, resume
            self._start_simulation()
        elif self.simulator.is_running:
            # En cours, mettre en pause / Running, pause
            self._pause_simulation()
        else:
            # Arrêté, redémarrer / Stopped, restart
            self._start_simulation()
    
    def _quick_save(self):
        """Enregistrement rapide (Ctrl+S) / Quick save (Ctrl+S)"""
        if self.current_filename:
            # Sauvegarder dans le fichier actuel / Save to current file
            self._save_to_file(self.current_filename)
            # Afficher un message de confirmation dans la barre de statut / Show confirmation message in status bar
            self.status_label.config(text=f"✓ Enregistré : {self.current_filename}")
            self.root.after(3000, lambda: self._update_status())  # Revenir au statut normal après 3s / Return to normal status after 3s
        else:
            # Pas de fichier actuel, demander où enregistrer / No current file, ask where to save
            self._save_flow()
    
    def _on_probe_added(self, probe):
        """Appelé quand une pipette est ajoutée / Called when a probe is added"""
        self.graphs_panel.update_probe_list()
        self.graphs_panel.refresh_graphs()
        self._update_status()
    
    def _on_probe_removed(self, probe_id):
        """Appelé quand une pipette est supprimée / Called when a probe is removed"""
        self.graphs_panel.update_probe_list()
        self.graphs_panel.refresh_graphs()
        self._update_status()
    
    def _add_time_probe(self, node_id=None):
        """Ouvre un dialogue pour ajouter une loupe de temps à un nœud / Open dialog to add a time probe to a node"""
        # Si pas de node_id fourni, on est en mode sélection / If no node_id provided, we're in selection mode
        if not node_id:
            return
        
        from gui.time_probe_config_dialog import TimeProbeConfigDialog
        
        def on_save(time_probe):
            """Callback appelé quand la loupe est sauvegardée / Callback called when time probe is saved"""
            self.time_probe_panel.refresh_all_graphs()
            self.canvas.redraw_all()  # Redessiner pour afficher l'icône loupe / Redraw to display time probe icon
            self._update_status()
            # Revenir en mode sélection après ajout / Return to selection mode after adding
            self.mode_var.set("select")
            self._change_mode()
        
        dialog = TimeProbeConfigDialog(
            self.root,
            self.flow_model,
            node_id,
            time_probe=None,
            on_save=on_save
        )
        self.root.wait_window(dialog)
    
    def _on_time_probe_added(self, time_probe):
        """Appelé quand une loupe de temps est ajoutée / Called when a time probe is added"""
        self.time_probe_panel.refresh_all_graphs()
        if hasattr(self, 'operator_travel_panel'):
            self.operator_travel_panel.refresh_all_graphs()
        self.canvas.redraw_all()  # Redessiner pour afficher l'icône loupe / Redraw to display time probe icon
        self._update_status()
    
    def _on_time_probe_removed(self, probe_id):
        """Appelé quand une loupe de temps est supprimée / Called when a time probe is removed"""
        self.time_probe_panel.refresh_all_graphs()
        self.canvas.redraw_all()  # Redessiner pour retirer l'icône loupe / Redraw to remove time probe icon
        self._update_status()
    
    def _change_mode(self):
        """Change le mode d'édition du canvas / Change the canvas editing mode"""
        mode = self.mode_var.get()
        self.canvas.set_mode(mode)
        self._update_status()
    
    def _on_mode_changed(self, event=None):
        """Appelé quand le mode change depuis le canvas (ex: après ajout pipette) / Called when mode changes from canvas (e.g.: after adding probe)"""
        self.mode_var.set(self.canvas.mode)
        self._update_status()
    
    def _set_add_node_type(self, node_type):
        """Définit le type de nœud à ajouter et passe en mode ajout / Set node type to add and switch to add mode"""
        from models.flow_model import NodeType
        self.selected_node_type = node_type
        self.mode_var.set("add_node")
        self.canvas.set_mode("add_node")
        
        # Déterminer le label détaillé pour le statut / Determine detailed label for status
        node_type_labels = {
            NodeType.SOURCE: tr('node_type_source'),
            NodeType.CUSTOM: tr('node_type_processing'),
            NodeType.SINK: tr('node_type_sink'),
            NodeType.SPLITTER: tr('node_type_splitter'),
            NodeType.MERGER: tr('node_type_merger')
        }
        node_label = node_type_labels.get(node_type, tr('node'))
        self.status_label.config(text=tr('mode_add_node_type').format(node_type=node_label))
        # Mise à jour du comptage après un délai pour ne pas écraser le message / Update count after delay to avoid overwriting message
        self.root.after(10, self._update_node_counts)
    
    def _on_canvas_click(self, event):
        """Gestion du clic sur le canvas pour ajouter un nœud / Handle canvas click to add a node"""
        if self.canvas.mode == "add_node" and self.selected_node_type:
            # Déterminer le nom par défaut / Determine default name
            from models.flow_model import NodeType
            if self.selected_node_type == NodeType.SOURCE:
                name = tr('default_name_source')
            elif self.selected_node_type == NodeType.SINK:
                name = tr('default_name_sink')
            elif self.selected_node_type == NodeType.SPLITTER:
                name = tr('default_name_splitter')
            elif self.selected_node_type == NodeType.MERGER:
                name = tr('default_name_merger')
            else:
                name = tr('default_name_processing')
            
            # Convertir les coordonnées de la fenêtre en coordonnées du canvas / Convert window coordinates to canvas coordinates
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Le canvas gère l'ajout, mais on doit passer le bon type / Canvas handles adding, but we need to pass correct type
            self.canvas.add_node_at_position(canvas_x, canvas_y, self.selected_node_type, name)
            self._update_status()
    
    def _change_time_unit(self, event=None):
        """Change l'unité de temps d'affichage / Change display time unit"""
        new_unit = TimeUnit[self.time_unit_var.get()]
        self.flow_model.set_time_unit(new_unit)
        self.canvas.redraw_all()
        self._update_status()
    
    def _edit_analysis(self):
        """Ouvre l'onglet Analyse pour éditer les paramètres / Open Analysis tab to edit parameters"""
        # Sélectionner l'onglet Analyse (index 4) / Select Analysis tab (index 4)
        self.info_notebook.select(4)
    
    def _run_analysis(self):
        """Lance l'analyse depuis le panneau d'analyse / Launch analysis from analysis panel"""
        # Sélectionner l'onglet Analyse et lancer l'analyse / Select Analysis tab and launch analysis
        self.info_notebook.select(2)
        if hasattr(self.analysis_panel, '_run_analysis'):
            self.analysis_panel._run_analysis()
    
    def _update_analysis_time_unit(self):
        """Met à jour les labels du panneau d'analyse quand l'unité change / Update analysis panel labels when unit changes"""
        if hasattr(self, 'analysis_panel'):
            self.analysis_panel.update_time_unit_labels()
    
    def _on_node_double_click(self, event=None):
        """Ouvre le dialogue de configuration du nœud / Open node configuration dialog"""
        if self.canvas.selected_node_id:
            node = self.flow_model.get_node(self.canvas.selected_node_id)
            if node:
                from gui.node_config_dialog import NodeConfigDialog
                
                def on_node_save(saved_node):
                    """Callback après sauvegarde du nœud / Callback after node save"""
                    self.canvas.redraw_node(saved_node)
                    
                    # Si c'est une source, rebuild le cache des couleurs d'items / If it's a source, rebuild item colors cache
                    if saved_node.is_source:
                        self.canvas._rebuild_item_type_colors_cache()
                    
                    # Redessiner toutes les connexions liées à ce nœud / Redraw all connections linked to this node
                    for connection in self.flow_model.connections.values():
                        if connection.source_id == saved_node.node_id or connection.target_id == saved_node.node_id:
                            self.canvas.redraw_connection(connection)
                    
                    # Rafraîchir le panneau des loupes / Refresh time probe panel
                    if hasattr(self, 'time_probe_panel'):
                        self.time_probe_panel.refresh_all_graphs()
                    if hasattr(self, 'operator_travel_panel'):
                        self.operator_travel_panel.refresh_all_graphs()
                    
                    # Arrêter la simulation si elle est en cours / Stop simulation if running
                    self._stop_simulation_if_running()
                
                dialog = NodeConfigDialog(
                    self.root, node, self.flow_model.current_time_unit,
                    flow_model=self.flow_model,
                    on_save_callback=on_node_save
                )
    
    def _on_connection_right_click(self, event=None):
        """Ouvre le dialogue de configuration de la connexion / Open connection configuration dialog"""
        if hasattr(self.canvas, 'selected_connection_id') and self.canvas.selected_connection_id:
            connection = self.flow_model.get_connection(self.canvas.selected_connection_id)
            if connection:
                from gui.connection_config_dialog import ConnectionConfigDialog
                dialog = ConnectionConfigDialog(
                    self.root, connection, self.flow_model,
                    on_save_callback=self._on_connection_config_saved
                )
    
    def _delete_selected(self):
        """Supprime l'élément sélectionné / Delete selected element"""
        self.canvas.delete_selected_node()
        self._update_status()
        # Arrêter la simulation si elle est en cours / Stop simulation if running
        self._stop_simulation_if_running()
    
    def _delete_connection(self, connection_id: str):
        """Supprime une connexion / Delete a connection"""
        # Supprimer les objets canvas de la connexion / Delete canvas objects of the connection
        if connection_id in self.canvas.connection_canvas_objects:
            for obj in self.canvas.connection_canvas_objects[connection_id].values():
                if obj:
                    self.canvas.delete(obj)
            del self.canvas.connection_canvas_objects[connection_id]
        # Supprimer aussi par tag / Also delete by tag
        self.canvas.delete(connection_id)
        # Supprimer du modèle / Delete from model
        self.flow_model.remove_connection(connection_id)
        self._update_status()
        # Arrêter la simulation si elle est en cours / Stop simulation if running
        self._stop_simulation_if_running()
    
    def _on_connection_double_click(self, event):
        """Gère le double-clic sur une connexion / Handle double-click on a connection"""
        # Même comportement que le clic droit / Same behavior as right-click
        self._on_connection_right_click(event)
    
    def _on_connection_config_saved(self):
        """Appelé après sauvegarde de la configuration de connexion / Called after connection configuration save"""
        # Redessiner uniquement la connexion sélectionnée au lieu de tout redessiner / Redraw only selected connection instead of all
        if hasattr(self.canvas, 'selected_connection_id') and self.canvas.selected_connection_id:
            connection = self.flow_model.get_connection(self.canvas.selected_connection_id)
            if connection:
                self.canvas.redraw_connection(connection)
        
        # Arrêter la simulation si elle est en cours / Stop simulation if running
        self._stop_simulation_if_running()
        
        # Note: pas besoin de redraw_probes() ici, les pipettes n'ont pas changé / Note: no need for redraw_probes() here, probes haven't changed
        if hasattr(self, 'graphs_panel'):
            self.graphs_panel.update_probe_list()
            self.graphs_panel.refresh_graphs()
        self._update_status()
    
    def _clear_all(self):
        """Efface tout le flux / Clear entire flow"""
        if messagebox.askyesno(tr('confirm'), tr('confirm_clear_all')):
            self.flow_model.nodes.clear()
            self.flow_model.connections.clear()
            self.flow_model.probes.clear()  # Effacer les pipettes / Clear probes
            if hasattr(self.flow_model, 'time_probes'):
                self.flow_model.time_probes.clear()  # Effacer les loupes / Clear time probes
            if hasattr(self.flow_model, 'annotations'):
                self.flow_model.annotations.clear()  # Effacer les annotations / Clear annotations
            # Réinitialiser les compteurs d'ID à 0 (comme dans __init__) / Reset ID counters to 0 (as in __init__)
            self.flow_model._next_node_id = 0
            self.flow_model._next_connection_id = 0
            self.flow_model._next_probe_id = 0
            self.flow_model._next_time_probe_id = 0
            if hasattr(self.flow_model, '_next_annotation_id'):
                self.flow_model._next_annotation_id = 0
            # Effacer les objets canvas / Clear canvas objects
            self.canvas.delete("all")
            self.canvas.node_canvas_objects.clear()
            self.canvas.connection_canvas_objects.clear()
            self.canvas.probe_canvas_objects.clear()
            self.canvas.animated_items.clear()
            # Réinitialiser le zoom / Reset zoom
            self.canvas.zoom_level = 1.0
            # Redessiner (canvas vide maintenant) / Redraw (canvas is now empty)
            self.canvas.redraw_all()
            # Redessiner la bordure du canvas / Redraw canvas border
            self._draw_canvas_border()
            # Mettre à jour les panneaux / Update panels
            if hasattr(self, 'graphs_panel'):
                self.graphs_panel.update_probe_list()
                self.graphs_panel.refresh_graphs()
            if hasattr(self, 'time_probe_panel'):
                self.time_probe_panel.update_probe_list()
                self.time_probe_panel.refresh_all_graphs()
            if hasattr(self, 'operator_travel_panel'):
                self.operator_travel_panel.refresh_all_graphs()
            self._update_status()
    
    def _new_flow(self):
        """Crée un nouveau flux / Create a new flow"""
        if messagebox.askyesno(tr('confirm'), tr('confirm_new_flow')):
            self._clear_all()
            self.current_filename = None  # Réinitialiser le fichier actuel / Reset current file
    
    def _open_flow(self):
        """Ouvre un flux existant / Open an existing flow"""
        from tkinter import filedialog
        import pickle
        
        filename = filedialog.askopenfilename(
            filetypes=[("SimPy Flow", "*.simpy"), ("Tous les fichiers", "*.*")],
            title="Ouvrir un flux"
        )
        
        if filename:
            try:
                # ========================================
                # PHASE 1: TOUT EFFACER AVANT DE CHARGER
                # PHASE 1: CLEAR EVERYTHING BEFORE LOADING
                # ========================================
                
                if self.app_config.DEBUG_MODE:
                    print("[LOAD] Phase 1: Nettoyage complet avant chargement...")
                
                # 1. Effacer tous les graphiques et données des panneaux d'information / 1. Clear all graphs and data from info panels
                if hasattr(self, 'graphs_panel'):
                    self.graphs_panel.clear_all_graphs()
                
                if hasattr(self, 'time_probe_panel'):
                    self.time_probe_panel.clear_all_graphs()
                
                if hasattr(self, 'operator_travel_panel'):
                    # Effacer les graphiques des opérateurs si le panneau a une méthode clear / Clear operator graphs if panel has clear method
                    if hasattr(self.operator_travel_panel, 'clear_all_graphs'):
                        self.operator_travel_panel.clear_all_graphs()
                
                if hasattr(self, 'analysis_panel'):
                    self.analysis_panel.clear_analysis_results()
                
                # Effacer les données et graphiques des types d'items / Clear item types data and graphs
                if hasattr(self, 'item_types_stats_panel'):
                    self.item_types_stats_panel.clear_data()
                
                # 2. Effacer complètement le canvas et tous les éléments graphiques / 2. Completely clear canvas and all graphic elements
                self.canvas.delete("all")
                self.canvas.node_canvas_objects.clear()
                self.canvas.connection_canvas_objects.clear()
                self.canvas.probe_canvas_objects.clear()
                self.canvas.annotation_canvas_objects.clear()
                self.canvas.animated_items.clear()
                if hasattr(self.canvas, 'operator_canvas_objects'):
                    self.canvas.operator_canvas_objects.clear()
                if hasattr(self.canvas, 'operator_animations'):
                    self.canvas.operator_animations.clear()
                
                # 3. Effacer toutes les données du modèle / 3. Clear all model data
                self.flow_model.nodes.clear()
                self.flow_model.connections.clear()
                self.flow_model.probes.clear()
                
                if hasattr(self.flow_model, 'time_probes'):
                    self.flow_model.time_probes.clear()
                
                if hasattr(self.flow_model, 'annotations'):
                    self.flow_model.annotations.clear()
                
                if hasattr(self.flow_model, 'operators'):
                    self.flow_model.operators.clear()
                
                # 4. Réinitialiser les compteurs d'ID / 4. Reset ID counters
                self.flow_model._next_node_id = 0
                self.flow_model._next_connection_id = 0
                self.flow_model._next_probe_id = 0
                self.flow_model._next_time_probe_id = 0
                if hasattr(self.flow_model, '_next_annotation_id'):
                    self.flow_model._next_annotation_id = 0
                if hasattr(self.flow_model, '_next_operator_id'):
                    self.flow_model._next_operator_id = 0
                
                # 5. Réinitialiser le zoom / 5. Reset zoom
                self.canvas.zoom_level = 1.0
                
                if self.app_config.DEBUG_MODE:
                    print("[LOAD] Phase 1: Nettoyage terminé")
                
                # ========================================
                # PHASE 2: CHARGER LE NOUVEAU FICHIER
                # PHASE 2: LOAD THE NEW FILE
                # ========================================
                
                if self.app_config.DEBUG_MODE:
                    print(f"[LOAD] Phase 2: Chargement du fichier {filename}...")
                
                # Lire le fichier / Read file
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                
                # Restaurer l'unité de temps / Restore time unit
                if 'time_unit' in data:
                    self.flow_model.current_time_unit = TimeUnit[data['time_unit']]
                    self.time_unit_var.set(data['time_unit'])
                
                # Restaurer les nœuds / Restore nodes
                from models.flow_model import FlowNode, NodeType, SyncMode, SourceMode
                if self.app_config.DEBUG_MODE:
                    print(f"[LOAD] Chargement de {len(data['nodes'])} nœuds")
                for node_id, node_data in data['nodes'].items():
                    # Migration des anciens types de sources vers le nouveau système / Migration from old source types to new system
                    node_type_str = node_data['node_type']
                    source_mode = None
                    
                    # Convertir les anciens types SOURCE_* vers SOURCE avec source_mode / Convert old SOURCE_* types to SOURCE with source_mode
                    if node_type_str == 'SOURCE_CONSTANT':
                        node_type_str = 'SOURCE'
                        source_mode = SourceMode.CONSTANT
                    elif node_type_str == 'SOURCE_NORMAL':
                        node_type_str = 'SOURCE'
                        source_mode = SourceMode.NORMAL
                    elif node_type_str == 'SOURCE_POISSON':
                        node_type_str = 'SOURCE'
                        source_mode = SourceMode.POISSON
                    elif node_type_str == 'SOURCE_EXPONENTIAL':
                        node_type_str = 'SOURCE'
                        source_mode = SourceMode.EXPONENTIAL
                    
                    node_type = NodeType[node_type_str]
                    node = FlowNode(
                        node_id,
                        node_type,
                        node_data['name'],
                        node_data['x'],
                        node_data['y']
                    )
                    
                    # Appliquer le source_mode si c'était un ancien type source / Apply source_mode if it was an old source type
                    if source_mode is not None:
                        node.source_mode = source_mode
                    
                    node.processing_time_cs = node_data['processing_time_cs']
                    node.generation_interval_cs = node_data['generation_interval_cs']
                    
                    # Migrer generation_std_dev : ancien format (secondes) → nouveau format (centisecondes)
                    # Heuristique : si < 10, c'est probablement en secondes (ancien format)
                    # Migrate generation_std_dev : old format (seconds) → new format (centiseconds)
                    # Heuristic : if < 10, probably in seconds (old format)
                    generation_std_dev = node_data['generation_std_dev']
                    if generation_std_dev < 10.0:
                        # Ancien format : convertir secondes → centisecondes / Old format : convert seconds → centiseconds
                        generation_std_dev *= 100.0
                    node.generation_std_dev = generation_std_dev
                    
                    node.generation_lambda = node_data['generation_lambda']
                    node.generation_skewness = node_data.get('generation_skewness', 0.0)
                    node.max_items_to_generate = node_data['max_items_to_generate']
                    node.batch_size = node_data['batch_size']
                    node.sync_mode = SyncMode[node_data['sync_mode']]
                    node.required_units = node_data['required_units']
                    
                    # Restaurer la configuration de sortie legacy / Restore legacy output configuration
                    node.legacy_output_quantity = node_data.get('legacy_output_quantity', 1)
                    node.legacy_output_type = node_data.get('legacy_output_type', '')
                    
                    # Restaurer l'ensemble de combinaisons (backward compatibility avec recipe_book) / Restore combination set (backward compatibility with recipe_book)
                    if 'combination_set' in node_data or 'recipe_book' in node_data:
                        from models.combination import CombinationSet
                        data_key = 'combination_set' if 'combination_set' in node_data else 'recipe_book'
                        node.combination_set = CombinationSet.from_dict(node_data[data_key])
                    
                    # Restaurer le mode de combinaison / Restore combination mode
                    node.use_combinations = node_data.get('use_combinations', False)
                    
                    # NE PAS restaurer directement les listes de connexions ici / DO NOT restore connection lists directly here
                    # Elles seront reconstruites lors de l'ajout des connexions / They will be rebuilt when adding connections
                    if self.app_config.DEBUG_MODE:
                        print(f"[LOAD]   Nœud {node_id} ({node_data['name']}): inputs={node_data['input_connections']}, outputs={node_data['output_connections']}")
                    node.input_connections = []
                    node.output_connections = []
                    node.output_multiplier = node_data.get('output_multiplier', 1)
                    
                    # Restaurer le mode de traitement, l'écart-type et l'asymétrie / Restore processing mode, std dev and skewness
                    if 'processing_time_mode' in node_data:
                        from models.flow_model import ProcessingTimeMode
                        node.processing_time_mode = ProcessingTimeMode[node_data['processing_time_mode']]
                    if 'processing_time_std_dev_cs' in node_data:
                        node.processing_time_std_dev_cs = node_data['processing_time_std_dev_cs']
                    if 'processing_time_skewness' in node_data:
                        node.processing_time_skewness = node_data['processing_time_skewness']
                    
                    # Restaurer le mode source (utilise SourceMode déjà importé au début) / Restore source mode (uses SourceMode already imported at start)
                    if 'source_mode' in node_data:
                        node.source_mode = SourceMode[node_data['source_mode']]
                    
                    # Restaurer les paramètres du splitter / Restore splitter parameters
                    if 'splitter_mode' in node_data:
                        from models.flow_model import SplitterMode
                        node.splitter_mode = SplitterMode[node_data['splitter_mode']]
                    if 'first_available_mode' in node_data:
                        from models.flow_model import FirstAvailableMode
                        node.first_available_mode = FirstAvailableMode[node_data['first_available_mode']]
                    
                    # Restaurer la priorité pour FIRST_AVAILABLE (nœuds de traitement) / Restore priority for FIRST_AVAILABLE (processing nodes)
                    if 'first_available_priority' in node_data:
                        from models.flow_model import FirstAvailablePriority
                        node.first_available_priority = FirstAvailablePriority[node_data['first_available_priority']]
                    
                    # Restaurer la configuration des types d'items (pour sources) / Restore item type configuration (for sources)
                    if 'item_type_config' in node_data:
                        from models.item_type import ItemTypeConfig
                        node.item_type_config = ItemTypeConfig.from_dict(node_data['item_type_config'])
                    
                    # Restaurer la configuration de traitement par type / Restore processing configuration by type
                    if 'processing_config' in node_data:
                        from models.item_type import ProcessingConfig
                        node.processing_config = ProcessingConfig.from_dict(node_data['processing_config'])
                    
                    self.flow_model.nodes[node_id] = node
                
                # Restaurer les connexions avec add_connection pour maintenir la cohérence / Restore connections with add_connection to maintain consistency
                from models.flow_model import Connection
                if self.app_config.DEBUG_MODE:
                    print(f"[LOAD] Chargement de {len(data['connections'])} connexions")
                for conn_id, conn_data in data['connections'].items():
                    if self.app_config.DEBUG_MODE:
                        print(f"[LOAD]   Connexion {conn_id}: {conn_data['source_id']} → {conn_data['target_id']}")
                    conn = Connection(
                        conn_id,
                        conn_data['source_id'],
                        conn_data['target_id']
                    )
                    conn.buffer_capacity = conn_data['buffer_capacity']
                    conn.show_buffer = conn_data['show_buffer']
                    if 'buffer_visual_size' in conn_data:
                        conn.buffer_visual_size = conn_data['buffer_visual_size']
                    if 'initial_buffer_count' in conn_data:
                        conn.initial_buffer_count = conn_data['initial_buffer_count']
                        # Afficher aussi les conditions initiales immédiatement / Also display initial conditions immediately
                        conn.current_buffer_count = conn_data['initial_buffer_count']
                    # Utiliser add_connection pour maintenir la cohérence bidirectionnelle / Use add_connection to maintain bidirectional consistency
                    self.flow_model.add_connection(conn)
                
                # Vérifier la cohérence après chargement / Verify consistency after loading
                if self.app_config.DEBUG_MODE:
                    print(f"[LOAD] Vérification de la cohérence...")
                for node_id, node in self.flow_model.nodes.items():
                    if self.app_config.DEBUG_MODE:
                        print(f"[LOAD]   {node_id}: inputs={node.input_connections}, outputs={node.output_connections}")
                
                # Restaurer les pipettes AVANT de calculer les compteurs / Restore probes BEFORE calculating counters
                if 'probes' in data:
                    from models.measurement_probe import MeasurementProbe
                    
                    for probe_id, probe_data in data['probes'].items():
                        probe = MeasurementProbe(
                            probe_id,
                            probe_data['name'],
                            probe_data['connection_id'],
                            measure_mode=probe_data.get('measure_mode', 'buffer'),
                            max_points=self.app_config.PROBE_ANALYSIS_MAX_POINTS
                        )
                        probe.x = probe_data['x']
                        probe.y = probe_data['y']
                        probe.color = probe_data['color']
                        probe.visible = probe_data.get('visible', True)
                        self.flow_model.probes[probe_id] = probe
                
                # Restaurer les loupes de temps / Restore time probes
                if 'time_probes' in data:
                    from models.time_probe import TimeProbe, TimeProbeType
                    
                    for probe_id, probe_data in data['time_probes'].items():
                        # Migration : INTERARRIVAL et INTERDEPARTURE → INTER_EVENTS / Migration : INTERARRIVAL and INTERDEPARTURE → INTER_EVENTS
                        probe_type_name = probe_data['probe_type']
                        if probe_type_name in ['INTERARRIVAL', 'INTERDEPARTURE']:
                            probe_type_name = 'INTER_EVENTS'
                        
                        probe_type = TimeProbeType[probe_type_name]
                        time_probe = TimeProbe(
                            probe_id,
                            probe_data['name'],
                            probe_data['node_id'],
                            probe_type
                        )
                        time_probe.color = probe_data['color']
                        time_probe.visible = probe_data.get('visible', True)
                        self.flow_model.time_probes[probe_id] = time_probe
                
                # Restaurer les annotations / Restore annotations
                if 'annotations' in data:
                    from models.annotation import Annotation
                    
                    for annotation_id, annotation_data in data['annotations'].items():
                        annotation = Annotation.from_dict(annotation_data)
                        self.flow_model.annotations[annotation_id] = annotation
                
                # Restaurer les opérateurs et tracker les suppressions / Restore operators and track deletions
                operators_to_remove = []  # Définir au niveau de la fonction pour être accessible plus tard / Define at function level to be accessible later
                if 'operators' in data:
                    from models.operator import Operator
                    
                    for operator_id, operator_data in data['operators'].items():
                        operator = Operator.from_dict(operator_data)
                        
                        # Vérifier que toutes les machines assignées existent / Verify all assigned machines exist
                        valid_machines = []
                        invalid_machines = []
                        for machine_id in operator.assigned_machines:
                            if machine_id in self.flow_model.nodes:
                                valid_machines.append(machine_id)
                            else:
                                invalid_machines.append(machine_id)
                        
                        # Si l'opérateur a des machines invalides, le nettoyer ou le supprimer / If operator has invalid machines, clean or delete it
                        if invalid_machines:
                            if self.app_config.DEBUG_MODE:
                                print(f"[LOAD] ⚠️ Opérateur {operator_id} fait référence à des nœuds inexistants: {invalid_machines}")
                            
                            if valid_machines:
                                # Il reste des machines valides, on garde l'opérateur avec les machines valides / Valid machines remain, keep operator with valid machines
                                operator.assigned_machines = valid_machines
                                if self.app_config.DEBUG_MODE:
                                    print(f"[LOAD]   → Opérateur conservé avec machines valides: {valid_machines}")
                                self.flow_model.operators[operator_id] = operator
                            else:
                                # Aucune machine valide, supprimer l'opérateur / No valid machine, delete operator
                                operators_to_remove.append(operator_id)
                                if self.app_config.DEBUG_MODE:
                                    print(f"[LOAD]   → Opérateur supprimé (aucune machine valide)")
                        else:
                            # Toutes les machines sont valides / All machines are valid
                            self.flow_model.operators[operator_id] = operator
                    
                    if operators_to_remove and self.app_config.DEBUG_MODE:
                        print(f"[LOAD] {len(operators_to_remove)} opérateur(s) supprimé(s) car invalide(s)")
                    elif 'operators' in data and self.app_config.DEBUG_MODE:
                        print(f"[LOAD] {len(self.flow_model.operators)} opérateur(s) chargé(s)")
                
                # CRITIQUE : Mettre à jour les compteurs d'ID pour éviter les collisions
                # Ceci doit être fait APRÈS le chargement des pipettes et loupes
                # CRITICAL : Update ID counters to avoid collisions
                # This must be done AFTER loading probes and time probes
                max_node_id = 0
                max_conn_id = 0
                max_probe_id = 0
                max_time_probe_id = 0
                
                for node_id in self.flow_model.nodes.keys():
                    if node_id.startswith('node_'):
                        try:
                            num = int(node_id.split('_')[1])
                            max_node_id = max(max_node_id, num)
                        except (IndexError, ValueError):
                            pass
                
                for conn_id in self.flow_model.connections.keys():
                    if conn_id.startswith('conn_'):
                        try:
                            num = int(conn_id.split('_')[1])
                            max_conn_id = max(max_conn_id, num)
                        except (IndexError, ValueError):
                            pass
                
                for probe_id in self.flow_model.probes.keys():
                    if probe_id.startswith('probe_'):
                        try:
                            num = int(probe_id.split('_')[1])
                            max_probe_id = max(max_probe_id, num)
                        except (IndexError, ValueError):
                            pass
                
                for time_probe_id in self.flow_model.time_probes.keys():
                    if time_probe_id.startswith('time_probe_'):
                        try:
                            num = int(time_probe_id.split('_')[2])
                            max_time_probe_id = max(max_time_probe_id, num)
                        except (IndexError, ValueError):
                            pass
                
                max_annotation_id = 0
                if hasattr(self.flow_model, 'annotations'):
                    for annotation_id in self.flow_model.annotations.keys():
                        if annotation_id.startswith('annotation_'):
                            try:
                                num = int(annotation_id.split('_')[1])
                                max_annotation_id = max(max_annotation_id, num)
                            except (IndexError, ValueError):
                                pass
                
                max_operator_id = 0
                if hasattr(self.flow_model, 'operators'):
                    for operator_id in self.flow_model.operators.keys():
                        if operator_id.startswith('op_'):
                            try:
                                num = int(operator_id.split('_')[1])
                                max_operator_id = max(max_operator_id, num)
                            except (IndexError, ValueError):
                                pass
                
                # Incrémenter de 1 pour le prochain ID / Increment by 1 for next ID
                self.flow_model._next_node_id = max_node_id + 1
                self.flow_model._next_connection_id = max_conn_id + 1
                self.flow_model._next_probe_id = max_probe_id + 1
                self.flow_model._next_time_probe_id = max_time_probe_id + 1
                if hasattr(self.flow_model, '_next_annotation_id'):
                    self.flow_model._next_annotation_id = max_annotation_id + 1
                if hasattr(self.flow_model, '_next_operator_id'):
                    self.flow_model._next_operator_id = max_operator_id + 1
                
                if self.app_config.DEBUG_MODE:
                    print(f"[LOAD] Compteurs mis à jour: next_node_id={self.flow_model._next_node_id}, next_conn_id={self.flow_model._next_connection_id}, next_probe_id={self.flow_model._next_probe_id}, next_time_probe_id={self.flow_model._next_time_probe_id}, next_annotation_id={getattr(self.flow_model, '_next_annotation_id', 0)}")
                
                # ========================================
                # PHASE 2.5: RESTAURER PARAMÈTRES CANVAS
                # PHASE 2.5: RESTORE CANVAS PARAMETERS
                # ========================================
                
                # Restaurer les paramètres généraux AVANT la validation des positions / Restore general parameters BEFORE position validation
                if 'general_params' in data:
                    params = data['general_params']
                    max_speed = params.get('max_speed', 5.0)
                    self.analysis_timeout = params.get('analysis_timeout', 600)
                    self.canvas_width = params.get('canvas_width', 2000)
                    self.canvas_height = params.get('canvas_height', 2000)
                    # Mettre à jour le scale de vitesse / Update speed scale
                    if hasattr(self, 'speed_scale'):
                        self.speed_scale.config(to=max_speed)
                    # Mettre à jour la taille du canvas / Update canvas size
                    if hasattr(self, 'canvas'):
                        self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
                
                # ========================================
                # PHASE 2.6: VALIDATION ET REPOSITIONNEMENT
                # PHASE 2.6: VALIDATION AND REPOSITIONING
                # ========================================
                
                if self.app_config.DEBUG_MODE:
                    print("[LOAD] Phase 2.6: Validation des positions...")
                
                # Calculer la bounding box de tous les éléments / Calculate bounding box of all elements
                min_x = float('inf')
                min_y = float('inf')
                max_x = float('-inf')
                max_y = float('-inf')
                
                has_elements = False
                
                # Vérifier les nœuds / Check nodes
                for node in self.flow_model.nodes.values():
                    has_elements = True
                    min_x = min(min_x, node.x)
                    min_y = min(min_y, node.y)
                    max_x = max(max_x, node.x)
                    max_y = max(max_y, node.y)
                
                # Vérifier les annotations / Check annotations
                if hasattr(self.flow_model, 'annotations'):
                    for annotation in self.flow_model.annotations.values():
                        has_elements = True
                        min_x = min(min_x, annotation.x)
                        min_y = min(min_y, annotation.y)
                        max_x = max(max_x, annotation.x + annotation.width)
                        max_y = max(max_y, annotation.y + annotation.height)
                
                # Vérifier les pipettes (probes) / Check probes
                for probe in self.flow_model.probes.values():
                    has_elements = True
                    min_x = min(min_x, probe.x)
                    min_y = min(min_y, probe.y)
                    max_x = max(max_x, probe.x)
                    max_y = max(max_y, probe.y)
                
                if has_elements:
                    # Définir les marges de sécurité / Define safety margins
                    MARGIN = 50
                    
                    # Calculer les offsets nécessaires pour ramener dans les limites / Calculate offsets needed to bring within bounds
                    offset_x = 0
                    offset_y = 0
                    
                    # Si des éléments sont en négatif, décaler vers la droite/bas / If elements are negative, shift right/down
                    if min_x < MARGIN:
                        offset_x = MARGIN - min_x
                    
                    if min_y < MARGIN:
                        offset_y = MARGIN - min_y
                    
                    # Si des éléments dépassent, décaler vers la gauche/haut / If elements exceed, shift left/up
                    if max_x > self.canvas_width - MARGIN:
                        offset_x -= (max_x - (self.canvas_width - MARGIN))
                    
                    if max_y > self.canvas_height - MARGIN:
                        offset_y -= (max_y - (self.canvas_height - MARGIN))
                    
                    # Appliquer les offsets si nécessaires / Apply offsets if needed
                    if offset_x != 0 or offset_y != 0:
                        if self.app_config.DEBUG_MODE:
                            print(f"[LOAD] ⚠️ Éléments hors limites détectés!")
                            print(f"[LOAD]   Bounding box: ({min_x:.0f}, {min_y:.0f}) → ({max_x:.0f}, {max_y:.0f})")
                            print(f"[LOAD]   Canvas: (0, 0) → ({self.canvas_width}, {self.canvas_height})")
                            print(f"[LOAD]   Décalage appliqué: ({offset_x:.0f}, {offset_y:.0f})")
                        
                        # Appliquer aux nœuds / Apply to nodes
                        for node in self.flow_model.nodes.values():
                            node.x += offset_x
                            node.y += offset_y
                        
                        # Appliquer aux annotations / Apply to annotations
                        if hasattr(self.flow_model, 'annotations'):
                            for annotation in self.flow_model.annotations.values():
                                annotation.x += offset_x
                                annotation.y += offset_y
                        
                        # Appliquer aux pipettes / Apply to probes
                        for probe in self.flow_model.probes.values():
                            probe.x += offset_x
                            probe.y += offset_y
                        
                        # Appliquer aux opérateurs (si présents) / Apply to operators (if present)
                        if hasattr(self.flow_model, 'operators'):
                            for operator in self.flow_model.operators.values():
                                operator.x += offset_x
                                operator.y += offset_y
                        
                        if self.app_config.DEBUG_MODE:
                            print(f"[LOAD]   ✓ Repositionnement global appliqué à tous les éléments")
                    else:
                        if self.app_config.DEBUG_MODE:
                            print(f"[LOAD]   ✓ Toutes les positions sont dans les limites")
                
                # ========================================
                # PHASE 3: RECONSTRUIRE L'AFFICHAGE
                # PHASE 3: REBUILD DISPLAY
                # ========================================
                
                if self.app_config.DEBUG_MODE:
                    print("[LOAD] Phase 3: Reconstruction de l'affichage...")
                
                # Mettre à jour les listes et afficher les nouveaux graphiques / Update lists and display new graphs
                if hasattr(self, 'graphs_panel'):
                    self.graphs_panel.update_probe_list()
                    self.graphs_panel.refresh_graphs()
                
                if hasattr(self, 'time_probe_panel'):
                    self.time_probe_panel.update_probe_list()
                    self.time_probe_panel.refresh_all_graphs()
                
                if hasattr(self, 'operator_travel_panel'):
                    self.operator_travel_panel.refresh_all_graphs()
                
                # Redessiner tout sur le canvas / Redraw everything on canvas
                self.canvas.redraw_all()
                
                # Placer les opérateurs sur leur première machine / Place operators on their first machine
                self._place_operators_on_first_machine()
                
                # Dessiner la bordure du canvas après le redraw / Draw canvas border after redraw
                self.root.after(100, self._draw_canvas_border)
                
                # Restaurer les paramètres des pipettes / Restore probe parameters
                if 'pipettes_params' in data and hasattr(self, 'graphs_panel'):
                    params = data['pipettes_params']
                    self.graphs_panel.graph_height = params.get('graph_height', 2.0)
                    self.graphs_panel.time_window_enabled = params.get('time_window_enabled', True)
                    self.graphs_panel.time_window_duration = params.get('time_window_duration', 20.0)
                
                # Restaurer les paramètres des loupes / Restore time probe parameters
                if 'time_probes_params' in data and hasattr(self, 'time_probe_panel'):
                    params = data['time_probes_params']
                    self.time_probe_panel.graph_height = params.get('graph_height', 1.5)
                
                # Restaurer les paramètres de performance / Restore performance parameters
                if 'performance_params' in data:
                    self.performance_params = data['performance_params'].copy()
                    # Appliquer immédiatement à la configuration globale / Apply immediately to global config
                    self.app_config.update_from_dict(self.performance_params)
                
                # Restaurer les paramètres d'analyse / Restore analysis parameters
                if 'analysis_params' in data and hasattr(self, 'analysis_panel'):
                    params = data['analysis_params']
                    self.analysis_panel.duration_var.set(params.get('duration', '100'))
                    self.analysis_panel.interval_var.set(params.get('interval', '10'))
                    self.analysis_panel.show_arrivals.set(params.get('show_arrivals', True))
                    self.analysis_panel.show_outputs.set(params.get('show_outputs', True))
                    self.analysis_panel.show_wip.set(params.get('show_wip', True))
                    self.analysis_panel.show_utilization.set(params.get('show_utilization', True))
                    self.analysis_panel.show_summary.set(params.get('show_summary', True))
                
                # Assurer que toutes les sources ont au moins un type par défaut / Ensure all sources have at least a default type
                self.flow_model.ensure_all_sources_have_default_types()
                
                # Actualiser les types référencés dans le panneau d'information / Update referenced types in info panel
                if hasattr(self, 'item_types_stats_panel'):
                    self.item_types_stats_panel._update_types_reference_content()
                
                # Stocker le fichier actuel / Store current file
                self.current_filename = filename
                
                # Centrer la vue du canvas sur le contenu chargé / Center canvas view on loaded content
                self.canvas.center_view_on_content()
                
                # Informer l'utilisateur si des opérateurs invalides ont été supprimés / Inform user if invalid operators were removed
                if operators_to_remove:
                    messagebox.showinfo(
                        "Opérateurs supprimés",
                        f"{len(operators_to_remove)} opérateur(s) ont été supprimés car ils faisaient référence à des nœuds qui n'existent plus dans le modèle.\n\n"
                        f"Opérateurs supprimés: {', '.join(operators_to_remove)}\n\n"
                        "Le fichier sera corrigé lors de la prochaine sauvegarde."
                    )
                
                if self.app_config.DEBUG_MODE:
                    print(f"[LOAD] ✓ Chargement terminé avec succès : {filename}")
                
                # Afficher dans la barre de statut au lieu d'une pop-up / Display in status bar instead of pop-up
                self.status_label.config(text=f"✓ Flux chargé : {filename}")
                self.root.after(3000, lambda: self._update_status())  # Revenir au statut normal après 3s / Return to normal status after 3s
            except Exception as e:
                messagebox.showerror(tr('error'), f"{tr('error_opening')}: {e}")
                if self.app_config.DEBUG_MODE:
                    print(f"[LOAD] ✗ Erreur de chargement: {e}")
                import traceback
                traceback.print_exc()
    
    def _import_flow(self):
        """Importe un flux et le fusionne avec le flux actuel (sans effacer) / Import a flow and merge with current flow (without clearing)"""
        from tkinter import filedialog, messagebox
        import pickle
        
        filename = filedialog.askopenfilename(
            filetypes=[("SimPy Flow", "*.simpy"), ("Tous les fichiers", "*.*")],
            title="Importer un flux (fusion)"
        )
        
        if not filename:
            return
        
        try:
            # Lire le fichier à importer / Read file to import
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            
            # ========================================
            # PHASE 1: CALCULER LES NOUVEAUX IDs
            # PHASE 1: CALCULATE NEW IDs
            # ========================================
            
            # Créer les mappings d'anciens IDs vers nouveaux IDs / Create mappings from old IDs to new IDs
            node_id_mapping = {}  # old_id -> new_id
            conn_id_mapping = {}
            probe_id_mapping = {}
            time_probe_id_mapping = {}
            annotation_id_mapping = {}
            operator_id_mapping = {}
            
            # PAS d'offset automatique - on utilise le placement interactif / NO automatic offset - we use interactive placement
            offset_x = 0
            offset_y = 0
            
            # Générer les nouveaux IDs pour les nœuds / Generate new IDs for nodes
            for old_node_id in data['nodes'].keys():
                new_node_id = self.flow_model.generate_node_id()
                node_id_mapping[old_node_id] = new_node_id
            
            # Générer les nouveaux IDs pour les connexions / Generate new IDs for connections
            for old_conn_id in data['connections'].keys():
                new_conn_id = self.flow_model.generate_connection_id()
                conn_id_mapping[old_conn_id] = new_conn_id
            
            # Générer les nouveaux IDs pour les pipettes / Generate new IDs for probes
            if 'probes' in data:
                for old_probe_id in data['probes'].keys():
                    new_probe_id = self.flow_model.generate_probe_id()
                    probe_id_mapping[old_probe_id] = new_probe_id
            
            # Générer les nouveaux IDs pour les loupes de temps / Generate new IDs for time probes
            if 'time_probes' in data:
                for old_time_probe_id in data['time_probes'].keys():
                    new_time_probe_id = self.flow_model.generate_time_probe_id()
                    time_probe_id_mapping[old_time_probe_id] = new_time_probe_id
            
            # Générer les nouveaux IDs pour les annotations / Generate new IDs for annotations
            if 'annotations' in data:
                for old_annotation_id in data['annotations'].keys():
                    new_annotation_id = self.flow_model.generate_annotation_id()
                    annotation_id_mapping[old_annotation_id] = new_annotation_id
            
            # Générer les nouveaux IDs pour les opérateurs / Generate new IDs for operators
            if 'operators' in data:
                for old_operator_id in data['operators'].keys():
                    new_operator_id = self.flow_model.generate_operator_id()
                    operator_id_mapping[old_operator_id] = new_operator_id
            
            # ========================================
            # FONCTION HELPER: NOMS UNIQUES
            # HELPER FUNCTION: UNIQUE NAMES
            # ========================================
            
            def get_unique_name(base_name: str, existing_names: set) -> str:
                """
                Génère un nom unique en ajoutant un suffixe _i si nécessaire.
                Generate unique name by adding _i suffix if needed.
                """
                if base_name not in existing_names:
                    return base_name
                
                # Trouver le prochain numéro disponible / Find next available number
                i = 1
                while f"{base_name}_{i}" in existing_names:
                    i += 1
                return f"{base_name}_{i}"
            
            # Collecter tous les noms existants / Collect all existing names
            existing_node_names = {n.name for n in self.flow_model.nodes.values()}
            existing_probe_names = {p.name for p in self.flow_model.probes.values()}
            existing_time_probe_names = {tp.name for tp in self.flow_model.time_probes.values()}
            existing_operator_names = {op.name for op in self.flow_model.operators.values()}
            
            # ========================================
            # PHASE 2: IMPORTER LES NŒUDS
            # PHASE 2: IMPORT NODES
            # ========================================
            
            from models.flow_model import FlowNode, NodeType, SyncMode, SourceMode
            
            for old_node_id, node_data in data['nodes'].items():
                new_node_id = node_id_mapping[old_node_id]
                
                # Migration des anciens types de sources / Migration of old source types
                node_type_str = node_data['node_type']
                source_mode = None
                
                if node_type_str == 'SOURCE_CONSTANT':
                    node_type_str = 'SOURCE'
                    source_mode = SourceMode.CONSTANT
                elif node_type_str == 'SOURCE_NORMAL':
                    node_type_str = 'SOURCE'
                    source_mode = SourceMode.NORMAL
                elif node_type_str == 'SOURCE_POISSON':
                    node_type_str = 'SOURCE'
                    source_mode = SourceMode.POISSON
                elif node_type_str == 'SOURCE_EXPONENTIAL':
                    node_type_str = 'SOURCE'
                    source_mode = SourceMode.EXPONENTIAL
                
                node_type = NodeType[node_type_str]
                
                # Générer un nom unique (sans suffixe si pas de conflit) / Generate unique name (no suffix if no conflict)
                unique_name = get_unique_name(node_data['name'], existing_node_names)
                existing_node_names.add(unique_name)  # Ajouter pour les futurs imports / Add for future imports
                
                # Créer le nœud avec les nouvelles coordonnées décalées / Create node with new offset coordinates
                node = FlowNode(
                    new_node_id,
                    node_type,
                    unique_name,
                    node_data['x'] + offset_x,
                    node_data['y'] + offset_y
                )
                
                if source_mode is not None:
                    node.source_mode = source_mode
                
                # Copier les propriétés / Copy properties
                node.processing_time_cs = node_data['processing_time_cs']
                node.generation_interval_cs = node_data['generation_interval_cs']
                
                generation_std_dev = node_data['generation_std_dev']
                if generation_std_dev < 10.0:
                    generation_std_dev *= 100.0
                node.generation_std_dev = generation_std_dev
                
                node.generation_lambda = node_data['generation_lambda']
                node.generation_skewness = node_data.get('generation_skewness', 0.0)
                node.max_items_to_generate = node_data['max_items_to_generate']
                node.batch_size = node_data['batch_size']
                node.sync_mode = SyncMode[node_data['sync_mode']]
                node.required_units = node_data['required_units']
                node.legacy_output_quantity = node_data.get('legacy_output_quantity', 1)
                node.legacy_output_type = node_data.get('legacy_output_type', '')
                
                if 'combination_set' in node_data or 'recipe_book' in node_data:
                    from models.combination import CombinationSet
                    data_key = 'combination_set' if 'combination_set' in node_data else 'recipe_book'
                    node.combination_set = CombinationSet.from_dict(node_data[data_key])
                
                node.use_combinations = node_data.get('use_combinations', False)
                node.input_connections = []
                node.output_connections = []
                node.output_multiplier = node_data.get('output_multiplier', 1)
                
                if 'processing_time_mode' in node_data:
                    from models.flow_model import ProcessingTimeMode
                    node.processing_time_mode = ProcessingTimeMode[node_data['processing_time_mode']]
                if 'processing_time_std_dev_cs' in node_data:
                    node.processing_time_std_dev_cs = node_data['processing_time_std_dev_cs']
                if 'processing_time_skewness' in node_data:
                    node.processing_time_skewness = node_data['processing_time_skewness']
                if 'source_mode' in node_data:
                    node.source_mode = SourceMode[node_data['source_mode']]
                if 'splitter_mode' in node_data:
                    from models.flow_model import SplitterMode
                    node.splitter_mode = SplitterMode[node_data['splitter_mode']]
                if 'first_available_mode' in node_data:
                    from models.flow_model import FirstAvailableMode
                    node.first_available_mode = FirstAvailableMode[node_data['first_available_mode']]
                if 'first_available_priority' in node_data:
                    from models.flow_model import FirstAvailablePriority
                    node.first_available_priority = FirstAvailablePriority[node_data['first_available_priority']]
                if 'item_type_config' in node_data:
                    from models.item_type import ItemTypeConfig
                    node.item_type_config = ItemTypeConfig.from_dict(node_data['item_type_config'])
                if 'processing_config' in node_data:
                    from models.item_type import ProcessingConfig
                    node.processing_config = ProcessingConfig.from_dict(node_data['processing_config'])
                
                self.flow_model.nodes[new_node_id] = node
            
            # ========================================
            # PHASE 3: IMPORTER LES CONNEXIONS
            # PHASE 3: IMPORT CONNECTIONS
            # ========================================
            
            from models.flow_model import Connection
            
            for old_conn_id, conn_data in data['connections'].items():
                new_conn_id = conn_id_mapping[old_conn_id]
                new_source_id = node_id_mapping[conn_data['source_id']]
                new_target_id = node_id_mapping[conn_data['target_id']]
                
                conn = Connection(new_conn_id, new_source_id, new_target_id)
                conn.buffer_capacity = conn_data['buffer_capacity']
                conn.show_buffer = conn_data['show_buffer']
                if 'buffer_visual_size' in conn_data:
                    conn.buffer_visual_size = conn_data['buffer_visual_size']
                if 'initial_buffer_count' in conn_data:
                    conn.initial_buffer_count = conn_data['initial_buffer_count']
                    conn.current_buffer_count = conn_data['initial_buffer_count']
                
                self.flow_model.add_connection(conn)
            
            # ========================================
            # PHASE 4: IMPORTER LES PIPETTES
            # PHASE 4: IMPORT PROBES
            # ========================================
            
            if 'probes' in data:
                from models.measurement_probe import MeasurementProbe
                
                for old_probe_id, probe_data in data['probes'].items():
                    new_probe_id = probe_id_mapping[old_probe_id]
                    new_conn_id = conn_id_mapping.get(probe_data['connection_id'])
                    
                    if new_conn_id:  # La connexion existe / The connection exists
                        # Générer un nom unique / Generate unique name
                        unique_name = get_unique_name(probe_data['name'], existing_probe_names)
                        existing_probe_names.add(unique_name)
                        
                        probe = MeasurementProbe(
                            new_probe_id,
                            unique_name,
                            new_conn_id,
                            measure_mode=probe_data.get('measure_mode', 'buffer'),
                            max_points=self.app_config.PROBE_ANALYSIS_MAX_POINTS
                        )
                        probe.x = probe_data['x'] + offset_x
                        probe.y = probe_data['y'] + offset_y
                        probe.color = probe_data['color']
                        probe.visible = probe_data.get('visible', True)
                        self.flow_model.probes[new_probe_id] = probe
            
            # ========================================
            # PHASE 5: IMPORTER LES LOUPES DE TEMPS
            # PHASE 5: IMPORT TIME PROBES
            # ========================================
            
            if 'time_probes' in data:
                from models.time_probe import TimeProbe, TimeProbeType
                
                for old_probe_id, probe_data in data['time_probes'].items():
                    new_probe_id = time_probe_id_mapping[old_probe_id]
                    new_node_id = node_id_mapping.get(probe_data['node_id'])
                    
                    if new_node_id:  # Le nœud existe / The node exists
                        probe_type_name = probe_data['probe_type']
                        if probe_type_name in ['INTERARRIVAL', 'INTERDEPARTURE']:
                            probe_type_name = 'INTER_EVENTS'
                        
                        probe_type = TimeProbeType[probe_type_name]
                        
                        # Générer un nom unique / Generate unique name
                        unique_name = get_unique_name(probe_data['name'], existing_time_probe_names)
                        existing_time_probe_names.add(unique_name)
                        
                        time_probe = TimeProbe(
                            new_probe_id,
                            unique_name,
                            new_node_id,
                            probe_type
                        )
                        time_probe.color = probe_data['color']
                        time_probe.visible = probe_data.get('visible', True)
                        self.flow_model.time_probes[new_probe_id] = time_probe
            
            # ========================================
            # PHASE 6: IMPORTER LES ANNOTATIONS
            # PHASE 6: IMPORT ANNOTATIONS
            # ========================================
            
            if 'annotations' in data:
                from models.annotation import Annotation
                
                for old_annotation_id, annotation_data in data['annotations'].items():
                    new_annotation_id = annotation_id_mapping[old_annotation_id]
                    annotation = Annotation.from_dict(annotation_data)
                    annotation.annotation_id = new_annotation_id
                    annotation.x += offset_x
                    annotation.y += offset_y
                    self.flow_model.annotations[new_annotation_id] = annotation
            
            # ========================================
            # PHASE 7: IMPORTER LES OPÉRATEURS
            # PHASE 7: IMPORT OPERATORS
            # ========================================
            
            if 'operators' in data:
                from models.operator import Operator
                
                for old_operator_id, operator_data in data['operators'].items():
                    new_operator_id = operator_id_mapping[old_operator_id]
                    operator = Operator.from_dict(operator_data)
                    operator.operator_id = new_operator_id
                    
                    # Générer un nom unique / Generate unique name
                    unique_name = get_unique_name(operator.name, existing_operator_names)
                    existing_operator_names.add(unique_name)
                    operator.name = unique_name
                    
                    # Mapper les machines assignées vers les nouveaux IDs / Map assigned machines to new IDs
                    new_assigned_machines = []
                    for old_machine_id in operator.assigned_machines:
                        new_machine_id = node_id_mapping.get(old_machine_id)
                        if new_machine_id and new_machine_id in self.flow_model.nodes:
                            new_assigned_machines.append(new_machine_id)
                    
                    if new_assigned_machines:
                        operator.assigned_machines = new_assigned_machines
                        
                        # Mapper les travel_times vers les nouveaux IDs de machines / Map travel_times to new machine IDs
                        new_travel_times = {}
                        for (old_from, old_to), travel_config in operator.travel_times.items():
                            new_from = node_id_mapping.get(old_from)
                            new_to = node_id_mapping.get(old_to)
                            if new_from and new_to:
                                new_travel_times[(new_from, new_to)] = travel_config
                        operator.travel_times = new_travel_times
                        
                        # Mapper les travel_probes vers les nouveaux IDs de machines / Map travel_probes to new machine IDs
                        new_travel_probes = {}
                        for (old_from, old_to), probe_config in operator.travel_probes.items():
                            new_from = node_id_mapping.get(old_from)
                            new_to = node_id_mapping.get(old_to)
                            if new_from and new_to:
                                new_travel_probes[(new_from, new_to)] = probe_config
                        operator.travel_probes = new_travel_probes
                        
                        operator.x += offset_x
                        operator.y += offset_y
                        self.flow_model.operators[new_operator_id] = operator
            
            # ========================================
            # PHASE 8: RAFRAÎCHIR L'AFFICHAGE ET MODE PLACEMENT
            # PHASE 8: REFRESH DISPLAY AND PLACEMENT MODE
            # ========================================
            
            # Mettre à jour les listes de pipettes/loupes ET les graphiques / Update probe/time probe lists AND graphs
            if hasattr(self, 'graphs_panel'):
                self.graphs_panel.update_probe_list()
                self.graphs_panel.refresh_graphs()
            if hasattr(self, 'time_probe_panel'):
                self.time_probe_panel.update_probe_list()
                self.time_probe_panel.refresh_all_graphs()
            
            # Mettre à jour le panneau d'analyse avec les nouvelles pipettes/loupes / Update analysis panel with new probes/time probes
            if hasattr(self, 'analysis_panel'):
                self.analysis_panel.update_probe_selections()
            
            # Préparer les sets d'éléments importés AVANT le dessin / Prepare sets of imported elements BEFORE drawing
            imported_nodes = set(node_id_mapping.values())
            imported_operators = set(operator_id_mapping.values())
            imported_probes = set(probe_id_mapping.values())
            imported_annotations = set(annotation_id_mapping.values())
            
            # Dessiner UNIQUEMENT les éléments importés (pas redraw_all qui efface tout) / Draw ONLY imported elements (not redraw_all which clears everything)
            self.canvas.draw_imported_elements(
                imported_nodes,
                imported_operators, 
                imported_probes,
                imported_annotations
            )
            
            # Placer les opérateurs / Place operators
            self._place_operators_on_first_machine()
            
            # Activer le mode placement interactif / Enable interactive placement mode
            self.canvas.start_import_placement_mode(
                imported_nodes, 
                imported_operators, 
                imported_probes, 
                imported_annotations
            )
            
            # Statistiques d'importation / Import statistics
            stats = {
                'nodes': len(node_id_mapping),
                'connections': len(conn_id_mapping),
                'probes': len(probe_id_mapping),
                'time_probes': len(time_probe_id_mapping),
                'annotations': len(annotation_id_mapping),
                'operators': len(operator_id_mapping)
            }
            
            # Message informatif (pas de blocage pour permettre le placement) / Info message (no blocking to allow placement)
            msg_parts = []
            if stats['nodes'] > 0:
                msg_parts.append(f"{stats['nodes']} nœud(s)")
            if stats['connections'] > 0:
                msg_parts.append(f"{stats['connections']} connexion(s)")
            if stats['probes'] > 0:
                msg_parts.append(f"{stats['probes']} pipette(s)")
            if stats['time_probes'] > 0:
                msg_parts.append(f"{stats['time_probes']} loupe(s)")
            if stats['annotations'] > 0:
                msg_parts.append(f"{stats['annotations']} annotation(s)")
            if stats['operators'] > 0:
                msg_parts.append(f"{stats['operators']} opérateur(s)")
            
            self.status_label.config(
                text=f"✓ Import: {', '.join(msg_parts)} - Déplacez le curseur et cliquez pour placer"
            )
            
        except Exception as e:
            messagebox.showerror(tr('error'), f"{tr('error_importing')}: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_flow(self):
        """Enregistre le flux actuel (demande le nom de fichier) / Save current flow (ask for filename)"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".simpy",
            filetypes=[("SimPy Flow", "*.simpy"), ("Tous les fichiers", "*.*")],
            title="Enregistrer le flux"
        )
        
        if filename:
            self.current_filename = filename
            self._save_to_file(filename)
    
    def _save_to_file(self, filename):
        """Sauvegarde effectivement le flux dans un fichier / Actually save flow to file"""
        import pickle
        
        if filename:
            try:
                # Préparer les données à sauvegarder / Prepare data to save
                data = {
                    'nodes': {},
                    'connections': {},
                    'time_unit': self.flow_model.current_time_unit.name
                }
                
                # Sauvegarder les nœuds avec tous leurs attributs / Save nodes with all their attributes
                for node_id, node in self.flow_model.nodes.items():
                    node_data = {
                        'node_type': node.node_type.name,
                        'name': node.name,
                        'x': node.x,
                        'y': node.y,
                        'processing_time_cs': node.processing_time_cs,
                        'generation_interval_cs': node.generation_interval_cs,
                        'generation_std_dev': node.generation_std_dev,
                        'generation_lambda': node.generation_lambda,
                        'generation_skewness': node.generation_skewness,
                        'max_items_to_generate': node.max_items_to_generate,
                        'batch_size': node.batch_size,
                        'sync_mode': node.sync_mode.name,
                        'required_units': node.required_units,
                        'legacy_output_quantity': getattr(node, 'legacy_output_quantity', 1),
                        'legacy_output_type': getattr(node, 'legacy_output_type', ''),
                        'combination_set': node.combination_set.to_dict(),  # Sauvegarder les combinaisons / Save combinations
                        'use_combinations': getattr(node, 'use_combinations', False),  # Sauvegarder le mode combinaison / Save combination mode
                        'input_connections': node.input_connections,
                        'output_connections': node.output_connections,
                        'output_multiplier': getattr(node, 'output_multiplier', 1)
                    }
                    
                    # Sauvegarder le mode de traitement, l'écart-type et l'asymétrie / Save processing mode, std dev and skewness
                    if hasattr(node, 'processing_time_mode'):
                        from models.flow_model import ProcessingTimeMode
                        node_data['processing_time_mode'] = node.processing_time_mode.name
                    if hasattr(node, 'processing_time_std_dev_cs'):
                        node_data['processing_time_std_dev_cs'] = node.processing_time_std_dev_cs
                    if hasattr(node, 'processing_time_skewness'):
                        node_data['processing_time_skewness'] = node.processing_time_skewness
                    
                    # Sauvegarder le mode source / Save source mode
                    if hasattr(node, 'source_mode'):
                        node_data['source_mode'] = node.source_mode.name
                    
                    # Sauvegarder les paramètres du splitter / Save splitter parameters
                    if hasattr(node, 'splitter_mode'):
                        node_data['splitter_mode'] = node.splitter_mode.name
                    if hasattr(node, 'first_available_mode'):
                        node_data['first_available_mode'] = node.first_available_mode.name
                    
                    # Sauvegarder la priorité pour FIRST_AVAILABLE (nœuds de traitement) / Save priority for FIRST_AVAILABLE (processing nodes)
                    if hasattr(node, 'first_available_priority'):
                        node_data['first_available_priority'] = node.first_available_priority.name
                    
                    # Sauvegarder la configuration des types d'items (pour sources) / Save item type config (for sources)
                    if hasattr(node, 'item_type_config'):
                        node_data['item_type_config'] = node.item_type_config.to_dict()
                    
                    # Sauvegarder la configuration de traitement par type / Save processing config by type
                    if hasattr(node, 'processing_config'):
                        node_data['processing_config'] = node.processing_config.to_dict()
                    
                    data['nodes'][node_id] = node_data
                
                # Sauvegarder les connexions / Save connections
                for conn_id, conn in self.flow_model.connections.items():
                    data['connections'][conn_id] = {
                        'source_id': conn.source_id,
                        'target_id': conn.target_id,
                        'buffer_capacity': conn.buffer_capacity,
                        'show_buffer': conn.show_buffer,
                        'buffer_visual_size': conn.buffer_visual_size,
                        'initial_buffer_count': getattr(conn, 'initial_buffer_count', 0)
                    }
                
                # Sauvegarder les pipettes / Save probes
                data['probes'] = {}
                for probe_id, probe in self.flow_model.probes.items():
                    data['probes'][probe_id] = {
                        'name': probe.name,
                        'connection_id': probe.connection_id,
                        'measure_mode': probe.measure_mode,
                        'x': probe.x,
                        'y': probe.y,
                        'color': probe.color,
                        'visible': probe.visible
                    }
                
                # Sauvegarder les loupes de temps / Save time probes
                data['time_probes'] = {}
                if hasattr(self.flow_model, 'time_probes'):
                    for probe_id, time_probe in self.flow_model.time_probes.items():
                        data['time_probes'][probe_id] = {
                            'name': time_probe.name,
                            'node_id': time_probe.node_id,
                            'probe_type': time_probe.probe_type.name,
                            'color': time_probe.color,
                            'visible': time_probe.visible
                        }
                
                # Sauvegarder les annotations / Save annotations
                data['annotations'] = {}
                if hasattr(self.flow_model, 'annotations'):
                    for annotation_id, annotation in self.flow_model.annotations.items():
                        data['annotations'][annotation_id] = annotation.to_dict()
                
                # Sauvegarder les opérateurs / Save operators
                data['operators'] = {}
                if hasattr(self.flow_model, 'operators'):
                    for operator_id, operator in self.flow_model.operators.items():
                        data['operators'][operator_id] = operator.to_dict()
                
                # Sauvegarder les paramètres d'analyse / Save analysis parameters
                if hasattr(self, 'analysis_panel'):
                    data['analysis_params'] = {
                        'duration': self.analysis_panel.duration_var.get(),
                        'interval': self.analysis_panel.interval_var.get(),
                        'show_arrivals': getattr(self.analysis_panel, 'show_arrivals', tk.BooleanVar(value=True)).get(),
                        'show_outputs': getattr(self.analysis_panel, 'show_outputs', tk.BooleanVar(value=True)).get(),
                        'show_wip': getattr(self.analysis_panel, 'show_wip', tk.BooleanVar(value=True)).get(),
                        'show_probes': getattr(self.analysis_panel, 'show_probes', tk.BooleanVar(value=True)).get(),
                        'show_time_probes': getattr(self.analysis_panel, 'show_time_probes', tk.BooleanVar(value=True)).get(),
                        'show_utilization': getattr(self.analysis_panel, 'show_utilization', tk.BooleanVar(value=True)).get(),
                        'show_summary': getattr(self.analysis_panel, 'show_summary', tk.BooleanVar(value=True)).get()
                    }
                
                # Sauvegarder les paramètres des pipettes (graphiques) / Save probe parameters (graphs)
                if hasattr(self, 'graphs_panel'):
                    data['pipettes_params'] = {
                        'graph_height': self.graphs_panel.graph_height,
                        'time_window_enabled': self.graphs_panel.time_window_enabled,
                        'time_window_duration': self.graphs_panel.time_window_duration
                    }
                
                # Sauvegarder les paramètres des loupes / Save time probe parameters
                if hasattr(self, 'time_probe_panel'):
                    data['time_probes_params'] = {
                        'graph_height': self.time_probe_panel.graph_height
                    }
                
                # Sauvegarder les paramètres généraux / Save general parameters
                max_speed = 5.0
                if hasattr(self, 'speed_scale'):
                    max_speed = self.speed_scale.cget('to')
                data['general_params'] = {
                    'max_speed': max_speed,
                    'analysis_timeout': getattr(self, 'analysis_timeout', 600),
                    'canvas_width': getattr(self, 'canvas_width', 2000),
                    'canvas_height': getattr(self, 'canvas_height', 2000)
                }
                
                # Sauvegarder les paramètres de performance / Save performance parameters
                data['performance_params'] = self.performance_params.copy()
                
                # Écrire dans le fichier / Write to file
                with open(filename, 'wb') as f:
                    pickle.dump(data, f)
                
                # Afficher la confirmation dans la barre de statut au lieu d'une pop-up / Show confirmation in status bar instead of pop-up
                self.status_label.config(text=f"✓ Flux sauvegardé : {filename}")
                self.root.after(3000, lambda: self._update_status())  # Revenir au statut normal après 3s / Return to normal status after 3s
            except Exception as e:
                messagebox.showerror(tr('error'), f"{tr('error_saving')}: {e}")
    
    def _place_operators_on_first_machine(self):
        """Place tous les opérateurs sur leur première machine assignée / Place all operators on their first assigned machine"""
        if self.app_config.DEBUG_MODE:
            print("\n" + "="*80)
        if self.app_config.DEBUG_MODE:
            print("[PLACE_OP] Début de _place_operators_on_first_machine()")
        if self.app_config.DEBUG_MODE:
            print("="*80)
        
        if not hasattr(self.flow_model, 'operators'):
            if self.app_config.DEBUG_MODE:
                print("[PLACE_OP] Aucun opérateur dans le modèle")
            return
        
        for operator_id, operator in self.flow_model.operators.items():
            if self.app_config.DEBUG_MODE:
                print(f"\n[PLACE_OP] Traitement de {operator_id}:")
            if operator.assigned_machines and len(operator.assigned_machines) > 0:
                first_machine_id = operator.assigned_machines[0]
                first_node = self.flow_model.get_node(first_machine_id)
                
                if first_node:
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Première machine: {first_machine_id}")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Position du nœud (modèle): x={first_node.x}, y={first_node.y}")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Position actuelle opérateur AVANT: x={operator.x}, y={operator.y}")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - current_machine_id AVANT: {getattr(operator, 'current_machine_id', 'None')}")
                    
                    # Mettre à jour les coordonnées modèle / Update model coordinates
                    operator.x = first_node.x
                    operator.y = first_node.y
                    operator.current_machine_id = first_machine_id
                    
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Position opérateur APRÈS mise à jour: x={operator.x}, y={operator.y}")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - current_machine_id APRÈS: {operator.current_machine_id}")
                    
                    # Nettoyer les attributs d'animation résiduels / Clean residual animation attributes
                    operator.animation_from_node = None
                    operator.animation_to_node = None
                    operator.animation_progress = 0.0
                    
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Attributs d'animation nettoyés")
                    
                    # Toujours supprimer puis redessiner complètement pour éviter les décalages / Always delete then redraw completely to avoid offsets
                    was_on_canvas = operator_id in self.canvas.operator_canvas_objects
                    if was_on_canvas:
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Suppression de l'opérateur du canvas")
                        self.canvas.remove_operator(operator_id)
                    else:
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Opérateur n'était pas sur le canvas")
                    
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Appel à draw_operator()")
                    self.canvas.draw_operator(operator)
                    if self.app_config.DEBUG_MODE:
                        print(f"  - draw_operator() terminé")
                    
                    # Synchroniser immédiatement avec la position canvas réelle du nœud / Sync immediately with actual canvas node position
                    # (important si le canvas a été panné/zoomé) / (important if canvas was panned/zoomed)
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Synchronisation avec update_operator_position()")
                    self.canvas.update_operator_position(operator)
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Synchronisation terminée")
        
        if self.app_config.DEBUG_MODE:
            print("\n" + "="*80)
            if self.app_config.DEBUG_MODE:
                print("[PLACE_OP] Fin de _place_operators_on_first_machine()")
            if self.app_config.DEBUG_MODE:
                print("="*80 + "\n")
    
    def _start_simulation(self):
        """Démarre ou reprend la simulation / Start or resume simulation"""
        # Si on démarre manuellement après une analyse, reset les données / If starting manually after analysis, reset data
        if self.is_analysis_mode:
            self._reset_simulation()
            self.is_analysis_mode = False
        
        # Si le simulateur existe, est en cours d'exécution et est en pause, reprendre / If simulator exists, is running and paused, resume
        if (self.simulator and 
            hasattr(self.simulator, 'is_running') and self.simulator.is_running and
            hasattr(self.simulator, 'is_paused') and self.simulator.is_paused):
            # Reprendre la simulation en remettant is_paused à False / Resume simulation by setting is_paused to False
            self.simulator.is_paused = False
        else:
            # Créer un nouveau simulateur pour un nouveau démarrage / Create new simulator for new start
            from simulation.simulator import FlowSimulator
            speed = self.speed_var.get()
            time_unit = self.time_unit_var.get()
            self.simulator = FlowSimulator(
                self.flow_model, 
                update_callback=self._update_canvas,
                speed_factor=speed,
                time_unit=time_unit,
                app_config=self.app_config
            )
            
            # Donner accès au simulateur au canvas pour le clignotement des connexions / Give simulator access to canvas for connection blinking
            self.canvas.simulator = self.simulator
            
            # Connecter les callbacks pour les statistiques de types d'items / Connect callbacks for item type statistics
            if hasattr(self, 'item_types_stats_panel'):
                self.simulator._record_item_generation = self.item_types_stats_panel.record_generation
                self.simulator._record_node_arrival = self.item_types_stats_panel.record_node_arrival
                self.simulator._record_node_departure = self.item_types_stats_panel.record_node_departure
            
            # Placer les opérateurs sur leur première machine avant de démarrer / Place operators on first machine before starting
            self._place_operators_on_first_machine()
            
            # Démarrer le simulateur - il initialisera les positions des opérateurs / Start simulator - it will initialize operator positions
            self.simulator.start()
            
            # Les opérateurs seront dessinés automatiquement dans _do_update_canvas / Operators will be drawn automatically in _do_update_canvas
            # après que le simulateur ait initialisé leurs positions / after simulator has initialized their positions
            
            # Rafraîchir les graphiques des loupes de déplacement au démarrage / Refresh travel probe graphs on startup
            if hasattr(self, 'operator_travel_panel'):
                self.operator_travel_panel.refresh_all_graphs()
        
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal")
        self.btn_stop.config(state="normal")
        self._update_status()
    
    def _update_canvas(self):
        """Callback appelé par le simulateur pour mettre à jour le canvas / Callback called by simulator to update canvas"""
        # Utiliser after pour s'assurer que la mise à jour se fait dans le thread principal / Use after to ensure update is done in main thread
        self.root.after(0, self._do_update_canvas)
    
    def _stop_simulation_if_running(self):
        """Arrête la simulation si elle est en cours après modification du système / Stop simulation if running after system modification"""
        if self.simulator and hasattr(self.simulator, 'is_running') and self.simulator.is_running:
            if self.app_config.DEBUG_MODE:
                print("\n" + "!"*80)
            if self.app_config.DEBUG_MODE:
                print("[RESET] Modification détectée pendant la simulation - Arrêt automatique")
            if self.app_config.DEBUG_MODE:
                print("!"*80 + "\n")
            
            # Arrêter la simulation / Stop simulation
            self._stop_simulation()
            
            if self.app_config.DEBUG_MODE:
                print("\n" + "!"*80)
            if self.app_config.DEBUG_MODE:
                print("[RESET] Simulation arrêtée - Veuillez la redémarrer manuellement")
            if self.app_config.DEBUG_MODE:
                print("!"*80 + "\n")
    
    def _do_update_canvas(self):
        """Met à jour le canvas et les graphiques / Update canvas and graphs"""
        import time
        
        # Rate limiting: limiter à 30 FPS max pour éviter les ralentissements / Rate limiting: limit to 30 FPS max to avoid slowdowns
        current_time = time.time()
        if current_time - self.last_canvas_update_time < self.min_update_interval:
            return  # Ignorer cette update, trop tôt / Ignore this update, too early
        
        self.last_canvas_update_time = current_time
        
        # Mettre à jour les couleurs des nœuds selon leur état actif / Update node colors based on active state
        self.canvas._update_selection_visual()
        
        # Mettre à jour les positions des opérateurs (animation de déplacement) / Update operator positions (movement animation)
        # Utiliser update_operator_position pour déplacer sans redessiner / Use update_operator_position to move without redrawing
        # Cela évite les problèmes de shift avec le zoom/pan / This avoids shift problems with zoom/pan
        for operator_id, operator in self.flow_model.operators.items():
            # Mettre à jour la position de l'opérateur (crée si nécessaire) / Update operator position (creates if needed)
            self.canvas.update_operator_position(operator)
        
        # Mettre à jour uniquement les animations et les textes des buffers / Update only animations and buffer texts
        self.canvas.draw_animated_items()
        # Mettre à jour les textes des buffers sans tout redessiner / Update buffer texts without redrawing everything
        for conn_id, connection in self.flow_model.connections.items():
            # Vérifier si le buffer a changé avant de mettre à jour (OPTIMISATION) / Check if buffer changed before updating (OPTIMIZATION)
            if not getattr(connection, '_buffer_changed', True):
                continue
            
            if conn_id in self.canvas.connection_canvas_objects:
                objs = self.canvas.connection_canvas_objects[conn_id]
                if 'buffer_text' in objs and objs['buffer_text']:
                    buffer_text_str = f"{connection.current_buffer_count}"
                    if connection.buffer_capacity != float('inf'):
                        buffer_text_str += f"/{int(connection.buffer_capacity)}"
                    self.canvas.itemconfig(objs['buffer_text'], text=buffer_text_str)
                # Mettre à jour la couleur du buffer / Update buffer color
                if 'buffer_rect' in objs and objs['buffer_rect']:
                    fill_color = self.canvas.BUFFER_COLOR if connection.current_buffer_count > 0 else "#F0F0F0"
                    self.canvas.itemconfig(objs['buffer_rect'], fill=fill_color)
                # Réinitialiser le flag / Reset flag
                connection._buffer_changed = False
                # Réinitialiser le flag de mise à jour visuelle / Reset visual update flag
                if hasattr(connection, '_needs_visual_update'):
                    connection._needs_visual_update = False
        # Mettre à jour les compteurs des nœuds / Update node counters
        for node_id, node in self.flow_model.nodes.items():
            if node_id in self.canvas.node_canvas_objects:
                objs = self.canvas.node_canvas_objects[node_id]
                if node.is_source and 'count_text' in objs and objs['count_text']:
                    if node.max_items_to_generate > 0:
                        count_label = f"({node.items_generated}/{node.max_items_to_generate})"
                    else:
                        count_label = f"({node.items_generated})"
                    self.canvas.itemconfig(objs['count_text'], text=count_label)
                elif node.is_sink and 'count_text' in objs and objs['count_text']:
                    count_label = f"Reçus: {node.items_received}"
                    self.canvas.itemconfig(objs['count_text'], text=count_label)
        
        # Batch update: forcer le rafraîchissement une seule fois après toutes les modifications
        # Au lieu d'un rafraîchissement par itemconfig(), un seul à la fin
        # Batch update: force refresh once after all modifications
        # Instead of one refresh per itemconfig(), only one at the end
        self.canvas.update_idletasks()
        
        # Mettre à jour la barre de statut avec le WIP (Work In Progress) / Update status bar with WIP (Work In Progress)
        self._update_status()
        
        # Mettre à jour les graphiques de mesure (throttle à 2 Hz pour éviter les bugs d'interface) / Update measurement graphs (throttle to 2 Hz to avoid UI bugs)
        if hasattr(self, 'graphs_panel'):
            if not hasattr(self, 'last_graphs_update'):
                self.last_graphs_update = 0
            if current_time - self.last_graphs_update >= 0.5:  # Max 2 fois par seconde / Max 2 times per second
                self.graphs_panel.update_all_graphs()
                self.last_graphs_update = current_time
        
        # Mettre à jour les statistiques des types d'items (throttle à 1 Hz) / Update item type statistics (throttle to 1 Hz)
        if hasattr(self, 'item_types_stats_panel'):
            if not hasattr(self, 'last_item_types_update'):
                self.last_item_types_update = 0
            if current_time - self.last_item_types_update >= 1.0:  # Max 1 fois par seconde / Max 1 time per second
                self.item_types_stats_panel.refresh_all()
                self.last_item_types_update = current_time
        
        # Mettre à jour les graphiques des loupes de temps (rafraîchissement plus fréquent) / Update time probe graphs (more frequent refresh)
        # Ne pas rafraîchir pendant le mode analyse pour ne pas surcharger / Don't refresh during analysis mode to avoid overload
        if hasattr(self, 'time_probe_panel') and not self.is_analysis_mode:
            # Limiter le rafraîchissement des loupes à 3-4 Hz au lieu de 30 Hz (toutes les 0.25-0.3s) / Limit time probe refresh to 3-4 Hz instead of 30 Hz (every 0.25-0.3s)
            if not hasattr(self, 'last_time_probe_update'):
                self.last_time_probe_update = 0
            if current_time - self.last_time_probe_update >= 0.3:
                self.time_probe_panel.refresh_all_graphs()
                self.last_time_probe_update = current_time
        
        # Mettre à jour les graphiques des temps de déplacement des opérateurs / Update operator travel time graphs
        if hasattr(self, 'operator_travel_panel') and not self.is_analysis_mode:
            if not hasattr(self, 'last_operator_travel_update'):
                self.last_operator_travel_update = 0
            if current_time - self.last_operator_travel_update >= 0.3:
                self.operator_travel_panel.update_all_graphs()
                self.last_operator_travel_update = current_time
    
    def _pause_simulation(self):
        """Met en pause la simulation / Pause the simulation"""
        if self.simulator:
            self.simulator.pause()
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self._update_status()
    
    def _stop_simulation(self):
        """Arrête la simulation / Stop the simulation"""
        if self.simulator:
            self.simulator.stop()
            self.simulator = None  # Réinitialiser le simulateur / Reset simulator
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_stop.config(state="disabled")
        # Reset les animations et les compteurs / Reset animations and counters
        self._reset_simulation()
        # Réinitialiser les graphiques des types d'items / Reset item type graphs
        if hasattr(self, 'item_types_stats_panel'):
            self.item_types_stats_panel.clear_data()
        
        # Réinitialiser complètement les attributs des opérateurs / Completely reset operator attributes
        if self.app_config.DEBUG_MODE:
            print("\n" + "#"*80)
        if self.app_config.DEBUG_MODE:
            print("[STOP] Début de _stop_simulation - Réinitialisation des opérateurs")
        if self.app_config.DEBUG_MODE:
            print("#"*80)
        
        if hasattr(self.flow_model, 'operators'):
            for operator_id, operator in self.flow_model.operators.items():
                if self.app_config.DEBUG_MODE:
                    print(f"\n[STOP] Réinitialisation de {operator_id}:")
                if self.app_config.DEBUG_MODE:
                    print(f"  - AVANT: x={operator.x}, y={operator.y}")
                if self.app_config.DEBUG_MODE:
                    print(f"  - AVANT: current_machine_id={getattr(operator, 'current_machine_id', 'None')}")
                
                # Nettoyer tous les attributs d'animation et de position / Clean all animation and position attributes
                operator.current_machine_id = None
                operator.animation_from_node = None
                operator.animation_to_node = None
                operator.animation_progress = 0.0
                operator.is_available = True
                
                if self.app_config.DEBUG_MODE:
                    print(f"  - APRÈS nettoyage: current_machine_id={operator.current_machine_id}")
                
                # Effacer l'opérateur du canvas / Remove operator from canvas
                if operator_id in self.canvas.operator_canvas_objects:
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Suppression du canvas")
                    self.canvas.remove_operator(operator_id)
                else:
                    if self.app_config.DEBUG_MODE:
                        print(f"  - N'était pas sur le canvas")
        
        if self.app_config.DEBUG_MODE:
            print("\n[STOP] Appel à _place_operators_on_first_machine()")
        # Placer les opérateurs sur leur première machine et les redessiner / Place operators on first machine and redraw
        self._place_operators_on_first_machine()
        
        # Forcer une mise à jour du canvas pour afficher les opérateurs repositionnés / Force canvas update to show repositioned operators
        if self.app_config.DEBUG_MODE:
            print("[STOP] Mise à jour forcée du canvas")
        self.canvas.update_idletasks()
        
        if self.app_config.DEBUG_MODE:
            print("[STOP] Fin de _stop_simulation\n" + "#"*80 + "\n")
        self._update_status()
    
    def _reset_animations(self):
        """Réinitialise uniquement les animations (items en transit) / Reset only animations (items in transit)"""
        for connection in self.flow_model.connections.values():
            connection.items_in_transit.clear()
        # Effacer uniquement les items animés du canvas / Clear only animated items from canvas
        for item_id in list(self.canvas.animated_items.keys()):
            if item_id in self.canvas.animated_items:
                self.canvas.delete(item_id)
        self.canvas.animated_items.clear()
    
    def _reset_simulation(self):
        """Réinitialise la simulation complètement / Completely reset the simulation"""
        # Réinitialiser les compteurs / Reset counters
        for node in self.flow_model.nodes.values():
            if node.is_source:
                node.items_generated = 0
            if node.is_sink:
                node.items_received = 0
            # Réinitialiser l'état d'activité / Reset activity state
            node.is_active = False
        # Réinitialiser les buffers des connexions aux conditions initiales / Reset connection buffers to initial conditions
        for connection in self.flow_model.connections.values():
            # Restaurer les conditions initiales au lieu de mettre à zéro / Restore initial conditions instead of zeroing
            connection.current_buffer_count = getattr(connection, 'initial_buffer_count', 0)
            connection.items_in_transit.clear()
            # Réinitialiser les animations de clignotement / Reset blinking animations
            if hasattr(connection, 'highlight_until'):
                connection.highlight_until = 0
        
        # Réinitialiser les données des pipettes / Reset probe data
        for probe in self.flow_model.probes.values():
            probe.clear_data()
        
        # Réinitialiser les données des loupes de temps / Reset time probe data
        if hasattr(self.flow_model, 'time_probes'):
            for time_probe in self.flow_model.time_probes.values():
                time_probe.clear_data()
        
        # Mettre à jour les graphiques / Update graphs
        if hasattr(self, 'graphs_panel'):
            self.graphs_panel.refresh_graphs()
        
        # Mettre à jour les graphiques des loupes / Update time probe graphs
        if hasattr(self, 'time_probe_panel'):
            self.time_probe_panel.refresh_all_graphs()
        
        # Réinitialiser les données des loupes de déplacement des opérateurs / Reset operator travel probe data
        if hasattr(self.flow_model, 'operators'):
            for operator in self.flow_model.operators.values():
                if hasattr(operator, 'travel_probes'):
                    for probe in operator.travel_probes.values():
                        if 'measurements' in probe:
                            probe['measurements'] = []
        
        # Mettre à jour les graphiques des déplacements des opérateurs / Update operator travel graphs
        if hasattr(self, 'operator_travel_panel'):
            self.operator_travel_panel.refresh_all_graphs()
        
        # Effacer les items animés / Clear animated items
        for item_id in list(self.canvas.animated_items.keys()):
            if item_id in self.canvas.animated_items:
                self.canvas.delete(item_id)
        self.canvas.animated_items.clear()
        
        # Mettre à jour les textes des buffers et compteurs sans redessiner / Update buffer texts and counters without redrawing
        for conn_id, connection in self.flow_model.connections.items():
            if conn_id in self.canvas.connection_canvas_objects:
                objs = self.canvas.connection_canvas_objects[conn_id]
                if 'buffer_text' in objs and objs['buffer_text']:
                    # Afficher current_buffer_count (qui a été restauré aux conditions initiales) / Display current_buffer_count (restored to initial conditions)
                    buffer_text_str = f"{connection.current_buffer_count}"
                    if connection.buffer_capacity != float('inf'):
                        buffer_text_str += f"/{int(connection.buffer_capacity)}"
                    self.canvas.itemconfig(objs['buffer_text'], text=buffer_text_str)
                if 'buffer_rect' in objs and objs['buffer_rect']:
                    # Couleur selon si le buffer contient des unités / Color based on whether buffer contains units
                    fill_color = self.canvas.BUFFER_COLOR if connection.current_buffer_count > 0 else "#F0F0F0"
                    self.canvas.itemconfig(objs['buffer_rect'], fill=fill_color)
        
        for node_id, node in self.flow_model.nodes.items():
            if node_id in self.canvas.node_canvas_objects:
                objs = self.canvas.node_canvas_objects[node_id]
                if node.is_source and 'count_text' in objs and objs['count_text']:
                    if node.max_items_to_generate > 0:
                        count_label = f"(0/{node.max_items_to_generate})"
                    else:
                        count_label = "(0)"
                    self.canvas.itemconfig(objs['count_text'], text=count_label)
                elif node.is_sink and 'count_text' in objs and objs['count_text']:
                    self.canvas.itemconfig(objs['count_text'], text="Reçus: 0")
        
        self._update_status()
    
    def _zoom_in(self):
        """Zoom avant / Zoom in"""
        self.canvas.zoom_in_view()
    
    def _zoom_out(self):
        """Zoom arrière / Zoom out"""
        self.canvas.zoom_out_view()
    
    def _show_item_types_info(self):
        """Affiche le panneau d'information des types d'items / Show item types info panel"""
        # Créer une nouvelle fenêtre / Create a new window
        info_window = tk.Toplevel(self.root)
        info_window.title("Information - Types d'Items")
        info_window.geometry("900x700")
        
        # Import ici pour éviter les imports circulaires / Import here to avoid circular imports
        from gui.item_types_info_panel import ItemTypesInfoPanel
        
        # Créer le panneau / Create the panel
        panel = ItemTypesInfoPanel(info_window, self.flow_model, self.simulator)
        panel.pack(fill=tk.BOTH, expand=True)
        
        # Centrer / Center
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (info_window.winfo_width() // 2)
        y = (info_window.winfo_screenheight() // 2) - (info_window.winfo_height() // 2)
        info_window.geometry(f"+{x}+{y}")
    
    def _show_about(self):
        """Affiche la fenêtre À propos / Show the About window"""
        messagebox.showinfo(
            tr('about_title'),
            tr('about_text')
        )
    
    def _update_node_counts(self):
        """Met à jour uniquement les compteurs de nœuds et connexions / Update only node and connection counters"""
        node_count = len(self.flow_model.nodes)
        connection_count = len(self.flow_model.connections)
        self.node_count_label.config(text=f"Nœuds: {node_count}")
        self.connection_count_label.config(text=f"Connexions: {connection_count}")
    
    def _update_status(self):
        """Met à jour la barre de statut / Update the status bar"""
        mode_text = {
            "select": tr('mode_select'),
            "add_node": tr('mode_add_node'),
            "add_connection": tr('mode_add_connection'),
            "add_probe": tr('mode_add_probe'),
            "add_time_probe": tr('mode_add_time_probe'),
            "add_operator": tr('mode_add_operator'),
            "add_annotation": tr('mode_add_annotation')
        }
        self.status_label.config(text=mode_text.get(self.canvas.mode, tr('ready')))
        
        self.node_count_label.config(text=f"{tr('nodes')}: {len(self.flow_model.nodes)}")
        self.connection_count_label.config(text=f"{tr('connections')}: {len(self.flow_model.connections)}")
        
        # Calculer le Work In Progress (WIP) - nombre total d'unités dans le système / Calculate Work In Progress (WIP) - total units in system
        wip = sum(conn.current_buffer_count for conn in self.flow_model.connections.values())
        
        # Mettre à jour les pipettes et le WIP / Update probes and WIP
        if hasattr(self, 'graphs_panel'):
            probe_count = len(self.flow_model.probes)
            status_extra = f" | Pipettes: {probe_count}" if probe_count > 0 else ""
            status_extra += f" | WIP: {wip}"
            self.status_label.config(
                text=self.status_label.cget("text") + status_extra
            )
    
    def _update_speed_label(self, *args):
        """Met à jour le label de vitesse / Update the speed label"""
        speed = self.speed_var.get()
        self.speed_label.config(text=f"{speed:.1f}x")
        # Mettre à jour la vitesse du simulateur en cours si actif / Update current simulator speed if active
        if self.simulator and self.simulator.is_running:
            self.simulator.set_speed(speed)
    
    def _show_pipettes_settings_dialog(self):
        """Affiche une fenêtre de paramètres unifiée pour les pipettes / Show unified settings window for probes"""
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('pipettes_settings_title'))
        dialog.geometry("550x450")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrer la fenêtre / Center the window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (550 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f"550x450+{x}+{y}")
        
        # Créer un canvas avec scrollbar pour le contenu / Create a canvas with scrollbar for content
        canvas = tk.Canvas(dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mousewheel / Bind mousewheel
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Contenu principal / Main content
        main_frame = ttk.Frame(scrollable_frame, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre / Title
        ttk.Label(
            main_frame,
            text=tr('pipettes_graphs_settings'),
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 15))
        
        # Section 1: Hauteur des graphiques / Section 1: Graph height
        height_section = ttk.LabelFrame(main_frame, text=tr('graph_height_section'), padding="10")
        height_section.pack(fill=tk.X, pady=(0, 10))
        
        height_inner = ttk.Frame(height_section)
        height_inner.pack(fill=tk.X)
        
        ttk.Label(height_inner, text=tr('height_label')).pack(side=tk.LEFT, padx=5)
        
        current_height = self.graphs_panel.graph_height if hasattr(self, 'graphs_panel') else 2.0
        height_var = tk.DoubleVar(value=current_height)
        
        height_spinbox = ttk.Spinbox(
            height_inner,
            from_=0.5, to=5.0, increment=0.1,
            textvariable=height_var,
            width=10
        )
        height_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(height_inner, text=tr('inches')).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            height_section,
            text=tr('graph_height_desc'),
            font=("Arial", 8),
            foreground="#666"
        ).pack(pady=(5, 0))
        
        # Section 2: Fenêtre glissante temporelle / Section 2: Temporal sliding window
        window_section = ttk.LabelFrame(main_frame, text=tr('sliding_window_section'), padding="10")
        window_section.pack(fill=tk.X, pady=(0, 10))
        
        # Option pour activer/désactiver / Option to enable/disable
        current_enabled = False
        current_duration = 20.0
        if hasattr(self, 'graphs_panel'):
            current_enabled = self.graphs_panel.time_window_enabled
            current_duration = self.graphs_panel.time_window_duration
        
        enable_var = tk.BooleanVar(value=current_enabled)
        
        enable_check = ttk.Checkbutton(
            window_section,
            text=tr('enable_sliding_window'),
            variable=enable_var
        )
        enable_check.pack(anchor=tk.W, pady=(0, 10))
        
        # Durée de la fenêtre / Window duration
        duration_frame = ttk.Frame(window_section)
        duration_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(duration_frame, text=tr('duration_sim_time')).pack(side=tk.LEFT, padx=5)
        
        duration_var = tk.DoubleVar(value=current_duration)
        
        duration_spinbox = ttk.Spinbox(
            duration_frame,
            from_=10.0, to=10000.0, increment=10.0,
            textvariable=duration_var,
            width=12
        )
        duration_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(duration_frame, text=tr('units_text')).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            window_section,
            text=tr('sliding_window_desc'),
            font=("Arial", 8),
            foreground="#666"
        ).pack(pady=(0, 0))
        
        # Fonction d'application / Apply function
        def apply_all_settings():
            if hasattr(self, 'graphs_panel'):
                # Appliquer la hauteur / Apply height
                self.graphs_panel.set_graph_height(height_var.get())
                # Appliquer la fenêtre glissante / Apply sliding window
                self.graphs_panel.set_time_window(
                    enabled=enable_var.get(),
                    duration=duration_var.get()
                )
            canvas.unbind_all("<MouseWheel>")
            dialog.destroy()
        
        def on_cancel():
            canvas.unbind_all("<MouseWheel>")
            dialog.destroy()
        
        # Boutons / Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="✓ Appliquer", command=apply_all_settings, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✕ Annuler", command=on_cancel, width=12).pack(side=tk.LEFT, padx=5)
    
    def _show_time_probes_settings_dialog(self):
        """Affiche une fenêtre de paramètres pour les loupes de temps / Show settings window for time probes"""
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('time_probes_settings_title'))
        dialog.geometry("500x350")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrer la fenêtre / Center the window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"500x350+{x}+{y}")
        
        # Contenu principal / Main content
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre / Title
        ttk.Label(
            main_frame,
            text=tr('time_probes_graphs_settings'),
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 15))
        
        # Section: Hauteur des graphiques / Section: Graph height
        size_section = ttk.LabelFrame(main_frame, text=tr('graph_height_section'), padding="10")
        size_section.pack(fill=tk.X, pady=(0, 10))
        
        # Hauteur / Height
        height_frame = ttk.Frame(size_section)
        height_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(height_frame, text=tr('height_label')).pack(side=tk.LEFT, padx=5)
        
        current_height = self.time_probe_panel.graph_height if hasattr(self, 'time_probe_panel') else 1.5
        height_var = tk.DoubleVar(value=current_height)
        
        height_spinbox = ttk.Spinbox(
            height_frame,
            from_=2.0, to=10.0, increment=0.5,
            textvariable=height_var,
            width=10
        )
        height_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(height_frame, text=tr('inches')).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            size_section,
            text=tr('histogram_size_desc'),
            font=("Arial", 8),
            foreground="#666"
        ).pack(pady=(5, 0))
        
        # Fonction d'application / Apply function
        def apply_settings():
            if hasattr(self, 'time_probe_panel'):
                self.time_probe_panel.set_graph_height(height_var.get())
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Boutons / Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text=tr('apply'), command=apply_settings, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=tr('cancel_btn'), command=on_cancel, width=12).pack(side=tk.LEFT, padx=5)
    
    def _show_general_settings_dialog(self):
        """Affiche une fenêtre de paramètres généraux / Show general settings window"""
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('general_params'))
        dialog.geometry("450x250")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrer la fenêtre / Center the window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"450x250+{x}+{y}")
        
        # Contenu principal / Main content
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre / Title
        ttk.Label(
            main_frame,
            text="⚙️ " + tr('general_params'),
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 15))
        
        # Section: Vitesse de simulation / Section: Simulation speed
        speed_section = ttk.LabelFrame(main_frame, text=tr('simulation_speed_section'), padding="10")
        speed_section.pack(fill=tk.X, pady=(0, 10))
        
        # Vitesse maximale / Maximum speed
        max_speed_frame = ttk.Frame(speed_section)
        max_speed_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(max_speed_frame, text=tr('max_speed_label')).pack(side=tk.LEFT, padx=5)
        
        # Récupérer la vitesse max actuelle du scale / Get current max speed from scale
        current_max_speed = 5.0
        if hasattr(self, 'speed_scale'):
            current_max_speed = self.speed_scale.cget('to')
        
        max_speed_var = tk.DoubleVar(value=current_max_speed)
        
        max_speed_spinbox = ttk.Spinbox(
            max_speed_frame,
            from_=1.0, to=100.0, increment=1.0,
            textvariable=max_speed_var,
            width=10
        )
        max_speed_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(max_speed_frame, text="x").pack(side=tk.LEFT, padx=2)
        
        ttk.Label(
            speed_section,
            text=tr('max_speed_desc'),
            font=("Arial", 8),
            foreground="#666"
        ).pack(pady=(5, 0))
        
        # Fonction d'application / Apply function
        def apply_gen_settings():
            new_max_speed = max_speed_var.get()
            # Mettre à jour le scale de vitesse / Update speed scale
            if hasattr(self, 'speed_scale'):
                current_value = self.speed_scale.get()
                self.speed_scale.config(to=new_max_speed)
                # Ajuster la valeur actuelle si elle dépasse la nouvelle limite / Adjust current value if it exceeds new limit
                if current_value > new_max_speed:
                    self.speed_scale.set(new_max_speed)
            dialog.destroy()
        
        def on_gen_cancel():
            dialog.destroy()
        
        # Boutons / Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text=tr('apply'), command=apply_gen_settings, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=tr('cancel_btn'), command=on_gen_cancel, width=12).pack(side=tk.LEFT, padx=5)
    
    def _show_keyboard_shortcuts(self):
        """Affiche une fenêtre avec tous les raccourcis clavier / Show window with all keyboard shortcuts"""
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('keyboard_shortcuts_title'))
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrer la fenêtre / Center the window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (500 // 2)
        dialog.geometry(f"600x500+{x}+{y}")
        
        # Créer un canvas avec scrollbar / Create canvas with scrollbar
        canvas = tk.Canvas(dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Contenu / Content
        main_frame = ttk.Frame(scrollable_frame, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            main_frame,
            text=tr('keyboard_shortcuts_header'),
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 20))
        
        shortcuts = [
            (tr('file_section'), [
                ("Ctrl + S", tr('quick_save'))
            ]),
            (tr('edit_modes_section'), [
                ("W", tr('mode_selection')),
                ("A", tr('add_source_node')),
                ("S", tr('add_processing_node')),
                ("D", tr('add_sink_node')),
                ("X", tr('add_splitter_node')),
                ("C", tr('add_merger_node')),
                ("E", tr('add_measurement_probe')),
                ("R", tr('add_time_probe_shortcut')),
                ("Z", tr('add_operator_shortcut'))
            ]),
            (tr('simulation_section_shortcuts'), [
                (tr('space_key'), tr('start_pause_sim')),
                ("V", tr('stop_sim'))
            ]),
            (tr('edition_section'), [
                ("Suppr / Backspace", tr('delete_selected')),
                (tr('double_click'), tr('edit_node_connection'))
            ]),
            (tr('canvas_nav_section'), [
                (tr('mouse_wheel'), tr('zoom_in_out')),
                (tr('click_drag_select'), tr('move_node')),
                (tr('right_click'), tr('context_menu')),
                (tr('click_empty_drag'), tr('pan_view'))
            ])
        ]
        
        for section_title, section_shortcuts in shortcuts:
            # Titre de section / Section title
            section_frame = ttk.LabelFrame(main_frame, text=section_title, padding="10")
            section_frame.pack(fill=tk.X, pady=10)
            
            for key, description in section_shortcuts:
                shortcut_frame = ttk.Frame(section_frame)
                shortcut_frame.pack(fill=tk.X, pady=3)
                
                # Touche / Key
                key_label = ttk.Label(
                    shortcut_frame,
                    text=key,
                    font=("Arial", 9, "bold"),
                    foreground="#0066CC",
                    width=25
                )
                key_label.pack(side=tk.LEFT)
                
                # Description / Description
                desc_label = ttk.Label(
                    shortcut_frame,
                    text=description,
                    font=("Arial", 9)
                )
                desc_label.pack(side=tk.LEFT, padx=10)
        
        # Bouton fermer / Close button
        ttk.Button(
            main_frame,
            text=tr('close'),
            command=dialog.destroy,
            width=15
        ).pack(pady=20)
