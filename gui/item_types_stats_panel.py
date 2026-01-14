"""Panneau pour afficher les statistiques et visualisations des types d'items / Panel to display item types statistics and visualizations"""
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List
from gui.translations import tr

class ItemTypesStatsPanel(ttk.Frame):
    """Panneau pour afficher les statistiques des types d'items / Panel to display item types statistics"""
    
    def __init__(self, parent, flow_model, main_window=None):
        super().__init__(parent)
        self.flow_model = flow_model
        self.main_window = main_window
        
        # Données de suivi / Tracking data
        self.generation_history = deque(maxlen=1000)  # (temps, type_id) / (time, type_id)
        self.node_arrivals = defaultdict(lambda: defaultdict(int))  # node_id -> {type_id: count}
        self.node_departures = defaultdict(lambda: defaultdict(int))  # node_id -> {type_id: count}
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Crée les widgets / Creates the widgets"""
        # Notebook avec différentes vues / Notebook with different views
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglet 0: Types référencés / Tab 0: Referenced types
        self.types_ref_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.types_ref_frame, text=tr('referenced_types'))
        self._create_types_reference_view()
        
        # Onglet 1: Répartition globale / Tab 1: Global distribution
        self.distribution_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.distribution_frame, text=tr('types_distribution'))
        self._create_distribution_view()
        
        # Onglet 2: Historique temporel / Tab 2: Temporal history
        self.timeline_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.timeline_frame, text=tr('temporal_history'))
        self._create_timeline_view()
        
        # Onglet 3: Par nœud - RETIRÉ / Tab 3: Per node - REMOVED
        # (L'onglet statistiques par nœud a été retiré) / (The per-node statistics tab has been removed)
        
        # Bouton refresh / Refresh button
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            control_frame,
            text=tr('refresh'),
            command=self.refresh_all
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text=tr('reset_btn'),
            command=self.clear_data
        ).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, text=tr('no_data_label'))
        self.status_label.pack(side=tk.LEFT, padx=20)
    
    def _create_types_reference_view(self):
        """Crée la vue des types référencés / Creates the referenced types view"""
        # Canvas avec scrollbar / Canvas with scrollbar
        canvas_frame = ttk.Frame(self.types_ref_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Scroll avec molette / Scroll with mouse wheel
        def on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        # Contenu / Content
        self.types_ref_content = scrollable_frame
        self._update_types_reference_content()
    
    def _create_distribution_view(self):
        """Crée la vue de répartition des types / Creates the types distribution view"""
        # Contrôles en haut (fixe, non scrollable) / Controls at top (fixed, non-scrollable)
        controls = ttk.Frame(self.distribution_frame)
        controls.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(controls, text=tr('chart_type')).pack(side=tk.LEFT, padx=5)
        self.dist_chart_var = tk.StringVar(value="bar")
        ttk.Radiobutton(controls, text=tr('bar_chart'), variable=self.dist_chart_var, 
                       value="bar", command=self._update_distribution).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(controls, text=tr('pie_chart'), variable=self.dist_chart_var, 
                       value="pie", command=self._update_distribution).pack(side=tk.LEFT, padx=5)
        
        # Canvas avec scrollbar pour le contenu / Canvas with scrollbar for content
        canvas_frame = ttk.Frame(self.distribution_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        dist_scrollable = ttk.Frame(canvas)
        
        dist_scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=dist_scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Adapter la largeur du frame au canvas
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Scroll avec molette / Scroll with mouse wheel
        def on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        self.dist_canvas_widget = canvas
        self.dist_mousewheel_handler = on_mousewheel
        
        # Canvas pour graphique (taille réduite) / Canvas for chart (reduced size)
        self.dist_fig = Figure(figsize=(6, 3))
        self.dist_ax = self.dist_fig.add_subplot(111)
        self.dist_canvas = FigureCanvasTkAgg(self.dist_fig, dist_scrollable)
        self.dist_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Stats textuelles (agrandie et sans bordure noire au clic) / Text stats (enlarged and without black border on click)
        stats_frame = ttk.LabelFrame(dist_scrollable, text=tr('statistics'), padding="15")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.dist_stats_text = tk.Text(
            stats_frame, 
            height=6,  # Augmenté de 4 à 6
            wrap=tk.WORD, 
            state=tk.DISABLED,
            highlightthickness=0,  # Retire la bordure de sélection
            borderwidth=1,
            relief="solid"
        )
        self.dist_stats_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_timeline_view(self):
        """Crée la vue temporelle / Creates the temporal view"""
        # Contrôles en haut (fixe, non scrollable) / Controls at top (fixed, non-scrollable)
        controls = ttk.Frame(self.timeline_frame)
        controls.pack(fill=tk.X, padx=10, pady=5)
        
        # Navigation temporelle (comme pour les pipettes) / Temporal navigation (like for droppers)
        nav_frame = ttk.Frame(controls)
        nav_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(nav_frame, text=tr('navigation')).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(nav_frame, text="⏮", width=3, 
                  command=lambda: self._timeline_navigate('start')).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="◀", width=3,
                  command=lambda: self._timeline_navigate('back')).pack(side=tk.LEFT, padx=2)
        
        # Slider de position / Position slider
        self.timeline_position_var = tk.DoubleVar(value=1.0)
        self.timeline_slider = ttk.Scale(
            nav_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.timeline_position_var,
            command=lambda v: self._update_timeline_from_slider(),
            length=200
        )
        self.timeline_slider.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(nav_frame, text="▶", width=3,
                  command=lambda: self._timeline_navigate('forward')).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="⏭", width=3,
                  command=lambda: self._timeline_navigate('end')).pack(side=tk.LEFT, padx=2)
        
        # Label position actuelle / Current position label
        self.timeline_position_label = ttk.Label(nav_frame, text="0.0 s")
        self.timeline_position_label.pack(side=tk.LEFT, padx=10)
        
        # Canvas avec scrollbar pour le contenu / Canvas with scrollbar for content
        canvas_frame = ttk.Frame(self.timeline_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        timeline_scrollable = ttk.Frame(canvas)
        
        timeline_scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=timeline_scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Adapter la largeur du frame au canvas / Adapt frame width to canvas
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Scroll avec molette / Scroll with mouse wheel
        def on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        self.timeline_canvas_widget = canvas
        self.timeline_mousewheel_handler = on_mousewheel
        
        # Canvas pour graphique (taille réduite) / Canvas for chart (reduced size)
        self.timeline_fig = Figure(figsize=(6, 3))
        self.timeline_ax = self.timeline_fig.add_subplot(111)
        self.timeline_canvas = FigureCanvasTkAgg(self.timeline_fig, timeline_scrollable)
        self.timeline_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Info / Information
        info_label = ttk.Label(
            timeline_scrollable,
            text=tr('timeline_description'),
            font=("Arial", 9, "italic"),
            foreground="#666"
        )
        info_label.pack(pady=5)
    
    # _create_nodes_view() retiré - L'onglet statistiques par nœud a été supprimé / _create_nodes_view() removed - The per-node statistics tab has been removed
    
    def record_generation(self, time: float, type_id: str):
        """Enregistre la génération d'un item / Records an item generation"""
        self.generation_history.append((time, type_id))
    
    def record_node_arrival(self, node_id: str, type_id: str):
        """Enregistre l'arrivée d'un item sur un nœud / Records an item arrival on a node"""
        self.node_arrivals[node_id][type_id] += 1
    
    def record_node_departure(self, node_id: str, type_id: str):
        """Enregistre le départ d'un item d'un nœud / Records an item departure from a node"""
        self.node_departures[node_id][type_id] += 1
    
    def refresh_all(self):
        """Actualise tous les graphiques / Refreshes all charts"""
        self._update_types_reference_content()
        self._update_distribution()
        self._update_timeline()
        # _update_nodes_stats() retiré car l'onglet n'existe plus / _update_nodes_stats() removed as the tab no longer exists
        
        # Mettre à jour le statut / Update status
        total = len(self.generation_history)
        self.status_label.config(text=f"{total} {tr('items_generated_count')}")
    
    def _update_types_reference_content(self):
        """Met à jour le contenu de l'onglet Types Référencés / Updates the Referenced Types tab content"""
        # Effacer ancien contenu / Clear old content
        for widget in self.types_ref_content.winfo_children():
            widget.destroy()
        
        # Récupérer les types depuis les sources (utiliser un dict pour éviter les doublons) / Get types from sources (use dict to avoid duplicates)
        types_dict = {}  # type_id -> ItemType
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    # Utiliser le type_id comme clé pour éviter les doublons / Use type_id as key to avoid duplicates
                    types_dict[item_type.type_id] = item_type
        
        if types_dict:
                # Titre / Title
                ttk.Label(
                    self.types_ref_content,
                    text=tr('types_configured'),
                    font=("Arial", 12, "bold")
                ).pack(pady=10)
                
                # Liste des types avec couleurs (triés par nom) / List of types with colors (sorted by name)
                sorted_types = sorted(types_dict.values(), key=lambda t: t.name)
                for item_type in sorted_types:
                    type_frame = ttk.Frame(self.types_ref_content)
                    type_frame.pack(fill=tk.X, padx=20, pady=5)
                    
                    # Pastille de couleur / Color dot
                    color_label = tk.Label(
                        type_frame,
                        text="    ",
                        bg=item_type.color,
                        width=4,
                        relief=tk.RAISED,
                        borderwidth=2
                    )
                    color_label.pack(side=tk.LEFT, padx=5)
                    
                    # Nom du type / Type name
                    ttk.Label(
                        type_frame,
                        text=item_type.name,
                        font=("Arial", 11)
                    ).pack(side=tk.LEFT, padx=10)
                    
                    # Code couleur / Color code
                    ttk.Label(
                        type_frame,
                        text=item_type.color,
                        font=("Arial", 9),
                        foreground="#666"
                    ).pack(side=tk.LEFT, padx=10)
                
                # Info sur le nombre de types / Information about number of types
                info_frame = ttk.LabelFrame(
                    self.types_ref_content,
                    text=tr('informations'),
                    padding="10"
                )
                info_frame.pack(fill=tk.X, padx=20, pady=20)
                
                ttk.Label(
                    info_frame,
                    text=f"{tr('num_types')} {len(types_dict)}",
                    font=("Arial", 10)
                ).pack(anchor=tk.W, pady=2)
                
                return
        
        # Pas de types configurés / No types configured
        ttk.Label(
            self.types_ref_content,
            text=tr('no_item_type_msg'),
            font=("Arial", 10),
            justify=tk.CENTER,
            foreground="#666"
        ).pack(expand=True, pady=50)
    
    def _update_distribution(self):
        """Met à jour le graphique de répartition / Updates the distribution chart"""
        self.dist_ax.clear()
        
        if not self.generation_history:
            self.dist_ax.text(0.5, 0.5, tr('no_data_run_sim'),
                            ha='center', va='center', fontsize=12)
            self.dist_canvas.draw()
            return
        
        # Compter les types / Count types
        type_counts = defaultdict(int)
        for _, type_id in self.generation_history:
            type_counts[type_id] += 1
        
        # Obtenir les noms et couleurs depuis les sources du modèle / Get names and colors from model sources
        type_dict = {}
        # Chercher dans toutes les sources du modèle / Search in all model sources
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    type_dict[item_type.type_id] = (item_type.name, item_type.color)
                    # print(f"[DIST] Type enregistré depuis {node.name}: {item_type.type_id} -> {item_type.name} ({item_type.color})")
        
        # print(f"[DIST] Types dans generation_history: {set(tid for _, tid in self.generation_history)}")
        # print(f"[DIST] Types dans type_dict: {set(type_dict.keys())}")
        
        # Préparer les données / Prepare data
        labels = []
        values = []
        colors = []
        
        for type_id, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            name, color = type_dict.get(type_id, (type_id, "#999999"))
            # print(f"[DIST] Type {type_id}: nom={name}, couleur={color}")
            labels.append(name)
            values.append(count)
            colors.append(color)
        
        # Afficher selon le mode / Display according to mode
        chart_type = self.dist_chart_var.get()
        
        if chart_type == "bar":
            bars = self.dist_ax.bar(labels, values, color=colors, edgecolor='black', linewidth=1.5)
            self.dist_ax.set_ylabel(tr('num_items_generated'))
            self.dist_ax.set_xlabel(tr('item_type_label'))
            self.dist_ax.set_title(tr('item_type_distribution_title'), fontsize=12, fontweight='bold')
            
            # Ajouter les valeurs sur les barres / Add values on bars
            for bar in bars:
                height = bar.get_height()
                self.dist_ax.text(bar.get_x() + bar.get_width()/2., height,
                                f'{int(height)}',
                                ha='center', va='bottom', fontsize=9)
        else:  # pie
            self.dist_ax.pie(values, labels=labels, colors=colors, autopct='%1.1f%%',
                           startangle=90, textprops={'fontsize': 10})
            self.dist_ax.set_title(tr('item_type_distribution_title'), fontsize=12, fontweight='bold')
        
        self.dist_fig.tight_layout()
        self.dist_canvas.draw()
        
        # Mettre à jour les stats textuelles / Update text statistics
        self._update_dist_stats(type_counts, type_dict)
    
    def _update_dist_stats(self, type_counts: Dict, type_dict: Dict):
        """Met à jour les statistiques textuelles / Updates text statistics"""
        self.dist_stats_text.config(state=tk.NORMAL)
        self.dist_stats_text.delete(1.0, tk.END)
        
        total = sum(type_counts.values())
        
        stats_text = f"{tr('total_items_generated')} {total}\n\n"
        
        for type_id, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            name, _ = type_dict.get(type_id, (type_id, "#999999"))
            percentage = (count / total * 100) if total > 0 else 0
            stats_text += f"• {name} : {count} {tr('items_label')} ({percentage:.1f}%)\n"
        
        self.dist_stats_text.insert(1.0, stats_text)
        self.dist_stats_text.config(state=tk.DISABLED)
    
    def _update_timeline(self):
        """Met à jour le graphique temporel avec navigation / Updates the temporal chart with navigation"""
        self.timeline_ax.clear()
        
        if not self.generation_history:
            self.timeline_ax.text(0.5, 0.5, tr('no_data_run_sim'),
                                ha='center', va='center', fontsize=12)
            self.timeline_canvas.draw()
            return
        
        # Obtenir les infos des types depuis les sources du modèle / Get types info from model sources
        type_dict = {}
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    type_dict[item_type.type_id] = (item_type.name, item_type.color)
        
        # Mode points uniquement (lignes empilées retirées) / Points mode only (stacked lines removed)
        type_data = defaultdict(lambda: {'times': [], 'y_pos': None})
        
        # Organiser par type / Organize by type
        for time, type_id in self.generation_history:
            type_data[type_id]['times'].append(time)
        
        # Assigner positions Y / Assign Y positions
        for i, type_id in enumerate(sorted(type_data.keys())):
            type_data[type_id]['y_pos'] = i
        
        # Tracer / Draw
        for type_id, data in type_data.items():
            name, color = type_dict.get(type_id, (type_id, "#999999"))
            y_values = [data['y_pos']] * len(data['times'])
            self.timeline_ax.scatter(data['times'], y_values, c=color, 
                                   label=name, s=50, alpha=0.7, edgecolors='black')
        
        self.timeline_ax.set_ylabel("Type d'item")
        self.timeline_ax.set_yticks(range(len(type_data)))
        self.timeline_ax.set_yticklabels([type_dict.get(tid, (tid, ""))[0] 
                                         for tid in sorted(type_data.keys())])
        
        # Appliquer la fenêtre de visualisation selon la position du slider / Apply view window according to slider position
        if hasattr(self, 'timeline_position_var'):
            times = [t for t, _ in self.generation_history]
            if times:
                min_time, max_time = min(times), max(times)
                total_duration = max_time - min_time
                
                # Fenêtre de 10 secondes (ajustable) / 10 second window (adjustable)
                window_size = min(10.0, total_duration)
                
                # Position du slider (0 à 1) / Slider position (0 to 1)
                slider_pos = self.timeline_position_var.get()
                
                # Calculer les limites de la fenêtre / Calculate window limits
                if total_duration > window_size:
                    # Fenêtre mobile / Moving window
                    window_start = min_time + slider_pos * (total_duration - window_size)
                    window_end = window_start + window_size
                else:
                    # Afficher tout / Display all
                    window_start, window_end = min_time, max_time
                
                self.timeline_ax.set_xlim(window_start, window_end)
                
                # Mettre à jour le label de position / Update position label
                if hasattr(self, 'timeline_position_label'):
                    self.timeline_position_label.config(text=f"{window_start:.1f} s → {window_end:.1f} s")
        
        self.timeline_ax.set_xlabel("Temps de simulation")
        self.timeline_ax.set_title("Historique de génération des types d'items", 
                                  fontsize=12, fontweight='bold')
        self.timeline_ax.legend(loc='best')
        self.timeline_ax.grid(True, alpha=0.3)
        
        self.timeline_fig.tight_layout()
        self.timeline_canvas.draw()
    
    def _timeline_navigate(self, direction: str):
        """Navigation dans le timeline (comme pour les pipettes) / Timeline navigation (like for droppers)"""
        if not self.generation_history:
            return
        
        current_pos = self.timeline_position_var.get()
        step = 0.1  # 10% de déplacement / 10% movement
        
        if direction == 'start':
            new_pos = 0.0
        elif direction == 'end':
            new_pos = 1.0
        elif direction == 'back':
            new_pos = max(0.0, current_pos - step)
        elif direction == 'forward':
            new_pos = min(1.0, current_pos + step)
        else:
            return
        
        self.timeline_position_var.set(new_pos)
        self._update_timeline()
    
    def _update_timeline_from_slider(self):
        """Mise à jour du timeline depuis le slider / Updates timeline from slider"""
        if not self.generation_history:
            return
        self._update_timeline()
    
    def clear_data(self):
        """Efface toutes les données / Clears all data"""
        self.generation_history.clear()
        self.node_arrivals.clear()
        self.node_departures.clear()
        self.refresh_all()
        self.status_label.config(text="Données réinitialisées")
    
    def destroy(self):
        """Nettoyage lors de la destruction / Cleanup during destruction"""
        # Plus besoin de nettoyer nodes_canvas (onglet retiré) / No need to clean nodes_canvas anymore (tab removed)
        super().destroy()
