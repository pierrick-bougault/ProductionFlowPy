"""Panneau pour afficher les histogrammes des temps mesurés par les loupes
Panel to display histograms of times measured by probes"""
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from gui.translations import tr

class TimeProbePanel(ttk.Frame):
    """Panneau pour afficher les graphiques des loupes de temps / Panel to display time probe graphs"""
    
    def __init__(self, parent, flow_model, main_window=None):
        super().__init__(parent)
        self.configure(style='Gray.TFrame')
        self.flow_model = flow_model
        self.graphs = {}  # time_probe_id -> (fig, ax, canvas, frame)
        self.parent = parent
        self.main_window = main_window
        self.probe_checkboxes = {}  # probe_id -> (var, checkbox)
        
        # Paramètres de configuration / Configuration parameters
        self.graph_height = 3  # Hauteur des graphiques en pouces / Graph height in inches
        
        # Frame de contrôle en haut / Control frame at top
        self.control_frame = ttk.LabelFrame(self, text=tr('time_probes_panel'), padding="5")
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Frame avec scrollbar pour les graphiques / Frame with scrollbar for graphs
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas avec scrollbar (dimensionné dynamiquement) / Canvas with scrollbar (dynamically sized)
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
        
        # Bind mousewheel / Bind mousewheel
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        
        # Initialiser les graphiques / Initialize graphs
        self.refresh_all_graphs()

        # Adapter la hauteur du canvas à la taille de la fenêtre
        # Adapt canvas height to window size
        self._bind_resize_handlers()

    def _bind_resize_handlers(self):
        """Lie les événements de redimensionnement pour adapter le canvas.
        Bind resize events to adapt canvas."""
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
            try:
                main_window = root.nametowidget(root.winfo_children()[0].winfo_parent()) if root.winfo_children() else None
                if hasattr(main_window, 'master') and hasattr(main_window.master, 'is_initializing'):
                    if main_window.master.is_initializing:
                        return
            except:
                pass
            # Réserver de l'espace pour les éléments du bas (toolbar/status)
            # Reserve space for bottom elements (toolbar/status)
            reserved = 140
            height = max(200, root.winfo_height() - reserved)
            # Mettre à jour la hauteur visible du canvas sans écraser le bas
            # Update visible canvas height without overwriting bottom
            self.canvas.configure(height=height)
            # Mettre à jour la zone de scroll / Update scroll area
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Bind sur le toplevel et ce frame / Bind on toplevel and this frame
        if root:
            root.bind('<Configure>', lambda e: _on_resize(e), add='+')
    
    def _on_mousewheel(self, event):
        """Gestion de la molette de la souris / Handle mousewheel"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def refresh_all_graphs(self, force_recreate=False):
        """Rafraîchit tous les graphiques / Refresh all graphs"""
        # Toujours mettre à jour la liste des checkboxes / Always update checkbox list
        self.update_probe_list()
        
        if force_recreate:
            # Supprimer les anciens graphiques / Delete old graphs
            for graph_frame in list(self.graphs.values()):
                if len(graph_frame) >= 4:
                    graph_frame[3].destroy()
            self.graphs.clear()
            
            # Créer un graphique pour chaque loupe visible / Create graph for each visible probe
            for time_probe in self.flow_model.time_probes.values():
                if time_probe.visible:
                    self.create_graph(time_probe)
        else:
            # Mise à jour intelligente / Smart update
            current_probe_ids = set(self.flow_model.time_probes.keys())
            existing_probe_ids = set(self.graphs.keys())
            
            # Supprimer les graphiques des loupes qui n'existent plus
            # Delete graphs for probes that no longer exist
            for probe_id in existing_probe_ids - current_probe_ids:
                if probe_id in self.graphs and len(self.graphs[probe_id]) >= 4:
                    self.graphs[probe_id][3].destroy()
                    del self.graphs[probe_id]
            
            # Créer ou mettre à jour les graphiques / Create or update graphs
            for time_probe in self.flow_model.time_probes.values():
                if time_probe.visible:
                    if time_probe.probe_id in self.graphs:
                        self.update_graph(time_probe)
                    else:
                        self.create_graph(time_probe)
                elif time_probe.probe_id in self.graphs:
                    # Loupe devenue invisible, supprimer le graphique
                    # Probe became invisible, delete graph
                    self.graphs[time_probe.probe_id][3].destroy()
                    del self.graphs[time_probe.probe_id]
    
    def clear_all_graphs(self):
        """Efface complètement tous les graphiques / Completely clear all graphs"""
        # Supprimer tous les graphiques / Delete all graphs
        for graph_frame in list(self.graphs.values()):
            if len(graph_frame) >= 4:
                graph_frame[3].destroy()
        
        # Vider le dictionnaire / Empty dictionary
        self.graphs.clear()
    
    def create_graph(self, time_probe):
        """Crée un graphique pour une loupe de temps / Create graph for a time probe"""
        # Frame pour ce graphique / Frame for this graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"{time_probe.name} - {time_probe.probe_type.value}",
            padding="10"
        )
        graph_frame.pack(fill=tk.X, expand=False, padx=2, pady=2)
        
        # Récupérer les données / Get data
        measurements = time_probe.get_measurements()
        stats = time_probe.get_statistics()
        
        # Calculer la largeur disponible dynamiquement / Calculate available width dynamically
        self.update_idletasks()
        available_width = max(450, self.winfo_width() - 40)  # LARGEUR: 450px min, -40 pour scrollbar / WIDTH: 450px min, -40 for scrollbar
        
        # Créer une figure adaptée à la largeur disponible / Create figure adapted to available width
        fig_width_inches = available_width / 100.0  # 100 DPI pour cohérence / 100 DPI for consistency
        fig_height_inches = self.graph_height  # Hauteur configurable / Configurable height
        
        fig = Figure(figsize=(fig_width_inches, fig_height_inches), dpi=80)
        ax = fig.add_subplot(111)
        
        # Ajuster les marges pour éviter que le graphique soit coupé
        # Adjust margins to avoid graph being cut off
        fig.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.12)
        
        # Créer l'histogramme seulement s'il y a des données / Create histogram only if there's data
        if len(measurements) > 0:
            n_bins = min(30, max(10, len(measurements) // 10))
            counts, bins, patches = ax.hist(
                measurements,
                bins=n_bins,
                color=time_probe.color,
                alpha=0.7,
                edgecolor='black'
            )
        else:
            # Afficher un message si pas de données / Display message if no data
            ax.text(0.5, 0.5, tr('waiting_for_data'), 
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=12, color='#999', style='italic')
        
        # Ajouter les lignes de statistiques seulement s'il y a des données
        # Add statistics lines only if there's data
        if len(measurements) > 0:
            # Ajouter une ligne verticale pour la moyenne / Add vertical line for mean
            mean = stats['mean']
            ax.axvline(mean, color='red', linestyle='--', linewidth=2, label=f'Moyenne: {mean:.3f}')
            
            # Si on a un écart-type, tracer les limites ±1σ
            # If we have std dev, draw ±1σ limits
            if stats['std_dev'] > 0:
                ax.axvline(mean - stats['std_dev'], color='orange', linestyle=':', linewidth=1.5, alpha=0.7, label=f'±1σ')
                ax.axvline(mean + stats['std_dev'], color='orange', linestyle=':', linewidth=1.5, alpha=0.7)
            ax.legend()
        
        # Grid seulement (pas de labels pour garder compact) / Grid only (no labels to keep compact)
        ax.grid(True, alpha=0.3)
        
        # Statistiques textuelles (seulement s'il y a des données)
        # Text statistics (only if there's data)
        if len(measurements) > 0:
            stats_text = (
                f"N = {stats['count']} | "
                f"{tr('mean_label')} {stats['mean']:.3f} | "
                f"{tr('std_label')} {stats['std_dev']:.3f} | "
                f"{tr('min_label')} {stats['min']:.3f} | "
                f"{tr('max_label')} {stats['max']:.3f}"
            )
        else:
            stats_text = tr('no_data_collected')
        
        stats_label = ttk.Label(
            graph_frame,
            text=stats_text,
            font=("Arial", 9),
            foreground="#666"
        )
        stats_label.pack(pady=5)
        
        # Intégrer la figure dans tkinter avec taille exacte (comme pour les pipettes)
        # Integrate figure into tkinter with exact size (like for probes)
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        # Taille exacte de la figure convertie en pixels / Exact figure size converted to pixels
        canvas_widget.config(width=int(fig_width_inches * 80), height=int(fig_height_inches * 80))
        canvas_widget.pack(padx=0, pady=0)
        
        # Sauvegarder la référence / Save reference
        self.graphs[time_probe.probe_id] = (fig, ax, canvas, graph_frame)
    
    def update_graph(self, time_probe):
        """Met à jour un graphique existant sans le recréer (évite les clignotements)
        Update existing graph without recreating it (avoids flickering)"""
        if time_probe.probe_id not in self.graphs:
            return
        
        fig, ax, canvas, graph_frame = self.graphs[time_probe.probe_id]
        
        if fig is None:
            # Pas de graphique, recréer / No graph, recreate
            graph_frame.destroy()
            self.create_graph(time_probe)
            return
        
        # Récupérer les nouvelles données / Get new data
        measurements = time_probe.get_measurements()
        stats = time_probe.get_statistics()
        
        # Effacer l'ancien contenu de l'axe / Clear old axis content
        ax.clear()
        
        if len(measurements) == 0:
            ax.text(0.5, 0.5, tr('no_data'), ha='center', va='center', transform=ax.transAxes)
            canvas.draw()
            return
        
        # Redessiner l'histogramme / Redraw histogram
        n_bins = min(30, max(10, len(measurements) // 10))
        ax.hist(
            measurements,
            bins=n_bins,
            color=time_probe.color,
            alpha=0.7,
            edgecolor='black'
        )
        
        # Moyenne et écart-type / Mean and std dev
        mean = stats['mean']
        ax.axvline(mean, color='red', linestyle='--', linewidth=2, label=f'Moyenne: {mean:.3f}')
        
        if stats['std_dev'] > 0:
            ax.axvline(mean - stats['std_dev'], color='orange', linestyle=':', linewidth=1.5, alpha=0.7, label=f'±1σ')
            ax.axvline(mean + stats['std_dev'], color='orange', linestyle=':', linewidth=1.5, alpha=0.7)
        
        # Grid seulement (pas de labels pour garder compact) / Grid only (no labels to keep compact)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Mettre à jour les statistiques textuelles / Update text statistics
        stats_text = (
            f"N = {stats['count']} | "
            f"Moyenne = {stats['mean']:.3f} | "
            f"Écart-type = {stats['std_dev']:.3f} | "
            f"Min = {stats['min']:.3f} | "
            f"Max = {stats['max']:.3f}"
        )
        
        # Trouver et mettre à jour le label des statistiques
        # Find and update statistics label
        stats_label_found = False
        for widget in graph_frame.winfo_children():
            if isinstance(widget, ttk.Label):
                # Chercher le label avec les stats (peut contenir "N =" ou "Aucune donnée")
                # Look for label with stats (may contain "N =" or "No data")
                current_text = widget.cget('text')
                if 'N =' in current_text or 'Aucune' in current_text or 'donn' in current_text:
                    widget.config(text=stats_text)
                    stats_label_found = True
                    break
        
        # Si le label n'existe pas, le créer / If label doesn't exist, create it
        if not stats_label_found:
            stats_label = ttk.Label(
                graph_frame,
                text=stats_text,
                font=("Arial", 9),
                foreground="#666"
            )
            stats_label.pack(pady=5)
        
        # Redessiner le canvas / Redraw canvas
        canvas.draw_idle()  # draw_idle est plus efficace que draw() / draw_idle is more efficient than draw()
    
    def set_graph_height(self, height):
        """Change la hauteur des graphiques et les recrée / Change graph height and recreate them"""
        self.graph_height = height
        # Forcer la recréation complète de tous les graphiques avec la nouvelle taille
        # Force complete recreation of all graphs with new size
        self.refresh_all_graphs(force_recreate=True)
    
    def toggle_probe_visibility(self, time_probe):
        """Active/désactive l'affichage d'une loupe / Enable/disable probe display"""
        time_probe.visible = not time_probe.visible
        if time_probe.visible:
            self.create_graph(time_probe)
        else:
            if time_probe.probe_id in self.graphs:
                graph_frame = self.graphs[time_probe.probe_id][3]
                graph_frame.destroy()
                del self.graphs[time_probe.probe_id]
    
    def update_probe_list(self):
        """Met à jour la liste des checkboxes de loupes / Update probe checkbox list"""
        # Nettoyer les anciens checkboxes / Clean old checkboxes
        for widget in self.control_frame.winfo_children():
            widget.destroy()
        
        self.probe_checkboxes.clear()
        
        if not self.flow_model.time_probes:
            # Créer le label "aucune loupe" / Create "no probe" label
            ttk.Label(
                self.control_frame,
                text=tr('no_time_probe_installed'),
                foreground="#666",
                font=("Arial", 9, "italic")
            ).pack(pady=10)
            return
        
        # Créer un checkbox pour chaque loupe / Create checkbox for each probe
        for probe_id, time_probe in self.flow_model.time_probes.items():
            var = tk.BooleanVar(value=time_probe.visible)
            
            frame = ttk.Frame(self.control_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # Indicateur de couleur / Color indicator
            color_label = tk.Label(frame, text="  ", bg=time_probe.color, width=2)
            color_label.pack(side=tk.LEFT, padx=(5, 2))
            
            # Checkbox avec le nom / Checkbox with name
            cb = ttk.Checkbutton(
                frame,
                text=f"{time_probe.name} ({time_probe.probe_type.value})",
                variable=var,
                command=lambda tp=time_probe: self.toggle_probe_visibility(tp)
            )
            cb.pack(side=tk.LEFT, padx=2)
            
            # Bouton pour supprimer / Delete button
            delete_btn = ttk.Button(
                frame,
                text="✕",
                width=3,
                command=lambda pid=probe_id: self._remove_time_probe(pid)
            )
            delete_btn.pack(side=tk.LEFT, padx=2)
            
            self.probe_checkboxes[probe_id] = (var, cb)
    
    def _remove_time_probe(self, probe_id):
        """Supprime une loupe de temps / Delete time probe"""
        if probe_id not in self.flow_model.time_probes:
            return
        
        probe = self.flow_model.time_probes[probe_id]
        
        # Confirmation / Confirmation
        result = messagebox.askyesno(
            "Confirmer la suppression",
            f"Voulez-vous vraiment supprimer la loupe '{probe.name}' ?\n\n"
            f"Toutes les données collectées seront perdues.",
            parent=self
        )
        
        if result:
            # Supprimer la loupe / Delete probe
            del self.flow_model.time_probes[probe_id]
            
            # Rafraîchir l'affichage / Refresh display
            self.refresh_all_graphs()
            
            # Redessiner le canvas pour retirer l'icône loupe
            # Redraw canvas to remove probe icon
            if hasattr(self, 'main_window') and self.main_window:
                self.main_window.canvas.redraw_all()
