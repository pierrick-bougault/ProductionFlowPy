"""Fenêtre plein écran pour visualiser les graphiques d'analyse / Full screen window to display analysis graphs"""
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import numpy as np
from gui.translations import tr

class AnalysisGraphWindow:
    """Fenêtre plein écran pour afficher les graphiques d'analyse / Full screen window to display analysis graphs"""
    
    def __init__(self, parent, results, flow_model, selected_graphs, time_unit_var):
        self.parent = parent
        self.results = results
        self.flow_model = flow_model
        self.selected_graphs = selected_graphs
        self.time_unit_var = time_unit_var
        
        # Créer la fenêtre / Create the window
        self.window = tk.Toplevel(parent)
        self.window.title(tr('analysis_graphs'))
        
        # Mettre en plein écran / Set to full screen
        self.window.state('zoomed')  # Pour Windows / For Windows
        # Alternative pour d'autres OS: / Alternative for other OS:
        # self.window.attributes('-zoomed', True)  # Pour Linux / For Linux
        # self.window.attributes('-fullscreen', True)  # Pour tous / For all
        
        # Permettre de sortir du plein écran avec Echap / Allow exiting full screen with Escape
        self.window.bind('<Escape>', lambda e: self.window.state('normal'))
        
        # Régénérer les graphiques lors du redimensionnement (avec debounce) / Regenerate graphs on resize (with debounce)
        self._resize_timer = None
        self._last_width = 0
        self._initial_load = True  # Flag pour éviter double chargement / Flag to avoid double loading
        self.window.bind('<Configure>', self._on_window_resize)
        
        # Frame principal avec fond gris / Main frame with gray background
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.configure(style='Gray.TFrame')
        
        # Variables de configuration / Configuration variables
        self.cols_var = tk.IntVar(value=3)
        self.graph_height_var = tk.IntVar(value=400)
        
        # Barre de menu / Menu bar
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        
        # Menu Paramètres / Settings menu
        params_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=tr('settings'), menu=params_menu)
        params_menu.add_command(label=tr('grid_config'), command=self._show_grid_config)
        
        # Barre d'outils en haut / Top toolbar
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar_frame, text=tr('analysis_graphs').split(' - ')[0], font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            toolbar_frame,
            text=tr('fullscreen'),
            command=self._toggle_fullscreen
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar_frame,
            text="⟲ " + tr('reset_zoom_btn'),
            command=self._reset_zoom
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar_frame,
            text="✕ " + tr('close'),
            command=self.window.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        # Panel de sélection des graphiques et navigation temporelle côte à côte / Graph selection panel and time navigation side by side
        top_controls_frame = ttk.Frame(main_frame)
        top_controls_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Panel de sélection des graphiques (gauche) - Layout compact en ligne / Graph selection panel (left) - Compact inline layout
        selection_frame = ttk.LabelFrame(top_controls_frame, text=tr('graph_selection'), padding="5")
        selection_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Créer les sections de sélection en ligne (disposition horizontale compacte) / Create selection sections in line (compact horizontal layout)
        checks_container = ttk.Frame(selection_frame)
        checks_container.pack(fill=tk.BOTH, expand=True)
        
        self.graph_checks = {}
        
        # Fonction helper pour créer une section compacte avec scroll horizontal si nécessaire / Helper function to create compact section with horizontal scroll if needed
        def create_compact_section(parent, title, row, col, rowspan=1, colspan=1):
            frame = ttk.LabelFrame(parent, text=title, padding="3")
            frame.grid(row=row, column=col, padx=2, pady=2, sticky='nsew', rowspan=rowspan, columnspan=colspan)
            
            # Frame pour boutons / Frame for buttons
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X)
            
            # Frame pour les checkboxes avec scroll si nécessaire / Frame for checkboxes with scroll if needed
            content_frame = ttk.Frame(frame)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            return frame, btn_frame, content_frame
        
        # Graphiques globaux (compact - 2 checkboxes en ligne) / Global graphs (compact - 2 checkboxes inline)
        global_frame, global_btn, global_content = create_compact_section(checks_container, tr('graph_buffers'), 0, 0)
        ttk.Button(global_btn, text=tr('all'), width=6, 
                  command=lambda: self._toggle_all_globals(True)).pack(side=tk.LEFT, padx=1)
        ttk.Button(global_btn, text=tr('none'), width=6,
                  command=lambda: self._toggle_all_globals(False)).pack(side=tk.LEFT, padx=1)
        
        for graph_type in ['throughput', 'utilization']:
            labels = {'throughput': '📈 ' + tr('throughput'), 'utilization': '⚙️ ' + tr('utilization')}
            var = tk.BooleanVar(value=(graph_type in selected_graphs or graph_type == 'utilization'))
            self.graph_checks[graph_type] = var
            ttk.Checkbutton(global_content, text=labels[graph_type], variable=var,
                          command=self._regenerate_graphs).pack(side=tk.LEFT, padx=2)
        
        # Pipettes (scroll horizontal si nombreuses) / Pipettes (horizontal scroll if numerous)
        pipettes_frame, pip_btn, pip_content = create_compact_section(checks_container, tr('probes'), 0, 1)
        ttk.Button(pip_btn, text=tr('all'), width=5,
                  command=lambda: self._toggle_category('pipettes', True)).pack(side=tk.LEFT, padx=1)
        ttk.Button(pip_btn, text=tr('none'), width=5,
                  command=lambda: self._toggle_category('pipettes', False)).pack(side=tk.LEFT, padx=1)
        self.type_detail_btn = ttk.Button(pip_btn, text=tr('detail_btn'), width=5,
                                          command=self._toggle_type_detail)
        self.type_detail_btn.pack(side=tk.LEFT, padx=1)
        self.show_type_detail = False
        
        self.graph_checks['pipettes'] = {}
        pip_scroll_frame = ttk.Frame(pip_content)
        pip_scroll_frame.pack(fill=tk.X)
        for probe_id, probe in flow_model.probes.items():
            var = tk.BooleanVar(value=True)
            self.graph_checks['pipettes'][probe_id] = var
            ttk.Checkbutton(pip_scroll_frame, text=probe.name, variable=var,
                          command=self._regenerate_graphs).pack(side=tk.LEFT, padx=1)
        
        # Loupes de temps / Time magnifiers
        loupes_frame, loupe_btn, loupe_content = create_compact_section(checks_container, tr('time_probes'), 0, 2)
        ttk.Button(loupe_btn, text=tr('all'), width=5,
                  command=lambda: self._toggle_category('time_probes', True)).pack(side=tk.LEFT, padx=1)
        ttk.Button(loupe_btn, text=tr('none'), width=5,
                  command=lambda: self._toggle_category('time_probes', False)).pack(side=tk.LEFT, padx=1)
        
        self.graph_checks['time_probes'] = {}
        loupe_scroll_frame = ttk.Frame(loupe_content)
        loupe_scroll_frame.pack(fill=tk.X)
        for probe_id, probe in flow_model.time_probes.items():
            var = tk.BooleanVar(value=True)
            self.graph_checks['time_probes'][probe_id] = var
            ttk.Checkbutton(loupe_scroll_frame, text=probe.name, variable=var,
                          command=self._regenerate_graphs).pack(side=tk.LEFT, padx=1)
        
        # Déplacements opérateurs - Afficher les routes disponibles / Operator movements - Display available routes
        operators_frame, op_btn, op_content = create_compact_section(checks_container, "🚶 " + tr('operator_movements'), 0, 3)
        ttk.Button(op_btn, text=tr('all'), width=5,
                  command=lambda: self._toggle_category('operators', True)).pack(side=tk.LEFT, padx=1)
        ttk.Button(op_btn, text=tr('none'), width=5,
                  command=lambda: self._toggle_category('operators', False)).pack(side=tk.LEFT, padx=1)
        
        self.graph_checks['operators'] = {}
        op_scroll_frame = ttk.Frame(op_content)
        op_scroll_frame.pack(fill=tk.X)
        
        # Récupérer les données de déplacement pour afficher les routes disponibles / Get movement data to display available routes
        operator_travel_data = self.results.get('operator_travel_data', {})
        
        # Compter les noms d'opérateurs pour détecter les doublons / Count operator names to detect duplicates
        operator_name_counts = {}
        for op in flow_model.operators.values():
            operator_name_counts[op.name] = operator_name_counts.get(op.name, 0) + 1
        
        for operator_id, operator in flow_model.operators.items():
            var = tk.BooleanVar(value=True)
            self.graph_checks['operators'][operator_id] = var
            
            # Construire un label détaillé avec les routes disponibles / Build detailed label with available routes
            routes_info = ""
            if operator_id in operator_travel_data and operator_travel_data[operator_id]:
                num_routes = len(operator_travel_data[operator_id])
                route_word = tr('routes') if num_routes > 1 else tr('route')
                routes_info = f" ({num_routes} {route_word})"
            
            # Ajouter l'ID si plusieurs opérateurs ont le même nom / Add ID if multiple operators have the same name
            display_name = operator.name
            if operator_name_counts.get(operator.name, 0) > 1:
                display_name = f"{operator.name} [{operator_id}]"
            
            ttk.Checkbutton(op_scroll_frame, text=f"{display_name}{routes_info}", variable=var,
                          command=self._regenerate_graphs).pack(side=tk.LEFT, padx=1)
        
        # Types d'items (en dessous, compact) / Item types (below, compact)
        item_types_frame, items_btn, items_content = create_compact_section(checks_container, "📦 " + tr('item_types'), 1, 0, colspan=2)
        ttk.Button(items_btn, text=tr('all'), width=5,
                  command=lambda: self._toggle_category('item_types', True)).pack(side=tk.LEFT, padx=1)
        ttk.Button(items_btn, text=tr('none'), width=5,
                  command=lambda: self._toggle_category('item_types', False)).pack(side=tk.LEFT, padx=1)
        
        self.graph_checks['item_types'] = {}
        item_types_graphs = ['distribution', 'timeline', 'by_node']
        item_types_labels = {
            'distribution': '📊 ' + tr('graph_distribution'),
            'timeline': '⏱️ ' + tr('graph_timeline'),
            'by_node': '🔧 ' + tr('graph_by_node')
        }
        for graph_key in item_types_graphs:
            var = tk.BooleanVar(value=True)
            self.graph_checks['item_types'][graph_key] = var
            ttk.Checkbutton(items_content, text=item_types_labels[graph_key], variable=var,
                          command=self._regenerate_graphs).pack(side=tk.LEFT, padx=2)
        
        # Configurer les poids des colonnes pour répartir l'espace / Configure column weights to distribute space
        checks_container.columnconfigure(0, weight=1)
        checks_container.columnconfigure(1, weight=2)
        checks_container.columnconfigure(2, weight=1)
        checks_container.columnconfigure(3, weight=1)
        
        # Navigation temporelle compacte (droite) - Style pipettes / Compact time navigation (right) - Pipettes style
        time_nav_frame = ttk.LabelFrame(top_controls_frame, text=tr('time_navigation'), padding="5")
        time_nav_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        
        # Récupérer la durée totale / Get total duration
        duration = results['duration']
        time_unit = time_unit_var.get() if time_unit_var else "min"
        
        # Créer les variables pour le range de temps / Create variables for time range
        self.time_start = tk.DoubleVar(value=0)
        self.time_end = tk.DoubleVar(value=duration)
        self.duration = duration
        self.time_position = tk.DoubleVar(value=0)  # Position du curseur (décalage depuis fin) / Cursor position (offset from end)
        
        # Frame pour mode plage min-max / Frame for min-max range mode
        range_frame = ttk.Frame(time_nav_frame)
        range_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(range_frame, text=tr('start_time') + ":").grid(row=0, column=0, padx=2, sticky='w')
        start_slider = ttk.Scale(range_frame, from_=0, to=duration, variable=self.time_start, 
                                orient=tk.HORIZONTAL, command=self._on_time_range_change)
        start_slider.grid(row=0, column=1, padx=2, sticky='ew')
        self.start_label = ttk.Label(range_frame, text="0.0")
        self.start_label.grid(row=0, column=2, padx=2)
        
        ttk.Label(range_frame, text=tr('end_time') + ":").grid(row=1, column=0, padx=2, sticky='w')
        end_slider = ttk.Scale(range_frame, from_=0, to=duration, variable=self.time_end, 
                              orient=tk.HORIZONTAL, command=self._on_time_range_change)
        end_slider.grid(row=1, column=1, padx=2, sticky='ew')
        self.end_label = ttk.Label(range_frame, text=f"{duration:.1f}")
        self.end_label.grid(row=1, column=2, padx=2)
        
        range_frame.columnconfigure(1, weight=1)
        
        # Navigation avec curseur (style pipettes) / Navigation with cursor (pipettes style)
        nav_frame = ttk.Frame(time_nav_frame)
        nav_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(nav_frame, text=tr('time_navigation') + ":").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(nav_frame, text="◀◀", width=3,
                  command=lambda: self._shift_time(-10)).pack(side=tk.LEFT, padx=2)
        
        time_slider = ttk.Scale(nav_frame, from_=-duration, to=0,
                               variable=self.time_position, orient=tk.HORIZONTAL,
                               command=self._on_slider_change)
        time_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(nav_frame, text="▶▶", width=3,
                  command=lambda: self._shift_time(10)).pack(side=tk.LEFT, padx=2)
        
        self.time_position_label = ttk.Label(nav_frame, text="0.0", width=10)
        self.time_position_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(nav_frame, text=tr('now_btn'),
                  command=self._reset_time_navigation).pack(side=tk.LEFT, padx=2)
        
        # Zone de défilement pour les graphiques / Scroll area for graphs
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas avec scrollbar (fond gris) et optimisations pour réduire les artefacts
        # Canvas with scrollbar (gray background) and optimizations to reduce artifacts
        self.canvas = tk.Canvas(
            canvas_frame, 
            bg='#d9d9d9',
            highlightthickness=0,  # Pas de bordure de focus / No focus border
            borderwidth=0  # Pas de bordure / No border
        )
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self._smooth_scroll)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Variable pour éviter les mises à jour excessives de la scrollregion / Variable to avoid excessive scrollregion updates
        self._scrollregion_pending = False
        self._last_scrollregion = None
        
        def update_scrollregion(event=None):
            """Met à jour la scrollregion de manière optimisée / Updates scrollregion in an optimized way"""
            if self._scrollregion_pending:
                return
            self._scrollregion_pending = True
            
            def do_update():
                try:
                    bbox = self.canvas.bbox("all")
                    if bbox and bbox != self._last_scrollregion:
                        self._last_scrollregion = bbox
                        # Désactiver temporairement les updates visuels / Temporarily disable visual updates
                        self.canvas.configure(scrollregion=bbox)
                        self.canvas.update_idletasks()
                except tk.TclError:
                    pass
                finally:
                    self._scrollregion_pending = False
            
            # Délai pour éviter les mises à jour trop fréquentes / Delay to avoid too frequent updates
            self.window.after(100, do_update)
        
        self.scrollable_frame.bind("<Configure>", update_scrollregion)
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configurer le canvas pour un scroll plus fluide / Configure canvas for smoother scrolling
        self.canvas.configure(yscrollincrement=5)  # Incrément de scroll plus petit / Smaller scroll increment
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel avec Enter/Leave pour éviter TclError / Bind mousewheel with Enter/Leave to avoid TclError
        self._scroll_pending = False
        self.canvas.bind('<Enter>', lambda e: self.canvas.bind_all('<MouseWheel>', self._on_mousewheel))
        self.canvas.bind('<Leave>', lambda e: self.canvas.unbind_all('<MouseWheel>'))
        
        # Stocker les figures et axes / Store figures and axes
        self.figures = []
        self.axes = []
        self.toolbars = []
        
        # Initialiser le cache des couleurs de types d'items / Initialize item types color cache
        self._item_type_colors = {}
        self._build_item_type_colors_cache()
        
        # Message de chargement / Loading message
        loading_frame = ttk.Frame(self.scrollable_frame)
        loading_frame.pack(expand=True, pady=50)
        ttk.Label(loading_frame, text=tr('generating_graphs'), 
                 font=("Arial", 12)).pack()
        self.loading_label = ttk.Label(loading_frame, text=tr('preparing'), 
                                       font=("Arial", 10), foreground="#666")
        self.loading_label.pack(pady=10)
        
        # Générer les graphiques après un court délai (permet à la fenêtre de s'afficher) / Generate graphs after short delay (allows window to display)
        self.window.after(100, self._generate_graphs_deferred)
        
        # Centrer la fenêtre si pas en plein écran / Center window if not in full screen
        self.window.update_idletasks()
    
    def _generate_graphs_deferred(self):
        """Génère les graphiques de manière différée pour améliorer la réactivité / Generates graphs deferred to improve responsiveness"""
        # Nettoyer le message de chargement / Clean loading message
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Générer les graphiques / Generate graphs
        self._generate_graphs()
        
        # Forcer la mise à jour de l'affichage / Force display update
        self.window.update_idletasks()
        
        # Mémoriser la largeur actuelle et désactiver le flag de chargement initial
        # Remember current width and disable initial load flag
        self._last_width = self.window.winfo_width()
        self._initial_load = False
    
    def _toggle_all_globals(self, select_all):
        """Sélectionne ou désélectionne tous les graphiques globaux / Selects or deselects all global graphs"""
        for key in ['throughput', 'wip', 'utilization']:
            if key in self.graph_checks:
                self.graph_checks[key].set(select_all)
        self._regenerate_graphs()
    
    def _toggle_category(self, category, select_all):
        """Sélectionne ou désélectionne tous les graphiques d'une catégorie / Selects or deselects all graphs in a category"""
        if category in self.graph_checks and isinstance(self.graph_checks[category], dict):
            for var in self.graph_checks[category].values():
                var.set(select_all)
        self._regenerate_graphs()
    
    def _toggle_type_detail(self):
        """Bascule entre affichage général et détaillé par type pour les pipettes / Toggles between general and detailed by type view for pipettes"""
        self.show_type_detail = not self.show_type_detail
        # Mettre à jour le texte du bouton / Update button text
        if self.show_type_detail:
            self.type_detail_btn.config(text=tr('general_btn'))
        else:
            self.type_detail_btn.config(text=tr('detail_btn'))
        # Rafraîchir le cache des couleurs / Refresh colors cache
        self._build_item_type_colors_cache()
        # Régénérer les graphiques / Regenerate graphs
        self._regenerate_graphs()
    
    def _build_item_type_colors_cache(self):
        """Construit un cache des couleurs configurées pour chaque type d'item / Builds a cache of configured colors for each item type"""
        self._item_type_colors = {}
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    self._item_type_colors[item_type.type_id] = item_type.color
    
    def _show_grid_config(self):
        """Affiche la fenêtre de configuration de la grille / Displays the grid configuration window"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Configuration de la grille")
        dialog.geometry("300x150")
        dialog.transient(self.window)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Configuration de l'affichage des graphiques", 
                 font=("Arial", 10, "bold")).pack(pady=10)
        
        # Nombre de colonnes / Number of columns
        frame1 = ttk.Frame(dialog)
        frame1.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(frame1, text="Nombre de colonnes:").pack(side=tk.LEFT)
        ttk.Spinbox(frame1, from_=1, to=6, textvariable=self.cols_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # Hauteur des graphiques / Graph height
        frame2 = ttk.Frame(dialog)
        frame2.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(frame2, text="Hauteur des graphiques (px):").pack(side=tk.LEFT)
        ttk.Spinbox(frame2, from_=200, to=800, textvariable=self.graph_height_var, 
                   width=5, increment=50).pack(side=tk.LEFT, padx=5)
        
        # Boutons / Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Appliquer", command=lambda: [self._regenerate_graphs(), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annuler", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _on_window_resize(self, event):
        """Gère le redimensionnement de la fenêtre (avec debounce) / Handle window resize (with debounce)"""
        # Ignorer pendant le chargement initial / Ignore during initial load
        if self._initial_load:
            return
        
        # Ignorer les événements de widgets enfants / Ignore child widget events
        if event.widget != self.window:
            return
        
        # Vérifier si la largeur a vraiment changé significativement / Check if width really changed significantly
        new_width = event.width
        if abs(new_width - self._last_width) < 50:  # Seuil de 50px / 50px threshold
            return
        
        self._last_width = new_width
        
        # Annuler le timer précédent si existe / Cancel previous timer if exists
        if self._resize_timer:
            self.window.after_cancel(self._resize_timer)
        
        # Programmer la régénération après un délai (debounce) / Schedule regeneration after delay (debounce)
        self._resize_timer = self.window.after(300, self._regenerate_graphs)

    def _regenerate_graphs(self, event=None):
        """Régénère tous les graphiques selon les sélections / Regenerates all graphs according to selections"""
        # Nettoyer les anciens graphiques / Clean old graphs
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.figures = []
        self.axes = []
        self.toolbars = []
        
        # Régénérer / Regenerate
        self._generate_graphs()
    
    def _shift_time(self, delta):
        """Déplace le curseur temporel / Moves the time cursor"""
        new_pos = self.time_position.get() + delta
        new_pos = max(-self.duration, min(0, new_pos))
        self.time_position.set(new_pos)
        self._on_slider_change(new_pos)
    
    def _on_slider_change(self, value):
        """Met à jour l'affichage quand le curseur bouge / Updates display when cursor moves"""
        pos = self.time_position.get()
        actual_time = self.duration + pos  # Convertir position négative en temps réel / Convert negative position to real time
        self.time_position_label.config(text=f"{actual_time:.1f}")
        # La navigation temporelle affecte uniquement les graphiques de pipettes / Time navigation affects only pipette graphs
        self._update_time_filtered_graphs()
    
    def _reset_time_navigation(self):
        """Réinitialise la navigation au temps actuel / Resets navigation to current time"""
        self.time_position.set(0)
        self._on_slider_change(0)
    
    def _on_time_range_change(self, event=None):
        """Appelé quand les sliders min-max de temps changent / Called when min-max time sliders change"""
        start = self.time_start.get()
        end = self.time_end.get()
        
        # S'assurer que start < end / Ensure start < end
        if start >= end:
            if event:  # Éviter les boucles infinies / Avoid infinite loops
                return
            end = start + 1
            if end > self.duration:
                start = self.duration - 1
                end = self.duration
            self.time_start.set(start)
            self.time_end.set(end)
        
        # Mettre à jour les labels / Update labels
        self.start_label.config(text=f"{start:.1f}")
        self.end_label.config(text=f"{end:.1f}")
        
        # Point 4: La navigation min-max affecte UNIQUEMENT les graphiques de pipettes / Point 4: Min-max navigation affects ONLY pipette graphs
        # PAS le WIP, Utilisation, ni loupes de temps / NOT WIP, Utilization, nor time magnifiers
        self._update_time_filtered_graphs()
    
    def _update_time_filtered_graphs(self):
        """Met à jour uniquement les graphiques affectés par la navigation temporelle / Updates only graphs affected by time navigation"""
        # Récupérer la plage de temps actuelle / Get current time range
        time_min = self.time_start.get()
        time_max = self.time_end.get()
        
        # Prendre en compte le curseur de position (time_position) / Take into account position cursor (time_position)
        # time_position est négatif et représente le décalage par rapport à la durée / time_position is negative and represents offset from duration
        pos = self.time_position.get()
        actual_time = self.duration + pos  # Position actuelle / Current position
        
        # Si le curseur est utilisé, centrer la fenêtre autour de cette position / If cursor is used, center window around this position
        # en conservant la largeur de la fenêtre (time_max - time_min) / while keeping window width (time_max - time_min)
        window_width = time_max - time_min
        if pos < 0:  # Le curseur a été déplacé / The cursor has been moved
            # Centrer autour de actual_time / Center around actual_time
            time_min = max(0, actual_time - window_width / 2)
            time_max = min(self.duration, actual_time + window_width / 2)
            # Ajuster si on atteint les limites / Adjust if reaching limits
            if time_max >= self.duration:
                time_max = self.duration
                time_min = max(0, time_max - window_width)
            elif time_min <= 0:
                time_min = 0
                time_max = min(self.duration, window_width)
        
        # Appliquer uniquement aux graphiques de pipettes (throughput et individuelles) / Apply only to pipette graphs (throughput and individual)
        for ax in self.axes:
            if ax:
                # Identifier si c'est un graphique de pipette en regardant son titre / Identify if it's a pipette graph by looking at its title
                title = ax.get_title().lower()
                if 'pipette' in title or 'débit' in title or 'throughput' in title:
                    ax.set_xlim(time_min, time_max)
                    # Redessiner uniquement ce graphique / Redraw only this graph
                    ax.figure.canvas.draw()
    
    def _reset_time_range(self):
        """Réinitialise la plage de temps à la durée complète / Resets time range to full duration"""
        self.time_start.set(0)
        self.time_end.set(self.duration)
        self._on_time_range_change()
    
    def _toggle_fullscreen(self):
        """Bascule entre plein écran et fenêtre normale / Toggles between full screen and normal window"""
        current_state = self.window.state()
        if current_state == 'zoomed':
            self.window.state('normal')
        else:
            self.window.state('zoomed')
    
    def _reset_zoom(self):
        """Réinitialise le zoom de tous les graphiques / Resets zoom of all graphs"""
        for ax in self.axes:
            ax.relim()
            ax.autoscale()
        for fig in self.figures:
            fig.canvas.draw()
    
    def _smooth_scroll(self, *args):
        """Scroll fluide via scrollbar avec suspension temporaire des mises à jour
        
        Smooth scroll via scrollbar with temporary update suspension"""
        # Suspendre temporairement les mises à jour visuelles / Temporarily suspend visual updates
        try:
            self.canvas.yview(*args)
            # Forcer une mise à jour immédiate pour éviter le tearing / Force immediate update to avoid tearing
            self.canvas.update_idletasks()
        except tk.TclError:
            pass
    
    def _on_mousewheel(self, event):
        """Gestion de la molette de la souris - scroll fluide avec throttling / Mouse wheel handling - smooth scroll with throttling"""
        # Accumuler le delta pour un scroll plus fluide / Accumulate delta for smoother scroll
        if not hasattr(self, '_scroll_delta'):
            self._scroll_delta = 0
        
        self._scroll_delta += event.delta
        
        if self._scroll_pending:
            return
        
        self._scroll_pending = True
        
        def do_scroll():
            if hasattr(self, '_scroll_delta') and self._scroll_delta != 0:
                # Scroll avec le delta accumulé / Scroll with accumulated delta
                scroll_amount = int(-1 * (self._scroll_delta / 60))
                if scroll_amount != 0:
                    try:
                        self.canvas.yview_scroll(scroll_amount, "units")
                        # Forcer mise à jour immédiate / Force immediate update
                        self.canvas.update_idletasks()
                    except tk.TclError:
                        pass
                self._scroll_delta = 0
            self._scroll_pending = False
        
        # Exécuter le scroll après un très court délai (throttling) / Execute scroll after very short delay (throttling)
        self.window.after(8, do_scroll)
    
    def _generate_graphs(self):
        """Génère tous les graphiques sélectionnés / Generates all selected graphs"""
        from models.flow_model import NodeType
        
        # Récupérer les données / Get data
        duration = self.results['duration']
        probe_data = self.results.get('probe_data', {})
        buffer_data = self.results.get('buffer_data', {})
        time_probe_data = self.results.get('time_probe_data', {})
        operator_travel_data = self.results.get('operator_travel_data', {})
        
        # Obtenir l'unité de temps actuelle / Get current time unit
        time_unit_label = self.time_unit_var.get()
        
        # Réinitialiser le compteur de colonnes / Reset column counter
        if hasattr(self, 'columns_container'):
            self.columns_container.destroy()
            delattr(self, 'columns_container')
            if hasattr(self, 'columns'):
                delattr(self, 'columns')
            if hasattr(self, 'current_column'):
                delattr(self, 'current_column')
            if hasattr(self, 'column_graphs'):
                delattr(self, 'column_graphs')
            if hasattr(self, 'graph_count'):
                delattr(self, 'graph_count')
        
        # Générer chaque type de graphique sélectionné (stocks et production retirés) / Generate each selected graph type (stocks and production removed)
        if self.graph_checks.get('throughput', tk.BooleanVar(value=False)).get():
            self._plot_throughput(probe_data, duration, time_unit_label)
        
        # WIP graphique retiré - Non utilisé / WIP graph removed - Not used
        # if self.graph_checks.get('wip', tk.BooleanVar(value=False)).get():
        #     self._plot_wip(probe_data, buffer_data, duration, time_unit_label)
        
        if self.graph_checks.get('utilization', tk.BooleanVar(value=False)).get():
            # Graphique combiné: nœuds + opérateurs / Combined graph: nodes + operators
            operator_utilization = self.results.get('operator_utilization', {})
            self._plot_combined_utilization(duration, time_unit_label, operator_utilization)
        
        # Graphiques individuels pipettes / Individual pipette graphs
        for probe_id, var in self.graph_checks.get('pipettes', {}).items():
            if var.get() and probe_id in probe_data:
                self._plot_individual_probe(probe_id, probe_data[probe_id], duration, time_unit_label)
        
        # Graphiques loupes de temps / Time magnifier graphs
        if False:
            print(f"\n{'='*60}")
        if False:
            print(f"[DEBUG TIME PROBES] Diagnostic complet")
        if False:
            print(f"{'='*60}")
        if False:
            print(f"[DEBUG] Loupes dans flow_model: {list(self.flow_model.time_probes.keys())}")
        if False:
            print(f"[DEBUG] time_probe_data clés: {list(time_probe_data.keys())}")
        if False:
            print(f"[DEBUG] Loupes sélectionnées (checkboxes): {list(self.graph_checks.get('time_probes', {}).keys())}")
        
        if time_probe_data:
            if False:
                print(f"\n[DEBUG] Contenu de time_probe_data:")
            for pid, pdata in time_probe_data.items():
                if False:
                    print(f"  - {pid}: type={type(pdata)}, contenu={pdata if not isinstance(pdata, list) else f'liste de {len(pdata)} éléments'}")
        else:
            if False:
                print(f"[WARNING] time_probe_data est vide!")
        
        if False:
            print(f"\n[DEBUG] Itération sur les checkboxes:")
        for probe_id, var in self.graph_checks.get('time_probes', {}).items():
            checked = var.get()
            in_data = probe_id in time_probe_data
            if False:
                print(f"  - Loupe {probe_id}: checked={checked}, in_data={in_data}")
            if checked and in_data:
                if False:
                    print(f"    → Génération du graphique pour {probe_id}")
                self._plot_time_probe(probe_id, time_probe_data[probe_id], time_unit_label)
            elif checked and not in_data:
                if False:
                    print(f"    ⚠ Checked mais pas de données!")
            elif not checked:
                if False:
                    print(f"    ℹ Non sélectionnée")
        if False:
            print(f"{'='*60}\n")
        
        # Graphiques déplacements opérateurs
        for op_id, var in self.graph_checks.get('operators', {}).items():
            if var.get() and op_id in operator_travel_data:
                self._plot_operator_travel(op_id, operator_travel_data[op_id], time_unit_label)
        
        # Graphiques types d'items
        item_types_data = self.results.get('item_types_data', {})
        if item_types_data:
            for graph_key, var in self.graph_checks.get('item_types', {}).items():
                if var.get():
                    if graph_key == 'distribution':
                        self._plot_item_types_distribution(item_types_data)
                    elif graph_key == 'timeline':
                        self._plot_item_types_timeline(item_types_data, time_unit_label)
                    elif graph_key == 'by_node':
                        self._plot_item_types_by_node(item_types_data)
    
    def _plot_item_types_distribution(self, item_types_data):
        """Graphique de répartition des types d'items / Item types distribution chart"""
        from collections import Counter
        
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        generation_history = item_types_data.get('generation_history', [])
        if generation_history:
            # Compter les occurrences de chaque type / Count occurrences of each type
            type_counts = Counter([type_id for _, type_id in generation_history])
            
            if type_counts:
                types = list(type_counts.keys())
                counts = list(type_counts.values())
                
                # Obtenir les couleurs des types depuis le flow_model / Get type colors from flow_model
                colors = []
                labels = []
                for type_id in types:
                    # Chercher le type dans toutes les sources / Search for type in all sources
                    type_obj = None
                    for node in self.flow_model.nodes.values():
                        if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                            for it in node.item_type_config.item_types:
                                if str(it.type_id) == str(type_id):
                                    type_obj = it
                                    break
                            if type_obj:
                                break
                    
                    if type_obj:
                        colors.append(type_obj.color)
                        labels.append(type_obj.name)
                    else:
                        colors.append('#808080')
                        labels.append(str(type_id))
                
                ax.bar(labels, counts, color=colors, edgecolor='black', linewidth=1.5)
                ax.set_xlabel(tr('item_type'), fontsize=12)
                ax.set_ylabel(tr('items_generated'), fontsize=12)
                ax.set_title(tr('item_types_generated'), fontsize=14, fontweight='bold')
                ax.grid(True, alpha=0.3, axis='y')
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        fig.tight_layout()
        self._add_figure_to_canvas(fig, "📊 " + tr('item_types') + ": " + tr('graph_distribution'))
    
    def _plot_item_types_timeline(self, item_types_data, time_unit_label):
        """Graphique temporel des générations de types / Temporal graph of type generations"""
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        generation_history = item_types_data.get('generation_history', [])
        if generation_history:
            # Grouper par type / Group by type
            types_dict = {}
            for time, type_id in generation_history:
                if type_id not in types_dict:
                    types_dict[type_id] = []
                types_dict[type_id].append(time)
            
            # Tracer chaque type / Plot each type
            for type_id, times in types_dict.items():
                # Obtenir les informations du type / Get type information
                type_obj = None
                for node in self.flow_model.nodes.values():
                    if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                        for it in node.item_type_config.item_types:
                            if str(it.type_id) == str(type_id):
                                type_obj = it
                                break
                        if type_obj:
                            break
                
                if type_obj:
                    label = type_obj.name
                    color = type_obj.color
                else:
                    label = str(type_id)
                    color = '#808080'
                
                # Créer un histogramme cumulatif / Create a cumulative histogram
                sorted_times = sorted(times)
                cumulative = list(range(1, len(sorted_times) + 1))
                ax.plot(sorted_times, cumulative, label=label, color=color, linewidth=2)
        
        ax.set_xlabel(f"{tr('time_label')} ({time_unit_label})", fontsize=12)
        ax.set_ylabel(tr('cumulative_count'), fontsize=12)
        ax.set_title(tr('generation_timeline'), fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Limiter l'axe X à la durée d'analyse déclarée / Limit X axis to declared analysis duration
        duration = self.results.get('duration', 0)
        if duration > 0:
            ax.set_xlim(0, duration)
        
        fig.tight_layout()
        self._add_figure_to_canvas(fig, "⏱️ " + tr('item_types') + ": " + tr('graph_timeline'))
    
    def _plot_item_types_by_node(self, item_types_data):
        """Graphique des types d'items par nœud
        
        Item types chart by node"""
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        node_arrivals = item_types_data.get('node_arrivals', {})
        if node_arrivals:
            # Créer un graphique empilé / Create stacked chart
            import matplotlib.pyplot as plt
            
            nodes = list(node_arrivals.keys())
            # Obtenir tous les types uniques / Get all unique types
            all_types = set()
            for type_counts in node_arrivals.values():
                all_types.update(type_counts.keys())
            
            # Préparer les données pour l'empilement / Prepare data for stacking
            type_data = {}
            for type_id in all_types:
                type_data[type_id] = [node_arrivals[node_id].get(type_id, 0) for node_id in nodes]
            
            # Obtenir les noms et couleurs des types / Get type names and colors
            type_info = {}
            for type_id in all_types:
                for node in self.flow_model.nodes.values():
                    if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                        for it in node.item_type_config.item_types:
                            if str(it.type_id) == str(type_id):
                                type_info[type_id] = (it.name, it.color)
                                break
                        if type_id in type_info:
                            break
                if type_id not in type_info:
                    type_info[type_id] = (str(type_id), '#808080')
            
            # Créer le graphique empilé / Create stacked chart
            bottom = np.zeros(len(nodes))
            for type_id in all_types:
                name, color = type_info[type_id]
                ax.bar(nodes, type_data[type_id], bottom=bottom, label=name, color=color, edgecolor='black', linewidth=0.5)
                bottom += np.array(type_data[type_id])
            
            # Obtenir les noms des nœuds / Get node names
            node_labels = []
            for node_id in nodes:
                node = self.flow_model.get_node(node_id)
                node_labels.append(node.name if node else node_id)
            
            ax.set_xticks(range(len(nodes)))
            ax.set_xticklabels(node_labels, rotation=45, ha='right')
            ax.set_xlabel(tr('node'), fontsize=12)
            ax.set_ylabel(tr('items_generated'), fontsize=12)
            ax.set_title(tr('generation_by_type_node'), fontsize=14, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
        
        fig.tight_layout()
        self._add_figure_to_canvas(fig, "🔧 " + tr('item_types') + ": " + tr('graph_by_node'))
    
    def _get_figure_size(self):
        """Retourne les dimensions (width, height) pour les figures basées sur la taille de l'écran
        
        Returns dimensions (width, height) for figures based on screen size"""
        # Toujours recalculer en fonction de la taille actuelle de la fenêtre
        # Always recalculate based on current window size
        self.window.update_idletasks()
        window_width = self.window.winfo_width()
        
        # Nombre de colonnes / Number of columns
        num_cols = self.cols_var.get()
        
        # Largeur disponible (fenêtre - scrollbar 25px - marges diverses) / Available width (window - scrollbar 25px - various margins)
        # Tenir compte de: scrollbar (~25px), padding container (4px), padding colonnes (4px*n), bordures LabelFrame (~20px*n)
        total_padding = 25 + 4 + (num_cols * 4) + (num_cols * 20) + 10  # +10 marge sécurité
        available_width = max(window_width - total_padding, 600)
        
        # Largeur par graphique en pixels / Width per graph in pixels
        graph_width_px = available_width / num_cols
        
        # Convertir en pouces (100 DPI pour matplotlib par défaut) / Convert to inches (100 DPI matplotlib default)
        width_inches = max(graph_width_px / 100, 3.5)  # Min 3.5 inches
        
        # Hauteur basée sur la configuration / Height based on config
        height_inches = max(self.graph_height_var.get() / 100, 3)  # Min 3 inches
        
        # Stocker pour référence / Store for reference
        self.graph_width_inches = width_inches
        self.graph_height_inches = height_inches
        
        return (width_inches, height_inches)
    
    def _plot_throughput(self, probe_data, duration, time_unit_label):
        """Graphique des niveaux de buffer par pipette
        
        Buffer levels chart by probe"""
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        # Afficher les niveaux de buffer au lieu du débit / Display buffer levels instead of throughput
        buffer_data = self.results.get('buffer_data', {})
        
        for conn_id, conn in self.flow_model.connections.items():
            # Exclure les connexions vers les sorties (sinks)
            target_node = self.flow_model.get_node(conn.target_id)
            if target_node and target_node.is_sink:
                continue  # Ne pas afficher les buffers vers les sorties
            
            if conn.show_buffer and conn.buffer_capacity > 0:
                if conn_id in buffer_data and buffer_data[conn_id]:
                    # Collecter toutes les données
                    all_times = []
                    all_counts = []
                    for interval_data in buffer_data[conn_id].values():
                        for timestamp, count in interval_data:
                            all_times.append(timestamp)
                            all_counts.append(count)
                    
                    if all_times:
                        # Trier par temps / Sort by time
                        sorted_pairs = sorted(zip(all_times, all_counts))
                        times, counts = zip(*sorted_pairs)
                        
                        source_node = self.flow_model.get_node(conn.source_id)
                        target_node = self.flow_model.get_node(conn.target_id)
                        label = f"{source_node.name}→{target_node.name}"
                        ax.step(times, counts, label=label, where='post', linewidth=2)
        
        ax.set_xlabel(f"{tr('time_label')} ({time_unit_label})", fontsize=12)
        ax.set_ylabel(tr('buffer_level'), fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Limiter l'axe X à la durée d'analyse déclarée / Limit X axis to declared analysis duration
        if duration > 0:
            ax.set_xlim(0, duration)
        
        fig.tight_layout()
        
        self._add_figure_to_canvas(fig, tr('graph_buffers'))
    
    def _plot_buffer_levels(self, buffer_data, duration, time_unit_label):
        """Graphique des niveaux de stock par buffer
        
        Stock levels chart by buffer"""
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        for conn_id, conn in self.flow_model.connections.items():
            # Exclure les connexions vers les sorties (sinks) / Exclude connections to sinks
            target_node = self.flow_model.get_node(conn.target_id)
            if target_node and target_node.is_sink:
                continue  # Ne pas afficher les buffers vers les sorties / Don't display buffers to sinks
            
            if conn.show_buffer and conn.buffer_capacity > 0:
                if conn_id in buffer_data and buffer_data[conn_id]:
                    # Collecter toutes les données / Collect all data
                    all_times = []
                    all_counts = []
                    for interval_data in buffer_data[conn_id].values():
                        for timestamp, count in interval_data:
                            all_times.append(timestamp)
                            all_counts.append(count)
                    
                    if all_times:
                        # Trier par temps / Sort by time
                        sorted_pairs = sorted(zip(all_times, all_counts))
                        times, counts = zip(*sorted_pairs)
                        
                        source_node = self.flow_model.get_node(conn.source_id)
                        target_node = self.flow_model.get_node(conn.target_id)
                        label = f"{source_node.name}→{target_node.name}"
                        ax.step(times, counts, label=label, where='post', linewidth=2)
        
        ax.set_xlabel(f"{tr('time_label')} ({time_unit_label})", fontsize=12)
        ax.set_ylabel(tr('stock_level'), fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Limiter l'axe X à la durée d'analyse déclarée / Limit X axis to declared analysis duration
        if duration > 0:
            ax.set_xlim(0, duration)
        
        fig.tight_layout()
        
        self._add_figure_to_canvas(fig, tr('graph_stocks'))
    
    def _plot_cumulative_production(self, probe_data, duration, time_unit_label):
        """Graphique de production cumulative
        
        Cumulative production chart"""
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        for probe_id, probe in self.flow_model.probes.items():
            if probe_id in probe_data and probe_data[probe_id]:
                # Collecter toutes les données et calculer le cumulatif / Collect all data and calculate cumulative
                all_times = []
                all_values = []
                for interval_data in probe_data[probe_id].values():
                    for timestamp, value in interval_data:
                        all_times.append(timestamp)
                        all_values.append(value)
                
                if all_times:
                    # Trier par temps / Sort by time
                    sorted_pairs = sorted(zip(all_times, all_values))
                    times, values = zip(*sorted_pairs)
                    
                    # Calculer le cumulatif / Calculate cumulative
                    cumulative = np.cumsum(values)
                    ax.plot(times, cumulative, label=probe.name, linewidth=2)
        
        ax.set_xlabel(f"{tr('time_label')} ({time_unit_label})", fontsize=12)
        ax.set_ylabel(tr('cumulative_production'), fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        
        self._add_figure_to_canvas(fig, tr('graph_production'))
    
    def _plot_wip(self, probe_data, buffer_data, duration, time_unit_label):
        """Graphique du Work-In-Process (WIP) - Version optimisée
        
        Work-In-Process (WIP) chart - Optimized version"""
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        # Calculer le WIP total (somme de tous les buffers) - Optimisé / Calculate total WIP (sum of all buffers) - Optimized
        if buffer_data:
            # Créer un dictionnaire avec timestamp -> {conn_id -> count} / Create dict with timestamp -> {conn_id -> count}
            # pour accéder rapidement aux données / for quick data access
            time_to_buffers = {}
            
            for conn_id in buffer_data:
                for interval_data in buffer_data[conn_id].values():
                    for timestamp, count in interval_data:
                        if timestamp not in time_to_buffers:
                            time_to_buffers[timestamp] = {}
                        time_to_buffers[timestamp][conn_id] = count
            
            all_times = sorted(time_to_buffers.keys())
            
            if all_times:
                # Garder l'état actuel de chaque buffer / Keep current state of each buffer
                current_counts = {}
                wip_values = []
                
                for t in all_times:
                    # Mettre à jour les comptes pour ce timestamp / Update counts for this timestamp
                    for conn_id, count in time_to_buffers[t].items():
                        current_counts[conn_id] = count
                    
                    # Calculer le WIP total à ce moment / Calculate total WIP at this time
                    total_wip = sum(current_counts.values())
                    wip_values.append(total_wip)
                
                ax.step(all_times, wip_values, label='WIP Total', where='post', linewidth=2, color='blue')
        
        ax.set_xlabel(f"{tr('time_label')} ({time_unit_label})", fontsize=12)
        ax.set_ylabel('WIP (' + tr('items') + ')', fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        
        self._add_figure_to_canvas(fig, tr('graph_wip'))
    
    def _add_figure_to_canvas(self, fig, title):
        """Ajoute une figure au canvas scrollable avec grille dynamique et largeur auto
        
        Adds a figure to scrollable canvas with dynamic grid and auto width"""
        # Créer un container pour la grille s'il n'existe pas / Create container for grid if it doesn't exist
        if not hasattr(self, 'columns_container'):
            self.columns_container = ttk.Frame(self.scrollable_frame)
            self.columns_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # TOUJOURS recalculer les dimensions pour s'adapter au redimensionnement / ALWAYS recalculate dimensions to adapt to resizing
        # Obtenir le nombre de colonnes configuré / Get configured number of columns
        num_cols = self.cols_var.get()
        
        # Calculer la largeur disponible pour les graphiques / Calculate available width for graphs
        self.window.update_idletasks()
        window_width = self.window.winfo_width()
        
        # Tenir compte de: scrollbar (~25px), padding container (4px), padding colonnes (4px*n), bordures LabelFrame (~20px*n)
        # Account for: scrollbar (~25px), container padding (4px), column padding (4px*n), LabelFrame borders (~20px*n)
        total_padding = 25 + 4 + (num_cols * 4) + (num_cols * 20) + 10  # +10 marge sécurité
        available_width = max(window_width - total_padding, 600)
        
        # Largeur par graphique en pixels / Width per graph in pixels
        graph_width_px = available_width / num_cols
        
        # Convertir en pouces (100 DPI pour matplotlib) / Convert to inches (100 DPI for matplotlib)
        self.graph_width_inches = max(graph_width_px / 100, 3.5)  # Min 3.5 inches
        
        # Hauteur depuis la configuration / Height from config
        self.graph_height_inches = max(self.graph_height_var.get() / 100, 3)  # Min 3 inches
        
        # Créer les colonnes si elles n'existent pas / Create columns if they don't exist
        if not hasattr(self, 'columns'):
            self.columns = []
            self.column_graphs = []  # Tracker graphiques par colonne
            for i in range(num_cols):
                col = ttk.Frame(self.columns_container)
                col.grid(row=0, column=i, sticky='nsew', padx=2)  # Padding réduit / Reduced padding
                self.columns_container.columnconfigure(i, weight=1, uniform="cols")
                self.columns.append(col)
                self.column_graphs.append(0)
            
            self.current_column = 0
            self.graph_count = 0
        
        # Trouver la colonne avec le moins de graphiques (équilibrage) / Find column with fewest graphs (balancing)
        self.current_column = self.column_graphs.index(min(self.column_graphs))
        
        # Frame pour ce graphique dans la colonne appropriée / Frame for this graph in appropriate column
        graph_frame = ttk.LabelFrame(self.columns[self.current_column], text=title, padding="3")
        graph_frame.pack(fill=tk.X, expand=False, pady=3)
        
        # Intégrer la figure matplotlib / Integrate matplotlib figure
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=False)
        
        # Ajouter la barre d'outils matplotlib / Add matplotlib toolbar
        toolbar = NavigationToolbar2Tk(canvas, graph_frame)
        toolbar.update()
        
        # Sauvegarder les références / Save references
        self.figures.append(fig)
        self.axes.append(fig.axes[0] if fig.axes else None)
        self.toolbars.append(toolbar)
        
        # Incrémenter le compteur de graphiques pour cette colonne / Increment graph counter for this column
        self.column_graphs[self.current_column] += 1
        self.graph_count += 1
    
    def _plot_utilization(self, duration, time_unit_label):
        """Graphique d'utilisation des nœuds de traitement
        
        Processing nodes utilization chart"""
        from models.flow_model import NodeType
        
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        # Récupérer les données d'utilisation / Get utilization data
        utilization_data = self.results.get('utilization_data', {})
        
        if utilization_data:
            nodes = []
            utilizations = []
            
            for node_id, util_percent in utilization_data.items():
                node = self.flow_model.get_node(node_id)
                if node and node.node_type == NodeType.CUSTOM and not node.is_source:
                    nodes.append(node.name)
                    utilizations.append(util_percent)
            
            if nodes:
                ax.barh(nodes, utilizations, color='steelblue')
                ax.set_xlabel(tr('utilization') + ' (%)', fontsize=12)
                ax.grid(True, axis='x', alpha=0.3)
                ax.set_xlim(0, 100)
        
        fig.tight_layout()
        self._add_figure_to_canvas(fig, tr('graph_utilization'))
    
    def _plot_combined_utilization(self, duration, time_unit_label, operator_utilization):
        """Graphique combiné d'utilisation des nœuds ET opérateurs
        
        Combined utilization chart for nodes AND operators"""
        from models.flow_model import NodeType
        
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        # Récupérer les données d'utilisation des nœuds / Get node utilization data
        utilization_data = self.results.get('utilization_data', {})
        
        names = []
        utilizations = []
        colors = []
        
        # Ajouter les nœuds de traitement / Add processing nodes
        if utilization_data:
            for node_id, util_percent in utilization_data.items():
                node = self.flow_model.get_node(node_id)
                if node and node.node_type == NodeType.CUSTOM and not node.is_source:
                    names.append(f"[M] {node.name}")
                    utilizations.append(util_percent)
                    colors.append('steelblue')
        
        # Ajouter les opérateurs / Add operators
        if operator_utilization:
            for operator_id, util_percent in operator_utilization.items():
                operator = self.flow_model.get_operator(operator_id)
                if operator:
                    names.append(f"[OP] {operator.name}")
                    utilizations.append(util_percent)
                    colors.append('#FF6B6B')
        
        if names:
            ax.barh(names, utilizations, color=colors)
            ax.set_xlabel(tr('utilization') + ' (%)', fontsize=12)
            ax.grid(True, axis='x', alpha=0.3)
            ax.set_xlim(0, 100)
            # Légende / Legend
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor='steelblue', label=tr('nodes')),
                             Patch(facecolor='#FF6B6B', label=tr('operators'))]
            ax.legend(handles=legend_elements, loc='lower right')
        
        fig.tight_layout()
        self._add_figure_to_canvas(fig, tr('graph_utilization'))
    
    def _plot_individual_probe(self, probe_id, probe_data, duration, time_unit_label):
        """Graphique individuel pour une pipette avec modes général et détail
        
        Individual chart for a probe with general and detail modes"""
        probe = self.flow_model.probes.get(probe_id)
        if not probe:
            return
        
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        # Récupérer les données de types depuis les résultats / Get type data from results
        probe_type_data_all = self.results.get('probe_type_data', {})
        probe_type_data_intervals = probe_type_data_all.get(probe_id, {})
        
        if self.show_type_detail and probe_type_data_intervals:
            # Mode détaillé : graphique empilé par type d'item / Detail mode: stacked chart by item type
            # Collecter toutes les données de types / Collect all type data
            all_times = []
            all_type_counts = []
            for interval_data in probe_type_data_intervals.values():
                for timestamp, type_counts in interval_data:
                    all_times.append(timestamp)
                    all_type_counts.append(type_counts)
            
            if all_times:
                # Trier par timestamp uniquement (type_counts sont des dicts, non comparables) / Sort by timestamp only (type_counts are dicts, not comparable)
                sorted_data = sorted(zip(all_times, all_type_counts), key=lambda x: x[0])
                times = [t for t, _ in sorted_data]
                type_counts_list = [tc for _, tc in sorted_data]
                
                # Obtenir tous les types d'items / Get all item types
                all_types = set()
                for type_counts in type_counts_list:
                    all_types.update(type_counts.keys())
                all_types = sorted(all_types)
                
                if times and all_types:
                    # Préparer les données pour chaque type / Prepare data for each type
                    type_data_dict = {item_type: [] for item_type in all_types}
                    for type_counts in type_counts_list:
                        for item_type in all_types:
                            type_data_dict[item_type].append(type_counts.get(item_type, 0))
                    
                    # Récupérer les couleurs configurées pour chaque type / Get configured colors for each type
                    self._build_item_type_colors_cache()
                    colors_default = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', 
                                      '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B195', '#C06C84']
                    
                    # Dessiner le graphique empilé / Draw stacked chart
                    bottom = [0] * len(times)
                    for i, item_type in enumerate(all_types):
                        vals = type_data_dict[item_type]
                        color = self._item_type_colors.get(item_type, colors_default[i % len(colors_default)])
                        
                        # Calculer la hauteur totale (bottom + vals) / Calculate total height (bottom + vals)
                        top = [b + v for b, v in zip(bottom, vals)]
                        
                        # Pour les pipettes cumulatives, interpolation linéaire lisse / For cumulative probes, smooth linear interpolation
                        # Pour les pipettes buffer, créer des segments horizontaux pour empilement en escalier / For buffer probes, create horizontal segments for stair stacking
                        if probe.measure_mode == "cumulative":
                            # Zone remplie avec bordure blanche fine pour séparer visuellement les zones empilées / Filled area with thin white border to visually separate stacked zones
                            ax.fill_between(times, bottom, top, 
                                            label=item_type, alpha=1.0, color=color, 
                                            edgecolor='white', linewidth=0.5)
                        else:
                            # Pour les pipettes buffer, créer des segments horizontaux manuellement / For buffer probes, create horizontal segments manually
                            # pour avoir un rendu en escalier propre avec empilement correct / for clean stair rendering with correct stacking
                            times_extended = []
                            bottom_extended = []
                            top_extended = []
                            
                            for j in range(len(times)):
                                times_extended.append(times[j])
                                bottom_extended.append(bottom[j])
                                top_extended.append(top[j])
                                
                                # Ajouter un point juste avant le prochain pour créer l'escalier / Add point just before next to create stair
                                if j < len(times) - 1:
                                    times_extended.append(times[j+1])
                                    bottom_extended.append(bottom[j])
                                    top_extended.append(top[j])
                            
                            ax.fill_between(times_extended, bottom_extended, top_extended, 
                                            label=item_type, alpha=1.0, color=color,
                                            edgecolor='white', linewidth=0.5)
                        
                        bottom = top
                    
                    ax.legend(loc='upper left', fontsize=8)
        else:
            # Mode général : graphique normal / General mode: normal chart
            all_times = []
            all_values = []
            for interval_data in probe_data.values():
                for timestamp, value in interval_data:
                    all_times.append(timestamp)
                    all_values.append(value)
            
            if all_times:
                sorted_pairs = sorted(zip(all_times, all_values))
                times, values = zip(*sorted_pairs)
                if probe.measure_mode == "cumulative":
                    ax.plot(times, values, linewidth=2, color=probe.color)
                else:
                    ax.step(times, values, where='post', linewidth=2, color=probe.color)
                    ax.fill_between(times, values, alpha=0.3, color=probe.color, step='post')
        
        ax.set_xlabel(f"{tr('time_label')} ({time_unit_label})", fontsize=12)
        ylabel = tr('cumulative_items') if probe.measure_mode == "cumulative" else tr('items_in_buffer')
        ax.set_ylabel(ylabel, fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Limiter l'axe X à la durée d'analyse / Limit X axis to analysis duration
        if duration > 0:
            ax.set_xlim(0, duration)
        
        fig.tight_layout()
        
        mode_text = " " + tr('detail_by_type') if self.show_type_detail else ""
        self._add_figure_to_canvas(fig, f"{tr('probe_label')} {probe.name}{mode_text}")
    
    def _plot_time_probe(self, probe_id, probe_data, time_unit_label):
        """Graphique pour une loupe de temps
        
        Chart for a time magnifier"""
        probe = self.flow_model.time_probes.get(probe_id)
        if not probe:
            if False:
                print(f"[WARNING] Loupe {probe_id} non trouvée dans flow_model / Magnifier {probe_id} not found in flow_model")
            return
        
        fig = Figure(figsize=self._get_figure_size(), dpi=100)
        ax = fig.add_subplot(111)
        
        # Gérer différentes structures de données / Handle different data structures
        if isinstance(probe_data, dict):
            times = probe_data.get('times', [])
        elif isinstance(probe_data, list):
            times = probe_data
        else:
            times = []
        
        if False:
            print(f"[DEBUG] Loupe {probe.name}: {len(times)} mesures")
        
        if times:
            ax.hist(times, bins=30, color='orange', alpha=0.7, edgecolor='black')
            ax.set_title(f'{tr("time_probe_prefix")} {probe.name}', fontsize=12, fontweight='bold')
        else:
            # Afficher un message si pas de données / Display message if no data
            ax.text(0.5, 0.5, tr('no_data_collected'), 
                   ha='center', va='center', fontsize=12, color='gray')
            ax.set_title(f'{tr("time_probe_prefix")} {probe.name}', fontsize=12, fontweight='bold')
        
        ax.set_xlabel(f'{tr("time_label")} ({time_unit_label})', fontsize=12)
        ax.set_ylabel(tr('frequency'), fontsize=12)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        
        self._add_figure_to_canvas(fig, f'{tr("time_probe_prefix")} {probe.name}')
    
    def _plot_operator_travel(self, op_id, travel_data, time_unit_label):
        """Graphique des déplacements d'un opérateur - un graphique par route
        
        Operator travel chart - one chart per route"""
        operator = self.flow_model.operators.get(op_id)
        if not operator:
            return
        
        # Créer un graphique séparé pour CHAQUE route (au lieu de tous dans un seul graphique) / Create separate chart for EACH route (instead of all in one chart)
        if travel_data:
            for route_key, times in travel_data.items():
                if times and len(times) > 0:
                    from_id, to_id = route_key
                    from_node = self.flow_model.get_node(from_id)
                    to_node = self.flow_model.get_node(to_id)
                    
                    if from_node and to_node:
                        # Créer une figure pour cette route spécifique / Create figure for this specific route
                        fig = Figure(figsize=self._get_figure_size(), dpi=100)
                        ax = fig.add_subplot(111)
                        
                        route_label = f"{from_node.name} → {to_node.name}"
                        
                        # Calculer le nombre de bins / Calculate number of bins
                        n_bins = min(30, max(10, len(times) // 5))
                        
                        # Créer l'histogramme / Create histogram
                        ax.hist(times, bins=n_bins, color='purple', alpha=0.7, edgecolor='black')
                        
                        # Calculer les statistiques / Calculate statistics
                        mean_val = np.mean(times)
                        std_val = np.std(times)
                        min_val = np.min(times)
                        max_val = np.max(times)
                        count_val = len(times)
                        
                        # Titre explicite avec la route / Explicit title with route
                        ax.set_title(f"{tr('operator_travel')}: {route_label}", fontsize=12, fontweight='bold')
                        
                        # Ajouter les statistiques en texte / Add statistics as text
                        stats_text = f"{tr('average')}: {mean_val:.2f}\n{tr('std_dev')}: {std_val:.2f}\n{tr('min')}: {min_val:.2f}\n{tr('max')}: {max_val:.2f}\n{tr('count')}: {count_val}"
                        ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
                               verticalalignment='top', horizontalalignment='right',
                               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                               fontsize=9)
                        
                        ax.set_xlabel(f"{tr('travel_time')} ({time_unit_label})", fontsize=10)
                        ax.set_ylabel(tr('frequency'), fontsize=10)
                        ax.grid(True, alpha=0.3)
                        
                        fig.tight_layout()
                        # Titre du graphique avec nom de l'opérateur et la route détaillée
                        self._add_figure_to_canvas(fig, f"🚶 {operator.name}: {from_node.name}→{to_node.name}")
