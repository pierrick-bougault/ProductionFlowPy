"""Fenêtre de configuration pour une connexion / Connection configuration window"""
import tkinter as tk
from tkinter import ttk
from models.flow_model import Connection
from models.time_converter import TimeUnit, TimeConverter
from gui.translations import tr

class ConnectionConfigDialog(tk.Toplevel):
    """Dialogue de configuration d'une connexion / Connection configuration dialog"""
    
    def __init__(self, parent, connection: Connection, flow_model, on_save_callback=None, on_delete_callback=None):
        super().__init__(parent)
        self.connection = connection
        self.flow_model = flow_model
        self.on_save_callback = on_save_callback
        self.on_delete_callback = on_delete_callback
        
        # Récupérer les nœuds source et cible / Get source and target nodes
        self.source_node = flow_model.get_node(connection.source_id)
        self.target_node = flow_model.get_node(connection.target_id)
        
        self.title(tr('connection_config_title'))
        self.geometry("500x700")  # Taille initiale / Initial size
        self.minsize(400, 400)  # Taille minimale / Minimum size
        self.resizable(True, True)  # Fenêtre redimensionnable / Resizable window
        
        # Rendre la fenêtre modale / Make window modal
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_connection_data()
        
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
        # Create a canvas with scrollbar for scrollable content
        # Utiliser la couleur de fond par défaut du système au lieu de blanc
        # Use default system background color instead of white
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        
        # Frame scrollable qui contiendra tout le contenu / Scrollable frame that will contain all content
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
        # Allow mousewheel scrolling (only when mouse is over canvas)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Stocker le canvas pour le nettoyage / Store canvas for cleanup
        self.canvas = canvas
        
        # Utiliser scrollable_frame au lieu de main_frame / Use scrollable_frame instead of main_frame
        main_frame = self.scrollable_frame
        
        # Informations sur la connexion / Connection information
        info_frame = ttk.LabelFrame(main_frame, text=tr('connection_section'), padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        source_name = self.source_node.name if self.source_node else "?"
        target_name = self.target_node.name if self.target_node else "?"
        
        ttk.Label(info_frame, text=f"{tr('from_label')} {source_name}", font=("Arial", 9)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"{tr('to_label')} {target_name}", font=("Arial", 9)).pack(anchor=tk.W, pady=2)
        
        # Configuration du buffer / Buffer configuration
        buffer_frame = ttk.LabelFrame(main_frame, text=tr('buffer_on_connection'), padding="10")
        buffer_frame.pack(fill=tk.X, pady=10)
        
        # Afficher le buffer / Show buffer
        self.show_buffer_var = tk.BooleanVar()
        ttk.Checkbutton(
            buffer_frame, text=tr('show_buffer_visually'),
            variable=self.show_buffer_var
        ).pack(anchor=tk.W, pady=5)
        
        # Capacité illimitée / Unlimited capacity
        self.buffer_unlimited_var = tk.BooleanVar()
        ttk.Checkbutton(
            buffer_frame, text=tr('unlimited_capacity'),
            variable=self.buffer_unlimited_var,
            command=self._toggle_buffer_capacity
        ).pack(anchor=tk.W, pady=5)
        
        # Capacité / Capacity
        capacity_frame = ttk.Frame(buffer_frame)
        capacity_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(capacity_frame, text=tr('capacity_label')).pack(side=tk.LEFT, padx=5)
        self.buffer_capacity_var = tk.StringVar()
        self.buffer_capacity_entry = ttk.Entry(
            capacity_frame, textvariable=self.buffer_capacity_var, width=15
        )
        self.buffer_capacity_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(capacity_frame, text=tr('units_label')).pack(side=tk.LEFT)
        
        # Taille visuelle / Visual size
        size_frame = ttk.Frame(buffer_frame)
        size_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(size_frame, text=tr('visual_size_label')).pack(side=tk.LEFT, padx=5)
        self.buffer_size_var = tk.StringVar()
        ttk.Entry(size_frame, textvariable=self.buffer_size_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_frame, text=tr('pixels_label')).pack(side=tk.LEFT)
        
        # Conditions initiales / Initial conditions
        ttk.Separator(buffer_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(
            buffer_frame,
            text=tr('initial_conditions'),
            font=("Arial", 9, "bold")
        ).pack(anchor=tk.W, pady=5)
        
        initial_frame = ttk.Frame(buffer_frame)
        initial_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(initial_frame, text=tr('units_at_start')).pack(side=tk.LEFT, padx=5)
        self.initial_buffer_var = tk.StringVar()
        ttk.Entry(initial_frame, textvariable=self.initial_buffer_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(initial_frame, text=tr('units_label')).pack(side=tk.LEFT)
        
        # Description / Description
        ttk.Label(
            buffer_frame,
            text=tr('buffer_description'),
            font=("Arial", 8, "italic"),
            foreground="#666"
        ).pack(anchor=tk.W, pady=10)
        
        # Section Pipettes / Probes section
        self.probe_frame = ttk.LabelFrame(main_frame, text=tr('measurement_probe'), padding="10")
        self.probe_frame.pack(fill=tk.X, pady=10)
        
        # Conteneur pour le contenu dynamique / Container for dynamic content
        self.probe_content_frame = ttk.Frame(self.probe_frame)
        self.probe_content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sera rempli par _update_probe_section / Will be filled by _update_probe_section
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text=tr('save_btn'), command=self._save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=tr('delete_btn'), command=self._delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=tr('cancel_btn'), command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _load_connection_data(self):
        """Charge les données de la connexion dans le formulaire / Load connection data into form"""
        # Affichage du buffer / Buffer display
        self.show_buffer_var.set(self.connection.show_buffer)
        
        # Capacité / Capacity
        if self.connection.buffer_capacity == float('inf'):
            self.buffer_unlimited_var.set(True)
            self.buffer_capacity_var.set("0")
        else:
            self.buffer_unlimited_var.set(False)
            self.buffer_capacity_var.set(str(int(self.connection.buffer_capacity)))
        
        # Taille visuelle / Visual size
        self.buffer_size_var.set(str(self.connection.buffer_visual_size))
        
        # Conditions initiales / Initial conditions
        self.initial_buffer_var.set(str(getattr(self.connection, 'initial_buffer_count', 0)))
        
        self._toggle_buffer_capacity()
        
        # Charger la section pipette / Load probe section
        self._update_probe_section()
    
    def _update_probe_section(self):
        """Met à jour dynamiquement la section pipette / Dynamically update probe section"""
        # Nettoyer le contenu existant / Clean existing content
        for widget in self.probe_content_frame.winfo_children():
            widget.destroy()
        
        # Vérifier s'il y a une pipette sur cette connexion / Check if there's a probe on this connection
        probe = self._get_probe_for_connection()
        
        if probe:
            # Il y a une pipette : afficher les infos et le bouton supprimer
            # There's a probe: show info and delete button
            self._create_probe_config_widgets(probe)
        else:
            # Pas de pipette : afficher le bouton ajouter
            # No probe: show add button
            self._create_add_probe_button()
    
    def _get_probe_for_connection(self):
        """Récupère la pipette associée à cette connexion (s'il y en a une) / Get probe associated with this connection (if any)"""
        for probe in self.flow_model.probes.values():
            if probe.connection_id == self.connection.connection_id:
                return probe
        return None
    
    def _create_add_probe_button(self):
        """Crée le bouton pour ajouter une pipette / Create button to add a probe"""
        info_label = ttk.Label(
            self.probe_content_frame,
            text=tr('no_probe_installed'),
            font=("Arial", 9, "italic"),
            foreground="#666"
        )
        info_label.pack(pady=5)
        
        add_button = ttk.Button(
            self.probe_content_frame,
            text=tr('add_probe_btn'),
            command=self._add_probe
        )
        add_button.pack(pady=10)
    
    def _create_probe_config_widgets(self, probe):
        """Crée les widgets de configuration pour une pipette existante / Create configuration widgets for existing probe"""
        # Nom de la pipette / Probe name
        name_frame = ttk.Frame(self.probe_content_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame, text=tr('probe_name'), font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.probe_name_var = tk.StringVar(value=probe.name)
        ttk.Entry(name_frame, textvariable=self.probe_name_var, width=25).pack(side=tk.LEFT, padx=5)
        
        # Mode de mesure / Measurement mode
        mode_frame = ttk.Frame(self.probe_content_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text=tr('probe_mode'), font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.probe_mode_var = tk.StringVar(value=probe.measure_mode)
        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.probe_mode_var,
            values=["buffer", "cumulative"],
            state="readonly",
            width=15
        )
        mode_combo.pack(side=tk.LEFT, padx=5)
        
        # Description du mode / Mode description
        mode_desc = {
            "buffer": tr('buffer_mode_desc'),
            "cumulative": tr('cumulative_mode_desc')
        }
        self.mode_desc_label = ttk.Label(
            self.probe_content_frame,
            text=mode_desc.get(probe.measure_mode, ""),
            font=("Arial", 8, "italic"),
            foreground="#666",
            wraplength=400
        )
        self.mode_desc_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Mettre à jour la description quand le mode change / Update description when mode changes
        mode_combo.bind("<<ComboboxSelected>>", lambda e: self.mode_desc_label.config(
            text=mode_desc.get(self.probe_mode_var.get(), "")
        ))
        
        # Couleur / Color
        color_frame = ttk.Frame(self.probe_content_frame)
        color_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(color_frame, text=tr('color_label'), font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.probe_color_var = tk.StringVar(value=probe.color)
        
        # Aperçu de couleur / Color preview
        self.color_preview = tk.Label(color_frame, text="  ███  ", fg=probe.color, font=("Arial", 12))
        self.color_preview.pack(side=tk.LEFT, padx=5)
        
        # Bouton pour choisir la couleur / Button to choose color
        def choose_color():
            from tkinter import colorchooser
            color = colorchooser.askcolor(initialcolor=self.probe_color_var.get(), title=tr('choose_color_title'))
            if color and color[1]:
                self.probe_color_var.set(color[1])
                self.color_preview.config(fg=color[1])
        
        ttk.Button(color_frame, text=tr('choose_color'), command=choose_color).pack(side=tk.LEFT, padx=5)
        
        # Statistiques / Statistics
        stats_frame = ttk.LabelFrame(self.probe_content_frame, text=tr('statistics'), padding="5")
        stats_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(stats_frame, text=f"{tr('total_items_passed')} {probe.total_items}").pack(anchor=tk.W, pady=2)
        ttk.Label(stats_frame, text=f"{tr('current_flow_rate')} {probe.current_flow_rate:.2f} {tr('items_per_unit')}").pack(anchor=tk.W, pady=2)
        
        # Bouton d'action / Action button
        action_frame = ttk.Frame(self.probe_content_frame)
        action_frame.pack(pady=10)
        
        ttk.Button(
            action_frame,
            text=tr('delete_probe_btn'),
            command=lambda: self._remove_probe(probe)
        ).pack(padx=5)
    
    def _toggle_buffer_capacity(self):
        """Active/désactive le champ de capacité du buffer / Enable/disable buffer capacity field"""
        if self.buffer_unlimited_var.get():
            self.buffer_capacity_entry.config(state="disabled")
        else:
            self.buffer_capacity_entry.config(state="normal")
    
    def _save(self):
        """Enregistre les modifications / Save modifications"""
        try:
            # Affichage / Display
            self.connection.show_buffer = self.show_buffer_var.get()
            
            # Capacité / Capacity
            if self.buffer_unlimited_var.get():
                self.connection.buffer_capacity = float('inf')
            else:
                capacity_value = float(self.buffer_capacity_var.get())
                if capacity_value <= 0:
                    raise ValueError("La capacité doit être supérieure à 0")
                self.connection.buffer_capacity = capacity_value
            
            # Taille visuelle / Visual size
            size_value = int(self.buffer_size_var.get())
            if size_value <= 0:
                raise ValueError("La taille visuelle doit être supérieure à 0")
            self.connection.buffer_visual_size = size_value
            
            # Conditions initiales / Initial conditions
            initial_value = int(self.initial_buffer_var.get())
            if initial_value < 0:
                raise ValueError("Le nombre d'unités initiales ne peut pas être négatif")
            self.connection.initial_buffer_count = initial_value
            # Mettre à jour aussi current_buffer_count pour l'affichage immédiat
            # Also update current_buffer_count for immediate display
            self.connection.current_buffer_count = initial_value
            
            # Sauvegarder les modifications de la pipette si elle existe
            # Save probe modifications if it exists
            probe = self._get_probe_for_connection()
            if probe and hasattr(self, 'probe_name_var') and hasattr(self, 'probe_mode_var') and hasattr(self, 'probe_color_var'):
                probe.name = self.probe_name_var.get()
                probe.measure_mode = self.probe_mode_var.get()
                probe.color = self.probe_color_var.get()
            
            # Fermer d'abord le dialogue / Close dialog first
            self.destroy()
            
            # Callback pour mettre à jour l'affichage (après la fermeture)
            # Callback to update display (after closing)
            if self.on_save_callback:
                self.on_save_callback()
        
        except ValueError as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror(tr('error'), tr('invalid_value_error').format(error=e))
    
    def _delete(self):
        """Supprime la connexion / Delete connection"""
        from tkinter import messagebox
        if messagebox.askyesno(tr('confirmation'), tr('confirm_delete_connection')):
            # D'abord appeler le callback de suppression / First call delete callback
            if self.on_delete_callback:
                self.on_delete_callback()
            # Puis fermer la fenêtre / Then close window
            self.destroy()
    
    def _add_probe(self):
        """Ajoute une pipette de mesure sur cette connexion / Add measurement probe to this connection"""
        from gui.measurement_probe_config_dialog import MeasurementProbeConfigDialog
        
        def on_save(probe):
            # Notifier via le callback de sauvegarde / Notify via save callback
            if self.on_save_callback:
                self.on_save_callback()
            # Rafraîchir l'affichage / Refresh display
            self._update_probe_section()
        
        dialog = MeasurementProbeConfigDialog(
            self,
            self.flow_model,
            self.connection.connection_id,
            probe=None,
            on_save=on_save
        )
        self.wait_window(dialog)
    
    def _save_probe_changes(self, probe):
        """Sauvegarde les modifications de la pipette / Save probe modifications"""
        # Mettre à jour les propriétés de la pipette / Update probe properties
        probe.name = self.probe_name_var.get()
        probe.measure_mode = self.probe_mode_var.get()
        probe.color = self.probe_color_var.get()
        
        # Notifier via le callback de sauvegarde / Notify via save callback
        if self.on_save_callback:
            self.on_save_callback()
    
    def _remove_probe(self, probe):
        """Supprime la pipette / Delete probe"""
        self.flow_model.remove_probe(probe.probe_id)
        
        # Notifier via le callback de sauvegarde / Notify via save callback
        if self.on_save_callback:
            self.on_save_callback()
        
        # Rafraîchir l'affichage de la section pipette / Refresh probe section display
        self._update_probe_section()
    
    def _save_as(self):
        """Enregistre la connexion sous un nouveau fichier / Save connection as new file"""
        from tkinter import filedialog
        import pickle
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".conn",
            filetypes=[("Connection Config", "*.conn"), ("Tous les fichiers", "*.*")],
            title="Enregistrer la configuration de connexion"
        )
        
        if filename:
            try:
                # Sauvegarder les paramètres de la connexion / Save connection parameters
                data = {
                    'buffer_capacity': self.connection.buffer_capacity,
                    'show_buffer': self.connection.show_buffer
                }
                
                with open(filename, 'wb') as f:
                    pickle.dump(data, f)
                
                from tkinter import messagebox
                messagebox.showinfo(tr('success'), tr('config_saved_to').format(filename=filename))
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror(tr('error'), tr('save_error').format(error=e))
    
    def _center_window(self):
        """Centre la fenêtre sur l'écran / Center window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
