"""Dialogue pour configurer une annotation (rectangle avec texte) / Dialog to configure an annotation (rectangle with text)"""
import tkinter as tk
from tkinter import ttk, colorchooser
from gui.translations import tr

class AnnotationConfigDialog:
    """Dialogue pour créer/éditer une annotation / Dialog to create/edit an annotation"""
    
    def __init__(self, parent, annotation=None):
        self.result = None
        self.annotation = annotation
        
        # Créer la fenêtre modale / Create modal window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configurer l'annotation")  # Configure annotation
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenêtre / Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"400x300+{x}+{y}")
        
        self._create_widgets()
        
        # Remplir avec les valeurs existantes si modification / Fill with existing values if editing
        if annotation:
            self.text_var.set(annotation.text)
            self.color = annotation.color
            self.color_button.config(bg=self.color)
        
        # Attendre la fermeture / Wait for close
        self.dialog.wait_window()
    
    def _create_widgets(self):
        """Crée les widgets du dialogue / Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Texte de l'annotation / Annotation text
        ttk.Label(main_frame, text="Texte de l'annotation:").pack(anchor=tk.W, pady=5)
        self.text_var = tk.StringVar(value="Système 1")
        text_entry = ttk.Entry(main_frame, textvariable=self.text_var, width=40)
        text_entry.pack(fill=tk.X, pady=5)
        text_entry.focus()
        
        # Couleur / Color
        color_frame = ttk.Frame(main_frame)
        color_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(color_frame, text="Couleur:").pack(side=tk.LEFT, padx=5)
        self.color = "#888888"
        self.color_button = tk.Button(
            color_frame,
            text="Choisir",
            bg=self.color,
            width=10,
            command=self._choose_color
        )
        self.color_button.pack(side=tk.LEFT, padx=5)
        
        # Taille du texte / Text size
        text_size_frame = ttk.Frame(main_frame)
        text_size_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(text_size_frame, text="Taille du texte:").pack(side=tk.LEFT, padx=5)
        self.text_size_var = tk.IntVar(value=self.annotation.text_size if self.annotation else 12)
        text_size_spinbox = ttk.Spinbox(
            text_size_frame,
            from_=8,
            to=24,
            textvariable=self.text_size_var,
            width=10
        )
        text_size_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Boutons OK/Annuler/Supprimer / OK/Cancel/Delete buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        # Bouton Supprimer (seulement si on édite une annotation existante) / Delete button (only if editing existing annotation)
        if self.annotation:
            ttk.Button(button_frame, text="Supprimer", command=self._on_delete, width=15).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key / Lier touche Entrée
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.dialog.focus_force()
    
    def _choose_color(self):
        """Ouvre un dialogue de sélection de couleur / Open color selection dialog"""
        # Relâcher le grab pour permettre à la fenêtre de couleur de fonctionner
        self.dialog.grab_release()
        color = colorchooser.askcolor(
            title="Choisir la couleur",  # Choose color
            initialcolor=self.color
        )
        # Reprendre le grab
        self.dialog.grab_set()
        if color[1]:  # color[1] est le code hex
            self.color = color[1]
            self.color_button.config(bg=self.color)
    
    def _on_ok(self):
        """Valide et ferme le dialogue / Validate and close dialog"""
        text = self.text_var.get().strip()
        if not text:
            from tkinter import messagebox
            messagebox.showwarning(tr('text_required'), tr('enter_annotation_text'))
            return
        
        self.result = {
            'text': text,
            'color': self.color,
            'text_size': self.text_size_var.get()
        }
        self.dialog.destroy()
    
    def _on_delete(self):
        """Supprime l'annotation / Delete annotation"""
        self.result = {'delete': True}
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Annule et ferme le dialogue / Cancel and close dialog"""
        self.result = None
        self.dialog.destroy()
