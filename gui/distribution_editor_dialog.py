"""Éditeur graphique interactif pour les distributions de probabilité
Interactive graphical editor for probability distributions"""
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy import stats
from gui.translations import tr

class DistributionEditorDialog(tk.Toplevel):
    """Dialogue pour éditer graphiquement une distribution de probabilité
    Dialog to graphically edit a probability distribution"""
    
    def __init__(self, parent, initial_mean=10.0, initial_std=2.0, initial_skewness=0.0, 
                 distribution_type='NORMAL', callback=None):
        super().__init__(parent)
        
        self.title(tr('distribution_editor_title'))
        
        # Utiliser une taille fixe raisonnable au lieu de proportionnelle à l'écran
        # Use a reasonable fixed size instead of proportional to screen
        dialog_width = 900
        dialog_height = 650  # Hauteur augmentée pour les boutons en skew_normal / Increased height for skew_normal buttons
        self.dialog_height = dialog_height  # Stocker comme variable d'instance / Store as instance variable
        
        self.geometry(f"{dialog_width}x{dialog_height}")
        self.resizable(True, True)
        
        # Centrer la fenêtre / Center window
        from gui.dialog_utils import center_window
        self.update_idletasks()
        center_window(self)
        
        # Paramètres de distribution / Distribution parameters
        self.mean = initial_mean  # ξ (xi) - paramètre de position / position parameter
        self.std = initial_std    # ω (omega) - paramètre d'échelle / scale parameter
        self.alpha = initial_skewness  # α (alpha) - paramètre d'asymétrie / skewness parameter
        self.distribution_type = distribution_type  # 'CONSTANT', 'NORMAL' ou 'SKEW_NORMAL'
        self.callback = callback
        
        # Points de contrôle (positions x sur la courbe) / Control points (x positions on curve)
        self.control_points = {
            'mean': self.mean,           # Point central / Central point
            'plus_1sigma': self.mean + self.std,   # +1σ
            'minus_1sigma': self.mean - self.std,  # -1σ
        }
        
        # État du drag / Drag state
        self.dragging_point = None
        self.drag_offset = 0
        
        self._create_widgets()
        self._setup_plot()
        self._update_plot()
        
        # Bind touche Entrée au bouton Appliquer et Échap au bouton Annuler
        # Bind Enter key to Apply button and Escape to Cancel button
        self.bind('<Return>', lambda e: self._apply())
        self.bind('<Escape>', lambda e: self._cancel())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.focus_force()
        
        # Centrer la fenêtre / Center window
        self.transient(parent)
        self.grab_set()
    
    def _create_widgets(self):
        """Crée les widgets de l'interface / Create interface widgets"""
        # Frame principale / Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame du graphique avec hauteur fixe / Graph frame with fixed height
        self.graph_frame = ttk.Frame(main_frame, height=350)
        self.graph_frame.pack(fill=tk.BOTH, expand=False)
        self.graph_frame.pack_propagate(False)
        
        # Figure matplotlib avec taille dynamique / Matplotlib figure with dynamic size
        self._update_figure_size()
        
        # Lier le redimensionnement de la fenêtre / Bind window resize
        self.bind("<Configure>", self._on_window_resize)
        
        # Frame des paramètres avec sliders / Parameters frame with sliders
        params_frame = ttk.LabelFrame(main_frame, text=tr('parameters'), padding="10")
        params_frame.pack(fill=tk.X, pady=10)
        
        # Slider pour la moyenne (ξ - paramètre de position)
        # Slider for mean (ξ - position parameter)
        mean_slider_frame = ttk.Frame(params_frame)
        mean_slider_frame.pack(fill=tk.X, pady=5)
        self.mean_label = ttk.Label(mean_slider_frame, text=f"{tr('position_param')}: {self.mean:.2f}", width=20)
        self.mean_label.pack(side=tk.LEFT)
        
        # Bouton pour configurer la plage / Button to configure range
        ttk.Button(
            mean_slider_frame,
            text="⚙️",
            width=3,
            command=lambda: self._configure_slider_range('mean')
        ).pack(side=tk.LEFT, padx=2)
        
        self.mean_slider = tk.Scale(
            mean_slider_frame, from_=0.1, to=50.0, resolution=0.1,
            orient=tk.HORIZONTAL, command=self._on_mean_slider_change,
            showvalue=0
        )
        self.mean_slider.set(self.mean)
        self.mean_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Stocker les plages par défaut / Store default ranges
        self.slider_ranges = {
            'mean': {'min': 0.1, 'max': 50.0},
            'std': {'min': 0.01, 'max': 10.0},
            'alpha': {'min': -10.0, 'max': 10.0}
        }
        
        # Slider pour l'écart-type (ω - paramètre d'échelle)
        # Slider for standard deviation (ω - scale parameter)
        # Masqué pour le mode CONSTANT / Hidden for CONSTANT mode
        if self.distribution_type != 'CONSTANT':
            std_slider_frame = ttk.Frame(params_frame)
            std_slider_frame.pack(fill=tk.X, pady=5)
            self.std_label = ttk.Label(std_slider_frame, text=f"{tr('scale_param')}: {self.std:.2f}", width=20)
            self.std_label.pack(side=tk.LEFT)
            
            # Bouton pour configurer la plage / Button to configure range
            ttk.Button(
                std_slider_frame,
                text="⚙️",
                width=3,
                command=lambda: self._configure_slider_range('std')
            ).pack(side=tk.LEFT, padx=2)
            
            self.std_slider = tk.Scale(
                std_slider_frame, from_=0.01, to=10.0, resolution=0.01,
                orient=tk.HORIZONTAL, command=self._on_std_slider_change,
                showvalue=0
            )
            self.std_slider.set(self.std)
            self.std_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            # Mode CONSTANT : pas de variabilité / CONSTANT mode: no variability
            ttk.Label(
                params_frame,
                text=tr('constant_mode_info'),
                font=("Arial", 9, "italic"),
                foreground="#2196F3"
            ).pack(pady=5)
        
        # Slider pour l'asymétrie α (uniquement pour SKEW_NORMAL)
        # Slider for skewness α (only for SKEW_NORMAL)
        if self.distribution_type == 'SKEW_NORMAL':
            alpha_slider_frame = ttk.Frame(params_frame)
            alpha_slider_frame.pack(fill=tk.X, pady=5)
            self.alpha_label = ttk.Label(alpha_slider_frame, text=f"{tr('skewness_param')}: {self.alpha:.2f}", width=20)
            self.alpha_label.pack(side=tk.LEFT)
            
            # Bouton pour configurer la plage / Button to configure range
            ttk.Button(
                alpha_slider_frame,
                text="⚙️",
                width=3,
                command=lambda: self._configure_slider_range('alpha')
            ).pack(side=tk.LEFT, padx=2)
            
            self.alpha_slider = tk.Scale(
                alpha_slider_frame, from_=-10.0, to=10.0, resolution=0.1,
                orient=tk.HORIZONTAL, command=self._on_alpha_slider_change,
                showvalue=0
            )
            self.alpha_slider.set(self.alpha)
            self.alpha_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Explication / Explanation
            ttk.Label(
                params_frame,
                text=tr('skew_explanation'),
                font=("Arial", 8, "italic"),
                foreground="#666"
            ).pack(pady=2)
        
        # Instructions / Instructions
        if self.distribution_type == 'CONSTANT':
            instructions_text = tr('constant_mode_instruction')
        else:
            instructions_text = tr('slider_instruction')
        
        instructions = ttk.Label(
            params_frame,
            text=instructions_text,
            font=("Arial", 9, "italic"),
            foreground="#666"
        )
        instructions.pack(pady=5)
        
        # Frame des boutons / Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text=tr('validate_btn'),
            command=self._on_validate
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text=tr('cancel_btn_symbol'),
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=5)
        
        # Bouton reset / Reset button
        ttk.Button(
            button_frame,
            text=tr('reset_btn'),
            command=self._on_reset
        ).pack(side=tk.LEFT, padx=5)
    
    def _setup_plot(self):
        """Configure le graphique matplotlib avec les événements de souris / Configure matplotlib plot with mouse events"""
        # Connecter les événements de souris / Connect mouse events
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
    
    def _configure_slider_range(self, slider_name):
        """Ouvre un dialogue pour configurer la plage d'un slider / Open dialog to configure slider range"""
        # Créer une fenêtre popup / Create popup window
        config_window = tk.Toplevel(self)
        config_window.title(f"{tr('configure_range')} - {slider_name}")
        config_window.geometry("350x200")
        config_window.transient(self)
        config_window.grab_set()
        
        # Centrer la fenêtre / Center window
        config_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (config_window.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (config_window.winfo_height() // 2)
        config_window.geometry(f"+{x}+{y}")
        
        # Frame principal / Main frame
        main_frame = ttk.Frame(config_window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nom du paramètre / Parameter name
        param_names = {
            'mean': tr('position_param'),
            'std': tr('scale_param'),
            'alpha': tr('skewness_param')
        }
        ttk.Label(
            main_frame,
            text=f"{tr('configure_range')}: {param_names.get(slider_name, slider_name)}",
            font=("Arial", 10, "bold")
        ).pack(pady=(0, 10))
        
        # Valeur min / Min value
        min_frame = ttk.Frame(main_frame)
        min_frame.pack(fill=tk.X, pady=5)
        ttk.Label(min_frame, text=tr('minimum'), width=12).pack(side=tk.LEFT)
        min_var = tk.StringVar(value=str(self.slider_ranges[slider_name]['min']))
        min_entry = ttk.Entry(min_frame, textvariable=min_var, width=15)
        min_entry.pack(side=tk.LEFT, padx=5)
        
        # Valeur max / Max value
        max_frame = ttk.Frame(main_frame)
        max_frame.pack(fill=tk.X, pady=5)
        ttk.Label(max_frame, text=tr('maximum'), width=12).pack(side=tk.LEFT)
        max_var = tk.StringVar(value=str(self.slider_ranges[slider_name]['max']))
        max_entry = ttk.Entry(max_frame, textvariable=max_var, width=15)
        max_entry.pack(side=tk.LEFT, padx=5)
        
        # Boutons / Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)
        
        def apply_range():
            try:
                new_min = float(min_var.get())
                new_max = float(max_var.get())
                
                if new_min >= new_max:
                    messagebox.showerror(tr('error'), tr('min_less_than_max'))
                    return
                
                # Mettre à jour la plage / Update range
                self.slider_ranges[slider_name]['min'] = new_min
                self.slider_ranges[slider_name]['max'] = new_max
                
                # Reconfigurer le slider / Reconfigure slider
                if slider_name == 'mean':
                    self.mean_slider.config(from_=new_min, to=new_max)
                elif slider_name == 'std':
                    self.std_slider.config(from_=new_min, to=new_max)
                elif slider_name == 'alpha':
                    self.alpha_slider.config(from_=new_min, to=new_max)
                
                config_window.destroy()
            except ValueError:
                messagebox.showerror(tr('error'), tr('enter_valid_numeric'))
        
        ttk.Button(btn_frame, text=tr('apply_btn'), command=apply_range).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=tr('cancel_btn_symbol'), command=config_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def _on_mean_slider_change(self, value):
        """Ère le changement du slider de position (ξ) / Handle position slider (ξ) change"""
        self.mean = float(value)
        self._update_plot()
    
    def _on_std_slider_change(self, value):
        """Gère le changement du slider d'échelle (ω) / Handle scale slider (ω) change"""
        self.std = max(0.01, float(value))
        self._update_plot()
    
    def _on_alpha_slider_change(self, value):
        """Gère le changement du slider d'asymétrie (α) / Handle skewness slider (α) change"""
        self.alpha = float(value)
        self._update_plot()
    
    def _update_plot(self):
        """Met à jour le graphique avec la distribution actuelle / Update plot with current distribution"""
        self.ax.clear()
        
        # Mode CONSTANT : afficher une ligne verticale unique
        # CONSTANT mode: display single vertical line
        if self.distribution_type == 'CONSTANT':
            # Ligne verticale pour le temps constant / Vertical line for constant time
            self.ax.axvline(self.mean, color='blue', linewidth=4, label=f"{tr('constant_time')} = {self.mean:.2f}")
            
            # Marquer le point / Mark the point
            self.ax.plot(self.mean, 0.5, 'ro', markersize=15, label=tr('fixed_value'), zorder=5)
            
            # Zone de contexte / Context area
            x_min = max(0.01, self.mean - 5)
            x_max = self.mean + 5
            self.ax.set_xlim(x_min, x_max)
            self.ax.set_ylim(0, 1)
            
            # Annotations / Annotations
            self.ax.text(self.mean, 0.7, f'{self.mean:.2f}', 
                        ha='center', va='bottom', fontsize=14, fontweight='bold', color='blue')
            self.ax.text(self.mean, 0.3, tr('no_variability'), 
                        ha='center', va='top', fontsize=10, style='italic', color='#666')
            
            # Labels et titre / Labels and title
            self.ax.set_xlabel(tr('time_axis'), fontsize=12)
            self.ax.set_ylabel(tr('probability'), fontsize=12)
            self.ax.set_title(tr('constant_mode_title'), fontsize=11, fontweight='bold', pad=10)
            self.ax.grid(True, alpha=0.3)
            self.ax.legend(loc='upper right', fontsize=9)
            
            # Mettre à jour le label / Update label
            self.mean_label.config(text=f"{tr('constant_value')}: {self.mean:.2f}")
            self.mean_slider.set(self.mean)
            
            self.canvas.draw()
            return
        
        # Générer les données de la distribution pour NORMAL et SKEW_NORMAL
        # Generate distribution data for NORMAL and SKEW_NORMAL
        # Pour skew-normal, ajuster la plage pour bien montrer l'asymétrie
        # For skew-normal, adjust range to show asymmetry well
        if self.distribution_type == 'SKEW_NORMAL' and abs(self.alpha) > 0.5:
            # Plage asymétrique selon le signe du skew / Asymmetric range based on skew sign
            if self.alpha > 0:
                x_min = max(0.01, self.mean - 3 * self.std)
                x_max = self.mean + 5 * self.std
            else:
                x_min = max(0.01, self.mean - 5 * self.std)
                x_max = self.mean + 3 * self.std
        else:
            x_min = max(0.01, self.mean - 4 * self.std)
            x_max = self.mean + 4 * self.std
        
        x = np.linspace(x_min, x_max, 500)
        
        # Calculer la densité de probabilité / Calculate probability density
        if self.distribution_type == 'SKEW_NORMAL':
            # Distribution skew-normal de scipy.stats / Skew-normal distribution from scipy.stats
            # skewnorm.pdf(x, a, loc, scale) où / where:
            # - a = alpha (paramètre d'asymétrie / skewness parameter)
            # - loc = xi (paramètre de position / position parameter)
            # - scale = omega (paramètre d'échelle / scale parameter)
            y = stats.skewnorm.pdf(x, self.alpha, loc=self.mean, scale=self.std)
        else:
            # Distribution normale standard / Standard normal distribution
            y = stats.norm.pdf(x, loc=self.mean, scale=self.std)
        
        # Tracer la courbe / Draw curve
        self.ax.plot(x, y, 'b-', linewidth=2, label=tr('pdf_label'))
        self.ax.fill_between(x, y, alpha=0.3)
        
        # Tracer les points de contrôle / Draw control points
        y_max = max(y) if len(y) > 0 else 1.0
        
        # Trouver le mode (pic) de la distribution / Find mode (peak) of distribution
        if self.distribution_type == 'SKEW_NORMAL' and len(y) > 0:
            # Pour skew-normal, le mode n'est pas à loc, il faut le trouver
            # For skew-normal, mode is not at loc, need to find it
            mode_idx = np.argmax(y)
            mode_x = x[mode_idx]
            mode_y = y[mode_idx]
            label_text = tr('mode_peak_label')
        else:
            # Pour normale standard, mode = moyenne / For standard normal, mode = mean
            mode_x = self.mean
            mode_y = np.interp(self.mean, x, y) if self.mean >= x_min and self.mean <= x_max else y_max * 0.5
            label_text = tr('mean_mode_label')
        
        self.ax.plot(mode_x, mode_y, 'ro', markersize=12, label=label_text, zorder=5)
        
        # Ligne verticale pour le paramètre de position (ξ)
        # Vertical line for position parameter (ξ)
        if self.distribution_type == 'SKEW_NORMAL':
            # Montrer aussi la position ξ si différente du mode
            # Also show position ξ if different from mode
            if abs(mode_x - self.mean) > 0.1:
                self.ax.axvline(self.mean, color='orange', linestyle=':', alpha=0.5, linewidth=2, label=tr('position_xi_label'))
        
        # Ligne verticale pour le mode / Vertical line for mode
        self.ax.axvline(mode_x, color='r', linestyle='--', alpha=0.3)
        
        # Points à ±1σ (vert) / Points at ±1σ (green)
        plus_1sigma = self.mean + self.std
        minus_1sigma = self.mean - self.std
        
        if plus_1sigma >= x_min and plus_1sigma <= x_max:
            plus_y = np.interp(plus_1sigma, x, y)
            self.ax.plot(plus_1sigma, plus_y, 'go', markersize=10, label='+1σ', zorder=5)
            self.ax.axvline(plus_1sigma, color='g', linestyle='--', alpha=0.3)
        
        if minus_1sigma >= x_min and minus_1sigma <= x_max:
            minus_y = np.interp(minus_1sigma, x, y)
            self.ax.plot(minus_1sigma, minus_y, 'go', markersize=10, label='-1σ', zorder=5)
            self.ax.axvline(minus_1sigma, color='g', linestyle='--', alpha=0.3)
        
        # Labels et titre / Labels and title
        self.ax.set_xlabel(tr('time_axis'), fontsize=12)
        self.ax.set_ylabel(tr('probability_density'), fontsize=12)
        
        if self.distribution_type == 'SKEW_NORMAL':
            # Titre avec les paramètres / Title with parameters
            if abs(self.alpha) < 0.1:
                title = f"{tr('skew_normal_distribution')} ({tr('skew_symmetric')}, α≈0)"
            elif self.alpha > 0:
                title = f"{tr('skew_normal_distribution')} (α={self.alpha:.2f}, {tr('skew_stretched_right')})"
            else:
                title = f"{tr('skew_normal_distribution')} (α={self.alpha:.2f}, {tr('skew_stretched_left')})"
        else:
            title = tr('normal_distribution')
        
        self.ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
        
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(loc='upper right', fontsize=9)
        
        # Mettre à jour les labels et sliders / Update labels and sliders
        self.mean_label.config(text=f"{tr('position_param')}: {self.mean:.2f}")
        self.mean_slider.set(self.mean)
        
        if self.distribution_type != 'CONSTANT':
            self.std_label.config(text=f"{tr('scale_param')}: {self.std:.2f}")
            self.std_slider.set(self.std)
        
        if self.distribution_type == 'SKEW_NORMAL' and hasattr(self, 'alpha_label'):
            self.alpha_label.config(text=f"{tr('skewness_param')}: {self.alpha:.2f}")
            self.alpha_slider.set(self.alpha)
        
        self.canvas.draw()
    
    def _get_nearest_control_point(self, x_data):
        """Trouve le point de contrôle le plus proche d'une position x / Find nearest control point to x position"""
        min_dist = float('inf')
        nearest = None
        
        distances = {
            'mean': abs(x_data - self.mean),
            'plus_1sigma': abs(x_data - (self.mean + self.std)),
            'minus_1sigma': abs(x_data - (self.mean - self.std)),
        }
        
        for point, dist in distances.items():
            if dist < min_dist and dist < (self.std * 0.3):  # Seuil de capture / Capture threshold
                min_dist = dist
                nearest = point
        
        return nearest
    
    def _on_mouse_press(self, event):
        """Gère le clic de souris / Handle mouse click"""
        if event.inaxes != self.ax or event.xdata is None:
            return
        
        # Trouver le point de contrôle le plus proche / Find nearest control point
        self.dragging_point = self._get_nearest_control_point(event.xdata)
        
        if self.dragging_point:
            # Calculer l'offset pour un drag fluide / Calculate offset for smooth drag
            if self.dragging_point == 'mean':
                self.drag_offset = event.xdata - self.mean
            elif self.dragging_point == 'plus_1sigma':
                self.drag_offset = event.xdata - (self.mean + self.std)
            elif self.dragging_point == 'minus_1sigma':
                self.drag_offset = event.xdata - (self.mean - self.std)
    
    def _on_mouse_move(self, event):
        """Gère le déplacement de la souris / Handle mouse move"""
        if not self.dragging_point or event.inaxes != self.ax or event.xdata is None:
            return
        
        # Calculer la nouvelle position avec l'offset / Calculate new position with offset
        new_x = event.xdata - self.drag_offset
        
        if self.dragging_point == 'mean':
            # Déplacer la moyenne (et donc toute la distribution)
            # Move mean (and thus entire distribution)
            self.mean = max(0.01, new_x)
            
        elif self.dragging_point == 'plus_1sigma':
            # Ajuster l'écart-type en déplaçant +1σ
            # Adjust std dev by moving +1σ
            new_std = new_x - self.mean
            if new_std > 0.1:  # Écart-type minimum / Minimum std dev
                self.std = new_std
                    
        elif self.dragging_point == 'minus_1sigma':
            # Ajuster l'écart-type en déplaçant -1σ
            # Adjust std dev by moving -1σ
            new_std = self.mean - new_x
            if new_std > 0.1:  # Écart-type minimum / Minimum std dev
                self.std = new_std
        
        self._update_plot()
    
    def _on_mouse_release(self, event):
        """Gère le relâchement de la souris / Handle mouse release"""
        self.dragging_point = None
        self.drag_offset = 0
    
    def _on_reset(self):
        """Réinitialise aux valeurs par défaut / Reset to default values"""
        self.mean = 10.0
        self.std = 2.0
        self.alpha = 0.0
        self._update_plot()
    
    def _on_validate(self):
        """Valide et retourne les paramètres / Validate and return parameters"""
        if self.callback:
            self.callback(self.mean, self.std, self.alpha)
        self.destroy()
    
    def _update_figure_size(self):
        """Met à jour la taille de la figure en fonction de la taille de la fenêtre
        Update figure size based on window size"""
        # Obtenir la taille disponible / Get available size
        self.update_idletasks()
        available_width = max(400, self.graph_frame.winfo_width())
        available_height = max(300, self.graph_frame.winfo_height())
        
        # Convertir en pouces (80 DPI) / Convert to inches (80 DPI)
        fig_width = available_width / 100
        fig_height = available_height / 100
        
        # Créer ou recréer la figure / Create or recreate figure
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        self.figure = Figure(figsize=(fig_width, fig_height), dpi=100)
        self.ax = self.figure.add_subplot(111)
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _on_window_resize(self, event):
        """Gère le redimensionnement de la fenêtre / Handle window resize"""
        # Éviter de redessiner trop souvent (seulement pour les événements de la fenêtre principale)
        # Avoid redrawing too often (only for main window events)
        if event.widget == self:
            # Utiliser after pour éviter les appels répétés / Use after to avoid repeated calls
            if hasattr(self, '_resize_after_id'):
                self.after_cancel(self._resize_after_id)
            self._resize_after_id = self.after(200, self._delayed_resize)
    
    def _delayed_resize(self):
        """Redimensionnement retardé pour éviter trop d'appels / Delayed resize to avoid too many calls"""
        self._update_figure_size()
        if hasattr(self, 'ax'):
            self._update_plot()
    
    def _on_cancel(self):
        """Annule et ferme la fenêtre / Cancel and close window"""
        self.destroy()
