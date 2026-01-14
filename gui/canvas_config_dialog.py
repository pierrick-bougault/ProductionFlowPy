"""Dialogue de configuration du canvas / Canvas configuration dialog"""
import tkinter as tk
from tkinter import ttk
from gui.translations import tr

class CanvasConfigDialog:
    """Dialogue pour configurer les paramètres du canvas / Dialog to configure canvas parameters"""
    
    def __init__(self, parent, current_width=2000, current_height=2000):
        self.result = None
        
        # Créer la fenêtre de dialogue / Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(tr('canvas_config_title'))
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenêtre / Center window
        self.dialog.geometry("400x300")
        dialog_width = 400
        dialog_height = 300
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Frame principal / Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=tr('canvas_dimensions'), font=("Arial", 12, "bold")).pack(pady=(0, 20))
        
        # Largeur / Width
        width_frame = ttk.Frame(main_frame)
        width_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(width_frame, text=tr('width_px')).pack(side=tk.LEFT, padx=5)
        self.width_var = tk.IntVar(value=current_width)
        width_spinbox = ttk.Spinbox(
            width_frame,
            from_=1000,
            to=10000,
            increment=100,
            textvariable=self.width_var,
            width=15
        )
        width_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Hauteur / Height
        height_frame = ttk.Frame(main_frame)
        height_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(height_frame, text=tr('height_px')).pack(side=tk.LEFT, padx=5)
        self.height_var = tk.IntVar(value=current_height)
        height_spinbox = ttk.Spinbox(
            height_frame,
            from_=1000,
            to=10000,
            increment=100,
            textvariable=self.height_var,
            width=15
        )
        height_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Information sur la taille actuelle / Current size information
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(
            info_frame,
            text=f"{tr('current_size')} {current_width} × {current_height} px",
            foreground="blue"
        ).pack()
        
        # Boutons OK/Annuler / OK/Cancel buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=20)
        
        ttk.Button(button_frame, text=tr('ok'), command=self._on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=tr('cancel'), command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler
        # Bind Enter key to OK and Escape to Cancel
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.dialog.focus_force()
        
        # Attendre la fermeture du dialogue / Wait for dialog close
        self.dialog.wait_window()
    
    def _on_ok(self):
        """Valide et ferme le dialogue / Validate and close dialog"""
        self.result = {
            'width': self.width_var.get(),
            'height': self.height_var.get()
        }
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Annule et ferme le dialogue / Cancel and close dialog"""
        self.dialog.destroy()
