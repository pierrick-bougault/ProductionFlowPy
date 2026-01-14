"""Fenêtre de configuration pour un nœud / Node configuration dialog"""
import tkinter as tk
from tkinter import ttk, messagebox
from models.flow_model import FlowNode, SyncMode
from models.time_converter import TimeUnit, TimeConverter
from gui.item_types_config_dialog import ItemTypesConfigDialog
from gui.translations import tr

# Mapping entre les modes de génération et leurs clés de traduction
# Mapping between generation modes and their translation keys
ITEM_GEN_MODE_TRANSLATIONS = {
    'SINGLE_TYPE': 'single_type',
    'SEQUENCE': 'defined_sequence',
    'RANDOM_FINITE': 'random_finite',
    'RANDOM_INFINITE': 'random_infinite'
}

# Mapping entre les modes de synchronisation et leurs clés de traduction
# Mapping between sync modes and their translation keys
SYNC_MODE_TRANSLATIONS = {
    'WAIT_N_FROM_BRANCH': 'sync_wait_n_from_branch',
    'FIRST_AVAILABLE': 'sync_first_available'
}

# Mapping entre les modes de priorité et leurs clés de traduction
# Mapping between priority modes and their translation keys
PRIORITY_MODE_TRANSLATIONS = {
    'ORDER': 'priority_order',
    'ROUND_ROBIN': 'priority_round_robin',
    'RANDOM': 'priority_random'
}

