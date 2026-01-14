"""Dialogue pour configurer les temps de traitement des machines assignées à un opérateur

Dialog to configure processing times for machines assigned to an operator"""
import tkinter as tk
from tkinter import ttk, messagebox
from models.operator import DistributionType
from gui.translations import tr

class MachineProcessingTimeDialog:
    """Dialogue pour configurer les temps de traitement des machines
    
    Dialog to configure machine processing times"""
    
    def __init__(self, parent, flow_model, machine_ids):
        self.result = None
        self.flow_model = flow_model
        self.machine_ids = machine_ids
        self.machine_configs = {}  # machine_id -> config dict / machine_id -> config dict
        
        # Créer la fenêtre / Create window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configuration des temps de traitement")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Taille de la fenêtre / Window size
        dialog_width = 700
        dialog_height = 600
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        self._create_widgets()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler / Bind Enter key to OK button and Escape to Cancel button
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # Activer automatiquement la fenêtre / Auto-focus window
        self.dialog.focus_force()
        
        self.dialog.wait_window()
    
    def _create_widgets(self):
        """Crée les widgets du dialogue / Creates dialog widgets"""
        # Info en haut / Info at top
        info_frame = ttk.Frame(self.dialog, padding=10)
        info_frame.pack(fill=tk.X)
        
        ttk.Label(
            info_frame,
            text="Configurez les temps de traitement pour chaque machine.\n"
                 "Ces paramètres seront appliqués lorsque l'opérateur traite des items sur ces machines.",
            font=("Arial", 9, "italic"),
            foreground="#666"
        ).pack()
        
        # Canvas avec scrollbar pour les machines / Canvas with scrollbar for machines
        canvas_frame = ttk.Frame(self.dialog)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
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
        
        # Bind mousewheel (bind au lieu de bind_all pour éviter les conflits) / Bind mousewheel (bind instead of bind_all to avoid conflicts)
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        
        # Créer une entrée pour chaque machine / Create entry for each machine
        for machine_id in self.machine_ids:
            machine_node = self.flow_model.get_node(machine_id)
            if machine_node:
                self._create_machine_entry(scrollable_frame, machine_node)
        
        # Boutons / Buttons
        button_frame = ttk.Frame(self.dialog, padding=10)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="✓ OK", command=self._on_ok, width=12).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="✕ Annuler", command=self._on_cancel, width=12).pack(side=tk.RIGHT)
    
    def _create_machine_entry(self, parent, machine_node):
        """Crée une entrée de configuration pour une machine
        
        Creates a configuration entry for a machine"""
        machine_id = machine_node.node_id
        
        # Frame pour cette machine / Frame for this machine
        machine_frame = ttk.LabelFrame(parent, text=f"🔧 {machine_node.name}", padding=10)
        machine_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Type de distribution / Distribution type
        dist_frame = ttk.Frame(machine_frame)
        dist_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dist_frame, text="Type de distribution:").pack(side=tk.LEFT, padx=5)
        
        dist_var = tk.StringVar(value="Constant")
        dist_combo = ttk.Combobox(
            dist_frame,
            textvariable=dist_var,
            values=["Constant", "Normal", "Skew Normal"],
            state="readonly",
            width=15
        )
        dist_combo.pack(side=tk.LEFT, padx=5)
        
        # Frame pour les paramètres / Frame for parameters
        params_frame = ttk.Frame(machine_frame)
        params_frame.pack(fill=tk.X, pady=5)
        
        # Variables pour les paramètres / Variables for parameters
        param_vars = {}
        param_entries = {}
        
        # Fonction pour mettre à jour les paramètres affichés / Function to update displayed parameters
        def update_params(*args):
            # Effacer le frame / Clear frame
            for widget in params_frame.winfo_children():
                widget.destroy()
            
            dist_type = dist_var.get()
            
            if dist_type == "Constant":
                ttk.Label(params_frame, text="Valeur:").pack(side=tk.LEFT, padx=5)
                var = tk.StringVar(value="1.0")
                param_vars['value'] = var
                entry = ttk.Entry(params_frame, textvariable=var, width=10)
                entry.pack(side=tk.LEFT, padx=5)
                param_entries['value'] = entry
                ttk.Label(params_frame, text="unités", foreground="#666").pack(side=tk.LEFT)
                
            elif dist_type == "Normal":
                ttk.Label(params_frame, text="Moyenne:").pack(side=tk.LEFT, padx=5)
                mean_var = tk.StringVar(value="1.0")
                param_vars['mean'] = mean_var
                ttk.Entry(params_frame, textvariable=mean_var, width=10).pack(side=tk.LEFT, padx=5)
                
                ttk.Label(params_frame, text="Écart-type:").pack(side=tk.LEFT, padx=5)
                std_var = tk.StringVar(value="0.1")
                param_vars['std_dev'] = std_var
                ttk.Entry(params_frame, textvariable=std_var, width=10).pack(side=tk.LEFT, padx=5)
                
            elif dist_type == "Skew Normal":
                ttk.Label(params_frame, text="Location:").pack(side=tk.LEFT, padx=5)
                loc_var = tk.StringVar(value="1.0")
                param_vars['location'] = loc_var
                ttk.Entry(params_frame, textvariable=loc_var, width=10).pack(side=tk.LEFT, padx=5)
                
                ttk.Label(params_frame, text="Scale:").pack(side=tk.LEFT, padx=5)
                scale_var = tk.StringVar(value="0.1")
                param_vars['scale'] = scale_var
                ttk.Entry(params_frame, textvariable=scale_var, width=10).pack(side=tk.LEFT, padx=5)
                
                ttk.Label(params_frame, text="Shape:").pack(side=tk.LEFT, padx=5)
                shape_var = tk.StringVar(value="0.0")
                param_vars['shape'] = shape_var
                ttk.Entry(params_frame, textvariable=shape_var, width=10).pack(side=tk.LEFT, padx=5)
        
        dist_var.trace('w', update_params)
        update_params()  # Initialiser / Initialize
        
        # Charger les valeurs existantes de la machine / Load existing machine values
        if hasattr(machine_node, 'processing_time_dist'):
            dist_type_str = machine_node.processing_time_dist.get('type', 'Constant')
            dist_var.set(dist_type_str)
            params = machine_node.processing_time_dist.get('params', {})
            for key, value in params.items():
                if key in param_vars:
                    param_vars[key].set(str(value))
        
        # Sauvegarder les références / Save references
        self.machine_configs[machine_id] = {
            'dist_var': dist_var,
            'param_vars': param_vars
        }
    
    def _on_ok(self):
        """Valide et applique les configurations / Validates and applies configurations"""
        from tkinter import messagebox
        
        # Construire le dictionnaire de résultats / Build results dictionary
        result = {}
        
        for machine_id, config in self.machine_configs.items():
            try:
                dist_type_str = config['dist_var'].get()
                dist_type = DistributionType(dist_type_str)
                
                params = {}
                for key, var in config['param_vars'].items():
                    params[key] = float(var.get())
                
                # Appliquer directement à la machine / Apply directly to machine
                machine_node = self.flow_model.get_node(machine_id)
                if machine_node:
                    machine_node.processing_time_dist = {
                        'type': dist_type,
                        'params': params
                    }
                
                result[machine_id] = {
                    'type': dist_type,
                    'params': params
                }
            
            except ValueError as e:
                messagebox.showerror(tr('error'), tr('invalid_value_error').format(error=f"{machine_id}: {e}"))
                return
        
        self.result = result
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Annule et ferme / Cancels and closes"""
        self.result = None
        self.dialog.destroy()
