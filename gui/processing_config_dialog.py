"""Dialogue de configuration des traitements par type d'item / Processing configuration dialog by item type"""
import tkinter as tk
from tkinter import ttk, messagebox
from models.item_type import ProcessingConfig, ItemType
from models.flow_model import ProcessingTimeMode
from models.time_converter import TimeUnit, TimeConverter
from typing import List
from gui.translations import tr

class ProcessingConfigDialog(tk.Toplevel):
    """Dialogue pour configurer le traitement par type d'item / Dialog to configure processing by item type"""
    
    def __init__(self, parent, processing_config: ProcessingConfig, available_types: List[ItemType], 
                 current_time_unit: TimeUnit):
        super().__init__(parent)
        self.processing_config = processing_config
        self.available_types = available_types
        self.current_time_unit = current_time_unit
        self.result = None
        
        self.title("Configuration Traitement par Type")
        self.geometry("800x500")
        self.resizable(True, True)
        
        # Rendre modal / Make modal
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_data()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler / Bind Enter to OK and Escape to Cancel
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self._on_cancel())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.focus_force()
        
        # Centrer / Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Crée les widgets / Create widgets"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info
        info_label = ttk.Label(
            main_frame,
            text="Configurez les temps de traitement et transformations pour chaque type d'item",  # Configure processing times and transformations for each item type
            font=("Arial", 9, "italic"),
            foreground="#666"
        )
        info_label.pack(pady=(0, 10))
        
        # Frame avec scrollbar / Frame with scrollbar
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Scroll avec molette / Scroll with mouse wheel
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        self.type_configs = {}
        
        # Une section par type / One section per type
        for idx, item_type in enumerate(self.available_types):
            self._create_type_section(scrollable_frame, item_type, idx)
        
        # Boutons / Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok, width=12).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=self._on_cancel, width=12).pack(side=tk.RIGHT, padx=5)
    
    def _create_type_section(self, parent, item_type: ItemType, idx: int):
        """Crée une section pour un type / Create section for a type"""
        # Frame principal / Main frame
        section = ttk.LabelFrame(parent, text=f"Type: {item_type.name}", padding="10")
        section.pack(fill=tk.X, pady=5, padx=5)
        
        # Couleur indicateur / Color indicator
        color_label = tk.Label(section, text="  ", bg=item_type.color, width=3, relief=tk.RAISED)
        color_label.grid(row=0, column=0, rowspan=4, padx=5, sticky=tk.N)
        
        # Mode de traitement + bouton éditeur / Processing mode + editor button
        mode_frame = ttk.Frame(section)
        mode_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT, padx=(0, 5))
        mode_var = tk.StringVar()
        mode_combo = ttk.Combobox(mode_frame, textvariable=mode_var, state="readonly", width=15)
        mode_combo['values'] = [mode.value for mode in ProcessingTimeMode]
        mode_combo.set(ProcessingTimeMode.CONSTANT.value)
        mode_combo.pack(side=tk.LEFT, padx=2)
        mode_combo.bind("<<ComboboxSelected>>", lambda e, t=item_type.type_id: self._on_mode_change(t))
        
        ttk.Button(
            mode_frame,
            text="📊 Éditer graphiquement",  # Edit graphically
            command=lambda t=item_type.type_id: self._open_distribution_editor(t)
        ).pack(side=tk.LEFT, padx=10)
        
        # Temps moyen / Mean time
        ttk.Label(section, text="Temps moyen:").grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        time_frame = ttk.Frame(section)
        time_frame.grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        
        time_var = tk.StringVar(value="1.0")
        ttk.Entry(time_frame, textvariable=time_var, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(time_frame, text=TimeConverter.get_unit_symbol(self.current_time_unit)).pack(side=tk.LEFT)
        
        # Écart-type (visible pour NORMAL et SKEW_NORMAL) / Std dev (visible for NORMAL and SKEW_NORMAL)
        std_dev_frame = ttk.Frame(section)
        std_dev_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=2)
        std_dev_frame.grid_remove()
        
        ttk.Label(std_dev_frame, text="Écart-type:").pack(side=tk.LEFT, padx=2)  # Std dev
        std_dev_var = tk.StringVar(value="0.2")
        ttk.Entry(std_dev_frame, textvariable=std_dev_var, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(std_dev_frame, text=TimeConverter.get_unit_symbol(self.current_time_unit)).pack(side=tk.LEFT)
        
        # Asymétrie (visible pour SKEW_NORMAL) / Skewness (visible for SKEW_NORMAL)
        skewness_frame = ttk.Frame(section)
        skewness_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=5, pady=2)
        skewness_frame.grid_remove()
        
        ttk.Label(skewness_frame, text="Asymétrie:").pack(side=tk.LEFT, padx=2)  # Skewness
        skewness_var = tk.StringVar(value="0.0")
        ttk.Entry(skewness_frame, textvariable=skewness_var, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(skewness_frame, text="(-5 à +5)").pack(side=tk.LEFT)
        
        # Transformation de type / Type transformation
        ttk.Separator(section, orient=tk.HORIZONTAL).grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Label(section, text="Type de sortie:", font=("Arial", 9, "bold")).grid(  # Output type
            row=5, column=1, sticky=tk.W, padx=5, pady=2
        )
        
        output_frame = ttk.Frame(section)
        output_frame.grid(row=6, column=1, columnspan=2, sticky=tk.W, padx=5)
        
        output_var = tk.StringVar()
        keep_type_radio = ttk.Radiobutton(
            output_frame,
            text=f"Garder le type '{item_type.name}'",  # Keep type
            variable=output_var,
            value="keep"
        )
        keep_type_radio.pack(anchor=tk.W, pady=2)
        
        change_type_frame = ttk.Frame(output_frame)
        change_type_frame.pack(anchor=tk.W, pady=2)
        
        change_type_radio = ttk.Radiobutton(
            change_type_frame,
            text="Transformer en:",  # Transform to
            variable=output_var,
            value="change"
        )
        change_type_radio.pack(side=tk.LEFT)
        
        output_type_combo = ttk.Combobox(change_type_frame, state="readonly", width=15)
        output_type_combo['values'] = [t.name for t in self.available_types]
        output_type_combo.pack(side=tk.LEFT, padx=5)
        
        output_var.set("keep")
        
        # Stocker les références / Store references
        self.type_configs[item_type.type_id] = {
            'mode_var': mode_var,
            'mode_combo': mode_combo,
            'time_var': time_var,
            'std_dev_var': std_dev_var,
            'std_dev_frame': std_dev_frame,
            'skewness_var': skewness_var,
            'skewness_frame': skewness_frame,
            'output_var': output_var,
            'output_combo': output_type_combo
        }
    
    def _on_mode_change(self, type_id: str):
        """Changement de mode pour un type / Mode change for a type"""
        config = self.type_configs[type_id]
        mode_str = config['mode_var'].get()
        
        # Cacher tout / Hide all
        config['std_dev_frame'].grid_remove()
        config['skewness_frame'].grid_remove()
        
        # Afficher selon mode / Show by mode
        if mode_str == ProcessingTimeMode.NORMAL.value:
            config['std_dev_frame'].grid()
        elif mode_str == ProcessingTimeMode.SKEW_NORMAL.value:
            config['std_dev_frame'].grid()
            config['skewness_frame'].grid()
    
    def _load_data(self):
        """Charge les données existantes / Load existing data"""
        for item_type in self.available_types:
            type_id = item_type.type_id
            config = self.type_configs[type_id]
            
            # Temps / Time
            time_cs = self.processing_config.processing_times_cs.get(type_id, 100.0)
            time_in_unit = TimeConverter.convert(time_cs, TimeUnit.CENTISECONDS, self.current_time_unit)
            config['time_var'].set(f"{time_in_unit:.2f}")
            
            # Mode
            mode_str = self.processing_config.processing_modes.get(type_id, "CONSTANT")
            for mode in ProcessingTimeMode:
                if mode.name == mode_str:
                    config['mode_var'].set(mode.value)
                    break
            
            # Std dev / Ecart-type
            std_dev_cs = self.processing_config.std_devs_cs.get(type_id, 20.0)
            std_dev_in_unit = TimeConverter.convert(std_dev_cs, TimeUnit.CENTISECONDS, self.current_time_unit)
            config['std_dev_var'].set(f"{std_dev_in_unit:.2f}")
            
            # Skewness / Asymétrie
            skewness = self.processing_config.skewnesses.get(type_id, 0.0)
            config['skewness_var'].set(f"{skewness:.2f}")
            
            # Output type / Type de sortie
            output_type_id = self.processing_config.output_type_mapping.get(type_id)
            if output_type_id and output_type_id != type_id:
                config['output_var'].set("change")
                # Trouver le nom / Find name
                for t in self.available_types:
                    if t.type_id == output_type_id:
                        config['output_combo'].set(t.name)
                        break
            else:
                config['output_var'].set("keep")
            
            # Appliquer la visibilité / Apply visibility
            self._on_mode_change(type_id)
    
    def _on_ok(self):
        """Valide et sauvegarde / Validate and save"""
        try:
            for item_type in self.available_types:
                type_id = item_type.type_id
                config = self.type_configs[type_id]
                
                # Temps
                time_in_unit = float(config['time_var'].get())
                time_cs = TimeConverter.convert(time_in_unit, self.current_time_unit, TimeUnit.CENTISECONDS)
                self.processing_config.processing_times_cs[type_id] = time_cs
                
                # Mode
                mode_str = config['mode_var'].get()
                for mode in ProcessingTimeMode:
                    if mode.value == mode_str:
                        self.processing_config.processing_modes[type_id] = mode.name
                        break
                
                # Std dev
                std_dev_in_unit = float(config['std_dev_var'].get())
                std_dev_cs = TimeConverter.convert(std_dev_in_unit, self.current_time_unit, TimeUnit.CENTISECONDS)
                self.processing_config.std_devs_cs[type_id] = std_dev_cs
                
                # Skewness
                skewness = float(config['skewness_var'].get())
                self.processing_config.skewnesses[type_id] = skewness
                
                # Output type
                if config['output_var'].get() == "change":
                    output_name = config['output_combo'].get()
                    for t in self.available_types:
                        if t.name == output_name:
                            self.processing_config.output_type_mapping[type_id] = t.type_id
                            break
                else:
                    self.processing_config.output_type_mapping[type_id] = type_id
            
            self.result = True
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror(tr('error'), tr('invalid_value_error').format(error=e))
    
    def _on_cancel(self):
        """Annule / Cancel"""
        self.result = None
        self.destroy()
    
    def _open_distribution_editor(self, type_id: str):
        """Ouvre l'éditeur graphique de distribution pour un type spécifique / Open graphical distribution editor for a specific type"""
        config = self.type_configs[type_id]
        
        # Récupérer les valeurs actuelles / Get current values
        try:
            mean = float(config['time_var'].get()) if config['time_var'].get() else 1.0
        except ValueError:
            mean = 1.0
        
        try:
            std = float(config['std_dev_var'].get()) if config['std_dev_var'].get() else 0.2
        except ValueError:
            std = 0.2
        
        try:
            skewness = float(config['skewness_var'].get()) if config['skewness_var'].get() else 0.0
        except ValueError:
            skewness = 0.0
        
        # Type de distribution / Distribution type
        mode = config['mode_var'].get()
        dist_type = 'SKEW_NORMAL' if mode == ProcessingTimeMode.SKEW_NORMAL.value else 'NORMAL'
        
        # Ouvrir l'éditeur / Open editor
        from gui.distribution_editor_dialog import DistributionEditorDialog
        
        def on_editor_save(new_mean, new_std, new_skewness):
            config['time_var'].set(f"{new_mean:.2f}")
            config['std_dev_var'].set(f"{new_std:.2f}")
            config['skewness_var'].set(f"{new_skewness:.2f}")
            
            # Si l'asymétrie est significative, basculer en mode SKEW_NORMAL / If skewness is significant, switch to SKEW_NORMAL mode
            if abs(new_skewness) > 0.1 and mode != ProcessingTimeMode.SKEW_NORMAL.value:
                config['mode_var'].set(ProcessingTimeMode.SKEW_NORMAL.value)
                config['mode_combo'].set(ProcessingTimeMode.SKEW_NORMAL.value)
                self._on_mode_change(type_id)
        
        DistributionEditorDialog(
            self,
            initial_mean=mean,
            initial_std=std,
            initial_skewness=skewness,
            distribution_type=dist_type,
            callback=on_editor_save
        )
