"""Dialogue de configuration des temps de trajet entre machines / Travel time configuration dialog between machines"""
import tkinter as tk
from tkinter import ttk
from models.operator import DistributionType
from gui.translations import tr

class TravelTimeConfigDialog:
    """Dialogue pour configurer les temps de trajet d'un opérateur entre machines / Dialog to configure operator travel times between machines"""
    
    def __init__(self, parent, flow_model, operator, selected_machines):
        self.result = None
        self.flow_model = flow_model
        self.operator = operator
        self.selected_machines = selected_machines
        
        # Créer la fenêtre de dialogue / Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(tr('travel_time_config_title'))
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenêtre / Center window
        dialog_width = 700
        dialog_height = 500
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Copier les temps existants / Copy existing times
        self.travel_times = dict(operator.travel_times)
        
        self._create_widgets()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler / Bind Enter to OK and Escape to Cancel
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.dialog.focus_force()
        
        # Attendre la fermeture du dialogue / Wait for dialog close
        self.dialog.wait_window()
    
    def _create_widgets(self):
        """Crée les widgets du dialogue / Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            main_frame,
            text=tr('travel_time_description'),
            font=("Arial", 10)
        ).pack(pady=(0, 10))
        
        # Frame avec scrollbar pour la liste des trajets / Frame with scrollbar for travel list
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Créer une entrée pour chaque paire de machines / Create entry for each pair of machines
        self.travel_entries = {}
        
        for i, from_machine in enumerate(self.selected_machines):
            for j, to_machine in enumerate(self.selected_machines):
                if i != j:  # Pas de trajet vers soi-même / No travel to self
                    self._create_travel_entry(from_machine, to_machine)
        
        # Boutons OK/Annuler / OK/Cancel buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=20)
        
        ttk.Button(button_frame, text=tr('ok'), command=self._on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=tr('cancel_btn'), command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=5)
    
    def _create_travel_entry(self, from_machine, to_machine):
        """Crée une entrée pour un trajet spécifique / Create entry for a specific travel"""
        from_node = self.flow_model.nodes[from_machine]
        to_node = self.flow_model.nodes[to_machine]
        
        # Frame pour ce trajet / Frame for this travel
        travel_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"{from_node.name} → {to_node.name}",
            padding=10
        )
        travel_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Frame horizontal pour type + bouton éditeur / Horizontal frame for type + editor button
        type_and_editor_frame = ttk.Frame(travel_frame)
        type_and_editor_frame.pack(fill=tk.X, pady=2)
        
        # Type de distribution / Distribution type
        type_frame = ttk.Frame(type_and_editor_frame)
        type_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(type_frame, text=tr('distribution_label')).pack(side=tk.LEFT, padx=5)
        
        # Mapping pour affichage traduit / Mapping for translated display
        dist_display_values = [tr('dist_constant'), tr('dist_normal'), tr('dist_skew_normal')]
        dist_internal_values = [dt.value for dt in DistributionType]
        
        dist_var = tk.StringVar(value=tr('dist_constant'))
        dist_combo = ttk.Combobox(
            type_frame,
            textvariable=dist_var,
            values=dist_display_values,
            state="readonly",
            width=20
        )
        dist_combo.pack(side=tk.LEFT, padx=5)
        
        # Bouton pour ouvrir l'éditeur graphique / Button to open graphical editor
        editor_button = ttk.Button(
            type_and_editor_frame,
            text=tr('graphical_editor_btn'),
            command=lambda: self._open_graphical_editor(
                from_machine, to_machine, dist_var, param_vars
            )
        )
        editor_button.pack(side=tk.LEFT, padx=5)
        
        # Frame pour les paramètres (change selon le type) / Frame for parameters (changes by type)
        params_frame = ttk.Frame(travel_frame)
        params_frame.pack(fill=tk.X, pady=5)
        
        # Variables pour les paramètres / Variables for parameters
        param_vars = {
            'value': tk.DoubleVar(value=5.0),
            'mean': tk.DoubleVar(value=5.0),
            'std_dev': tk.DoubleVar(value=1.0),
            'location': tk.DoubleVar(value=5.0),
            'scale': tk.DoubleVar(value=1.0),
            'shape': tk.DoubleVar(value=0.0)
        }
        
        # Checkbox pour activer la loupe de mesure / Checkbox to enable measurement probe
        probe_var = tk.BooleanVar(value=False)
        # Charger l'état de la loupe si existant / Load probe state if existing
        if hasattr(self.operator, 'travel_probes'):
            existing_probe = self.operator.travel_probes.get((from_machine, to_machine))
            if existing_probe:
                probe_var.set(existing_probe.get('enabled', False))
        
        # Charger les valeurs existantes si disponibles / Load existing values if available
        existing_travel = self.travel_times.get((from_machine, to_machine))
        if existing_travel:
            # Convertir le type d'enum en traduction / Convert enum type to translation
            dist_type_enum = existing_travel['type']
            if dist_type_enum == DistributionType.CONSTANT:
                dist_var.set(tr('dist_constant'))
            elif dist_type_enum == DistributionType.NORMAL:
                dist_var.set(tr('dist_normal'))
            else:
                dist_var.set(tr('dist_skew_normal'))
            for key, value in existing_travel['params'].items():
                if key in param_vars:
                    param_vars[key].set(value)
        
        # Ajouter la checkbox pour la loupe / Add checkbox for probe
        probe_frame = ttk.Frame(travel_frame)
        probe_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(
            probe_frame,
            text=tr('enable_travel_probe'),
            variable=probe_var
        ).pack(side=tk.LEFT, padx=5)
        
        # Fonction pour mettre à jour l'affichage des paramètres / Function to update parameters display
        def update_params_display(*args):
            # Effacer les widgets existants / Clear existing widgets
            for widget in params_frame.winfo_children():
                widget.destroy()
            
            dist_type = dist_var.get()
            
            if dist_type == tr('dist_constant'):
                ttk.Label(params_frame, text=tr('value_label')).pack(side=tk.LEFT, padx=5)
                ttk.Spinbox(
                    params_frame,
                    from_=0.1,
                    to=1000,
                    increment=0.5,
                    textvariable=param_vars['value'],
                    width=10
                ).pack(side=tk.LEFT, padx=5)
                ttk.Label(params_frame, text=tr('seconds_label')).pack(side=tk.LEFT)
            
            elif dist_type == tr('dist_normal'):
                ttk.Label(params_frame, text=tr('mean_label')).pack(side=tk.LEFT, padx=5)
                ttk.Spinbox(
                    params_frame,
                    from_=0.1,
                    to=1000,
                    increment=0.5,
                    textvariable=param_vars['mean'],
                    width=10
                ).pack(side=tk.LEFT, padx=5)
                
                ttk.Label(params_frame, text=tr('std_dev_param_label')).pack(side=tk.LEFT, padx=5)
                ttk.Spinbox(
                    params_frame,
                    from_=0.1,
                    to=100,
                    increment=0.5,
                    textvariable=param_vars['std_dev'],
                    width=10
                ).pack(side=tk.LEFT, padx=5)
            
            elif dist_type == tr('dist_skew_normal'):
                ttk.Label(params_frame, text=tr('location_label')).pack(side=tk.LEFT, padx=5)
                ttk.Spinbox(
                    params_frame,
                    from_=0.1,
                    to=1000,
                    increment=0.5,
                    textvariable=param_vars['location'],
                    width=8
                ).pack(side=tk.LEFT, padx=2)
                
                ttk.Label(params_frame, text=tr('scale_label')).pack(side=tk.LEFT, padx=5)
                ttk.Spinbox(
                    params_frame,
                    from_=0.1,
                    to=100,
                    increment=0.5,
                    textvariable=param_vars['scale'],
                    width=8
                ).pack(side=tk.LEFT, padx=2)
                
                ttk.Label(params_frame, text=tr('shape_label')).pack(side=tk.LEFT, padx=5)
                ttk.Spinbox(
                    params_frame,
                    from_=-10,
                    to=10,
                    increment=0.5,
                    textvariable=param_vars['shape'],
                    width=8
                ).pack(side=tk.LEFT, padx=2)
        
        # Lier le changement de distribution / Bind distribution change
        dist_var.trace_add("write", update_params_display)
        update_params_display()
        
        # Sauvegarder les références / Save references
        self.travel_entries[(from_machine, to_machine)] = {
            'dist_var': dist_var,
            'param_vars': param_vars,
            'probe_var': probe_var
        }
    
    def _open_graphical_editor(self, from_machine, to_machine, dist_var, param_vars):
        """Ouvre l'éditeur graphique de distribution pour ce trajet / Open graphical distribution editor for this travel"""
        from gui.distribution_editor_dialog import DistributionEditorDialog
        
        # Récupérer les valeurs actuelles / Get current values
        dist_type = dist_var.get()
        
        if dist_type == tr('dist_constant'):
            mean = param_vars['value'].get()
            std = 0.1  # Valeur par défaut pour constant
            skewness = 0.0
            dist_type_for_editor = DistributionType.CONSTANT.value
        elif dist_type == tr('dist_normal'):
            mean = param_vars['mean'].get()
            std = param_vars['std_dev'].get()
            skewness = 0.0
            dist_type_for_editor = DistributionType.NORMAL.value
        else:  # SKEW_NORMAL
            mean = param_vars['location'].get()
            std = param_vars['scale'].get()
            skewness = param_vars['shape'].get()
            dist_type_for_editor = DistributionType.SKEW_NORMAL.value
        
        # Callback pour mettre à jour les valeurs / Callback to update values
        def on_editor_result(new_mean, new_std, new_skewness, new_dist_type):
            # Mettre à jour le type de distribution avec traduction / Update distribution type with translation
            if new_dist_type == 'CONSTANT' or new_dist_type == DistributionType.CONSTANT.value:
                dist_var.set(tr('dist_constant'))
                param_vars['value'].set(new_mean)
            elif new_dist_type == 'NORMAL' or new_dist_type == DistributionType.NORMAL.value:
                dist_var.set(tr('dist_normal'))
                param_vars['mean'].set(new_mean)
                param_vars['std_dev'].set(new_std)
            else:  # SKEW_NORMAL
                dist_var.set(tr('dist_skew_normal'))
                param_vars['location'].set(new_mean)
                param_vars['scale'].set(new_std)
                param_vars['shape'].set(new_skewness)
        
        # Ouvrir l'éditeur / Open editor
        editor = DistributionEditorDialog(
            self.dialog,
            initial_mean=mean,
            initial_std=std,
            initial_skewness=skewness,
            distribution_type=dist_type_for_editor,
            callback=on_editor_result
        )
    
    def _on_ok(self):
        """Valide et ferme le dialogue / Validate and close dialog"""
        # Collecter tous les temps de trajet / Collect all travel times
        result = {}
        
        for (from_machine, to_machine), widgets in self.travel_entries.items():
            dist_type_str = widgets['dist_var'].get()
            
            # Convertir la traduction en enum / Convert translation to enum
            if dist_type_str == tr('dist_constant'):
                dist_type = DistributionType.CONSTANT
            elif dist_type_str == tr('dist_normal'):
                dist_type = DistributionType.NORMAL
            else:
                dist_type = DistributionType.SKEW_NORMAL
            
            # Extraire les paramètres selon le type / Extract parameters by type
            if dist_type == DistributionType.CONSTANT:
                params = {'value': widgets['param_vars']['value'].get()}
            elif dist_type == DistributionType.NORMAL:
                params = {
                    'mean': widgets['param_vars']['mean'].get(),
                    'std_dev': widgets['param_vars']['std_dev'].get()
                }
            else:  # SKEW_NORMAL
                params = {
                    'location': widgets['param_vars']['location'].get(),
                    'scale': widgets['param_vars']['scale'].get(),
                    'shape': widgets['param_vars']['shape'].get()
                }
            
            result[(from_machine, to_machine)] = {
                'type': dist_type,
                'params': params
            }
            
            # Sauvegarder aussi l'état de la loupe dans l'opérateur / Also save probe state in operator
            probe_enabled = widgets['probe_var'].get()
            if not hasattr(self.operator, 'travel_probes'):
                self.operator.travel_probes = {}
            # Utiliser liste sans limite pour garder toutes les mesures / Use unlimited list to keep all measurements
            self.operator.travel_probes[(from_machine, to_machine)] = {
                'enabled': probe_enabled,
                'measurements': []
            }
        
        self.result = result
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Annule et ferme le dialogue / Cancel and close dialog"""
        self.dialog.destroy()
