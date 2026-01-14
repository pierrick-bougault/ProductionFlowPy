"""Dialogue de configuration pour une pipette de mesure / Configuration dialog for a measurement probe"""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from models.measurement_probe import MeasurementProbe
from gui.translations import tr

class MeasurementProbeConfigDialog(tk.Toplevel):
    """Dialogue pour configurer une pipette de mesure / Dialog to configure a measurement probe"""
    
    def __init__(self, parent, flow_model, connection_id, probe=None, on_save=None):
        super().__init__(parent)
        
        self.flow_model = flow_model
        self.connection_id = connection_id
        self.probe = probe
        self.on_save_callback = on_save
        self.result = None
        
        # Configuration de la fenêtre / Window configuration
        self.title("Configuration Pipette de Mesure")  # Measurement Probe Configuration
        self.geometry("550x380")
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
        
        # Nom de la pipette / Probe name
        ttk.Label(main_frame, text="Nom de la pipette:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=10
        )
        
        # Mode de mesure (buffer ou cumulatif) / Measurement mode (buffer or cumulative)
        ttk.Label(main_frame, text="Mode de mesure:", font=("Arial", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.measure_mode_var = tk.StringVar(value="buffer")
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Radiobutton(
            mode_frame,
            text="Buffer - Nombre d'items dans le buffer à chaque instant",  # Number of items in buffer at each instant
            variable=self.measure_mode_var,
            value="buffer"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            mode_frame,
            text="Cumulatif - Nombre total d'items passés depuis le début",  # Total items passed since start
            variable=self.measure_mode_var,
            value="cumulative"
        ).pack(anchor=tk.W, pady=(2, 0))
        
        # Couleur / Color
        ttk.Label(main_frame, text="Couleur du graphique:", font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        
        self.color_var = tk.StringVar(value="#2196F3")
        self.color_preview = tk.Canvas(color_frame, width=30, height=20, bg=self.color_var.get())
        self.color_preview.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            color_frame,
            text="Choisir...",
            command=self._choose_color
        ).pack(side=tk.LEFT)
        
        # Visibilité / Visibility
        ttk.Label(main_frame, text="Affichage:", font=("Arial", 10, "bold")).grid(  # Display
            row=3, column=0, sticky=tk.W, pady=5
        )
        self.visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text="Afficher le graphique",  # Show graph
            variable=self.visible_var
        ).grid(row=3, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="Enregistrer",  # Save
            command=self._save
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Annuler",  # Cancel
            command=self.destroy
        ).pack(side=tk.LEFT, padx=5)
    
    def _choose_color(self):
        """Ouvre le sélecteur de couleur / Open color picker"""
        # Relâcher le grab pour permettre à la fenêtre de couleur de fonctionner
        self.grab_release()
        color = colorchooser.askcolor(
            initialcolor=self.color_var.get(),
            title="Choisir une couleur"  # Choose a color
        )
        # Reprendre le grab
        self.grab_set()
        if color[1]:  # color[1] contient le code hex
            self.color_var.set(color[1])
            self.color_preview.config(bg=color[1])
    
    def _load_values(self):
        """Charge les valeurs de la pipette existante / Load existing probe values"""
        if self.probe:
            self.name_var.set(self.probe.name)
            self.color_var.set(self.probe.color)
            self.color_preview.config(bg=self.probe.color)
            self.visible_var.set(self.probe.visible)
            self.measure_mode_var.set(self.probe.measure_mode)
        else:
            # Valeurs par défaut pour nouvelle pipette / Default values for new probe
            self.name_var.set(f"{tr('probe_label')} {len(self.flow_model.probes) + 1}")
            # Alterner les couleurs / Alternate colors
            colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336"]
            self.color_var.set(colors[len(self.flow_model.probes) % len(colors)])
            self.color_preview.config(bg=self.color_var.get())
    
    def _save(self):
        """Enregistre la pipette / Save probe"""
        try:
            name = self.name_var.get().strip()
            if not name:
                raise ValueError("Le nom ne peut pas être vide")  # Name cannot be empty
            
            if self.probe:
                # Modifier pipette existante / Modify existing probe
                self.probe.name = name
                self.probe.measure_mode = self.measure_mode_var.get()
                self.probe.color = self.color_var.get()
                self.probe.visible = self.visible_var.get()
                self.result = self.probe
            else:
                # Créer nouvelle pipette / Create new probe
                probe_id = self.flow_model.generate_probe_id()
                # Récupérer max_points depuis main_window si disponible / Get max_points from main_window if available
                max_points = 500000  # Valeur par défaut / Default value
                try:
                    import tkinter as tk
                    root = tk._default_root
                    if root and hasattr(root, 'main_window') and hasattr(root.main_window, 'app_config'):
                        max_points = root.main_window.app_config.PROBE_ANALYSIS_MAX_POINTS
                except:
                    pass
                
                self.result = MeasurementProbe(probe_id, name, self.connection_id, measure_mode=self.measure_mode_var.get(), max_points=max_points)
                self.result.color = self.color_var.get()
                self.result.visible = self.visible_var.get()
                
                # Position par défaut (centre de la connexion) / Default position (center of connection)
                connection = self.flow_model.get_connection(self.connection_id)
                if connection:
                    source_node = self.flow_model.get_node(connection.source_id)
                    target_node = self.flow_model.get_node(connection.target_id)
                    if source_node and target_node:
                        self.result.x = (source_node.x + target_node.x) / 2
                        self.result.y = (source_node.y + target_node.y) / 2
                
                self.flow_model.add_probe(self.result)
            
            if self.on_save_callback:
                self.on_save_callback(self.result)
            
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror(tr('error'), str(e), parent=self)
