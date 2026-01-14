"""Dialogue de configuration des types d'items pour sources / Item types configuration dialog for sources"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from models.item_type import ItemType, ItemTypeConfig, ItemGenerationMode
from gui.translations import tr

class ItemTypesConfigDialog(tk.Toplevel):
    """Dialogue pour configurer les types d'items d'une source / Dialog to configure item types for a source"""
    
    def __init__(self, parent, item_type_config: ItemTypeConfig):
        super().__init__(parent)
        self.item_type_config = item_type_config
        self.result = None
        self._canvas = None
        self._mousewheel_handler = None
        
        self.title("Configuration des Types d'Items")
        self.geometry("700x600")
        self.resizable(True, True)
        
        # Rendre modal / Make modal
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_data()
        
        # Cleanup lors de la fermeture / Cleanup on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler / Bind Enter key to OK button and Escape to Cancel
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self._on_cancel())
        
        # Activer automatiquement la fenêtre / Automatically focus the window
        self.focus_force()
        
        # Centrer / Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Crée les widgets / Creates the widgets"""
        # Frame principale avec scrollbar / Main frame with scrollbar
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas avec scrollbar / Canvas with scrollbar
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Activer scroll avec molette (bind au canvas au lieu de bind_all) / Enable scroll with mousewheel (bind to canvas instead of bind_all)
        def on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        # Sauvegarder pour cleanup / Save for cleanup
        self._canvas = canvas
        self._mousewheel_handler = on_mousewheel
        
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Mode de génération / Generation mode
        mode_frame = ttk.LabelFrame(main_frame, text="Mode de Génération", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mode_var = tk.StringVar()
        modes = [
            ("Type Unique", ItemGenerationMode.SINGLE_TYPE.value),
            ("Séquence Définie", ItemGenerationMode.SEQUENCE.value),
            ("Aléatoire Fini (Hypergéométrique)", ItemGenerationMode.RANDOM_FINITE.value),
            ("Aléatoire Infini (Catégoriel)", ItemGenerationMode.RANDOM_INFINITE.value)
        ]
        
        for i, (text, value) in enumerate(modes):
            ttk.Radiobutton(
                mode_frame,
                text=text,
                variable=self.mode_var,
                value=value,
                command=self._on_mode_change
            ).grid(row=i, column=0, sticky=tk.W, pady=2)
        
        # Info : Les types sont gérés via le bouton "Editer Items" de la toolbar / Info: Types are managed via "Edit Items" toolbar button
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
            
        # Configuration spécifique au mode / Mode-specific configuration
        self.config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        self.config_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Séquence / Sequence
        self.sequence_frame = ttk.Frame(self.config_frame)
        
        ttk.Label(self.sequence_frame, text="Séquence d'items:").pack(anchor=tk.W)
        
        seq_controls = ttk.Frame(self.sequence_frame)
        seq_controls.pack(fill=tk.X, pady=5)
        
        self.sequence_combo = ttk.Combobox(seq_controls, state="readonly", width=20)
        self.sequence_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(seq_controls, text="➕", width=3, command=self._add_to_sequence).pack(side=tk.LEFT, padx=2)
        ttk.Button(seq_controls, text="🗑️", width=3, command=self._remove_from_sequence).pack(side=tk.LEFT, padx=2)
        ttk.Button(seq_controls, text="⬆️", width=3, command=self._move_sequence_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(seq_controls, text="⬇️", width=3, command=self._move_sequence_down).pack(side=tk.LEFT, padx=2)
        
        # Liste séquence / Sequence list
        self.sequence_listbox = tk.Listbox(self.sequence_frame, height=6)
        self.sequence_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.sequence_loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.sequence_frame,
            text="Boucler à l'infini",
            variable=self.sequence_loop_var
        ).pack(anchor=tk.W)
        
        # Boutons en bas de la fenêtre (hors du scrollable) / Buttons at bottom of window (outside scrollable)
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok, width=12).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=self._on_cancel, width=12).pack(side=tk.RIGHT, padx=5)
    
    def _load_data(self):
        """Charge les données existantes / Loads existing data"""
        # Mode
        self.mode_var.set(self.item_type_config.generation_mode.value)
        
        # Types - Ne plus afficher la liste, elle est gérée via "Editer Items"
        # self._refresh_types_list()
        
        # Séquence
        self._refresh_sequence()
        
        # Afficher la bonne config
        self._on_mode_change()
    
    def _refresh_types_list(self):
        """Rafraîchit la liste des types / Refreshes the types list"""
        # Vider / Clear
        for item in self.types_tree.get_children():
            self.types_tree.delete(item)
        
        # Remplir / Fill
        for item_type in self.item_type_config.item_types:
            # Toujours afficher les valeurs (pas de "-") / Always display values (no "-")
            quantity = self.item_type_config.finite_counts.get(item_type.type_id, 0)
            proportion = self.item_type_config.proportions.get(item_type.type_id, 0.0)
            proportion_str = f"{proportion*100:.1f}"
            
            # Créer une représentation visuelle de la couleur / Create a visual representation of the color
            color_display = f"███ {item_type.color}"
            
            # Insérer dans le treeview avec le type_id comme tag / Insert in treeview with type_id as tag
            if False:
                print(f"[REFRESH] Insertion type: id='{item_type.type_id}', name='{item_type.name}'")
            item_id = self.types_tree.insert("", tk.END, values=(
                item_type.name,
                color_display,
                quantity,
                proportion_str
            ), tags=(item_type.type_id,))
            
            # Vérifier que les tags sont bien définis / Verify that tags are properly defined
            actual_tags = self.types_tree.item(item_id)['tags']
            if False:
                print(f"[REFRESH] Tags après insertion: {actual_tags}")
            
            # Configurer la couleur pour l'affichage / Configure color for display
            self.types_tree.tag_configure(item_type.type_id, foreground=item_type.color)
        
        # Mettre à jour combo séquence / Update sequence combo
        type_names = [t.name for t in self.item_type_config.item_types]
        self.sequence_combo['values'] = type_names
    
    def _refresh_sequence(self):
        """Rafraîchit l'affichage de la séquence / Refreshes the sequence display"""
        self.sequence_listbox.delete(0, tk.END)
        
        # Trouver les noms depuis les IDs / Find names from IDs
        type_dict = {t.type_id: t.name for t in self.item_type_config.item_types}
        
        for idx, type_id in enumerate(self.item_type_config.sequence, start=1):
            name = type_dict.get(type_id, type_id)
            # Ajouter numéro explicite / Add explicit number
            self.sequence_listbox.insert(tk.END, f"{idx}. {name}")
        
        self.sequence_loop_var.set(self.item_type_config.sequence_loop)
    
    def _on_mode_change(self):
        """Changement de mode / Mode change"""
        # Cacher tout / Hide all
        self.sequence_frame.pack_forget()
        
        mode = ItemGenerationMode(self.mode_var.get())
        
        # Afficher selon mode / Display according to mode
        if mode == ItemGenerationMode.SEQUENCE:
            self.sequence_frame.pack(fill=tk.BOTH, expand=True)
        
        # Les colonnes sont toujours visibles (correction bug graphique) / Columns are always visible (graphical bug fix)
        # Ne pas masquer les colonnes selon le mode / Don't hide columns based on mode
    
    def _add_type(self):
        """Ajoute un type d'item / Adds an item type"""
        dialog = AddItemTypeDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
            item_type = dialog.result
            self.item_type_config.item_types.append(item_type)
            # Sauvegarder aussi la quantité et proportion du dialogue / Also save quantity and proportion from dialog
            if hasattr(dialog, 'quantity_var'):
                self.item_type_config.finite_counts[item_type.type_id] = dialog.quantity_var.get()
            if hasattr(dialog, 'proportion_var'):
                self.item_type_config.proportions[item_type.type_id] = dialog.proportion_var.get() / 100.0
            self._refresh_types_list()
    
    def _edit_type(self):
        """Édite un type sélectionné / Edits a selected type"""
        selection = self.types_tree.selection()
        if False:
            print(f"[EDIT] Sélection: {selection}")
        if not selection:
            messagebox.showwarning(tr('selection'), tr('select_type_to_edit'))
            return
        
        item = selection[0]
        tags = self.types_tree.item(item)['tags']
        if False:
            print(f"[EDIT] Tags de l'item: {tags}")
        if not tags:
            if False:
                print("[EDIT] ERREUR: Aucun tag trouvé !")
            messagebox.showerror(tr('error'), tr('cannot_get_type_id'))
            return
        # Convertir en string car tkinter peut convertir '1' en entier 1
        type_id = str(tags[0])
        if False:
            print(f"[EDIT] Type ID: {type_id} (type: {type(type_id)})")
        
        # Trouver le type / Find the type
        if False:
            print(f"[EDIT] Types disponibles: {[t.type_id for t in self.item_type_config.item_types]}")
        item_type = next((t for t in self.item_type_config.item_types if str(t.type_id) == type_id), None)
        if not item_type:
            if False:
                print(f"[EDIT] ERREUR: Type {type_id} non trouvé !")
            messagebox.showerror(tr('error'), tr('type_not_found').format(type_id=type_id))
            return
        
        if False:
            print(f"[EDIT] Type trouvé: {item_type.name}")
        # Dialogue d'édition / Edit dialog
        dialog = EditItemTypeDialog(self, item_type, self.item_type_config, self.mode_var.get())
        self.wait_window(dialog)
        
        # Toujours rafraîchir l'affichage après édition (même si annulé) / Always refresh display after editing (even if cancelled)
        self._refresh_types_list()
    
    def _delete_type(self):
        """Supprime un type / Deletes a type"""
        selection = self.types_tree.selection()
        if False:
            print(f"[DELETE] Sélection: {selection}")
        if not selection:
            messagebox.showwarning(tr('selection'), tr('select_type_to_delete'))
            return
        
        if not messagebox.askyesno(tr('confirmation'), tr('delete_type_confirm')):
            return
        
        item = selection[0]
        tags = self.types_tree.item(item)['tags']
        if False:
            print(f"[DELETE] Tags de l'item: {tags}")
        if not tags:
            if False:
                print("[DELETE] ERREUR: Aucun tag trouvé !")
            messagebox.showerror(tr('error'), tr('cannot_get_type_id'))
            return
        # Convertir en string car tkinter peut convertir '1' en entier 1 / Convert to string as tkinter may convert '1' to int 1
        type_id = str(tags[0])
        if False:
            print(f"[DELETE] Type ID à supprimer: {type_id} (type: {type(type_id)})")
        
        # Supprimer / Delete
        self.item_type_config.item_types = [
            t for t in self.item_type_config.item_types if str(t.type_id) != type_id
        ]
        
        # Nettoyer config / Clean config
        self.item_type_config.sequence = [
            tid for tid in self.item_type_config.sequence if tid != type_id
        ]
        self.item_type_config.finite_counts.pop(type_id, None)
        self.item_type_config.proportions.pop(type_id, None)
        
        self._refresh_types_list()
        self._refresh_sequence()
    
    def _add_to_sequence(self):
        """Ajoute à la séquence / Adds to sequence"""
        if not self.sequence_combo.get():
            return
        
        # Trouver l'ID depuis le nom / Find ID from name
        name = self.sequence_combo.get()
        type_id = next((t.type_id for t in self.item_type_config.item_types if t.name == name), None)
        
        if type_id:
            self.item_type_config.sequence.append(type_id)
            self._refresh_sequence()
    
    def _remove_from_sequence(self):
        """Retire de la séquence / Removes from sequence"""
        selection = self.sequence_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.item_type_config.sequence[idx]
            self._refresh_sequence()
    
    def _move_sequence_up(self):
        """Monte dans la séquence / Moves up in sequence"""
        selection = self.sequence_listbox.curselection()
        if selection and selection[0] > 0:
            idx = selection[0]
            seq = self.item_type_config.sequence
            seq[idx], seq[idx-1] = seq[idx-1], seq[idx]
            self._refresh_sequence()
            self.sequence_listbox.selection_set(idx-1)
    
    def _move_sequence_down(self):
        """Descend dans la séquence / Moves down in sequence"""
        selection = self.sequence_listbox.curselection()
        if selection and selection[0] < len(self.item_type_config.sequence) - 1:
            idx = selection[0]
            seq = self.item_type_config.sequence
            seq[idx], seq[idx+1] = seq[idx+1], seq[idx]
            self._refresh_sequence()
            self.sequence_listbox.selection_set(idx+1)
    
    def _on_ok(self):
        """Valide / Validates"""
        # Sauvegarder mode / Save mode
        self.item_type_config.generation_mode = ItemGenerationMode(self.mode_var.get())
        
        # Sauvegarder séquence loop / Save sequence loop
        self.item_type_config.sequence_loop = self.sequence_loop_var.get()
        
        # Validation / Validation
        mode = self.item_type_config.generation_mode
        
        if mode != ItemGenerationMode.SINGLE_TYPE and not self.item_type_config.item_types:
            messagebox.showerror(tr('error'), tr('define_at_least_one_type'))
            return
        
        if mode == ItemGenerationMode.SEQUENCE and not self.item_type_config.sequence:
            messagebox.showerror(tr('error'), tr('sequence_cannot_be_empty'))
            return
        
        if mode == ItemGenerationMode.RANDOM_FINITE:
            if not any(self.item_type_config.finite_counts.values()):
                messagebox.showerror(tr('error'), tr('must_define_quantities'))
                return
        
        if mode == ItemGenerationMode.RANDOM_INFINITE:
            total = sum(self.item_type_config.proportions.values())
            if abs(total - 1.0) > 0.01:
                messagebox.showerror(tr('error'), tr('proportions_must_total_100').format(total=f"{total*100:.1f}"))
                return
        
        self.result = True
        self._cleanup()
        self.destroy()
    
    def _on_close(self):
        """Fermeture de la fenêtre / Window closing"""
        self._cleanup()
        self.destroy()
    
    def _cleanup(self):
        """Nettoie les bindings pour éviter les erreurs / Cleans bindings to avoid errors"""
        if self._canvas and self._canvas.winfo_exists():
            try:
                self._canvas.unbind_all("<MouseWheel>")
            except:
                pass
    
    def _on_cancel(self):
        """Annule / Cancels"""
        self.result = None
        self._cleanup()
        self.destroy()


