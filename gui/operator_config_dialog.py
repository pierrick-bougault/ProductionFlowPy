"""Dialogue de configuration d'un opérateur / Operator configuration dialog"""
import tkinter as tk
from tkinter import ttk, colorchooser
from models.operator import Operator, DistributionType
from gui.translations import tr

class OperatorConfigDialog:
    """Dialogue pour configurer un opérateur / Dialog to configure an operator"""
    
    def __init__(self, parent, flow_model, operator=None):
        self.result = None
        self.flow_model = flow_model
        self.operator = operator  # None si création, sinon édition / None if creation, else editing
        
        # Créer la fenêtre de dialogue / Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(tr('operator_config_title') if operator else tr('new_operator_title'))
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenêtre / Center window
        dialog_width = 700
        dialog_height = 550  # Hauteur réduite après suppression de la section temps de traitement / Reduced height after removing processing time section
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Permettre le redimensionnement / Allow resizing
        self.dialog.resizable(True, True)
        
        self._create_widgets()
        
        # Bind touche Entrée au bouton OK et Échap au bouton Annuler / Bind Enter to OK and Escape to Cancel
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # Activer automatiquement la fenêtre / Automatically focus window
        self.dialog.focus_force()
        
        # Attendre la fermeture du dialogue / Wait for dialog close
        self.dialog.wait_window()
    
    def _create_widgets(self):
        """Crée les widgets du dialogue / Create dialog widgets"""
        # Créer un canvas avec scrollbar pour tout le contenu / Create canvas with scrollbar for all content
        canvas = tk.Canvas(self.dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Stocker les références pour cleanup / Store references for cleanup
        self.canvas = canvas
        self.mousewheel_bound = False
        
        # Bind mousewheel (bind au lieu de bind_all pour éviter les conflits) / Bind mousewheel (bind instead of bind_all to avoid conflicts)
        def on_mousewheel(event):
            # Vérifier que le canvas existe toujours / Verify canvas still exists
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def on_enter(event):
            if canvas.winfo_exists():
                canvas.bind_all('<MouseWheel>', on_mousewheel)
                self.mousewheel_bound = True
        
        def on_leave(event):
            if self.mousewheel_bound:
                canvas.unbind_all('<MouseWheel>')
                self.mousewheel_bound = False
        
        canvas.bind('<Enter>', on_enter)
        canvas.bind('<Leave>', on_leave)
        
        # Unbind lors de la destruction de la fenêtre / Unbind on window destruction
        def on_destroy(event=None):
            if self.mousewheel_bound:
                try:
                    canvas.unbind_all('<MouseWheel>')
                    self.mousewheel_bound = False
                except:
                    pass
        
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: (on_destroy(), self._on_cancel()))
        self.dialog.bind('<Destroy>', on_destroy)
        
        # Frame principal dans le canvas scrollable / Main frame in scrollable canvas
        main_frame = ttk.Frame(scrollable_frame, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nom / Name
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame, text=tr('operator_name_label')).pack(side=tk.LEFT, padx=5)
        self.name_var = tk.StringVar(value=self.operator.name if self.operator else tr('operator_default_name'))
        ttk.Entry(name_frame, textvariable=self.name_var, width=30).pack(side=tk.LEFT, padx=5)
        
        # Couleur / Color
        color_frame = ttk.Frame(main_frame)
        color_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(color_frame, text=tr('color_label')).pack(side=tk.LEFT, padx=5)
        self.color = self.operator.color if self.operator else "#FF9800"
        self.color_button = tk.Button(
            color_frame,
            text=tr('choose_btn'),
            bg=self.color,
            width=10,
            command=self._choose_color
        )
        self.color_button.pack(side=tk.LEFT, padx=5)
        
        # Liste des machines disponibles et ordre de visite / List of available machines and visit order
        machines_frame = ttk.LabelFrame(main_frame, text=tr('assigned_machines_section'), padding=10)
        machines_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Frame horizontal avec deux listes / Horizontal frame with two lists
        lists_frame = ttk.Frame(machines_frame)
        lists_frame.pack(fill=tk.BOTH, expand=True)
        
        # Liste gauche : Machines disponibles / Left list: Available machines
        available_frame = ttk.LabelFrame(lists_frame, text=tr('available_label'), padding=5)
        available_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        avail_scrollbar = ttk.Scrollbar(available_frame)
        avail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.available_listbox = tk.Listbox(
            available_frame,
            selectmode=tk.SINGLE,
            yscrollcommand=avail_scrollbar.set,
            height=8
        )
        self.available_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        avail_scrollbar.config(command=self.available_listbox.yview)
        
        # Boutons au milieu / Buttons in the middle
        buttons_frame = ttk.Frame(lists_frame)
        buttons_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text=tr('add_arrow_btn'), command=self._add_machine, width=12).pack(pady=5)
        ttk.Button(buttons_frame, text=tr('remove_arrow_btn'), command=self._remove_machine, width=12).pack(pady=5)
        ttk.Button(buttons_frame, text=tr('move_up_btn'), command=self._move_up, width=12).pack(pady=5)
        ttk.Button(buttons_frame, text=tr('move_down_btn'), command=self._move_down, width=12).pack(pady=5)
        
        # Liste droite : Machines assignées (dans l'ordre) / Right list: Assigned machines (in order)
        assigned_frame = ttk.LabelFrame(lists_frame, text=tr('assigned_order_label'), padding=5)
        assigned_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        assigned_scrollbar = ttk.Scrollbar(assigned_frame)
        assigned_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.assigned_listbox = tk.Listbox(
            assigned_frame,
            selectmode=tk.SINGLE,
            yscrollcommand=assigned_scrollbar.set,
            height=8
        )
        self.assigned_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        assigned_scrollbar.config(command=self.assigned_listbox.yview)
        
        # Remplir avec les nœuds de traitement disponibles / Fill with available processing nodes
        from models.flow_model import NodeType
        self.machine_ids = []
        self.machine_names = {}
        
        for node_id, node in self.flow_model.nodes.items():
            # Exclure les sources - un opérateur ne contrôle que les machines de traitement
            # Exclude sources - operator only controls processing machines
            if node.node_type == NodeType.CUSTOM and not node.is_source:
                self.machine_ids.append(node_id)
                self.machine_names[node_id] = f"{node.name} ({node_id})"
        
        # Remplir les listes selon l'état de l'opérateur / Fill lists according to operator state
        if self.operator and self.operator.assigned_machines:
            # Machines assignées dans l'ordre / Assigned machines in order
            for machine_id in self.operator.assigned_machines:
                if machine_id in self.machine_names:
                    self.assigned_listbox.insert(tk.END, self.machine_names[machine_id])
            
            # Machines disponibles (non assignées) / Available machines (not assigned)
            for machine_id in self.machine_ids:
                if machine_id not in self.operator.assigned_machines:
                    self.available_listbox.insert(tk.END, self.machine_names[machine_id])
        else:
            # Toutes les machines sont disponibles / All machines are available
            for machine_id in self.machine_ids:
                self.available_listbox.insert(tk.END, self.machine_names[machine_id])
        
        # Bouton pour configurer les temps de trajet / Button to configure travel times
        travel_btn_frame = ttk.Frame(main_frame)
        travel_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            travel_btn_frame,
            text=tr('configure_travel_times_btn'),
            command=self._configure_travel_times
        ).pack(side=tk.LEFT, padx=5)
        
        # Info sur les temps de trajet / Info about travel times
        self.travel_info_label = ttk.Label(
            travel_btn_frame,
            text=tr('no_time_configured'),
            foreground="blue"
        )
        self.travel_info_label.pack(side=tk.LEFT, padx=5)
        
        if self.operator:
            count = len(self.operator.travel_times)
            self.travel_info_label.config(text=tr('routes_configured').format(count=count))
        
        # Note informative sur les temps de traitement / Informative note about processing times
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(
            info_frame,
            text=tr('operator_processing_info'),
            font=("Arial", 9, "italic"),
            foreground="#0066CC",
            wraplength=650,
            justify=tk.LEFT
        ).pack(pady=5)
        
        # Boutons OK/Annuler / OK/Cancel buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=20)
        
        ttk.Button(button_frame, text=tr('ok'), command=self._on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=tr('cancel_btn'), command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        # Bouton Supprimer (seulement si on édite un opérateur existant) / Delete button (only if editing existing operator)
        if self.operator:
            ttk.Button(button_frame, text=tr('delete_operator_btn'), command=self._on_delete, width=12).pack(side=tk.LEFT, padx=5)
    
    def _add_machine(self):
        """Ajoute une machine à la liste assignée / Add machine to assigned list"""
        selection = self.available_listbox.curselection()
        if selection:
            index = selection[0]
            machine_name = self.available_listbox.get(index)
            self.assigned_listbox.insert(tk.END, machine_name)
            self.available_listbox.delete(index)
    
    def _remove_machine(self):
        """Retire une machine de la liste assignée / Remove machine from assigned list"""
        selection = self.assigned_listbox.curselection()
        if selection:
            index = selection[0]
            machine_name = self.assigned_listbox.get(index)
            self.available_listbox.insert(tk.END, machine_name)
            self.assigned_listbox.delete(index)
    
    def _move_up(self):
        """Déplace une machine vers le haut dans l'ordre / Move machine up in order"""
        selection = self.assigned_listbox.curselection()
        if selection and selection[0] > 0:
            index = selection[0]
            machine_name = self.assigned_listbox.get(index)
            self.assigned_listbox.delete(index)
            self.assigned_listbox.insert(index - 1, machine_name)
            self.assigned_listbox.selection_set(index - 1)
    
    def _move_down(self):
        """Déplace une machine vers le bas dans l'ordre / Move machine down in order"""
        selection = self.assigned_listbox.curselection()
        if selection and selection[0] < self.assigned_listbox.size() - 1:
            index = selection[0]
            machine_name = self.assigned_listbox.get(index)
            self.assigned_listbox.delete(index)
            self.assigned_listbox.insert(index + 1, machine_name)
            self.assigned_listbox.selection_set(index + 1)
    
    def _choose_color(self):
        """Ouvre le sélecteur de couleur / Open color picker"""
        # Relâcher le grab pour permettre à la fenêtre de couleur de fonctionner
        self.grab_release()
        color = colorchooser.askcolor(initialcolor=self.color, title=tr('choose_color_dialog_title'))
        # Reprendre le grab
        self.grab_set()
        if color[1]:
            self.color = color[1]
            self.color_button.config(bg=self.color)
    
    def _configure_travel_times(self):
        """Ouvre le dialogue de configuration des temps de trajet / Open travel time configuration dialog"""
        # Récupérer les machines assignées / Get assigned machines
        if self.assigned_listbox.size() < 2:
            from tkinter import messagebox
            messagebox.showwarning(
                tr('insufficient_machines'),
                tr('assign_at_least_2_machines')
            )
            return
        
        # Extraire les IDs des machines assignées dans l'ordre / Extract assigned machine IDs in order
        selected_machines = []
        for i in range(self.assigned_listbox.size()):
            machine_name = self.assigned_listbox.get(i)
            # Extraire l'ID entre parenthèses / Extract ID between parentheses
            machine_id = machine_name.split('(')[1].rstrip(')')
            selected_machines.append(machine_id)
        
        # Créer un opérateur temporaire si nouveau / Create temporary operator if new
        temp_operator = self.operator if self.operator else Operator("temp", self.name_var.get())
        
        # Ouvrir le dialogue de configuration des trajets / Open travel configuration dialog
        from gui.travel_time_config_dialog import TravelTimeConfigDialog
        dialog = TravelTimeConfigDialog(self.dialog, self.flow_model, temp_operator, selected_machines)
        
        if dialog.result:
            # Mettre à jour l'info / Update info
            count = len(dialog.result)
            self.travel_info_label.config(text=tr('routes_configured').format(count=count))
            
            # Sauvegarder les temps / Save times
            if not self.operator:
                self.operator = temp_operator
            self.operator.travel_times = dialog.result
    
    def _on_ok(self):
        """Valide et ferme le dialogue / Validate and close dialog"""
        name = self.name_var.get().strip()
        if not name:
            from tkinter import messagebox
            messagebox.showwarning(tr('name_required'), tr('assign_at_least_1_machine'))
            return
        
        # Récupérer les machines assignées dans l'ordre / Get assigned machines in order
        if self.assigned_listbox.size() == 0:
            from tkinter import messagebox
            messagebox.showwarning(
                tr('machines_required'),
                tr('assign_at_least_1_machine')
            )
            return
        
        # Extraire les IDs des machines assignées dans l'ordre / Extract assigned machine IDs in order
        selected_machines = []
        for i in range(self.assigned_listbox.size()):
            machine_name = self.assigned_listbox.get(i)
            # Extraire l'ID entre parenthèses / Extract ID from parentheses
            machine_id = machine_name.split('(')[1].rstrip(')')
            selected_machines.append(machine_id)
        
        self.result = {
            'name': name,
            'color': self.color,
            'assigned_machines': selected_machines,
            'travel_times': self.operator.travel_times if self.operator else {}
        }
        
        # Unbind la molette de souris avant de fermer / Unbind mousewheel before closing
        if self.mousewheel_bound:
            try:
                self.canvas.unbind_all('<MouseWheel>')
                self.mousewheel_bound = False
            except:
                pass
        
        self.dialog.destroy()
    
    def _on_delete(self):
        """Supprime l'opérateur / Delete operator"""
        self.result = {'delete': True}
        
        # Unbind la molette de souris avant de fermer / Unbind mousewheel before closing
        if self.mousewheel_bound:
            try:
                self.canvas.unbind_all('<MouseWheel>')
                self.mousewheel_bound = False
            except:
                pass
        
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Annule et ferme le dialogue / Cancel and close dialog"""
        # Unbind la molette de souris avant de fermer / Unbind mousewheel before closing
        if self.mousewheel_bound:
            try:
                self.canvas.unbind_all('<MouseWheel>')
                self.mousewheel_bound = False
            except:
                pass
        
        self.dialog.destroy()
