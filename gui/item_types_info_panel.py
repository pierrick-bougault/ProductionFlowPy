"""Panneau d'information et analyse des types d'items / Item types information and analysis panel"""
import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
from collections import Counter
from gui.translations import tr

class ItemTypesInfoPanel(ttk.Frame):
    """Panneau d'information sur les types d'items / Item types information panel"""
    
    def __init__(self, parent, flow_model, simulator=None):
        super().__init__(parent)
        self.flow_model = flow_model
        self.simulator = simulator
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Crée les widgets du panneau / Create panel widgets"""
        # Notebook avec onglets / Notebook with tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglet 1: Configuration / Tab 1: Configuration
        config_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(config_frame, text=tr('configuration'))
        self._create_config_tab(config_frame)
        
        # Onglet 2: Répartition Globale / Tab 2: Global Distribution
        dist_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(dist_frame, text=tr('distribution'))
        self._create_distribution_tab(dist_frame)
        
        # Onglet 3: Timeline / Tab 3: Timeline
        timeline_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(timeline_frame, text=tr('timeline'))
        self._create_timeline_tab(timeline_frame)
        
        # Onglet 4: Par Nœud / Tab 4: By Node
        node_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(node_frame, text=tr('by_node'))
        self._create_node_tab(node_frame)
        
        # Onglet 5: Flux dans Connexions / Tab 5: Flow in Connections
        flow_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(flow_frame, text=tr('flow_connections'))
        self._create_flow_tab(flow_frame)
    
    def _create_config_tab(self, parent):
        """Onglet de configuration / Configuration tab"""
        # Titre / Title
        ttk.Label(
            parent,
            text=tr('item_types_config'),
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Frame scrollable / Scrollable frame
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.config_text_widget = scrollable_frame
        
        # Bouton refresh / Refresh button
        ttk.Button(
            parent,
            text=tr('refresh'),
            command=self.refresh_config
        ).pack(pady=10)
    
    def _create_distribution_tab(self, parent):
        """Onglet de répartition / Distribution tab"""
        # Frame supérieure avec contrôles / Top frame with controls
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, pady=5)
        
        ttk.Label(controls, text=tr('chart_type')).pack(side=tk.LEFT, padx=5)
        self.chart_type_var = tk.StringVar(value="pie")
        ttk.Radiobutton(controls, text=tr('pie_chart'), variable=self.chart_type_var, value="pie", command=self.refresh_distribution).pack(side=tk.LEFT)
        ttk.Radiobutton(controls, text=tr('bar_chart'), variable=self.chart_type_var, value="bar", command=self.refresh_distribution).pack(side=tk.LEFT)
        
        ttk.Button(controls, text=tr('refresh'), command=self.refresh_distribution).pack(side=tk.RIGHT, padx=5)
        
        # Canvas matplotlib
        self.dist_figure = Figure(figsize=(8, 6))
        self.dist_canvas = FigureCanvasTkAgg(self.dist_figure, parent)
        self.dist_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Toolbar / Barre d'outils
        toolbar = NavigationToolbar2Tk(self.dist_canvas, parent)
        toolbar.update()
    
    def _create_timeline_tab(self, parent):
        """Onglet timeline / Timeline tab"""
        # Contrôles / Controls
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, pady=5)
        
        ttk.Button(controls, text=tr('refresh'), command=self.refresh_timeline).pack(side=tk.RIGHT, padx=5)
        
        # Canvas matplotlib
        self.timeline_figure = Figure(figsize=(10, 6))
        self.timeline_canvas = FigureCanvasTkAgg(self.timeline_figure, parent)
        self.timeline_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        toolbar = NavigationToolbar2Tk(self.timeline_canvas, parent)
        toolbar.update()
    
    def _create_node_tab(self, parent):
        """Onglet par nœud / By node tab"""
        # Sélection du nœud / Node selection
        select_frame = ttk.Frame(parent)
        select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(select_frame, text=tr('node_label')).pack(side=tk.LEFT, padx=5)
        self.node_combo = ttk.Combobox(select_frame, state="readonly", width=30)
        self.node_combo.pack(side=tk.LEFT, padx=5)
        self.node_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_node_stats())
        
        ttk.Button(select_frame, text=tr('refresh'), command=self.refresh_node_stats).pack(side=tk.RIGHT, padx=5)
        
        # Notebook interne / Internal notebook
        self.node_notebook = ttk.Notebook(parent)
        self.node_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Arrivées / Arrivals
        arrivals_frame = ttk.Frame(self.node_notebook)
        self.node_notebook.add(arrivals_frame, text=tr('arrivals'))
        
        self.arrivals_figure = Figure(figsize=(8, 5))
        self.arrivals_canvas = FigureCanvasTkAgg(self.arrivals_figure, arrivals_frame)
        self.arrivals_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Départs / Departures
        departures_frame = ttk.Frame(self.node_notebook)
        self.node_notebook.add(departures_frame, text=tr('departures'))
        
        self.departures_figure = Figure(figsize=(8, 5))
        self.departures_canvas = FigureCanvasTkAgg(self.departures_figure, departures_frame)
        self.departures_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def set_simulator(self, simulator):
        """Définit le simulateur actif / Set active simulator"""
        self.simulator = simulator
        self.refresh_all()
    
    def refresh_all(self):
        """Rafraîchit tous les onglets / Refresh all tabs"""
        self.refresh_config()
        self.refresh_distribution()
        self.refresh_timeline()
        self.refresh_node_stats()
    
    def refresh_config(self):
        """Rafraîchit la configuration / Refresh configuration"""
        # Nettoyer / Clean
        for widget in self.config_text_widget.winfo_children():
            widget.destroy()
        
        # Parcourir les sources / Browse sources
        sources = [n for n in self.flow_model.nodes.values() if n.is_source]
        
        if not sources:
            ttk.Label(
                self.config_text_widget,
                text=tr('no_source_configured'),
                font=("Arial", 10, "italic")
            ).pack(pady=20)
            return
        
        for source in sources:
            frame = ttk.LabelFrame(self.config_text_widget, text=source.name, padding="10")
            frame.pack(fill=tk.X, pady=5, padx=10)
            
            config = source.item_type_config
            
            # Mode
            ttk.Label(frame, text=f"Mode: {config.generation_mode.value}", font=("Arial", 9, "bold")).pack(anchor=tk.W)
            
            # Types
            if config.item_types:
                types_frame = ttk.Frame(frame)
                types_frame.pack(fill=tk.X, pady=5)
                
                ttk.Label(types_frame, text=tr('types_defined'), font=("Arial", 9)).pack(anchor=tk.W)
                
                for item_type in config.item_types:
                    type_line = ttk.Frame(types_frame)
                    type_line.pack(fill=tk.X, pady=2)
                    
                    color_label = tk.Label(type_line, text="  ", bg=item_type.color, width=2, relief=tk.RAISED)
                    color_label.pack(side=tk.LEFT, padx=5)
                    
                    ttk.Label(type_line, text=item_type.name).pack(side=tk.LEFT, padx=5)
                    
                    # Info selon mode / Info by mode
                    from models.item_type import ItemGenerationMode
                    if config.generation_mode == ItemGenerationMode.RANDOM_FINITE:
                        qty = config.finite_counts.get(item_type.type_id, 0)
                        ttk.Label(type_line, text=f"({qty} {tr('units')})", font=("Arial", 8, "italic")).pack(side=tk.LEFT)
                    elif config.generation_mode == ItemGenerationMode.RANDOM_INFINITE:
                        prop = config.proportions.get(item_type.type_id, 0.0)
                        ttk.Label(type_line, text=f"({prop*100:.1f}%)", font=("Arial", 8, "italic")).pack(side=tk.LEFT)
            
            # Séquence / Sequence
            from models.item_type import ItemGenerationMode
            if config.generation_mode == ItemGenerationMode.SEQUENCE and config.sequence:
                seq_frame = ttk.Frame(frame)
                seq_frame.pack(fill=tk.X, pady=5)
                
                ttk.Label(seq_frame, text=tr('sequence'), font=("Arial", 9)).pack(anchor=tk.W)
                
                type_dict = {t.type_id: t.name for t in config.item_types}
                seq_str = " → ".join([type_dict.get(tid, tid) for tid in config.sequence])
                
                if config.sequence_loop:
                    seq_str += f" ({tr('loop')})"
                
                ttk.Label(seq_frame, text=seq_str, wraplength=500).pack(anchor=tk.W, padx=20)
    
    def refresh_distribution(self):
        """Rafraîchit le graphique de répartition / Refresh distribution chart"""
        self.dist_figure.clear()
        
        if not self.simulator or not hasattr(self.simulator, 'item_type_stats'):
            ax = self.dist_figure.add_subplot(111)
            ax.text(0.5, 0.5, tr('no_data_available'), 
                   ha='center', va='center', fontsize=12)
            self.dist_canvas.draw()
            return
        
        # Récupérer les données / Get data
        stats = self.simulator.item_type_stats
        distribution = stats.get_generation_distribution()
        
        if not distribution:
            ax = self.dist_figure.add_subplot(111)
            ax.text(0.5, 0.5, tr('no_item_generated'), ha='center', va='center', fontsize=12)
            self.dist_canvas.draw()
            return
        
        # Créer le graphique / Create chart
        ax = self.dist_figure.add_subplot(111)
        
        types = list(distribution.keys())
        counts = list(distribution.values())
        
        # Récupérer les couleurs / Get colors
        colors = self._get_type_colors(types)
        
        if self.chart_type_var.get() == "pie":
            # Camembert / Pie chart
            ax.pie(counts, labels=types, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.set_title(tr('types_distribution'))
        else:
            # Barres / Bar chart
            bars = ax.bar(types, counts, color=colors)
            ax.set_xlabel(tr('item_type'))
            ax.set_ylabel(tr('items_generated'))
            ax.set_title(tr('types_distribution'))
            ax.grid(axis='y', alpha=0.3)
            
            # Ajouter les valeurs sur les barres / Add values on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom')
        
        self.dist_figure.tight_layout()
        self.dist_canvas.draw()
    
    def refresh_timeline(self):
        """Rafraîchit la timeline / Refresh timeline"""
        self.timeline_figure.clear()
        
        if not self.simulator or not hasattr(self.simulator, 'item_type_stats'):
            ax = self.timeline_figure.add_subplot(111)
            ax.text(0.5, 0.5, tr('no_data_available'), 
                   ha='center', va='center', fontsize=12)
            self.timeline_canvas.draw()
            return
        
        # Récupérer la timeline / Get timeline
        stats = self.simulator.item_type_stats
        timeline = stats.get_generation_timeline()
        
        if not timeline:
            ax = self.timeline_figure.add_subplot(111)
            ax.text(0.5, 0.5, tr('no_item_generated'), ha='center', va='center', fontsize=12)
            self.timeline_canvas.draw()
            return
        
        # Préparer les données / Prepare data
        ax = self.timeline_figure.add_subplot(111)
        
        # Grouper par type / Group by type
        type_timelines = {}
        for timestamp, type_id in timeline:
            if type_id not in type_timelines:
                type_timelines[type_id] = []
            type_timelines[type_id].append(timestamp)
        
        # Récupérer les couleurs
        colors = self._get_type_colors(list(type_timelines.keys()))
        
        # Tracer / Plot
        y_pos = 0
        yticks = []
        yticklabels = []
        
        for type_id, timestamps in type_timelines.items():
            color = colors[list(type_timelines.keys()).index(type_id)]
            ax.scatter(timestamps, [y_pos] * len(timestamps), c=color, s=50, alpha=0.7, label=type_id)
            yticks.append(y_pos)
            yticklabels.append(type_id)
            y_pos += 1
        
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)
        ax.set_xlabel(tr('time_cs'))
        ax.set_title(tr('generation_timeline_title'))
        ax.legend(loc='upper right')
        ax.grid(axis='x', alpha=0.3)
        
        self.timeline_figure.tight_layout()
        self.timeline_canvas.draw()
    
    def refresh_node_stats(self):
        """Rafraîchit les stats par nœud / Refresh node stats"""
        # Mettre à jour la liste des nœuds / Update node list
        nodes = list(self.flow_model.nodes.values())
        node_names = [n.name for n in nodes]
        self.node_combo['values'] = node_names
        
        if not self.node_combo.get() and node_names:
            self.node_combo.current(0)
        
        selected_name = self.node_combo.get()
        if not selected_name:
            return
        
        # Trouver le nœud / Find node
        node = next((n for n in nodes if n.name == selected_name), None)
        if not node:
            return
        
        if not self.simulator or not hasattr(self.simulator, 'item_type_stats'):
            return
        
        stats = self.simulator.item_type_stats
        node_id = node.node_id
        
        # Arrivées / Arrivals
        self.arrivals_figure.clear()
        ax_arr = self.arrivals_figure.add_subplot(111)
        
        arrivals_dist = stats.get_node_distribution(node_id)
        if arrivals_dist:
            types = list(arrivals_dist.keys())
            counts = list(arrivals_dist.values())
            colors = self._get_type_colors(types)
            
            bars = ax_arr.bar(types, counts, color=colors)
            ax_arr.set_ylabel(tr('arrivals_count'))
            ax_arr.set_title(f"{tr('arrivals_on')} {node.name}")
            ax_arr.grid(axis='y', alpha=0.3)
            
            for bar in bars:
                height = bar.get_height()
                ax_arr.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom')
        else:
            ax_arr.text(0.5, 0.5, tr('no_data'), ha='center', va='center')
        
        self.arrivals_figure.tight_layout()
        self.arrivals_canvas.draw()
        
        # Départs / Departures
        self.departures_figure.clear()
        ax_dep = self.departures_figure.add_subplot(111)
        
        departures = stats.get_node_departures(node_id)
        if departures:
            # Compter par type / Count by type
            type_counts = Counter([t for _, t in departures])
            types = list(type_counts.keys())
            counts = list(type_counts.values())
            colors = self._get_type_colors(types)
            
            bars = ax_dep.bar(types, counts, color=colors)
            ax_dep.set_ylabel(tr('departures_count'))
            ax_dep.set_title(f"{tr('departures_from')} {node.name}")
            ax_dep.grid(axis='y', alpha=0.3)
            
            for bar in bars:
                height = bar.get_height()
                ax_dep.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom')
        else:
            ax_dep.text(0.5, 0.5, tr('no_data'), ha='center', va='center')
        
        self.departures_figure.tight_layout()
        self.departures_canvas.draw()
    
    def _get_type_colors(self, type_ids):
        """Récupère les couleurs des types depuis la config / Get type colors from config"""
        colors = []
        
        # Chercher dans toutes les sources / Search in all sources
        type_color_map = {}
        for node in self.flow_model.nodes.values():
            if node.is_source:
                for item_type in node.item_type_config.item_types:
                    type_color_map[item_type.type_id] = item_type.color
        
        # Mapper / Map
        default_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
        for i, type_id in enumerate(type_ids):
            if type_id in type_color_map:
                colors.append(type_color_map[type_id])
            else:
                colors.append(default_colors[i % len(default_colors)])
        
        return colors
    
    def _create_flow_tab(self, parent):
        """Onglet flux dans les connexions / Flow in connections tab"""
        # Titre / Title
        ttk.Label(
            parent,
            text=tr('flow_types_connections'),
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Info
        ttk.Label(
            parent,
            text="Visualisation des flux de types d'items circulant dans chaque connexion",  # Item type flow visualization in each connection
            font=("Arial", 9, "italic"),
            foreground="#666"
        ).pack(pady=5)
        
        # Contrôles / Controls
        controls = ttk.Frame(parent)
        controls.pack(fill=tk.X, pady=5)
        
        ttk.Button(controls, text="🔄 Actualiser", command=self.refresh_connection_flows).pack(side=tk.LEFT, padx=5)
        
        # Canvas avec scrollbar pour graphiques multiples / Canvas with scrollbar for multiple graphs
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.flow_canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        flow_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.flow_canvas.yview)
        self.flow_scrollable = ttk.Frame(self.flow_canvas)
        
        self.flow_scrollable.bind(
            "<Configure>",
            lambda e: self.flow_canvas.configure(scrollregion=self.flow_canvas.bbox("all"))
        )
        
        self.flow_canvas.create_window((0, 0), window=self.flow_scrollable, anchor="nw")
        self.flow_canvas.configure(yscrollcommand=flow_scrollbar.set)
        
        self.flow_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        flow_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Scroll avec molette - utiliser bind local au lieu de bind_all / Scroll with wheel - use local bind instead of bind_all
        def _on_mousewheel(event):
            if self.flow_canvas.winfo_exists():
                self.flow_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.flow_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.flow_scrollable.bind("<MouseWheel>", _on_mousewheel)
    
    def refresh_connection_flows(self):
        """Rafraîchit les graphiques de flux dans les connexions / Refresh connection flow graphs"""
        # Nettoyer / Clean
        for widget in self.flow_scrollable.winfo_children():
            widget.destroy()
        
        if not self.simulator or not hasattr(self.simulator, 'item_type_stats'):
            ttk.Label(
                self.flow_scrollable,
                text="⚠️ Aucune donnée de simulation disponible.\nExécutez une simulation d'abord.",  # No simulation data available. Run a simulation first.
                font=("Arial", 10)
            ).pack(pady=20)
            return
        
        stats = self.simulator.item_type_stats
        
        # Pour chaque connexion, afficher les flux / For each connection, display flows
        for conn in self.flow_model.connections:
            self._create_connection_flow_graph(conn, stats)
    
    def _create_connection_flow_graph(self, connection, stats):
        """Crée un graphique de flux pour une connexion / Create flow graph for a connection"""
        conn_id = connection.connection_id
        
        # Frame pour cette connexion / Frame for this connection
        conn_frame = ttk.LabelFrame(
            self.flow_scrollable,
            text=f"Connexion: {connection.source_node.name} → {connection.target_node.name}",
            padding="10"
        )
        conn_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Récupérer les données de flux pour cette connexion / Get flow data for this connection
        # Les données sont dans la timeline des arrivées du nœud cible / Data is in target node arrival timeline
        arrivals = stats.get_node_arrivals(connection.target_node.node_id)
        
        if not arrivals:
            ttk.Label(
                conn_frame,
                text="Aucun flux détecté",  # No flow detected
                font=("Arial", 9, "italic")
            ).pack()
            return
        
        # Créer graphique / Create graph
        fig = Figure(figsize=(10, 3), dpi=80)
        ax = fig.add_subplot(111)
        
        # Compter par type / Count by type
        type_counts = Counter([t for _, t in arrivals])
        
        if type_counts:
            types = list(type_counts.keys())
            counts = list(type_counts.values())
            colors = self._get_type_colors(types)
            
            bars = ax.bar(types, counts, color=colors)
            ax.set_ylabel("Nombre d'items")  # Number of items
            ax.set_xlabel("Type d'item")  # Item type
            ax.set_title(f"Répartition des types dans la connexion")  # Type distribution in connection
            ax.grid(axis='y', alpha=0.3)
            
            # Ajouter valeurs sur les barres / Add values on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom')
            
            # Total
            total = sum(counts)
            ax.text(0.98, 0.98, f"Total: {total} items",
                   transform=ax.transAxes, ha='right', va='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        fig.tight_layout()
        
        # Intégrer dans Tkinter / Integrate in Tkinter
        canvas = FigureCanvasTkAgg(fig, conn_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
