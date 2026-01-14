"""Widget pour afficher les graphiques de mesure / Widget to display measurement graphs"""
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from typing import Dict, List
import threading
from gui.translations import tr

class MeasurementGraphsPanel(ttk.Frame):
    """Panneau pour afficher les graphiques de mesure / Panel to display measurement graphs"""
    
    def __init__(self, parent, flow_model, flow_canvas=None, main_window=None):
        super().__init__(parent)
        self.configure(style='Gray.TFrame')
        self.flow_model = flow_model
        self.flow_canvas = flow_canvas
        self.graphs = {}  # probe_id -> (fig, ax, canvas, graph_frame, toolbar, controls)
        self.parent = parent
        self.main_window = main_window
        
        # Cache des couleurs par type d'item / Color cache per item type
        self._item_type_colors = {}
        self._build_item_type_colors_cache()
        
        # Paramètres de configuration / Configuration parameters
        self.graph_height = 2.0  # Hauteur des graphiques en pouces / Graph height in inches
        
        # Fenêtre glissante temporelle / Temporal sliding window
        self.time_window_enabled = True  # Activé par défaut / Enabled by default
        self.time_window_duration = 20.0  # Durée par défaut (en unités de temps simulation) / Default duration (in simulation time units)
        
        # Navigation temporelle / Time navigation
        self.time_offset = 0.0  # Décalage temporel pour la navigation (0 = temps actuel) / Time offset for navigation (0 = current time)
        self.time_slider_max = 100.0  # Plage maximale du curseur (en unités de temps) / Maximum slider range (in time units)
        
        # Options d'affichage par pipette / Display options per probe
        self.probe_display_options = {}  # probe_id -> {'show_in': bool, 'show_out': bool, 'time_range': (min, max) or None}
        
        # Mode d'affichage : False = général, True = détaillé par type
        # Display mode: False = general, True = detailed by type
        self.show_type_detail = False
        
        # Protection thread-safe pour éviter les conflits pendant la simulation
        # Thread-safe protection to avoid conflicts during simulation
        self.update_lock = threading.Lock()
        self.pending_updates = set()  # probe_ids en attente de mise à jour
        
        # Frame principale avec scrollbar / Main frame with scrollbar
        self.canvas_frame = tk.Canvas(self, bg='#f0f0f0')
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas_frame.yview)
        self.scrollable_frame = ttk.Frame(self.canvas_frame, style='Gray.TFrame')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_frame.configure(scrollregion=self.canvas_frame.bbox("all"))
        )
        
        self.canvas_frame.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_frame.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Binding de la molette de souris pour le scroll
        # Mousewheel binding for scroll
        self.canvas_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        # Binding global quand la souris entre dans le widget
        # Global binding when mouse enters widget
        self.canvas_frame.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.canvas_frame.bind("<Leave>", lambda e: self._unbind_mousewheel())
        
        # Frame de contrôle en haut / Control frame at top
        self.control_frame = ttk.LabelFrame(self.scrollable_frame, text=tr('measurement_probes'), padding="5")
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.probe_checkboxes = {}  # probe_id -> (var, checkbox)
        
        # Contrôles globaux pour tous les graphiques / Global controls for all graphs
        self.global_controls_frame = ttk.Frame(self.control_frame)
        self.global_controls_frame.pack(fill=tk.X, pady=5)
        
        # Ligne 1 : Affichage / Line 1: Display
        line1 = ttk.Frame(self.global_controls_frame)
        line1.pack(fill=tk.X, pady=2)
        
        ttk.Label(line1, text=tr('display_label')).pack(side=tk.LEFT, padx=5)
        
        self.global_show_in_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            line1,
            text=tr('entries_checkbox'),
            variable=self.global_show_in_var,
            command=self._toggle_all_events
        ).pack(side=tk.LEFT, padx=5)
        
        self.global_show_out_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            line1,
            text=tr('exits_checkbox'),
            variable=self.global_show_out_var,
            command=self._toggle_all_events
        ).pack(side=tk.LEFT, padx=5)
        
        # Bouton Maintenant à côté de Sorties / Now button next to Exits
        ttk.Button(
            line1,
            text=tr('now_btn'),
            command=self._reset_time_navigation
        ).pack(side=tk.LEFT, padx=10)
        
        # Bouton pour basculer entre affichage général et détaillé par type
        # Button to toggle between general and detailed by type display
        self.type_detail_btn = ttk.Button(
            line1,
            text=tr('detail_btn'),
            command=self._toggle_type_detail
        )
        self.type_detail_btn.pack(side=tk.LEFT, padx=10)
        
        # Ligne 2 : Curseur de navigation temporelle / Line 2: Time navigation slider
        line3 = ttk.Frame(self.global_controls_frame)
        line3.pack(fill=tk.X, pady=5)
        
        ttk.Label(line3, text=tr('navigation_label')).pack(side=tk.LEFT, padx=5)
        
        # Bouton pour reculer rapidement / Button to quickly go back
        ttk.Button(
            line3,
            text="◀◀",
            width=3,
            command=lambda: self._shift_time(-10)
        ).pack(side=tk.LEFT, padx=2)
        
        # Slider de navigation / Navigation slider
        self.time_slider_var = tk.DoubleVar(value=0.0)
        self.time_slider = ttk.Scale(
            line3,
            from_=-100.0,
            to=0.0,
            variable=self.time_slider_var,
            orient=tk.HORIZONTAL,
            command=self._on_slider_change
        )
        self.time_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Bouton pour avancer rapidement / Button to quickly go forward
        ttk.Button(
            line3,
            text="▶▶",
            width=3,
            command=lambda: self._shift_time(10)
        ).pack(side=tk.LEFT, padx=2)
        
        # Label pour afficher la position / Label to display position
        self.time_position_label = ttk.Label(line3, text="0.0", width=10)
        self.time_position_label.pack(side=tk.LEFT, padx=5)
        
        # Référence pour le label "aucune pipette" / Reference for "no probe" label
        self.no_probes_label = None
    
    def _on_mousewheel(self, event):
        """Gestion du scroll avec la molette de souris / Handle scroll with mousewheel"""
        self.canvas_frame.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _bind_mousewheel(self):
        """Lie la molette de souris au scroll quand la souris entre dans le widget
        Bind mousewheel to scroll when mouse enters widget"""
        self.canvas_frame.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _unbind_mousewheel(self):
        """Délie la molette de souris quand la souris sort du widget
        Unbind mousewheel when mouse leaves widget"""
        self.canvas_frame.unbind_all("<MouseWheel>")
        
    def update_probe_list(self):
        """Met à jour la liste des pipettes / Update probe list"""
        # Nettoyer les anciens checkboxes SAUF les contrôles globaux
        # Clean old checkboxes EXCEPT global controls
        for widget in self.control_frame.winfo_children():
            # Ne garder que les contrôles globaux / Only keep global controls
            if widget != self.global_controls_frame:
                widget.destroy()
        
        self.probe_checkboxes.clear()
        
        # Les contrôles globaux doivent rester en haut / Global controls must stay at top
        self.global_controls_frame.pack(fill=tk.X, pady=5)
        
        if not self.flow_model.probes:
            # Créer le label "aucune pipette" / Create "no probe" label
            self.no_probes_label = ttk.Label(
                self.control_frame,
                text=tr('no_probe_installed'),
                foreground="#666",
                font=("Arial", 9, "italic")
            )
            self.no_probes_label.pack(pady=10)
            return
        
        # Si on a des pipettes, le label n'est plus nécessaire
        # If we have probes, label is no longer needed
        self.no_probes_label = None
        
        # Créer un checkbox pour chaque pipette / Create checkbox for each probe
        for probe_id, probe in self.flow_model.probes.items():
            var = tk.BooleanVar(value=probe.visible)
            
            frame = ttk.Frame(self.control_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # Indicateur de couleur (d'abord) / Color indicator (first)
            color_label = tk.Label(frame, text="  ", bg=probe.color, width=2)
            color_label.pack(side=tk.LEFT, padx=(5, 2))
            
            # Checkbox avec le nom / Checkbox with name
            cb = ttk.Checkbutton(
                frame,
                text=f"{probe.name} (Connexion: {probe.connection_id})",
                variable=var,
                command=lambda p=probe: self.toggle_probe_visibility(p)
            )
            cb.pack(side=tk.LEFT, padx=2)
            
            # Bouton pour supprimer (juste après) / Delete button (just after)
            delete_btn = ttk.Button(
                frame,
                text="✕",
                width=3,
                command=lambda pid=probe_id: self.delete_probe(pid)
            )
            delete_btn.pack(side=tk.LEFT, padx=2)
            
            self.probe_checkboxes[probe_id] = (var, cb)
    
    def _toggle_all_events(self):
        """Active/désactive l'affichage des événements pour tous les graphiques
        Enable/disable event display for all graphs"""
        for probe_id in self.graphs.keys():
            probe = self.flow_model.probes.get(probe_id)
            if probe:
                self.update_graph(probe)
    
    def _on_slider_change(self, value):
        """Gère le changement de position du slider / Handle slider position change"""
        self.time_offset = float(value)
        self.time_position_label.config(text=f"{self.time_offset:.1f}")
        # Mettre à jour la plage du slider dynamiquement / Update slider range dynamically
        self._update_slider_range()
        # Rafraîchir tous les graphiques avec le nouvel offset / Refresh all graphs with new offset
        for probe_id in self.graphs.keys():
            probe = self.flow_model.probes.get(probe_id)
            if probe:
                self.update_graph(probe)
    
    def _shift_time(self, delta):
        """Décale le temps de delta unités / Shift time by delta units"""
        new_offset = self.time_offset + delta
        # Limiter à la plage du slider (utilise time_slider_max dynamique)
        # Limit to slider range (uses dynamic time_slider_max)
        new_offset = max(-self.time_slider_max, min(0.0, new_offset))
        self.time_slider_var.set(new_offset)
        self._on_slider_change(new_offset)
    
    def _reset_time_navigation(self):
        """Réinitialise la navigation au temps actuel / Reset navigation to current time"""
        self.time_slider_var.set(0.0)
        self._on_slider_change(0.0)
    
    def _toggle_type_detail(self):
        """Bascule entre affichage général et détaillé par type
        Toggle between general and detailed by type display"""
        self.show_type_detail = not self.show_type_detail
        # Mettre à jour le texte du bouton / Update button text
        if self.show_type_detail:
            self.type_detail_btn.config(text=tr('general_btn'))
        else:
            self.type_detail_btn.config(text=tr('detail_btn'))
        # Rafraîchir le cache des couleurs / Refresh color cache
        self._build_item_type_colors_cache()
        # Rafraîchir tous les graphiques avec le nouveau mode / Refresh all graphs with new mode
        for probe_id in self.graphs.keys():
            probe = self.flow_model.probes.get(probe_id)
            if probe:
                self.update_graph(probe)
    
    def _build_item_type_colors_cache(self):
        """Construit le cache des couleurs par type d'item depuis les sources
        Build color cache per item type from sources"""
        self._item_type_colors.clear()
        # Parcourir tous les nœuds sources pour récupérer les couleurs des types
        # Loop through all source nodes to get type colors
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    # Utiliser le nom du type comme clé (car c'est ce qui est affiché dans les graphiques)
                    # Use type name as key (since that's what's displayed in graphs)
                    self._item_type_colors[item_type.name] = item_type.color
    
    def _update_slider_range(self):
        """Met à jour dynamiquement la plage maximale du curseur basée sur le temps max de simulation
        Dynamically update slider max range based on max simulation time"""
        # Calculer le temps maximum à partir de toutes les pipettes
        # Calculate max time from all probes
        max_time = 0.0
        for probe_id, probe in self.flow_model.probes.items():
            data = probe.get_data()
            if data:
                times = [t for t, _ in data]
                if times:
                    max_time = max(max_time, max(times))
        
        # La plage du slider doit permettre de remonter jusqu'au début
        # Slider range must allow going back to beginning
        # Minimum de 10 unités pour éviter une plage trop petite
        # Minimum of 10 units to avoid too small range
        new_range = max(10.0, max_time)
        self.time_slider_max = new_range
        
        # Mettre à jour la plage du slider / Update slider range
        current_value = self.time_slider_var.get()
        self.time_slider.config(from_=-new_range)
        
        # Ajuster la valeur actuelle si elle dépasse la nouvelle limite
        # Adjust current value if it exceeds new limit
        if current_value < -new_range:
            self.time_slider_var.set(-new_range)
            self._on_slider_change(-new_range)
    
    def set_graph_height(self, height):
        """Change la hauteur des graphiques et les recrée / Change graph height and recreate them"""
        self.graph_height = height
        # Forcer la recréation complète de tous les graphiques avec la nouvelle taille
        # Force complete recreation of all graphs with new size
        # Détruire tous les graphiques existants / Destroy all existing graphs
        for probe_id in list(self.graphs.keys()):
            fig, ax, canvas, graph_frame = self.graphs[probe_id]
            graph_frame.destroy()
            plt.close(fig)
        self.graphs.clear()
        
        # Recréer tous les graphiques visibles / Recreate all visible graphs
        for probe_id, probe in self.flow_model.probes.items():
            if probe.visible:
                self.create_graph(probe)
    
    def set_time_window(self, enabled, duration):
        """Configure la fenêtre glissante temporelle / Configure temporal sliding window"""
        self.time_window_enabled = enabled
        self.time_window_duration = duration
        # Rafraîchir tous les graphiques pour appliquer le changement
        # Refresh all graphs to apply change
        self.refresh_graphs()
    
    def toggle_probe_visibility(self, probe):
        """Active/désactive la visibilité d'une pipette / Enable/disable probe visibility"""
        probe.visible = not probe.visible
        self.refresh_graphs()
    
    def delete_probe(self, probe_id):
        """Supprime une pipette / Delete probe"""
        if probe_id in self.graphs:
            # Détruire le widget du graphique / Destroy graph widget
            fig, ax, canvas, graph_frame = self.graphs[probe_id]
            graph_frame.destroy()
            plt.close(fig)
            del self.graphs[probe_id]
        
        # Supprimer du canvas (objets visuels) / Remove from canvas (visual objects)
        if self.flow_canvas:
            self.flow_canvas.remove_probe(probe_id)
        else:
            # Fallback si pas de canvas / Fallback if no canvas
            self.flow_model.remove_probe(probe_id)
        
        self.update_probe_list()
        self.refresh_graphs()
    
    def refresh_graphs(self):
        """Rafraîchit tous les graphiques / Refresh all graphs"""
        # Nettoyer les anciens graphiques / Clean old graphs
        for probe_id in list(self.graphs.keys()):
            if probe_id not in self.flow_model.probes or not self.flow_model.probes[probe_id].visible:
                fig, ax, canvas, graph_frame = self.graphs[probe_id]
                graph_frame.destroy()
                plt.close(fig)
                del self.graphs[probe_id]
        
        # Créer/mettre à jour les graphiques visibles / Create/update visible graphs
        for probe_id, probe in self.flow_model.probes.items():
            if probe.visible:
                if probe_id not in self.graphs:
                    self.create_graph(probe)
                else:
                    self.update_graph(probe)
    
    def clear_all_graphs(self):
        """Efface complètement tous les graphiques / Completely clear all graphs"""
        # Fermer et détruire tous les graphiques / Close and destroy all graphs
        for probe_id in list(self.graphs.keys()):
            fig, ax, canvas, graph_frame = self.graphs[probe_id]
            graph_frame.destroy()
            plt.close(fig)
        
        # Vider le dictionnaire / Empty dictionary
        self.graphs.clear()
        
        # Réinitialiser les options d'affichage / Reset display options
        self.probe_display_options.clear()
        
        # Réinitialiser la navigation temporelle / Reset time navigation
        self.time_offset = 0.0
    
    def create_graph(self, probe):
        """Crée un nouveau graphique pour une pipette / Create new graph for probe"""
        # Initialiser les options d'affichage si nécessaire / Initialize display options if needed
        if probe.probe_id not in self.probe_display_options:
            self.probe_display_options[probe.probe_id] = {
                'show_in': True,
                'show_out': True,
                'time_range': None
            }
        
        # Frame pour le graphique / Frame for graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"{probe.name}",
            padding="1"
        )
        graph_frame.pack(fill=tk.X, expand=False, padx=2, pady=2)
        
        # Calculer la largeur disponible dynamiquement / Calculate available width dynamically
        self.update_idletasks()
        available_width = max(300, self.winfo_width() - 40)  # -40 pour scrollbar et marges / -40 for scrollbar and margins
        
        # Créer une figure adaptée à la largeur disponible / Create figure adapted to available width
        fig_width_inches = available_width / 80.0  # 80 DPI
        fig_height_inches = self.graph_height  # Hauteur configurable / Configurable height
        
        fig = Figure(figsize=(fig_width_inches, fig_height_inches), dpi=80)
        ax = fig.add_subplot(111)
        
        ax.tick_params(labelsize=9)
        ax.grid(True, alpha=0.3)
        
        # Optimiser les marges (réduites car pas de labels)
        # Optimize margins (reduced because no labels)
        fig.subplots_adjust(left=0.10, right=0.96, top=0.95, bottom=0.10)
        
        # Canvas qui s'adapte à la figure exacte sans espace supplémentaire
        # Canvas that adapts to exact figure without extra space
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        # Taille exacte de la figure convertie en pixels / Exact figure size converted to pixels
        canvas_widget.config(width=int(fig_width_inches * 80), height=int(fig_height_inches * 80))
        canvas_widget.pack(padx=0, pady=0)
        
        self.graphs[probe.probe_id] = (fig, ax, canvas, graph_frame)
        
        # Première mise à jour / First update
        self.update_graph(probe)

    def _bind_resize_handlers(self, graph_frame, canvas):
        """Lie les événements de redimensionnement pour adapter le canvas sans masquer le bas.
        Bind resize events to adapt canvas without hiding bottom."""
        try:
            root = self.winfo_toplevel()
        except Exception:
            root = None

        def _on_resize(event=None):
            # Ignorer les événements pendant le chargement initial
            # Ignore events during initial loading
            if not root or not root.winfo_viewable():
                return
            # Vérifier si la fenetre est en cours d'initialisation
            # Check if window is being initialized
            if self.main_window and getattr(self.main_window, 'is_initializing', False):
                return
            # Réserver de l'espace pour les contrôles bas (toolbar/status)
            # Reserve space for bottom controls (toolbar/status)
            reserved = 140
            available = root.winfo_height() - reserved
            height = max(200, available)
            widget = canvas.get_tk_widget()
            widget.configure(height=height)

        if root:
            root.bind('<Configure>', lambda e: _on_resize(e), add='+')
    

    
    def _reset_zoom(self, probe_id):
        """Réinitialise le zoom d'un graphique / Reset graph zoom"""
        if probe_id in self.probe_display_options:
            self.probe_display_options[probe_id]['time_range'] = None
            
            # Mettre à jour le graphique / Update graph
            probe = self.flow_model.probes.get(probe_id)
            if probe:
                self.update_graph(probe)
    
    def _zoom_in(self, probe_id):
        """Zoom avant sur le graphique / Zoom in on graph"""
        probe = self.flow_model.probes.get(probe_id)
        if not probe:
            return
        
        data = probe.get_data()
        if not data:
            return
        
        times = [t for t, _ in data]
        if not times:
            return
        
        # Obtenir la plage actuelle / Get current range
        current_range = self.probe_display_options.get(probe_id, {}).get('time_range')
        if current_range:
            t_min, t_max = current_range
        else:
            t_min, t_max = min(times), max(times)
        
        # Réduire la plage de 50% en zoomant vers le centre
        # Reduce range by 50% by zooming towards center
        span = t_max - t_min
        center = (t_min + t_max) / 2
        new_span = span * 0.5
        
        new_t_min = max(min(times), center - new_span / 2)
        new_t_max = min(max(times), center + new_span / 2)
        
        # Appliquer le nouveau zoom / Apply new zoom
        self.probe_display_options[probe_id]['time_range'] = (new_t_min, new_t_max)
        
        self.update_graph(probe)
    
    def _zoom_out(self, probe_id):
        """Zoom arrière sur le graphique / Zoom out on graph"""
        probe = self.flow_model.probes.get(probe_id)
        if not probe:
            return
        
        data = probe.get_data()
        if not data:
            return
        
        times = [t for t, _ in data]
        if not times:
            return
        
        # Obtenir la plage actuelle / Get current range
        current_range = self.probe_display_options.get(probe_id, {}).get('time_range')
        if current_range:
            t_min, t_max = current_range
        else:
            t_min, t_max = min(times), max(times)
        
        # Augmenter la plage de 100% en dézoomant depuis le centre
        # Increase range by 100% by zooming out from center
        span = t_max - t_min
        center = (t_min + t_max) / 2
        new_span = span * 2.0
        
        new_t_min = max(min(times), center - new_span / 2)
        new_t_max = min(max(times), center + new_span / 2)
        
        # Si on atteint les limites, réinitialiser / If we reach limits, reset
        if new_t_min <= min(times) and new_t_max >= max(times):
            self._reset_zoom(probe_id)
            return
        
        # Appliquer le nouveau zoom
        self.probe_display_options[probe_id]['time_range'] = (new_t_min, new_t_max)
        
        self.update_graph(probe)
    
    def update_graph(self, probe):
        """Met à jour un graphique existant / Update existing graph"""
        if probe.probe_id not in self.graphs:
            return
        
        fig, ax, canvas, graph_frame = self.graphs[probe.probe_id]
        # Utiliser les contrôles globaux pour show_in et show_out
        # Use global controls for show_in and show_out
        options = {
            'show_in': self.global_show_in_var.get(),
            'show_out': self.global_show_out_var.get(),
            'time_range': None  # Ne pas utiliser les plages individuelles, utiliser le slider global / Don't use individual ranges, use global slider
        }
        
        # Effacer et redessiner / Clear and redraw
        ax.clear()
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        
        # Obtenir les données / Get data
        data = probe.get_data()
        
        # Déterminer la plage de temps à appliquer (toujours utiliser le slider global)
        # Determine time range to apply (always use global slider)
        user_time_range = None
        
        if data:
            # Vérifier si on doit afficher le mode détaillé par type
            # Check if we should display detailed by type mode
            if self.show_type_detail:
                # Mode détaillé : graphique empilé par type d'item
                # Detailed mode: stacked chart by item type
                type_data = probe.get_type_data()
                if not type_data:
                    times = []
                    values = []
                else:
                    times = [t for t, _ in type_data]
                    type_counts_list = [tc for _, tc in type_data]
                    
                    # Appliquer le filtre de plage de temps / Apply time range filter
                    if user_time_range:
                        time_range = user_time_range
                    elif self.time_window_enabled and times:
                        max_time = max(times) + self.time_offset
                        min_time = max(0, max_time - self.time_window_duration)
                        time_range = (min_time, max_time)
                    else:
                        time_range = None
                    
                    if time_range:
                        filtered_data = [(t, tc) for t, tc in zip(times, type_counts_list) if time_range[0] <= t <= time_range[1]]
                        if filtered_data:
                            times, type_counts_list = zip(*filtered_data)
                            times, type_counts_list = list(times), list(type_counts_list)
                        else:
                            times, type_counts_list = [], []
                    
                    # Obtenir tous les types d'items / Get all item types
                    all_types = probe.get_all_item_types()
                    
                    if times and all_types:
                        # Préparer les données pour chaque type / Prepare data for each type
                        type_data_dict = {item_type: [] for item_type in all_types}
                        for type_counts in type_counts_list:
                            for item_type in all_types:
                                type_data_dict[item_type].append(type_counts.get(item_type, 0))
                        
                        # Récupérer les couleurs configurées pour chaque type
                        # Get configured colors for each type
                        self._build_item_type_colors_cache()  # Rafraîchir le cache / Refresh cache
                        colors_default = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', 
                                  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B195', '#C06C84']
                        
                        # Dessiner le graphique empilé / Draw stacked chart
                        bottom = [0] * len(times)
                        for i, item_type in enumerate(all_types):
                            vals = type_data_dict[item_type]
                            # Utiliser la couleur configurée ou une couleur par défaut
                            # Use configured color or default color
                            color = self._item_type_colors.get(item_type, colors_default[i % len(colors_default)])
                            
                            # Dessiner la zone empilée / Draw stacked area
                            if probe.measure_mode == "cumulative":
                                # Pour les pipettes cumulatives, utiliser une interpolation linéaire
                                # For cumulative probes, use linear interpolation
                                ax.fill_between(times, bottom, [b + v for b, v in zip(bottom, vals)], 
                                                label=item_type, alpha=0.7, color=color)
                                # Ajouter une ligne de contour pour mieux voir les changements
                                # Add contour line to better see changes
                                ax.plot(times, [b + v for b, v in zip(bottom, vals)], 
                                       color=color, linewidth=1.5, alpha=0.9)
                            else:
                                # Pour les pipettes buffer, utiliser step='post' (aspect marches)
                                # For buffer probes, use step='post' (staircase look)
                                ax.fill_between(times, bottom, [b + v for b, v in zip(bottom, vals)], 
                                                label=item_type, alpha=0.7, color=color, step='post')
                            
                            bottom = [b + v for b, v in zip(bottom, vals)]
                        
                        # Ajouter la légende avec une taille de police légèrement plus grande
                        # Add legend with slightly larger font size
                        ax.legend(loc='upper left', fontsize=8)
                        values = bottom  # Pour les événements, utiliser le total / For events, use total
                    else:
                        times, values = [], []
            else:
                # Mode général : graphique normal (buffer ou cumulatif)
                # General mode: normal chart (buffer or cumulative)
                times = [t for t, _ in data]
                values = [v for _, v in data]
                
                if user_time_range:
                    time_range = user_time_range
                elif self.time_window_enabled and times:
                    max_time = max(times) + self.time_offset
                    min_time = max(0, max_time - self.time_window_duration)
                    time_range = (min_time, max_time)
                else:
                    time_range = None
                
                # Appliquer le filtre de plage de temps si défini
                # Apply time range filter if defined
                if time_range:
                    filtered_data = [(t, v) for t, v in zip(times, values) if time_range[0] <= t <= time_range[1]]
                    if filtered_data:
                        times, values = zip(*filtered_data)
                        times, values = list(times), list(values)
                    else:
                        times, values = [], []
                
                if times and values:
                    ax.step(times, values, where='post', color=probe.color, linewidth=2)
                    ax.fill_between(times, values, alpha=0.3, color=probe.color, step='post')
        else:
            times, values = [], []
        
        # Ajouter les événements d'entrée et de sortie
        # Add input and output events
        # Seulement si on a des données dans la plage visible (courbe affichée)
        # Only if we have data in the visible range (curve displayed)
        if hasattr(probe, 'events') and probe.events and data and times and values:
            # Créer un dictionnaire temps -> valeur du buffer pour interpolation
            # Create time -> buffer value dictionary for interpolation
            # IMPORTANT: Utiliser les données FILTRÉES (times/values), pas les données originales (data)
            # IMPORTANT: Use FILTERED data (times/values), not original data (data)
            # pour éviter d'afficher des événements en dehors de la plage visible
            # to avoid displaying events outside the visible range
            time_to_value = {t: v for t, v in zip(times, values)}
            
            # Fonction pour trouver la valeur du buffer à un temps donné
            # Function to find buffer value at given time
            def get_buffer_value_at_time(event_time):
                if event_time in time_to_value:
                    return time_to_value[event_time]
                
                if not time_to_value:
                    return None
                
                times_list = sorted(time_to_value.keys())
                min_time_data = times_list[0]
                max_time_data = times_list[-1]
                
                # Vérifier que l'événement est dans la plage des données disponibles
                # Check that event is in available data range
                # Si l'événement est avant ou après les données, retourner None
                # If event is before or after data, return None
                if event_time < min_time_data or event_time > max_time_data:
                    return None
                
                before_time = None
                after_time = None
                for t in times_list:
                    if t <= event_time:
                        before_time = t
                    if t >= event_time and after_time is None:
                        after_time = t
                        break
                
                if before_time is not None and after_time is not None and before_time != after_time:
                    # Interpolation linéaire / Linear interpolation
                    before_val = time_to_value[before_time]
                    after_val = time_to_value[after_time]
                    ratio = (event_time - before_time) / (after_time - before_time)
                    return before_val + (after_val - before_val) * ratio
                elif before_time is not None:
                    return time_to_value[before_time]
                elif after_time is not None:
                    return time_to_value[after_time]
                else:
                    return None  # Pas de données disponibles pour cet événement / No data available for this event
            
            # Filtrer les événements par plage de temps (utiliser la même time_range que pour la courbe)
            # Filter events by time range (use same time_range as for the curve)
            filtered_events = probe.events
            if time_range:
                filtered_events = [(t, q, evt) for t, q, evt in probe.events if time_range[0] <= t <= time_range[1]]
            
            # Séparer les événements par type avec leurs hauteurs
            # Separate events by type with their heights
            in_times = []
            in_values = []
            out_times = []
            out_values = []
            
            for t, q, evt_type in filtered_events:
                buffer_value = get_buffer_value_at_time(t)
                # Ne garder que les événements qui ont une valeur buffer valide (dans la plage)
                # Keep only events with valid buffer value (in range)
                if buffer_value is not None:
                    if evt_type == 'in':
                        in_times.append(t)
                        in_values.append(buffer_value)
                    else:  # 'out'
                        out_times.append(t)
                        out_values.append(buffer_value)
            
            # Affichage intelligent adapté au nombre d'événements
            # Smart display adapted to number of events
            total_events = len(in_times) + len(out_times)
            
            if total_events > 100:
                # MODE HAUTE DENSITÉ : Utiliser des barres verticales avec transparence
                # HIGH DENSITY MODE: Use vertical bars with transparency
                if in_times and options.get('show_in', True):
                    for t in in_times:
                        ax.axvline(x=t, color='green', alpha=0.15, linewidth=0.5, zorder=3)
                    # Afficher quelques marqueurs échantillonnés pour la légende
                    # Display some sampled markers for legend
                    sample_indices = [i * len(in_times) // 10 for i in range(min(10, len(in_times)))]
                    sample_times = [in_times[i] for i in sample_indices]
                    sample_values = [in_values[i] for i in sample_indices]
                    ax.scatter(sample_times, sample_values, 
                              marker='^', s=30, c='green', alpha=0.8, 
                              label=f'Entrées ({len(in_times)})', zorder=5)
                
                if out_times and options.get('show_out', True):
                    for t in out_times:
                        ax.axvline(x=t, color='red', alpha=0.15, linewidth=0.5, zorder=3)
                    # Afficher quelques marqueurs échantillonnés pour la légende
                    # Display some sampled markers for legend
                    sample_indices = [i * len(out_times) // 10 for i in range(min(10, len(out_times)))]
                    sample_times = [out_times[i] for i in sample_indices]
                    sample_values = [out_values[i] for i in sample_indices]
                    ax.scatter(sample_times, sample_values, 
                              marker='v', s=30, c='red', alpha=0.8, 
                              label=f'Sorties ({len(out_times)})', zorder=5)
                
            elif total_events > 50:
                # MODE DENSITÉ MOYENNE : Échantillonnage intelligent
                # MEDIUM DENSITY MODE: Smart sampling
                sample_rate = max(1, total_events // 50)  # Garder ~50 marqueurs max / Keep ~50 markers max
                
                if in_times and options.get('show_in', True):
                    sampled_in_times = in_times[::sample_rate]
                    sampled_in_values = in_values[::sample_rate]
                    marker_size = 50
                    ax.scatter(sampled_in_times, sampled_in_values, 
                              marker='^', s=marker_size, c='green', alpha=0.7, 
                              label=f'Entrées ({len(in_times)}, affiché: {len(sampled_in_times)})', 
                              zorder=5, edgecolors='darkgreen', linewidths=1)
                
                if out_times and options.get('show_out', True):
                    sampled_out_times = out_times[::sample_rate]
                    sampled_out_values = out_values[::sample_rate]
                    marker_size = 50
                    ax.scatter(sampled_out_times, sampled_out_values, 
                              marker='v', s=marker_size, c='red', alpha=0.7, 
                              label=f'Sorties ({len(out_times)}, affiché: {len(sampled_out_times)})', 
                              zorder=5, edgecolors='darkred', linewidths=1)
            else:
                # MODE NORMAL : Afficher tous les marqueurs avec taille adaptative
                # NORMAL MODE: Display all markers with adaptive size
                marker_size = 100
                if total_events > 0:
                    # Calculer la plage de temps visible
                    # Calculate visible time range
                    if time_range:
                        visible_time_span = time_range[1] - time_range[0]
                    else:
                        visible_time_span = max(times) - min(times) if times else 1
                    
                    # Adapter la taille selon la densité
                    # Adapt size based on density
                    density = total_events / max(visible_time_span, 1)
                    if density > 2:
                        marker_size = max(30, 100 - int(density * 15))
                    elif density > 1:
                        marker_size = max(50, 100 - int(density * 20))
                
                # Marqueurs pour les entrées / Markers for inputs
                if in_times and options.get('show_in', True):
                    ax.scatter(in_times, in_values, 
                              marker='^', s=marker_size, c='green', alpha=0.7, 
                              zorder=5, 
                              edgecolors='darkgreen', linewidths=1)
                
                # Marqueurs pour les sorties / Markers for outputs
                if out_times and options.get('show_out', True):
                    ax.scatter(out_times, out_values, 
                              marker='v', s=marker_size, c='red', alpha=0.7, 
                              zorder=5, 
                              edgecolors='darkred', linewidths=1)

        
        # Ne pas appliquer de plage individuelle - tous les graphiques partagent la même fenêtre temporelle
        # Don't apply individual range - all graphs share the same time window
        # déterminée par le slider global et time_window_enabled
        # determined by global slider and time_window_enabled
        
        # Ajuster les marges pour un affichage correct
        # Adjust margins for correct display
        fig.tight_layout(pad=1.5)
        
        # Dessiner uniquement si on détient le verrou (évite les conflits)
        # Draw only if we hold the lock (avoids conflicts)
        try:
            canvas.draw()
        except:
            # Ignorer les erreurs de dessin pendant les mises à jour concurrentes
            # Ignore drawing errors during concurrent updates
            pass
    
    def update_all_graphs(self):
        """Met à jour tous les graphiques visibles de manière thread-safe
        Update all visible graphs in thread-safe manner"""
        # Utiliser after_idle pour mettre à jour dans le thread GUI
        # Use after_idle to update in GUI thread
        self.after_idle(self._do_update_all_graphs)
    
    def _do_update_all_graphs(self):
        """Effectue réellement la mise à jour dans le thread GUI
        Actually perform update in GUI thread"""
        if not self.update_lock.acquire(blocking=False):
            # Si on ne peut pas obtenir le verrou, réessayer plus tard
            # If we can't get lock, try again later
            self.after(100, self.update_all_graphs)
            return
        
        try:
            for probe_id, probe in self.flow_model.probes.items():
                if probe.visible and probe_id in self.graphs:
                    try:
                        self.update_graph(probe)
                    except:
                        # Ignorer les erreurs individuelles / Ignore individual errors
                        pass
        finally:
            self.update_lock.release()
