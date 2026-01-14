"""
Gestionnaire optimisé de combinaisons - Interface unifiée / Optimized combination manager - Unified interface
"""
import tkinter as tk
from tkinter import ttk, messagebox
from models.combination import Combination, CombinationIngredient, CombinationSet
from typing import List, Optional
from gui.translations import tr


class CombinationManagerDialog:
    """Interface unifiée pour gérer toutes les combinaisons d'un nœud / Unified interface to manage all combinations of a node"""
    
    def __init__(self, parent, flow_model, node):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Gestionnaire de Combinaisons - {node.name}")
        self.dialog.geometry("1100x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.flow_model = flow_model
        self.node = node
        self.current_combination = None
        self.available_types = self._get_available_item_types()
        
        # Créer un mapping nom→type_id pour retrouver les IDs / Create name→type_id mapping to find IDs
        self.name_to_type_id = {name: type_id for type_id, name, _ in self.available_types}
        
        self._create_widgets()
        self._refresh_combinations_list()
        
        # Centrer la fenêtre / Center the window
        self._center_window()
        
        self.dialog.wait_window()
    
    def _center_window(self):
        """Centre la fenêtre sur l'écran / Centers the window on screen"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def _get_available_item_types(self) -> List[tuple]:
        """Récupère tous les types d'items disponibles en amont du nœud / Gets all item types available upstream of the node"""
        types = []
        visited = set()
        
        def collect_types_recursive(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            
            node = self.flow_model.get_node(node_id)
            if not node:
                return
            
            # Si c'est une source avec types configurés / If it's a source with configured types
            if node.is_source and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    type_tuple = (item_type.type_id, item_type.name, item_type.color)
                    if type_tuple not in types:
                        types.append(type_tuple)
            
            # Remonter récursivement / Climb recursively
            for conn_id in node.input_connections:
                conn = self.flow_model.get_connection(conn_id)
                if conn:
                    collect_types_recursive(conn.source_id)
        
        # Partir du nœud actuel / Start from current node
        collect_types_recursive(self.node.node_id)
        
        return types
    
    def _create_widgets(self):
        """Crée l'interface en 2 panneaux / Creates the 2-panel interface"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # PanedWindow pour diviser l'interface en 2 / PanedWindow to split interface in 2
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # ===== PANNEAU GAUCHE : Liste des combinaisons ===== / ===== LEFT PANEL: Combinations list =====
        left_panel = ttk.Frame(paned, padding="5")
        paned.add(left_panel, weight=1)
        
        ttk.Label(left_panel, text="📋 Combinaisons Définies", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        # Liste des combinaisons / Combinations list
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.combinations_listbox = tk.Listbox(list_frame, font=('Arial', 9))
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.combinations_listbox.yview)
        self.combinations_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        self.combinations_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection / Bind sélection
        self.combinations_listbox.bind('<<ListboxSelect>>', self._on_combination_selected)
        
        # Boutons de gestion de la liste / List management buttons
        list_buttons = ttk.Frame(left_panel)
        list_buttons.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(list_buttons, text="➕ Nouvelle", command=self._new_combination).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_buttons, text="🗑️ Supprimer", command=self._delete_combination).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_buttons, text="📋 Dupliquer", command=self._duplicate_combination).pack(side=tk.LEFT, padx=2)
        
        # ===== PANNEAU DROIT : Éditeur de combinaison ===== / ===== RIGHT PANEL: Combination editor =====
        right_panel = ttk.Frame(paned, padding="5")
        paned.add(right_panel, weight=2)
        
        ttk.Label(right_panel, text="✏️ Éditeur de Combinaison", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        # Scroll pour l'éditeur / Scroll for editor
        editor_canvas = tk.Canvas(right_panel, bg='#f0f0f0', highlightthickness=0)
        editor_scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=editor_canvas.yview)
        self.editor_frame = ttk.Frame(editor_canvas)
        
        self.editor_frame.bind('<Configure>', lambda e: editor_canvas.configure(scrollregion=editor_canvas.bbox('all')))
        editor_canvas.create_window((0, 0), window=self.editor_frame, anchor='nw')
        editor_canvas.configure(yscrollcommand=editor_scrollbar.set)
        
        editor_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        editor_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Contenu de l'éditeur / Editor content
        self._create_editor_widgets()
        
        # ===== BOUTONS GLOBAUX ===== / ===== GLOBAL BUTTONS =====
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(bottom_frame, text="💾 Enregistrer et Fermer", command=self._save_and_close, 
                   style='Accent.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Annuler", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    
    def _create_editor_widgets(self):
        """Crée les widgets de l'éditeur / Creates editor widgets"""
        # Désactivé par défaut (aucune combinaison sélectionnée) / Disabled by default (no combination selected)
        self.editor_enabled = False
        
        # === Informations de base === / === Basic information ===
        info_frame = ttk.LabelFrame(self.editor_frame, text="📝 Informations", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="Nom:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(info_frame, textvariable=self.name_var, width=40, font=('Arial', 10))
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        info_frame.columnconfigure(1, weight=1)
        
        # === Composants (Ingrédients) === / === Components (Ingredients) ===
        ingredients_frame = ttk.LabelFrame(self.editor_frame, text="🧪 Composants Requis", padding="10")
        ingredients_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Container pour tree + boutons / Container for tree + buttons
        tree_container = ttk.Frame(ingredients_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Liste des ingrédients avec style moderne / Ingredients list with modern style
        columns = ('type', 'quantité')
        self.ingredients_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=6)
        self.ingredients_tree.heading('type', text='Type d\'Item')
        self.ingredients_tree.heading('quantité', text='Quantité')
        
        self.ingredients_tree.column('type', width=300)
        self.ingredients_tree.column('quantité', width=100)
        
        ing_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.ingredients_tree.yview)
        self.ingredients_tree.configure(yscrollcommand=ing_scrollbar.set)
        
        # Boutons de gestion des ingrédients (à droite, verticalement) / Ingredients management buttons (right, vertically)
        ing_buttons = ttk.Frame(tree_container)
        ing_buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        ttk.Button(ing_buttons, text="➕ Ajouter", command=self._add_ingredient, width=12).pack(pady=2)
        ttk.Button(ing_buttons, text="✏️ Modifier", command=self._edit_ingredient, width=12).pack(pady=2)
        ttk.Button(ing_buttons, text="➖ Supprimer", command=self._remove_ingredient, width=12).pack(pady=2)
        
        self.ingredients_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ing_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        # === Résultat (Output) === / === Result (Output) ===
        output_frame = ttk.LabelFrame(self.editor_frame, text="✨ Résultat Produit", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Type produit:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_type_var = tk.StringVar()
        
        if self.available_types:
            type_names = [name for type_id, name, _ in self.available_types]
            self.output_type_combo = ttk.Combobox(output_frame, textvariable=self.output_type_var, 
                                                   values=type_names, width=35, font=('Arial', 9))
            # Définir "Item par défaut" comme valeur par défaut / Set "Default Item" as default value
            for type_id, name, _ in self.available_types:
                if type_id == "default":
                    self.output_type_var.set(name)
                    break
        else:
            self.output_type_combo = ttk.Entry(output_frame, textvariable=self.output_type_var, 
                                               width=35, font=('Arial', 9))
        self.output_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(output_frame, text="Quantité produite:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_quantity_var = tk.IntVar(value=1)
        self.output_quantity_spin = ttk.Spinbox(output_frame, from_=1, to=100, 
                                                 textvariable=self.output_quantity_var, width=10)
        self.output_quantity_spin.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        output_frame.columnconfigure(1, weight=1)
        
        # Désactiver les widgets par défaut / Disable widgets by default
        self._set_editor_enabled(False)
    
    def _set_editor_enabled(self, enabled: bool):
        """Active ou désactive l'éditeur / Enables or disables the editor"""
        self.editor_enabled = enabled
        state = tk.NORMAL if enabled else tk.DISABLED
        
        self.name_entry.config(state=state)
        self.ingredients_tree.config(selectmode=tk.BROWSE if enabled else tk.NONE)
        self.output_type_combo.config(state='readonly' if enabled else tk.DISABLED)
        self.output_quantity_spin.config(state=state)
    
    def _refresh_combinations_list(self):
        """Rafraîchit la liste des combinaisons / Refreshes the combinations list"""
        self.combinations_listbox.delete(0, tk.END)
        
        for i, combination in enumerate(self.node.combination_set.combinations):
            # Format: "Nom (X composants → Y items)" / Format: "Name (X components → Y items)"
            num_ingredients = len(combination.ingredients)
            output_qty = combination.output_quantity
            display_text = f"{combination.name} ({num_ingredients} composants → {output_qty} items)"
            
            self.combinations_listbox.insert(tk.END, display_text)
            
            # Sélectionner la combinaison courante si elle existe / Select current combination if it exists
            if self.current_combination and combination.combination_id == self.current_combination.combination_id:
                self.combinations_listbox.selection_set(i)
    
    def _on_combination_selected(self, event):
        """Appelé quand une combinaison est sélectionnée / Called when a combination is selected"""
        selection = self.combinations_listbox.curselection()
        if not selection:
            # Ne pas désactiver si on a déjà une combinaison courante / Don't disable if we already have a current combination
            # (évite la désactivation lors de l'ouverture de dialogues modaux) / (avoids deactivation when opening modal dialogs)
            if not self.current_combination:
                self._set_editor_enabled(False)
            return
        
        idx = selection[0]
        next_combination = self.node.combination_set.combinations[idx]
        
        # Si on change de combinaison, sauvegarder l'ancienne d'abord / If changing combination, save the old one first
        if self.current_combination and self.current_combination != next_combination and self.editor_enabled:
            if not self._save_current_combination():
                # Si la sauvegarde échoue, annuler le changement de sélection / If save fails, cancel selection change
                # Retrouver l'index de la combinaison courante et la resélectionner / Find current combination index and reselect it
                for i, combo in enumerate(self.node.combination_set.combinations):
                    if combo.combination_id == self.current_combination.combination_id:
                        self.combinations_listbox.selection_clear(0, tk.END)
                        self.combinations_listbox.selection_set(i)
                        return
        
        self.current_combination = next_combination
        
        # Charger les données dans l'éditeur / Load data into editor
        self._load_combination_to_editor()
        self._set_editor_enabled(True)
    
    def _load_combination_to_editor(self):
        """Charge la combinaison courante dans l'éditeur / Loads current combination into editor"""
        if not self.current_combination:
            return
        
        # Nom / Name
        self.name_var.set(self.current_combination.name)
        
        # Ingrédients / Ingredients
        self.ingredients_tree.delete(*self.ingredients_tree.get_children())
        for ingredient in self.current_combination.ingredients:
            # Trouver le nom du type / Find type name
            type_name = ingredient.type_id
            for type_id, name, _ in self.available_types:
                if type_id == ingredient.type_id:
                    type_name = name
                    break
            
            self.ingredients_tree.insert('', tk.END, values=(
                type_name,
                ingredient.quantity
            ), tags=(ingredient.type_id,))
        
        # Output / Sortie
        output_type_display = self.current_combination.output_type_id
        for type_id, name, _ in self.available_types:
            if type_id == self.current_combination.output_type_id:
                output_type_display = name
                break
        
        self.output_type_var.set(output_type_display)
        self.output_quantity_var.set(self.current_combination.output_quantity)
    
    def _save_current_combination(self):
        """Sauvegarde les modifications de la combinaison courante / Saves current combination modifications"""
        if not self.current_combination or not self.editor_enabled:
            return True
        
        # Validation / Validation
        if not self.name_var.get():
            messagebox.showerror(tr('error'), tr('combination_name_required'))
            return False
        
        if not self.output_type_var.get():
            messagebox.showerror(tr('error'), tr('output_type_required'))
            return False
        
        # Récupérer les ingrédients / Get ingredients
        ingredients = []
        for item in self.ingredients_tree.get_children():
            values = self.ingredients_tree.item(item, 'values')
            tags = self.ingredients_tree.item(item, 'tags')
            
            type_id = tags[0] if tags else ""
            quantity = int(values[1])
            
            ingredients.append(CombinationIngredient(
                type_id=type_id,
                quantity=quantity
            ))
        
        if not ingredients:
            messagebox.showerror(tr('error'), tr('combination_needs_component'))
            return False
        
        # Récupérer le type_id depuis le nom / Get type_id from name
        output_type_name = self.output_type_var.get()
        output_type = self.name_to_type_id.get(output_type_name, output_type_name)
        
        # Mettre à jour la combinaison / Update the combination
        self.current_combination.name = self.name_var.get()
        self.current_combination.ingredients = ingredients
        self.current_combination.output_type_id = output_type
        self.current_combination.output_quantity = self.output_quantity_var.get()
        
        return True
    
    def _new_combination(self):
        """Crée une nouvelle combinaison / Creates a new combination"""
        # Sauvegarder la combinaison courante si modifiée / Save current combination if modified
        if self.current_combination and self.editor_enabled:
            if not self._save_current_combination():
                return
        
        # Créer nouvelle combinaison avec type par défaut / Create new combination with default type
        default_type_id = "default"
        # Vérifier si le type 'default' existe dans les types disponibles / Check if 'default' type exists in available types
        for type_id, name, _ in self.available_types:
            if type_id == "default":
                default_type_id = type_id
                break
        
        new_combination = Combination(
            combination_id=f"combination_{len(self.node.combination_set.combinations)}_{id(self)}",
            name="Nouvelle Combinaison",
            ingredients=[],
            output_type_id=default_type_id,
            output_quantity=1
        )
        
        self.node.combination_set.add_combination(new_combination)
        self.current_combination = new_combination
        
        # Rafraîchir et sélectionner la nouvelle / Refresh and select the new one
        self._refresh_combinations_list()
        self.combinations_listbox.selection_clear(0, tk.END)
        self.combinations_listbox.selection_set(tk.END)
        self.combinations_listbox.see(tk.END)
        
        self._load_combination_to_editor()
        self._set_editor_enabled(True)
    
    def _delete_combination(self):
        """Supprime la combinaison sélectionnée / Deletes the selected combination"""
        selection = self.combinations_listbox.curselection()
        if not selection:
            messagebox.showwarning(tr('warning'), tr('select_combination_delete'))
            return
        
        if messagebox.askyesno(tr('confirmation'), tr('confirm_delete_combination')):
            idx = selection[0]
            combination = self.node.combination_set.combinations[idx]
            self.node.combination_set.remove_combination(combination.combination_id)
            
            self.current_combination = None
            self._set_editor_enabled(False)
            self._refresh_combinations_list()
    
    def _duplicate_combination(self):
        """Duplique la combinaison sélectionnée / Duplicates the selected combination"""
        selection = self.combinations_listbox.curselection()
        if not selection:
            messagebox.showwarning(tr('warning'), tr('select_combination_duplicate'))
            return
        
        idx = selection[0]
        original = self.node.combination_set.combinations[idx]
        
        # Créer copie / Create copy
        duplicate = Combination(
            combination_id=f"combination_{len(self.node.combination_set.combinations)}_{id(self)}",
            name=f"{original.name} (Copie)",
            ingredients=[CombinationIngredient(ing.type_id, ing.quantity) for ing in original.ingredients],
            output_type_id=original.output_type_id,
            output_quantity=original.output_quantity
        )
        
        self.node.combination_set.add_combination(duplicate)
        self.current_combination = duplicate
        
        self._refresh_combinations_list()
        self.combinations_listbox.selection_clear(0, tk.END)
        self.combinations_listbox.selection_set(tk.END)
        self.combinations_listbox.see(tk.END)
        
        self._load_combination_to_editor()
        self._set_editor_enabled(True)
    
    def _add_ingredient(self):
        """Ajoute un nouvel ingrédient / Adds a new ingredient"""
        if not self.editor_enabled:
            return
        
        if not self.available_types:
            messagebox.showwarning(tr('warning'), tr('no_upstream_item_types'))
            return
        
        # Mini-dialogue pour ajouter un ingrédient / Mini-dialog to add an ingredient
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Ajouter un Composant")
        dialog.geometry("400x150")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # Centrer / Center
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Type d'item:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W, pady=10)
        type_var = tk.StringVar()
        type_names = [name for type_id, name, _ in self.available_types]
        type_combo = ttk.Combobox(frame, textvariable=type_var, values=type_names, width=30)
        type_combo.grid(row=0, column=1, padx=10, pady=10)
        if type_names:
            type_combo.current(0)
        
        ttk.Label(frame, text="Quantité:", font=('Arial', 9)).grid(row=1, column=0, sticky=tk.W, pady=10)
        quantity_var = tk.IntVar(value=1)
        ttk.Spinbox(frame, from_=1, to=100, textvariable=quantity_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)
        
        def on_add():
            # Extraire le type_id depuis le nom / Extract type_id from name
            selected_name = type_var.get()
            if not selected_name:
                messagebox.showwarning(tr('warning'), tr('please_select_item_type_combo'))
                return
            
            type_id = self.name_to_type_id.get(selected_name, selected_name)
            
            self.ingredients_tree.insert('', tk.END, values=(
                selected_name,
                quantity_var.get()
            ), tags=(type_id,))
            
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Ajouter", command=on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Attendre que le dialogue soit fermé / Wait for dialog to close
        dialog.wait_window()
    
    def _edit_ingredient(self):
        """Modifie l'ingrédient sélectionné / Modifies the selected ingredient"""
        if not self.editor_enabled:
            return
        
        selection = self.ingredients_tree.selection()
        if not selection:
            messagebox.showwarning(tr('warning'), tr('select_component_edit'))
            return
        
        item = selection[0]
        values = self.ingredients_tree.item(item, 'values')
        tags = self.ingredients_tree.item(item, 'tags')
        
        current_type_id = tags[0] if tags else ""
        current_quantity = int(values[1])
        
        # Mini-dialogue pour modifier / Mini-dialog to modify
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Modifier le Composant")
        dialog.geometry("400x150")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # Centrer / Center
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Type d'item:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W, pady=10)
        type_var = tk.StringVar()
        type_names = [name for type_id, name, _ in self.available_types]
        type_combo = ttk.Combobox(frame, textvariable=type_var, values=type_names, width=30)
        type_combo.grid(row=0, column=1, padx=10, pady=10)
        
        # Sélectionner le type actuel / Select current type
        for i, (type_id, name, _) in enumerate(self.available_types):
            if type_id == current_type_id:
                type_combo.current(i)
                break
        
        ttk.Label(frame, text="Quantité:", font=('Arial', 9)).grid(row=1, column=0, sticky=tk.W, pady=10)
        quantity_var = tk.IntVar(value=current_quantity)
        ttk.Spinbox(frame, from_=1, to=100, textvariable=quantity_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)
        
        def on_save():
            # Extraire le type_id depuis le nom / Extract type_id from name
            selected_name = type_var.get()
            type_id = self.name_to_type_id.get(selected_name, selected_name)
            
            self.ingredients_tree.item(item, values=(
                selected_name,
                quantity_var.get()
            ), tags=(type_id,))
            
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Enregistrer", command=on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Annuler", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Attendre que le dialogue soit fermé / Wait for dialog to close
        dialog.wait_window()
    
    def _remove_ingredient(self):
        """Supprime l'ingrédient sélectionné / Removes the selected ingredient"""
        if not self.editor_enabled:
            return
        
        selection = self.ingredients_tree.selection()
        if not selection:
            messagebox.showwarning(tr('warning'), tr('select_component_delete'))
            return
        
        for item in selection:
            self.ingredients_tree.delete(item)
    
    def _save_and_close(self):
        """Sauvegarde toutes les modifications et ferme / Saves all modifications and closes"""
        # Sauvegarder la combinaison courante / Save current combination
        if self.current_combination and self.editor_enabled:
            if not self._save_current_combination():
                return
        
        # Rafraîchir une dernière fois pour confirmer / Refresh one last time to confirm
        self._refresh_combinations_list()
        
        self.dialog.destroy()
