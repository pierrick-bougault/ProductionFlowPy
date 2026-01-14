"""Dialogue de configuration pour une loupe de temps / Time probe configuration dialog"""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from models.time_probe import TimeProbe, TimeProbeType
from gui.translations import tr

class TimeProbeConfigDialog(tk.Toplevel):
    """Dialogue pour configurer une loupe de temps / Dialog to configure a time probe"""
    
    def __init__(self, parent, flow_model, node_id, time_probe=None, on_save=None):
        super().__init__(parent)
        
        self.flow_model = flow_model
        self.node_id = node_id
        self.time_probe = time_probe
        self.on_save_callback = on_save
        self.result = None
        
        # Configuration de la fenêtre / Window configuration
        self.title(tr('time_probe_config_title'))
        self.geometry("550x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_values()
        
        # Centrer la fenêtre / Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Crée les widgets du dialogue / Create dialog widgets"""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nom de la loupe / Probe name
        ttk.Label(main_frame, text=tr('probe_name_label'), font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=10
        )
        
        # Type de mesure / Measurement type
        ttk.Label(main_frame, text=tr('measurement_type_label'), font=("Arial", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.probe_type_var = tk.StringVar()
        
        # Utiliser les valeurs traduites pour l'affichage / Use translated values for display
        type_display_values = [tr('processing_time_type'), tr('inter_events_time_type')]
        type_combo = ttk.Combobox(
            main_frame,
            textvariable=self.probe_type_var,
            values=type_display_values,
            state="readonly",
            width=27
        )
        type_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Description des types / Type descriptions
        desc_frame = ttk.Frame(main_frame)
        desc_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        self.desc_label = ttk.Label(
            desc_frame,
            text="",
            font=("Arial", 9, "italic"),
            foreground="#666",
            wraplength=500,
            justify=tk.LEFT
        )
        self.desc_label.pack(anchor=tk.W)
        
        # Callback pour mettre à jour la description / Callback to update description
        def update_description(*args):
            probe_type = self.probe_type_var.get()
            if probe_type == tr('processing_time_type'):
                self.desc_label.config(text=tr('processing_time_desc'))
            elif probe_type == tr('inter_events_time_type'):
                self.desc_label.config(text=tr('inter_events_time_desc'))
            else:
                self.desc_label.config(text="")
        
        self.probe_type_var.trace('w', update_description)
        
        # Mode de mesure (buffer ou cumulatif) / Measurement mode (buffer or cumulative)
        ttk.Label(main_frame, text=tr('measure_mode_label'), font=("Arial", 10, "bold")).grid(
            row=3, column=0, sticky=tk.W, pady=5
        )
        self.measure_mode_var = tk.StringVar(value="buffer")
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=3, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Radiobutton(
            mode_frame,
            text=tr('buffer_mode'),
            variable=self.measure_mode_var,
            value="buffer"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            mode_frame,
            text=tr('cumulative_mode'),
            variable=self.measure_mode_var,
            value="cumulative"
        ).pack(anchor=tk.W, pady=(2, 0))
        
        # Couleur / Color
        ttk.Label(main_frame, text=tr('graph_color_label'), font=("Arial", 10, "bold")).grid(
            row=4, column=0, sticky=tk.W, pady=5
        )
        
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=4, column=1, sticky=tk.W, pady=5, padx=10)
        
        self.color_var = tk.StringVar(value="#FF6B6B")
        self.color_preview = tk.Canvas(color_frame, width=30, height=20, bg=self.color_var.get())
        self.color_preview.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            color_frame,
            text=tr('choose_color_btn'),
            command=self._choose_color
        ).pack(side=tk.LEFT)
        
        # Visibilité / Visibility
        ttk.Label(main_frame, text=tr('display_label'), font=("Arial", 10, "bold")).grid(
            row=5, column=0, sticky=tk.W, pady=5
        )
        self.visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text=tr('show_graph_checkbox'),
            variable=self.visible_var
        ).grid(row=5, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text=tr('save_btn'),
            command=self._save
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text=tr('cancel_btn'),
            command=self.destroy
        ).pack(side=tk.LEFT, padx=5)
    
    def _choose_color(self):
        """Ouvre le sélecteur de couleur / Open color picker"""
        # Relâcher le grab pour permettre à la fenêtre de couleur de fonctionner
        self.grab_release()
        color = colorchooser.askcolor(
            initialcolor=self.color_var.get(),
            title=tr('choose_color_dialog_title')
        )
        # Reprendre le grab
        self.grab_set()
        if color[1]:  # color[1] contient le code hex / color[1] contains hex code
            self.color_var.set(color[1])
            self.color_preview.config(bg=color[1])
    
    def _load_values(self):
        """Charge les valeurs de la loupe existante / Load existing probe values"""
        if self.time_probe:
            self.name_var.set(self.time_probe.name)
            # Convertir le type de probe en valeur traduite / Convert probe type to translated value
            if self.time_probe.probe_type == TimeProbeType.PROCESSING:
                self.probe_type_var.set(tr('processing_time_type'))
            else:
                self.probe_type_var.set(tr('inter_events_time_type'))
            self.color_var.set(self.time_probe.color)
            self.color_preview.config(bg=self.time_probe.color)
            self.visible_var.set(self.time_probe.visible)
            if hasattr(self.time_probe, 'measure_mode'):
                self.measure_mode_var.set(self.time_probe.measure_mode)
        else:
            # Valeurs par défaut / Default values
            node = self.flow_model.get_node(self.node_id)
            if node:
                self.name_var.set(f"{tr('time_probe_prefix')} {node.name}")
                
                # Suggérer le bon type selon le type de nœud
                # Suggest correct type based on node type
                from models.flow_model import NodeType
                if node.node_type == NodeType.SOURCE:
                    # Pour une Source : inter-arrivées / For Source: inter-arrivals
                    self.probe_type_var.set(tr('inter_events_time_type'))
                elif node.node_type == NodeType.SINK:
                    # Pour une Sortie : inter-départs / For Sink: inter-departures
                    self.probe_type_var.set(tr('inter_events_time_type'))
                else:
                    # Pour les autres nœuds : temps de traitement par défaut
                    # For other nodes: processing time by default
                    self.probe_type_var.set(tr('processing_time_type'))
            else:
                self.probe_type_var.set(tr('processing_time_type'))
    
    def _get_probe_type_from_display(self, display_value: str) -> TimeProbeType:
        """Convertit la valeur affichée en TimeProbeType / Convert display value to TimeProbeType"""
        if display_value == tr('processing_time_type'):
            return TimeProbeType.PROCESSING
        elif display_value == tr('inter_events_time_type'):
            return TimeProbeType.INTER_EVENTS
        else:
            return None
    
    def _save(self):
        """Enregistre la loupe / Save probe"""
        try:
            name = self.name_var.get().strip()
            if not name:
                raise ValueError(tr('name_empty_error'))
            
            # Trouver le TimeProbeType correspondant / Find corresponding TimeProbeType
            probe_type_str = self.probe_type_var.get()
            probe_type = self._get_probe_type_from_display(probe_type_str)
            
            if probe_type is None:
                raise ValueError(tr('invalid_measure_type_error'))
            
            # Validation : vérifier la compatibilité avec le type de nœud
            # Validation: check compatibility with node type
            node = self.flow_model.get_node(self.node_id)
            if node:
                from models.flow_model import NodeType
                
                # Pour une Source, seul INTER_EVENTS est valide (inter-arrivées)
                # For Source, only INTER_EVENTS is valid (inter-arrivals)
                if node.node_type == NodeType.SOURCE and probe_type == TimeProbeType.PROCESSING:
                    response = messagebox.askyesno(
                        tr('incompatible_type_title'),
                        tr('source_incompatible_msg'),
                        parent=self
                    )
                    if response:
                        probe_type = TimeProbeType.INTER_EVENTS
                        self.probe_type_var.set(tr('inter_events_time_type'))
                    else:
                        return  # Annuler la sauvegarde
                
                # Pour une Sortie, seul INTER_EVENTS est valide (inter-départs)
                # For Sink, only INTER_EVENTS is valid (inter-departures)
                if node.node_type == NodeType.SINK and probe_type == TimeProbeType.PROCESSING:
                    response = messagebox.askyesno(
                        tr('incompatible_type_title'),
                        tr('sink_incompatible_msg'),
                        parent=self
                    )
                    if response:
                        probe_type = TimeProbeType.INTER_EVENTS
                        self.probe_type_var.set(tr('inter_events_time_type'))
                    else:
                        return  # Annuler la sauvegarde
            
            if self.time_probe:
                # Modifier loupe existante / Modify existing probe
                self.time_probe.name = name
                self.time_probe.probe_type = probe_type
                self.time_probe.color = self.color_var.get()
                self.time_probe.visible = self.visible_var.get()
                self.time_probe.measure_mode = self.measure_mode_var.get()
                self.result = self.time_probe
            else:
                # Créer nouvelle loupe / Create new probe
                time_probe_id = self.flow_model.generate_time_probe_id()
                self.result = TimeProbe(time_probe_id, name, self.node_id, probe_type)
                self.result.color = self.color_var.get()
                self.result.visible = self.visible_var.get()
                self.result.measure_mode = self.measure_mode_var.get()
                self.flow_model.add_time_probe(self.result)
            
            if self.on_save_callback:
                self.on_save_callback(self.result)
            
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror(tr('error'), str(e), parent=self)
