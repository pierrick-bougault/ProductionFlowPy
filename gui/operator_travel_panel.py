"""Panneau pour afficher les statistiques des temps de déplacement des opérateurs / Panel to display operator travel time statistics"""
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from gui.translations import tr

class OperatorTravelPanel(ttk.Frame):
    """Panneau pour afficher les graphiques des temps de déplacement des opérateurs / Panel to display operator travel time graphs"""
    
    def __init__(self, parent, flow_model, main_window=None):
        super().__init__(parent)
        self.configure(style='Gray.TFrame')
        self.flow_model = flow_model
        self.graphs = {}  # (operator_id, route) -> (fig, ax, canvas, frame)
        self.parent = parent
        self.main_window = main_window
        
        # Paramètres de configuration / Configuration parameters
        self.graph_height = 3  # Hauteur des graphiques en pouces / Graph height in inches
        
        # Frame de contrôle en haut / Control frame at top
        self.control_frame = ttk.LabelFrame(self, text=tr('operator_travel_probes'), padding="5")
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Frame avec scrollbar pour les graphiques / Frame with scrollbar for graphs
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas avec scrollbar / Canvas with scrollbar
        self.canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel / Lier molette souris
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        
        # Initialiser les graphiques / Initialize graphs
        self.refresh_all_graphs()
        
        # Adapter la hauteur du canvas à la taille de la fenêtre / Adapt canvas height to window size
        self._bind_resize_handlers()
    
    def _bind_resize_handlers(self):
        """Lie les événements de redimensionnement pour adapter le canvas. / Bind resize events to adapt canvas."""
        try:
            root = self.winfo_toplevel()
        except Exception:
            root = None
        
        def _on_resize(event=None):
            if not root or not root.winfo_viewable():
                return
            try:
                main_window = root.nametowidget(root.winfo_children()[0].winfo_parent()) if root.winfo_children() else None
                if hasattr(main_window, 'master') and hasattr(main_window.master, 'is_initializing'):
                    if main_window.master.is_initializing:
                        return
            except:
                pass
            reserved = 140
            height = max(200, root.winfo_height() - reserved)
            self.canvas.configure(height=height)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        if root:
            root.bind('<Configure>', lambda e: _on_resize(e), add='+')
    
    def _on_mousewheel(self, event):
        """Gestion de la molette de la souris / Mouse wheel handling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def refresh_all_graphs(self):
        """Rafraîchit tous les graphiques / Refresh all graphs"""
        # Supprimer les anciens graphiques / Delete old graphs
        for graph_frame in list(self.graphs.values()):
            if len(graph_frame) >= 4:
                graph_frame[3].destroy()
        self.graphs.clear()
        
        # Créer un graphique pour chaque loupe de déplacement activée / Create graph for each enabled travel probe
        for operator in self.flow_model.operators.values():
            if hasattr(operator, 'travel_probes') and operator.travel_probes:
                for route_key, probe in operator.travel_probes.items():
                    if probe.get('enabled', False):
                        self.create_graph(operator, route_key, probe)
    
    def create_graph(self, operator, route_key, probe):
        """Crée un graphique pour une loupe de déplacement / Create graph for a travel probe"""
        from_machine_id, to_machine_id = route_key
        
        # Récupérer les noms des nœuds / Get node names
        from_node = self.flow_model.get_node(from_machine_id)
        to_node = self.flow_model.get_node(to_machine_id)
        from_name = from_node.name if from_node else from_machine_id
        to_name = to_node.name if to_node else to_machine_id
        
        # Frame pour ce graphique / Frame for this graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"{operator.name}: {from_name} → {to_name}",
            padding="10"
        )
        graph_frame.pack(fill=tk.X, expand=False, padx=2, pady=2)
        
        # Récupérer les mesures / Get measurements
        measurements = probe.get('measurements', [])
        
        # Calculer les statistiques / Calculate statistics
        stats = {}
        if measurements:
            stats['count'] = len(measurements)
            stats['mean'] = np.mean(measurements)
            stats['std'] = np.std(measurements)
            stats['min'] = np.min(measurements)
            stats['max'] = np.max(measurements)
        else:
            stats['count'] = 0
            stats['mean'] = 0
            stats['std'] = 0
            stats['min'] = 0
            stats['max'] = 0
        
        # Calculer la largeur disponible / Calculate available width
        self.update_idletasks()
        available_width = max(450, self.winfo_width() - 40)  # LARGEUR: 450px min, -40 pour scrollbar / WIDTH: 450px min, -40 for scrollbar
        
        # Créer une figure adaptée à la largeur disponible / Create figure adapted to available width
        fig_width_inches = available_width / 100.0  # 100 DPI pour cohérence
        fig_height_inches = self.graph_height
        
        # Créer la figure / Create figure
        fig = Figure(figsize=(fig_width_inches, fig_height_inches), dpi=80)
        ax = fig.add_subplot(111)
        
        # Tracer l'histogramme / Plot histogram
        if measurements and len(measurements) > 0:
            # Calculer le nombre de bins (max 30) / Calculate number of bins (max 30)
            n_bins = min(30, max(10, len(measurements) // 5))
            ax.hist(measurements, bins=n_bins, edgecolor='black', alpha=0.7)
            ax.set_xlabel(tr('travel_time'))
            ax.set_ylabel(tr('frequency'))
            ax.set_title(f"n={stats['count']}, μ={stats['mean']:.2f}, σ={stats['std']:.2f}")
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, tr('no_measurement_available'),
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=ax.transAxes,
                   fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
        
        fig.tight_layout()
        
        # Intégrer dans tkinter / Integrate in tkinter
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Frame pour les statistiques / Frame for statistics
        stats_frame = ttk.Frame(graph_frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Afficher les statistiques / Display statistics
        if stats['count'] > 0:
            stats_text = (
                f"{tr('count_label')} {stats['count']} | "
                f"{tr('mean_label')} {stats['mean']:.2f} | "
                f"{tr('std_label')} {stats['std']:.2f} | "
                f"{tr('min_label')} {stats['min']:.2f} | "
                f"{tr('max_label')} {stats['max']:.2f}"
            )
        else:
            stats_text = tr('no_measurement')
        
        ttk.Label(stats_frame, text=stats_text, font=('TkDefaultFont', 9)).pack()
        
        # Sauvegarder les références / Save references
        graph_id = (operator.operator_id, route_key)
        self.graphs[graph_id] = (fig, ax, canvas, graph_frame)
    
    def update_all_graphs(self):
        """Met à jour tous les graphiques existants / Update all existing graphs"""
        for graph_id, (fig, ax, canvas, graph_frame) in list(self.graphs.items()):
            operator_id, route_key = graph_id
            
            # Trouver l'opérateur / Find operator
            operator = self.flow_model.operators.get(operator_id)
            if not operator or not hasattr(operator, 'travel_probes'):
                # Opérateur supprimé ou pas de travel_probes, retirer le graphique / Operator deleted or no travel_probes, remove graph
                graph_frame.destroy()
                del self.graphs[graph_id]
                continue
            
            # Vérifier si la loupe est toujours activée / Check if probe is still enabled
            probe = operator.travel_probes.get(route_key)
            if not probe or not probe.get('enabled', False):
                # Loupe désactivée, retirer le graphique / Probe disabled, remove graph
                graph_frame.destroy()
                del self.graphs[graph_id]
                continue
            
            # Mettre à jour le graphique / Update graph
            measurements = probe.get('measurements', [])
            
            # Calculer les statistiques / Calculate statistics
            stats = {}
            if measurements:
                stats['count'] = len(measurements)
                stats['mean'] = np.mean(measurements)
                stats['std'] = np.std(measurements)
                stats['min'] = np.min(measurements)
                stats['max'] = np.max(measurements)
            else:
                stats['count'] = 0
                stats['mean'] = 0
                stats['std'] = 0
                stats['min'] = 0
                stats['max'] = 0
            
            # Effacer et redessiner / Clear and redraw
            ax.clear()
            
            if measurements and len(measurements) > 0:
                n_bins = min(30, max(10, len(measurements) // 5))
                ax.hist(measurements, bins=n_bins, edgecolor='black', alpha=0.7)
                ax.set_xlabel('Temps de déplacement')  # Travel time
                ax.set_ylabel('Fréquence')  # Frequency
                ax.set_title(f"n={stats['count']}, μ={stats['mean']:.2f}, σ={stats['std']:.2f}")
                ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, 'Aucune mesure disponible',  # No measurement available
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes,
                       fontsize=12)
                ax.set_xticks([])
                ax.set_yticks([])
            
            fig.tight_layout()
            canvas.draw()
