"""Dialogue pour la gestion globale des types d'items (sans séquençage)
Dialog for global item types management (without sequencing)"""
import tkinter as tk
from tkinter import ttk, messagebox
from models.item_type import ItemType, ItemTypeConfig
from gui.translations import tr
from gui.color_picker_dialog import askcolor as custom_askcolor

class GlobalItemTypesDialog(tk.Toplevel):
    """Dialogue simplifié pour gérer uniquement l'édition des types d'items
    Simplified dialog for editing item types only"""
    
    def __init__(self, parent, item_type_config: ItemTypeConfig):
        super().__init__(parent)
        self.item_type_config = item_type_config
        self.result = False
        
        self.title("Gestion des Types d'Items")
        self.geometry("700x500")
        self.resizable(True, True)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_data()
        
        # Bind touche Entrée au bouton OK / Bind Enter key to OK button
        self.bind('<Return>', lambda e: self._on_ok())
        
        # Centrer / Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        """Crée les widgets / Create widgets"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info
        info_label = ttk.Label(
            main_frame,
            text="Gérez ici tous les types d'items disponibles dans votre modèle.\n"
                 "Les sources pourront ensuite utiliser ces types dans leur configuration.\n"
                 "Manage all available item types in your model here.\n"
                 "Sources can then use these types in their configuration.",
            font=("Arial", 9, "italic"),
            foreground="#666",
            justify=tk.LEFT
        )
        info_label.pack(pady=(0, 10))
        
        # Frame pour la liste et les boutons / Frame for list and buttons
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Liste des types / Types list
        list_frame = ttk.LabelFrame(content_frame, text="Types d'items définis", padding="10")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Treeview
        columns = ("Nom", "Couleur", "ID")
        self.types_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        self.types_tree.heading("Nom", text="Nom / Name")
        self.types_tree.heading("Couleur", text="Couleur / Color")
        self.types_tree.heading("ID", text="ID Technique / Technical ID")
        
        self.types_tree.column("Nom", width=200)
        self.types_tree.column("Couleur", width=150)
        self.types_tree.column("ID", width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._on_tree_scroll)
        self.types_tree.configure(yscrollcommand=self._on_tree_yscroll)
        
        self.types_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._scrollbar = scrollbar
        
        # Lier les événements de redimensionnement / Bind resize events
        self.types_tree.bind('<Configure>', lambda e: self.after(10, self._update_color_previews))
        self.types_tree.bind('<Expose>', lambda e: self.after(10, self._update_color_previews))
        
        # Boutons d'action / Action buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(button_frame, text="➕ Ajouter / Add", command=self._add_type, width=15).pack(pady=5)
        ttk.Button(button_frame, text="✏️ Modifier / Edit", command=self._edit_type, width=15).pack(pady=5)
        ttk.Button(button_frame, text="🗑️ Supprimer / Delete", command=self._delete_type, width=15).pack(pady=5)
        
        # Séparateur / Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Boutons de validation / Validation buttons
        button_frame_bottom = ttk.Frame(main_frame)
        button_frame_bottom.pack(fill=tk.X)
        
        ttk.Button(button_frame_bottom, text="OK", command=self._on_ok, width=12).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame_bottom, text="Annuler / Cancel", command=self._on_close, width=12).pack(side=tk.RIGHT, padx=5)
    
    def _on_tree_scroll(self, *args):
        """Gère le scroll du Treeview / Handle Treeview scroll"""
        self.types_tree.yview(*args)
        self.after(10, self._update_color_previews)
    
    def _on_tree_yscroll(self, *args):
        """Gère le callback de scroll / Handle scroll callback"""
        self._scrollbar.set(*args)
        self.after(10, self._update_color_previews)
    
    def _update_color_previews(self):
        """Met à jour les aperçus de couleur superposés sur le Treeview / Updates color previews overlaid on Treeview"""
        # Nettoyer les anciens widgets / Clean old widgets
        if hasattr(self, '_color_labels'):
            for label in self._color_labels:
                try:
                    label.destroy()
                except:
                    pass
        self._color_labels = []
        
        # Pour chaque item dans le Treeview / For each item in Treeview
        for item_id in self.types_tree.get_children():
            tags = self.types_tree.item(item_id)['tags']
            if not tags:
                continue
            
            type_id = str(tags[0])
            item_type = next((t for t in self.item_type_config.item_types if str(t.type_id) == type_id), None)
            if not item_type:
                continue
            
            try:
                # Obtenir la position de la cellule de couleur / Get color cell position
                bbox = self.types_tree.bbox(item_id, "Couleur")
                if bbox:
                    x, y, width, height = bbox
                    
                    # Créer un label coloré / Create colored label
                    color_label = tk.Label(
                        self.types_tree,
                        bg=item_type.color,
                        width=3,
                        height=1,
                        relief=tk.RAISED,
                        borderwidth=1
                    )
                    # Positionner le label dans la cellule / Position label in cell
                    color_label.place(x=x + 5, y=y + 2, width=25, height=height - 4)
                    
                    # Transférer les clics au Treeview pour permettre la sélection / Transfer clicks to Treeview to allow selection
                    def on_label_click(event, iid=item_id):
                        self.types_tree.selection_set(iid)
                        self.types_tree.focus(iid)
                        return "break"  # Empêcher propagation
                    
                    def on_label_double_click(event, iid=item_id):
                        self.types_tree.selection_set(iid)
                        self.types_tree.focus(iid)
                        # Utiliser after pour s'assurer que l'événement est terminé avant d'ouvrir le dialogue
                        self.after(50, self._edit_type)
                        return "break"  # Empêcher propagation
                    
                    color_label.bind('<Button-1>', on_label_click)
                    color_label.bind('<Double-Button-1>', on_label_double_click)
                    
                    self._color_labels.append(color_label)
            except Exception:
                pass
    
    def _load_data(self):
        """Charge les données / Load data"""
        self._refresh_types_list()
    
    def _refresh_types_list(self):
        """Rafraîchit la liste des types / Refresh types list"""
        # Vider / Clear
        for item in self.types_tree.get_children():
            self.types_tree.delete(item)
        
        # Nettoyer les anciens widgets de couleur / Clean old color widgets
        if hasattr(self, '_color_labels'):
            for label in self._color_labels:
                try:
                    label.destroy()
                except:
                    pass
        self._color_labels = []
        
        # Remplir / Fill
        for item_type in self.item_type_config.item_types:
            # Créer une représentation textuelle de la couleur
            # Create text color representation
            color_display = f"■ {item_type.color}"
            
            # Insérer l'item avec SEULEMENT le type_id dans les tags
            # Insert item with ONLY type_id in tags
            item_id = self.types_tree.insert("", tk.END, values=(
                item_type.name,
                color_display,
                item_type.type_id
            ), tags=(item_type.type_id,))
        
        # Créer les aperçus de couleur après un court délai
        # Create color previews after a short delay
        self.after(50, self._update_color_previews)
    
    def _add_type(self):
        """Ajoute un nouveau type / Add new type"""
        dialog = AddItemTypeDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
            # Vérifier l'unicité de l'ID / Check ID uniqueness
            if any(str(t.type_id) == str(dialog.result.type_id) for t in self.item_type_config.item_types):
                messagebox.showerror(tr('error'), tr('type_id_exists'))
                return
            
            self.item_type_config.item_types.append(dialog.result)
            self._refresh_types_list()
    
    def _edit_type(self):
        """Édite un type sélectionné / Edit selected type"""
        selection = self.types_tree.selection()
        if False:
            print(f"[GLOBAL_EDIT] Sélection: {selection}")
        if not selection:
            messagebox.showwarning(tr('selection'), tr('select_type_to_edit'))
            return
        
        item = selection[0]
        tags = self.types_tree.item(item)['tags']
        if False:
            print(f"[GLOBAL_EDIT] Tags de l'item: {tags}")
        if not tags:
            if False:
                print("[GLOBAL_EDIT] ERREUR: Aucun tag trouvé !")
            messagebox.showerror(tr('error'), tr('cannot_get_type_id'))
            return
        # Convertir en string car tkinter peut convertir '1' en entier 1
        type_id = str(tags[0])
        if False:
            print(f"[GLOBAL_EDIT] Type ID: {type_id}")
        
        # Trouver le type / Find the type
        if False:
            print(f"[GLOBAL_EDIT] Types disponibles: {[t.type_id for t in self.item_type_config.item_types]}")
        item_type = next((t for t in self.item_type_config.item_types if str(t.type_id) == type_id), None)
        if not item_type:
            if False:
                print(f"[GLOBAL_EDIT] ERREUR: Type {type_id} non trouvé !")
            messagebox.showerror(tr('error'), tr('type_not_found').format(type_id=type_id))
            return
        
        if False:
            print(f"[GLOBAL_EDIT] Type trouvé: {item_type.name}")
        # Relâcher le grab temporairement pour le dialogue enfant
        self.grab_release()
        
        # Dialogue d'édition / Edit dialog
        dialog = EditItemTypeDialogSimple(self, item_type)
        self.wait_window(dialog)
        
        # Reprendre le grab
        self.grab_set()
        
        # Toujours rafraîchir l'affichage après édition / Always refresh after edit
        self._refresh_types_list()
    
    def _delete_type(self):
        """Supprime un type / Delete type"""
        selection = self.types_tree.selection()
        if False:
            print(f"[GLOBAL_DELETE] Sélection: {selection}")
        if not selection:
            messagebox.showwarning(tr('selection'), tr('select_type_to_delete'))
            return
        
        if not messagebox.askyesno(tr('confirmation'), tr('delete_type_confirm')):
            return
        
        item = selection[0]
        tags = self.types_tree.item(item)['tags']
        if False:
            print(f"[GLOBAL_DELETE] Tags de l'item: {tags}")
        if not tags:
            if False:
                print("[GLOBAL_DELETE] ERREUR: Aucun tag trouvé !")
            messagebox.showerror(tr('error'), tr('cannot_get_type_id'))
            return
        # Convertir en string car tkinter peut convertir '1' en entier 1
        type_id = str(tags[0])
        if False:
            print(f"[GLOBAL_DELETE] Type ID à supprimer: {type_id}")
        
        # Supprimer / Delete
        self.item_type_config.item_types = [
            t for t in self.item_type_config.item_types if str(t.type_id) != type_id
        ]
        
        # Rafraîchir / Refresh
        self._refresh_types_list()
    
    def _on_ok(self):
        """Valide / Validate"""
        if not self.item_type_config.item_types:
            if not messagebox.askyesno(
                tr('confirmation'),
                tr('no_item_type_warning'),
                parent=self
            ):
                return
        
        self.result = True
        self.destroy()
    
    def _on_close(self):
        """Fermeture / Close"""
        self.destroy()


