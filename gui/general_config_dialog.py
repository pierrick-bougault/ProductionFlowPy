"""Dialogue de configuration générale / General configuration dialog"""
import tkinter as tk
from tkinter import ttk
from gui.translations import tr, get_language, get_available_languages

class GeneralConfigDialog:
    """Dialogue pour configurer les paramètres généraux de l'application / Dialog to configure application general parameters"""
    
    def __init__(self, parent, current_timeout=600, performance_params=None):
        self.result = None
        
        # Paramètres de performance actuels (ou valeurs par défaut depuis config.py) / Current performance parameters (or defaults from config.py)
        if performance_params is None:
            performance_params = {}
        
        # Créer la fenêtre de dialogue / Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(tr('general_params'))
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenêtre avec une taille plus grande / Center window with larger size
        dialog_width = 750
        dialog_height = 700
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Titre principal / Main title
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(title_frame, text="⚙️ " + tr('general_params'), font=("Arial", 14, "bold")).pack()
        
        # Boutons OK/Annuler (packagés en BOTTOM avant le canvas pour rester fixes) / OK/Cancel buttons (packed at BOTTOM before canvas to stay fixed)
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=15)
        
        ttk.Button(button_frame, text=tr('apply'), command=self._on_ok, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text=tr('cancel_btn'), command=self._on_cancel, width=15).pack(side=tk.RIGHT, padx=5)
        
        # Frame scrollable pour le contenu / Scrollable frame for content
        canvas = tk.Canvas(self.dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=680)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=(0, 10))
        scrollbar.pack(side="right", fill="y", padx=(0, 0), pady=(0, 10))
        
        # Bind la molette de la souris au scroll / Bind mouse wheel to scroll
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Canvas détruit, ignorer l'événement / Canvas destroyed, ignore event
                pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # ========== SECTION 1: Langue (en premier) / Language (first) ==========
        lang_section = ttk.LabelFrame(scrollable_frame, text=tr('language_section'), padding=15)
        lang_section.pack(fill=tk.X, padx=10, pady=10)
        
        self._create_language_row(
            lang_section,
            current_language=performance_params.get('language', 'fr')
        )
        
        # ========== SECTION 2: Analyse - Pipettes / Analysis - Probes ==========
        analysis_section = ttk.LabelFrame(scrollable_frame, text=tr('analysis_pipettes_section'), padding=15)
        analysis_section.pack(fill=tk.X, padx=10, pady=10)
        
        self._create_param_row(
            analysis_section,
            label=tr('measurement_limit_label'),
            var_type="int",
            var_name="probe_analysis_max_points_var",
            default_value=performance_params.get('probe_analysis_max_points', 500000),
            from_=50000,
            to=2000000,
            increment=50000,
            description=tr('measurement_limit_desc_full')
        )
        
        # ========== SECTION 3: Simulation ==========
        sim_section = ttk.LabelFrame(scrollable_frame, text=tr('simulation_section_icon'), padding=15)
        sim_section.pack(fill=tk.X, padx=10, pady=10)
        
        # Timeout d'analyse / Analysis timeout
        self._create_param_row(
            sim_section,
            label=tr('analysis_timeout_label'),
            var_type="int",
            var_name="timeout_var",
            default_value=current_timeout,
            from_=60,
            to=7200,
            increment=60,
            description=tr('timeout_desc_full')
        )
        
        # ========== SECTION 4: Mode Debug / Debug Mode ==========
        debug_section = ttk.LabelFrame(scrollable_frame, text=tr('debug_section'), padding=15)
        debug_section.pack(fill=tk.X, padx=10, pady=10)
        
        self._create_param_row(
            debug_section,
            label=tr('debug_mode_label'),
            var_type="bool",
            var_name="debug_mode_var",
            default_value=performance_params.get('debug_mode', False),
            description=tr('debug_mode_desc_full')
        )
        
        # ========== SECTION 5: Performance des Opérateurs / Operator Performance ==========
        operator_section = ttk.LabelFrame(scrollable_frame, text=tr('operator_perf_section'), padding=15)
        operator_section.pack(fill=tk.X, padx=10, pady=10)
        
        self._create_param_row(
            operator_section,
            label=tr('movement_threshold_label'),
            var_type="double",
            var_name="movement_threshold_var",
            default_value=performance_params.get('movement_threshold', 2.0),
            from_=0.5,
            to=10.0,
            increment=0.5,
            description=tr('movement_threshold_desc')
        )
        
        self._create_param_row(
            operator_section,
            label=tr('measurements_limit_label'),
            var_type="int",
            var_name="probe_max_measurements_var",
            default_value=performance_params.get('probe_max_measurements', 1000),
            from_=100,
            to=10000,
            increment=100,
            description=tr('measurements_limit_desc')
        )
        
        # ========== SECTION 6: Cache et UI / Cache and UI ==========
        cache_section = ttk.LabelFrame(scrollable_frame, text=tr('cache_ui_section'), padding=15)
        cache_section.pack(fill=tk.X, padx=10, pady=10)
        
        self._create_param_row(
            cache_section,
            label=tr('cache_validity_label'),
            var_type="int",
            var_name="cache_validity_var",
            default_value=performance_params.get('cache_validity', 50),
            from_=10,
            to=500,
            increment=10,
            description=tr('cache_validity_desc')
        )
        
        self._create_param_row(
            cache_section,
            label=tr('ui_update_interval_label'),
            var_type="double",
            var_name="ui_update_interval_var",
            default_value=performance_params.get('ui_update_interval', 0.2),
            from_=0.1,
            to=2.0,
            increment=0.1,
            description=tr('ui_update_interval_desc')
        )
        
        # ========== SECTION 7: Animations ==========
        anim_section = ttk.LabelFrame(scrollable_frame, text=tr('animations_section'), padding=15)
        anim_section.pack(fill=tk.X, padx=10, pady=10)
        
        self._create_param_row(
            anim_section,
            label=tr('animations_enabled_label'),
            var_type="bool",
            var_name="enable_animations_var",
            default_value=performance_params.get('enable_animations', True),
            description=tr('animations_enabled_desc')
        )
        
        self._create_param_row(
            anim_section,
            label=tr('animation_steps_label'),
            var_type="int",
            var_name="animation_steps_var",
            default_value=performance_params.get('animation_steps', 7),
            from_=1,
            to=20,
            increment=1,
            description=tr('animation_steps_desc')
        )
        
        # Bind touches / Bind keys
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # Cleanup du binding mousewheel à la fermeture / Cleanup mousewheel binding on close
        def _on_close():
            canvas.unbind_all("<MouseWheel>")
            self.dialog.destroy()
        
        self.dialog.protocol("WM_DELETE_WINDOW", _on_close)
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.dialog.focus_force()
        
        # Attendre la fermeture du dialogue / Wait for dialog close
        self.dialog.wait_window()
    
    def _create_param_row(self, parent, label, var_type, var_name, default_value, 
                         from_=None, to=None, increment=None, description=None):
        """Crée une ligne de paramètre avec label, widget et description / Create a parameter row with label, widget and description"""
        container = ttk.Frame(parent)
        container.pack(fill=tk.X, pady=8, padx=5)
        
        # Label / Libellé
        label_frame = ttk.Frame(container)
        label_frame.pack(fill=tk.X)
        ttk.Label(label_frame, text=label, font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # Widget selon le type / Widget by type
        widget_frame = ttk.Frame(container)
        widget_frame.pack(fill=tk.X, pady=5)
        
        if var_type == "bool":
            var = tk.BooleanVar(value=default_value)
            widget = ttk.Checkbutton(widget_frame, text=tr('enabled'), variable=var)
            widget.pack(anchor=tk.W)
        elif var_type == "int":
            var = tk.IntVar(value=default_value)
            widget = ttk.Spinbox(
                widget_frame,
                from_=from_,
                to=to,
                increment=increment,
                textvariable=var,
                width=20
            )
            widget.pack(anchor=tk.W)
        elif var_type == "double":
            var = tk.DoubleVar(value=default_value)
            widget = ttk.Spinbox(
                widget_frame,
                from_=from_,
                to=to,
                increment=increment,
                textvariable=var,
                width=20,
                format="%.1f"
            )
            widget.pack(anchor=tk.W)
        
        # Stocker la variable / Store variable
        setattr(self, var_name, var)
        
        # Description
        if description:
            desc_frame = ttk.Frame(container)
            desc_frame.pack(fill=tk.X, pady=(0, 5))
            
            desc_label = ttk.Label(
                desc_frame,
                text=description,
                foreground="gray30",
                font=("Arial", 9),
                justify=tk.LEFT,
                wraplength=600  # Largeur sûre pour l'espace disponible / Safe width for available space
            )
            desc_label.pack(fill=tk.X, anchor=tk.W)
    
    def _create_language_row(self, parent, current_language):
        """Crée une ligne pour le choix de la langue / Create a row for language selection"""
        container = ttk.Frame(parent)
        container.pack(fill=tk.X, pady=8, padx=5)
        
        # Label / Libellé
        label_frame = ttk.Frame(container)
        label_frame.pack(fill=tk.X)
        ttk.Label(label_frame, text=tr('language'), font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # Widget combobox pour la langue / Combobox widget for language
        widget_frame = ttk.Frame(container)
        widget_frame.pack(fill=tk.X, pady=5)
        
        self.language_var = tk.StringVar(value=current_language)
        
        languages = get_available_languages()
        language_names = list(languages.values())
        language_codes = list(languages.keys())
        
        # Trouver l'index de la langue courante / Find current language index
        current_index = language_codes.index(current_language) if current_language in language_codes else 0
        
        self.language_combo = ttk.Combobox(
            widget_frame,
            values=language_names,
            state='readonly',
            width=20
        )
        self.language_combo.current(current_index)
        self.language_combo.pack(anchor=tk.W)
        
        # Stocker le mapping pour la conversion / Store mapping for conversion
        self.language_code_map = dict(zip(language_names, language_codes))
        
        # Description
        desc_frame = ttk.Frame(container)
        desc_frame.pack(fill=tk.X, pady=(0, 5))
        
        desc_label = ttk.Label(
            desc_frame,
            text=tr('language_desc'),
            foreground="gray30",
            font=("Arial", 9),
            justify=tk.LEFT,
            wraplength=600
        )
        desc_label.pack(fill=tk.X, anchor=tk.W)
    
    def _on_ok(self):
        """Valide et ferme le dialogue / Validate and close dialog"""
        # Récupérer le code de langue à partir du nom affiché / Get language code from displayed name
        selected_lang_name = self.language_combo.get()
        selected_lang_code = self.language_code_map.get(selected_lang_name, 'fr')
        
        self.result = {
            'timeout': self.timeout_var.get(),
            'debug_mode': self.debug_mode_var.get(),
            'movement_threshold': self.movement_threshold_var.get(),
            'probe_max_measurements': self.probe_max_measurements_var.get(),
            'probe_analysis_max_points': self.probe_analysis_max_points_var.get(),
            'cache_validity': self.cache_validity_var.get(),
            'ui_update_interval': self.ui_update_interval_var.get(),
            'enable_animations': self.enable_animations_var.get(),
            'animation_steps': self.animation_steps_var.get(),
            'language': selected_lang_code
        }
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Annule et ferme le dialogue / Cancel and close dialog"""
        self.dialog.destroy()