class NodeConfigDialog(tk.Toplevel):
    """Dialogue de configuration d'un nœud / Node configuration dialog"""
    
    def __init__(self, parent, node: FlowNode, current_time_unit: TimeUnit, flow_model=None, on_save_callback=None):
        super().__init__(parent)
        self.node = node
        self.current_time_unit = current_time_unit
        self.flow_model = flow_model
        self.on_save_callback = on_save_callback
        self.loupe_ids = []  # Liste des IDs des loupes affichées / List of displayed probe IDs
        
        self.title(f"Configuration - {node.name}")
        self.geometry("900x650")  # Taille initiale élargie / Initial expanded size
        self.minsize(700, 400)  # Taille minimale / Minimum size
        self.resizable(True, True)  # Fenêtre redimensionnable / Resizable window
        
        # Rendre la fenêtre modale / Make window modal
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_node_data()
        
        # Forcer le rafraîchissement des types pour les nœuds de traitement
        # Force type refresh for processing nodes
        # Cela garantit que les types détectés sont toujours à jour à l'ouverture
        # This ensures detected types are always up-to-date on open
        if not self.node.is_source and not self.node.is_splitter and not self.node.is_merger:
            if hasattr(self, '_refresh_type_processing_config'):
                self._refresh_type_processing_config()
        
        # Bind touche Entrée au bouton Enregistrer et Échap au bouton Annuler
        # Bind Enter key to Save button and Escape to Cancel button
        self.bind('<Return>', lambda e: self._save())
        self.bind('<Escape>', lambda e: self.destroy())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.focus_force()
        
        # Centrer la fenêtre / Center window
        self._center_window()
    
    def _create_widgets(self):
        """Crée les widgets du dialogue / Create dialog widgets"""
        # Créer un canvas avec scrollbar pour le contenu scrollable
        # Create canvas with scrollbar for scrollable content
        # Utiliser la couleur de fond par défaut du système au lieu de blanc
        # Use system default background color instead of white
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        
        # Frame scrollable qui contiendra tout le contenu
        # Scrollable frame that will contain all content
        self.scrollable_frame = ttk.Frame(canvas, padding="10")
        
        # Configurer le scroll / Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Créer la fenêtre dans le canvas avec une largeur fixe
        # Create window in canvas with fixed width
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Faire en sorte que la frame s'adapte à la largeur du canvas
        # Make frame adapt to canvas width
        def _configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', _configure_canvas)
        
        # Empaqueter le canvas et la scrollbar / Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Permettre le scroll avec la molette de la souris (seulement quand la souris est sur le canvas)
        # Allow scroll with mouse wheel (only when mouse is over canvas)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Stocker le canvas pour le nettoyage / Store canvas for cleanup
        self.canvas = canvas
        
        # Utiliser scrollable_frame au lieu de main_frame
        # Use scrollable_frame instead of main_frame
        main_frame = self.scrollable_frame
        
        # Configurer les colonnes pour qu'elles s'étendent
        # Configure columns to expand
        main_frame.columnconfigure(0, weight=0, minsize=150)  # Labels
        main_frame.columnconfigure(1, weight=1)  # Contenu principal / Main content
        main_frame.columnconfigure(2, weight=0)  # Colonne supplémentaire si nécessaire / Additional column if needed
        
        # Nom du nœud / Node name
        ttk.Label(main_frame, text=tr('node_name') + ":", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10)
        )
        self.name_entry = ttk.Entry(main_frame)
        self.name_entry.grid(row=0, column=1, columnspan=2, pady=5, padx=5, sticky="ew")
        
        # Temps de traitement / Processing time
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=10
        )
        
        # Section spécifique selon le type de nœud
        # Specific section based on node type
        if self.node.is_source:
            self._create_source_config(main_frame, start_row=2)
            next_row = 9
        elif self.node.is_splitter:
            self._create_splitter_config(main_frame, start_row=2)
            next_row = 6
        elif self.node.is_merger:
            self._create_merger_config(main_frame, start_row=2)
            next_row = 5
        else:
            self._create_processing_config(main_frame, start_row=2)
            next_row = 11  # Augmenté pour tenir compte des champs mode/std_dev/skewness/output / Increased for mode/std_dev/skewness/output fields
        
        # Configuration des flux multiples (uniquement pour nœuds non-sources, non-splitters, non-mergers)
        # Multiple flow configuration (only for non-source, non-splitter, non-merger nodes)
        if not self.node.is_source and not self.node.is_splitter and not self.node.is_merger:
            ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
                row=next_row, column=0, columnspan=3, sticky="ew", padx=20, pady=10
            )
            
            ttk.Label(main_frame, text=tr('multiple_flows'), font=("Arial", 10, "bold")).grid(
                row=next_row+1, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5
            )

            sync_frame = ttk.Frame(main_frame)
            sync_frame.grid(row=next_row+2, column=0, columnspan=3, sticky=tk.W, padx=20)

            ttk.Label(sync_frame, text=tr('sync_mode')).pack(anchor=tk.W, pady=5)
            
            self.sync_mode_var = tk.StringVar()
            for sync_mode in SyncMode:
                ttk.Radiobutton(
                    sync_frame,
                    text=tr(SYNC_MODE_TRANSLATIONS.get(sync_mode.name, sync_mode.name)),
                    variable=self.sync_mode_var,
                    value=sync_mode.name,
                    command=self._on_sync_mode_change
                ).pack(anchor=tk.W, padx=10)
            
            # Configuration de la priorité pour FIRST_AVAILABLE
            # Priority configuration for FIRST_AVAILABLE
            self.priority_config_frame = ttk.LabelFrame(main_frame, text=tr('priority_config'), padding="5")
            self.priority_config_frame.grid(row=next_row+3, column=0, columnspan=3, sticky="ew", padx=20, pady=5)
            self.priority_config_frame.grid_remove()  # Caché par défaut / Hidden by default
            
            from models.flow_model import FirstAvailablePriority
            self.first_available_priority_var = tk.StringVar()
            for priority_mode in FirstAvailablePriority:
                ttk.Radiobutton(
                    self.priority_config_frame,
                    text=tr(PRIORITY_MODE_TRANSLATIONS.get(priority_mode.name, priority_mode.name)),
                    variable=self.first_available_priority_var,
                    value=priority_mode.name
                ).pack(anchor=tk.W, padx=10)
            
            # Configuration des branches (visible si WAIT_N_FROM_BRANCH)
            # Branch configuration (visible if WAIT_N_FROM_BRANCH)
            self.branch_config_frame = ttk.LabelFrame(main_frame, text=tr('branch_config'), padding="5")
            self.branch_config_frame.grid(row=next_row+4, column=0, columnspan=3, sticky="ew", padx=20, pady=10)
            self.branch_config_frame.grid_remove()  # Caché par défaut / Hidden by default
            
            # Choix du mode: Combinaisons ou Legacy
            # Mode choice: Combinations or Legacy
            mode_frame = ttk.Frame(self.branch_config_frame)
            mode_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(mode_frame, text=tr('processing_mode'), font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))

            self.combination_mode_var = tk.StringVar(value="legacy")

            ttk.Radiobutton(
                mode_frame,
                text=tr('quantity_mode'),
                variable=self.combination_mode_var,
                value="legacy",
                command=self._on_combination_mode_changed
            ).pack(anchor=tk.W, padx=20)

            ttk.Radiobutton(
                mode_frame,
                text=tr('combination_mode'),
                variable=self.combination_mode_var,
                value="combinations",
                command=self._on_combination_mode_changed
            ).pack(anchor=tk.W, padx=20, pady=(5, 10))
            
            # Frame pour le mode Combinaisons / Frame for Combinations mode
            self.combinations_mode_frame = ttk.Frame(self.branch_config_frame)
            self.combinations_mode_frame.pack(fill=tk.X, pady=5)
            
            ttk.Button(
                self.combinations_mode_frame,
                text=tr('configure_combinations'),
                command=self._open_combination_set
            ).pack(pady=5)

            self.combinations_info_label = ttk.Label(
                self.combinations_mode_frame,
                text=tr('no_combination_configured'),
                foreground="gray"
            )
            self.combinations_info_label.pack(anchor=tk.W, padx=20)
            
            # Frame pour le mode Legacy / Frame for Legacy mode
            self.legacy_mode_frame = ttk.Frame(self.branch_config_frame)
            self.legacy_mode_frame.pack(fill=tk.X, pady=5)
            
            self.branch_entries = {}
            # Note: Le contenu sera créé dynamiquement dans _setup_branch_config()
            # Note: Content will be created dynamically in _setup_branch_config()
            
            next_row = next_row + 5  # Ajuster pour les boutons / Adjust for buttons
        else:
            # Initialiser les variables pour les sources (qui n'ont pas de sync)
            # Initialize variables for sources (which have no sync)
            self.sync_mode_var = tk.StringVar()
            self.first_available_priority_var = tk.StringVar()
            self.priority_config_frame = None
            self.branch_config_frame = None
            self.branch_entries = {}
        
        # Section Loupes de temps / Time probes section
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
            row=next_row, column=0, columnspan=3, sticky="ew", padx=20, pady=10
        )
        
        ttk.Label(main_frame, text=tr('time_probes_label'), font=("Arial", 10, "bold")).grid(
            row=next_row+1, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5
        )
        
        # Frame pour le contenu dynamique de la loupe (similaire aux pipettes)
        # Frame for dynamic probe content (similar to probes)
        self.loupe_content_frame = ttk.Frame(main_frame)
        self.loupe_content_frame.grid(row=next_row+2, column=0, columnspan=3, sticky="ew", padx=20, pady=5)
        
        # Charger la section loupe / Load probe section
        self._update_time_probe_section()
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=next_row+5, column=0, columnspan=3, pady=20, padx=20, sticky="ew")
        
        # Centrer les boutons / Center buttons
        button_container = ttk.Frame(button_frame)
        button_container.pack(expand=True)
        
        ttk.Button(button_container, text=tr('save_btn'), command=self._save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_container, text=tr('cancel_btn'), command=self.destroy, width=15).pack(side=tk.LEFT, padx=5)
    
    def _create_source_config(self, parent, start_row):
        """Crée la section de configuration pour les nœuds sources / Create configuration section for source nodes"""
        ttk.Label(parent, text=tr('flow_generation'), font=("Arial", 10, "bold")).grid(
            row=start_row, column=0, sticky=tk.W, pady=5
        )
        
        # Mode de génération / Generation mode
        mode_frame = ttk.Frame(parent)
        mode_frame.grid(row=start_row+1, column=0, columnspan=3, sticky=tk.W, padx=20)
        
        from models.flow_model import SourceMode
        self.source_mode_var = tk.StringVar()
        ttk.Label(mode_frame, text=tr('mode_label')).pack(side=tk.LEFT, padx=5)
        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.source_mode_var,
            values=[mode.name for mode in SourceMode],
            state="readonly",
            width=20
        )
        mode_combo.pack(side=tk.LEFT, padx=5)
        mode_combo.bind('<<ComboboxSelected>>', lambda e: self._on_source_mode_change())
        
        # Bouton d'édition graphique / Graphical edit button
        ttk.Button(
            mode_frame,
            text=tr('edit_graphically'),
            command=self._open_source_distribution_editor
        ).pack(side=tk.LEFT, padx=10)
        
        # Nombre d'items à générer / Number of items to generate
        ttk.Label(parent, text=tr('items_count')).grid(row=start_row+2, column=0, sticky=tk.W, padx=20)
        items_frame = ttk.Frame(parent)
        items_frame.grid(row=start_row+2, column=1, columnspan=2, sticky=tk.W)

        self.max_items_var = tk.StringVar()
        ttk.Entry(items_frame, textvariable=self.max_items_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(items_frame, text=tr('unlimited_note')).pack(side=tk.LEFT)
        # Taille des lots / Batch size
        ttk.Label(parent, text=tr('units_per_batch')).grid(row=start_row+3, column=0, sticky=tk.W, padx=20)
        batch_frame = ttk.Frame(parent)
        batch_frame.grid(row=start_row+3, column=1, columnspan=2, sticky=tk.W)

        self.batch_size_var = tk.StringVar()
        ttk.Entry(batch_frame, textvariable=self.batch_size_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(batch_frame, text=tr('units_per_generation')).pack(side=tk.LEFT)
        # Intervalle moyen / Average interval
        ttk.Label(parent, text=tr('average_interval')).grid(row=start_row+4, column=0, sticky=tk.W, padx=20)
        interval_frame = ttk.Frame(parent)
        interval_frame.grid(row=start_row+4, column=1, columnspan=2, sticky=tk.W)
        
        self.generation_interval_var = tk.StringVar()
        ttk.Entry(interval_frame, textvariable=self.generation_interval_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(interval_frame, text=TimeConverter.get_unit_symbol(self.current_time_unit)).pack(side=tk.LEFT)
        
        # Écart-type (visible pour NORMAL et SKEW_NORMAL)
        # Standard deviation (visible for NORMAL and SKEW_NORMAL)
        self.gen_std_dev_frame = ttk.Frame(parent)
        self.gen_std_dev_frame.grid(row=start_row+5, column=0, columnspan=3, sticky=tk.W, padx=20)
        self.gen_std_dev_frame.grid_remove()  # Caché par défaut / Hidden by default
        
        ttk.Label(self.gen_std_dev_frame, text=tr('std_dev_label')).pack(side=tk.LEFT, padx=5)
        self.generation_stddev_var = tk.StringVar()
        ttk.Entry(self.gen_std_dev_frame, textvariable=self.generation_stddev_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.gen_std_dev_frame, text=TimeConverter.get_unit_symbol(self.current_time_unit)).pack(side=tk.LEFT)
        
        # Asymétrie (visible pour SKEW_NORMAL)
        # Skewness (visible for SKEW_NORMAL)
        self.gen_skewness_frame = ttk.Frame(parent)
        self.gen_skewness_frame.grid(row=start_row+5, column=0, columnspan=3, sticky=tk.W, padx=20)
        self.gen_skewness_frame.grid_remove()  # Caché par défaut / Hidden by default
        
        ttk.Label(self.gen_skewness_frame, text=tr('skewness_label')).pack(side=tk.LEFT, padx=5)
        self.generation_skewness_var = tk.StringVar(value="0.0")
        ttk.Entry(self.gen_skewness_frame, textvariable=self.generation_skewness_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.gen_skewness_frame, text="(-5 / +5)").pack(side=tk.LEFT)

        # Types d'items multiples - Intégré directement
        # Multiple item types - Integrated directly
        types_labelframe = ttk.LabelFrame(parent, text=tr('item_types_label'), padding="10")
        types_labelframe.grid(row=start_row+6, column=0, columnspan=3, sticky="ew", padx=20, pady=10)

        # Mode de génération des types / Type generation mode
        ttk.Label(types_labelframe, text=tr('mode_label')).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.item_gen_mode_var = tk.StringVar()
        from models.item_type import ItemGenerationMode
        
        # Créer les valeurs traduites pour la combobox
        # Create translated values for combobox
        translated_mode_values = [tr(ITEM_GEN_MODE_TRANSLATIONS[mode.name]) for mode in ItemGenerationMode]
        
        item_mode_combo = ttk.Combobox(
            types_labelframe,
            textvariable=self.item_gen_mode_var,
            values=translated_mode_values,
            state="readonly",
            width=35
        )
        item_mode_combo.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        item_mode_combo.bind('<<ComboboxSelected>>', lambda e: self._on_item_gen_mode_change())
        
        # ========== Frame SINGLE_TYPE / SINGLE_TYPE Frame ==========
        self.single_type_frame = ttk.Frame(types_labelframe)
        self.single_type_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        ttk.Label(self.single_type_frame, text=tr('item_type_single_label')).pack(side=tk.LEFT, padx=5)
        self.selected_type_var = tk.StringVar()
        self.single_type_combo = ttk.Combobox(
            self.single_type_frame,
            textvariable=self.selected_type_var,
            state="readonly",
            width=25
        )
        self.single_type_combo.pack(side=tk.LEFT, padx=5)
        
        # ========== Frame SEQUENCE / SEQUENCE Frame ==========
        self.sequence_frame = ttk.Frame(types_labelframe)
        self.sequence_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        ttk.Label(self.sequence_frame, text=tr('sequence_label')).pack(anchor=tk.W, pady=(0, 5))
        
        seq_controls = ttk.Frame(self.sequence_frame)
        seq_controls.pack(fill=tk.X, pady=5)
        
        self.sequence_combo = ttk.Combobox(seq_controls, state="readonly", width=25)
        self.sequence_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(seq_controls, text="➕", width=3, command=self._add_to_sequence).pack(side=tk.LEFT, padx=2)
        ttk.Button(seq_controls, text="🗑️", width=3, command=self._remove_from_sequence).pack(side=tk.LEFT, padx=2)
        ttk.Button(seq_controls, text="⬆️", width=3, command=self._move_sequence_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(seq_controls, text="⬇️", width=3, command=self._move_sequence_down).pack(side=tk.LEFT, padx=2)
        
        self.sequence_listbox = tk.Listbox(self.sequence_frame, height=6)
        self.sequence_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.sequence_loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.sequence_frame,
            text=tr('loop_forever'),
            variable=self.sequence_loop_var
        ).pack(anchor=tk.W)
        
        # ========== Frame RANDOM_FINITE / RANDOM_FINITE Frame ==========
        self.random_finite_frame = ttk.Frame(types_labelframe)
        self.random_finite_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        ttk.Label(self.random_finite_frame, text=tr('hypergeometric_qty'), 
                 font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Scrollable frame pour les quantités / Scrollable frame for quantities
        finite_canvas = tk.Canvas(self.random_finite_frame, height=150)
        finite_scroll = ttk.Scrollbar(self.random_finite_frame, orient="vertical", command=finite_canvas.yview)
        self.finite_quantities_frame = ttk.Frame(finite_canvas)
        
        self.finite_quantities_frame.bind(
            "<Configure>",
            lambda e: finite_canvas.configure(scrollregion=finite_canvas.bbox("all"))
        )
        
        finite_canvas.create_window((0, 0), window=self.finite_quantities_frame, anchor="nw")
        finite_canvas.configure(yscrollcommand=finite_scroll.set)
        
        finite_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        finite_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Dictionnaire pour stocker les entrées de quantités
        # Dictionary to store quantity entries
        self.finite_quantity_vars = {}
        
        # ========== Frame RANDOM_INFINITE / RANDOM_INFINITE Frame ==========
        self.random_infinite_frame = ttk.Frame(types_labelframe)
        self.random_infinite_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        ttk.Label(self.random_infinite_frame, text=tr('categorical_props'), 
                 font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Scrollable frame pour les proportions / Scrollable frame for proportions
        infinite_canvas = tk.Canvas(self.random_infinite_frame, height=180)
        infinite_scroll = ttk.Scrollbar(self.random_infinite_frame, orient="vertical", command=infinite_canvas.yview)
        self.infinite_proportions_frame = ttk.Frame(infinite_canvas)
        
        self.infinite_proportions_frame.bind(
            "<Configure>",
            lambda e: infinite_canvas.configure(scrollregion=infinite_canvas.bbox("all"))
        )
        
        infinite_canvas.create_window((0, 0), window=self.infinite_proportions_frame, anchor="nw")
        infinite_canvas.configure(yscrollcommand=infinite_scroll.set)
        
        infinite_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        infinite_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Dictionnaire pour stocker les entrées de proportions
        # Dictionary to store proportion entries
        self.infinite_proportion_vars = {}
        
        # Information
        info_text = "Les items seront générés selon le mode choisi."  # Items will be generated according to chosen mode
        ttk.Label(types_labelframe, text=info_text, font=("Arial", 8, "italic"), 
                 foreground="#666").grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # Cacher tous les frames par défaut / Hide all frames by default
        self.single_type_frame.grid_remove()
        self.sequence_frame.grid_remove()
        self.random_finite_frame.grid_remove()
        self.random_infinite_frame.grid_remove()
    
    def _create_processing_config(self, parent, start_row):
        """Crée la section de configuration pour les nœuds de traitement / Create configuration section for processing nodes"""
        # Configuration globale du temps de traitement / Global processing time configuration
        ttk.Label(parent, text=tr('global_config'), font=("Arial", 10, "bold")).grid(
            row=start_row, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5
        )

        # Temps de traitement global / Global processing time
        time_frame = ttk.Frame(parent)
        time_frame.grid(row=start_row+1, column=0, columnspan=3, sticky=tk.W, padx=20)
        ttk.Label(time_frame, text=tr('processing_time_label')).pack(side=tk.LEFT, padx=5)
        self.global_processing_time_var = tk.StringVar()
        ttk.Entry(time_frame, textvariable=self.global_processing_time_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(time_frame, text=TimeConverter.get_unit_symbol(self.current_time_unit)).pack(side=tk.LEFT)
        
        # Mode de traitement global / Global processing mode
        mode_frame = ttk.Frame(parent)
        mode_frame.grid(row=start_row+2, column=0, columnspan=3, sticky=tk.W, padx=20)
        ttk.Label(mode_frame, text=tr('mode_label')).pack(side=tk.LEFT, padx=5)
        from models.flow_model import ProcessingTimeMode
        self.global_processing_mode_var = tk.StringVar()
        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.global_processing_mode_var,
            values=[mode.name for mode in ProcessingTimeMode],
            state="readonly",
            width=20
        )
        mode_combo.pack(side=tk.LEFT, padx=5)
        mode_combo.bind('<<ComboboxSelected>>', lambda e: self._on_global_processing_mode_change())
        
        # Bouton d'édition graphique / Graphical edit button
        ttk.Button(
            mode_frame,
            text=tr('edit_graphically'),
            command=self._open_global_processing_distribution_editor
        ).pack(side=tk.LEFT, padx=10)
        
        # Écart-type global (pour mode NORMAL)
        # Global standard deviation (for NORMAL mode)
        self.global_std_dev_frame = ttk.Frame(parent)
        self.global_std_dev_frame.grid(row=start_row+3, column=0, columnspan=3, sticky=tk.W, padx=20)
        self.global_std_dev_frame.grid_remove()
        ttk.Label(self.global_std_dev_frame, text=tr('std_dev_label')).pack(side=tk.LEFT, padx=5)
        self.global_std_dev_var = tk.StringVar()
        ttk.Entry(self.global_std_dev_frame, textvariable=self.global_std_dev_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.global_std_dev_frame, text=TimeConverter.get_unit_symbol(self.current_time_unit)).pack(side=tk.LEFT)

        # Asymétrie globale (pour mode SKEW_NORMAL)
        # Global skewness (for SKEW_NORMAL mode)
        self.global_skewness_frame = ttk.Frame(parent)
        self.global_skewness_frame.grid(row=start_row+4, column=0, columnspan=3, sticky=tk.W, padx=20)
        self.global_skewness_frame.grid_remove()
        ttk.Label(self.global_skewness_frame, text=tr('skewness_label') + " (α):").pack(side=tk.LEFT, padx=5)
        self.global_skewness_var = tk.StringVar()
        ttk.Entry(self.global_skewness_frame, textvariable=self.global_skewness_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.global_skewness_frame, text="(-10 / 10)").pack(side=tk.LEFT)
        
        # Séparateur / Separator
        self.type_separator = ttk.Separator(parent, orient=tk.HORIZONTAL)
        self.type_separator.grid(
            row=start_row+5, column=0, columnspan=3, sticky="ew", padx=20, pady=10
        )
        
        # En-tête pour configuration par type / Header for per-type configuration
        self.type_section_label = ttk.Label(parent, text=tr('processing_by_type'), font=("Arial", 10, "bold"))
        self.type_section_label.grid(
            row=start_row+6, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5
        )

        # Bouton pour rafraîchir la liste des types (en dehors du tableau)
        # Button to refresh type list (outside the table)
        self.type_refresh_btn = ttk.Button(
            parent,
            text=tr('refresh_types'),
            command=self._refresh_type_processing_config
        )
        self.type_refresh_btn.grid(row=start_row+7, column=0, columnspan=3, sticky="ew", padx=20, pady=5)

        # Frame scrollable pour la configuration par type
        # Scrollable frame for per-type configuration
        self.type_config_frame = ttk.LabelFrame(parent, text=tr('types_config'), padding="5")
        self.type_config_frame.grid(row=start_row+8, column=0, columnspan=3, sticky="nsew", padx=20, pady=5)
        
        # Canvas avec scrollbar pour les types (hauteur initiale, sera ajustée dynamiquement)
        # Canvas with scrollbar for types (initial height, will be adjusted dynamically)
        self.type_canvas = tk.Canvas(self.type_config_frame, height=200, highlightthickness=0)
        type_scrollbar = ttk.Scrollbar(self.type_config_frame, orient="vertical", command=self.type_canvas.yview)
        self.type_items_frame = ttk.Frame(self.type_canvas)
        
        self.type_items_frame.bind(
            "<Configure>",
            lambda e: self.type_canvas.configure(scrollregion=self.type_canvas.bbox("all"))
        )
        
        self.type_canvas.create_window((0, 0), window=self.type_items_frame, anchor="nw")
        self.type_canvas.configure(yscrollcommand=type_scrollbar.set)
        
        self.type_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        type_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurer le frame interne pour qu'il s'étende
        # Configure inner frame to expand
        self.type_items_frame.columnconfigure(0, weight=1)
        
        # Dictionnaires pour stocker les variables
        # Dictionaries to store variables
        self.type_processing_time_vars = {}
        self.type_processing_mode_vars = {}
        self.type_std_dev_vars = {}
        self.type_skewness_vars = {}
        self.type_output_multiplier_vars = {}
        self.type_output_type_vars = {}
    
    def _create_splitter_config(self, parent, start_row):
        """Crée la section de configuration pour les diviseurs (splitters) / Create configuration section for splitters"""
        ttk.Label(parent, text=tr('distribution_mode_label'), font=("Arial", 10, "bold")).grid(
            row=start_row, column=0, sticky=tk.W, pady=5
        )
        
        mode_frame = ttk.Frame(parent)
        mode_frame.grid(row=start_row+1, column=0, columnspan=3, sticky=tk.W, padx=20)
        
        from models.flow_model import SplitterMode, FirstAvailableMode
        self.splitter_mode_var = tk.StringVar()
        self.splitter_mode_var.trace('w', self._on_splitter_mode_change)
        
        # Mapping entre enum et clés de traduction / Mapping between enum and translation keys
        splitter_mode_translations = {
            SplitterMode.ROUND_ROBIN: 'splitter_round_robin',
            SplitterMode.FIRST_AVAILABLE: 'splitter_first_available',
            SplitterMode.RANDOM: 'splitter_random'
        }
        
        for splitter_mode in SplitterMode:
            ttk.Radiobutton(
                mode_frame,
                text=tr(splitter_mode_translations[splitter_mode]),
                variable=self.splitter_mode_var,
                value=splitter_mode.name
            ).pack(anchor=tk.W, pady=2)
        
        ttk.Label(parent, text=tr('splitter_distributes_info'),
                 font=("Arial", 8, "italic"), foreground="#666").grid(
            row=start_row+2, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5
        )

        # Sous-options pour FIRST_AVAILABLE / Sub-options for FIRST_AVAILABLE
        self.first_available_frame = ttk.LabelFrame(parent, text=tr('first_available_options'), padding="5")
        self.first_available_frame.grid(row=start_row+3, column=0, columnspan=3, sticky=tk.EW, padx=20, pady=5)
        
        # Mapping entre enum et clés de traduction / Mapping between enum and translation keys
        first_avail_mode_translations = {
            FirstAvailableMode.BY_BUFFER: 'first_avail_by_buffer',
            FirstAvailableMode.BY_NODE_STATE: 'first_avail_by_node_state'
        }
        
        self.first_available_mode_var = tk.StringVar()
        for fav_mode in FirstAvailableMode:
            ttk.Radiobutton(
                self.first_available_frame,
                text=tr(first_avail_mode_translations[fav_mode]),
                variable=self.first_available_mode_var,
                value=fav_mode.name
            ).pack(anchor=tk.W, pady=2, padx=10)
        
        # Cacher par défaut / Hidden by default
        self.first_available_frame.grid_remove()
    
    def _on_splitter_mode_change(self, *args):
        """Afficher/cacher les options FirstAvailableMode selon le mode sélectionné / Show/hide FirstAvailableMode options based on selected mode"""
        if hasattr(self, 'first_available_frame') and hasattr(self, 'splitter_mode_var'):
            from models.flow_model import SplitterMode
            if self.splitter_mode_var.get() == SplitterMode.FIRST_AVAILABLE.name:
                self.first_available_frame.grid()
            else:
                self.first_available_frame.grid_remove()
    
    def _create_merger_config(self, parent, start_row):
        """Crée la section de configuration pour les concatenateurs (mergers) / Create configuration section for mergers"""
        ttk.Label(parent, text=tr('fifo_mode_label'), font=("Arial", 10, "bold")).grid(
            row=start_row, column=0, sticky=tk.W, pady=5
        )
        
        ttk.Label(parent, text=tr('merger_info'),
                 font=("Arial", 9), foreground="#333").grid(
            row=start_row+1, column=0, columnspan=3, sticky=tk.W, padx=20, pady=5
        )
        
        ttk.Label(parent, text=tr('fifo_auto'),
                 font=("Arial", 8, "italic"), foreground="#666").grid(
            row=start_row+2, column=0, columnspan=3, sticky=tk.W, padx=20
        )
    
    def _load_node_data(self):
        """Charge les données du nœud dans le formulaire / Load node data into form"""
        # Nom / Name
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.node.name)
        
        # Temps de traitement ou intervalle de génération
        # Processing time or generation interval
        if self.node.is_source:
            # Mode de génération / Generation mode
            if hasattr(self, 'source_mode_var'):
                from models.flow_model import SourceMode
                mode = getattr(self.node, 'source_mode', SourceMode.CONSTANT)
                self.source_mode_var.set(mode.name)
                self._on_source_mode_change()
            
            # Nombre d'items / Number of items
            self.max_items_var.set(str(self.node.max_items_to_generate))
            
            # Taille des lots / Batch size
            self.batch_size_var.set(str(self.node.batch_size))
            
            generation_interval = self.node.get_generation_interval(self.current_time_unit)
            self.generation_interval_var.set(f"{generation_interval:.2f}")
            
            # Paramètres spécifiques / Specific parameters
            if hasattr(self, 'generation_stddev_var'):
                generation_std_dev = self.node.get_generation_std_dev(self.current_time_unit)
                self.generation_stddev_var.set(f"{generation_std_dev:.2f}")
            if hasattr(self, 'generation_skewness_var'):
                skewness = getattr(self.node, 'generation_skewness', 0.0)
                self.generation_skewness_var.set(f"{skewness:.2f}")
            
            # Charger la configuration des types d'items
            # Load item types configuration
            if hasattr(self, 'item_gen_mode_var') and hasattr(self.node, 'item_type_config') and self.node.item_type_config:
                from models.item_type import ItemGenerationMode
                
                # MISE À JOUR AUTOMATIQUE: Synchroniser item_types avec la configuration actuelle
                # AUTOMATIC UPDATE: Sync item_types with current configuration
                self._update_source_item_types_from_config()
                
                # Mode de génération - utiliser la traduction
                # Generation mode - use translation
                mode_name = self.node.item_type_config.generation_mode.name
                self.item_gen_mode_var.set(tr(ITEM_GEN_MODE_TRANSLATIONS[mode_name]))
                
                # Peupler les combobox de types avec TOUS les types définis globalement
                # Populate type comboboxes with ALL globally defined types
                all_global_types = self._detect_incoming_item_types()
                type_list = [f"{t.name} (ID: {t.type_id})" for t in all_global_types]
                
                if hasattr(self, 'single_type_combo'):
                    self.single_type_combo['values'] = type_list
                    # Sélectionner le type actuel pour SINGLE_TYPE
                    # Select current type for SINGLE_TYPE
                    if self.node.item_type_config.generation_mode == ItemGenerationMode.SINGLE_TYPE:
                        if self.node.item_type_config.single_type_id:
                            # Trouver le type / Find the type
                            for t in all_global_types:
                                if str(t.type_id) == str(self.node.item_type_config.single_type_id):
                                    self.single_type_combo.set(f"{t.name} (ID: {t.type_id})")
                                    break
                
                if hasattr(self, 'sequence_combo'):
                    self.sequence_combo['values'] = type_list
                
                # Loop de séquence / Sequence loop
                if hasattr(self, 'sequence_loop_var'):
                    self.sequence_loop_var.set(self.node.item_type_config.sequence_loop)
                
                # Rafraîchir tous les affichages / Refresh all displays
                self._refresh_sequence()
                self._refresh_finite_quantities()
                self._refresh_infinite_proportions()
                
                # Déclencher l'affichage du bon frame / Trigger correct frame display
                self._on_item_gen_mode_change()
        elif self.node.is_splitter:
            # Mode du splitter / Splitter mode
            if hasattr(self, 'splitter_mode_var'):
                self.splitter_mode_var.set(self.node.splitter_mode.name)
            # Sous-mode first_available / First_available sub-mode
            if hasattr(self, 'first_available_mode_var'):
                self.first_available_mode_var.set(self.node.first_available_mode.name)
            # Afficher/cacher les options FirstAvailableMode
            # Show/hide FirstAvailableMode options
            self._on_splitter_mode_change()
        elif not self.node.is_merger:
            # Charger les valeurs globales de traitement
            # Load global processing values
            if hasattr(self, 'global_processing_time_var'):
                time_value = TimeConverter.from_centiseconds(self.node.processing_time_cs, self.current_time_unit)
                self.global_processing_time_var.set(f"{time_value:.2f}")
            
            if hasattr(self, 'global_processing_mode_var'):
                from models.flow_model import ProcessingTimeMode
                mode = getattr(self.node, 'processing_time_mode', ProcessingTimeMode.CONSTANT)
                self.global_processing_mode_var.set(mode.name)
                self._on_global_processing_mode_change()
            
            if hasattr(self, 'global_std_dev_var'):
                std_dev_cs = getattr(self.node, 'processing_time_std_dev_cs', 0.0)
                std_dev = TimeConverter.from_centiseconds(std_dev_cs, self.current_time_unit)
                self.global_std_dev_var.set(f"{std_dev:.2f}")
            
            if hasattr(self, 'global_skewness_var'):
                skewness = getattr(self.node, 'processing_time_skewness', 0.0)
                self.global_skewness_var.set(f"{skewness:.2f}")
            
            # Rafraîchir la configuration par type / Refresh per-type configuration
            if hasattr(self, '_refresh_type_processing_config'):
                self._refresh_type_processing_config()
        
        # Mode de synchronisation (uniquement pour nœuds non-sources, non-splitters, non-mergers)
        # Sync mode (only for non-source, non-splitter, non-merger nodes)
        if not self.node.is_source and not self.node.is_splitter and not self.node.is_merger:
            self.sync_mode_var.set(self.node.sync_mode.name)
            
            # Mode de priorité pour FIRST_AVAILABLE / Priority mode for FIRST_AVAILABLE
            from models.flow_model import FirstAvailablePriority
            if hasattr(self.node, 'first_available_priority'):
                self.first_available_priority_var.set(self.node.first_available_priority.name)
            else:
                self.first_available_priority_var.set(FirstAvailablePriority.ORDER.name)
            
            # Charger le mode de combinaison depuis le nœud
            # Load combination mode from node
            if hasattr(self, 'combination_mode_var'):
                if hasattr(self.node, 'use_combinations') and self.node.use_combinations:
                    self.combination_mode_var.set("combinations")
                else:
                    self.combination_mode_var.set("legacy")
                
                # Mettre à jour l'affichage / Update display
                self._on_combination_mode_changed()
                self._update_combinations_info()
            
            # Configuration des branches / Branch configuration
            self._setup_branch_config()
            self._on_sync_mode_change()
    
    def _on_source_mode_change(self):
        """Affiche/masque les paramètres selon le mode source / Show/hide parameters based on source mode"""
        from models.flow_model import SourceMode
        if not hasattr(self, 'source_mode_var'):
            return
        
        mode = self.source_mode_var.get()
        
        # Cacher tous les frames spécifiques / Hide all specific frames
        if hasattr(self, 'gen_std_dev_frame'):
            self.gen_std_dev_frame.grid_remove()
        if hasattr(self, 'gen_skewness_frame'):
            self.gen_skewness_frame.grid_remove()
        
        # Afficher le frame approprié / Show appropriate frame
        if mode == SourceMode.NORMAL.name:
            if hasattr(self, 'gen_std_dev_frame'):
                self.gen_std_dev_frame.grid()
        elif mode == SourceMode.SKEW_NORMAL.name:
            if hasattr(self, 'gen_std_dev_frame'):
                self.gen_std_dev_frame.grid()
            if hasattr(self, 'gen_skewness_frame'):
                self.gen_skewness_frame.grid()
    
    def _on_global_processing_mode_change(self):
        """Affiche/masque les paramètres selon le mode de traitement global / Show/hide parameters based on global processing mode"""
        from models.flow_model import ProcessingTimeMode
        if not hasattr(self, 'global_processing_mode_var'):
            return
        
        mode = self.global_processing_mode_var.get()
        
        # Cacher tous les frames spécifiques / Hide all specific frames
        if hasattr(self, 'global_std_dev_frame'):
            self.global_std_dev_frame.grid_remove()
        if hasattr(self, 'global_skewness_frame'):
            self.global_skewness_frame.grid_remove()
        
        # Afficher le frame approprié / Show appropriate frame
        if mode == ProcessingTimeMode.NORMAL.name:
            if hasattr(self, 'global_std_dev_frame'):
                self.global_std_dev_frame.grid()
        elif mode == ProcessingTimeMode.SKEW_NORMAL.name:
            if hasattr(self, 'global_std_dev_frame'):
                self.global_std_dev_frame.grid()
            if hasattr(self, 'global_skewness_frame'):
                self.global_skewness_frame.grid()
    
    def _open_source_distribution_editor(self):
        """Ouvre l'éditeur graphique de distribution pour la source
        
        Opens graphical distribution editor for the source"""
        from gui.distribution_editor_dialog import DistributionEditorDialog
        from models.flow_model import SourceMode
        
        # Récupérer les valeurs actuelles
        mean = float(self.generation_interval_var.get()) if self.generation_interval_var.get() else 10.0
        std = float(self.generation_stddev_var.get()) if self.generation_stddev_var.get() else 2.0
        skewness = float(self.generation_skewness_var.get()) if self.generation_skewness_var.get() else 0.0
        
        # Déterminer le type de distribution
        mode = self.source_mode_var.get()
        if mode == SourceMode.SKEW_NORMAL.name:
            dist_type = 'SKEW_NORMAL'
        else:
            dist_type = 'NORMAL'
        
        # Callback pour appliquer les changements
        def on_apply(new_mean, new_std, new_skewness):
            self.generation_interval_var.set(f"{new_mean:.2f}")
            self.generation_stddev_var.set(f"{new_std:.2f}")
            if hasattr(self, 'generation_skewness_var'):
                self.generation_skewness_var.set(f"{new_skewness:.2f}")
            
            # Sauvegarder automatiquement
            if self.on_save_callback:
                self.on_save_callback(self.node)
        
        # Ouvrir le dialogue
        dialog = DistributionEditorDialog(
            self,
            initial_mean=mean,
            initial_std=std,
            initial_skewness=skewness,
            distribution_type=dist_type,
            callback=on_apply
        )
        dialog.wait_window()
    
    def _open_global_processing_distribution_editor(self):
        """Ouvre l'éditeur graphique de distribution pour le temps de traitement global
        
        Opens graphical distribution editor for global processing time"""
        from gui.distribution_editor_dialog import DistributionEditorDialog
        from models.flow_model import ProcessingTimeMode
        
        # Récupérer les valeurs actuelles
        mean = float(self.global_processing_time_var.get()) if self.global_processing_time_var.get() else 1.0
        std = float(self.global_std_dev_var.get()) if self.global_std_dev_var.get() else 0.0
        skewness = float(self.global_skewness_var.get()) if self.global_skewness_var.get() else 0.0
        
        # Déterminer le type de distribution
        mode = self.global_processing_mode_var.get()
        if mode == ProcessingTimeMode.SKEW_NORMAL.name:
            dist_type = 'SKEW_NORMAL'
        elif mode == ProcessingTimeMode.NORMAL.name:
            dist_type = 'NORMAL'
        else:
            dist_type = 'CONSTANT'
        
        # Callback pour appliquer les changements
        def on_apply(new_mean, new_std, new_skewness):
            self.global_processing_time_var.set(f"{new_mean:.2f}")
            self.global_std_dev_var.set(f"{new_std:.2f}")
            self.global_skewness_var.set(f"{new_skewness:.2f}")
            
            # Mettre à jour le mode si nécessaire
            if new_std > 0 and new_skewness != 0:
                self.global_processing_mode_var.set(ProcessingTimeMode.SKEW_NORMAL.name)
            elif new_std > 0:
                self.global_processing_mode_var.set(ProcessingTimeMode.NORMAL.name)
            else:
                self.global_processing_mode_var.set(ProcessingTimeMode.CONSTANT.name)
            
            # Mettre à jour l'affichage des frames
            self._on_global_processing_mode_change()
            
            # Sauvegarder automatiquement
            if self.on_save_callback:
                self.on_save_callback(self.node)
        
        # Ouvrir le dialogue
        dialog = DistributionEditorDialog(
            self,
            initial_mean=mean,
            initial_std=std,
            initial_skewness=skewness,
            distribution_type=dist_type,
            callback=on_apply
        )
        dialog.wait_window()
    def _on_item_gen_mode_change(self, *args):
        """Affiche/masque les frames selon le mode de génération d'items"""
        from models.item_type import ItemGenerationMode
        
        if not hasattr(self, 'item_gen_mode_var'):
            return
        
        # Récupérer le mode à partir de la valeur traduite
        mode_value = self.item_gen_mode_var.get()
        mode = None
        
        # Trouver le mode correspondant à la traduction sélectionnée
        for m in ItemGenerationMode:
            translated_value = tr(ITEM_GEN_MODE_TRANSLATIONS[m.name])
            if translated_value == mode_value:
                mode = m
                break
        
        if mode is None:
            return
        
        # Cacher tous les frames
        if hasattr(self, 'single_type_frame'):
            self.single_type_frame.grid_remove()
        if hasattr(self, 'sequence_frame'):
            self.sequence_frame.grid_remove()
        if hasattr(self, 'random_finite_frame'):
            self.random_finite_frame.grid_remove()
        if hasattr(self, 'random_infinite_frame'):
            self.random_infinite_frame.grid_remove()
        
        # Afficher le frame approprié
        if mode == ItemGenerationMode.SINGLE_TYPE:
            if hasattr(self, 'single_type_frame'):
                self.single_type_frame.grid()
        elif mode == ItemGenerationMode.SEQUENCE:
            if hasattr(self, 'sequence_frame'):
                self.sequence_frame.grid()
                self._refresh_sequence()
        elif mode == ItemGenerationMode.RANDOM_FINITE:
            if hasattr(self, 'random_finite_frame'):
                self.random_finite_frame.grid()
                self._refresh_finite_quantities()
                # Mettre à jour le nombre d'items automatiquement
                self._update_max_items_from_finite()
        elif mode == ItemGenerationMode.RANDOM_INFINITE:
            if hasattr(self, 'random_infinite_frame'):
                self.random_infinite_frame.grid()
                self._refresh_infinite_proportions()
                # Mettre le nombre d'items à 0 (infini)
                if hasattr(self, 'max_items_var'):
                    self.max_items_var.set('0')
                self._refresh_infinite_proportions()
    
    def _refresh_sequence(self):
        """Rafraîchit l'affichage de la séquence
        
        Refreshes sequence display"""
        if not hasattr(self, 'sequence_listbox'):
            return
        
        self.sequence_listbox.delete(0, tk.END)
        
        if hasattr(self.node, 'item_type_config') and self.node.item_type_config:
            # Récupérer tous les types globaux pour trouver les noms
            all_global_types = self._detect_incoming_item_types()
            
            for type_id in self.node.item_type_config.sequence:
                # Trouver le type correspondant dans les types globaux
                item_type = None
                for t in all_global_types:
                    if str(t.type_id) == str(type_id):
                        item_type = t
                        break
                
                if item_type:
                    self.sequence_listbox.insert(tk.END, f"{item_type.name} (ID: {item_type.type_id})")
    
    def _add_to_sequence(self):
        """Ajoute un type à la séquence
        
        Adds a type to the sequence"""
        if not hasattr(self, 'sequence_combo'):
            return
        
        selection = self.sequence_combo.get()
        if not selection:
            messagebox.showwarning(tr('selection_required'), tr('please_select_item_type'))
            return
        
        # Extraire l'ID du type depuis la sélection (format: "Nom (ID: X)")
        import re
        match = re.search(r'\(ID:\s*(\w+)\)', selection)
        if not match:
            return
        
        type_id = match.group(1)
        
        # Ajouter à la séquence du modèle
        if hasattr(self.node, 'item_type_config') and self.node.item_type_config:
            self.node.item_type_config.sequence.append(type_id)
            self._refresh_sequence()
    
    def _remove_from_sequence(self):
        """Supprime un type de la séquence
        
        Removes a type from the sequence"""
        if not hasattr(self, 'sequence_listbox'):
            return
        
        selection = self.sequence_listbox.curselection()
        if not selection:
            messagebox.showwarning(tr('selection_required'), tr('please_select_sequence_item'))
            return
        
        index = selection[0]
        
        # Supprimer de la séquence du modèle
        if hasattr(self.node, 'item_type_config') and self.node.item_type_config:
            if 0 <= index < len(self.node.item_type_config.sequence):
                del self.node.item_type_config.sequence[index]
                self._refresh_sequence()
    
    def _move_sequence_up(self):
        """Déplace un type vers le haut dans la séquence
        
        Moves a type up in the sequence"""
        if not hasattr(self, 'sequence_listbox'):
            return
        
        selection = self.sequence_listbox.curselection()
        if not selection:
            messagebox.showwarning(tr('selection_required'), tr('please_select_sequence_item'))
            return
        
        index = selection[0]
        if index == 0:
            return  # Déjà en haut
        
        # Échanger dans la séquence du modèle
        if hasattr(self.node, 'item_type_config') and self.node.item_type_config:
            sequence = self.node.item_type_config.sequence
            sequence[index], sequence[index-1] = sequence[index-1], sequence[index]
            self._refresh_sequence()
            self.sequence_listbox.selection_set(index-1)
    
    def _move_sequence_down(self):
        """Déplace un type vers le bas dans la séquence
        
        Moves a type down in the sequence"""
        if not hasattr(self, 'sequence_listbox'):
            return
        
        selection = self.sequence_listbox.curselection()
        if not selection:
            messagebox.showwarning(tr('selection_required'), tr('please_select_sequence_item'))
            return
        
        index = selection[0]
        
        # Vérifier si on peut descendre
        if hasattr(self.node, 'item_type_config') and self.node.item_type_config:
            sequence = self.node.item_type_config.sequence
            if index >= len(sequence) - 1:
                return  # Déjà en bas
            
            # Échanger dans la séquence du modèle
            sequence[index], sequence[index+1] = sequence[index+1], sequence[index]
            self._refresh_sequence()
            self.sequence_listbox.selection_set(index+1)
    
    def _refresh_finite_quantities(self):
        """Rafraîchit l'affichage des quantités finies
        
        Refreshes finite quantities display"""
        if not hasattr(self, 'finite_quantities_frame'):
            return
        
        # Effacer les widgets existants
        for widget in self.finite_quantities_frame.winfo_children():
            widget.destroy()
        
        self.finite_quantity_vars.clear()
        
        if not hasattr(self.node, 'item_type_config') or not self.node.item_type_config:
            return
        
        # Utiliser tous les types globaux
        all_global_types = self._detect_incoming_item_types()
        
        # Créer une ligne par type
        for i, item_type in enumerate(all_global_types):
            frame = ttk.Frame(self.finite_quantities_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # Nom du type avec couleur
            label = ttk.Label(frame, text=f"{item_type.name}:", width=20)
            label.pack(side=tk.LEFT, padx=5)
            
            # Entrée pour la quantité
            var = tk.StringVar()
            current_count = self.node.item_type_config.finite_counts.get(item_type.type_id, 0)
            var.set(str(current_count))
            
            # Callback pour mise à jour automatique du total
            var.trace_add('write', lambda *args: self._update_max_items_from_finite())
            
            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            
            ttk.Label(frame, text=tr('units_text')).pack(side=tk.LEFT)
            
            self.finite_quantity_vars[item_type.type_id] = var
    
    def _update_max_items_from_finite(self):
        """Met à jour le nombre total d'items basé sur les quantités finies / Update total items count based on finite quantities"""
        if not hasattr(self, 'finite_quantity_vars') or not hasattr(self, 'max_items_var'):
            return
        
        total = 0
        for var in self.finite_quantity_vars.values():
            try:
                value = int(var.get())
                if value > 0:
                    total += value
            except ValueError:
                pass  # Ignorer les valeurs non numériques / Ignore non-numeric values
        
        self.max_items_var.set(str(total))
    
    def _refresh_infinite_proportions(self):
        """Rafraîchit l'affichage des proportions infinies / Refresh infinite proportions display"""
        if not hasattr(self, 'infinite_proportions_frame'):
            return
        
        # Effacer les widgets existants / Clear existing widgets
        for widget in self.infinite_proportions_frame.winfo_children():
            widget.destroy()
        
        self.infinite_proportion_vars.clear()
        
        if not hasattr(self.node, 'item_type_config') or not self.node.item_type_config:
            return
        
        # Utiliser tous les types globaux / Use all global types
        all_global_types = self._detect_incoming_item_types()
        
        # Créer une ligne par type / Create one row per type
        for i, item_type in enumerate(all_global_types):
            frame = ttk.Frame(self.infinite_proportions_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # Nom du type / Type name
            label = ttk.Label(frame, text=f"{item_type.name}:", width=20)
            label.pack(side=tk.LEFT, padx=5)
            
            # Entrée pour la proportion en pourcentage
            # Entry for proportion as percentage
            var = tk.StringVar()
            current_prop = self.node.item_type_config.proportions.get(item_type.type_id, 0.0)
            # Convertir en pourcentage / Convert to percentage
            var.set(f"{current_prop * 100:.1f}")
            
            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            
            ttk.Label(frame, text="%").pack(side=tk.LEFT)
            
            # Ajouter un callback pour mettre à jour la somme
            # Add callback to update sum
            var.trace_add('write', lambda *args: self._update_proportion_sum())
            
            self.infinite_proportion_vars[item_type.type_id] = var
        
        # Frame pour afficher la somme / Frame to display sum
        sum_frame = ttk.Frame(self.infinite_proportions_frame)
        sum_frame.pack(fill=tk.X, pady=10)
        
        separator = ttk.Separator(sum_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=5)
        
        sum_display_frame = ttk.Frame(sum_frame)
        sum_display_frame.pack(fill=tk.X)
        
        ttk.Label(sum_display_frame, text=tr('total_label'), font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.proportion_sum_label = ttk.Label(sum_display_frame, text="0.0 %", font=("Arial", 9, "bold"))
        self.proportion_sum_label.pack(side=tk.LEFT, padx=5)
        
        self.proportion_status_label = ttk.Label(sum_display_frame, text="", font=("Arial", 8))
        self.proportion_status_label.pack(side=tk.LEFT, padx=10)
        
        # Mettre à jour la somme initiale / Update initial sum
        self._update_proportion_sum()
    
    def _update_proportion_sum(self):
        """Met à jour l'affichage de la somme des proportions / Update proportion sum display"""
        if not hasattr(self, 'proportion_sum_label'):
            return
        
        total = 0.0
        for var in self.infinite_proportion_vars.values():
            try:
                value = float(var.get())
                total += value
            except ValueError:
                pass
        
        # Afficher la somme / Display sum
        self.proportion_sum_label.config(text=f"{total:.1f} %")
        
        # Afficher un indicateur de statut / Display status indicator
        if abs(total - 100.0) < 0.1:  # Tolérance de 0.1% / 0.1% tolerance
            self.proportion_status_label.config(text="✓ OK", foreground="green")
        else:
            self.proportion_status_label.config(text=tr('must_be_100_pct'), foreground="orange")
    
    def _get_actually_generated_types(self, source_node):
        """
        Retourne uniquement les types RÉELLEMENT générés par une source selon sa configuration.
        Différent de item_types qui contient TOUS les types globaux (Option A).
        Returns only types ACTUALLY generated by a source based on its configuration.
        Different from item_types which contains ALL global types (Option A).
        """
        if not source_node.is_source or not hasattr(source_node, 'item_type_config') or not source_node.item_type_config:
            return []
        
        from models.item_type import ItemGenerationMode
        generated_types = []
        all_available = source_node.item_type_config.item_types
        
        # Type unique : seulement celui sélectionné / Single type: only the selected one
        if source_node.item_type_config.generation_mode == ItemGenerationMode.SINGLE_TYPE:
            if source_node.item_type_config.single_type_id:
                for t in all_available:
                    if str(t.type_id) == str(source_node.item_type_config.single_type_id):
                        return [t]
        
        # Séquence : tous les types dans la séquence / Sequence: all types in sequence
        elif source_node.item_type_config.generation_mode == ItemGenerationMode.SEQUENCE:
            if source_node.item_type_config.sequence:
                for type_id in source_node.item_type_config.sequence:
                    for t in all_available:
                        if str(t.type_id) == str(type_id):
                            if t not in generated_types:
                                generated_types.append(t)
                            break
        
        # Quantités finies : types avec quantités > 0 / Finite quantities: types with qty > 0
        elif source_node.item_type_config.generation_mode == ItemGenerationMode.RANDOM_FINITE:
            if source_node.item_type_config.finite_counts:
                for type_id in source_node.item_type_config.finite_counts.keys():
                    for t in all_available:
                        if str(t.type_id) == str(type_id):
                            if t not in generated_types:
                                generated_types.append(t)
                            break
        
        # Proportions infinies : types avec proportions > 0 / Infinite proportions: types with prop > 0
        elif source_node.item_type_config.generation_mode == ItemGenerationMode.RANDOM_INFINITE:
            if source_node.item_type_config.proportions:
                for type_id in source_node.item_type_config.proportions.keys():
                    for t in all_available:
                        if str(t.type_id) == str(type_id):
                            if t not in generated_types:
                                generated_types.append(t)
                            break
        
        return generated_types
    
    def _sync_source_item_types(self, source_node):
        """
        Synchronise item_types d'une source avec sa configuration actuelle.
        OPTION A : Conserve TOUS les types globaux + ajoute les types configurés.
        Les types définis globalement restent disponibles même s'ils ne sont pas utilisés.
        Synchronize item_types of a source with its current configuration.
        OPTION A: Keep ALL global types + add configured types.
        Globally defined types remain available even if unused.
        """
        if not source_node.is_source or not hasattr(source_node, 'item_type_config') or not source_node.item_type_config:
            return
        
        from models.item_type import ItemGenerationMode
        
        # Récupérer tous les types globaux disponibles (liste maître)
        # Get all available global types (master list)
        all_global_types = []
        seen_ids = set()
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for t in node.item_type_config.item_types:
                    if t.type_id not in seen_ids:
                        all_global_types.append(t)
                        seen_ids.add(t.type_id)
        
        # GARDER tous les types globaux existants
        # KEEP all existing global types
        # La liste maître est all_global_types, ne jamais réduire cette liste
        # The master list is all_global_types, never reduce this list
        # On s'assure juste que la source contient tous ces types
        # We just ensure the source contains all these types
        
        if all_global_types:
            # Mettre à jour avec TOUS les types globaux (ne rien supprimer)
            # Update with ALL global types (don't delete anything)
            source_node.item_type_config.item_types = all_global_types.copy()
            # Note : On ne filtre PAS selon la configuration, on garde tout
            # Note: We do NOT filter based on configuration, we keep everything
    
    def _update_source_item_types_from_config(self):
        """
        Met à jour item_types de la source en fonction de sa configuration actuelle.
        OPTION A : Conserve TOUS les types globaux (ne supprime jamais).
        Update source item_types based on its current configuration.
        OPTION A: Keep ALL global types (never delete).
        """
        if not self.node.is_source or not hasattr(self.node, 'item_type_config') or not self.node.item_type_config:
            return
        
        # Utiliser la même logique que _sync_source_item_types
        # Use same logic as _sync_source_item_types
        # Garder tous les types globaux disponibles
        # Keep all available global types
        all_global_types = self._detect_incoming_item_types()
        
        if all_global_types:
            # GARDER tous les types globaux (ne jamais réduire)
            # KEEP all global types (never reduce)
            self.node.item_type_config.item_types = all_global_types.copy()
    
    def _get_all_available_item_types(self):
        """
        Récupère TOUS les types d'items disponibles globalement depuis toutes les sources
        ET tous les types définis comme sortie dans les nœuds de traitement.
        Utilisé pour permettre la définition de nouveaux types de sortie.
        Get ALL globally available item types from all sources
        AND all types defined as output in processing nodes.
        Used to allow definition of new output types.
        """
        all_types = []
        seen_type_ids = set()
        
        # 1. Parcourir toutes les sources pour collecter tous les types déclarés
        # 1. Traverse all sources to collect all declared types
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    if item_type.type_id not in seen_type_ids:
                        all_types.append(item_type)
                        seen_type_ids.add(item_type.type_id)
        
        # 2. Parcourir tous les nœuds de traitement pour collecter les types de sortie
        # 2. Traverse all processing nodes to collect output types
        for node in self.flow_model.nodes.values():
            if not node.is_source and not node.is_sink and hasattr(node, 'processing_config') and node.processing_config:
                # Collecter les types de sortie depuis output_type_mapping
                # Collect output types from output_type_mapping
                for output_type_id in node.processing_config.output_type_mapping.values():
                    if output_type_id not in seen_type_ids:
                        # Chercher le type dans item_type_config du nœud
                        # Look for the type in the node's item_type_config
                        if hasattr(node, 'item_type_config') and node.item_type_config:
                            for item_type in node.item_type_config.item_types:
                                if str(item_type.type_id) == str(output_type_id) and item_type.type_id not in seen_type_ids:
                                    all_types.append(item_type)
                                    seen_type_ids.add(item_type.type_id)
        
        return all_types
    
    def _detect_incoming_item_types(self):
        """
        Détecte les types d'items pertinents selon le type de nœud :
        - FLUX ENTRANT (Source) : tous les types définis globalement
        - NŒUD DE TRAITEMENT : uniquement les types arrivant via les connexions entrantes
        Detect relevant item types based on node type:
        - INPUT FLOW (Source): all globally defined types
        - PROCESSING NODE: only types arriving via incoming connections
        """
        all_types = []
        seen_type_ids = set()
        
        # FLUX ENTRANT : récupérer tous les types globaux
        # INPUT FLOW: get all global types
        if self.node.is_source:
            if False:
                print(f"[DEBUG] Détection pour SOURCE: {self.node.name} (ID: {self.node.node_id})")
            for node in self.flow_model.nodes.values():
                if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                    # Mettre à jour automatiquement item_types de cette source basé sur sa config
                    # Automatically update item_types of this source based on its config
                    self._sync_source_item_types(node)
                    if False:
                        print(f"  └─ Source trouvée: {node.name} (ID: {node.node_id}), types: {[t.name for t in node.item_type_config.item_types]}")
                    for item_type in node.item_type_config.item_types:
                        if item_type.type_id not in seen_type_ids:
                            all_types.append(item_type)
                            seen_type_ids.add(item_type.type_id)
            if False:
                print(f"  └─ RÉSULTAT: {len(all_types)} types détectés: {[t.name for t in all_types]}")
            return all_types
        
        # NŒUD DE TRAITEMENT : analyser uniquement les connexions entrantes
        if False:
            print(f"[DEBUG] Détection pour NOEUD DE TRAITEMENT: {self.node.name} (ID: {self.node.node_id})")
        nodes_to_check = set()
        
        # Trouver tous les nœuds qui se connectent à ce nœud (connexions entrantes)
        for connection in self.flow_model.connections.values():
            if connection.target_id == self.node.node_id:
                # Ajouter le nœud source de cette connexion
                source_node = self.flow_model.nodes.get(connection.source_id)
                if source_node:
                    if False:
                        print(f"  └─ Connexion {connection.connection_id}: {source_node.name} (ID: {source_node.node_id}) → {self.node.name} (ID: {self.node.node_id})")
                    nodes_to_check.add(source_node)
        
        # Parcourir le graphe en remontant pour trouver toutes les sources
        visited = set()
        
        while nodes_to_check:
            current_node = nodes_to_check.pop()
            
            if current_node in visited:
                continue
            visited.add(current_node)
            
            # Si c'est une source, collecter ses types RÉELLEMENT GÉNÉRÉS
            if current_node.is_source and hasattr(current_node, 'item_type_config') and current_node.item_type_config:
                # Mettre à jour automatiquement item_types de cette source basé sur sa config
                self._sync_source_item_types(current_node)
                
                # Pour les nœuds de traitement, ne prendre que les types réellement générés
                # For processing nodes, only take actually generated types
                actually_generated = self._get_actually_generated_types(current_node)
                if False:
                    print(f"  └─ Source en amont trouvée: {current_node.name} (ID: {current_node.node_id}), types générés: {[t.name for t in actually_generated]}")
                
                for item_type in actually_generated:
                    if item_type.type_id not in seen_type_ids:
                        all_types.append(item_type)
                        seen_type_ids.add(item_type.type_id)
            else:
                # Si ce n'est pas une source, continuer à remonter
                # If not a source, continue going up
                # Chercher les nœuds qui se connectent à current_node
                # Find nodes that connect to current_node
                for connection in self.flow_model.connections.values():
                    if connection.target_id == current_node.node_id:
                        source_node = self.flow_model.nodes.get(connection.source_id)
                        if source_node:
                            nodes_to_check.add(source_node)
            
            # Pour les nœuds de traitement, prendre en compte les transformations de types
            # For processing nodes, take into account type transformations
            if hasattr(current_node, 'processing_config') and current_node.processing_config:
                # Si un nœud transforme des types, ajouter les types de sortie
                # If a node transforms types, add output types
                for type_id, output_type_id in current_node.processing_config.output_type_mapping.items():
                    # Trouver le type de sortie / Find output type
                    for item_type in all_types:
                        if str(item_type.type_id) == str(output_type_id):
                            # Le type est déjà dans la liste / Type is already in the list
                            break
                    else:
                        # Le type de sortie n'est pas encore dans la liste
                        # The output type is not yet in the list
                        # Il faut le chercher dans toutes les sources pour avoir l'objet ItemType complet
                        # Need to search all sources to get the complete ItemType object
                        for node in self.flow_model.nodes.values():
                            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                                for item_type in node.item_type_config.item_types:
                                    if str(item_type.type_id) == str(output_type_id) and item_type.type_id not in seen_type_ids:
                                        all_types.append(item_type)
                                        seen_type_ids.add(item_type.type_id)
                                        break
        
        if False:
            print(f"  └─ RÉSULTAT FINAL: {len(all_types)} types détectés: {[t.name for t in all_types]}")
        return all_types
    
    def _refresh_type_processing_config(self):
        """Rafraîchit l'affichage de la configuration de traitement par type / Refresh per-type processing config display"""
        if not hasattr(self, 'type_items_frame'):
            return
        
        # Effacer les widgets existants / Clear existing widgets
        for widget in self.type_items_frame.winfo_children():
            widget.destroy()
        
        self.type_processing_time_vars.clear()
        self.type_processing_mode_vars.clear()
        self.type_std_dev_vars.clear()
        self.type_skewness_vars.clear()
        self.type_output_multiplier_vars.clear()
        self.type_output_type_vars.clear()
        
        # Détecter automatiquement les types d'items arrivant dans ce nœud
        # Automatically detect item types arriving in this node
        all_types = self._detect_incoming_item_types()
        
        if not all_types:
            ttk.Label(
                self.type_items_frame,
                text=tr('no_type_detected'),
                font=("Arial", 9, "italic"),
                foreground="#666"
            ).pack(pady=10)
            return
        
        # Créer un header avec grid pour un alignement propre
        # Create header with grid for clean alignment
        header_frame = ttk.Frame(self.type_items_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Configurer les colonnes avec des largeurs uniformes
        # Configure columns with uniform widths
        header_frame.columnconfigure(0, minsize=100)  # Type
        header_frame.columnconfigure(1, minsize=70)   # Temps
        header_frame.columnconfigure(2, minsize=110)  # Mode
        header_frame.columnconfigure(3, minsize=70)   # Écart-type
        header_frame.columnconfigure(4, minsize=70)   # Asymétrie / Skewness
        header_frame.columnconfigure(5, minsize=80)   # Graphique / Graph
        header_frame.columnconfigure(6, minsize=70)   # Sortie / Output
        header_frame.columnconfigure(7, minsize=110)  # Type sortie / Output type
        
        ttk.Label(header_frame, text=tr('type_header'), font=("Arial", 9, "bold")).grid(row=0, column=0, padx=2, sticky=tk.W)
        ttk.Label(header_frame, text=tr('time_header'), font=("Arial", 9, "bold")).grid(row=0, column=1, padx=2)
        ttk.Label(header_frame, text=tr('mode_label'), font=("Arial", 9, "bold")).grid(row=0, column=2, padx=2)
        ttk.Label(header_frame, text=tr('std_dev_header'), font=("Arial", 9, "bold")).grid(row=0, column=3, padx=2)
        ttk.Label(header_frame, text=tr('skewness_header'), font=("Arial", 9, "bold")).grid(row=0, column=4, padx=2)
        ttk.Label(header_frame, text=tr('graph_header'), font=("Arial", 9, "bold")).grid(row=0, column=5, padx=2)
        ttk.Label(header_frame, text=tr('output_mult_header'), font=("Arial", 9, "bold")).grid(row=0, column=6, padx=2)
        ttk.Label(header_frame, text=tr('output_type_header'), font=("Arial", 9, "bold")).grid(row=0, column=7, padx=2)
        
        # Créer une ligne par type / Create one row per type
        for item_type in all_types:
            type_frame = ttk.Frame(self.type_items_frame)
            type_frame.pack(fill=tk.X, pady=2)
            
            # Configurer les colonnes avec les mêmes largeurs que les en-têtes
            # Configure columns with same widths as headers
            type_frame.columnconfigure(0, minsize=100)
            type_frame.columnconfigure(1, minsize=70)
            type_frame.columnconfigure(2, minsize=110)
            type_frame.columnconfigure(3, minsize=70)
            type_frame.columnconfigure(4, minsize=70)
            type_frame.columnconfigure(5, minsize=80)
            type_frame.columnconfigure(6, minsize=70)
            type_frame.columnconfigure(7, minsize=110)
            
            # Colonne 0: Indicateur de couleur + nom / Column 0: Color indicator + name
            name_frame = ttk.Frame(type_frame)
            name_frame.grid(row=0, column=0, padx=2, sticky=tk.W)
            
            color_canvas = tk.Canvas(name_frame, width=10, height=10, highlightthickness=0)
            color_canvas.pack(side=tk.LEFT, padx=(0, 3))
            color_canvas.create_rectangle(0, 0, 10, 10, fill=item_type.color, outline="#888")
            
            name_label = ttk.Label(name_frame, text=item_type.name, width=10)
            name_label.pack(side=tk.LEFT)
            
            # Colonne 1: Temps de traitement / Column 1: Processing time
            time_var = tk.StringVar()
            if hasattr(self.node, 'processing_config') and self.node.processing_config:
                time_cs = self.node.processing_config.processing_times_cs.get(item_type.type_id, self.node.processing_time_cs)
                time_value = TimeConverter.from_centiseconds(time_cs, self.current_time_unit)
                time_var.set(f"{time_value:.2f}")
            else:
                time_value = self.node.get_processing_time(self.current_time_unit)
                time_var.set(f"{time_value:.2f}")
            
            time_entry = ttk.Entry(type_frame, textvariable=time_var, width=8)
            time_entry.grid(row=0, column=1, padx=2)
            self.type_processing_time_vars[item_type.type_id] = time_var
            
            # Colonne 2: Mode de distribution / Column 2: Distribution mode
            mode_var = tk.StringVar()
            if hasattr(self.node, 'processing_config') and self.node.processing_config:
                mode_name = self.node.processing_config.processing_modes.get(item_type.type_id, "CONSTANT")
                mode_var.set(mode_name)
            else:
                mode_var.set("CONSTANT")
            
            mode_combo = ttk.Combobox(
                type_frame,
                textvariable=mode_var,
                values=["CONSTANT", "NORMAL", "SKEW_NORMAL"],
                state="readonly",
                width=10
            )
            mode_combo.grid(row=0, column=2, padx=2)
            mode_combo.bind('<<ComboboxSelected>>', lambda e, tid=item_type.type_id: self._on_type_mode_change(tid))
            self.type_processing_mode_vars[item_type.type_id] = mode_var
            
            # Colonne 3: Écart-type / Column 3: Standard deviation
            std_var = tk.StringVar()
            if hasattr(self.node, 'processing_config') and self.node.processing_config:
                std_cs = self.node.processing_config.std_devs_cs.get(item_type.type_id, 0.0)
                std_value = TimeConverter.from_centiseconds(std_cs, self.current_time_unit)
                std_var.set(f"{std_value:.2f}" if std_value > 0 else "")
            else:
                std_var.set("")
            
            std_entry = ttk.Entry(type_frame, textvariable=std_var, width=8)
            std_entry.grid(row=0, column=3, padx=2)
            self.type_std_dev_vars[item_type.type_id] = std_var
            
            # Colonne 4: Asymétrie / Column 4: Skewness
            skew_var = tk.StringVar()
            if hasattr(self.node, 'processing_config') and self.node.processing_config:
                skew_value = self.node.processing_config.skewnesses.get(item_type.type_id, 0.0)
                skew_var.set(f"{skew_value:.2f}" if skew_value != 0 else "")
            else:
                skew_var.set("")
            
            skew_entry = ttk.Entry(type_frame, textvariable=skew_var, width=8)
            skew_entry.grid(row=0, column=4, padx=2)
            self.type_skewness_vars[item_type.type_id] = skew_var
            
            # Colonne 5: Bouton graphique / Column 5: Graph button
            graph_btn = ttk.Button(
                type_frame,
                text="📊",
                width=3,
                command=lambda tid=item_type.type_id: self._open_type_distribution_editor(tid)
            )
            graph_btn.grid(row=0, column=5, padx=2)
            
            # Colonne 6: Multiplicateur de sortie / Column 6: Output multiplier
            output_var = tk.StringVar()
            output_var.set("1")  # Valeur par défaut / Default value
            
            output_entry = ttk.Entry(type_frame, textvariable=output_var, width=6)
            output_entry.grid(row=0, column=6, padx=2)
            self.type_output_multiplier_vars[item_type.type_id] = output_var
            
            # Colonne 7: Type de sortie (transformation) / Column 7: Output type (transformation)
            # Récupérer TOUS les types disponibles globalement (pas seulement ceux en entrée)
            # Get ALL globally available types (not just input ones)
            all_available_types = self._get_all_available_item_types()
            
            output_type_var = tk.StringVar()
            if hasattr(self.node, 'processing_config') and self.node.processing_config:
                output_type_id = self.node.processing_config.output_type_mapping.get(item_type.type_id, item_type.type_id)
            else:
                output_type_id = item_type.type_id
            
            # Créer la liste des types pour le combobox
            # Create type list for combobox
            type_names = [f"{t.name}" for t in all_available_types]
            
            output_combo = ttk.Combobox(type_frame, textvariable=output_type_var, values=type_names, state="readonly", width=12)
            output_combo.grid(row=0, column=7, padx=2)
            
            # Sélectionner le type actuel / Select current type
            for t in all_available_types:
                if str(t.type_id) == str(output_type_id):
                    output_type_var.set(t.name)
                    break
            
            # Stocker avec tous les types disponibles pour la sauvegarde
            # Store with all available types for saving
            self.type_output_type_vars[item_type.type_id] = (output_type_var, all_available_types, output_combo)
        
        # Messages d'information / Information messages
        info_frame = ttk.Frame(self.type_items_frame)
        info_frame.pack(pady=(10, 0), fill=tk.X)
              
        ttk.Label(
            info_frame,
            text=tr('output_types_info'),
            font=("Arial", 8, "italic"),
            foreground="#666"
        ).pack(anchor=tk.W, pady=2)
        
        # Ajuster dynamiquement la hauteur du canvas selon le nombre de types
        # Dynamically adjust canvas height based on number of types
        # 40px par ligne + 30px header + 50px padding, min 100px, max 300px
        # 40px per row + 30px header + 50px padding, min 100px, max 300px
        num_types = len(all_types)
        dynamic_height = max(100, min(20 * num_types + 80, 300))
        if hasattr(self, 'type_canvas'):
            self.type_canvas.config(height=dynamic_height)
    
    def _on_sync_mode_change(self):
        """Affiche/masque la configuration des branches selon le mode / Show/hide branch config based on mode"""
        sync_mode = SyncMode[self.sync_mode_var.get()]
        
        # Afficher/masquer la configuration de priorité pour FIRST_AVAILABLE
        # Show/hide priority config for FIRST_AVAILABLE
        if self.priority_config_frame is not None:
            if sync_mode == SyncMode.FIRST_AVAILABLE:
                self.priority_config_frame.grid()
            else:
                self.priority_config_frame.grid_remove()
        
        # Afficher/masquer la configuration des branches pour WAIT_N_FROM_BRANCH
        # Show/hide branch config for WAIT_N_FROM_BRANCH
        if self.branch_config_frame is not None:
            if sync_mode == SyncMode.WAIT_N_FROM_BRANCH:
                self.branch_config_frame.grid()
            else:
                self.branch_config_frame.grid_remove()
        
        # Afficher/masquer la section "Traitement par type d'item" selon le mode
        # Show/hide "Processing by item type" section based on mode
        # Cette section n'est pertinente que pour le mode FIRST_AVAILABLE
        # This section is only relevant for FIRST_AVAILABLE mode
        if hasattr(self, 'type_separator') and hasattr(self, 'type_section_label') and hasattr(self, 'type_refresh_btn') and hasattr(self, 'type_config_frame'):
            if sync_mode == SyncMode.FIRST_AVAILABLE:
                self.type_separator.grid()
                self.type_section_label.grid()
                self.type_refresh_btn.grid()
                self.type_config_frame.grid()
            else:
                self.type_separator.grid_remove()
                self.type_section_label.grid_remove()
                self.type_refresh_btn.grid_remove()
                self.type_config_frame.grid_remove()
    
    def _open_combination_set(self):
        """Ouvre le dialogue de configuration du ensemble de combinaisons / Open combination set configuration dialog"""
        from gui.combination_manager_dialog import CombinationManagerDialog
        CombinationManagerDialog(self, self.flow_model, self.node)
        # Rafraîchir l'info après la fermeture du dialogue / Refresh info after dialog closes
        self._update_combinations_info()
    
    def _on_combination_mode_changed(self):
        """Gère le changement de mode entre Combinaisons et Legacy / Handle mode change between Combinations and Legacy"""
        mode = self.combination_mode_var.get()
        
        if mode == "combinations":
            # Afficher le frame des combinaisons, masquer legacy
            # Show combinations frame, hide legacy
            self.combinations_mode_frame.pack(fill=tk.X, pady=5)
            self.legacy_mode_frame.pack_forget()
        else:
            # Afficher le frame legacy, masquer combinaisons
            # Show legacy frame, hide combinations
            self.legacy_mode_frame.pack(fill=tk.X, pady=5)
            self.combinations_mode_frame.pack_forget()
            # Initialiser toutes les quantités à 1 si elles n'existent pas
            # Initialize all quantities to 1 if they don't exist
            for conn_id in self.node.input_connections:
                if conn_id not in self.node.required_units:
                    self.node.required_units[conn_id] = 1
            # Rafraîchir l'affichage des entrées / Refresh input display
            self._setup_branch_config()
    
    def _update_combinations_info(self):
        """Met à jour l'affichage d'information sur les combinaisons configurées / Update display info about configured combinations"""
        if not hasattr(self, 'combinations_info_label'):
            return
        
        count = len(self.node.combination_set)
        if count == 0:
            self.combinations_info_label.config(
                text=tr('no_combination_configured'),
                foreground="gray"
            )
        elif count == 1:
            self.combinations_info_label.config(
                text=tr('one_combination'),
                foreground="green"
            )
        else:
            self.combinations_info_label.config(
                text=tr('n_combinations').format(n=count),
                foreground="green"
            )
    
    def _setup_branch_config(self):
        """Configure les entrées pour chaque branche / Configure entries for each branch"""
        if self.branch_config_frame is None or not hasattr(self, 'branch_entries'):
            return
        
        # Nettoyer tous les widgets du legacy_mode_frame
        # Clean all widgets from legacy_mode_frame
        if hasattr(self, 'legacy_mode_frame'):
            for widget in self.legacy_mode_frame.winfo_children():
                widget.destroy()
        
        self.branch_entries.clear()
        
        # Importer FlowModel pour accéder aux connexions
        # Import FlowModel to access connections
        from models.flow_model import FlowModel
        
        # Recréer le titre / Recreate title
        if hasattr(self, 'legacy_mode_frame'):
            ttk.Label(
                self.legacy_mode_frame,
                text="Nombre d'unités requises par connexion:"
            ).pack(anchor=tk.W, pady=(0, 5))
        
        # Créer une entrée pour chaque connexion entrante dans le legacy_mode_frame
        # Create entry for each incoming connection in legacy_mode_frame
        if hasattr(self, 'legacy_mode_frame'):
            for i, conn_id in enumerate(self.node.input_connections):
                frame = ttk.Frame(self.legacy_mode_frame)
                frame.pack(fill=tk.X, pady=2, padx=20)
                
                # Récupérer la connexion pour obtenir le nom du nœud source
                # Get connection to retrieve source node name
                # Note: on doit passer par le parent pour accéder au flow_model
                # Note: must go through parent to access flow_model
                connection_name = f"Branche {i+1}"
                if hasattr(self, 'flow_model'):
                    connection = self.flow_model.get_connection(conn_id)
                    if connection:
                        source_node = self.flow_model.get_node(connection.source_id)
                        if source_node:
                            connection_name = f"{source_node.name}"
                
                ttk.Label(frame, text=f"{connection_name}:").pack(side=tk.LEFT, padx=5)
                
                var = tk.StringVar()
                # Quantité par défaut de 1 / Default quantity of 1
                required_units = self.node.required_units.get(conn_id, 1)
                var.set(str(required_units))
                
                entry = ttk.Entry(frame, textvariable=var, width=10)
                entry.pack(side=tk.LEFT, padx=5)
                
                ttk.Label(frame, text=tr('units_label')).pack(side=tk.LEFT)
                
                # Enregistrer CHAQUE connexion dans branch_entries (pas seulement la dernière !)
                # Register EACH connection in branch_entries (not just the last one!)
                self.branch_entries[conn_id] = var
            
            # Recréer la section de sortie pour le mode legacy
            # Recreate output section for legacy mode
            ttk.Separator(self.legacy_mode_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
            
            ttk.Label(
                self.legacy_mode_frame,
                text=tr('output_config_label'),
                font=("Arial", 9, "bold")
            ).pack(anchor=tk.W, pady=(5, 5))
            
            output_frame = ttk.Frame(self.legacy_mode_frame)
            output_frame.pack(fill=tk.X, padx=20)
            
            # Nombre d'items de sortie / Number of output items
            qty_frame = ttk.Frame(output_frame)
            qty_frame.pack(fill=tk.X, pady=5)
            ttk.Label(qty_frame, text=tr('output_items_count_label')).pack(side=tk.LEFT, padx=5)
            self.legacy_output_quantity_var = tk.StringVar()
            output_qty = getattr(self.node, 'legacy_output_quantity', 1)
            self.legacy_output_quantity_var.set(str(output_qty))
            ttk.Entry(qty_frame, textvariable=self.legacy_output_quantity_var, width=10).pack(side=tk.LEFT, padx=5)
            
            # Type d'item de sortie / Output item type
            type_frame = ttk.Frame(output_frame)
            type_frame.pack(fill=tk.X, pady=5)
            ttk.Label(type_frame, text=tr('output_item_type_label')).pack(side=tk.LEFT, padx=5)
            self.legacy_output_type_var = tk.StringVar()
            self.legacy_output_type_combo = ttk.Combobox(
                type_frame,
                textvariable=self.legacy_output_type_var,
                state="readonly",
                width=25
            )
            self.legacy_output_type_combo.pack(side=tk.LEFT, padx=5)
            ttk.Label(type_frame, text=tr('optional_keep_input_type'), 
                     font=("Arial", 8, "italic"), foreground="gray").pack(side=tk.LEFT, padx=5)
            
            # Peupler la combobox avec TOUS les types disponibles globalement
            # Populate combobox with ALL globally available types
            all_types = self._get_all_available_item_types()
            type_names = [t.name for t in all_types]
            self.legacy_output_type_combo['values'] = [''] + type_names  # Inclure option vide / Include empty option
            
            # Charger le type de sortie sélectionné / Load selected output type
            output_type = getattr(self.node, 'legacy_output_type', '')
            if output_type:
                # Trouver le nom correspondant au type_id
                # Find name corresponding to type_id
                for t in all_types:
                    if t.type_id == output_type:
                        self.legacy_output_type_var.set(t.name)
                        break
                else:
                    self.legacy_output_type_var.set(output_type)  # Au cas où c'est déjà un nom / In case it's already a name
            else:
                # Sélectionner le premier type par défaut s'il y en a
                # Select first type by default if any
                if all_types and len(all_types) > 0:
                    self.legacy_output_type_var.set(all_types[0].name)
                    # Sauvegarder aussi dans le nœud / Also save in node
                    self.node.legacy_output_type = all_types[0].type_id
                else:
                    self.legacy_output_type_var.set('')

    def _configure_item_types(self):
        """Ouvre le dialogue de configuration des types d'items / Open item types configuration dialog"""
        dialog = ItemTypesConfigDialog(self, self.node.item_type_config)
        self.wait_window(dialog)
        
        # Pas de messagebox de confirmation - l'utilisateur sait qu'il a validé
        # No confirmation messagebox - user knows they validated
    
    def _configure_processing_by_type(self):
        """Ouvre le dialogue de configuration du traitement par type / Open per-type processing configuration dialog"""
        from gui.processing_config_dialog import ProcessingConfigDialog
        
        # Collecter tous les types disponibles depuis les sources
        # Collect all available types from sources
        all_types = []
        seen_type_ids = set()
        
        for node in self.flow_model.nodes.values():
            if node.is_source:
                for item_type in node.item_type_config.item_types:
                    if item_type.type_id not in seen_type_ids:
                        all_types.append(item_type)
                        seen_type_ids.add(item_type.type_id)
        
        if not all_types:
            messagebox.showinfo(
                tr('info'),
                tr('no_item_type_configured'),
                parent=self
            )
            return
        
        dialog = ProcessingConfigDialog(
            self,
            self.node.processing_config,
            all_types,
            self.current_time_unit
        )
        self.wait_window(dialog)
        
        if dialog.result:
            messagebox.showinfo(tr('success'), tr('processing_config_saved'), parent=self)
    
    def _on_type_mode_change(self, type_id):
        """Callback quand le mode de traitement d'un type change / Callback when type processing mode changes"""
        # Cette méthode pourrait être étendue pour activer/désactiver
        # les champs std/skew selon le mode sélectionné
        # This method could be extended to enable/disable
        # std/skew fields based on selected mode
        pass
    
    def _open_type_distribution_editor(self, type_id):
        """Ouvre l'éditeur graphique pour un type spécifique / Open graphical editor for specific type"""
        from gui.distribution_editor_dialog import DistributionEditorDialog
        
        # Récupérer les valeurs actuelles pour ce type
        # Get current values for this type
        try:
            mean = float(self.type_processing_time_vars[type_id].get())
        except (ValueError, KeyError):
            mean = 10.0
        
        try:
            std = float(self.type_std_dev_vars[type_id].get()) if self.type_std_dev_vars[type_id].get() else 2.0
        except (ValueError, KeyError):
            std = 2.0
        
        try:
            skewness = float(self.type_skewness_vars[type_id].get()) if self.type_skewness_vars[type_id].get() else 0.0
        except (ValueError, KeyError):
            skewness = 0.0
        
        # Déterminer le type de distribution / Determine distribution type
        try:
            mode = self.type_processing_mode_vars[type_id].get()
            if mode == "SKEW_NORMAL":
                dist_type = 'SKEW_NORMAL'
            elif mode == "NORMAL":
                dist_type = 'NORMAL'
            else:
                dist_type = 'CONSTANT'
        except KeyError:
            dist_type = 'CONSTANT'
        
        # Callback pour appliquer les changements / Callback to apply changes
        def on_apply(new_mean, new_std, new_skewness):
            self.type_processing_time_vars[type_id].set(f"{new_mean:.2f}")
            self.type_std_dev_vars[type_id].set(f"{new_std:.2f}")
            self.type_skewness_vars[type_id].set(f"{new_skewness:.2f}")
        
        # Ouvrir le dialogue / Open dialog
        dialog = DistributionEditorDialog(
            self,
            initial_mean=mean,
            initial_std=std,
            initial_skewness=skewness,
            distribution_type=dist_type,
            callback=on_apply
        )
        dialog.wait_window()
    

    def _update_time_probe_section(self):
        """Met à jour dynamiquement la section loupe (similaire aux pipettes) / Dynamically update probe section (similar to probes)"""
        # Nettoyer le contenu existant / Clean existing content
        for widget in self.loupe_content_frame.winfo_children():
            widget.destroy()
        
        # Vérifier s'il y a une loupe sur ce nœud / Check if there's a probe on this node
        time_probe = self._get_time_probe_for_node()
        
        if time_probe:
            # Il y a une loupe : afficher les infos et le bouton supprimer
            # There's a probe: show info and delete button
            self._create_time_probe_config_widgets(time_probe)
        else:
            # Pas de loupe : afficher le bouton ajouter
            # No probe: show add button
            self._create_add_time_probe_button()
    
    def _get_time_probe_for_node(self):
        """Récupère la loupe associée à ce nœud (s'il y en a une) / Get probe associated with this node (if any)"""
        if hasattr(self.flow_model, 'time_probes'):
            for probe in self.flow_model.time_probes.values():
                if probe.node_id == self.node.node_id:
                    return probe
        return None
    
    def _create_add_time_probe_button(self):
        """Crée le bouton pour ajouter une loupe / Create button to add a probe"""
        info_label = ttk.Label(
            self.loupe_content_frame,
            text=tr('no_time_probe_on_node'),
            font=("Arial", 9, "italic"),
            foreground="#666"
        )
        info_label.pack(pady=5)
        
        add_button = ttk.Button(
            self.loupe_content_frame,
            text=tr('add_time_probe_btn'),
            command=self._add_time_probe
        )
        add_button.pack(pady=10)
    
    def _create_time_probe_config_widgets(self, time_probe):
        """Crée les widgets de configuration pour une loupe existante / Create configuration widgets for existing probe"""
        from models.time_probe import TimeProbeType
        
        # Nom de la loupe / Probe name
        name_frame = ttk.Frame(self.loupe_content_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame, text="Nom:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)  # Name
        self.time_probe_name_var = tk.StringVar(value=time_probe.name)
        ttk.Entry(name_frame, textvariable=self.time_probe_name_var, width=25).pack(side=tk.LEFT, padx=5)
        
        # Type de mesure / Measurement type
        type_frame = ttk.Frame(self.loupe_content_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(type_frame, text="Type:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.time_probe_type_var = tk.StringVar(value=time_probe.probe_type.name)
        
        # Options selon le type de nœud / Options based on node type
        type_options = []
        if not self.node.is_source and not self.node.is_sink and not self.node.is_splitter and not self.node.is_merger:
            type_options = ["PROCESSING", "INTER_EVENTS"]
        else:
            type_options = ["INTER_EVENTS"]
        
        type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.time_probe_type_var,
            values=type_options,
            state="readonly",
            width=20
        )
        type_combo.pack(side=tk.LEFT, padx=5)
        
        # Description du type / Type description
        type_desc = {
            "PROCESSING": "Mesure le temps de traitement de chaque item",  # Measures processing time for each item
            "INTER_EVENTS": "Mesure l'intervalle entre événements successifs"  # Measures interval between successive events
        }
        current_desc = type_desc.get(time_probe.probe_type.name, "")
        self.time_probe_type_desc_label = ttk.Label(
            self.loupe_content_frame,
            text=current_desc,
            font=("Arial", 8, "italic"),
            foreground="#666",
            wraplength=400
        )
        self.time_probe_type_desc_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Mettre à jour la description quand le type change
        # Update description when type changes
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.time_probe_type_desc_label.config(
            text=type_desc.get(self.time_probe_type_var.get(), "")
        ))
        
        # Couleur de la loupe / Probe color
        color_frame = ttk.Frame(self.loupe_content_frame)
        color_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(color_frame, text="Couleur:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)  # Color
        self.time_probe_color_var = tk.StringVar(value=time_probe.color)
        
        # Aperçu de couleur / Color preview
        self.time_probe_color_preview = tk.Label(color_frame, text="  ███  ", fg=time_probe.color, font=("Arial", 12))
        self.time_probe_color_preview.pack(side=tk.LEFT, padx=5)
        
        # Bouton pour choisir la couleur / Button to choose color
        def choose_loupe_color():
            from tkinter import colorchooser
            color = colorchooser.askcolor(initialcolor=self.time_probe_color_var.get(), title="Choisir une couleur")  # Choose a color
            if color and color[1]:
                self.time_probe_color_var.set(color[1])
                self.time_probe_color_preview.config(fg=color[1])
        
        ttk.Button(color_frame, text="Choisir la couleur", command=choose_loupe_color).pack(side=tk.LEFT, padx=5)
        
        # Statistiques / Statistics
        stats_frame = ttk.LabelFrame(self.loupe_content_frame, text="Statistiques", padding="5")  # Statistics
        stats_frame.pack(fill=tk.X, pady=10)
        
        stats = time_probe.get_statistics()
        ttk.Label(stats_frame, text=f"Nombre de mesures: {stats['count']}").pack(anchor=tk.W, pady=2)
        if stats['count'] > 0:
            ttk.Label(stats_frame, text=f"Moyenne: {stats['mean']:.3f}").pack(anchor=tk.W, pady=2)
            ttk.Label(stats_frame, text=f"Min: {stats['min']:.3f} | Max: {stats['max']:.3f}").pack(anchor=tk.W, pady=2)
            ttk.Label(stats_frame, text=f"Écart-type: {stats['std_dev']:.3f}").pack(anchor=tk.W, pady=2)
        
        # Bouton d'action / Action button
        action_frame = ttk.Frame(self.loupe_content_frame)
        action_frame.pack(pady=10)
        
        ttk.Button(
            action_frame,
            text="🗑️ Supprimer la loupe",
            command=lambda: self._remove_time_probe_widget(time_probe)
        ).pack(padx=5)
    
    def _add_time_probe(self):
        """Ouvre le dialogue pour ajouter une loupe de temps / Open dialog to add a time probe"""
        # Vérifier s'il y a déjà une loupe sur ce nœud / Check if there's already a probe on this node
        existing_probe = self._get_time_probe_for_node()
        if existing_probe:
            messagebox.showwarning(
                "Loupe existante",
                "Ce nœud a déjà une loupe de temps. Supprimez-la d'abord si vous voulez en ajouter une nouvelle.",
                parent=self
            )
            return
        
        from gui.time_probe_config_dialog import TimeProbeConfigDialog
        
        def on_save(time_probe):
            """Callback appelé quand la loupe est sauvegardée / Callback called when probe is saved"""
            self._update_time_probe_section()
            # Notifier le parent si callback défini (qui va redessiner le canvas)
            # Notify parent if callback defined (which will redraw canvas)
            if self.on_save_callback:
                self.on_save_callback(self.node)
        
        dialog = TimeProbeConfigDialog(
            self,
            self.flow_model,
            self.node.node_id,
            time_probe=None,
            on_save=on_save
        )
        self.wait_window(dialog)
    
    def _save_time_probe_changes(self, time_probe):
        """Sauvegarde les modifications de la loupe / Save probe modifications"""
        from models.time_probe import TimeProbeType
        
        # Mettre à jour les propriétés de la loupe / Update probe properties
        time_probe.name = self.time_probe_name_var.get()
        time_probe.probe_type = TimeProbeType[self.time_probe_type_var.get()]
        if hasattr(self, 'time_probe_color_var'):
            time_probe.color = self.time_probe_color_var.get()
        
        # Notifier via le callback / Notify via callback
        if self.on_save_callback:
            self.on_save_callback(self.node)
        
        messagebox.showinfo(tr('success'), tr('modifications_saved'), parent=self)
    
    def _remove_time_probe_widget(self, time_probe):
        """Supprime la loupe / Delete probe"""
        result = messagebox.askyesno(
            tr('confirm_delete_title'),
            tr('confirm_delete_time_probe').format(name=time_probe.name),
            parent=self
        )
        if result:
            # Supprimer la loupe / Delete probe
            if time_probe.probe_id in self.flow_model.time_probes:
                del self.flow_model.time_probes[time_probe.probe_id]
            
            # Rafraîchir l'affichage / Refresh display
            self._update_time_probe_section()
            
            # Notifier le parent / Notify parent
            if self.on_save_callback:
                self.on_save_callback(self.node)
            
            messagebox.showinfo(tr('success'), tr('time_probe_deleted_msg').format(name=time_probe.name), parent=self)
    
    def _save(self):
        """Enregistre les modifications / Save modifications"""
        try:
            # Nom / Name
            self.node.name = self.name_entry.get()
            
            # Temps de traitement ou intervalle de génération
            # Processing time or generation interval
            if self.node.is_source:
                # Mode de génération / Generation mode
                if hasattr(self, 'source_mode_var'):
                    from models.flow_model import SourceMode
                    self.node.source_mode = SourceMode[self.source_mode_var.get()]
                
                # Nombre d'items / Number of items
                self.node.max_items_to_generate = int(self.max_items_var.get())
                
                # Taille des lots / Batch size
                self.node.batch_size = int(self.batch_size_var.get())
                if self.node.batch_size < 1:
                    self.node.batch_size = 1
                
                generation_interval = float(self.generation_interval_var.get())
                self.node.set_generation_interval(generation_interval, self.current_time_unit)
                
                # Paramètres spécifiques selon le mode / Specific parameters based on mode
                if hasattr(self, 'generation_stddev_var'):
                    stddev_str = self.generation_stddev_var.get().strip()
                    if stddev_str:
                        stddev_value = float(stddev_str)
                        self.node.set_generation_std_dev(stddev_value, self.current_time_unit)
                
                if hasattr(self, 'generation_skewness_var'):
                    skewness_str = self.generation_skewness_var.get().strip()
                    if skewness_str:
                        self.node.generation_skewness = float(skewness_str)
                
                # Configuration des types d'items / Item types configuration
                if hasattr(self, 'item_gen_mode_var') and hasattr(self.node, 'item_type_config') and self.node.item_type_config:
                    from models.item_type import ItemGenerationMode
                    import re
                    
                    # Mode de génération - récupérer depuis la traduction
                    # Generation mode - get from translation
                    mode_value = self.item_gen_mode_var.get()
                    for mode in ItemGenerationMode:
                        translated_value = tr(ITEM_GEN_MODE_TRANSLATIONS[mode.name])
                        if translated_value == mode_value:
                            self.node.item_type_config.generation_mode = mode
                            break
                    
                    # Type unique pour SINGLE_TYPE / Single type for SINGLE_TYPE
                    if self.node.item_type_config.generation_mode == ItemGenerationMode.SINGLE_TYPE:
                        if hasattr(self, 'single_type_combo'):
                            selection = self.single_type_combo.get()
                            if selection:
                                match = re.search(r'\(ID:\s*(\w+)\)', selection)
                                if match:
                                    selected_type_id = match.group(1)
                                    self.node.item_type_config.single_type_id = selected_type_id
                                    
                                    # OPTION A : Garder tous les types globaux, ne rien supprimer
                                    # OPTION A: Keep all global types, don't delete anything
                                    # On stocke juste single_type_id, la liste item_types reste complète
                                    # We just store single_type_id, item_types list stays complete
                                    if False:
                                        print(f"[SAVE] {self.node.name} (ID: {self.node.node_id}) configuré en SINGLE_TYPE avec: {selected_type_id}")
                    
                    # Loop de séquence (pour SEQUENCE) / Sequence loop (for SEQUENCE)
                    elif self.node.item_type_config.generation_mode == ItemGenerationMode.SEQUENCE:
                        if hasattr(self, 'sequence_loop_var'):
                            self.node.item_type_config.sequence_loop = self.sequence_loop_var.get()
                        
                        # OPTION A : La séquence est stockée, item_types reste complet
                        # OPTION A: Sequence is stored, item_types stays complete
                        if False:
                            print(f"[SAVE] {self.node.name} (ID: {self.node.node_id}) configuré en SEQUENCE")
                    
                    # Quantités finies (pour RANDOM_FINITE) / Finite quantities (for RANDOM_FINITE)
                    elif self.node.item_type_config.generation_mode == ItemGenerationMode.RANDOM_FINITE:
                        if hasattr(self, 'finite_quantity_vars'):
                            self.node.item_type_config.finite_counts.clear()
                            
                            for type_id, var in self.finite_quantity_vars.items():
                                try:
                                    count = int(var.get())
                                    if count > 0:
                                        self.node.item_type_config.finite_counts[type_id] = count
                                except ValueError:
                                    pass
                            
                            # OPTION A : Les quantités sont stockées, item_types reste complet
                            # OPTION A: Quantities are stored, item_types stays complete
                            if False:
                                print(f"[SAVE] {self.node.name} (ID: {self.node.node_id}) configuré en RANDOM_FINITE")
                    
                    # Proportions infinies (pour RANDOM_INFINITE) / Infinite proportions (for RANDOM_INFINITE)
                    elif self.node.item_type_config.generation_mode == ItemGenerationMode.RANDOM_INFINITE:
                        if hasattr(self, 'infinite_proportion_vars'):
                            self.node.item_type_config.proportions.clear()
                            total = 0.0
                            
                            # Récupérer toutes les proportions (en pourcentage)
                            # Get all proportions (as percentage)
                            for type_id, var in self.infinite_proportion_vars.items():
                                try:
                                    percentage = float(var.get())
                                    if percentage > 0:
                                        # Convertir de pourcentage à proportion (diviser par 100)
                                        # Convert from percentage to proportion (divide by 100)
                                        prop = percentage / 100.0
                                        self.node.item_type_config.proportions[type_id] = prop
                                        total += prop
                                except ValueError:
                                    pass
                            
                            # Normaliser pour que la somme fasse exactement 1.0
                            # Normalize so sum equals exactly 1.0
                            if total > 0:
                                for type_id in self.node.item_type_config.proportions:
                                    self.node.item_type_config.proportions[type_id] /= total
                            
                            # OPTION A : Les proportions sont stockées, item_types reste complet
                            # OPTION A: Proportions are stored, item_types stays complete
                            if False:
                                print(f"[SAVE] {self.node.name} (ID: {self.node.node_id}) configuré en RANDOM_INFINITE")
                        
            elif self.node.is_splitter:
                # Mode du splitter / Splitter mode
                if hasattr(self, 'splitter_mode_var'):
                    from models.flow_model import SplitterMode, FirstAvailableMode
                    self.node.splitter_mode = SplitterMode[self.splitter_mode_var.get()]
                # Sous-mode first_available / First_available sub-mode
                if hasattr(self, 'first_available_mode_var'):
                    self.node.first_available_mode = FirstAvailableMode[self.first_available_mode_var.get()]
            elif not self.node.is_merger:
                # Sauvegarder les paramètres de traitement globaux
                # Save global processing parameters
                if hasattr(self, 'global_processing_time_var'):
                    try:
                        time_value = float(self.global_processing_time_var.get())
                        time_cs = TimeConverter.to_centiseconds(time_value, self.current_time_unit)
                        self.node.processing_time_cs = time_cs
                    except ValueError:
                        pass
                
                if hasattr(self, 'global_processing_mode_var'):
                    from models.flow_model import ProcessingTimeMode
                    mode_name = self.global_processing_mode_var.get()
                    if mode_name:
                        self.node.processing_time_mode = ProcessingTimeMode[mode_name]
                
                if hasattr(self, 'global_std_dev_var'):
                    try:
                        std_str = self.global_std_dev_var.get().strip()
                        if std_str:
                            std_value = float(std_str)
                            std_cs = TimeConverter.to_centiseconds(std_value, self.current_time_unit)
                            self.node.processing_time_std_dev_cs = std_cs
                    except ValueError:
                        pass
                
                if hasattr(self, 'global_skewness_var'):
                    try:
                        skew_str = self.global_skewness_var.get().strip()
                        if skew_str:
                            self.node.processing_time_skewness = float(skew_str)
                    except ValueError:
                        pass
                
                # Sauvegarder la configuration par type d'item
                # Save per-type item configuration
                # Sauvegarder la configuration par type d'item
                # Save per-type item configuration
                if hasattr(self, 'type_processing_time_vars') and self.type_processing_time_vars:
                    # Initialiser processing_config si nécessaire
                    # Initialize processing_config if necessary
                    if not hasattr(self.node, 'processing_config') or self.node.processing_config is None:
                        from models.item_type import ProcessingConfig
                        self.node.processing_config = ProcessingConfig()
                    
                    # Sauvegarder les temps de traitement par type
                    # Save processing times per type
                    for type_id, time_var in self.type_processing_time_vars.items():
                        try:
                            time_value = float(time_var.get())
                            time_cs = TimeConverter.to_centiseconds(time_value, self.current_time_unit)
                            self.node.processing_config.processing_times_cs[type_id] = time_cs
                        except ValueError:
                            pass
                    
                    # Sauvegarder les modes de traitement par type
                    # Save processing modes per type
                    if hasattr(self, 'type_processing_mode_vars'):
                        for type_id, mode_var in self.type_processing_mode_vars.items():
                            mode = mode_var.get()
                            self.node.processing_config.processing_modes[type_id] = mode
                    
                    # Sauvegarder les écarts-types par type
                    # Save standard deviations per type
                    if hasattr(self, 'type_std_dev_vars'):
                        for type_id, std_var in self.type_std_dev_vars.items():
                            try:
                                std_str = std_var.get().strip()
                                if std_str:
                                    std_value = float(std_str)
                                    std_cs = TimeConverter.to_centiseconds(std_value, self.current_time_unit)
                                    self.node.processing_config.std_devs_cs[type_id] = std_cs
                            except ValueError:
                                pass
                    
                    # Sauvegarder les asymétries par type
                    # Save skewnesses per type
                    if hasattr(self, 'type_skewness_vars'):
                        for type_id, skew_var in self.type_skewness_vars.items():
                            try:
                                skew_str = skew_var.get().strip()
                                if skew_str:
                                    skew_value = float(skew_str)
                                    self.node.processing_config.skewnesses[type_id] = skew_value
                            except ValueError:
                                pass
                    
                    # Sauvegarder les transformations de type
                    # Save type transformations
                    if hasattr(self, 'type_output_type_vars'):
                        for type_id, type_data in self.type_output_type_vars.items():
                            # Support pour tuple de 2 ou 3 éléments / Support for 2 or 3 element tuple
                            output_var = type_data[0]
                            all_types = type_data[1]
                            selection = output_var.get()
                            # Ignorer si c'est l'option "Nouveau type..." / Ignore if it's "New type..." option
                            if selection and not selection.startswith("➕"):
                                # Trouver le type_id correspondant au nom
                                # Find type_id corresponding to name
                                for t in all_types:
                                    if t.name == selection:
                                        self.node.processing_config.output_type_mapping[type_id] = t.type_id
                                        break
            
            # Mode de synchronisation (uniquement pour nœuds non-sources, non-splitters, non-mergers)
            # Sync mode (only for non-source, non-splitter, non-merger nodes)
            if not self.node.is_source and not self.node.is_splitter and not self.node.is_merger:
                self.node.sync_mode = SyncMode[self.sync_mode_var.get()]
                
                # Mode de priorité pour FIRST_AVAILABLE / Priority mode for FIRST_AVAILABLE
                from models.flow_model import FirstAvailablePriority
                self.node.first_available_priority = FirstAvailablePriority[self.first_available_priority_var.get()]
                
                # Sauvegarder le mode de combinaison / Save combination mode
                if hasattr(self, 'combination_mode_var'):
                    self.node.use_combinations = (self.combination_mode_var.get() == "combinations")
                
                # Configuration des branches / Branch configuration
                self.node.required_units.clear()
                for conn_id, var in self.branch_entries.items():
                    try:
                        self.node.required_units[conn_id] = int(var.get())
                    except ValueError:
                        self.node.required_units[conn_id] = 1
                
                # Configuration de sortie pour le mode legacy
                # Output configuration for legacy mode
                if hasattr(self, 'legacy_output_quantity_var'):
                    try:
                        self.node.legacy_output_quantity = int(self.legacy_output_quantity_var.get())
                    except ValueError:
                        self.node.legacy_output_quantity = 1
                
                if hasattr(self, 'legacy_output_type_var'):
                    type_name = self.legacy_output_type_var.get()
                    if type_name:
                        # Convertir le nom en type_id / Convert name to type_id
                        all_types = self._detect_incoming_item_types()
                        for t in all_types:
                            if t.name == type_name:
                                self.node.legacy_output_type = t.type_id
                                break
                        else:
                            # Si pas trouvé, stocker quand même le nom
                            # If not found, store the name anyway
                            self.node.legacy_output_type = type_name
                    else:
                        self.node.legacy_output_type = ""
            
            # Sauvegarder les modifications de la loupe si elle existe
            # Save probe modifications if it exists
            time_probe = self._get_time_probe_for_node()
            if time_probe and hasattr(self, 'time_probe_name_var') and hasattr(self, 'time_probe_type_var'):
                from models.time_probe import TimeProbeType
                time_probe.name = self.time_probe_name_var.get()
                time_probe.probe_type = TimeProbeType[self.time_probe_type_var.get()]
            
            # Callback
            if self.on_save_callback:
                self.on_save_callback(self.node)
            
            self.destroy()
        
        except ValueError as e:
            messagebox.showerror(tr('error'), tr('invalid_value_error').format(error=e))
    
    def _center_window(self):
        """Centre la fenêtre sur l'écran / Center window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