class AddItemTypeDialog(tk.Toplevel):
    """Dialogue pour ajouter un type / Dialog to add a type"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        
        self.title("Ajouter un type / Add type")
        self.geometry("400x250")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self.destroy())
        
        # Activer automatiquement la fenêtre
        self.focus_force()
        
        # Centrer
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        # ID
        ttk.Label(main_frame, text="ID Technique / Technical ID:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.id_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.id_var, width=30).grid(row=row, column=1, pady=5)
        row += 1
        
        ttk.Label(
            main_frame,
            text="(ex: 'roue', 'chassis', 'moteur')",
            font=("Arial", 8, "italic"),
            foreground="#666"
        ).grid(row=row, column=1, sticky=tk.W)
        row += 1
        
        # Nom / Name
        ttk.Label(main_frame, text="Nom d'affichage / Display name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, pady=5)
        row += 1
        
        # Couleur
        ttk.Label(main_frame, text="Couleur:").grid(row=row, column=0, sticky=tk.W, pady=5)
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        self.color_var = tk.StringVar(value="#FF5733")
        self.color_preview = tk.Label(color_frame, text="    ", width=4, relief=tk.RAISED, bg="#FF5733")
        self.color_preview.pack(side=tk.LEFT, padx=5)
        ttk.Button(color_frame, text="Choisir... / Choose...", command=self._choose_color).pack(side=tk.LEFT)
        row += 1
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler / Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _choose_color(self):
        # Utiliser notre sélecteur de couleur ctypes
        result = custom_askcolor(initialcolor=self.color_var.get(), parent=self, title="Choisir une couleur / Choose a color")
        color = result[1]
        if color:
            self.color_var.set(color)
            self.color_preview.config(bg=color)
        # Ramener le focus
        self.focus_force()
        self.lift()

    def _on_ok(self):
        type_id = self.id_var.get().strip()
        name = self.name_var.get().strip()
        
        if not type_id or not name:
            messagebox.showerror(tr('error'), tr('id_name_required'))
            return
        
        self.result = ItemType(type_id, name, self.color_var.get())
        self.destroy()


class EditItemTypeDialogSimple(tk.Toplevel):
    """Dialogue pour éditer un type (simplifié - sans quantités/proportions)
    Dialog to edit a type (simplified - without quantities/proportions)"""
    
    def __init__(self, parent, item_type: ItemType):
        super().__init__(parent)
        self.item_type = item_type
        self.result = False
        
        self.title(f"Éditer / Edit: {item_type.name}")
        self.geometry("400x200")
        self.resizable(False, False)
        
        self.transient(parent)
        # Ne pas utiliser grab_set() car le parent a déjà un grab
        
        self._create_widgets()
        self._load_data()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self.destroy())
        
        # Empêcher propagation du double-clic
        self.bind('<Double-Button-1>', lambda e: None)
        
        # Activer automatiquement la fenêtre
        self.focus_force()
        
        # Centrer
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        # ID (non éditable / non-editable)
        ttk.Label(main_frame, text="ID:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text=self.item_type.type_id, foreground="#666").grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Nom / Name
        ttk.Label(main_frame, text="Nom / Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, pady=5)
        row += 1
        
        # Couleur / Color
        ttk.Label(main_frame, text="Couleur / Color:").grid(row=row, column=0, sticky=tk.W, pady=5)
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        self.color_var = tk.StringVar()
        self.color_preview = tk.Label(color_frame, text="    ", width=4, relief=tk.RAISED)
        self.color_preview.pack(side=tk.LEFT, padx=5)
        ttk.Button(color_frame, text="Choisir... / Choose...", command=self._choose_color).pack(side=tk.LEFT)
        row += 1
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        self.ok_btn = ttk.Button(button_frame, text="OK", command=self._on_ok)
        self.ok_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler / Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _load_data(self):
        self.name_var.set(self.item_type.name)
        self.color_var.set(self.item_type.color)
        self.color_preview.config(bg=self.item_type.color)
    
    def _choose_color(self):
        # Utiliser notre sélecteur de couleur ctypes
        result = custom_askcolor(initialcolor=self.color_var.get(), parent=self, title="Choisir une couleur")
        color = result[1]
        if color:
            self.color_var.set(color)
            self.color_preview.config(bg=color)
        # Ramener le focus sur cette fenêtre
        self.focus_force()
        self.lift()
    def _on_ok(self):
        # Sauvegarder / Save
        new_name = self.name_var.get().strip()
        new_color = self.color_var.get()
        
        if not new_name:
            messagebox.showerror("Erreur / Error", "Le nom est requis / Name is required")
            return
        
        self.item_type.name = new_name
        self.item_type.color = new_color
        
        self.result = True
        self.destroy()