class AddItemTypeDialog(tk.Toplevel):
    """Dialogue pour ajouter un type / Dialog to add a type"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.parent_dialog = parent  # Référence au parent pour accéder à la config / Reference to parent to access config
        
        self.title("Nouveau Type d'Item")
        self.geometry("400x170")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        
        # Générer automatiquement un ID unique / Automatically generate unique ID
        self._generate_unique_id()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler / Bind Enter to OK button and Escape to Cancel
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self.destroy())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.focus_force()
        
        # Centrer / Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _generate_unique_id(self):
        """Génère automatiquement un ID unique basé sur les IDs existants / Automatically generates unique ID based on existing IDs"""
        existing_ids = set()
        
        # Récupérer les IDs existants depuis le parent / Get existing IDs from parent
        if hasattr(self.parent_dialog, 'item_type_config'):
            for item_type in self.parent_dialog.item_type_config.item_types:
                # Essayer de convertir l'ID en int s'il est numérique / Try to convert ID to int if numeric
                try:
                    existing_ids.add(int(item_type.type_id))
                except (ValueError, TypeError):
                    pass
        
        # Trouver le prochain ID disponible / Find next available ID
        next_id = 1
        while next_id in existing_ids:
            next_id += 1
        
        self.id_var.set(str(next_id))
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ID généré automatiquement en arrière-plan (non affiché) / ID automatically generated in background (not displayed)
        self.id_var = tk.StringVar()
        
        # Nom (focus initial) / Name (initial focus)
        ttk.Label(main_frame, text="Nom d'affichage:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, pady=5)
        name_entry.focus_set()  # Focus sur le nom au démarrage / Focus on name at start
        
        # Couleur / Color
        ttk.Label(main_frame, text="Couleur:").grid(row=1, column=0, sticky=tk.W, pady=5)
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.color_var = tk.StringVar(value="#4CAF50")
        self.color_preview = tk.Label(color_frame, text="    ", bg="#4CAF50", width=4, relief=tk.RAISED)
        self.color_preview.pack(side=tk.LEFT, padx=5)
        ttk.Button(color_frame, text="Choisir...", command=self._choose_color).pack(side=tk.LEFT)
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _choose_color(self):
        # Relâcher le grab pour permettre à la fenêtre de couleur de fonctionner
        self.grab_release()
        self.update_idletasks()
        # Utiliser la fenêtre racine comme parent pour éviter les problèmes
        root = self.winfo_toplevel().master
        if root is None:
            root = self.winfo_toplevel()
        color = colorchooser.askcolor(initialcolor=self.color_var.get(), parent=root, title="Choisir une couleur")[1]
        # Reprendre le grab et ramener le focus
        self.grab_set()
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


class EditItemTypeDialog(tk.Toplevel):
    """Dialogue pour éditer un type / Dialog to edit a type"""
    
    def __init__(self, parent, item_type: ItemType, config: ItemTypeConfig, mode: str):
        super().__init__(parent)
        self.item_type = item_type
        self.config = config
        self.mode = mode
        self.result = False  # Important: False par défaut, True si sauvegarde / Important: False by default, True if saved
        
        self.title(f"Éditer: {item_type.name}")
        self.geometry("400x350")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_data()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler / Bind Enter to OK button and Escape to Cancel
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self.destroy())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.focus_force()
        
        # Centrer / Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        row = 0
        
        # Nom / Name
        ttk.Label(main_frame, text="Nom:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, pady=5)
        row += 1
        
        # Couleur / Color
        ttk.Label(main_frame, text="Couleur:").grid(row=row, column=0, sticky=tk.W, pady=5)
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        self.color_var = tk.StringVar()
        self.color_preview = tk.Label(color_frame, text="    ", width=4, relief=tk.RAISED)
        self.color_preview.pack(side=tk.LEFT, padx=5)
        ttk.Button(color_frame, text="Choisir...", command=self._choose_color).pack(side=tk.LEFT)
        row += 1
        
        # Quantité (toujours éditable) / Quantity (always editable)
        ttk.Label(main_frame, text="Quantité:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.quantity_var = tk.IntVar(value=10)
        ttk.Spinbox(main_frame, from_=1, to=10000, textvariable=self.quantity_var, width=28).grid(row=row, column=1, pady=5)
        row += 1
        
        # Proportion (toujours éditable) / Proportion (always editable)
        ttk.Label(main_frame, text="Proportion (%):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.proportion_var = tk.DoubleVar(value=33.3)
        ttk.Spinbox(main_frame, from_=0.1, to=100.0, increment=0.1, textvariable=self.proportion_var, width=28).grid(row=row, column=1, pady=5)
        row += 1
        
        # Boutons / Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def _load_data(self):
        self.name_var.set(self.item_type.name)
        self.color_var.set(self.item_type.color)
        self.color_preview.config(bg=self.item_type.color)
        
        # Quantité / Quantity
        quantity = self.config.finite_counts.get(self.item_type.type_id, 10)
        self.quantity_var.set(quantity)
        
        # Proportion / Proportion
        proportion = self.config.proportions.get(self.item_type.type_id, 0.0)
        self.proportion_var.set(proportion * 100)
    
    def _choose_color(self):
        # Relâcher le grab pour permettre à la fenêtre de couleur de fonctionner
        self.grab_release()
        self.update_idletasks()
        # Utiliser la fenêtre racine comme parent pour éviter les problèmes
        root = self.winfo_toplevel().master
        if root is None:
            root = self.winfo_toplevel()
        color = colorchooser.askcolor(initialcolor=self.color_var.get(), parent=root, title="Choisir une couleur")[1]
        # Reprendre le grab et ramener le focus
        self.grab_set()
        self.focus_force()
        self.lift()
        if color:
            self.color_var.set(color)
            self.color_preview.config(bg=color)

    def _on_ok(self):
        # Sauvegarder / Save
        self.item_type.name = self.name_var.get()
        self.item_type.color = self.color_var.get()
        
        # Sauvegarder quantité et proportion (toujours, peu importe le mode) / Save quantity and proportion (always, regardless of mode)
        self.config.finite_counts[self.item_type.type_id] = self.quantity_var.get()
        self.config.proportions[self.item_type.type_id] = self.proportion_var.get() / 100.0
        
        self.result = True
        self.destroy()
