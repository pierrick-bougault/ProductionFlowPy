"""Panneau d'analyse pour exécuter des simulations batch et visualiser les résultats
Analysis panel for running batch simulations and visualizing results"""
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
from collections import defaultdict
import os
from gui.translations import tr

class AnalysisPanel(ttk.Frame):
    """Panneau pour l'analyse batch de simulations / Panel for batch analysis of simulations"""
    
    def __init__(self, parent, flow_model, time_unit_var=None, main_window=None):
        super().__init__(parent)
        self.configure(style='Gray.TFrame')
        self.flow_model = flow_model
        self.time_unit_var = time_unit_var
        self.main_window = main_window  # Référence à la fenêtre principale / Reference to main window
        self.analysis_running = False
        self.results = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Crée les widgets du panneau d'analyse / Create the analysis panel widgets"""
        # Frame de configuration / Configuration frame
        config_frame = ttk.LabelFrame(self, text=tr('analysis_config'), padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Durée de simulation / Simulation duration
        duration_frame = ttk.Frame(config_frame)
        duration_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(duration_frame, text=tr('simulation_duration')).pack(side=tk.LEFT, padx=5)
        self.duration_var = tk.StringVar(value="100")
        ttk.Entry(duration_frame, textvariable=self.duration_var, width=15).pack(side=tk.LEFT, padx=5)
        self.duration_unit_label = ttk.Label(duration_frame, text=tr('time_units'))
        self.duration_unit_label.pack(side=tk.LEFT)
        
        # Intervalle d'échantillonnage pour les arrivées (fixé à 1, masqué) / Sampling interval for arrivals (fixed at 1, hidden)
        interval_frame = ttk.Frame(config_frame)
        # interval_frame.pack(fill=tk.X, pady=5)  # Masqué / Hidden
        
        # ttk.Label(interval_frame, text="Intervalle d'analyse:").pack(side=tk.LEFT, padx=5)
        self.interval_var = tk.StringVar(value="1")  # Fixé à 1s / Fixed at 1s
        # ttk.Entry(interval_frame, textvariable=self.interval_var, width=15).pack(side=tk.LEFT, padx=5)  # Masqué / Hidden
        self.interval_unit_label = ttk.Label(interval_frame, text=tr('time_units'))
        # self.interval_unit_label.pack(side=tk.LEFT)  # Masqué / Hidden
        
        # Section de sélection des graphiques retirée - Plus nécessaire
        # Les graphiques sont maintenant configurés directement dans la fenêtre d'analyse
        # Graph selection section removed - No longer needed
        # Graphs are now configured directly in the analysis window
        
        self.show_graph_options = tk.BooleanVar(value=False)
        self.toggle_graph_btn = None  # Placeholder pour compatibilité / Placeholder for compatibility
        
        # Frame pour les options (initialement caché) - conservé pour compatibilité / Frame for options (initially hidden) - kept for compatibility
        self.graph_options_container = ttk.Frame(self)
        
        # Créer un layout en grille pour compacité / Create grid layout for compactness
        grid_frame = ttk.Frame(self.graph_options_container)
        grid_frame.pack(fill=tk.X)
        
        # Variables pour les checkboxes globales / Variables for global checkboxes
        self.show_arrivals = tk.BooleanVar(value=True)
        self.show_outputs = tk.BooleanVar(value=True)
        self.show_wip = tk.BooleanVar(value=True)
        self.show_utilization = tk.BooleanVar(value=True)
        self.show_summary = tk.BooleanVar(value=True)
        
        # Grille 2x3 pour affichage compact / 2x3 grid for compact display
        ttk.Checkbutton(
            grid_frame,
            text=tr('incoming_flows'),
            variable=self.show_arrivals,
            command=self._update_graph_display
        ).grid(row=0, column=0, sticky=tk.W, padx=3, pady=1)
        
        ttk.Checkbutton(
            grid_frame,
            text=tr('outgoing_flows'),
            variable=self.show_outputs,
            command=self._update_graph_display
        ).grid(row=0, column=1, sticky=tk.W, padx=3, pady=1)
        
        ttk.Checkbutton(
            grid_frame,
            text=tr('wip_checkbox'),
            variable=self.show_wip,
            command=self._update_graph_display
        ).grid(row=1, column=0, sticky=tk.W, padx=3, pady=1)
        
        ttk.Checkbutton(
            grid_frame,
            text=tr('utilization_checkbox'),
            variable=self.show_utilization,
            command=self._update_graph_display
        ).grid(row=1, column=1, sticky=tk.W, padx=3, pady=1)
        
        ttk.Checkbutton(
            grid_frame,
            text=tr('summary_checkbox'),
            variable=self.show_summary,
            command=self._update_graph_display
        ).grid(row=2, column=0, sticky=tk.W, padx=3, pady=1)
        
        # Section pour pipettes - sélection individuelle / Section for probes - individual selection
        separator1 = ttk.Separator(self.graph_options_container, orient='horizontal')
        separator1.pack(fill=tk.X, pady=5)
        
        pipettes_frame = ttk.Frame(self.graph_options_container)
        pipettes_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pipettes_frame, text=tr('pipettes_label'), font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=3)
        self.pipette_selection_vars = {}  # probe_id -> BooleanVar
        self.pipette_checkboxes_frame = ttk.Frame(pipettes_frame)
        self.pipette_checkboxes_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Section pour loupes - sélection individuelle / Section for time probes - individual selection
        loupes_frame = ttk.Frame(self.graph_options_container)
        loupes_frame.pack(fill=tk.X, pady=2)
        ttk.Label(loupes_frame, text=tr('loupes_label'), font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=3)
        self.loupe_selection_vars = {}  # time_probe_id -> BooleanVar
        self.loupe_checkboxes_frame = ttk.Frame(loupes_frame)
        self.loupe_checkboxes_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Créer des variables supplémentaires pour les types de graphiques de la fenêtre d'analyse / Create additional variables for analysis window graph types
        self.show_throughput = tk.BooleanVar(value=True)
        self.show_stock_levels = tk.BooleanVar(value=True)
        self.show_cumulative = tk.BooleanVar(value=True)
        
        # Créer le dictionnaire pour les types de graphiques (pour analyse) / Create dictionary for graph types (for analysis)
        self.graph_vars = {
            'throughput': self.show_throughput,
            'stocks': self.show_stock_levels,
            'production': self.show_cumulative,
            'wip': self.show_wip
        }
        
        # Bouton pour tout sélectionner/désélectionner / Button to select/deselect all
        separator2 = ttk.Separator(self.graph_options_container, orient='horizontal')
        separator2.pack(fill=tk.X, pady=5)
        btn_frame = ttk.Frame(self.graph_options_container)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text=tr('all_btn'), command=self._select_all_graphs, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=tr('none_btn'), command=self._deselect_all_graphs, width=8).pack(side=tk.LEFT, padx=2)
        
        # Boutons d'exécution et export (APRÈS la sélection des graphiques) / Execute and export buttons (AFTER graph selection)
        # Premier rang: Lancer et Exporter côte à côte / First row: Run and Export side by side
        buttons_frame_top = ttk.Frame(config_frame)
        buttons_frame_top.pack(pady=(10, 5))
        
        self.run_button = ttk.Button(
            buttons_frame_top,
            text=tr('run_analysis'),
            command=self._run_analysis
        )
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.export_button = ttk.Button(
            buttons_frame_top,
            text=tr('export_data_btn'),
            command=self._export_analysis_data,
            state="disabled"
        )
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # Deuxième rang: Afficher graphiques en dessous / Second row: Show graphs below
        buttons_frame_bottom = ttk.Frame(config_frame)
        buttons_frame_bottom.pack(pady=(0, 10))
        
        self.view_graphs_button = ttk.Button(
            buttons_frame_bottom,
            text=tr('show_analysis_graphs'),
            command=self._show_analysis_graphs,
            state="disabled"
        )
        self.view_graphs_button.pack()
        
        # Barre de progression / Progress bar
        self.progress_frame = ttk.Frame(config_frame)
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=300,
            maximum=100
        )
        self.progress_bar.pack(pady=5)
        
        # Message de statut d'analyse / Analysis status message
        self.status_label = ttk.Label(
            config_frame, 
            text="", 
            font=("Arial", 10),
            foreground="#2E7D32"
        )
        self.status_label.pack(pady=5)
    
    def update_probe_selections(self):
        """Met à jour la liste des pipettes et loupes disponibles pour sélection / Update list of available probes and time probes for selection"""
        # Effacer les anciennes checkboxes de pipettes / Clear old probe checkboxes
        for widget in self.pipette_checkboxes_frame.winfo_children():
            widget.destroy()
        
        # Créer des checkboxes pour chaque pipette / Create checkboxes for each probe
        if self.flow_model.probes:
            for probe_id, probe in self.flow_model.probes.items():
                if probe_id not in self.pipette_selection_vars:
                    self.pipette_selection_vars[probe_id] = tk.BooleanVar(value=True)
                cb = ttk.Checkbutton(
                    self.pipette_checkboxes_frame,
                    text=probe.name,
                    variable=self.pipette_selection_vars[probe_id],
                    command=self._update_graph_display
                )
                cb.pack(side=tk.LEFT, padx=2)
        else:
            ttk.Label(
                self.pipette_checkboxes_frame,
                text=tr('none_item'),
                foreground="#999"
            ).pack(side=tk.LEFT)
        
        # Effacer les anciennes checkboxes de loupes / Clear old time probe checkboxes
        for widget in self.loupe_checkboxes_frame.winfo_children():
            widget.destroy()
        
        # Créer des checkboxes pour chaque loupe / Create checkboxes for each time probe
        if hasattr(self.flow_model, 'time_probes') and self.flow_model.time_probes:
            for probe_id, probe in self.flow_model.time_probes.items():
                if probe_id not in self.loupe_selection_vars:
                    self.loupe_selection_vars[probe_id] = tk.BooleanVar(value=True)
                cb = ttk.Checkbutton(
                    self.loupe_checkboxes_frame,
                    text=probe.name,
                    variable=self.loupe_selection_vars[probe_id],
                    command=self._update_graph_display
                )
                cb.pack(side=tk.LEFT, padx=2)
        else:
            ttk.Label(
                self.loupe_checkboxes_frame,
                text=tr('none_item'),
                foreground="#999"
            ).pack(side=tk.LEFT)
    
    def _select_all_graphs(self):
        """Sélectionne tous les graphiques / Select all graphs"""
        self.show_arrivals.set(True)
        self.show_outputs.set(True)
        self.show_wip.set(True)
        self.show_utilization.set(True)
        self.show_summary.set(True)
        # Sélectionner toutes les pipettes / Select all probes
        for var in self.pipette_selection_vars.values():
            var.set(True)
        # Sélectionner toutes les loupes / Select all time probes
        for var in self.loupe_selection_vars.values():
            var.set(True)
        self._update_graph_display()
    
    def _deselect_all_graphs(self):
        """Désélectionne tous les graphiques / Deselect all graphs"""
        self.show_arrivals.set(False)
        self.show_outputs.set(False)
        self.show_wip.set(False)
        self.show_utilization.set(False)
        self.show_summary.set(False)
        # Désélectionner toutes les pipettes / Deselect all probes
        for var in self.pipette_selection_vars.values():
            var.set(False)
        # Désélectionner toutes les loupes / Deselect all time probes
        for var in self.loupe_selection_vars.values():
            var.set(False)
        self._update_graph_display()
    
    def _update_graph_display(self):
        """Met à jour l'affichage des graphiques selon la sélection / Update graph display based on selection"""
        if self.results:
            self._display_results()
    
    def _toggle_graph_options(self):
        """Affiche ou masque les options de graphiques / Show or hide graph options"""
        if self.show_graph_options.get():
            # Masquer les options / Hide options
            self.graph_options_container.pack_forget()
            self.toggle_graph_btn.config(text="▼ Options d'affichage")
            self.show_graph_options.set(False)
        else:
            # Afficher les options / Show options
            self.graph_options_container.pack(fill=tk.X, pady=5)
            self.toggle_graph_btn.config(text="▲ Options d'affichage")
            self.show_graph_options.set(True)
    
    def update_time_unit_labels(self):
        """Met à jour les labels avec l'unité de temps actuelle / Update labels with current time unit"""
        if self.time_unit_var:
            from models.time_converter import TimeUnit, TimeConverter
            try:
                time_unit = TimeUnit[self.time_unit_var.get()]
                unit_symbol = TimeConverter.get_unit_symbol(time_unit)
                self.duration_unit_label.config(text=unit_symbol)
                self.interval_unit_label.config(text=unit_symbol)
            except:
                pass
    
    def clear_analysis_results(self):
        """Efface tous les résultats d'analyse affichés / Clear all displayed analysis results"""
        # Réinitialiser l'état / Reset state
        self.results = None
        self.analysis_running = False
        self.stop_requested = False
        
        # Réactiver les boutons / Re-enable buttons
        self.run_button.config(text=tr('run_analysis'), command=self._run_analysis, state="normal")
        self.export_button.config(state="disabled")
        self.view_graphs_button.config(state="disabled")
        
        # Cacher la barre de progression / Hide progress bar
        if hasattr(self, 'progress_frame'):
            self.progress_frame.pack_forget()
        
        # Effacer le message de statut / Clear status message
        if hasattr(self, 'status_label'):
            self.status_label.config(text="")
        
        # Fermer la fenêtre des graphiques si elle est ouverte / Close graphs window if open
        if hasattr(self, 'graphs_window') and self.graphs_window and self.graphs_window.winfo_exists():
            try:
                self.graphs_window.destroy()
                self.graphs_window = None
            except:
                pass
    
    def _run_analysis(self):
        """Lance l'analyse en arrière-plan / Run analysis in background"""
        if self.analysis_running:
            messagebox.showwarning(tr('analysis_in_progress'), tr('analysis_already_running'))
            return
        
        # Mettre à jour les listes de pipettes et loupes disponibles / Update available probes and time probes lists
        self.update_probe_selections()
        self.update_idletasks()  # Forcer la mise à jour après reconstruction des checkboxes / Force update after rebuilding checkboxes
        
        # Valider les entrées / Validate inputs
        try:
            duration = float(self.duration_var.get())
            interval = float(self.interval_var.get())
            
            if duration <= 0 or interval <= 0:
                raise ValueError("Les valeurs doivent être positives / Values must be positive")
            
            if interval > duration:
                raise ValueError("L'intervalle doit être inférieur à la durée totale / Interval must be less than total duration")
        
        except ValueError as e:
            messagebox.showerror(tr('error'), f"{tr('invalid_values')}: {e}")
            return
        
        # Vérifier qu'il y a des nœuds / Check that there are nodes
        if not self.flow_model.nodes:
            messagebox.showwarning(tr('empty_model'), tr('add_nodes_first'))
            return
        
        # Vérification proactive : capacité des pipettes pour la durée demandée / Proactive check: probe capacity for requested duration
        if self.main_window and hasattr(self.main_window, 'app_config'):
            max_points = self.main_window.app_config.PROBE_ANALYSIS_MAX_POINTS
            measurement_interval = 0.06  # Intervalle de mesure des pipettes en secondes / Probe measurement interval in seconds
            estimated_points = int(duration / measurement_interval)
            
            # Calculer le pourcentage d'utilisation / Calculate usage percentage
            usage_percent = (estimated_points / max_points) * 100
            
            if usage_percent >= 100:
                # Calculer la limite recommandée (avec marge de 20%) / Calculate recommended limit (with 20% margin)
                recommended_limit = int(estimated_points * 1.2)
                # Arrondir au multiple de 50k supérieur / Round up to next 50k multiple
                recommended_limit = ((recommended_limit // 50000) + 1) * 50000
                
                # Créer une fenêtre personnalisée avec boutons / Create custom window with buttons
                response = self._show_capacity_warning_dialog(
                    duration, estimated_points, max_points, usage_percent, recommended_limit, critical=True
                )
                
                if response == "apply":
                    # Appliquer automatiquement la limite recommandée / Automatically apply recommended limit
                    self.main_window.app_config.PROBE_ANALYSIS_MAX_POINTS = recommended_limit
                    self.main_window.performance_params['probe_analysis_max_points'] = recommended_limit
                elif response == "cancel":
                    return
                # Si "continue", on poursuit sans modification / If "continue", proceed without modification
                
            elif usage_percent >= 80:
                # Avertissement si proche de la limite / Warning if close to limit
                recommended_limit = int(estimated_points * 1.2)
                recommended_limit = ((recommended_limit // 50000) + 1) * 50000
                
                response = self._show_capacity_warning_dialog(
                    duration, estimated_points, max_points, usage_percent, recommended_limit, critical=False
                )
                
                if response == "apply":
                    self.main_window.app_config.PROBE_ANALYSIS_MAX_POINTS = recommended_limit
                    self.main_window.performance_params['probe_analysis_max_points'] = recommended_limit
                elif response == "cancel":
                    return
        
        # Vérification proactive : timeout suffisant pour la durée demandée / Proactive check: sufficient timeout for requested duration
        if self.main_window and hasattr(self.main_window, 'analysis_timeout'):
            timeout = self.main_window.analysis_timeout
            # Estimation : en mode turbo, ~100 unités simulées par seconde réelle (approximation) / Estimate: in turbo mode, ~100 simulated units per real second (approximation)
            estimated_real_time = duration / 100  # Très approximatif / Very approximate
            
            if estimated_real_time > timeout:
                # Le timeout risque d'interrompre la simulation / Timeout may interrupt simulation
                recommended_timeout = int(estimated_real_time * 1.5)
                
                response = self._show_timeout_warning_dialog(
                    duration, timeout, int(estimated_real_time), recommended_timeout
                )
                
                if response == "apply":
                    # Appliquer automatiquement le timeout recommandé / Automatically apply recommended timeout
                    self.main_window.analysis_timeout = recommended_timeout
                elif response == "cancel":
                    return
        
        # Activer le mode analyse dans la fenêtre principale / Enable analysis mode in main window
        if self.main_window:
            self.main_window.is_analysis_mode = True
        
        # Démarrer l'analyse dans un thread / Start analysis in thread
        self.analysis_running = True
        self.stop_requested = False
        self.run_button.config(text="⛔ Stop Analyse", command=self._stop_analysis)
        self.export_button.config(state="disabled")
        self.view_graphs_button.config(state="disabled")
        self.progress_frame.pack(pady=10)
        self.progress_label.config(text=f"🔄 Préparation de l'analyse (durée: {duration} unités)...")
        self.progress_bar['value'] = 0
        self.update_idletasks()  # Forcer la mise à jour de l'interface avant de lancer le thread / Force UI update before launching thread
        
        thread = threading.Thread(target=self._run_simulation_batch, args=(duration, interval))
        thread.daemon = True
        thread.start()
    
    def _show_capacity_warning_dialog(self, duration, estimated_points, max_points, usage_percent, recommended_limit, critical=False):
        """Affiche un dialogue personnalisé pour l'avertissement de capacité avec option d'application automatique
        Show custom dialog for capacity warning with automatic apply option"""
        dialog = tk.Toplevel(self.main_window.root if self.main_window else None)
        dialog.title("⚠️ Capacité insuffisante" if critical else "⚠️ Avertissement capacité")
        dialog.geometry("550x400")
        dialog.transient(self.main_window.root if self.main_window else None)
        dialog.grab_set()
        
        # Centrer la fenêtre / Center window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        result = {"choice": "cancel"}
        
        # Contenu / Content
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        if critical:
            title_text = "❌ CAPACITÉ INSUFFISANTE POUR LES PIPETTES"
            warning_text = "La limite sera atteinte pendant l'analyse!\nLes données anciennes seront perdues.\nLes graphiques seront INCORRECTS."
        else:
            title_text = "⚠️ CAPACITÉ PIPETTES PROCHE DE LA LIMITE"
            warning_text = "La limite risque d'être atteinte.\nRecommandé d'augmenter la capacité."
        
        ttk.Label(main_frame, text=title_text, font=("Arial", 11, "bold"), foreground="red" if critical else "orange").pack(pady=(0, 15))
        
        info_text = (f"Durée simulation : {duration:,.0f}s\n"
                    f"Points estimés : {estimated_points:,}\n"
                    f"Limite actuelle : {max_points:,}\n"
                    f"Utilisation : {usage_percent:.0f}%\n\n"
                    f"{warning_text}\n\n"
                    f"✅ Limite recommandée : {recommended_limit:,} points")
        
        ttk.Label(main_frame, text=info_text, justify=tk.LEFT).pack(pady=(0, 20))
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        def on_apply():
            result["choice"] = "apply"
            dialog.destroy()
        
        def on_continue():
            result["choice"] = "continue"
            dialog.destroy()
        
        def on_cancel():
            result["choice"] = "cancel"
            dialog.destroy()
        
        ttk.Button(button_frame, text=f"✅ Appliquer ({recommended_limit:,} points)", command=on_apply, width=30).pack(pady=5)
        ttk.Button(button_frame, text="⚠️ Continuer sans modifier", command=on_continue, width=30).pack(pady=5)
        ttk.Button(button_frame, text="❌ Annuler l'analyse", command=on_cancel, width=30).pack(pady=5)
        
        dialog.wait_window()
        return result["choice"]
    
    def _show_timeout_warning_dialog(self, duration, timeout, estimated_real_time, recommended_timeout):
        """Affiche un dialogue personnalisé pour l'avertissement de timeout avec option d'application automatique
        Show custom dialog for timeout warning with automatic apply option"""
        dialog = tk.Toplevel(self.main_window.root if self.main_window else None)
        dialog.title("⏱️ Timeout insuffisant")
        dialog.geometry("550x380")
        dialog.transient(self.main_window.root if self.main_window else None)
        dialog.grab_set()
        
        # Centrer la fenêtre / Center window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        result = {"choice": "cancel"}
        
        # Contenu / Content
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="⏱️ TIMEOUT INSUFFISANT", font=("Arial", 11, "bold"), foreground="red").pack(pady=(0, 15))
        
        info_text = (f"Durée simulation demandée : {duration:,.0f}s\n"
                    f"Timeout actuel : {timeout}s de temps réel\n"
                    f"Temps réel estimé nécessaire : ~{estimated_real_time}s\n\n"
                    f"⚠️ La simulation risque d'être INTERROMPUE!\n"
                    f"   Les résultats seront incomplets.\n\n"
                    f"✅ Timeout recommandé : {recommended_timeout}s")
        
        ttk.Label(main_frame, text=info_text, justify=tk.LEFT).pack(pady=(0, 20))
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        def on_apply():
            result["choice"] = "apply"
            dialog.destroy()
        
        def on_continue():
            result["choice"] = "continue"
            dialog.destroy()
        
        def on_cancel():
            result["choice"] = "cancel"
            dialog.destroy()
        
        ttk.Button(button_frame, text=f"✅ Appliquer ({recommended_timeout}s)", command=on_apply, width=30).pack(pady=5)
        ttk.Button(button_frame, text="⚠️ Continuer sans modifier", command=on_continue, width=30).pack(pady=5)
        ttk.Button(button_frame, text="❌ Annuler l'analyse", command=on_cancel, width=30).pack(pady=5)
        
        dialog.wait_window()
        return result["choice"]
    
    def _stop_analysis(self):
        """Arrête l'analyse en cours / Stop current analysis"""
        if self.analysis_running:
            self.stop_requested = True
            self.run_button.config(state="disabled")
            self.progress_label.config(text="⏳ Arrêt en cours...")
    
    def _run_simulation_batch(self, duration, interval):
        """Exécute la simulation en mode batch / Run simulation in batch mode"""
        # Validation stricte des paramètres / Strict parameter validation
        if isinstance(duration, dict):
            raise ValueError(f"Duration est un dict au lieu d'un nombre: {duration}")
        if isinstance(interval, dict):
            raise ValueError(f"Interval est un dict au lieu d'un nombre: {interval}")
        if not isinstance(duration, (int, float)):
            raise ValueError(f"Duration doit être un nombre, reçu: {type(duration)} = {duration}")
        if not isinstance(interval, (int, float)):
            raise ValueError(f"Interval doit être un nombre, reçu: {type(interval)} = {interval}")
        if duration <= 0:
            raise ValueError(f"Duration doit être positif, reçu: {duration}")
        if interval <= 0:
            raise ValueError(f"Interval doit être positif, reçu: {interval}")
        
        from simulation.simulator import FlowSimulator
        from models.time_converter import TimeUnit
        
        # Obtenir l'unité de temps actuelle / Get current time unit
        if self.time_unit_var:
            try:
                time_unit = TimeUnit[self.time_unit_var.get()]
            except:
                time_unit = TimeUnit.SECONDS
        else:
            time_unit = TimeUnit.SECONDS
        
        # Créer un simulateur en mode turbo pour analyse rapide / Create turbo mode simulator for fast analysis
        simulator = FlowSimulator(
            self.flow_model,
            update_callback=None,  # Pas de mise à jour visuelle / No visual update
            speed_factor=1.0,
            time_unit=time_unit,
            fast_mode=True,  # Mode turbo: pas de synchronisation temps réel / Turbo mode: no real-time synchronization
            simulation_duration=duration  # Utiliser la durée demandée par l'utilisateur / Use user-requested duration
        )
        
        # Préparer la collecte de données / Prepare data collection
        arrivals_by_interval = defaultdict(lambda: defaultdict(int))
        arrivals_cumulative = defaultdict(int)
        outputs_by_interval = defaultdict(lambda: defaultdict(int))
        outputs_cumulative = defaultdict(int)
        
        # Suivre le WIP (Work In Progress) - nombre d'unités dans le système / Track WIP (Work In Progress) - units in system
        wip_by_interval = defaultdict(int)  # interval_index -> WIP
        
        # Suivre le taux d'utilisation des nœuds / Track node utilization rate
        node_active_time = defaultdict(float)  # Temps total actif par nœud / Total active time per node
        node_last_state_change = defaultdict(float)  # Dernier changement d'état / Last state change
        node_is_active = defaultdict(bool)  # État actuel / Current state
        
        # Données des pipettes / Probe data
        probe_data = defaultdict(lambda: defaultdict(list))  # probe_id -> interval -> [(timestamp, value)]
        probe_type_data = defaultdict(lambda: defaultdict(list))  # probe_id -> interval -> [(timestamp, type_counts_dict)]
        
        # NOUVEAU: Données séparées buffer/cumulative pour export CSV / NEW: Separate buffer/cumulative data for CSV export
        probe_data_buffer = defaultdict(lambda: defaultdict(list))  # probe_id -> interval -> [(timestamp, buffer_value)]
        probe_data_cumulative = defaultdict(lambda: defaultdict(list))  # probe_id -> interval -> [(timestamp, cumulative_value)]
        
        # Données des buffers / Buffer data
        buffer_data = defaultdict(lambda: defaultdict(list))  # conn_id -> interval -> [(timestamp, count)]
        
        # Données des états des machines et opérateurs / Machine and operator state data
        machine_states = defaultdict(list)  # node_id -> [(timestamp, "ON"/"OFF")]
        operator_states = defaultdict(list)  # operator_id -> [(timestamp, {'action': str, 'position': str})]
        
        # Données des types d'items / Item type data
        item_types_generation_history = []  # [(timestamp, type_id)]
        item_types_node_arrivals = defaultdict(lambda: defaultdict(int))  # node_id -> {type_id: count}
        
        # Hook pour capturer les événements / Hook to capture events
        def capture_arrival(node_id, timestamp):
            if not isinstance(interval, (int, float)) or interval <= 0:
                return
            interval_index = int(timestamp // interval)
            arrivals_by_interval[node_id][interval_index] += 1
            arrivals_cumulative[node_id] += 1
        
        def capture_output(node_id, timestamp):
            if not isinstance(interval, (int, float)) or interval <= 0:
                return
            interval_index = int(timestamp // interval)
            outputs_by_interval[node_id][interval_index] += 1
            outputs_cumulative[node_id] += 1
        
        def capture_node_active_change(node_id, timestamp, is_active):
            """Capture les changements d'état actif/inactif des nœuds / Capture node active/inactive state changes"""
            if node_id in node_is_active and node_is_active[node_id]:
                # Le nœud était actif, ajouter le temps écoulé / Node was active, add elapsed time
                elapsed = timestamp - node_last_state_change[node_id]
                node_active_time[node_id] += elapsed
            
            node_is_active[node_id] = is_active
            node_last_state_change[node_id] = timestamp
        
        def capture_probe_measurement(probe_id, timestamp, value):
            """Capture les mesures des pipettes / Capture probe measurements"""
            if not isinstance(interval, (int, float)) or interval <= 0:
                return
            interval_index = int(timestamp // interval)
            probe_data[probe_id][interval_index].append((timestamp, value))
        
        def capture_probe_measurement_both(probe_id, timestamp, buffer_value, cumulative_value):
            """Capture les mesures des pipettes - les deux types (buffer et cumulative) / Capture probe measurements - both types (buffer and cumulative)"""
            if not isinstance(interval, (int, float)) or interval <= 0:
                return
            interval_index = int(timestamp // interval)
            probe_data_buffer[probe_id][interval_index].append((timestamp, buffer_value))
            probe_data_cumulative[probe_id][interval_index].append((timestamp, cumulative_value))
        
        def capture_buffer_state(conn_id, timestamp, count):
            """Capture l'état d'un buffer / Capture buffer state"""
            if not isinstance(interval, (int, float)) or interval <= 0:
                return
            interval_index = int(timestamp // interval)
            buffer_data[conn_id][interval_index].append((timestamp, count))
            # Debug: Afficher les 10 premières et dernières captures (désactivé) / Debug: Show first and last 10 captures (disabled)
            # if len(buffer_data[conn_id][interval_index]) <= 10 or timestamp > 195:
            #     print(f"[DEBUG BUFFER] t={timestamp:.2f}s | conn={conn_id} | count={count} | interval={interval_index}")
        
        def capture_wip(timestamp):
            """Capture le Work In Progress (nombre total d'unités dans le système) / Capture Work In Progress (total units in system)"""
            if not isinstance(interval, (int, float)) or interval <= 0:
                return
            interval_index = int(timestamp // interval)
            # Compter les unités dans tous les buffers / Count units in all buffers
            total_wip = sum(conn.current_buffer_count for conn in self.flow_model.connections.values())
            # Stocker le WIP maximum pour cet intervalle / Store maximum WIP for this interval
            wip_by_interval[interval_index] = max(wip_by_interval.get(interval_index, 0), total_wip)
        
        def capture_machine_state(node_id, timestamp, state):
            """Capture les changements d'état des machines (ON/OFF) / Capture machine state changes (ON/OFF)"""
            machine_states[node_id].append((timestamp, state))
        
        def capture_operator_state(operator_id, timestamp, action, position):
            """Capture les états des opérateurs (action et position) / Capture operator states (action and position)"""
            state_data = {
                'action': action,
                'position': position
            }
            operator_states[operator_id].append((timestamp, state_data))
        
        def capture_item_generation(timestamp, type_id):
            """Capture la génération d'un item avec son type / Capture item generation with its type"""
            item_types_generation_history.append((timestamp, type_id))
        
        def capture_item_node_arrival(node_id, type_id):
            """Capture l'arrivée d'un type d'item dans un nœud / Capture item type arrival in a node"""
            item_types_node_arrivals[node_id][type_id] += 1
        
        # Réinitialiser les pipettes de mesure avant de lancer l'analyse / Reset measurement probes before starting analysis
        if hasattr(self.flow_model, 'probes'):
            for probe in self.flow_model.probes.values():
                probe.clear_data()
        
        # Réinitialiser les loupes de temps avant de lancer l'analyse / Reset time probes before starting analysis
        if hasattr(self.flow_model, 'time_probes'):
            for time_probe in self.flow_model.time_probes.values():
                time_probe.clear_data()
        
        # Patcher le simulateur pour capturer les événements / Patch simulator to capture events
        simulator._capture_arrival = capture_arrival
        simulator._capture_output = capture_output
        simulator._capture_node_active_change = capture_node_active_change
        simulator._capture_probe_measurement = capture_probe_measurement
        simulator._capture_probe_measurement_both = capture_probe_measurement_both  # NOUVEAU: pour export CSV / NEW: for CSV export
        simulator._capture_buffer_state = capture_buffer_state
        simulator._capture_wip = capture_wip
        simulator._capture_machine_state = capture_machine_state
        simulator._capture_operator_state = capture_operator_state
        simulator._record_item_generation = capture_item_generation
        simulator._record_node_arrival = capture_item_node_arrival
        
        # Lancer la simulation / Start simulation
        simulator.start()
        
        # En mode turbo, attendre simplement que le thread se termine / In turbo mode, just wait for thread to finish
        # La simulation s'exécute directement sans sleep() / Simulation runs directly without sleep()
        import time
        start_real_time = time.time()
        # Utiliser le timeout configuré ou 600s par défaut / Use configured timeout or 600s default
        max_wait = getattr(self.main_window, 'analysis_timeout', 600) if self.main_window else 600
        last_progress_update = 0
        
        # Attendre la fin du thread de simulation avec mise à jour de la progression / Wait for simulation thread with progress update
        while simulator.is_running:
            # Vérifier si l'utilisateur a demandé l'arrêt / Check if user requested stop
            if self.stop_requested:
                simulator.stop()
                self.progress_label.config(text="⛔ Analyse arrêtée par l'utilisateur")
                self.update_idletasks()
                break
            
            if time.time() - start_real_time > max_wait:
                # Timeout atteint - Arrêter la simulation et notifier l'utilisateur / Timeout reached - Stop simulation and notify user
                current_sim_time = simulator.env.now if (simulator.env and hasattr(simulator.env, 'now')) else 0
                
                # Afficher une fenêtre d'avertissement / Show warning window
                timeout_message = (
                    f"⏱️ TIMEOUT DE SIMULATION ATTEINT\n\n"
                    f"La simulation a été interrompue après {max_wait}s de temps réel.\n\n"
                    f"Temps simulé atteint : {current_sim_time:,.0f}s\n"
                    f"Durée demandée : {duration:,.0f}s\n"
                    f"Progression : {(current_sim_time/duration)*100:.1f}%\n\n"
                    f"❌ Les résultats sont INCOMPLETS!\n\n"
                    f"✅ SOLUTIONS :\n"
                    f"• Réduire la durée de simulation\n"
                    f"• Augmenter le timeout dans:\n"
                    f"  Paramètres > Paramètres Généraux > Timeout d'analyse\n"
                    f"  Recommandé pour {duration:,.0f}s : {int(duration/100)}s minimum"
                )
                
                self.progress_label.config(text=f"⏱️ Timeout atteint - Analyse interrompue à {current_sim_time:.0f}s/{duration:.0f}s")
                self.update_idletasks()
                messagebox.showwarning(tr('simulation_timeout'), timeout_message)
                
                simulator.stop()
                break
            
            # Mettre à jour la progression toutes les 0.5 secondes / Update progress every 0.5 seconds
            if time.time() - last_progress_update > 0.5:
                current_sim_time = simulator.env.now if (simulator.env and hasattr(simulator.env, 'now')) else 0
                progress_percent = min(100, (current_sim_time / duration) * 100)
                self.progress_bar['value'] = progress_percent
                self.progress_label.config(text=f"⏳ Analyse en cours... {progress_percent:.0f}% (temps: {current_sim_time:.1f}/{duration})")
                self.update_idletasks()
                last_progress_update = time.time()
            
            time.sleep(0.1)  # Vérification toutes les 100ms / Check every 100ms
        
        # Finaliser le temps actif des nœuds encore actifs / Finalize active time for still-active nodes
        final_time = simulator.env.now if (simulator.env and hasattr(simulator.env, 'now')) else duration
        for node_id, is_active in node_is_active.items():
            if is_active:
                elapsed = final_time - node_last_state_change[node_id]
                node_active_time[node_id] += elapsed
        
        # Arrêter / Stop
        simulator.stop()
        
        # Calculer les taux d'utilisation des nœuds / Calculate node utilization rates
        node_utilization = {}
        for node_id in self.flow_model.nodes.keys():
            active_time = node_active_time.get(node_id, 0)
            utilization = (active_time / final_time * 100) if final_time > 0 else 0
            node_utilization[node_id] = utilization
        
        # Calculer les taux d'utilisation des opérateurs / Calculate operator utilization rates
        # Inclure le temps de déplacement dans le calcul d'utilisation / Include travel time in utilization calculation
        operator_utilization = {}
        operator_total_utilization = {}  # Garde pour compatibilité / Keep for compatibility
        if hasattr(simulator, 'operator_busy_time'):
            for operator_id, busy_time in simulator.operator_busy_time.items():
                # Calculer utilisation TOTALE (busy + travel) comme utilisation principale / Calculate TOTAL utilization (busy + travel) as main utilization
                travel_time = simulator.operator_travel_time.get(operator_id, 0) if hasattr(simulator, 'operator_travel_time') else 0
                total_time = busy_time + travel_time
                total_utilization = (total_time / final_time * 100) if final_time > 0 else 0
                
                # Utilisation principale inclut le déplacement / Main utilization includes travel
                operator_utilization[operator_id] = total_utilization
                operator_total_utilization[operator_id] = total_utilization
                
                if False:
                    print(f"[UTIL] Opérateur {operator_id}: busy={busy_time:.2f}, travel={travel_time:.2f}, total={total_time:.2f}, util={total_utilization:.1f}%")
        
        # Convertir probe_data et buffer_data (defaultdict imbriqué) en dict normal / Convert probe_data and buffer_data (nested defaultdict) to normal dict
        probe_data_dict = {}
        for probe_id, intervals in probe_data.items():
            probe_data_dict[probe_id] = dict(intervals)
        
        # NOUVEAU: Convertir les données buffer/cumulative pour export CSV / NEW: Convert buffer/cumulative data for CSV export
        probe_data_buffer_dict = {}
        for probe_id, intervals in probe_data_buffer.items():
            probe_data_buffer_dict[probe_id] = dict(intervals)
        
        probe_data_cumulative_dict = {}
        for probe_id, intervals in probe_data_cumulative.items():
            probe_data_cumulative_dict[probe_id] = dict(intervals)
        
        # Collecter les données de types depuis les pipettes après la simulation / Collect type data from probes after simulation
        probe_type_data_dict = {}
        for probe_id, probe in self.flow_model.probes.items():
            if hasattr(probe, 'type_data_points') and probe.type_data_points:
                # Organiser par intervalle comme pour probe_data / Organize by interval like probe_data
                probe_type_data_dict[probe_id] = {}
                for timestamp, type_counts in probe.type_data_points:
                    if not isinstance(interval, (int, float)) or interval <= 0:
                        continue
                    interval_index = int(timestamp // interval)
                    if interval_index not in probe_type_data_dict[probe_id]:
                        probe_type_data_dict[probe_id][interval_index] = []
                    probe_type_data_dict[probe_id][interval_index].append((timestamp, type_counts))
        
        buffer_data_dict = {}
        for conn_id, intervals in buffer_data.items():
            buffer_data_dict[conn_id] = dict(intervals)
            # Debug: Afficher le résumé des données collectées par buffer / Debug: Show collected data summary per buffer
            total_points = sum(len(interval_data) for interval_data in intervals.values())
            if intervals:
                all_timestamps = []
                for interval_data in intervals.values():
                    all_timestamps.extend([t for t, _ in interval_data])
                if all_timestamps:
                    min_t = min(all_timestamps)
                    max_t = max(all_timestamps)
                    # print(f"[DEBUG COLLECT] Buffer {conn_id}: {total_points} points | t_min={min_t:.2f}s | t_max={max_t:.2f}s")
        
        # Collecter les données des time_probes (loupes de temps) / Collect time probe data
        time_probe_data = {}
        if False:
            print(f"\n[DEBUG ANALYSIS] Collecte des données de loupes de temps")
        if False:
            print(f"[DEBUG ANALYSIS] Nombre de loupes dans flow_model: {len(self.flow_model.time_probes) if hasattr(self.flow_model, 'time_probes') else 0}")
        
        if hasattr(self.flow_model, 'time_probes'):
            for probe_id, time_probe in self.flow_model.time_probes.items():
                if False:
                    print(f"[DEBUG ANALYSIS] Loupe {probe_id} ({time_probe.name}):")
                if False:
                    print(f"  - has get_measurements: {hasattr(time_probe, 'get_measurements')}")
                
                if hasattr(time_probe, 'get_measurements'):
                    measurements = time_probe.get_measurements()
                    if False:
                        print(f"  - measurements type: {type(measurements)}")
                    if False:
                        print(f"  - measurements length: {len(measurements) if measurements else 0}")
                    
                    if measurements:
                        time_probe_data[probe_id] = measurements
                        if False:
                            print(f"  ✓ Données ajoutées: {len(measurements)} mesures")
                        if len(measurements) > 0:
                            if False:
                                print(f"  - Exemple (premiers 3): {measurements[:3]}")
                    else:
                        if False:
                            print(f"  ⚠ Aucune mesure collectée")
                else:
                    if False:
                        print(f"  ✗ Pas de méthode get_measurements")
        
        if False:
            print(f"[DEBUG ANALYSIS] Total loupes avec données: {len(time_probe_data)}")
        if False:
            print(f"[DEBUG ANALYSIS] IDs des loupes avec données: {list(time_probe_data.keys())}\n")
        
        # Collecter les données des déplacements opérateurs (loupes de mouvement) / Collect operator travel data (movement probes)
        operator_travel_data = {}
        for operator_id, operator in self.flow_model.operators.items():
            if hasattr(operator, 'travel_probes') and operator.travel_probes:
                operator_travel_data[operator_id] = {}
                for route_key, probe in operator.travel_probes.items():
                    if probe.get('enabled', False) and 'measurements' in probe:
                        operator_travel_data[operator_id][route_key] = probe['measurements']
        
        # Convertir machine_states et operator_states en dict normal / Convert machine_states and operator_states to normal dict
        machine_states_dict = {node_id: list(states) for node_id, states in machine_states.items()}
        operator_states_dict = {operator_id: list(states) for operator_id, states in operator_states.items()}
        
        # Préparer les résultats / Prepare results
        self.results = {
            'duration': duration,
            'interval': interval,
            'time_unit': time_unit,
            'arrivals_by_interval': dict(arrivals_by_interval),
            'arrivals_cumulative': dict(arrivals_cumulative),
            'outputs_by_interval': dict(outputs_by_interval),
            'outputs_cumulative': dict(outputs_cumulative),
            'num_intervals': int(duration / interval) if isinstance(duration, (int, float)) and isinstance(interval, (int, float)) and interval > 0 else 0,
            'node_utilization': node_utilization,
            'utilization_data': node_utilization,  # Alias pour compatibilité avec analysis_graph_window / Alias for compatibility with analysis_graph_window
            'operator_utilization': operator_utilization,  # Utilisation des opérateurs (contrôle uniquement) / Operator utilization (control only)
            'operator_total_utilization': operator_total_utilization,  # Utilisation totale (contrôle + déplacement) / Total utilization (control + travel)
            'probe_data': probe_data_dict,
            'probe_data_buffer': probe_data_buffer_dict,  # NOUVEAU: Données buffer pour export CSV / NEW: Buffer data for CSV export
            'probe_data_cumulative': probe_data_cumulative_dict,  # NOUVEAU: Données cumulative pour export CSV / NEW: Cumulative data for CSV export
            'probe_type_data': probe_type_data_dict,  # Données par type pour les pipettes / Data by type for probes
            'buffer_data': buffer_data_dict,
            'wip_by_interval': dict(wip_by_interval),
            'time_probe_data': time_probe_data,  # Données des loupes de temps / Time probe data
            'operator_travel_data': operator_travel_data,  # Données des déplacements opérateurs / Operator travel data
            'machine_states': machine_states_dict,  # États ON/OFF des machines / Machine ON/OFF states
            'operator_states': operator_states_dict,  # États (action, position) des opérateurs / Operator states (action, position)
            'item_types_data': {  # Données des types d'items / Item type data
                'generation_history': item_types_generation_history,
                'node_arrivals': dict(item_types_node_arrivals)
            }
        }
        
        # Mettre à jour l'interface dans le thread principal / Update interface in main thread
        self.after(0, lambda: self.progress_label.config(text=tr('analysis_complete_generating')))
        self.after(0, self._display_results)
    
    def _display_results(self):
        """Affiche les résultats de l'analyse / Display analysis results"""
        self.analysis_running = False
        self.stop_requested = False
        self.run_button.config(text=tr('run_analysis'), command=self._run_analysis, state="normal")
        self.export_button.config(state="normal")  # Activer l'export après une analyse / Enable export after analysis
        self.view_graphs_button.config(state="normal")  # Activer le bouton d'affichage des graphiques / Enable graphs display button
        self.progress_bar['value'] = 0
        self.progress_frame.pack_forget()
        
        # Afficher un message de succès dans le panneau / Show success message in panel
        self.status_label.config(
            text=tr('analysis_success'),
            foreground="#2E7D32"
        )
    
    def _create_arrivals_graphs(self):
        """Crée les graphiques d'arrivées pour les sources / Create arrival graphs for sources"""
        sources = [node for node in self.flow_model.nodes.values() if node.is_source]
        
        if not sources:
            return
        
        # Titre / Title
        ttk.Label(
            self.scrollable_frame,
            text="📥 Analyse des flux entrants (Sources)",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        for node in sources:
            self._create_node_arrival_graph(node)
    
    def _create_node_arrival_graph(self, node):
        """Crée un graphique pour les arrivées d'un nœud source / Create a graph for source node arrivals"""
        node_id = node.node_id
        interval = self.results['interval']
        num_intervals = self.results['num_intervals']
        time_unit = self.results.get('time_unit')
        
        from models.time_converter import TimeConverter
        unit_symbol = TimeConverter.get_unit_symbol(time_unit) if time_unit else "unités"
        
        # Frame pour le graphique / Frame for graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"Source: {node.name}",
            padding="10"
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Créer la figure matplotlib / Create matplotlib figure
        fig = Figure(figsize=(8, 3), dpi=80)
        ax = fig.add_subplot(111)
        
        # Récupérer les données / Get data
        arrivals_data = self.results['arrivals_by_interval'].get(node_id, {})
        
        # Préparer les données pour le graphique / Prepare data for graph
        intervals = list(range(num_intervals))
        counts = [arrivals_data.get(i, 0) for i in intervals]
        
        # Créer le graphique / Create graph
        ax.bar(intervals, counts, color='#4CAF50', alpha=0.7, label=node.name)
        ax.set_xlabel(f'Intervalle de temps ({unit_symbol})')
        ax.set_ylabel('Nombre d\'arrivées')
        ax.set_title(f'Arrivées - {node.name} (intervalle: {interval} {unit_symbol})')
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend()
        
        # Stats / Stats
        total = sum(counts)
        avg = total / num_intervals if num_intervals > 0 else 0
        
        stats_text = f"Total: {total} | Moyenne: {avg:.2f}/intervalle | Max: {max(counts) if counts else 0}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        fig.tight_layout()
        
        # Canvas matplotlib / Matplotlib canvas
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_outputs_graphs(self):
        """Crée les graphiques de sorties pour les sinks / Create output graphs for sinks"""
        sinks = [node for node in self.flow_model.nodes.values() if node.is_sink]
        
        if not sinks:
            return
        
        # Titre / Title
        ttk.Label(
            self.scrollable_frame,
            text="📤 Analyse des flux sortants (Sorties)",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        for node in sinks:
            self._create_node_output_graph(node)
    
    def _create_node_output_graph(self, node):
        """Crée un graphique pour les sorties d'un nœud sink / Create a graph for sink node outputs"""
        node_id = node.node_id
        interval = self.results['interval']
        num_intervals = self.results['num_intervals']
        time_unit = self.results.get('time_unit')
        
        from models.time_converter import TimeConverter
        unit_symbol = TimeConverter.get_unit_symbol(time_unit) if time_unit else "unités"
        
        # Frame pour le graphique / Frame for graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"Sortie: {node.name}",
            padding="10"
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Créer la figure matplotlib / Create matplotlib figure
        fig = Figure(figsize=(8, 3), dpi=80)
        ax = fig.add_subplot(111)
        
        # Récupérer les données / Get data
        outputs_data = self.results['outputs_by_interval'].get(node_id, {})
        
        # Préparer les données pour le graphique / Prepare data for graph
        intervals = list(range(num_intervals))
        counts = [outputs_data.get(i, 0) for i in intervals]
        
        # Créer le graphique / Create graph
        ax.bar(intervals, counts, color='#F44336', alpha=0.7, label=node.name)
        ax.set_xlabel(f'Intervalle de temps ({unit_symbol})')
        ax.set_ylabel('Nombre de sorties')
        ax.set_title(f'Sorties - {node.name} (intervalle: {interval} {unit_symbol})')
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend()
        
        # Stats / Stats
        total = sum(counts)
        avg = total / num_intervals if num_intervals > 0 else 0
        
        stats_text = f"Total: {total} | Moyenne: {avg:.2f}/intervalle | Max: {max(counts) if counts else 0}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        fig.tight_layout()
        
        # Canvas matplotlib / Matplotlib canvas
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_wip_graph(self):
        """Crée le graphique du Work In Progress (WIP) / Create Work In Progress (WIP) graph"""
        wip_data = self.results.get('wip_by_interval', {})
        
        if not wip_data:
            return
        
        interval = self.results['interval']
        num_intervals = self.results['num_intervals']
        time_unit = self.results.get('time_unit')
        
        from models.time_converter import TimeConverter
        unit_symbol = TimeConverter.get_unit_symbol(time_unit) if time_unit else "unités"
        
        # Titre / Title
        ttk.Label(
            self.scrollable_frame,
            text="📊 Work In Progress (WIP)",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Frame pour le graphique / Frame for graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text="Nombre d'unités présentes dans le système",
            padding="10"
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Créer la figure matplotlib / Create matplotlib figure
        fig = Figure(figsize=(8, 3), dpi=80)
        ax = fig.add_subplot(111)
        
        # Préparer les données pour le graphique / Prepare data for graph
        intervals = list(range(num_intervals))
        wip_values = [wip_data.get(i, 0) for i in intervals]
        
        # Créer le graphique en ligne / Create line graph
        ax.plot(intervals, wip_values, color='#2196F3', linewidth=2, marker='o', markersize=4, label='WIP')
        ax.fill_between(intervals, wip_values, alpha=0.3, color='#2196F3')
        ax.set_xlabel(f'Intervalle de temps ({unit_symbol})')
        ax.set_ylabel('Nombre d\'unités')
        ax.set_title(f'Work In Progress (WIP) - Variation du nombre d\'unités dans le système')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Stats / Stats
        avg_wip = sum(wip_values) / len(wip_values) if wip_values else 0
        max_wip = max(wip_values) if wip_values else 0
        min_wip = min(wip_values) if wip_values else 0
        
        stats_text = f"Moyenne: {avg_wip:.2f} | Min: {min_wip} | Max: {max_wip}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        
        fig.tight_layout()
        
        # Canvas matplotlib / Matplotlib canvas
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_probe_graphs(self):
        """Crée les graphiques pour les pipettes - sélection individuelle / Create graphs for probes - individual selection"""
        if not self.flow_model.probes or 'probe_data' not in self.results:
            return
        
        probe_data = self.results['probe_data']
        if not probe_data:
            return
        
        # Compter combien de pipettes sont sélectionnées / Count how many probes are selected
        selected_count = sum(1 for probe_id in self.flow_model.probes.keys() 
                           if probe_id in self.pipette_selection_vars and self.pipette_selection_vars[probe_id].get())
        
        if selected_count == 0:
            return
        
        # Titre / Title
        ttk.Label(
            self.scrollable_frame,
            text="🔬 Analyse des pipettes de mesure",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Afficher seulement les pipettes sélectionnées / Show only selected probes
        for probe_id, probe in self.flow_model.probes.items():
            # Vérifier si cette pipette est sélectionnée / Check if this probe is selected
            if probe_id in self.pipette_selection_vars and self.pipette_selection_vars[probe_id].get():
                if probe_id in probe_data:
                    self._create_probe_graph(probe, probe_data[probe_id])
    
    def _create_probe_graph(self, probe, intervals_data):
        """Crée un graphique pour une pipette / Create a graph for a probe"""
        interval = self.results['interval']
        num_intervals = self.results['num_intervals']
        time_unit = self.results.get('time_unit')
        
        from models.time_converter import TimeConverter
        unit_symbol = TimeConverter.get_unit_symbol(time_unit) if time_unit else "unités"
        
        # Frame pour le graphique / Frame for graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"Pipette: {probe.name}",
            padding="10"
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Créer la figure matplotlib / Create matplotlib figure
        fig = Figure(figsize=(8, 3), dpi=80)
        ax = fig.add_subplot(111)
        
        # Agréger les données par intervalle (moyenne) / Aggregate data by interval (average)
        interval_averages = []
        for i in range(num_intervals):
            if i in intervals_data and intervals_data[i]:
                values = [v for _, v in intervals_data[i]]
                avg = sum(values) / len(values)
                interval_averages.append(avg)
            else:
                interval_averages.append(0)
        
        # Créer le graphique / Create graph
        intervals = list(range(num_intervals))
        ax.plot(intervals, interval_averages, color=probe.color, linewidth=2, marker='o', label=probe.name)
        ax.fill_between(intervals, interval_averages, alpha=0.3, color=probe.color)
        
        ax.set_xlabel(f'Intervalle de temps ({unit_symbol})')
        
        if probe.measure_mode == "cumulative":
            ax.set_ylabel('Items cumulés')
            ax.set_title(f'Pipette {probe.name} - Mode cumulatif')
        else:
            ax.set_ylabel('Items dans buffer (moyenne)')
            ax.set_title(f'Pipette {probe.name} - Buffer moyen')
        
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        fig.tight_layout()
        
        # Canvas matplotlib / Matplotlib canvas
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_utilization_graph(self):
        """Crée un graphique du taux d'utilisation des nœuds / Create a graph of node utilization rate"""
        if 'node_utilization' not in self.results:
            return
        
        utilization = self.results['node_utilization']
        if not utilization:
            return
        
        # Titre / Title
        ttk.Label(
            self.scrollable_frame,
            text="📊 Taux d'utilisation des nœuds",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Frame pour le graphique / Frame for graph
        graph_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text="Taux d'utilisation (%)",
            padding="10"
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Créer la figure matplotlib / Create matplotlib figure
        fig = Figure(figsize=(8, 4), dpi=80)
        ax = fig.add_subplot(111)
        
        # Préparer les données / Prepare data
        node_names = []
        utilization_values = []
        colors = []
        
        for node_id, util in utilization.items():
            node = self.flow_model.get_node(node_id)
            if node:
                node_names.append(node.name)
                utilization_values.append(util)
                
                # Couleur selon le type / Color by type
                if node.is_source:
                    colors.append('#4CAF50')
                elif node.is_sink:
                    colors.append('#F44336')
                else:
                    colors.append('#2196F3')
        
        # Créer le graphique en barres horizontales / Create horizontal bar chart
        y_pos = range(len(node_names))
        bars = ax.barh(y_pos, utilization_values, color=colors, alpha=0.7)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(node_names)
        ax.set_xlabel('Taux d\'utilisation (%)')
        ax.set_xlim(0, 100)
        ax.grid(True, alpha=0.3, axis='x')
        
        # Ajouter les valeurs sur les barres / Add values on bars
        for i, (bar, value) in enumerate(zip(bars, utilization_values)):
            ax.text(value + 1, i, f'{value:.1f}%', va='center')
        
        fig.tight_layout()
        
        # Canvas matplotlib / Matplotlib canvas
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_summary_stats(self):
        """Crée un résumé des statistiques globales / Create a global statistics summary"""
        ttk.Label(
            self.scrollable_frame,
            text="📊 Résumé global",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        stats_frame = ttk.Frame(self.scrollable_frame)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Stats textuelles / Text stats
        stats_text = tk.Text(stats_frame, height=12, wrap=tk.WORD)
        stats_text.pack(fill=tk.BOTH, expand=True)
        
        total_arrivals = sum(self.results['arrivals_cumulative'].values())
        total_outputs = sum(self.results['outputs_cumulative'].values())
        duration = self.results['duration']
        
        # Validation: s'assurer que duration est un nombre / Validation: ensure duration is a number
        if isinstance(duration, dict):
            # Si duration est un dict, essayer de récupérer une valeur numérique / If duration is a dict, try to get a numeric value
            if 'value' in duration:
                duration = duration['value']
            else:
                # Utiliser num_intervals * interval comme fallback / Use num_intervals * interval as fallback
                duration = self.results.get('num_intervals', 0) * self.results.get('interval', 1)
        if not isinstance(duration, (int, float)):
            duration = 0  # Valeur par défaut de sécurité / Default safety value
        
        time_unit = self.results.get('time_unit')
        
        from models.time_converter import TimeConverter
        unit_symbol = TimeConverter.get_unit_symbol(time_unit) if time_unit else "unités"
        
        stats_text.insert("1.0", f"Durée de simulation: {duration} {unit_symbol}\n")
        stats_text.insert("end", f"Intervalle d'analyse: {self.results['interval']} {unit_symbol}\n")
        stats_text.insert("end", f"\nTotal d'arrivées: {total_arrivals}\n")
        stats_text.insert("end", f"Total de sorties: {total_outputs}\n")
        
        # Calculer les taux moyens seulement si duration > 0 / Calculate average rates only if duration > 0
        if duration > 0:
            stats_text.insert("end", f"Taux d'arrivée moyen: {total_arrivals/duration:.2f} items/{unit_symbol}\n")
            stats_text.insert("end", f"Taux de sortie moyen: {total_outputs/duration:.2f} items/{unit_symbol}\n")
        
        if total_arrivals > 0:
            efficiency = (total_outputs / total_arrivals) * 100
            stats_text.insert("end", f"\nEfficacité globale: {efficiency:.1f}%\n")
        
        # Utilisation moyenne / Average utilization
        if 'node_utilization' in self.results:
            utilization_values = list(self.results['node_utilization'].values())
            if utilization_values:
                avg_util = sum(utilization_values) / len(utilization_values)
                stats_text.insert("end", f"Utilisation moyenne des nœuds: {avg_util:.1f}%\n")
        
        stats_text.config(state="disabled")
    
    def _create_item_types_stats(self):
        """Crée les graphiques et statistiques des types d'items / Create graphs and statistics for item types"""
        # Vérifier si le simulateur a des stats de types / Check if simulator has type stats
        if not hasattr(self.main_window, 'simulator') or not hasattr(self.main_window.simulator, 'item_type_stats'):
            return
        
        stats = self.main_window.simulator.item_type_stats
        
        # Titre / Title
        ttk.Label(
            self.scrollable_frame,
            text="🎨 Analyse des Flux par Type d'Item",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Répartition globale des générations / Global generation distribution
        self._create_generation_distribution_graph(stats)
        
        # Timeline des générations / Generation timeline
        self._create_generation_timeline_graph(stats)
        
        # Flux par connexion / Flow by connection
        self._create_connection_flows_graphs(stats)
    
    def _create_generation_distribution_graph(self, stats):
        """Graphique de répartition des types générés / Generated types distribution graph"""
        dist = stats.get_generation_distribution()
        
        if not dist:
            return
        
        frame = ttk.LabelFrame(self.scrollable_frame, text="Répartition des Types Générés", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        fig = Figure(figsize=(10, 4), dpi=80)
        ax = fig.add_subplot(111)
        
        types = list(dist.keys())
        counts = list(dist.values())
        
        # Récupérer les couleurs depuis les types configurés / Get colors from configured types
        colors = self._get_item_type_colors(types)
        
        bars = ax.bar(types, counts, color=colors)
        ax.set_ylabel("Nombre d'items générés")
        ax.set_xlabel("Type d'item")
        ax.set_title("Distribution des types d'items générés")
        ax.grid(axis='y', alpha=0.3)
        
        # Ajouter valeurs sur les barres / Add values on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom')
        
        # Total / Total
        total = sum(counts)
        ax.text(0.98, 0.98, f"Total: {total} items",
               transform=ax.transAxes, ha='right', va='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_generation_timeline_graph(self, stats):
        """Timeline des générations par type / Generation timeline by type"""
        timeline = stats.get_generation_timeline()
        
        if not timeline:
            return
        
        frame = ttk.LabelFrame(self.scrollable_frame, text="Timeline des Générations", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        fig = Figure(figsize=(10, 4), dpi=80)
        ax = fig.add_subplot(111)
        
        # Grouper par type / Group by type
        type_times = {}
        for time, type_id in timeline:
            if type_id not in type_times:
                type_times[type_id] = []
            type_times[type_id].append(time)
        
        # Afficher scatter plot pour chaque type / Display scatter plot for each type
        colors = self._get_item_type_colors(list(type_times.keys()))
        
        for idx, (type_id, times) in enumerate(type_times.items()):
            y_values = [idx] * len(times)
            ax.scatter(times, y_values, c=colors[idx], s=50, alpha=0.6, label=type_id)
        
        ax.set_yticks(range(len(type_times)))
        ax.set_yticklabels(list(type_times.keys()))
        ax.set_xlabel("Temps de simulation")
        ax.set_title("Timeline des générations par type")
        ax.grid(axis='x', alpha=0.3)
        ax.legend(loc='upper right')
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_connection_flows_graphs(self, stats):
        """Graphiques des flux dans les connexions
        
        Connection flow graphs"""
        frame = ttk.LabelFrame(self.scrollable_frame, text="Types d'Items Entrants par N\u0153ud", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Pour chaque nœud, afficher les arrivées par type / For each node, show arrivals by type
        for node in self.flow_model.nodes.values():
            if node.is_source:
                continue
                
            arrivals = stats.get_node_arrivals(node.node_id)
            
            if not arrivals:
                continue
            
            # Compter par type / Count by type
            from collections import Counter
            type_counts = Counter([t for _, t in arrivals])
            
            if not type_counts:
                continue
            
            # Sous-frame pour ce nœud
            node_frame = ttk.Frame(frame)
            node_frame.pack(fill=tk.X, pady=5)
            
            fig = Figure(figsize=(8, 3), dpi=80)
            ax = fig.add_subplot(111)
            
            types = list(type_counts.keys())
            counts = list(type_counts.values())
            colors = self._get_item_type_colors(types)
            
            bars = ax.bar(types, counts, color=colors)
            ax.set_ylabel("Nombre d'items")
            ax.set_title(f"Types d'items reçus par '{node.name}'")
            ax.grid(axis='y', alpha=0.3)
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom')
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, node_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _get_item_type_colors(self, type_ids):
        """Récupère les couleurs configurées pour les types / Get configured colors for types"""
        colors = []
        type_color_map = {}
        
        # Chercher dans les sources / Search in sources
        for node in self.flow_model.nodes.values():
            if node.is_source:
                for item_type in node.item_type_config.item_types:
                    type_color_map[item_type.type_id] = item_type.color
        
        default_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
        
        for i, type_id in enumerate(type_ids):
            if type_id in type_color_map:
                colors.append(type_color_map[type_id])
            else:
                colors.append(default_colors[i % len(default_colors)])
        
        return colors
    
    def _create_time_probe_graphs(self):
        """Crée les graphiques des loupes de temps après l'analyse - sélection individuelle / Create time magnifier graphs after analysis - individual selection"""
        if not hasattr(self.flow_model, 'time_probes') or not self.flow_model.time_probes:
            return
        
        # Compter combien de loupes sont sélectionnées / Count how many magnifiers are selected
        selected_count = sum(1 for probe_id in self.flow_model.time_probes.keys() 
                           if probe_id in self.loupe_selection_vars and self.loupe_selection_vars[probe_id].get())
        
        if selected_count == 0:
            return
        
        # Titre / Title
        ttk.Label(
            self.scrollable_frame,
            text="🔍 Distribution des temps mesurés (Loupes)",
            font=("Arial", 12, "bold")
        ).pack(pady=(20, 10))
        
        # Pour chaque loupe sélectionnée, afficher son histogramme / For each selected magnifier, display its histogram
        for probe_id, time_probe in self.flow_model.time_probes.items():
            # Vérifier si cette loupe est sélectionnée / Check if this magnifier is selected
            if probe_id not in self.loupe_selection_vars or not self.loupe_selection_vars[probe_id].get():
                continue
            measurements = time_probe.get_measurements()
            if len(measurements) == 0:
                continue
            
            stats = time_probe.get_statistics()
            node = self.flow_model.get_node(time_probe.node_id)
            node_name = node.name if node else "Inconnu"
            
            # Frame pour ce graphique / Frame for this graph
            graph_frame = ttk.LabelFrame(
                self.scrollable_frame,
                text=f"{time_probe.name} - {node_name} ({time_probe.probe_type.value})",
                padding="10"
            )
            graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Créer la figure / Create figure
            fig = Figure(figsize=(10, 4), dpi=80)
            ax = fig.add_subplot(111)
            
            # Histogramme / Histogram
            n_bins = min(30, max(10, len(measurements) // 10))
            ax.hist(
                measurements,
                bins=n_bins,
                color=time_probe.color,
                alpha=0.7,
                edgecolor='black'
            )
            
            # Moyenne et écart-type / Mean and standard deviation
            mean = stats['mean']
            ax.axvline(mean, color='red', linestyle='--', linewidth=2, label=f'Moyenne: {mean:.3f}')
            
            if stats['std_dev'] > 0:
                ax.axvline(mean - stats['std_dev'], color='orange', linestyle=':', linewidth=1.5, alpha=0.7, label=f'±1σ')
                ax.axvline(mean + stats['std_dev'], color='orange', linestyle=':', linewidth=1.5, alpha=0.7)
            
            ax.set_xlabel('Temps (unités de simulation)')
            ax.set_ylabel('Fréquence')
            ax.set_title(f"Distribution - {time_probe.name}")
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Statistiques textuelles / Text statistics
            stats_text = (
                f"N = {stats['count']} | "
                f"Moyenne = {stats['mean']:.3f} | "
                f"Écart-type = {stats['std_dev']:.3f} | "
                f"Min = {stats['min']:.3f} | "
                f"Max = {stats['max']:.3f}"
            )
            
            ttk.Label(
                graph_frame,
                text=stats_text,
                font=("Arial", 9),
                foreground="#666"
            ).pack(pady=5)
            
            # Intégrer dans tkinter / Integrate into tkinter
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _show_analysis_graphs(self):
        """Ouvre une fenêtre plein écran pour afficher les graphiques d'analyse / Open full screen window to display analysis graphs"""
        if not self.results:
            messagebox.showwarning(tr('no_data_to_export'), tr('run_analysis_before_graphs'))
            return
        
        # Récupérer les graphiques sélectionnés / Get selected graphs
        selected_graphs = []
        if self.graph_vars['throughput'].get():
            selected_graphs.append('throughput')
        if self.graph_vars['stocks'].get():
            selected_graphs.append('stocks')
        if self.graph_vars['production'].get():
            selected_graphs.append('production')
        if self.graph_vars['wip'].get():
            selected_graphs.append('wip')
        
        if not selected_graphs:
            messagebox.showwarning(tr('no_graph_selected'), tr('select_graph_type'))
            return
        
        # Ouvrir la fenêtre de visualisation / Open visualization window
        from gui.analysis_graph_window import AnalysisGraphWindow
        AnalysisGraphWindow(self, self.results, self.flow_model, selected_graphs, self.time_unit_var)
    
    def _export_analysis_data(self):
        """Exporte les données d'analyse vers des fichiers CSV et TXT / Export analysis data to CSV and TXT files"""
        if not self.results:
            messagebox.showwarning(tr('no_data_to_export'), tr('run_analysis_before_export'))
            return
        
        from tkinter import filedialog
        import csv
        import os
        from datetime import datetime
        import threading
        
        # Demander le dossier de destination / Ask for destination folder
        base_folder = filedialog.askdirectory(title=tr('export_title'))
        if not base_folder:
            return

        # Créer un sous-dossier avec timestamp / Create subfolder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_folder = os.path.join(base_folder, f"{tr('export_folder')}_{timestamp}")
        os.makedirs(export_folder, exist_ok=True)

        base_name = tr('export_folder')

        # Désactiver le bouton d'export pendant le traitement / Disable export button during processing
        self.export_button.config(state='disabled', text=tr('exporting'))
        # Afficher la barre de progression pour l'export / Show progress bar for export
        self.progress_frame.pack(fill=tk.X, pady=5)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="📤 Export en cours...")
        
        def export_thread():
            """Thread d'export pour ne pas bloquer l'interface / Export thread to not block interface"""
            try:
                # Callback pour mettre à jour la progression / Callback to update progress
                def update_progress(percent, message):
                    self.after(0, lambda: self._update_export_progress(percent, message))
                
                # 1. Export CSV - États du système par unité de temps (le plus lourd) / 1. Export CSV - System states per time unit (heaviest)
                update_progress(5, "📤 " + tr('export_progress'))
                self._export_system_states_csv(export_folder, base_name, update_progress)
                
                # 2. Export CSV - Données des loupes de temps / 2. Export CSV - Time magnifier data
                update_progress(90, "📤 " + tr('export_progress'))
                self._export_time_probes_csv(export_folder, base_name)
                
                # 3. Export TXT - Conditions de l'analyse / 3. Export TXT - Analysis conditions
                update_progress(95, "📤 " + tr('export_progress'))
                self._export_analysis_conditions(export_folder, base_name)
                
                update_progress(100, "✅ " + tr('export_complete'))
                
                # Notifier le succès dans le thread principal (thread-safe) / Notify success in main thread (thread-safe)
                self.after(0, lambda: self._on_export_success(export_folder, base_name))
            
            except Exception as e:
                # Notifier l'erreur dans le thread principal (thread-safe) / Notify error in main thread (thread-safe)
                import traceback
                error_msg = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                self.after(0, lambda msg=error_msg: self._on_export_error(msg))
        
        # Lancer l'export dans un thread séparé / Launch export in separate thread
        thread = threading.Thread(target=export_thread, daemon=True)
        thread.start()
    
    def _update_export_progress(self, percent, message):
        """Met à jour la barre de progression de l'export (thread-safe) / Update export progress bar (thread-safe)"""
        self.progress_bar['value'] = percent
        self.progress_label.config(text=message)
    
    def _on_export_success(self, export_folder, base_name):
        """Callback appelé après un export réussi (dans le thread principal) / Callback called after successful export (in main thread)"""
        self.progress_frame.pack_forget()
        self.progress_bar['value'] = 0
        self.export_button.config(state='normal', text=tr('export_data'))
        
        # Construire la liste des fichiers créés / Build list of created files
        files_list = f"- {base_name}_{tr('system_states')}.csv\n"
        
        # Ajouter le fichier des loupes seulement s'il existe des loupes / Add magnifier file only if magnifiers exist
        if hasattr(self.flow_model, 'time_probes') and self.flow_model.time_probes:
            files_list += f"- {base_name}_{tr('time_probes_file')}.csv\n"
        
        files_list += f"- {base_name}_conditions.txt"
        
        messagebox.showinfo(
            tr('export_success'),
            f"{tr('files_created')}:\n{export_folder}\n\n{files_list}"
        )
    
    def _on_export_error(self, error_message):
        """Callback appelé après une erreur d'export (dans le thread principal) / Callback called after export error (in main thread)"""
        self.progress_frame.pack_forget()
        self.progress_bar['value'] = 0
        self.export_button.config(state='normal', text=tr('export_data'))
        messagebox.showerror(tr('export_error_title'), f"{tr('export_error_msg')}: {error_message}")
    
    def _export_system_states_csv(self, folder, base_name, progress_callback=None):
        """Exporte les états du système (pipettes + buffers) par unité de temps en CSV / Export system states (probes + buffers) per time unit in CSV
        
        Optimisations / Optimizations:
        - Générateur de timestamps (évite de stocker tous en mémoire) / Timestamp generator (avoids storing all in memory)
        - Écriture par lots (réduit les appels I/O) / Batch writing (reduces I/O calls)
        - Recherche binaire pour les états machines (bisect) / Binary search for machine states (bisect)
        """
        import csv
        import unicodedata
        import bisect
        
        def remove_accents(text):
            """Retire les accents et caractères spéciaux pour Excel / Remove accents and special characters for Excel"""
            # Normaliser en NFD (décompose les caractères accentués) / Normalize to NFD (decomposes accented characters)
            nfd = unicodedata.normalize('NFD', text)
            # Filtrer les marques diacritiques (accents) / Filter diacritical marks (accents)
            without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
            # Remplacer les caractères spéciaux restants / Replace remaining special characters
            return without_accents.encode('ascii', 'ignore').decode('ascii')
        
        filepath = os.path.join(folder, f"{base_name}_{tr('system_states')}.csv")
        
        duration = self.results['duration']
        
        # Validation: s'assurer que duration est un nombre / Validation: ensure duration is a number
        if isinstance(duration, dict):
            if 'value' in duration:
                duration = duration['value']
            else:
                duration = self.results.get('num_intervals', 0) * self.results.get('interval', 1)
        if not isinstance(duration, (int, float)):
            raise ValueError(f"Duration doit être un nombre, reçu: {type(duration)} = {duration}")
        
        # En-têtes: temps + toutes les pipettes (buffer ET cumulative) + tous les buffers / Headers: time + all probes (buffer AND cumulative) + all buffers
        headers = [tr('csv_time')]
        probe_ids = []
        
        for probe_id, probe in self.flow_model.probes.items():
            # Retirer accents et caractères spéciaux pour Excel / Remove accents and special characters for Excel
            safe_name = remove_accents(probe.name)
            # NOUVEAU: Deux colonnes par pipette (buffer et cumulative) / NEW: Two columns per probe (buffer and cumulative)
            headers.append(f"{tr('csv_probe')}_{safe_name}_{tr('probe_buffer')}")
            headers.append(f"{tr('csv_probe')}_{safe_name}_{tr('probe_cumul')}")
            probe_ids.append(probe_id)
        
        # Ajouter les buffers / Add buffers
        buffer_connections = []
        for conn_id, conn in self.flow_model.connections.items():
            if conn.show_buffer and conn.buffer_capacity > 0:
                # Nom du buffer basé sur les noeuds source et target / Buffer name based on source and target nodes
                source_node = self.flow_model.get_node(conn.source_id)
                target_node = self.flow_model.get_node(conn.target_id)
                # Retirer accents et caractères spéciaux pour Excel / Remove accents and special characters for Excel
                source_name = remove_accents(source_node.name)
                target_name = remove_accents(target_node.name)
                buffer_name = f"{tr('csv_buffer')}_{source_name}_{target_name}"
                headers.append(buffer_name)
                buffer_connections.append(conn_id)
        
        # Ajouter les états des machines (ON/OFF) et opérateurs si disponibles / Add machine states (ON/OFF) and operators if available
        from models.flow_model import NodeType
        machine_states = self.results.get('machine_states', {})
        operator_states = self.results.get('operator_states', {})
        
        machine_nodes = []
        if machine_states:
            for node_id, node in self.flow_model.nodes.items():
                if node.node_type == NodeType.CUSTOM and not node.is_source:
                    safe_name = remove_accents(node.name)
                    headers.append(f"{tr('csv_machine')}_{safe_name}_{tr('machine_state')}")
                    machine_nodes.append((node_id, node))
        
        operator_list = []
        if operator_states:
            for operator_id, operator in self.flow_model.operators.items():
                safe_name = remove_accents(operator.name)
                headers.append(f"{tr('csv_operator')}_{safe_name}_{tr('operator_action')}")
                operator_list.append((operator_id, operator))
        
        # Collecter toutes les mesures et créer des dictionnaires ordonnés (optimisé) / Collect all measurements and create ordered dictionaries (optimized)
        probe_data = self.results.get('probe_data', {})
        buffer_data = self.results.get('buffer_data', {})
        
        # Créer des dictionnaires timestamp -> valeur pour chaque pipette (buffer ET cumulative) et buffer / Create timestamp -> value dictionaries for each probe (buffer AND cumulative) and buffer
        # Utiliser round avec 1 décimale pour réduire le nombre de timestamps / Use round with 1 decimal to reduce number of timestamps
        probe_data_buffer = self.results.get('probe_data_buffer', {})
        probe_data_cumulative = self.results.get('probe_data_cumulative', {})
        
        probe_values_buffer = {}
        probe_values_cumulative = {}
        for probe_id in probe_ids:
            probe_values_buffer[probe_id] = {}
            probe_values_cumulative[probe_id] = {}
            if probe_id in probe_data_buffer:
                for interval_data in probe_data_buffer[probe_id].values():
                    for timestamp, value in interval_data:
                        probe_values_buffer[probe_id][round(timestamp, 1)] = value
            if probe_id in probe_data_cumulative:
                for interval_data in probe_data_cumulative[probe_id].values():
                    for timestamp, value in interval_data:
                        probe_values_cumulative[probe_id][round(timestamp, 1)] = value
        
        buffer_values = {}
        for conn_id in buffer_connections:
            buffer_values[conn_id] = {}
            if conn_id in buffer_data:
                for interval_data in buffer_data[conn_id].values():
                    for timestamp, count in interval_data:
                        buffer_values[conn_id][round(timestamp, 1)] = count
        
        # OPTIMISATION: Générateur de timestamps (évite de stocker tous en mémoire) / OPTIMIZATION: Timestamp generator (avoids storing all in memory)
        def timestamp_generator(max_duration, step=0.1):
            """Génère les timestamps un par un sans les stocker tous en mémoire / Generate timestamps one by one without storing all in memory"""
            t = 0.0
            while t <= max_duration + step:
                yield round(t, 1)
                t += step
        
        # Calculer le nombre total de timestamps pour la progression / Calculate total number of timestamps for progress
        total_timestamps = int((duration + 0.1) / 0.1) + 1
        
        # OPTIMISATION: Pré-traitement pour recherche binaire (bisect) des états machines / OPTIMIZATION: Pre-processing for binary search (bisect) of machine states
        machine_state_times = {}
        machine_state_values = {}
        for node_id in machine_states:
            machine_state_times[node_id] = [t for t, _ in machine_states[node_id]]
            machine_state_values[node_id] = [v for _, v in machine_states[node_id]]
        
        # Pré-traitement pour recherche binaire des états opérateurs / Pre-processing for binary search of operator states
        operator_state_times = {}
        operator_state_actions = {}
        for operator_id in operator_states:
            operator_state_times[operator_id] = [t for t, _ in operator_states[operator_id]]
            operator_state_actions[operator_id] = [data.get('action', tr('op_state_idle')) for _, data in operator_states[operator_id]]
        
        # Écrire le CSV avec encodage UTF-8-sig (BOM) pour Excel / Write CSV with UTF-8-sig encoding (BOM) for Excel
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            # Garder trace de la dernière valeur connue pour remplir les trous (initialisées à 0) / Track last known value to fill gaps (initialized to 0)
            last_probe_values_buffer = {probe_id: 0 for probe_id in probe_ids}
            last_probe_values_cumulative = {probe_id: 0 for probe_id in probe_ids}
            last_buffer_values = {conn_id: 0 for conn_id in buffer_connections}
            
            # Identifier les machines contrôlées par opérateur / Identify machines controlled by operator
            machines_controlled_by_operator = set()
            for operator in self.flow_model.operators.values():
                if hasattr(operator, 'assigned_machines') and operator.assigned_machines:
                    machines_controlled_by_operator.update(operator.assigned_machines)
            
            # OPTIMISATION: Buffer pour écriture par lots / OPTIMIZATION: Buffer for batch writing
            WRITE_BUFFER_SIZE = 10000
            row_buffer = []
            processed_count = 0
            last_progress_update = 0
            
            # Pour chaque unité de temps (via générateur) / For each time unit (via generator)
            for timestamp in timestamp_generator(duration):
                row = [f"{timestamp:.1f}"]
                
                # Pour chaque pipette (les deux colonnes: buffer et cumulative) / For each probe (both columns: buffer and cumulative)
                for probe_id in probe_ids:
                    # Colonne buffer / Buffer column
                    if timestamp in probe_values_buffer[probe_id]:
                        last_probe_values_buffer[probe_id] = probe_values_buffer[probe_id][timestamp]
                    row.append(f"{last_probe_values_buffer[probe_id]:.0f}")
                    
                    # Colonne cumulative / Cumulative column
                    if timestamp in probe_values_cumulative[probe_id]:
                        last_probe_values_cumulative[probe_id] = probe_values_cumulative[probe_id][timestamp]
                    row.append(f"{last_probe_values_cumulative[probe_id]:.0f}")
                
                # Pour chaque buffer / For each buffer
                for conn_id in buffer_connections:
                    if timestamp in buffer_values[conn_id]:
                        # Valeur exacte disponible / Exact value available
                        last_buffer_values[conn_id] = buffer_values[conn_id][timestamp]
                    row.append(str(int(last_buffer_values[conn_id])))
                
                # OPTIMISATION: Recherche binaire pour les états machines / OPTIMIZATION: Binary search for machine states
                if machine_nodes:
                    for node_id, node in machine_nodes:
                        # Par défaut OFF pour les machines contrôlées par opérateur, ON sinon / Default OFF for operator-controlled machines, ON otherwise
                        if node_id in machines_controlled_by_operator:
                            default_state = "OFF"
                        else:
                            default_state = "ON"
                        
                        if node_id in machine_state_times and machine_state_times[node_id]:
                            # Recherche binaire: trouver le dernier état <= timestamp / Binary search: find last state <= timestamp
                            idx = bisect.bisect_right(machine_state_times[node_id], timestamp) - 1
                            state = machine_state_values[node_id][idx] if idx >= 0 else default_state
                        else:
                            state = default_state
                        row.append(state)
                
                # OPTIMISATION: Recherche binaire pour les états opérateurs / OPTIMIZATION: Binary search for operator states
                if operator_list:
                    for operator_id, operator in operator_list:
                        if operator_id in operator_state_times and operator_state_times[operator_id]:
                            # Recherche binaire: trouver la dernière action <= timestamp / Binary search: find last action <= timestamp
                            idx = bisect.bisect_right(operator_state_times[operator_id], timestamp) - 1
                            action = operator_state_actions[operator_id][idx] if idx >= 0 else tr('op_state_idle')
                        else:
                            action = tr('op_state_idle')
                        row.append(action)
                
                # OPTIMISATION: Écriture par lots / OPTIMIZATION: Batch writing
                row_buffer.append(row)
                processed_count += 1
                
                # Écrire le buffer quand il est plein / Write buffer when full
                if len(row_buffer) >= WRITE_BUFFER_SIZE:
                    writer.writerows(row_buffer)
                    row_buffer.clear()
                    
                    # Mettre à jour la progression (5% à 85% pour cette partie) / Update progress (5% to 85% for this part)
                    if progress_callback and total_timestamps > 0:
                        progress = 5 + int((processed_count / total_timestamps) * 80)
                        if progress > last_progress_update + 2:  # Mise à jour tous les 2% / Update every 2%
                            progress_callback(progress, f"📤 Export: {processed_count:,}/{total_timestamps:,} lignes...")
                            last_progress_update = progress
            
            # Écrire les lignes restantes dans le buffer / Write remaining lines in buffer
            if row_buffer:
                writer.writerows(row_buffer)
                row_buffer.clear()
    
    def _export_time_probes_csv(self, folder, base_name):
        """Exporte les données des loupes de temps en CSV avec une colonne par loupe / Export time magnifier data in CSV with one column per magnifier"""
        import csv
        
        if not hasattr(self.flow_model, 'time_probes') or not self.flow_model.time_probes:
            return
        
        filepath = os.path.join(folder, f"{base_name}_{tr('time_probes_file')}.csv")
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # PARTIE 1: Statistiques résumées / PART 1: Summary statistics
            writer.writerow([f'=== {tr("time_probes").upper()} ==='])
            writer.writerow([tr('time_probes'), tr('csv_node'), 'Type', tr('count'), tr('average'), tr('std_dev'), tr('min'), tr('max')])
            
            # Pour chaque loupe de temps / For each time magnifier
            for time_probe in self.flow_model.time_probes.values():
                measurements = time_probe.get_measurements()
                if len(measurements) == 0:
                    continue
                
                stats = time_probe.get_statistics()
                node = self.flow_model.get_node(time_probe.node_id)
                node_name = node.name if node else tr('csv_unknown')
                
                writer.writerow([
                    time_probe.name,
                    node_name,
                    time_probe.probe_type.value,
                    stats['count'],
                    f"{stats['mean']:.3f}",
                    f"{stats['std_dev']:.3f}",
                    f"{stats['min']:.3f}",
                    f"{stats['max']:.3f}"
                ])
            
            writer.writerow([])
            
            # PARTIE 1b: Statistiques loupes de déplacement opérateurs / PART 1b: Operator movement magnifier statistics
            writer.writerow([tr('csv_operator_movements_stats')])
            writer.writerow([tr('csv_operator'), tr('csv_route'), tr('csv_measurement_count'), tr('csv_average'), tr('csv_std_dev'), tr('csv_min'), tr('csv_max')])
            
            # Utiliser les données sauvegardées dans results au lieu de flow_model directement
            # Use saved data from results instead of flow_model directly
            operator_travel_data = self.results.get('operator_travel_data', {})
            
            # Pour chaque opérateur / For each operator
            for operator_id, routes_data in operator_travel_data.items():
                operator = self.flow_model.operators.get(operator_id)
                if not operator:
                    continue
                    
                for route_key, measurements in routes_data.items():
                    if measurements and len(measurements) > 0:
                        from_id, to_id = route_key
                        from_node = self.flow_model.get_node(from_id)
                        to_node = self.flow_model.get_node(to_id)
                        route = f"{from_node.name}→{to_node.name}" if from_node and to_node else f"{from_id}→{to_id}"
                        
                        # Calculer statistiques / Calculate statistics
                        import numpy as np
                        mean_val = np.mean(measurements)
                        std_val = np.std(measurements)
                        min_val = np.min(measurements)
                        max_val = np.max(measurements)
                        
                        writer.writerow([
                            operator.name,
                            route,
                            len(measurements),
                            f"{mean_val:.3f}",
                            f"{std_val:.3f}",
                            f"{min_val:.3f}",
                            f"{max_val:.3f}"
                        ])
            
            writer.writerow([])
            writer.writerow([])
            
            # PARTIE 2: Mesures détaillées avec une colonne par loupe / PART 2: Detailed measurements with one column per magnifier
            writer.writerow([tr('csv_detailed_measurements')])
            
            # Préparer les en-têtes: Mesure_# + une colonne par loupe / Prepare headers: Measurement_# + one column per magnifier
            headers = [tr('csv_measurement_num')]
            time_probes_list = []
            
            for time_probe in self.flow_model.time_probes.values():
                measurements = time_probe.get_measurements()
                if len(measurements) > 0:
                    headers.append(f"{tr('csv_value')}_{time_probe.name}")
                    time_probes_list.append(time_probe)
            
            writer.writerow(headers)
            
            # Trouver le nombre maximum de mesures / Find maximum number of measurements
            max_measurements = 0
            for time_probe in time_probes_list:
                measurements = time_probe.get_measurements()
                max_measurements = max(max_measurements, len(measurements))
            
            # Écrire les données ligne par ligne / Write data line by line
            for i in range(max_measurements):
                row = [i + 1]  # Numéro de mesure / Measurement number
                
                for time_probe in time_probes_list:
                    measurements = time_probe.get_measurements()
                    if i < len(measurements):
                        row.append(f"{measurements[i]:.3f}")
                    else:
                        row.append("")  # Cellule vide si cette loupe n'a pas autant de mesures / Empty cell if this magnifier doesn't have that many measurements
                
                writer.writerow(row)
            
            writer.writerow([])
            writer.writerow([])
            
            # PARTIE 3: Mesures détaillées des déplacements opérateurs / PART 3: Detailed operator movement measurements
            writer.writerow([tr('csv_detailed_operator_movements')])
            
            # Utiliser les données sauvegardées dans results / Use saved data from results
            operator_travel_data = self.results.get('operator_travel_data', {})
            
            # Pour chaque opérateur avec des données de déplacement / For each operator with travel data
            for operator_id, routes_data in operator_travel_data.items():
                operator = self.flow_model.operators.get(operator_id)
                if not operator or not routes_data:
                    continue
                    
                writer.writerow([])
                writer.writerow([f"{tr('csv_operator')}: {operator.name}"])
                
                # En-têtes: Mesure_# + une colonne par trajet / Headers: Measurement_# + one column per route
                headers = [tr('csv_measurement_num')]
                routes_list = []
                
                for route_key, measurements in routes_data.items():
                    if measurements and len(measurements) > 0:
                        from_id, to_id = route_key
                        from_node = self.flow_model.get_node(from_id)
                        to_node = self.flow_model.get_node(to_id)
                        route = f"{from_node.name}→{to_node.name}" if from_node and to_node else f"{from_id}→{to_id}"
                        headers.append(route)
                        routes_list.append(measurements)
                
                if not routes_list:
                    continue  # Aucune mesure pour cet opérateur / No measurements for this operator
                
                writer.writerow(headers)
                
                # Trouver le nombre maximum de mesures / Find maximum number of measurements
                max_travel_measurements = 0
                for measurements in routes_list:
                    max_travel_measurements = max(max_travel_measurements, len(measurements))
                
                # Écrire les données / Write data
                for i in range(max_travel_measurements):
                    row = [i + 1]
                    for measurements in routes_list:
                        if i < len(measurements):
                            row.append(f"{measurements[i]:.3f}")
                        else:
                            row.append("")
                    writer.writerow(row)
    
    def _export_analysis_conditions(self, folder, base_name):
        """Exporte les conditions de l'analyse dans un fichier texte / Export analysis conditions to text file"""
        filepath = os.path.join(folder, f"{base_name}_conditions.txt")
        
        from datetime import datetime
        from models.time_converter import TimeConverter
        
        if False:
            print(f"[EXPORT_DEBUG] Début export analyse_conditions.txt")
        if False:
            print(f"[EXPORT_DEBUG] results.keys() = {list(self.results.keys())}")
        if False:
            print(f"[EXPORT_DEBUG] duration type = {type(self.results.get('duration'))}, value = {self.results.get('duration')}")
        if False:
            print(f"[EXPORT_DEBUG] interval type = {type(self.results.get('interval'))}, value = {self.results.get('interval')}")
        if False:
            print(f"[EXPORT_DEBUG] num_intervals type = {type(self.results.get('num_intervals'))}, value = {self.results.get('num_intervals')}")
        
        time_unit = self.results.get('time_unit')
        unit_symbol = TimeConverter.get_unit_symbol(time_unit) if time_unit else tr('units')
        
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write("="*60 + "\n")
            f.write(tr('report_title') + "\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"{tr('analysis_date')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(tr('analysis_params') + "\n")
            f.write("-"*60 + "\n")
            f.write(f"{tr('simulation_duration')}: {self.results['duration']} {unit_symbol}\n")
            f.write(f"{tr('analysis_interval')}: {self.results['interval']} {unit_symbol}\n")
            # Protection contre num_intervals qui pourrait être un dict / Protection against num_intervals that could be a dict
            num_int = self.results.get('num_intervals', 0)
            if isinstance(num_int, dict):
                num_int = 0
            f.write(f"{tr('num_intervals')}: {num_int}\n")
            f.write(f"{tr('time_unit_label')}: {unit_symbol}\n\n")
            
            f.write(tr('system_config') + "\n")
            f.write("-"*60 + "\n")
            f.write(f"{tr('num_nodes')}: {len(self.flow_model.nodes)}\n")
            f.write(f"{tr('num_connections')}: {len(self.flow_model.connections)}\n")
            f.write(f"{tr('num_probes')}: {len(self.flow_model.probes)}\n")
            if hasattr(self.flow_model, 'time_probes'):
                f.write(f"{tr('num_time_probes')}: {len(self.flow_model.time_probes)}\n")
            f.write("\n")
            
            f.write(tr('node_details') + "\n")
            f.write("-"*60 + "\n")
            for node_id, node in self.flow_model.nodes.items():
                f.write(f"\n{tr('node_label')}: {node.name} ({node.node_type.value})\n")
                f.write(f"  {tr('id_label')}: {node_id}\n")
                f.write(f"  {tr('position_label')}: (x={node.x:.1f}, y={node.y:.1f})\n")
                
                if node.is_source:
                    interval_val = node.get_generation_interval(self.flow_model.current_time_unit)
                    f.write(f"  {tr('generation_interval')}: {interval_val:.2f} {unit_symbol}\n")
                    f.write(f"  {tr('mode_label')}: {node.source_mode.value}\n")
                    if hasattr(node, 'generation_std_dev') and node.generation_std_dev > 0:
                        std_dev = node.generation_std_dev / 100.0
                        f.write(f"  {tr('std_dev_export')}: {std_dev:.2f} {unit_symbol}\n")
                    f.write(f"  {tr('items_to_generate')}: {node.max_items_to_generate if node.max_items_to_generate > 0 else tr('unlimited')}\n")
                    f.write(f"  {tr('batch_size')}: {node.batch_size}\n")
                elif node.is_sink:
                    f.write(f"  {tr('type_label')}: {tr('output_node')}\n")
                elif node.is_splitter:
                    f.write(f"  {tr('type_label')}: {tr('splitter_type')}\n")
                    f.write(f"  {tr('mode_label')}: {node.splitter_mode.value}\n")
                elif node.is_merger:
                    f.write(f"  {tr('type_label')}: {tr('merger_type')}\n")
                    if hasattr(node, 'sync_mode'):
                        f.write(f"  {tr('sync_mode_label')}: {node.sync_mode.value}\n")
                else:
                    time_val = node.get_processing_time(self.flow_model.current_time_unit)
                    f.write(f"  {tr('processing_time_label')}: {time_val:.2f} {unit_symbol}\n")
                    f.write(f"  {tr('mode_label')}: {node.processing_time_mode.value}\n")
                    if hasattr(node, 'processing_time_std_dev_cs') and node.processing_time_std_dev_cs > 0:
                        from models.time_converter import TimeConverter
                        std_dev = TimeConverter.from_centiseconds(node.processing_time_std_dev_cs, self.flow_model.current_time_unit)
                        f.write(f"  {tr('std_dev_export')}: {std_dev:.2f} {unit_symbol}\n")
                    if hasattr(node, 'output_multiplier') and node.output_multiplier != 1:
                        f.write(f"  {tr('output_multiplier')}: {node.output_multiplier}\n")
                
                # Connexions entrantes / Incoming connections
                if node.input_connections:
                    f.write(f"  {tr('incoming_connections')}: {len(node.input_connections)}\n")
                    for conn_id in node.input_connections:
                        conn = self.flow_model.get_connection(conn_id)
                        if conn:
                            source = self.flow_model.get_node(conn.source_id)
                            f.write(f"    ← {source.name if source else tr('csv_unknown')}")
                            if conn.buffer_capacity != float('inf'):
                                f.write(f" [Buffer: {int(conn.buffer_capacity)}]")
                            f.write("\n")
                
                # Connexions sortantes / Outgoing connections
                if node.output_connections:
                    f.write(f"  {tr('outgoing_connections')}: {len(node.output_connections)}\n")
                    for conn_id in node.output_connections:
                        conn = self.flow_model.get_connection(conn_id)
                        if conn:
                            target = self.flow_model.get_node(conn.target_id)
                            f.write(f"    → {target.name if target else tr('csv_unknown')}")
                            if conn.buffer_capacity != float('inf'):
                                f.write(f" [Buffer: {int(conn.buffer_capacity)}]")
                            f.write("\n")
                
                # Utilisation / Utilization
                if 'node_utilization' in self.results and node_id in self.results['node_utilization']:
                    util = self.results['node_utilization'][node_id]
                    f.write(f"  {tr('utilization_rate')}: {util:.1f}%\n")
            
            # Détail des connexions / Connection details
            f.write("\n" + "="*60 + "\n")
            f.write(tr('connection_details') + "\n")
            f.write("-"*60 + "\n")
            for conn_id, conn in self.flow_model.connections.items():
                source = self.flow_model.get_node(conn.source_id)
                target = self.flow_model.get_node(conn.target_id)
                
                source_name = (source.name if source else tr('csv_unknown')).encode('ascii', 'replace').decode('ascii')
                target_name = (target.name if target else tr('csv_unknown')).encode('ascii', 'replace').decode('ascii')
                f.write(f"\n{tr('connection_label')}: {source_name} -> {target_name}\n")
                f.write(f"  {tr('id_label')}: {conn_id}\n")
                
                if conn.buffer_capacity != float('inf'):
                    f.write(f"  {tr('buffer_capacity')}: {int(conn.buffer_capacity)} {tr('units')}\n")
                else:
                    f.write(f"  {tr('buffer_capacity')}: {tr('unlimited_capacity')}\n")
                
                if hasattr(conn, 'initial_buffer_count') and conn.initial_buffer_count > 0:
                    f.write(f"  {tr('initial_content')}: {conn.initial_buffer_count} {tr('units')}\n")
                
                # Pipettes sur cette connexion / Probes on this connection
                probes_on_conn = [p for p in self.flow_model.probes.values() if p.connection_id == conn_id]
                if probes_on_conn:
                    f.write(f"  {tr('probes_on_conn')}: {', '.join([p.name for p in probes_on_conn])}\n")
            
            # Pipettes de mesure / Measurement probes
            if self.flow_model.probes:
                f.write("\n" + "="*60 + "\n")
                f.write(tr('measurement_probes_section') + "\n")
                f.write("-"*60 + "\n")
                for probe_id, probe in self.flow_model.probes.items():
                    conn = self.flow_model.get_connection(probe.connection_id)
                    if conn:
                        source = self.flow_model.get_node(conn.source_id)
                        target = self.flow_model.get_node(conn.target_id)
                        probe_name = probe.name.encode('ascii', 'replace').decode('ascii')
                        source_name = (source.name if source else '?').encode('ascii', 'replace').decode('ascii')
                        target_name = (target.name if target else '?').encode('ascii', 'replace').decode('ascii')
                        f.write(f"\n{tr('probe_label')}: {probe_name}\n")
                        f.write(f"  {tr('on_connection')}: {source_name} -> {target_name}\n")
                        f.write(f"  {tr('mode_label')}: {probe.measure_mode}\n")
                        f.write(f"  {tr('color_label')}: {probe.color}\n")
            
            # Loupes de temps / Time magnifiers
            if hasattr(self.flow_model, 'time_probes') and self.flow_model.time_probes:
                f.write("\n" + "="*60 + "\n")
                f.write(tr('time_probes_section') + "\n")
                f.write("-"*60 + "\n")
                for probe_id, probe in self.flow_model.time_probes.items():
                    node = self.flow_model.get_node(probe.node_id)
                    f.write(f"\n{tr('time_probe_label')}: {probe.name}\n")
                    f.write(f"  {tr('on_node')}: {node.name if node else tr('csv_unknown')}\n")
                    f.write(f"  {tr('type_label')}: {probe.probe_type.value}\n")
                    f.write(f"  {tr('color_label')}: {probe.color}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write(tr('end_of_report') + "\n")
            f.write("="*60 + "\n")
