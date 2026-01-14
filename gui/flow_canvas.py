"""Canvas interactif pour dessiner et éditer le flux / Interactive canvas for drawing and editing flow"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, List
import time
from models.flow_model import FlowModel, FlowNode, Connection, NodeType
from models.time_converter import TimeUnit, TimeConverter

class FlowCanvas(tk.Canvas):
    """Canvas pour dessiner et manipuler le flux de production / Canvas for drawing and manipulating production flow"""
    
    # Constantes pour le dessin / Drawing constants
    NODE_WIDTH = 120
    NODE_HEIGHT = 60
    BUFFER_INDICATOR_SIZE = 15
    
    # Couleurs / Colors
    NODE_COLOR = "#E8F4F8"
    NODE_BORDER = "#2C5F7F"
    SELECTED_COLOR = "#FFF4B3"
    BUFFER_COLOR = "#FFD700"
    CONNECTION_COLOR = "#2C5F7F"
    
    def __init__(self, parent, flow_model: FlowModel, app_config=None):
        super().__init__(parent, bg="white", highlightthickness=1, highlightbackground="#cccccc")
        self.flow_model = flow_model
        
        # Configuration de l'application / Application configuration
        self.app_config = app_config
        if self.app_config is None:
            # Valeurs par défaut si aucune config n'est fournie / Default values if no config provided
            class DefaultConfig:
                DEBUG_MODE = False
                OPERATOR_MOVEMENT_THRESHOLD = 2.0
                NODE_POSITION_CACHE_VALIDITY_MS = 50
            self.app_config = DefaultConfig()
        
        # État de l'éditeur / Editor state
        self.mode = "select"  # "select", "add_node", "add_connection"
        self.selected_node_id: Optional[str] = None
        self.selected_connection_id: Optional[str] = None
        self.selected_probe_id: Optional[str] = None
        self.selected_annotation_id: Optional[str] = None
        self.selected_operator_id: Optional[str] = None
        self.dragging_node_id: Optional[str] = None
        self.dragging_probe_id: Optional[str] = None  # Pour le drag des pipettes / For probe dragging
        self.dragging_operator_id: Optional[str] = None  # Pour le drag des opérateurs / For operator dragging
        self.drag_start_pos: Optional[Tuple[float, float]] = None
        self.connection_start_node_id: Optional[str] = None
        self.temp_connection_line: Optional[int] = None
        
        # Sélection multiple (Ctrl + clic + glisser) / Multiple selection (Ctrl + click + drag)
        self.multi_selection_active = False  # True quand on dessine le rectangle de sélection / True when drawing selection rectangle
        self.multi_selection_start: Optional[Tuple[float, float]] = None  # Point de départ / Start point
        self.multi_selection_rect: Optional[int] = None  # Rectangle de sélection temporaire / Temporary selection rectangle
        self.selected_nodes: set = set()  # Ensemble des node_ids sélectionnés / Set of selected node_ids
        self.selected_operators: set = set()  # Ensemble des operator_ids sélectionnés / Set of selected operator_ids
        self.selected_probes: set = set()  # Ensemble des probe_ids sélectionnés / Set of selected probe_ids
        self.selected_annotations: set = set()  # Ensemble des annotation_ids sélectionnés / Set of selected annotation_ids
        self.multi_drag_active = False  # True quand on déplace une sélection multiple / True when moving multiple selection
        
        # Mode placement d'import (éléments suivent le curseur jusqu'au clic) / Import placement mode (elements follow cursor until click)
        self.import_placement_mode = False
        self.import_placement_offset: Optional[Tuple[float, float]] = None
        self.import_last_mouse_pos: Optional[Tuple[float, float]] = None  # Offset initial pour centrer / Initial offset to center
        
        # Mapping entre IDs et objets canvas / Mapping between IDs and canvas objects
        self.node_canvas_objects: dict = {}  # node_id -> {rect, text, buffer_indicators}
        self.connection_canvas_objects: dict = {}  # connection_id -> {line, arrow, buffer_indicator}
        self.animated_items: dict = {}  # item_id -> canvas_object (points rouges / red dots)
        self.probe_canvas_objects: dict = {}  # probe_id -> canvas_object (icône pipette / probe icon)
        self.annotation_canvas_objects: dict = {}  # annotation_id -> {rect, text}
        self.operator_canvas_objects: dict = {}  # operator_id -> {circle, text}
        self.operator_animations: dict = {}  # operator_id -> animation state
        
        # Cache des positions des nœuds (pour performances) / Node position cache (for performance)
        # Format: {node_id: (x, y, timestamp)}
        self._node_positions_cache: dict = {}
        self._cache_validity_seconds = self.app_config.NODE_POSITION_CACHE_VALIDITY_MS / 1000.0
        
        # Cache des couleurs d'items par type (OPTIMISATION) / Item colors cache by type (OPTIMIZATION)
        # Format: {item_type_id: color}
        self._item_type_colors: dict = {}
        self._rebuild_item_type_colors_cache()
        
        # Variables pour la création d'annotations / Variables for annotation creation
        self.annotation_start_pos: Optional[Tuple[float, float]] = None
        self.temp_annotation_rect: Optional[int] = None
        
        # Paramètres d'annotation (VARIABLES CONFIGURABLES) / Annotation parameters (CONFIGURABLE VARIABLES)
        self.annotation_line_width = 2  # Épaisseur des lignes du rectangle / Rectangle line thickness
        self.annotation_dash_pattern = (8, 4)  # Motif de pointillés (8 pixels trait, 4 pixels espace) / Dash pattern (8px dash, 4px space)
        
        # Callback pour notifier les changements de pipettes / Callback to notify probe changes
        self.on_probe_added = None
        self.on_probe_removed = None
        
        # Zoom
        self.zoom_level = 1.0
        self.zoom_min = 0.3
        self.zoom_max = 3.0
        
        # Pan (glissement du canvas) / Pan (canvas sliding)
        self.panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        
        # Bindings / Event bindings
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Double-Button-1>", self.on_double_click)
        self.bind("<Button-3>", self.on_right_click)  # Clic droit / Right click
        self.bind("<Delete>", self.on_delete_key)  # Touche Suppr / Delete key
        self.bind("<BackSpace>", self.on_delete_key)  # Touche Retour arrière / Backspace key
        self.bind("<Key>", self.on_key_press)  # Pour déboguer / For debugging
        self.bind("<MouseWheel>", self.on_mouse_wheel)  # Molette pour zoom / Mousewheel for zoom
        
        # Focus pour recevoir les événements clavier / Focus to receive keyboard events
        self.focus_set()
    
    def set_mode(self, mode: str):
        """Change le mode d'édition / Change editing mode"""
        # print(f"[CANVAS] set_mode appelé: {self.mode} → {mode}")
        # print(f"[CANVAS]   Nœuds dans le modèle: {list(self.flow_model.nodes.keys())}")
        
        self.mode = mode
        # Marquer l'ancien nœud sélectionné comme ayant changé (OPTIMISATION) / Mark old selected node as changed (OPTIMIZATION)
        if self.selected_node_id:
            old_node = self.flow_model.get_node(self.selected_node_id)
            if old_node:
                old_node._visual_changed = True
        self.selected_node_id = None
        self.connection_start_node_id = None
        self.dragging_node_id = None  # Réinitialiser l'état de drag / Reset drag state
        self.dragging_probe_id = None  # Réinitialiser le drag des pipettes / Reset probe drag
        self.drag_start_pos = None
        if self.temp_connection_line:
            self.delete(self.temp_connection_line)
            self.temp_connection_line = None
        
        # print(f"[CANVAS]   Mise à jour de la sélection visuelle")
        # Mettre à jour uniquement la sélection visuelle au lieu de tout redessiner / Update only visual selection instead of redrawing everything
        self._update_selection_visual()
    
    def get_selected_node(self):
        """Retourne l'ID du nœud actuellement sélectionné, ou None / Return the currently selected node ID, or None"""
        return self.selected_node_id
    
    def add_node_at_position(self, x: float, y: float, node_type: NodeType, name: str):
        """Ajoute un nouveau nœud à la position spécifiée / Add a new node at specified position"""
        # print(f"[CANVAS] add_node_at_position appelé: type={node_type}, name={name}, pos=({x}, {y})")
        # print(f"[CANVAS]   Nœuds avant ajout: {list(self.flow_model.nodes.keys())}")
        
        # Convertir les coordonnées canvas en coordonnées modèle / Convert canvas coordinates to model coordinates
        # Les coordonnées cliquées sont en pixels canvas, il faut diviser par le zoom / Clicked coordinates are in canvas pixels, divide by zoom
        model_x = x / self.zoom_level
        model_y = y / self.zoom_level
        # print(f"[CANVAS]   Conversion: canvas=({x:.2f}, {y:.2f}) → modèle=({model_x:.2f}, {model_y:.2f}), zoom={self.zoom_level:.3f}")
        
        node_id = self.flow_model.generate_node_id()
        # print(f"[CANVAS]   Nouvel ID généré: {node_id}")
        
        # Créer le nœud avec les coordonnées modèle / Create node with model coordinates
        node = FlowNode(node_id, node_type, name, model_x, model_y)
        node.set_processing_time(1.0, self.flow_model.current_time_unit)
        self.flow_model.add_node(node)
        
        # print(f"[CANVAS]   Nœuds après ajout: {list(self.flow_model.nodes.keys())}")
        # print(f"[CANVAS]   Dessin du nouveau nœud uniquement")
        
        # Dessiner uniquement le nouveau nœud au lieu de tout redessiner / Draw only new node instead of redrawing everything
        self.draw_node(node)
        
        # Si c'est une source, rebuild le cache des couleurs d'items / If it's a source, rebuild item colors cache
        if node.is_source:
            self._rebuild_item_type_colors_cache()
        
        # Appliquer le zoom au nouveau nœud / Apply zoom to new node
        for obj in self.node_canvas_objects[node.node_id].values():
            if obj:
                self.scale(obj, 0, 0, self.zoom_level, self.zoom_level)
        
        # Mettre à jour la scrollregion avec marge étendue pour panning libre / Update scrollregion with extended margin for free panning
        bbox = self.bbox("all")
        if bbox:
            margin = 5000
            extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                           bbox[2] + margin, bbox[3] + margin)
            self.configure(scrollregion=extended_bbox)
        else:
            self.configure(scrollregion=(-5000, -5000, 5000, 5000))
    
    def redraw_node(self, node: FlowNode):
        """Redessine un nœud individuel en préservant sa position canvas / Redraw individual node preserving its canvas position"""
        # print(f"\n[REDRAW_NODE] Début redraw pour {node.node_id} ('{node.name}'), zoom={self.zoom_level:.3f}")
        
        # Invalider le cache pour ce nœud car on va le redessiner / Invalidate cache for this node since we'll redraw it
        self._invalidate_node_position_cache(node.node_id)
        
        # ÉTAPE 1: Récupérer les coordonnées canvas actuelles (après zoom) du rectangle / STEP 1: Get current canvas coordinates (after zoom) of rectangle
        canvas_coords = None
        if node.node_id in self.node_canvas_objects and 'rect' in self.node_canvas_objects[node.node_id]:
            rect = self.node_canvas_objects[node.node_id]['rect']
            coords = self.coords(rect)
            if coords:
                # Coordonnées canvas du rectangle: [x1, y1, x2, y2] / Canvas coordinates of rectangle: [x1, y1, x2, y2]
                canvas_coords = coords
                canvas_center_x = (coords[0] + coords[2]) / 2
                canvas_center_y = (coords[1] + coords[3]) / 2
                # print(f"  [1] Position canvas avant: center=({canvas_center_x:.2f}, {canvas_center_y:.2f})")
        
        # ÉTAPE 2: Supprimer l'ancien nœud / STEP 2: Delete old node
        if node.node_id in self.node_canvas_objects:
            for obj in self.node_canvas_objects[node.node_id].values():
                if obj:
                    self.delete(obj)
            del self.node_canvas_objects[node.node_id]
        self.delete(node.node_id)
        
        # ÉTAPE 3: Créer le nouveau nœud en coordonnées modèle / STEP 3: Create new node in model coordinates
        # print(f"  [3] Dessin du nouveau nœud en coordonnées modèle: ({node.x:.2f}, {node.y:.2f})")
        self.draw_node(node)
        
        # ÉTAPE 4: Si zoom actif, appliquer le zoom sur les nouveaux éléments pour qu'ils aient la bonne taille / STEP 4: If zoom active, apply zoom on new elements for correct size
        if self.zoom_level != 1.0 and node.node_id in self.node_canvas_objects:
            # print(f"  [4] Application du scale({self.zoom_level:.3f}) autour de (0,0)")
            # Appliquer le scale autour de (0,0) pour zoomer les éléments / Apply scale around (0,0) to zoom elements
            for obj in self.node_canvas_objects[node.node_id].values():
                if obj:
                    self.scale(obj, 0, 0, self.zoom_level, self.zoom_level)
        
        # ÉTAPE 5: Si on avait des coords canvas, ajuster la position finale / STEP 5: If we had canvas coords, adjust final position
        if canvas_coords and self.zoom_level != 1.0:
            # Obtenir les nouvelles coords du rectangle après zoom / Get new rectangle coords after zoom
            if node.node_id in self.node_canvas_objects and 'rect' in self.node_canvas_objects[node.node_id]:
                new_rect = self.node_canvas_objects[node.node_id]['rect']
                new_coords = self.coords(new_rect)
                if new_coords:
                    new_center_x = (new_coords[0] + new_coords[2]) / 2
                    new_center_y = (new_coords[1] + new_coords[3]) / 2
                    # print(f"  [5] Position canvas après redraw+scale: center=({new_center_x:.2f}, {new_center_y:.2f})")
                    
                    # Calculer le décalage / Calculate offset
                    delta_x = canvas_center_x - new_center_x
                    delta_y = canvas_center_y - new_center_y
                    # print(f"  [5] Delta nécessaire: ({delta_x:.2f}, {delta_y:.2f})")
                    
                    # Déplacer tous les éléments du nœud / Move all node elements
                    if abs(delta_x) > 0.1 or abs(delta_y) > 0.1:
                        for obj in self.node_canvas_objects[node.node_id].values():
                            if obj:
                                self.move(obj, delta_x, delta_y)
                        # print(f"  [5] Nœud déplacé de ({delta_x:.2f}, {delta_y:.2f})")
        
        # print(f"[REDRAW_NODE] Fin redraw pour {node.node_id}\n")
    
    def draw_node(self, node: FlowNode):
        """Dessine un nœud sur le canvas / Draw a node on canvas"""
        # Invalider le cache pour ce nœud car on va le dessiner / Invalidate cache for this node since we'll draw it
        self._invalidate_node_position_cache(node.node_id)
        
        # Supprimer les anciens objets canvas de ce nœud s'ils existent / Delete old canvas objects for this node if they exist
        if node.node_id in self.node_canvas_objects:
            for obj in self.node_canvas_objects[node.node_id].values():
                if obj:
                    self.delete(obj)
        # Supprimer aussi par tag / Also delete by tag
        self.delete(node.node_id)
        
        # Utiliser les coordonnées modèle (non zoomées) / Use model coordinates (not zoomed)
        # Le canvas gère automatiquement le zoom via les transformations globales / Canvas handles zoom automatically via global transformations
        x, y = node.x, node.y
        
        is_selected = node.node_id == self.selected_node_id
        is_active = getattr(node, 'is_active', False)
        
        # Couleur selon le type et l'état / Color by type and state
        if node.is_source:
            if is_active:
                fill_color = "#81C784"  # Vert vif pour source active / Bright green for active source
                border_color = "#2E7D32"  # Vert foncé / Dark green
            else:
                fill_color = "#C8E6C9" if not is_selected else self.SELECTED_COLOR  # Vert clair / Light green
                border_color = "#4CAF50"  # Vert / Green
        elif node.is_sink:
            if is_active:
                fill_color = "#C62828"  # Rouge foncé pour sink actif / Dark red for active sink
                border_color = "#B71C1C"  # Rouge très foncé / Very dark red
            else:
                fill_color = "#FFCDD2" if not is_selected else self.SELECTED_COLOR  # Rouge clair / Light red
                border_color = "#F44336"  # Rouge / Red
        elif node.is_splitter:
            if is_active:
                fill_color = "#FFB74D"  # Orange vif pour splitter actif / Bright orange for active splitter
                border_color = "#E65100"  # Orange foncé / Dark orange
            else:
                fill_color = "#FFE0B2" if not is_selected else self.SELECTED_COLOR  # Orange clair / Light orange
                border_color = "#FF9800"  # Orange
        elif node.is_merger:
            if is_active:
                fill_color = "#9575CD"  # Violet vif pour merger actif / Bright purple for active merger
                border_color = "#4A148C"  # Violet foncé / Dark purple
            else:
                fill_color = "#D1C4E9" if not is_selected else self.SELECTED_COLOR  # Violet clair / Light purple
                border_color = "#673AB7"  # Violet / Purple
        else:
            if is_active:
                fill_color = "#FFD54F"  # Jaune vif pour traitement actif / Bright yellow for active processing
                border_color = "#F57F17"  # Jaune foncé / Dark yellow
            else:
                fill_color = self.SELECTED_COLOR if is_selected else self.NODE_COLOR
                border_color = self.NODE_BORDER
        
        # Créer en taille normale (coordonnées modèle) / Create at normal size (model coordinates)
        node_width = self.NODE_WIDTH
        node_height = self.NODE_HEIGHT
        
        # Dessiner le rectangle aux coordonnées modèle / Draw rectangle at model coordinates
        rect = self.create_rectangle(
            x - node_width/2, y - node_height/2,
            x + node_width/2, y + node_height/2,
            fill=fill_color, outline=border_color, width=2,
            tags=("node", node.node_id)
        )
        
        # Dessiner le texte (taille normale) / Draw text (normal size)
        text = self.create_text(
            x, y - 10,
            text=node.name, font=("Arial", 9, "bold"),
            tags=("node", node.node_id)
        )
        
        # Afficher le temps de traitement ou l'intervalle de génération / Display processing time or generation interval
        if node.is_source:
            interval = node.get_generation_interval(self.flow_model.current_time_unit)
            time_label = f"Int: {interval:.2f} {self._get_time_unit_symbol()}"
            
            # Afficher le mode de génération pour les sources (comme pour les nœuds de traitement) / Display generation mode for sources (like for processing nodes)
            if hasattr(node, 'source_mode'):
                from models.flow_model import SourceMode
                mode_display = ""
                if node.source_mode == SourceMode.CONSTANT:
                    mode_display = "CONST"
                elif node.source_mode == SourceMode.NORMAL:
                    # Récupérer l'écart-type et le convertir dans l'unité courante / Get std dev and convert to current unit
                    std_dev = node.get_generation_std_dev(self.flow_model.current_time_unit)
                    mode_display = f"NORM(μ={interval:.1f}, σ={std_dev:.1f})"
                elif node.source_mode == SourceMode.SKEW_NORMAL:
                    # Récupérer l'écart-type et le convertir dans l'unité courante / Get std dev and convert to current unit
                    std_dev = node.get_generation_std_dev(self.flow_model.current_time_unit)
                    alpha_val = getattr(node, 'generation_skewness', 0.0)
                    mode_display = f"SKEW(ξ={interval:.1f}, ω={std_dev:.1f}, α={alpha_val:.1f})"
                
                if mode_display:
                    count_label = mode_display
                else:
                    # Compteur d'items si pas de mode spécifique / Item counter if no specific mode
                    if node.max_items_to_generate > 0:
                        count_label = f"({node.items_generated}/{node.max_items_to_generate})"
                    else:
                        count_label = f"({node.items_generated})"
            else:
                # Fallback si pas de mode défini / Fallback if no mode defined
                if node.max_items_to_generate > 0:
                    count_label = f"({node.items_generated}/{node.max_items_to_generate})"
                else:
                    count_label = f"({node.items_generated})"
        elif node.is_sink:
            time_label = "Sortie"
            count_label = f"Reçus: {node.items_received}"
        elif node.is_splitter or node.is_merger:
            # Pas d'affichage de temps pour les splitters et mergers / No time display for splitters and mergers
            time_label = ""
            count_label = ""
        else:
            time_value = node.get_processing_time(self.flow_model.current_time_unit)
            time_label = f"{time_value:.2f} {self._get_time_unit_symbol()}"
            count_label = ""
            
            # Ajouter le mode de traitement pour les nœuds de traitement / Add processing mode for processing nodes
            if hasattr(node, 'processing_time_mode'):
                from models.flow_model import ProcessingTimeMode
                mode_display = ""
                if node.processing_time_mode == ProcessingTimeMode.CONSTANT:
                    mode_display = "CONST"
                elif node.processing_time_mode == ProcessingTimeMode.NORMAL:
                    # Récupérer l'écart-type et le convertir dans l'unité courante / Get std dev and convert to current unit
                    std_dev_cs = getattr(node, 'processing_time_std_dev_cs', 0.0)
                    std_dev = TimeConverter.from_centiseconds(std_dev_cs, self.flow_model.current_time_unit)
                    mode_display = f"NORM(μ={time_value:.1f}, σ={std_dev:.1f})"
                elif node.processing_time_mode == ProcessingTimeMode.SKEW_NORMAL:
                    # Récupérer l'écart-type et le convertir dans l'unité courante / Get std dev and convert to current unit
                    std_dev_cs = getattr(node, 'processing_time_std_dev_cs', 0.0)
                    std_dev = TimeConverter.from_centiseconds(std_dev_cs, self.flow_model.current_time_unit)
                    alpha_val = getattr(node, 'processing_time_skewness', 0.0)
                    mode_display = f"SKEW(ξ={time_value:.1f}, ω={std_dev:.1f}, α={alpha_val:.1f})"
                
                if mode_display:
                    count_label = mode_display
        
        # Textes en taille normale aux coordonnées modèle / Normal-sized text at model coordinates
        time_text = self.create_text(
            x, y + 10,
            text=time_label,
            font=("Arial", 8),
            tags=("node", node.node_id)
        )
        
        # Afficher le compteur pour les sources et sinks, ou le mode pour les nœuds de traitement / Display counter for sources and sinks, or mode for processing nodes
        count_text = None
        if node.is_source or node.is_sink or (not node.is_splitter and not node.is_merger and count_label):
            count_text = self.create_text(
                x, y + 22,
                text=count_label,
                font=("Arial", 7),
                fill="#666",
                tags=("node", node.node_id)
            )
        
        # Indicateur de loupe (si le nœud a des loupes de temps) / Time probe indicator (if node has time probes)
        loupe_icon = None
        has_time_probe = False
        if hasattr(self.flow_model, 'time_probes') and self.flow_model.time_probes:
            # Vérifier si ce nœud a au moins une loupe / Check if this node has at least one probe
            for probe in self.flow_model.time_probes.values():
                if probe.node_id == node.node_id:
                    has_time_probe = True
                    break
            
            if has_time_probe:
                # Dessiner une petite icône loupe en haut à droite du nœud / Draw small probe icon in top right of node
                icon_x = x + node_width/2 - 10
                icon_y = y - node_height/2 + 10
                loupe_icon = self.create_text(
                    icon_x, icon_y,
                    text="🔍",
                    font=("Arial", 10),
                    tags=("node", node.node_id)
                )
        
        self.node_canvas_objects[node.node_id] = {
            'rect': rect,
            'text': text,
            'time_text': time_text,
            'count_text': count_text,
            'loupe_icon': loupe_icon
        }
    
    def draw_buffer_indicator(self, x: float, y: float, current: int, capacity: float) -> int:
        """Dessine un indicateur de buffer / Draw a buffer indicator"""
        size = self.BUFFER_INDICATOR_SIZE
        indicator = self.create_rectangle(
            x, y, x + size, y + size,
            fill=self.BUFFER_COLOR, outline="#FF8C00", width=1
        )
        
        # Texte du buffer / Buffer text
        buffer_text = f"{current}"
        if capacity != float('inf'):
            buffer_text += f"/{int(capacity)}"
        
        text = self.create_text(
            x + size/2, y + size/2,
            text=buffer_text, font=("Arial", 7),
            fill="black"
        )
        
        return indicator
    
    def redraw_connection(self, connection: Connection):
        """Redessine une connexion individuelle en gérant correctement le zoom / Redraw a single connection while properly handling zoom"""
        # Ne pas toucher au zoom_level - laisser draw_connection utiliser le zoom actuel
        # Cela évite le double-scaling
        # Don't touch zoom_level - let draw_connection use current zoom
        # This avoids double-scaling
        
        # Obtenir les positions visuelles actuelles des nœuds source et target
        # Get current visual positions of source and target nodes
        source_node = self.flow_model.get_node(connection.source_id)
        target_node = self.flow_model.get_node(connection.target_id)
        
        # NOTE: On ne met PAS à jour node.x/node.y ici car les coordonnées canvas 
        # incluent le zoom. Les coordonnées modèle doivent rester intactes.
        # L'ancien code écrasait les coordonnées modèle avec les coordonnées canvas zoomées.
        # NOTE: We do NOT update node.x/node.y here because canvas coordinates
        # include zoom. Model coordinates must remain intact.
        # Old code was overwriting model coordinates with zoomed canvas coordinates.
        
        # Supprimer complètement l'ancienne connexion / Completely delete old connection
        if connection.connection_id in self.connection_canvas_objects:
            for obj in self.connection_canvas_objects[connection.connection_id].values():
                if obj:
                    self.delete(obj)
            del self.connection_canvas_objects[connection.connection_id]
        
        # Supprimer aussi par tag / Also delete by tag
        self.delete(connection.connection_id)
        
        # Redessiner avec le zoom_level actuel (sans le modifier)
        # Redraw with current zoom_level (without modifying it)
        self.draw_connection(connection)
    
    def draw_connection(self, connection: Connection):
        """Dessine une connexion entre deux nœuds / Draw a connection between two nodes"""
        # Supprimer tous les objets existants avec le tag de cette connexion
        # Delete all existing objects with this connection's tag
        self.delete(connection.connection_id)
        
        source_node = self.flow_model.get_node(connection.source_id)
        target_node = self.flow_model.get_node(connection.target_id)
        
        if not source_node or not target_node:
            if not source_node:
                if self.app_config.DEBUG_MODE:
                    print(f"[CANVAS] ⚠️ Connexion {connection.connection_id}: source {connection.source_id} INTROUVABLE")
            if not target_node:
                if self.app_config.DEBUG_MODE:
                    print(f"[CANVAS] ⚠️ Connexion {connection.connection_id}: target {connection.target_id} INTROUVABLE")
            return
        
        # Vérifier si la connexion est sélectionnée / Check if connection is selected
        is_selected = connection.connection_id == self.selected_connection_id
        
        # Vérifier si la connexion doit clignoter (highlight actif)
        # Check if connection should blink (highlight active)
        should_highlight = False
        if hasattr(connection, 'highlight_until'):
            # Obtenir le temps actuel de la simulation depuis le simulateur
            # Get current simulation time from simulator
            current_sim_time = 0
            if hasattr(self, 'simulator') and self.simulator and self.simulator.env:
                current_sim_time = self.simulator.env.now
            should_highlight = connection.highlight_until > current_sim_time
        
        # Couleur de la ligne / Line color
        if should_highlight:
            line_color = "#00FF00"  # Vert vif pour le clignotement / Bright green for blinking
            line_width = 4
        elif is_selected:
            line_color = "#FF8C00"
            line_width = 3
        else:
            line_color = self.CONNECTION_COLOR
            line_width = 2
        
        # Calculer les points de départ et d'arrivée en utilisant les coordonnées réelles des objets canvas
        # Calculate start and end points using actual canvas object coordinates
        # Obtenir les coordonnées du rectangle source / Get source rectangle coordinates
        if source_node.node_id in self.node_canvas_objects and 'rect' in self.node_canvas_objects[source_node.node_id]:
            source_rect = self.node_canvas_objects[source_node.node_id]['rect']
            if source_rect:
                source_coords = self.coords(source_rect)
                if source_coords and len(source_coords) >= 4:
                    # Point de sortie : milieu du bord droit / Exit point: middle of right edge
                    x1 = source_coords[2]  # x2 du rectangle (bord droit) / x2 of rectangle (right edge)
                    y1 = (source_coords[1] + source_coords[3]) / 2  # milieu vertical
                else:
                    x1, y1 = source_node.x + self.NODE_WIDTH/2, source_node.y
            else:
                x1, y1 = source_node.x + self.NODE_WIDTH/2, source_node.y
        else:
            x1, y1 = source_node.x + self.NODE_WIDTH/2, source_node.y
        
        # Obtenir les coordonnées du rectangle cible / Get target rectangle coordinates
        if target_node.node_id in self.node_canvas_objects and 'rect' in self.node_canvas_objects[target_node.node_id]:
            target_rect = self.node_canvas_objects[target_node.node_id]['rect']
            if target_rect:
                target_coords = self.coords(target_rect)
                if target_coords and len(target_coords) >= 4:
                    # Point d'entrée : milieu du bord gauche / Entry point: middle of left edge
                    x2 = target_coords[0]  # x1 du rectangle (bord gauche) / x1 of rectangle (left edge)
                    y2 = (target_coords[1] + target_coords[3]) / 2  # milieu vertical
                else:
                    x2, y2 = target_node.x - self.NODE_WIDTH/2, target_node.y
            else:
                x2, y2 = target_node.x - self.NODE_WIDTH/2, target_node.y
        else:
            x2, y2 = target_node.x - self.NODE_WIDTH/2, target_node.y
        
        # Dessiner la ligne / Draw the line
        line = self.create_line(
            x1, y1, x2, y2,
            fill=line_color, width=line_width, arrow=tk.LAST,
            tags=("connection", connection.connection_id)
        )
        
        # Calculer le point milieu pour le buffer / Calculate midpoint for buffer
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        
        # Toujours afficher l'indicateur de buffer sur les connexions
        # Always show buffer indicator on connections
        buffer_rect = None
        buffer_text = None
        buffer_bg = None
        
        # Taille de l'indicateur - multipliée par zoom_level car les nouveaux objets
        # ne sont PAS automatiquement scalés par le canvas
        # Indicator size - multiplied by zoom_level because new objects
        # are NOT automatically scaled by canvas
        buffer_size = connection.buffer_visual_size * self.zoom_level
        
        # Vérifier s'il y a une pipette sur cette connexion
        # Check if there's a probe on this connection
        has_probe = any(probe.connection_id == connection.connection_id 
                       for probe in self.flow_model.probes.values())
        
        # Si pipette présente, dessiner un indicateur / If probe present, draw an indicator
        if has_probe:
            # Dessiner un petit cercle côté du buffer / Draw a small circle beside buffer
            probe_indicator = self.create_oval(
                mid_x + buffer_size + 5, mid_y - 8,
                mid_x + buffer_size + 13, mid_y,
                fill="#2196F3", outline="black", width=1,
                tags=("connection", connection.connection_id)
            )
            # Symbole pipette (P) / Probe symbol (P)
            probe_text = self.create_text(
                mid_x + buffer_size + 9, mid_y - 4,
                text="P", font=("Arial", 6, "bold"),
                fill="white",
                tags=("connection", connection.connection_id)
            )
        
        # Fond blanc pour meilleure visibilité / White background for better visibility
        buffer_bg = self.create_rectangle(
            mid_x - buffer_size, mid_y - buffer_size/2,
            mid_x + buffer_size, mid_y + buffer_size/2,
            fill="white", outline="", width=0,
            tags=("connection", connection.connection_id)
        )
        
        # Rectangle du buffer / Buffer rectangle
        fill_color = self.BUFFER_COLOR if connection.current_buffer_count > 0 else "#F0F0F0"
        buffer_rect = self.create_rectangle(
            mid_x - buffer_size, mid_y - buffer_size/2,
            mid_x + buffer_size, mid_y + buffer_size/2,
            fill=fill_color, outline="#FF8C00", width=2,
            tags=("connection", connection.connection_id)
        )
        
        # Texte du buffer / Buffer text
        buffer_text_str = f"{connection.current_buffer_count}"
        if connection.buffer_capacity != float('inf'):
            buffer_text_str += f"/{int(connection.buffer_capacity)}"
        
        buffer_text = self.create_text(
            mid_x, mid_y,
            text=buffer_text_str, font=("Arial", 8, "bold"),
            fill="black",
            tags=("connection", connection.connection_id)
        )
        
        self.connection_canvas_objects[connection.connection_id] = {
            'line': line,
            'buffer_bg': buffer_bg,
            'buffer_rect': buffer_rect,
            'buffer_text': buffer_text
        }
    
    def redraw_all(self):
        """Redessine tout le flux / Redraw entire flow"""
        # print(f"[DEBUG] redraw_all() appelé - Nœuds: {len(self.flow_model.nodes)}, Connexions: {len(self.flow_model.connections)}")
        
        # Invalider tout le cache car on redessine tout
        # Invalidate entire cache since we're redrawing everything
        self._invalidate_node_position_cache()
        
        # Réinitialiser la sélection multiple (les objets canvas vont être supprimés)
        # Reset multi-selection (canvas objects will be deleted)
        self.multi_selection_active = False
        self.multi_selection_start = None
        self.multi_selection_rect = None
        self.multi_drag_active = False
        self.selected_nodes.clear()
        self.selected_operators.clear()
        self.selected_probes.clear()
        self.selected_annotations.clear()
        
        # Sauvegarder l'état de zoom actuel / Save current zoom state
        current_zoom = self.zoom_level
        
        # Sauvegarder la position de la vue actuelle
        # Save current view position
        view_x = self.xview()[0]  # Position horizontale du viewport (0.0 à 1.0) / Horizontal viewport position (0.0 to 1.0)
        view_y = self.yview()[0]  # Position verticale du viewport (0.0 à 1.0) / Vertical viewport position (0.0 to 1.0)
        
        # Sauvegarder la ligne temporaire si elle existe
        # Save temporary line if it exists
        temp_line_backup = self.temp_connection_line
        
        # Nettoyer les références invalides avant de redessiner
        # Clean up invalid references before redrawing
        if self.selected_node_id and self.selected_node_id not in self.flow_model.nodes:
            # print(f"[DEBUG] Nettoyage selected_node_id: {self.selected_node_id}")
            self.selected_node_id = None
        if self.selected_connection_id and self.selected_connection_id not in self.flow_model.connections:
            # print(f"[DEBUG] Nettoyage selected_connection_id: {self.selected_connection_id}")
            self.selected_connection_id = None
        if self.selected_probe_id and self.selected_probe_id not in self.flow_model.probes:
            # print(f"[DEBUG] Nettoyage selected_probe_id: {self.selected_probe_id}")
            self.selected_probe_id = None
        if self.connection_start_node_id and self.connection_start_node_id not in self.flow_model.nodes:
            # print(f"[DEBUG] Nettoyage connection_start_node_id: {self.connection_start_node_id}")
            self.connection_start_node_id = None
        
        self.delete("all")
        self.node_canvas_objects.clear()
        self.connection_canvas_objects.clear()
        self.animated_items.clear()
        self.probe_canvas_objects.clear()  # Nettoyer aussi les références de sondes / Also clean up probe references
        self.operator_canvas_objects.clear()  # Nettoyer les opérateurs - seront redessinés après init simulateur / Clean up operators - will be redrawn after simulator init
        
        if self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Canvas nettoyé, début du redessin...")
        
        # Réinitialiser zoom_level à 1.0 pour dessiner à la taille de base
        # Le scale() sera appliqué après
        # Reset zoom_level to 1.0 to draw at base size
        # scale() will be applied after
        self.zoom_level = 1.0
        
        # Réinitialiser la référence à la ligne temporaire
        # Reset temporary line reference
        self.temp_connection_line = None
        
        # Les connexions et annotations sont déjà dessinées plus haut
        # Connections and annotations are already drawn above
        
        # Dessiner les nœuds (au premier plan) / Draw nodes (foreground)
        if self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Dessin de {len(self.flow_model.nodes)} nœuds")
        for node_id, node in self.flow_model.nodes.items():
            if self.app_config.DEBUG_MODE:
                print(f"[DEBUG]   - {node_id} ({node.name}): inputs={node.input_connections}, outputs={node.output_connections}")
            self.draw_node(node)
        
        # Dessiner les sondes / Draw probes
        if self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Dessin de {len(self.flow_model.probes)} sondes")
        for probe in self.flow_model.probes.values():
            self.draw_probe(probe)
        
        # Dessiner les connexions d'abord / Draw connections first
        if self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Dessin de {len(self.flow_model.connections)} connexions")
        for conn_id, connection in self.flow_model.connections.items():
            if self.app_config.DEBUG_MODE:
                print(f"[DEBUG]   - {conn_id}: {connection.source_id} → {connection.target_id}")
            self.draw_connection(connection)
        
        # Dessiner les annotations (AVANT les nœuds pour être en arrière-plan)
        # Draw annotations (BEFORE nodes to be in background)
        if self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Dessin de {len(self.flow_model.annotations)} annotations")
        for annotation in self.flow_model.annotations.values():
            self.draw_annotation(annotation)
        
        # NE PAS dessiner les opérateurs ici - ils seront dessinés automatiquement
        # après l'initialisation du simulateur avec leurs bonnes coordonnées
        # DO NOT draw operators here - they will be drawn automatically
        # after simulator initialization with their correct coordinates
        if self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Opérateurs non dessinés (seront initialisés par le simulateur)")
        
        # Enfin les items animés (au premier plan) / Finally animated items (foreground)
        self.draw_animated_items()
        
        if self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Redessin terminé")
        
        # Réappliquer le zoom si on n'est pas au niveau 1.0
        # Reapply zoom if not at level 1.0
        if current_zoom != 1.0:
            # Calculer le facteur de zoom à appliquer / Calculate zoom factor to apply
            zoom_factor = current_zoom
            # Le zoom_level a déjà été réinitialisé à 1.0 avant le dessin
            # zoom_level has already been reset to 1.0 before drawing
            # Obtenir le centre du canvas / Get canvas center
            center_x = self.canvasx(self.winfo_width() / 2)
            center_y = self.canvasy(self.winfo_height() / 2)
            # Appliquer le zoom / Apply zoom
            self.scale("all", center_x, center_y, zoom_factor, zoom_factor)
            self.zoom_level = current_zoom
            bbox = self.bbox("all")
            if bbox:
                margin = 5000
                extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                               bbox[2] + margin, bbox[3] + margin)
                self.configure(scrollregion=extended_bbox)
            else:
                self.configure(scrollregion=(-5000, -5000, 5000, 5000))
        else:
            # Même sans zoom, mettre à jour la scrollregion avec marge
            # Even without zoom, update scrollregion with margin
            bbox = self.bbox("all")
            if bbox:
                margin = 5000
                extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                               bbox[2] + margin, bbox[3] + margin)
                self.configure(scrollregion=extended_bbox)
            else:
                self.configure(scrollregion=(-5000, -5000, 5000, 5000))
        
        # Restaurer la position de la vue / Restore view position
        self.xview_moveto(view_x)
        self.yview_moveto(view_y)
        
        # Redessiner la ligne temporaire si on était en train de créer une connexion
        # Redraw temporary line if we were creating a connection
        if self.mode == "add_connection" and self.connection_start_node_id:
            source_node = self.flow_model.get_node(self.connection_start_node_id)
            if source_node:
                # Récupérer la dernière position de la souris
                # Get last mouse position
                x, y = self.winfo_pointerx() - self.winfo_rootx(), self.winfo_pointery() - self.winfo_rooty()
                # Convertir en coordonnées canvas
                # Convert to canvas coordinates
                mouse_x = self.canvasx(x)
                mouse_y = self.canvasy(y)
                
                # Calculer le point de départ en utilisant les coordonnées réelles du rectangle canvas
                # Calculate start point using actual canvas rectangle coordinates
                start_x, start_y = None, None
                if source_node.node_id in self.node_canvas_objects and 'rect' in self.node_canvas_objects[source_node.node_id]:
                    source_rect = self.node_canvas_objects[source_node.node_id]['rect']
                    if source_rect:
                        source_coords = self.coords(source_rect)
                        if source_coords and len(source_coords) >= 4:
                            # Point de sortie : milieu du bord droit / Exit point: middle of right edge
                            start_x = source_coords[2]  # x2 du rectangle (bord droit)
                            start_y = (source_coords[1] + source_coords[3]) / 2  # milieu vertical
                
                # Fallback si le rectangle n'existe pas encore / Fallback if rectangle doesn't exist yet
                if start_x is None or start_y is None:
                    start_x = source_node.x * self.zoom_level + (self.NODE_WIDTH * self.zoom_level) / 2
                    start_y = source_node.y * self.zoom_level
                
                self.temp_connection_line = self.create_line(
                    start_x, start_y,
                    mouse_x, mouse_y,
                    fill="#999999", width=2, dash=(5, 5)
                )
    
    def draw_imported_elements(self, imported_nodes: set, imported_operators: set, 
                               imported_probes: set, imported_annotations: set):
        """
        Dessine uniquement les éléments importés sans effacer le canvas existant.
        Utilisé lors de l'import pour préserver le flux existant.
        
        Draw only imported elements without clearing existing canvas.
        Used during import to preserve existing flow.
        """
        # Dessiner les annotations importées / Draw imported annotations
        for ann_id in imported_annotations:
            annotation = self.flow_model.annotations.get(ann_id)
            if annotation:
                self.draw_annotation(annotation)
        
        # Dessiner les nœuds importés / Draw imported nodes
        for node_id in imported_nodes:
            node = self.flow_model.get_node(node_id)
            if node:
                self.draw_node(node)
        
        # Dessiner les connexions qui relient les nœuds importés
        # Draw connections linking imported nodes
        for conn in self.flow_model.connections.values():
            if conn.source_id in imported_nodes or conn.target_id in imported_nodes:
                # Vérifier que la connexion n'est pas déjà dessinée
                # Check that connection isn't already drawn
                if conn.connection_id not in self.connection_canvas_objects:
                    self.draw_connection(conn)
        
        # Dessiner les pipettes importées / Draw imported probes
        for probe_id in imported_probes:
            probe = self.flow_model.probes.get(probe_id)
            if probe:
                self.draw_probe(probe)
        
        # Dessiner les opérateurs importés / Draw imported operators
        for op_id in imported_operators:
            operator = self.flow_model.operators.get(op_id)
            if operator:
                self.draw_operator(operator)
        
        # Appliquer le zoom actuel aux éléments importés
        # Apply current zoom to imported elements
        if self.zoom_level != 1.0:
            center_x = self.canvasx(self.winfo_width() / 2)
            center_y = self.canvasy(self.winfo_height() / 2)
            
            # Appliquer le zoom uniquement aux éléments importés
            # Apply zoom only to imported elements
            for node_id in imported_nodes:
                if node_id in self.node_canvas_objects:
                    for obj in self.node_canvas_objects[node_id].values():
                        if obj:
                            self.scale(obj, center_x, center_y, self.zoom_level, self.zoom_level)
            
            for conn_id, objs in self.connection_canvas_objects.items():
                conn = self.flow_model.get_connection(conn_id)
                if conn and (conn.source_id in imported_nodes or conn.target_id in imported_nodes):
                    for obj in objs.values():
                        if obj:
                            self.scale(obj, center_x, center_y, self.zoom_level, self.zoom_level)
            
            for probe_id in imported_probes:
                if probe_id in self.probe_canvas_objects:
                    for obj in self.probe_canvas_objects[probe_id].values():
                        if obj:
                            self.scale(obj, center_x, center_y, self.zoom_level, self.zoom_level)
            
            for op_id in imported_operators:
                if op_id in self.operator_canvas_objects:
                    for obj in self.operator_canvas_objects[op_id].values():
                        if obj:
                            self.scale(obj, center_x, center_y, self.zoom_level, self.zoom_level)
            
            for ann_id in imported_annotations:
                if ann_id in self.annotation_canvas_objects:
                    for obj in self.annotation_canvas_objects[ann_id].values():
                        if obj:
                            self.scale(obj, center_x, center_y, self.zoom_level, self.zoom_level)
        
        # Mettre à jour la scrollregion / Update scrollregion
        bbox = self.bbox("all")
        if bbox:
            margin = 5000
            extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                           bbox[2] + margin, bbox[3] + margin)
            self.configure(scrollregion=extended_bbox)

    def on_click(self, event):
        """Gestion du clic / Click handling"""
        # S'assurer que le canvas a le focus pour recevoir les événements clavier
        # Ensure canvas has focus to receive keyboard events
        self.focus_set()
        
        # Convertir les coordonnées de l'événement en coordonnées canvas (tient compte du zoom et scroll)
        # Convert event coordinates to canvas coordinates (accounts for zoom and scroll)
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        
        # Mode placement d'import : clic pour placer définitivement
        # Import placement mode: click to place permanently
        if self.import_placement_mode:
            self._finalize_import_placement()
            return
        
        if self.mode == "select":
            # Vérifier si Ctrl est enfoncé pour la sélection multiple
            # Check if Ctrl is pressed for multi-selection
            ctrl_pressed = event.state & 0x4  # 0x4 = Control key
            
            if ctrl_pressed:
                # D'abord vérifier si on clique sur un élément spécifique
                # pour l'ajouter/retirer de la sélection
                # First check if clicking on a specific element
                # to add/remove from selection
                element_found = self._toggle_element_in_multi_selection(x, y)
                
                if not element_found:
                    # Sinon, démarrer la sélection multiple par rectangle
                    # Otherwise, start multi-selection rectangle
                    self.multi_selection_active = True
                    self.multi_selection_start = (x, y)
                return
            
            # Vérifier si on clique sur un élément déjà dans la sélection multiple
            # pour déplacer toute la sélection
            # Check if clicking on element already in multi-selection
            # to move entire selection
            if self._is_in_multi_selection(x, y):
                self.multi_drag_active = True
                self.drag_start_pos = (x, y)
                return
            
            # Clic normal - effacer la sélection multiple
            # Normal click - clear multi-selection
            if self.selected_nodes or self.selected_operators or self.selected_probes or self.selected_annotations:
                self._clear_multi_selection()
            
            # Vérifier si on clique sur une pipette (priorité maximale - petits éléments)
            # Check if clicking on a probe (maximum priority - small elements)
            clicked_probe_id = self._find_probe_at_position(x, y)
            if clicked_probe_id:
                old_selected_probe = self.selected_probe_id
                old_selected_node = self.selected_node_id
                old_selected_operator = self.selected_operator_id
                # Marquer l'ancien nœud comme ayant changé visuellement
                # Mark old node as visually changed
                if old_selected_node:
                    old_node = self.flow_model.get_node(old_selected_node)
                    if old_node:
                        old_node._visual_changed = True
                self.selected_probe_id = clicked_probe_id
                self.selected_node_id = None
                self.selected_connection_id = None
                self.selected_annotation_id = None
                self.selected_operator_id = None
                # Démarrer le drag de la pipette - RÉINITIALISER les autres drags
                # Start probe drag - RESET other drags
                self.dragging_probe_id = clicked_probe_id
                self.dragging_node_id = None
                self.dragging_operator_id = None
                self.drag_start_pos = (x, y)
                # Mettre à jour visuellement si quelque chose a changé
                if old_selected_probe != clicked_probe_id or old_selected_node or old_selected_operator:
                    self._update_selection_visual()
                return
            
            # Vérifier les opérateurs EN PREMIER (petits éléments, priorité haute)
            # Cela permet de sélectionner un opérateur même s'il est sur un nœud
            # Check operators FIRST (small elements, high priority)
            # This allows selecting an operator even if it's on a node
            clicked_operator_id = self._find_operator_at_position(x, y)
            if clicked_operator_id:
                old_selected_operator = self.selected_operator_id
                old_selected_node = self.selected_node_id
                old_selected_probe = self.selected_probe_id
                # Marquer l'ancien nœud comme ayant changé visuellement
                # Mark old node as visually changed
                if old_selected_node:
                    old_node = self.flow_model.get_node(old_selected_node)
                    if old_node:
                        old_node._visual_changed = True
                self.selected_operator_id = clicked_operator_id
                self.selected_node_id = None
                self.selected_connection_id = None
                self.selected_probe_id = None
                self.selected_annotation_id = None
                # Donner le focus au canvas pour recevoir les événements clavier
                # Give focus to canvas to receive keyboard events
                self.focus_set()
                # Démarrer le drag de l'opérateur - RÉINITIALISER les autres drags
                # Start operator drag - RESET other drags
                self.dragging_operator_id = clicked_operator_id
                self.dragging_node_id = None
                self.dragging_probe_id = None
                self.drag_start_pos = (x, y)
                # Mettre à jour visuellement si quelque chose a changé
                if old_selected_operator != clicked_operator_id or old_selected_node or old_selected_probe:
                    self._update_selection_visual()
                return
            
            # Vérifier les nœuds (plus grands, priorité après les petits éléments)
            # Check nodes (larger, priority after small elements)
            clicked_node_id = self._find_node_at_position(x, y)
            if clicked_node_id:
                old_selected_node = self.selected_node_id
                # Marquer l'ancien nœud comme ayant changé visuellement
                # Mark old node as visually changed
                if old_selected_node and old_selected_node != clicked_node_id:
                    old_node = self.flow_model.get_node(old_selected_node)
                    if old_node:
                        old_node._visual_changed = True
                self.selected_node_id = clicked_node_id
                new_node = self.flow_model.get_node(clicked_node_id)
                if new_node:
                    new_node._visual_changed = True
                self.selected_connection_id = None
                self.selected_probe_id = None
                self.selected_annotation_id = None
                self.selected_operator_id = None
                # Démarrer le drag du nœud - RÉINITIALISER les autres drags
                # Start node drag - RESET other drags
                self.dragging_node_id = clicked_node_id
                self.dragging_operator_id = None  # Important: éviter le drag simultané / Important: avoid simultaneous drag
                self.dragging_probe_id = None  # Important: éviter le drag simultané / Important: avoid simultaneous drag
                self.drag_start_pos = (x, y)
                if old_selected_node != clicked_node_id:
                    self._update_selection_visual()
                return
            
            # Vérifier si on clique sur une annotation / Check if clicking on an annotation
            clicked_annotation_id = self._find_annotation_at_position(x, y)
            if clicked_annotation_id:
                old_selected_annotation = self.selected_annotation_id
                self.selected_annotation_id = clicked_annotation_id
                self.selected_node_id = None
                self.selected_connection_id = None
                self.selected_probe_id = None
                self.selected_operator_id = None
                # Mettre à jour visuellement / Update visually
                if old_selected_annotation != clicked_annotation_id:
                    self._update_selection_visual()
                return
            
            # Vérifier si on clique sur une connexion / Check if clicking on a connection
            clicked_connection_id = self._find_connection_at_position(x, y)
            if clicked_connection_id:
                old_selected_conn = self.selected_connection_id
                self.selected_connection_id = clicked_connection_id
                self.selected_node_id = None  # Désélectionner le nœud / Deselect node
                self.selected_probe_id = None
                self.selected_annotation_id = None
                # Mettre à jour visuellement sans redessiner
                # Update visually without redrawing
                if old_selected_conn != clicked_connection_id:
                    self._update_selection_visual()
            else:
                # Clic dans le vide OU dans une annotation - démarrer le panning
                # Click in empty space OR on annotation - start panning
                self.panning = True
                self.pan_start_x = event.x
                self.pan_start_y = event.y
                self.scan_mark(event.x, event.y)
                # Désélectionner seulement les nœuds/connexions/pipettes/opérateurs, pas les annotations
                # Deselect only nodes/connections/probes/operators, not annotations
                if self.selected_node_id or self.selected_connection_id or self.selected_probe_id or self.selected_operator_id:
                    # Marquer l'ancien nœud sélectionné comme ayant changé visuellement
                    # Mark old selected node as visually changed
                    if self.selected_node_id:
                        old_node = self.flow_model.get_node(self.selected_node_id)
                        if old_node:
                            old_node._visual_changed = True
                    self.selected_node_id = None
                    self.selected_connection_id = None
                    self.selected_operator_id = None
                    self.selected_probe_id = None
                    self._update_selection_visual()
                    # Si on n'a pas cliqué sur une annotation, la désélectionner aussi
                    # If we didn't click on an annotation, deselect it too
                    if not clicked_annotation_id and self.selected_annotation_id:
                        self.selected_annotation_id = None
        
        # Le mode "add_node" est maintenant géré par main_window via _on_canvas_click
        # "add_node" mode is now handled by main_window via _on_canvas_click
        
        elif self.mode == "add_connection":
            # Commencer ou terminer une connexion / Start or end a connection
            clicked_node_id = self._find_node_at_position(x, y)
            if clicked_node_id:
                if self.connection_start_node_id is None:
                    # Démarrer la connexion / Start connection
                    self.connection_start_node_id = clicked_node_id
                else:
                    # Terminer la connexion / End connection
                    if self.connection_start_node_id != clicked_node_id:
                        self._create_connection(self.connection_start_node_id, clicked_node_id)
                    self.connection_start_node_id = None
                    if self.temp_connection_line:
                        self.delete(self.temp_connection_line)
                        self.temp_connection_line = None
        
        elif self.mode == "add_probe":
            # Ajouter une pipette sur une connexion / Add a probe on a connection
            clicked_connection_id = self._find_connection_at_position(x, y)
            if clicked_connection_id:
                self._add_probe_on_connection(clicked_connection_id, x, y)
                # Revenir en mode sélection / Return to select mode
                self.set_mode("select")
                # Notifier le changement de mode / Notify mode change
                self.event_generate("<<ModeChanged>>")
        
        elif self.mode == "add_time_probe":
            # Ajouter une loupe de temps sur un nœud / Add a time probe on a node
            clicked_node_id = self._find_node_at_position(x, y)
            if clicked_node_id:
                # Appeler le callback pour ajouter une loupe
                # Call callback to add a probe
                if hasattr(self, 'on_add_time_probe_callback') and self.on_add_time_probe_callback:
                    self.on_add_time_probe_callback(clicked_node_id)
                # Revenir en mode sélection / Return to select mode
                self.set_mode("select")
                # Notifier le changement de mode / Notify mode change
                self.event_generate("<<ModeChanged>>")
        
        elif self.mode == "add_annotation":
            # Mode annotation - démarrer le traçage du rectangle
            # Annotation mode - start drawing the rectangle
            self.annotation_start_pos = (x, y)
            # Le rectangle sera dessiné pendant le drag / Rectangle will be drawn during drag
        
        elif self.mode == "add_operator":
            # Mode opérateur - placer un nouvel opérateur
            # Operator mode - place a new operator
            from gui.operator_config_dialog import OperatorConfigDialog
            
            dialog = OperatorConfigDialog(self, self.flow_model, operator=None)
            
            if dialog.result and not dialog.result.get('delete'):
                # Créer le nouvel opérateur / Create new operator
                from models.operator import Operator
                operator_id = self.flow_model.generate_operator_id()
                operator = Operator(operator_id, dialog.result['name'])
                operator.color = dialog.result['color']
                operator.x = x
                operator.y = y
                operator.assigned_machines = dialog.result['assigned_machines']
                operator.travel_times = dialog.result['travel_times']
                
                # Ajouter au modèle / Add to model
                self.flow_model.add_operator(operator)
                
                # Dessiner / Draw
                self.draw_operator(operator)
                
                # Retour en mode sélection / Return to select mode
                self.set_mode("select")
                # Notifier le changement de mode / Notify mode change
                self.event_generate("<<ModeChanged>>")
    
    def on_drag(self, event):
        """Gestion du glissement / Drag handling"""
        if self.mode == "add_annotation" and self.annotation_start_pos:
            # Dessiner le rectangle temporaire pendant le drag
            # Draw temporary rectangle during drag
            x = self.canvasx(event.x)
            y = self.canvasy(event.y)
            
            # Supprimer l'ancien rectangle temporaire / Delete old temporary rectangle
            if self.temp_annotation_rect:
                self.delete(self.temp_annotation_rect)
            
            # Dessiner le nouveau rectangle temporaire / Draw new temporary rectangle
            x1, y1 = self.annotation_start_pos
            self.temp_annotation_rect = self.create_rectangle(
                x1, y1, x, y,
                outline="#888888",
                width=self.annotation_line_width,
                dash=self.annotation_dash_pattern,
                tags="temp_annotation"
            )
            return
        
        if self.mode == "select":
            # Panning du canvas si on est en mode panning
            # Canvas panning if in panning mode
            if self.panning:
                self.scan_dragto(event.x, event.y, gain=1)
                return
            
            # Mise à jour du rectangle de sélection multiple
            # Update multi-selection rectangle
            if self.multi_selection_active and self.multi_selection_start:
                x = self.canvasx(event.x)
                y = self.canvasy(event.y)
                self._update_multi_selection_rect(x, y)
                return
            
            # Déplacement de la sélection multiple / Move multi-selection
            if self.multi_drag_active and self.drag_start_pos:
                x = self.canvasx(event.x)
                y = self.canvasy(event.y)
                dx = x - self.drag_start_pos[0]
                dy = y - self.drag_start_pos[1]
                self._move_multi_selection(dx, dy)
                self.drag_start_pos = (x, y)
                return
            
            # Drag d'un opérateur / Operator drag
            if self.dragging_operator_id and self.drag_start_pos:
                # Convertir les coordonnées en coordonnées canvas
                # Convert coordinates to canvas coordinates
                x = self.canvasx(event.x)
                y = self.canvasy(event.y)
                
                # Calculer le déplacement en coordonnées canvas
                # Calculate displacement in canvas coordinates
                dx_canvas = x - self.drag_start_pos[0]
                dy_canvas = y - self.drag_start_pos[1]
                
                # Convertir en coordonnées modèle / Convert to model coordinates
                dx_model = dx_canvas / self.zoom_level
                dy_model = dy_canvas / self.zoom_level
                
                operator = self.flow_model.get_operator(self.dragging_operator_id)
                if operator:
                    operator.x += dx_model
                    operator.y += dy_model
                    self.drag_start_pos = (x, y)
                    
                    # Déplacer les objets visuels de l'opérateur avec le déplacement canvas
                    # Move operator visual objects with canvas displacement
                    if self.dragging_operator_id in self.operator_canvas_objects:
                        objs = self.operator_canvas_objects[self.dragging_operator_id]
                        for obj in objs.values():
                            if obj:
                                self.move(obj, dx_canvas, dy_canvas)
                return
            
            # Drag d'une pipette / Probe drag
            if self.dragging_probe_id and self.drag_start_pos:
                # Convertir les coordonnées en coordonnées canvas
                # Convert coordinates to canvas coordinates
                x = self.canvasx(event.x)
                y = self.canvasy(event.y)
                
                # Calculer le déplacement en coordonnées canvas
                # Calculate displacement in canvas coordinates
                dx_canvas = x - self.drag_start_pos[0]
                dy_canvas = y - self.drag_start_pos[1]
                
                # Convertir en coordonnées modèle / Convert to model coordinates
                dx_model = dx_canvas / self.zoom_level
                dy_model = dy_canvas / self.zoom_level
                
                probe = self.flow_model.probes.get(self.dragging_probe_id)
                if probe:
                    probe.x += dx_model
                    probe.y += dy_model
                    self.drag_start_pos = (x, y)
                    
                    # Déplacer les objets visuels de la pipette avec le déplacement canvas
                    # Move probe visual objects with canvas displacement
                    if self.dragging_probe_id in self.probe_canvas_objects:
                        objs = self.probe_canvas_objects[self.dragging_probe_id]
                        for obj in objs.values():
                            if obj:
                                self.move(obj, dx_canvas, dy_canvas)
                return
            
            # Drag d'un nœud / Node drag
            if self.dragging_node_id and self.drag_start_pos:
                # Convertir les coordonnées en coordonnées canvas
                # Convert coordinates to canvas coordinates
                x = self.canvasx(event.x)
                y = self.canvasy(event.y)
                
                # Calculer le déplacement en coordonnées canvas
                # Calculate displacement in canvas coordinates
                dx_canvas = x - self.drag_start_pos[0]
                dy_canvas = y - self.drag_start_pos[1]
                
                # Convertir le déplacement en coordonnées modèle
                # Si zoom = 2.0, un déplacement de 10 pixels canvas = 5 unités modèle
                # Convert displacement to model coordinates
                # If zoom = 2.0, a 10 pixel canvas displacement = 5 model units
                dx_model = dx_canvas / self.zoom_level
                dy_model = dy_canvas / self.zoom_level
                
                node = self.flow_model.get_node(self.dragging_node_id)
                if node:
                    # Mettre à jour les coordonnées MODÈLE / Update MODEL coordinates
                    node.x += dx_model
                    node.y += dy_model
                    self.drag_start_pos = (x, y)
                    
                    # Invalider le cache pour ce nœud car sa position a changé
                    # Invalidate cache for this node since its position changed
                    self._invalidate_node_position_cache(self.dragging_node_id)
                
                # Optimisation: déplacer seulement les objets visuels au lieu de tout redessiner
                # Optimization: move only visual objects instead of redrawing everything
                if self.dragging_node_id in self.node_canvas_objects:
                    objs = self.node_canvas_objects[self.dragging_node_id]
                    for obj in objs.values():
                        if obj:  # Peut être None pour count_text / Can be None for count_text
                            # Déplacer avec le déplacement CANVAS / Move with CANVAS displacement
                            self.move(obj, dx_canvas, dy_canvas)
                
                # Déplacer aussi les sondes attachées à ce nœud
                # Also move probes attached to this node
                for probe in self.flow_model.probes.values():
                    if probe.probe_id in self.probe_canvas_objects:
                        # Vérifier si la sonde est sur une connexion liée à ce nœud
                        # Check if probe is on a connection linked to this node
                        conn = self.flow_model.get_connection(probe.connection_id)
                        if conn and (conn.source_id == self.dragging_node_id or conn.target_id == self.dragging_node_id):
                            probe.x += dx_model
                            probe.y += dy_model
                            objs = self.probe_canvas_objects[probe.probe_id]
                            for obj in objs.values():
                                self.move(obj, dx_canvas, dy_canvas)
                
                # Redessiner seulement les connexions affectées
                # Pour simplifier, on redessine tout mais seulement toutes les 3 frames pour performance
                # Redraw only affected connections
                # For simplicity, we redraw everything but only every 3 frames for performance
                if not hasattr(self, '_drag_frame_count'):
                    self._drag_frame_count = 0
                self._drag_frame_count += 1
                
                if self._drag_frame_count % 3 == 0:  # Toutes les 3 frames / Every 3 frames
                    # Redessiner seulement les connexions liées au nœud déplacé
                    # Redraw only connections linked to the moved node
                    for conn_id in node.input_connections + node.output_connections:
                        if conn_id in self.flow_model.connections:
                            conn = self.flow_model.connections[conn_id]
                            # Supprimer l'ancienne représentation / Delete old representation
                            if conn_id in self.connection_canvas_objects:
                                for obj in self.connection_canvas_objects[conn_id].values():
                                    if obj:
                                        self.delete(obj)
                            # Redessiner / Redraw
                            self.redraw_connection(conn)
    
    def on_release(self, event):
        """Gestion du relâchement du bouton / Button release handling"""
        if self.mode == "add_annotation" and self.annotation_start_pos:
            # Finaliser l'annotation / Finalize annotation
            x = self.canvasx(event.x)
            y = self.canvasy(event.y)
            
            # Supprimer le rectangle temporaire / Delete temporary rectangle
            if self.temp_annotation_rect:
                self.delete(self.temp_annotation_rect)
                self.temp_annotation_rect = None
            
            # Calculer les coordonnées du rectangle / Calculate rectangle coordinates
            x1, y1 = self.annotation_start_pos
            
            # S'assurer que x1 < x2 et y1 < y2 / Ensure x1 < x2 and y1 < y2
            x_min, x_max = min(x1, x), max(x1, x)
            y_min, y_max = min(y1, y), max(y1, y)
            
            # Vérifier que le rectangle a une taille minimale
            # Check that rectangle has minimum size
            if abs(x_max - x_min) > 20 and abs(y_max - y_min) > 20:
                # Demander le texte de l'annotation / Ask for annotation text
                from gui.annotation_config_dialog import AnnotationConfigDialog
                dialog = AnnotationConfigDialog(self, annotation=None)
                
                if dialog.result and not dialog.result.get('delete'):
                    # Créer l'annotation / Create annotation
                    from models.annotation import Annotation
                    annotation_id = self.flow_model.generate_annotation_id()
                    annotation = Annotation(
                        annotation_id,
                        x_min, y_min,
                        x_max - x_min,
                        y_max - y_min,
                        dialog.result['text']
                    )
                    annotation.color = dialog.result['color']
                    annotation.dash_pattern = self.annotation_dash_pattern
                    if 'text_size' in dialog.result:
                        annotation.text_size = dialog.result['text_size']
                    
                    # Ajouter au modèle / Add to model
                    self.flow_model.add_annotation(annotation)
                    
                    # Dessiner / Draw
                    self.draw_annotation(annotation)
            
            # Réinitialiser / Reset
            self.annotation_start_pos = None
            
            # Revenir en mode sélection / Return to select mode
            self.set_mode("select")
            self.event_generate("<<ModeChanged>>")
            return
        
        if self.mode == "select":
            # Arrêter le panning / Stop panning
            if self.panning:
                self.panning = False
            
            # Finaliser la sélection multiple / Finalize multi-selection
            if self.multi_selection_active:
                x = self.canvasx(event.x)
                y = self.canvasy(event.y)
                self._finalize_multi_selection(x, y)
                return
            
            # Arrêter le déplacement de la sélection multiple
            # Stop multi-selection movement
            if self.multi_drag_active:
                self.multi_drag_active = False
                self.drag_start_pos = None
                return
            
            # Si on était en train de déplacer un nœud, redessiner uniquement les connexions affectées
            # SEULEMENT si le nœud a vraiment été déplacé
            # If we were moving a node, redraw only affected connections
            # ONLY if node has actually moved
            if self.dragging_node_id and self.drag_start_pos:
                # Vérifier si le nœud a réellement bougé / Check if node actually moved
                current_x = self.canvasx(event.x)
                current_y = self.canvasy(event.y)
                start_x, start_y = self.drag_start_pos
                
                # Seuil de 3 pixels pour considérer qu'il y a eu un déplacement
                # 3 pixel threshold to consider there was movement
                has_moved = (abs(current_x - start_x) > 3 or abs(current_y - start_y) > 3)
                
                if has_moved:
                    # Redessiner les connexions liées au nœud déplacé
                    # Redraw connections linked to moved node
                    node = self.flow_model.get_node(self.dragging_node_id)
                    if node:
                        for conn_id in node.input_connections + node.output_connections:
                            if conn_id in self.flow_model.connections:
                                conn = self.flow_model.connections[conn_id]
                                # Supprimer l'ancienne représentation de la connexion
                                # Delete old connection representation
                                if conn_id in self.connection_canvas_objects:
                                    for obj_name, obj in list(self.connection_canvas_objects[conn_id].items()):
                                        if obj:
                                            self.delete(obj)
                                    del self.connection_canvas_objects[conn_id]
                                # Redessiner la connexion / Redraw connection
                                self.redraw_connection(conn)
            
            self.dragging_node_id = None
            self.dragging_probe_id = None
            self.dragging_operator_id = None
            self.drag_start_pos = None
            
            # Réinitialiser le compteur de frames / Reset frame counter
            if hasattr(self, '_drag_frame_count'):
                del self._drag_frame_count
    
    def on_motion(self, event):
        """Gestion du mouvement de la souris / Mouse movement handling"""
        # Mode placement d'import : les éléments suivent le curseur
        # Import placement mode: elements follow cursor
        if self.import_placement_mode:
            # Vérifier qu'il y a des éléments sélectionnés
            # Check that there are selected elements
            if self.selected_nodes or self.selected_operators or self.selected_probes or self.selected_annotations:
                x = self.canvasx(event.x)
                y = self.canvasy(event.y)
                self._update_import_placement_position(x, y)
            return
        
        if self.mode == "add_connection" and self.connection_start_node_id:
            # Afficher une ligne temporaire / Display temporary line
            source_node = self.flow_model.get_node(self.connection_start_node_id)
            if source_node:
                if self.temp_connection_line:
                    self.delete(self.temp_connection_line)
                
                # Convertir les coordonnées en coordonnées canvas (tenir compte zoom/scroll)
                # Convert coordinates to canvas coordinates (account for zoom/scroll)
                mouse_x = self.canvasx(event.x)
                mouse_y = self.canvasy(event.y)
                
                # Calculer le point de départ en utilisant les coordonnées réelles du rectangle canvas
                # Calculate start point using actual canvas rectangle coordinates
                start_x, start_y = None, None
                if source_node.node_id in self.node_canvas_objects and 'rect' in self.node_canvas_objects[source_node.node_id]:
                    source_rect = self.node_canvas_objects[source_node.node_id]['rect']
                    if source_rect:
                        source_coords = self.coords(source_rect)
                        if source_coords and len(source_coords) >= 4:
                            # Point de sortie : milieu du bord droit / Exit point: middle of right edge
                            start_x = source_coords[2]  # x2 du rectangle (bord droit)
                            start_y = (source_coords[1] + source_coords[3]) / 2  # milieu vertical
                
                # Fallback si le rectangle n'existe pas encore / Fallback if rectangle doesn't exist yet
                if start_x is None or start_y is None:
                    start_x = source_node.x * self.zoom_level + (self.NODE_WIDTH * self.zoom_level) / 2
                    start_y = source_node.y * self.zoom_level
                
                self.temp_connection_line = self.create_line(
                    start_x, start_y,
                    mouse_x, mouse_y,
                    fill="#999999", width=2, dash=(5, 5)
                )
    
    def on_double_click(self, event):
        """Gestion du double-clic pour éditer un nœud, une connexion, une annotation ou un opérateur / Double-click handling to edit a node, connection, annotation or operator"""
        # Convertir les coordonnées en coordonnées canvas
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        
        # Vérifier d'abord si on double-clique sur un opérateur
        clicked_operator_id = self._find_operator_at_position(x, y)
        if clicked_operator_id:
            operator = self.flow_model.get_operator(clicked_operator_id)
            if operator:
                # Ouvrir le dialogue d'édition
                from gui.operator_config_dialog import OperatorConfigDialog
                dialog = OperatorConfigDialog(self, self.flow_model, operator=operator)
                
                if dialog.result:
                    if dialog.result.get('delete'):
                        # Supprimer l'opérateur / Delete operator
                        self.flow_model.remove_operator(clicked_operator_id)
                        self.remove_operator(clicked_operator_id)
                        self.selected_operator_id = None
                    else:
                        # Mettre à jour l'opérateur / Update operator
                        operator.name = dialog.result['name']
                        operator.color = dialog.result['color']
                        operator.assigned_machines = dialog.result['assigned_machines']
                        operator.travel_times = dialog.result['travel_times']
                        # Redessiner en préservant la position canvas
                        # Redraw while preserving canvas position
                        self.redraw_operator(operator)
                        
                        # Désélectionner l'opérateur après modification
                        # Deselect operator after modification
                        self.selected_operator_id = None
                        self._update_selection_visual()
                        
                        # Arrêter la simulation si elle est en cours
                        # Stop simulation if running
                        if hasattr(self, 'on_operator_modified'):
                            self.on_operator_modified()
            return
        
        # Vérifier si on double-clique sur une annotation
        # Check if double-clicking on an annotation
        clicked_annotation_id = self._find_annotation_at_position(x, y)
        if clicked_annotation_id:
            annotation = self.flow_model.get_annotation(clicked_annotation_id)
            if annotation:
                # Ouvrir le dialogue d'édition / Open edit dialog
                from gui.annotation_config_dialog import AnnotationConfigDialog
                dialog = AnnotationConfigDialog(self, annotation=annotation)
                
                if dialog.result:
                    if dialog.result.get('delete'):
                        # Supprimer l'annotation du modèle ET du canvas
                        # Delete annotation from model AND canvas
                        self.flow_model.remove_annotation(clicked_annotation_id)
                        self.remove_annotation(clicked_annotation_id)
                        self.selected_annotation_id = None
                        self.redraw_all()
                    else:
                        # Mettre à jour l'annotation / Update annotation
                        annotation.text = dialog.result['text']
                        annotation.color = dialog.result['color']
                        if 'text_size' in dialog.result:
                            annotation.text_size = dialog.result['text_size']
                        # Redessiner / Redraw
                        self.draw_annotation(annotation)
            return
        
        # Vérifier si on double-clique sur un nœud
        # Check if double-clicking on a node
        clicked_node_id = self._find_node_at_position(x, y)
        if clicked_node_id:
            self.selected_node_id = clicked_node_id
            self.event_generate("<<NodeDoubleClick>>")
        else:
            # Vérifier si on double-clique sur une connexion
            # Check if double-clicking on a connection
            clicked_connection_id = self._find_connection_at_position(x, y)
            if clicked_connection_id:
                self.selected_connection_id = clicked_connection_id
                self.event_generate("<<ConnectionDoubleClick>>")
    
    def on_right_click(self, event):
        """Gestion du clic droit / Right-click handling"""
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        
        # Vérifier si on a cliqué sur une pipette / Check if clicked on a probe
        clicked_probe_id = self._find_probe_at_position(x, y)
        if clicked_probe_id:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Supprimer la pipette", 
                           command=lambda: self.remove_probe(clicked_probe_id))
            menu.post(event.x_root, event.y_root)
            return
        
        # Vérifier si on a cliqué sur une connexion / Check if clicked on a connection
        clicked_connection_id = self._find_connection_at_position(event.x, event.y)
        if clicked_connection_id:
            self.selected_connection_id = clicked_connection_id
            self.event_generate("<<ConnectionRightClick>>")
    
    def on_delete_key(self, event):
        """Gestion de la touche Suppr pour supprimer un élément sélectionné / Delete key handling to delete a selected element"""
        if self.app_config.DEBUG_MODE:
            print(f"Touche Suppr pressée: {event.keysym}")
        if self.selected_probe_id:
            # Supprimer la pipette sélectionnée / Delete selected probe
            if self.app_config.DEBUG_MODE:
                print(f"Suppression de la pipette: {self.selected_probe_id}")
            self.remove_probe(self.selected_probe_id)
            self.selected_probe_id = None
        elif self.selected_operator_id:
            # Supprimer l'opérateur sélectionné / Delete selected operator
            if self.app_config.DEBUG_MODE:
                print(f"Suppression de l'opérateur: {self.selected_operator_id}")
            self.flow_model.remove_operator(self.selected_operator_id)
            self.remove_operator(self.selected_operator_id)
            self.selected_operator_id = None
        elif self.selected_annotation_id:
            # Supprimer l'annotation sélectionnée / Delete selected annotation
            if self.app_config.DEBUG_MODE:
                print(f"Suppression de l'annotation: {self.selected_annotation_id}")
            self.remove_annotation(self.selected_annotation_id)
            self.selected_annotation_id = None
            self.redraw_all()
        elif self.selected_node_id:
            if self.app_config.DEBUG_MODE:
                print(f"Suppression du nœud: {self.selected_node_id}")
            self.delete_selected_node()
        elif self.selected_connection_id:
            if self.app_config.DEBUG_MODE:
                print(f"Suppression de la connexion: {self.selected_connection_id}")
            self.delete_selected_connection()
        else:
            if self.app_config.DEBUG_MODE:
                print("Aucun élément sélectionné")
    
    def on_key_press(self, event):
        """Gère les touches clavier / Handle keyboard keys"""
        if event.keysym == "Delete":
            # Supprimer d'abord les éléments de la sélection multiple s'il y en a
            # First delete multi-selection elements if any
            if self.selected_nodes or self.selected_operators or self.selected_probes or self.selected_annotations:
                self._delete_multi_selection()
            elif self.selected_probe_id:
                # Supprimer la pipette sélectionnée / Delete selected probe
                self.remove_probe(self.selected_probe_id)
                self.selected_probe_id = None
            elif self.selected_operator_id:
                # Supprimer l'opérateur sélectionné / Delete selected operator
                self.flow_model.remove_operator(self.selected_operator_id)
                self.remove_operator(self.selected_operator_id)
                self.selected_operator_id = None
            elif self.selected_annotation_id:
                # Supprimer l'annotation sélectionnée / Delete selected annotation
                self.remove_annotation(self.selected_annotation_id)
                self.selected_annotation_id = None
                self.redraw_all()
            elif self.selected_connection_id:
                # Supprimer la connexion sélectionnée / Delete selected connection
                self.delete_selected_connection()
        # Touche Escape pour annuler la sélection multiple
        # Escape key to cancel multi-selection
        elif event.keysym == "Escape":
            if self.multi_selection_active or self.selected_nodes or self.selected_operators or self.selected_probes or self.selected_annotations:
                self._clear_multi_selection()
        if self.app_config.DEBUG_MODE:
            print(f"Touche pressée: {event.keysym} (keycode: {event.keycode})")
    
    def delete_selected_connection(self):
        """Supprime la connexion sélectionnée / Delete selected connection"""""
        if self.selected_connection_id:
            # Supprimer d'abord les pipettes associées à cette connexion
            # First delete probes associated with this connection
            probes_to_remove = [probe_id for probe_id, probe in self.flow_model.probes.items() 
                               if probe.connection_id == self.selected_connection_id]
            for probe_id in probes_to_remove:
                if probe_id in self.probe_canvas_objects:
                    objs = self.probe_canvas_objects[probe_id]
                    for obj in objs.values():
                        if obj:
                            self.delete(obj)
                    del self.probe_canvas_objects[probe_id]
                # Supprimer aussi par tag / Also delete by tag
                self.delete(probe_id)
            
            self.flow_model.remove_connection(self.selected_connection_id)
            self.selected_connection_id = None
            self.redraw_all()
    
    def _find_operator_at_position(self, x: float, y: float) -> Optional[str]:
        """Trouve l'opérateur à une position donnée (en tenant compte du zoom) / Find operator at given position (accounting for zoom)"""
        # Utiliser find_overlapping pour tenir compte du zoom
        # Use find_overlapping to account for zoom
        items = self.find_overlapping(x-5, y-5, x+5, y+5)
        for item in items:
            tags = self.gettags(item)
            if 'operator' in tags:
                for tag in tags:
                    if tag.startswith('op_'):
                        return tag
        return None
    
    def _find_annotation_at_position(self, x: float, y: float) -> Optional[str]:
        """Trouve l'annotation à une position donnée (rectangle OU texte) en tenant compte du zoom / Find annotation at given position (rectangle OR text) accounting for zoom"""
        # Utiliser find_overlapping pour tenir compte du zoom automatiquement
        # Use find_overlapping to automatically account for zoom
        items = self.find_overlapping(x-2, y-2, x+2, y+2)
        for item in items:
            tags = self.gettags(item)
            if 'annotation' in tags:
                # Trouver l'ID de l'annotation dans les tags
                # Find annotation ID in tags
                for tag in tags:
                    if tag.startswith('annotation_') and tag != 'annotation' and tag != 'annotation_text':
                        return tag
        return None
    
    def _find_node_at_position(self, x: float, y: float) -> Optional[str]:
        """Trouve le nœud à une position donnée en utilisant les coordonnées réelles des objets canvas / Find node at given position using actual canvas object coordinates"""
        for node_id in self.node_canvas_objects.keys():
            if node_id in self.node_canvas_objects:
                objs = self.node_canvas_objects[node_id]
                if 'rect' in objs and objs['rect']:
                    # Obtenir les coordonnées réelles de l'objet rectangle sur le canvas
                    # Get actual coordinates of rectangle object on canvas
                    coords = self.coords(objs['rect'])
                    if coords and len(coords) >= 4:
                        x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
                        # Vérifier si le point (x, y) est dans le rectangle
                        # Check if point (x, y) is in rectangle
                        if x1 <= x <= x2 and y1 <= y <= y2:
                            return node_id
        return None
    
    def _rebuild_item_type_colors_cache(self):
        """Reconstruit le cache des couleurs d'items par type (OPTIMISATION) / Rebuild item colors cache by type (OPTIMIZATION)"""
        self._item_type_colors.clear()
        # Parcourir tous les nœuds sources pour construire le mapping type_id -> couleur
        # Browse all source nodes to build type_id -> color mapping
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for itype in node.item_type_config.item_types:
                    self._item_type_colors[str(itype.type_id)] = itype.color
    
    def _update_selection_visual(self):
        """Met à jour l'apparence visuelle des sélections sans redessiner tout le canvas / Update visual appearance of selections without redrawing entire canvas"""
        # Mettre à jour les nœuds (OPTIMISÉ : seulement ceux qui ont changé)
        # Update nodes (OPTIMIZED: only those that changed)
        for node_id, objs in self.node_canvas_objects.items():
            if 'rect' in objs and objs['rect']:
                node = self.flow_model.get_node(node_id)
                if node:
                    # Vérifier si le nœud a changé visuellement (OPTIMISATION)
                    # Check if node changed visually (OPTIMIZATION)
                    if not getattr(node, '_visual_changed', True) and node_id != self.selected_node_id:
                        continue
                    
                    is_selected = node_id == self.selected_node_id
                    is_active = getattr(node, 'is_active', False)
                    
                    # Calculer la couleur selon le type et l'état
                    # Calculate color according to type and state
                    if node.is_source:
                        if is_active:
                            fill_color = "#81C784"
                        else:
                            fill_color = "#C8E6C9" if not is_selected else self.SELECTED_COLOR
                    elif node.is_sink:
                        if is_active:
                            fill_color = "#E57373"
                        else:
                            fill_color = "#FFCDD2" if not is_selected else self.SELECTED_COLOR
                    elif node.is_splitter:
                        if is_active:
                            fill_color = "#FFB74D"
                        else:
                            fill_color = "#FFE0B2" if not is_selected else self.SELECTED_COLOR
                    elif node.is_merger:
                        if is_active:
                            fill_color = "#9575CD"
                        else:
                            fill_color = "#D1C4E9" if not is_selected else self.SELECTED_COLOR
                    else:
                        if is_active:
                            fill_color = "#FFD54F"
                        else:
                            fill_color = self.SELECTED_COLOR if is_selected else self.NODE_COLOR
                    
                    # Appliquer la couleur / Apply color
                    self.itemconfig(objs['rect'], fill=fill_color)
                    
                    # Réinitialiser le flag après mise à jour / Reset flag after update
                    node._visual_changed = False
        
        # Mettre à jour les connexions / Update connections
        for conn_id, objs in self.connection_canvas_objects.items():
            if 'line' in objs and objs['line']:
                is_selected = conn_id == self.selected_connection_id
                line_color = "#FF8C00" if is_selected else self.CONNECTION_COLOR
                line_width = 3 if is_selected else 2
                self.itemconfig(objs['line'], fill=line_color, width=line_width)
                
                # Mettre à jour la bordure du buffer / Update buffer border
                if 'buffer_rect' in objs and objs['buffer_rect']:
                    buffer_outline = "#FF8C00" if is_selected else "#FF8C00"
                    buffer_outline_width = 2 if is_selected else 2
                    self.itemconfig(objs['buffer_rect'], outline=buffer_outline, width=buffer_outline_width)
        
        # Mettre à jour les opérateurs / Update operators
        for operator_id, objs in self.operator_canvas_objects.items():
            if 'circle' in objs and objs['circle']:
                operator = self.flow_model.get_operator(operator_id)
                if operator:
                    is_selected = operator_id == self.selected_operator_id
                    fill_color = self.SELECTED_COLOR if is_selected else operator.color
                    outline_color = "#FF4500" if is_selected else "#333333"
                    outline_width = 4 if is_selected else 2
                    self.itemconfig(objs['circle'], fill=fill_color, outline=outline_color, width=outline_width)
        
        # Mettre à jour les annotations / Update annotations
        for annotation_id, objs in self.annotation_canvas_objects.items():
            if 'rect' in objs and objs['rect']:
                annotation = self.flow_model.annotations.get(annotation_id)
                if annotation:
                    is_selected = annotation_id == self.selected_annotation_id
                    # Changer l'épaisseur et la couleur de la bordure pour indiquer la sélection
                    # Change border thickness and color to indicate selection
                    outline_width = 4 if is_selected else self.annotation_line_width
                    outline_color = "#FF4500" if is_selected else annotation.color
                    self.itemconfig(objs['rect'], outline=outline_color, width=outline_width)
    
    def _find_probe_at_position(self, x: float, y: float) -> Optional[str]:
        """Trouve une pipette à la position donnée / Find a probe at given position"""
        # Ajuster le rayon de sélection selon le zoom / Adjust selection radius according to zoom
        selection_radius = 15 * self.zoom_level
        
        for probe_id, probe in self.flow_model.probes.items():
            # Utiliser les coordonnées réelles de l'objet canvas
            # Use actual canvas object coordinates
            if probe_id in self.probe_canvas_objects:
                objs = self.probe_canvas_objects[probe_id]
                if 'circle' in objs:
                    # Obtenir les coordonnées réelles du cercle
                    # Get actual circle coordinates
                    coords = self.coords(objs['circle'])
                    if coords:
                        # Le cercle est (x1, y1, x2, y2), on prend le centre
                        # Circle is (x1, y1, x2, y2), take center
                        probe_x = (coords[0] + coords[2]) / 2
                        probe_y = (coords[1] + coords[3]) / 2
                        distance = ((x - probe_x) ** 2 + (y - probe_y) ** 2) ** 0.5
                        if distance < selection_radius:
                            return probe_id
        return None
    
    def _find_connection_at_position(self, x: float, y: float) -> Optional[str]:
        """Trouve la connexion à une position donnée en utilisant les coordonnées réelles des objets canvas / Find connection at given position using actual canvas object coordinates"""
        # Parcourir toutes les connexions dessinées / Browse all drawn connections
        for conn_id in self.connection_canvas_objects.keys():
            if conn_id in self.connection_canvas_objects:
                objs = self.connection_canvas_objects[conn_id]
                
                # Vérifier si on clique sur le buffer (rectangle)
                # Check if clicking on buffer (rectangle)
                if 'buffer_rect' in objs and objs['buffer_rect']:
                    coords = self.coords(objs['buffer_rect'])
                    if coords and len(coords) >= 4:
                        x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
                        if x1 <= x <= x2 and y1 <= y <= y2:
                            return conn_id
                
                # Vérifier si on clique sur la ligne elle-même (proximité)
                # Check if clicking on line itself (proximity)
                if 'line' in objs and objs['line']:
                    coords = self.coords(objs['line'])
                    if coords and len(coords) >= 4:
                        # Ligne de (x1,y1) à (x2,y2) / Line from (x1,y1) to (x2,y2)
                        line_x1, line_y1, line_x2, line_y2 = coords[0], coords[1], coords[2], coords[3]
                        # Calculer la distance du point à la ligne
                        # Distance point-à-segment
                        # Calculate distance from point to line
                        # Point-to-segment distance
                        px = line_x2 - line_x1
                        py = line_y2 - line_y1
                        norm = px*px + py*py
                        if norm > 0:
                            u = ((x - line_x1) * px + (y - line_y1) * py) / norm
                            u = max(0, min(1, u))  # Clamper entre 0 et 1 / Clamp between 0 and 1
                            dx = line_x1 + u * px - x
                            dy = line_y1 + u * py - y
                            distance = (dx*dx + dy*dy) ** 0.5
                            # Zone cliquable de 10 pixels autour de la ligne
                            # Clickable area of 10 pixels around line
                            if distance < 10:
                                return conn_id
        return None
    
    def _create_connection(self, source_id: str, target_id: str):
        """Crée une connexion entre deux nœuds / Create a connection between two nodes"""
        connection_id = self.flow_model.generate_connection_id()
        connection = Connection(connection_id, source_id, target_id)
        self.flow_model.add_connection(connection)
        # Dessiner uniquement la nouvelle connexion au lieu de tout redessiner
        # Draw only the new connection instead of redrawing everything
        self.draw_connection(connection)
        # Mettre à jour la scrollregion avec marge étendue
        # Update scrollregion with extended margin
        bbox = self.bbox("all")
        if bbox:
            margin = 5000
            extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                           bbox[2] + margin, bbox[3] + margin)
            self.configure(scrollregion=extended_bbox)
        else:
            self.configure(scrollregion=(-5000, -5000, 5000, 5000))
    
    def _get_time_unit_symbol(self) -> str:
        """Retourne le symbole de l'unité de temps actuelle / Return current time unit symbol"""""
        from models.time_converter import TimeConverter
        return TimeConverter.get_unit_symbol(self.flow_model.current_time_unit)
    
    def delete_selected_node(self):
        """Supprime le nœud sélectionné / Delete selected node"""
        if self.selected_node_id:
            if self.app_config.DEBUG_MODE:
                print(f"[DEBUG] Début suppression nœud: {self.selected_node_id}")
                if self.app_config.DEBUG_MODE:
                    print(f"[DEBUG] Nœuds avant: {list(self.flow_model.nodes.keys())}")
                if self.app_config.DEBUG_MODE:
                    print(f"[DEBUG] Connexions avant: {list(self.flow_model.connections.keys())}")
            
            # Récupérer le nœud avant de le supprimer pour obtenir ses connexions
            # Get node before deleting to get its connections
            node = self.flow_model.get_node(self.selected_node_id)
            if node:
                # Supprimer les pipettes associées aux connexions du nœud
                # Delete probes associated with node's connections
                for conn_id in node.input_connections + node.output_connections:
                    # Trouver et supprimer les probes de cette connexion
                    # Find and delete probes for this connection
                    probes_to_remove = [probe_id for probe_id, probe in self.flow_model.probes.items() 
                                       if probe.connection_id == conn_id]
                    for probe_id in probes_to_remove:
                        if probe_id in self.probe_canvas_objects:
                            objs = self.probe_canvas_objects[probe_id]
                            for obj in objs.values():
                                if obj:
                                    self.delete(obj)
                            del self.probe_canvas_objects[probe_id]
                        # Supprimer aussi par tag / Also delete by tag
                        self.delete(probe_id)
                
                # Supprimer les objets canvas des connexions liées
                # Delete canvas objects of linked connections
                for conn_id in node.input_connections + node.output_connections:
                    if conn_id in self.connection_canvas_objects:
                        for obj in self.connection_canvas_objects[conn_id].values():
                            if obj:
                                self.delete(obj)
                        del self.connection_canvas_objects[conn_id]
                    # Supprimer aussi par tag / Also delete by tag
                    self.delete(conn_id)
                
                # Supprimer les objets canvas du nœud
                # Delete canvas objects of node
                if self.selected_node_id in self.node_canvas_objects:
                    for obj in self.node_canvas_objects[self.selected_node_id].values():
                        if obj:
                            self.delete(obj)
                    del self.node_canvas_objects[self.selected_node_id]
                # Supprimer aussi par tag / Also delete by tag
                self.delete(self.selected_node_id)
            
            # Supprimer du modèle / Delete from model
            self.flow_model.remove_node(self.selected_node_id)
            self.selected_node_id = None
            
            if self.app_config.DEBUG_MODE:
                print(f"[DEBUG] Nœuds après: {list(self.flow_model.nodes.keys())}")
                if self.app_config.DEBUG_MODE:
                    print(f"[DEBUG] Connexions après: {list(self.flow_model.connections.keys())}")
                if self.app_config.DEBUG_MODE:
                    print(f"[DEBUG] Suppression terminée sans redraw_all()")
            
            # Mettre à jour la scrollregion avec marge étendue
            # Update scrollregion with extended margin
            bbox = self.bbox("all")
            if bbox:
                margin = 5000
                extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                               bbox[2] + margin, bbox[3] + margin)
                self.configure(scrollregion=extended_bbox)
            else:
                self.configure(scrollregion=(-5000, -5000, 5000, 5000))
    
    def draw_animated_items(self):
        """Dessine les items en transit (points rouges) sur les connexions / Draw items in transit (red dots) on connections"""
        # Optimisation: au lieu d'effacer et recréer, on déplace les objets existants
        # Optimization: instead of erasing and recreating, move existing objects
        
        # Construire un set des item_ids actuellement en transit
        # Build a set of item_ids currently in transit
        current_items = set()
        
        # Dessiner/mettre à jour les items / Draw/update items
        for connection in self.flow_model.connections.values():
            source_node = self.flow_model.get_node(connection.source_id)
            target_node = self.flow_model.get_node(connection.target_id)
            
            if source_node and target_node:
                # Utiliser le cache de positions pour éviter les appels coûteux coords() (OPTIMISATION)
                # Use position cache to avoid costly coords() calls (OPTIMIZATION)
                source_x, source_y = self._get_node_canvas_position(source_node.node_id)
                if source_x is not None:
                    # Point de sortie : bord droit du nœud / Exit point: right edge of node
                    x1 = source_x + (self.NODE_WIDTH * self.zoom_level) / 2
                    y1 = source_y
                else:
                    # Fallback si cache vide / Fallback if cache empty
                    x1, y1 = source_node.x * self.zoom_level + self.NODE_WIDTH/2, source_node.y * self.zoom_level
                
                target_x, target_y = self._get_node_canvas_position(target_node.node_id)
                if target_x is not None:
                    # Point d'entrée : bord gauche du nœud / Entry point: left edge of node
                    x2 = target_x - (self.NODE_WIDTH * self.zoom_level) / 2
                    y2 = target_y
                else:
                    # Fallback si cache vide / Fallback if cache empty
                    x2, y2 = target_node.x * self.zoom_level - self.NODE_WIDTH/2, target_node.y * self.zoom_level
                
                # Dessiner/mettre à jour chaque item en transit
                # Draw/update each item in transit
                for item_data in connection.items_in_transit:
                    progress = item_data.get('progress', 0.0)
                    item_id = item_data.get('item_id', '')
                    item_type = item_data.get('item_type', None)
                    current_items.add(item_id)
                    
                    # Calculer la position / Calculate position
                    x = x1 + (x2 - x1) * progress
                    y = y1 + (y2 - y1) * progress
                    
                    # Rayon adapté au zoom / Radius adapted to zoom
                    radius = 4 * self.zoom_level
                    
                    # Déterminer la couleur selon le type d'item
                    # Determine color according to item type
                    fill_color = "#FF0000"  # Rouge par défaut / Red by default
                    outline_color = "#CC0000"
                    
                    if item_type:
                        # Utiliser le cache de couleurs (OPTIMISATION)
                        # Use color cache (OPTIMIZATION)
                        cached_color = self._item_type_colors.get(str(item_type))
                        if cached_color:
                            fill_color = cached_color
                            # Assombrir la couleur pour le contour (20% plus sombre)
                            # Darken color for outline (20% darker)
                            try:
                                # Convertir hex en RGB / Convert hex to RGB
                                r = int(fill_color[1:3], 16)
                                g = int(fill_color[3:5], 16)
                                b = int(fill_color[5:7], 16)
                                # Assombrir de 20% / Darken by 20%
                                r = int(r * 0.8)
                                g = int(g * 0.8)
                                b = int(b * 0.8)
                                outline_color = f"#{r:02x}{g:02x}{b:02x}"
                            except:
                                outline_color = fill_color
                    
                    # Si l'item existe déjà, le déplacer et mettre à jour la couleur
                    # If item already exists, move it and update color
                    if item_id in self.animated_items:
                        # Déplacer l'objet existant / Move existing object
                        item_obj = self.animated_items[item_id]
                        try:
                            self.coords(item_obj, x - radius, y - radius, x + radius, y + radius)
                            # Mettre à jour la couleur au cas où le type a changé
                            # Update color in case type changed
                            self.itemconfig(item_obj, fill=fill_color, outline=outline_color)
                        except:
                            # L'objet n'existe plus, le recréer / Object no longer exists, recreate it
                            item_obj = self.create_oval(
                                x - radius, y - radius,
                                x + radius, y + radius,
                                fill=fill_color, outline=outline_color, width=1,
                                tags=("animated_item", item_id)
                            )
                            self.animated_items[item_id] = item_obj
                    else:
                        # Créer un nouvel objet avec la couleur appropriée
                        # Create new object with appropriate color
                        item_obj = self.create_oval(
                            x - radius, y - radius,
                            x + radius, y + radius,
                            fill=fill_color, outline=outline_color, width=1,
                            tags=("animated_item", item_id)
                        )
                        self.animated_items[item_id] = item_obj
        
        # Nettoyer les items qui ne sont plus en transit (OPTIMISATION)
        # Clean up items no longer in transit (OPTIMIZATION)
        items_to_remove = []
        for item_id in self.animated_items:
            if item_id not in current_items:
                try:
                    self.delete(self.animated_items[item_id])
                except:
                    pass
                items_to_remove.append(item_id)
        
        for item_id in items_to_remove:
            del self.animated_items[item_id]
    
    def on_ctrl_click(self, event):
        """Gère Ctrl+Clic pour ajouter une pipette sur une connexion / Handle Ctrl+Click to add a probe on a connection"""
        x, y = event.x, event.y
        
        # Chercher si on clique sur une connexion / Check if clicking on a connection
        conn_id = self._find_connection_at(x, y)
        if conn_id:
            self._add_probe_on_connection(conn_id, x, y)
    
    def _add_probe_on_connection(self, connection_id, x, y):
        """Ajoute une pipette de mesure sur une connexion / Add a measurement probe on a connection"""
        from gui.measurement_probe_config_dialog import MeasurementProbeConfigDialog
        
        # Ouvrir le dialogue de configuration / Open configuration dialog
        def on_save(probe):
            probe.x = x
            probe.y = y
            self.draw_probe(probe)
            if self.on_probe_added:
                self.on_probe_added(probe)
        
        dialog = MeasurementProbeConfigDialog(
            self.master,
            self.flow_model,
            connection_id,
            probe=None,
            on_save=on_save
        )
        self.wait_window(dialog)
    
    def draw_probe(self, probe):
        """Dessine une icône de pipette sur le canvas / Draw a probe icon on canvas"""
        # Supprimer les anciens objets canvas de cette pipette s'ils existent
        # Delete old canvas objects for this probe if they exist
        if probe.probe_id in self.probe_canvas_objects:
            for obj in self.probe_canvas_objects[probe.probe_id].values():
                if obj:
                    self.delete(obj)
        # Supprimer aussi par tag / Also delete by tag
        self.delete(probe.probe_id)
        
        x, y = probe.x, probe.y
        # Taille adaptée au zoom - multipliée par zoom_level comme pour les nœuds
        # Size adapted to zoom - multiplied by zoom_level like for nodes
        size = 12 * self.zoom_level
        
        # Dessiner l'icône (triangle + cercle) / Draw icon (triangle + circle)
        # Cercle / Circle
        circle = self.create_oval(
            x - size, y - size,
            x + size, y + size,
            fill=probe.color, outline="black", width=2,
            tags=("probe", probe.probe_id)
        )
        
        # Triangle (pipette) / Triangle (probe)
        triangle = self.create_polygon(
            x, y - size,
            x - size//2, y,
            x + size//2, y,
            fill="white", outline="black", width=1,
            tags=("probe", probe.probe_id)
        )
        
        # Texte avec le nom (traduit si c'est un nom par défaut) / Text with name (translated if default name)
        # Traduire les noms par défaut "Pipette X" ou "Probe X" selon la langue
        # Translate default names "Pipette X" or "Probe X" according to language
        display_name = probe.name
        import re
        match = re.match(r'^(Pipette|Probe)\s+(\d+)$', probe.name)
        if match:
            from gui.translations import tr
            display_name = f"{tr('probe_label')} {match.group(2)}"
        
        text = self.create_text(
            x, y + size + 10 * self.zoom_level,
            text=display_name,
            font=("Arial", 8, "bold"),
            fill=probe.color,
            tags=("probe", probe.probe_id)
        )
        
        self.probe_canvas_objects[probe.probe_id] = {
            'circle': circle,
            'triangle': triangle,
            'text': text
        }
    
    def draw_annotation(self, annotation):
        """Dessine une annotation (rectangle avec texte) sur le canvas / Draw an annotation (rectangle with text) on canvas"""
        # Supprimer les anciens objets canvas de cette annotation s'ils existent
        # Delete old canvas objects for this annotation if they exist
        if annotation.annotation_id in self.annotation_canvas_objects:
            for obj in self.annotation_canvas_objects[annotation.annotation_id].values():
                if obj:
                    self.delete(obj)
        
        # Calculer les coordonnées / Calculate coordinates
        x1, y1 = annotation.x, annotation.y
        x2, y2 = annotation.x + annotation.width, annotation.y + annotation.height
        
        # Dessiner le rectangle en pointillés / Draw dashed rectangle
        rect = self.create_rectangle(
            x1, y1, x2, y2,
            outline=annotation.color,
            width=self.annotation_line_width,
            dash=self.annotation_dash_pattern,
            tags=("annotation", annotation.annotation_id)
        )
        
        # Dessiner le texte AU-DESSUS du rectangle / Draw text ABOVE rectangle
        text_x = (x1 + x2) / 2
        text_y = y1 - 5  # 5 pixels au-dessus / 5 pixels above
        text = self.create_text(
            text_x, text_y,
            text=annotation.text,
            font=("Arial", annotation.text_size, "bold"),
            fill=annotation.text_color,
            tags=("annotation", annotation.annotation_id, "annotation_text"),
            anchor=tk.S  # Ancre en bas pour être au-dessus / Bottom anchor to be above
        )
        
        # Sauvegarder les références / Save references
        self.annotation_canvas_objects[annotation.annotation_id] = {
            'rect': rect,
            'text': text
        }
    
    def remove_annotation(self, annotation_id):
        """Supprime une annotation du canvas / Remove an annotation from canvas"""""
        if annotation_id in self.annotation_canvas_objects:
            objs = self.annotation_canvas_objects[annotation_id]
            for obj in objs.values():
                self.delete(obj)
            del self.annotation_canvas_objects[annotation_id]
    
    def draw_operator(self, operator):
        """Dessine un opérateur sur le canvas / Draw an operator on canvas"""
        if self.app_config.DEBUG_MODE:
            print(f"\n[DRAW_OP] draw_operator appelé pour {operator.operator_id}:")
            if self.app_config.DEBUG_MODE:
                print(f"  - Coordonnées modèle de l'opérateur: x={operator.x}, y={operator.y}")
            if self.app_config.DEBUG_MODE:
                print(f"  - current_machine_id: {getattr(operator, 'current_machine_id', 'None')}")
            if self.app_config.DEBUG_MODE:
                print(f"  - Zoom actuel: {self.zoom_level}")
        
        # Supprimer l'ancien dessin s'il existe / Delete old drawing if exists
        if operator.operator_id in self.operator_canvas_objects:
            if self.app_config.DEBUG_MODE:
                print(f"  - Suppression de l'ancien dessin")
            self.remove_operator(operator.operator_id)
        
        # Utiliser les coordonnées modèle (non zoomées) - comme pour les nœuds
        # Use model coordinates (not zoomed) - like for nodes
        x = operator.x
        y = operator.y
        
        if self.app_config.DEBUG_MODE:
            print(f"  - Utilisation des coordonnées: x={x}, y={y}")
        
        # Rayon en taille normale (comme NODE_HEIGHT/2)
        # Radius in normal size (like NODE_HEIGHT/2)
        radius = self.NODE_HEIGHT / 2
        
        # Vérifier si l'opérateur est sélectionné / Check if operator is selected
        is_selected = operator.operator_id == self.selected_operator_id
        
        # Dessiner un cercle coloré en coordonnées modèle
        # Draw colored circle in model coordinates
        circle = self.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=self.SELECTED_COLOR if is_selected else operator.color,
            outline="#FF4500" if is_selected else "#333333",
            width=2 if is_selected else 1,
            tags=("operator", operator.operator_id)
        )
        
        # Dessiner le texte O[i] en taille normale (le zoom sera appliqué via scale)
        op_num = operator.operator_id.replace("op_", "")
        text = self.create_text(
            x, y,
            text=f"O[{op_num}]",
            font=("Arial", 10, "bold"),  # Taille normale, pas multipliée par zoom
            fill="#FFFFFF",
            tags=("operator", operator.operator_id, "operator_text")
        )
        
        # Sauvegarder les références
        self.operator_canvas_objects[operator.operator_id] = {
            'circle': circle,
            'text': text
        }
        
        if self.app_config.DEBUG_MODE:
            print(f"  - Objets canvas créés: circle={circle}, text={text}")
        
        # Lire les coordonnées avant scale / Read coordinates before scale
        if self.app_config.DEBUG_MODE:
            coords_before = self.coords(circle)
            if self.app_config.DEBUG_MODE:
                print(f"  - Coordonnées circle AVANT scale: {coords_before}")
        
        # Appliquer le zoom si nécessaire (comme pour les nœuds)
        # Apply zoom if necessary (like for nodes)
        if self.zoom_level != 1.0:
            if self.app_config.DEBUG_MODE:
                print(f"  - Application du scale avec zoom_level={self.zoom_level}")
            self.scale(circle, 0, 0, self.zoom_level, self.zoom_level)
            self.scale(text, 0, 0, self.zoom_level, self.zoom_level)
            
            # Lire les coordonnées après scale / Read coordinates after scale
            if self.app_config.DEBUG_MODE:
                coords_after = self.coords(circle)
                center_x = (coords_after[0] + coords_after[2]) / 2
                center_y = (coords_after[1] + coords_after[3]) / 2
                if self.app_config.DEBUG_MODE:
                    print(f"  - Coordonnées circle APRÈS scale: {coords_after}")
                if self.app_config.DEBUG_MODE:
                    print(f"  - Centre de l'opérateur sur canvas: x={center_x}, y={center_y}")
        else:
            if self.app_config.DEBUG_MODE:
                print(f"  - Pas de scale nécessaire (zoom=1.0)")
    
    def redraw_operator(self, operator):
        """Redessine un opérateur individuel en préservant sa position canvas / Redraw an individual operator while preserving its canvas position"""""
        if self.app_config.DEBUG_MODE:
            print(f"\n[REDRAW_OP] Début redraw pour {operator.operator_id}, zoom={self.zoom_level:.3f}")
        
        # ÉTAPE 1: Récupérer les coordonnées canvas actuelles (après zoom) du cercle
        # STEP 1: Get current canvas coordinates (after zoom) of circle
        canvas_coords = None
        canvas_center_x = None
        canvas_center_y = None
        
        if operator.operator_id in self.operator_canvas_objects:
            circle = self.operator_canvas_objects[operator.operator_id].get('circle')
            if circle:
                coords = self.coords(circle)
                if coords:
                    # Coordonnées canvas du cercle: [x1, y1, x2, y2]
                    # Canvas coordinates of circle: [x1, y1, x2, y2]
                    canvas_coords = coords
                    canvas_center_x = (coords[0] + coords[2]) / 2
                    canvas_center_y = (coords[1] + coords[3]) / 2
                    if self.app_config.DEBUG_MODE:
                        print(f"  [1] Position canvas avant: center=({canvas_center_x:.2f}, {canvas_center_y:.2f})")
        
        # ÉTAPE 2: Supprimer l'ancien opérateur / STEP 2: Delete old operator
        if operator.operator_id in self.operator_canvas_objects:
            objs = self.operator_canvas_objects[operator.operator_id]
            for obj in objs.values():
                if obj:
                    self.delete(obj)
            del self.operator_canvas_objects[operator.operator_id]
        
        # ÉTAPE 3: Créer le nouveau opérateur en coordonnées modèle (SANS scale automatique)
        # STEP 3: Create new operator in model coordinates (WITHOUT automatic scale)
        if self.app_config.DEBUG_MODE:
            print(f"  [3] Dessin du nouvel opérateur en coordonnées modèle: ({operator.x:.2f}, {operator.y:.2f})")
        
        # Dessiner manuellement sans passer par draw_operator() qui applique déjà le scale
        # Draw manually without using draw_operator() which already applies scale
        x = operator.x
        y = operator.y
        radius = self.NODE_HEIGHT / 2
        is_selected = operator.operator_id == self.selected_operator_id
        
        # Dessiner le cercle et le texte en coordonnées modèle (taille normale)
        # Draw circle and text in model coordinates (normal size)
        circle = self.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=self.SELECTED_COLOR if is_selected else operator.color,
            outline="#FF4500" if is_selected else "#333333",
            width=2 if is_selected else 1,
            tags=("operator", operator.operator_id)
        )
        
        op_num = operator.operator_id.replace("op_", "")
        text = self.create_text(
            x, y,
            text=f"O[{op_num}]",
            font=("Arial", 10, "bold"),
            fill="#FFFFFF",
            tags=("operator", operator.operator_id, "operator_text")
        )
        
        # Sauvegarder les références / Save references
        self.operator_canvas_objects[operator.operator_id] = {
            'circle': circle,
            'text': text
        }
        
        # ÉTAPE 4: Si zoom actif, appliquer le zoom sur les nouveaux éléments (UNE SEULE FOIS)
        # STEP 4: If zoom active, apply zoom on new elements (ONLY ONCE)
        if self.zoom_level != 1.0:
            if self.app_config.DEBUG_MODE:
                print(f"  [4] Application du scale({self.zoom_level:.3f}) autour de (0,0)")
            self.scale(circle, 0, 0, self.zoom_level, self.zoom_level)
            self.scale(text, 0, 0, self.zoom_level, self.zoom_level)
        
        # ÉTAPE 5: Si on avait des coords canvas, ajuster la position finale
        # STEP 5: If we had canvas coords, adjust final position
        if canvas_coords and canvas_center_x is not None and self.zoom_level != 1.0:
            # Obtenir les nouvelles coords du cercle après zoom
            # Get new circle coords after zoom
            new_coords = self.coords(circle)
            if new_coords:
                new_center_x = (new_coords[0] + new_coords[2]) / 2
                new_center_y = (new_coords[1] + new_coords[3]) / 2
                if self.app_config.DEBUG_MODE:
                    print(f"  [5] Position canvas après redraw+scale: center=({new_center_x:.2f}, {new_center_y:.2f})")
                
                # Calculer le décalage / Calculate offset
                delta_x = canvas_center_x - new_center_x
                delta_y = canvas_center_y - new_center_y
                if self.app_config.DEBUG_MODE:
                    print(f"  [5] Delta nécessaire: ({delta_x:.2f}, {delta_y:.2f})")
                
                # Déplacer tous les éléments de l'opérateur
                # Move all operator elements
                if abs(delta_x) > 0.1 or abs(delta_y) > 0.1:
                    self.move(circle, delta_x, delta_y)
                    self.move(text, delta_x, delta_y)
                    if self.app_config.DEBUG_MODE:
                        print(f"  [5] Opérateur déplacé de ({delta_x:.2f}, {delta_y:.2f})")
        
        if self.app_config.DEBUG_MODE:
            print(f"[REDRAW_OP] Fin redraw pour {operator.operator_id}\n")
    
    def update_operator_position(self, operator):
        """Met à jour la position d'un opérateur existant en suivant les positions canvas réelles des nœuds / Update an existing operator's position by following actual canvas positions of nodes"""
        if operator.operator_id not in self.operator_canvas_objects:
            # L'opérateur n'existe pas encore, le dessiner
            # Operator doesn't exist yet, draw it
            if self.app_config.DEBUG_MODE:
                print(f"[UPDATE_OP] {operator.operator_id} n'existe pas sur canvas, appel à draw_operator()")
            self.draw_operator(operator)
            return
        
        objs = self.operator_canvas_objects[operator.operator_id]
        circle = objs.get('circle')
        
        if circle:
            # Lire la position ACTUELLE sur le canvas / Read CURRENT position on canvas
            coords = self.coords(circle)
            current_canvas_x = (coords[0] + coords[2]) / 2
            current_canvas_y = (coords[1] + coords[3]) / 2
            
            # Obtenir la position canvas CIBLE en lisant les nœuds réels
            # Get TARGET canvas position by reading actual nodes
            target_canvas_x, target_canvas_y = self._get_operator_target_position(operator)
            
            # Calculer le delta / Calculate delta
            dx_canvas = target_canvas_x - current_canvas_x
            dy_canvas = target_canvas_y - current_canvas_y
            
            # Ne déplacer que si le delta dépasse le seuil configuré (évite micro-mouvements)
            # Only move if delta exceeds configured threshold (avoids micro-movements)
            if abs(dx_canvas) > self.app_config.OPERATOR_MOVEMENT_THRESHOLD or abs(dy_canvas) > self.app_config.OPERATOR_MOVEMENT_THRESHOLD:
                # Logger uniquement en mode debug / Log only in debug mode
                if self.app_config.DEBUG_MODE:
                    print(f"[UPDATE_OP] {operator.operator_id}: déplacement de dx={dx_canvas:.2f}, dy={dy_canvas:.2f}")
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Position actuelle canvas: ({current_canvas_x:.2f}, {current_canvas_y:.2f})")
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Position cible canvas: ({target_canvas_x:.2f}, {target_canvas_y:.2f})")
                    if self.app_config.DEBUG_MODE:
                        print(f"  - Position modèle opérateur: ({operator.x:.2f}, {operator.y:.2f})")
                
                # Déplacer tous les objets de l'opérateur / Move all operator objects
                for obj in objs.values():
                    if obj:
                        self.move(obj, dx_canvas, dy_canvas)
        else:
            # Si le cercle n'existe pas, redessiner complètement
            # If circle doesn't exist, redraw completely
            if self.app_config.DEBUG_MODE:
                print(f"[UPDATE_OP] {operator.operator_id} cercle manquant, redessinage complet")
            self.draw_operator(operator)
    
    def _get_node_canvas_position(self, node_id: str) -> Tuple[Optional[float], Optional[float]]:
        """Lit la position canvas d'un nœud avec cache pour optimiser les performances
        Read a node's canvas position with cache to optimize performance
        
        Args:
            node_id: ID du nœud dont on veut la position / Node ID to get position for
            
        Returns:
            Tuple (x, y) de la position canvas, ou (None, None) si introuvable
            Tuple (x, y) of canvas position, or (None, None) if not found
        """
        now = time.time()
        
        # Vérifier le cache / Check cache
        if node_id in self._node_positions_cache:
            x, y, timestamp = self._node_positions_cache[node_id]
            if (now - timestamp) < self._cache_validity_seconds:
                return x, y
        
        # Cache expiré ou pas dans le cache, lire la position réelle
        # Cache expired or not in cache, read actual position
        if node_id in self.node_canvas_objects:
            rect = self.node_canvas_objects[node_id].get('rect')
            if rect:
                rect_coords = self.coords(rect)
                if rect_coords and len(rect_coords) >= 4:
                    x = (rect_coords[0] + rect_coords[2]) / 2
                    y = (rect_coords[1] + rect_coords[3]) / 2
                    # Mettre en cache / Put in cache
                    self._node_positions_cache[node_id] = (x, y, now)
                    return x, y
        
        return None, None
    
    def _invalidate_node_position_cache(self, node_id: Optional[str] = None):
        """Invalide le cache des positions des nœuds / Invalidate node positions cache
        
        Args:
            node_id: ID du nœud à invalider, ou None pour tout invalider
                     Node ID to invalidate, or None to invalidate all
        """
        if node_id:
            self._node_positions_cache.pop(node_id, None)
        else:
            self._node_positions_cache.clear()
    
    def _get_operator_target_position(self, operator):
        """Calcule la position canvas cible de l'opérateur en lisant les positions réelles des nœuds
        
        Calculates operator target canvas position by reading actual node positions"""
        if self.app_config.DEBUG_MODE:
            print(f"[TARGET_POS] Calcul position cible pour {operator.operator_id}:")
            if self.app_config.DEBUG_MODE:
                print(f"  - animation_from_node: {getattr(operator, 'animation_from_node', 'None')}")
            if self.app_config.DEBUG_MODE:
                print(f"  - animation_to_node: {getattr(operator, 'animation_to_node', 'None')}")
            if self.app_config.DEBUG_MODE:
                print(f"  - current_machine_id: {getattr(operator, 'current_machine_id', 'None')}")
        
        # Si l'opérateur est en animation entre deux nœuds, interpoler entre leurs positions canvas réelles
        # If operator is animating between two nodes, interpolate between their actual canvas positions
        if (hasattr(operator, 'animation_from_node') and operator.animation_from_node and 
            hasattr(operator, 'animation_to_node') and operator.animation_to_node and
            hasattr(operator, 'animation_progress')):
            
            from_node = self.flow_model.get_node(operator.animation_from_node)
            to_node = self.flow_model.get_node(operator.animation_to_node)
            
            if from_node and to_node:
                # Lire les positions canvas avec cache / Read canvas positions with cache
                from_x, from_y = self._get_node_canvas_position(from_node.node_id)
                to_x, to_y = self._get_node_canvas_position(to_node.node_id)
                
                # Interpoler entre les deux positions canvas réelles
                # Interpolate between the two actual canvas positions
                
                # Interpoler entre les deux positions canvas réelles
                if from_x is not None and to_x is not None:
                    progress = operator.animation_progress
                    target_x = from_x + (to_x - from_x) * progress
                    target_y = from_y + (to_y - from_y) * progress
                    if self.app_config.DEBUG_MODE:
                        print(f"  - CHEMIN: Animation (progress={progress:.2f})")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Position cible: ({target_x:.2f}, {target_y:.2f})")
                    return target_x, target_y
        
        # Si l'opérateur a une machine actuelle, lire sa position canvas
        # If operator has a current machine, read its canvas position
        if hasattr(operator, 'current_machine_id') and operator.current_machine_id:
            node = self.flow_model.get_node(operator.current_machine_id)
            if node:
                # Utiliser le cache pour la position / Use cache for position
                center_x, center_y = self._get_node_canvas_position(node.node_id)
                if center_x is not None:
                    if self.app_config.DEBUG_MODE:
                        print(f"  - CHEMIN: Machine actuelle ({operator.current_machine_id})")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Position nœud canvas: ({center_x:.2f}, {center_y:.2f})")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Position nœud modèle: ({node.x:.2f}, {node.y:.2f})")
                    return center_x, center_y
        
        # Fallback : lire la position canvas réelle de l'opérateur depuis ses objets canvas
        # Fallback: read actual canvas position of operator from its canvas objects
        if operator.operator_id in self.operator_canvas_objects:
            objs = self.operator_canvas_objects[operator.operator_id]
            circle = objs.get('circle')
            if circle:
                coords = self.coords(circle)
                if coords and len(coords) >= 4:
                    center_x = (coords[0] + coords[2]) / 2
                    center_y = (coords[1] + coords[3]) / 2
                    if self.app_config.DEBUG_MODE:
                        print(f"  - CHEMIN: Fallback opérateur canvas")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Position: ({center_x:.2f}, {center_y:.2f})")
                    return center_x, center_y
        
        # Dernier fallback : utiliser les coordonnées modèle (draw_operator appliquera le zoom)
        # Last fallback: use model coordinates (draw_operator will apply zoom)
        if self.app_config.DEBUG_MODE:
            print(f"  - CHEMIN: Dernier fallback (coordonnées modèle)")
            if self.app_config.DEBUG_MODE:
                print(f"  - Position: ({operator.x:.2f}, {operator.y:.2f})")
        return operator.x, operator.y
    
    def remove_operator(self, operator_id):
        """Supprime un opérateur du canvas / Remove an operator from canvas"""""
        if operator_id in self.operator_canvas_objects:
            objs = self.operator_canvas_objects[operator_id]
            for obj in objs.values():
                self.delete(obj)
            del self.operator_canvas_objects[operator_id]
    
    def remove_probe(self, probe_id):
        """Supprime une pipette du canvas / Remove a probe from canvas"""
        # Supprimer les objets canvas / Delete canvas objects
        if probe_id in self.probe_canvas_objects:
            objs = self.probe_canvas_objects[probe_id]
            for obj in objs.values():
                if obj:
                    self.delete(obj)
            del self.probe_canvas_objects[probe_id]
        
        # Supprimer aussi par tag pour être sûr / Also delete by tag to be sure
        self.delete(probe_id)
        
        # Supprimer du modèle / Delete from model
        if probe_id in self.flow_model.probes:
            self.flow_model.remove_probe(probe_id)
            
            if self.on_probe_removed:
                self.on_probe_removed(probe_id)
    
    def redraw_probes(self):
        """Redessine toutes les pipettes / Redraw all probes"""
        # Supprimer les anciennes / Delete old ones
        for probe_id in list(self.probe_canvas_objects.keys()):
            objs = self.probe_canvas_objects[probe_id]
            for obj in objs.values():
                self.delete(obj)
        self.probe_canvas_objects.clear()
        
        # Redessiner / Redraw
        for probe in self.flow_model.probes.values():
            self.draw_probe(probe)
    
    def on_mouse_wheel(self, event):
        """Gère le zoom avec molette de souris / Handle zoom with mouse wheel"""
        # Obtenir la position de la souris sur le canvas
        # Get mouse position on canvas
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        
        if event.delta > 0:
            self.zoom_in_view(x, y)
        else:
            self.zoom_out_view(x, y)
    
    def zoom_in_view(self, x=None, y=None):
        """Zoom avant / Zoom in"""
        # Effacer la sélection multiple pour éviter les incohérences visuelles
        # Clear multi-selection to avoid visual inconsistencies
        self._clear_multi_selection()
        
        factor = 1.1
        if self.zoom_level * factor > self.zoom_max:
            factor = self.zoom_max / self.zoom_level
        
        if factor > 1.0 and factor != 1.0:
            # Sauvegarder la position relative de la souris dans le viewport
            # Save relative mouse position in viewport
            if x is None or y is None:
                x = self.canvasx(self.winfo_width() / 2)
                y = self.canvasy(self.winfo_height() / 2)
            
            # Appliquer le zoom à TOUS les objets (y compris les opérateurs)
            # Apply zoom to ALL objects (including operators)
            self.scale("all", x, y, factor, factor)
            self.zoom_level *= factor
            
            # Invalider le cache des positions car toutes les positions ont changé
            # Invalidate position cache since all positions changed
            self._invalidate_node_position_cache()
            
            # Mettre à jour la scrollregion avec marge étendue
            # Update scrollregion with extended margin
            bbox = self.bbox("all")
            if bbox:
                margin = 5000
                extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                               bbox[2] + margin, bbox[3] + margin)
                self.configure(scrollregion=extended_bbox)
            else:
                self.configure(scrollregion=(-5000, -5000, 5000, 5000))
    
    def zoom_out_view(self, x=None, y=None):
        """Zoom arrière / Zoom out"""
        # Effacer la sélection multiple pour éviter les incohérences visuelles
        # Clear multi-selection to avoid visual inconsistencies
        self._clear_multi_selection()
        
        factor = 1.0 / 1.1
        if self.zoom_level * factor < self.zoom_min:
            factor = self.zoom_min / self.zoom_level
        
        if factor < 1.0 and factor != 1.0:
            # Sauvegarder la position relative de la souris dans le viewport
            # Save relative mouse position in viewport
            if x is None or y is None:
                x = self.canvasx(self.winfo_width() / 2)
                y = self.canvasy(self.winfo_height() / 2)
            
            # Appliquer le zoom à TOUS les objets (y compris les opérateurs)
            # Apply zoom to ALL objects (including operators)
            self.scale("all", x, y, factor, factor)
            self.zoom_level *= factor
            
            # Invalider le cache des positions car toutes les positions ont changé
            # Invalidate position cache since all positions changed
            self._invalidate_node_position_cache()
            
            # Mettre à jour la scrollregion avec marge étendue
            # Update scrollregion with extended margin
            bbox = self.bbox("all")
            if bbox:
                margin = 5000
                extended_bbox = (bbox[0] - margin, bbox[1] - margin, 
                               bbox[2] + margin, bbox[3] + margin)
                self.configure(scrollregion=extended_bbox)
            else:
                self.configure(scrollregion=(-5000, -5000, 5000, 5000))
    
    def center_view_on_content(self):
        """Centre la vue au milieu du canvas / Center view in the middle of canvas"""
        # Obtenir les dimensions du scrollregion / Get scrollregion dimensions
        scrollregion = self.cget('scrollregion')
        if not scrollregion:
            return
        
        x1, y1, x2, y2 = map(float, scrollregion.split())
        
        # Centre du scrollregion / Center of scrollregion
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Dimensions du canvas visible / Visible canvas dimensions
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()
        
        # Dimensions totales du scrollregion / Total scrollregion dimensions
        scroll_width = x2 - x1
        scroll_height = y2 - y1
        
        # Calculer la position de scroll pour centrer
        # Calculate scroll position to center
        if scroll_width > canvas_width:
            scroll_x = (center_x - x1 - canvas_width / 2) / (scroll_width - canvas_width)
        else:
            scroll_x = 0
            
        if scroll_height > canvas_height:
            scroll_y = (center_y - y1 - canvas_height / 2) / (scroll_height - canvas_height)
        else:
            scroll_y = 0
        
        # Appliquer le scroll / Apply scroll
        self.xview_moveto(max(0, min(1, scroll_x)))
        self.yview_moveto(max(0, min(1, scroll_y)))
    
    def _reposition_operators_after_zoom(self):
        """Repositionne les opérateurs après un zoom en les redessinant aux coordonnées exactes / Reposition operators after zoom by redrawing at exact coordinates"""
        if not hasattr(self, 'flow_model') or not self.flow_model:
            return
        
        # Redessiner chaque opérateur pour qu'il soit exactement à modèle × zoom
        for operator in self.flow_model.operators.values():
            if operator.operator_id in self.operator_canvas_objects:
                # Supprimer l'ancien dessin (qui a été transformé par scale)
                self.remove_operator(operator.operator_id)
                # Redessiner aux coordonnées exactes
                self.draw_operator(operator)
    
    def _old_reposition_operators_after_zoom(self):
        """Repositionne tous les opérateurs après un zoom pour corriger leur position / Reposition all operators after zoom to correct their position"""
        if self.app_config.DEBUG_MODE:
            print(f"\n[ZOOM_DEBUG] _reposition_operators_after_zoom appelé")
        # Récupérer la liste des opérateurs depuis le flow_model
        # Get list of operators from flow_model
        if not hasattr(self, 'flow_model') or not self.flow_model:
            if self.app_config.DEBUG_MODE:
                print(f"  Pas de flow_model, retour")
            return
        
        if self.app_config.DEBUG_MODE:
            print(f"  Nombre d'opérateurs à repositionner: {len(self.flow_model.operators)}")
        # Repositionner chaque opérateur aux coordonnées exactes
        # Reposition each operator to exact coordinates
        for operator in self.flow_model.operators.values():
            if operator.operator_id in self.operator_canvas_objects:
                objs = self.operator_canvas_objects[operator.operator_id]
                circle = objs.get('circle')
                
                if circle:
                    # Calculer où l'opérateur DEVRAIT être
                    # Calculate where operator SHOULD be
                    target_x = operator.x * self.zoom_level
                    target_y = operator.y * self.zoom_level
                    
                    # Obtenir où il EST actuellement (après le scale)
                    # Get where it IS currently (after scale)
                    coords = self.coords(circle)
                    current_x = (coords[0] + coords[2]) / 2
                    current_y = (coords[1] + coords[3]) / 2
                    
                    # Calculer le déplacement nécessaire / Calculate necessary displacement
                    dx = target_x - current_x
                    dy = target_y - current_y
                    
                    if self.app_config.DEBUG_MODE:
                        print(f"  {operator.name}: current=({current_x:.2f}, {current_y:.2f}), target=({target_x:.2f}, {target_y:.2f}), delta=({dx:.2f}, {dy:.2f})")
                    
                    # Déplacer tous les objets de l'opérateur
                    # Move all operator objects
                    for obj in objs.values():
                        if obj:
                            self.move(obj, dx, dy)
        
        if self.app_config.DEBUG_MODE:
            print(f"[ZOOM_DEBUG] _reposition_operators_after_zoom terminé\n")

    # === SÉLECTION MULTIPLE / MULTI-SELECTION ===
    
    def _clear_multi_selection(self):
        """Efface la sélection multiple courante / Clear current multi-selection"""
        # Supprimer le rectangle de sélection s'il existe
        # Delete selection rectangle if it exists
        if self.multi_selection_rect:
            try:
                self.delete(self.multi_selection_rect)
            except:
                pass
            self.multi_selection_rect = None
        
        # Réinitialiser les variables / Reset variables
        self.multi_selection_active = False
        self.multi_selection_start = None
        self.multi_drag_active = False
        
        # Retirer le surlignage des éléments sélectionnés (utiliser list() pour éviter erreurs pendant l'itération)
        # Remove highlighting from selected elements (use list() to avoid errors during iteration)
        for node_id in list(self.selected_nodes):
            self._unhighlight_element("node", node_id)
        for operator_id in list(self.selected_operators):
            self._unhighlight_element("operator", operator_id)
        for probe_id in list(self.selected_probes):
            self._unhighlight_element("probe", probe_id)
        for annotation_id in list(self.selected_annotations):
            self._unhighlight_element("annotation", annotation_id)
        
        # Vider les sets / Clear sets
        self.selected_nodes.clear()
        self.selected_operators.clear()
        self.selected_probes.clear()
        self.selected_annotations.clear()
    
    def _is_in_multi_selection(self, x: float, y: float) -> bool:
        """Vérifie si le clic est sur un élément de la sélection multiple / Check if click is on a multi-selection element"""
        # Vérifier les nœuds - utiliser les vraies coordonnées canvas
        # Check nodes - use actual canvas coordinates
        for node_id in self.selected_nodes:
            if node_id in self.node_canvas_objects:
                objs = self.node_canvas_objects[node_id]
                if 'rect' in objs and objs['rect']:
                    coords = self.coords(objs['rect'])
                    if coords and len(coords) >= 4:
                        bx1, by1, bx2, by2 = coords[0], coords[1], coords[2], coords[3]
                        if bx1 <= x <= bx2 and by1 <= y <= by2:
                            return True
        
        # Vérifier les opérateurs - utiliser les vraies coordonnées canvas
        # Check operators - use actual canvas coordinates
        for operator_id in self.selected_operators:
            if operator_id in self.operator_canvas_objects:
                objs = self.operator_canvas_objects[operator_id]
                if 'circle' in objs and objs['circle']:
                    coords = self.coords(objs['circle'])
                    if coords and len(coords) >= 4:
                        # Centre du cercle / Circle center
                        ox = (coords[0] + coords[2]) / 2
                        oy = (coords[1] + coords[3]) / 2
                        radius = (coords[2] - coords[0]) / 2
                        if ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 <= radius:
                            return True
        
        # Vérifier les pipettes - utiliser les vraies coordonnées canvas
        # Check probes - use actual canvas coordinates
        for probe_id in self.selected_probes:
            if probe_id in self.probe_canvas_objects:
                objs = self.probe_canvas_objects[probe_id]
                if 'circle' in objs and objs['circle']:
                    coords = self.coords(objs['circle'])
                    if coords and len(coords) >= 4:
                        # Centre du cercle / Circle center
                        px = (coords[0] + coords[2]) / 2
                        py = (coords[1] + coords[3]) / 2
                        radius = (coords[2] - coords[0]) / 2
                        if ((x - px) ** 2 + (y - py) ** 2) ** 0.5 <= radius:
                            return True
        
        # Vérifier les annotations - utiliser les vraies coordonnées canvas
        # Check annotations - use actual canvas coordinates
        for annotation_id in self.selected_annotations:
            if annotation_id in self.annotation_canvas_objects:
                objs = self.annotation_canvas_objects[annotation_id]
                if 'rect' in objs and objs['rect']:
                    coords = self.coords(objs['rect'])
                    if coords and len(coords) >= 4:
                        ax1, ay1, ax2, ay2 = coords[0], coords[1], coords[2], coords[3]
                        if ax1 <= x <= ax2 and ay1 <= y <= ay2:
                            return True
        
        return False
    
    def _update_multi_selection_rect(self, current_x: float, current_y: float):
        """Met à jour le rectangle de sélection pendant le drag / Update selection rectangle during drag"""
        if not self.multi_selection_start:
            return
        
        start_x, start_y = self.multi_selection_start
        
        # Supprimer l'ancien rectangle / Delete old rectangle
        if self.multi_selection_rect:
            self.delete(self.multi_selection_rect)
        
        # Créer le nouveau rectangle en pointillés / Create new dashed rectangle
        self.multi_selection_rect = self.create_rectangle(
            start_x, start_y, current_x, current_y,
            outline="#0078D4",  # Bleu Windows / Windows blue
            width=2,
            dash=(5, 5),  # Pointillés / Dashed
            fill=""  # Transparent
        )
    
    def _finalize_multi_selection(self, end_x: float, end_y: float):
        """Finalise la sélection multiple et sélectionne les éléments dans le rectangle / Finalize multi-selection and select elements in rectangle"""
        if not self.multi_selection_start:
            return
        
        start_x, start_y = self.multi_selection_start
        
        # Normaliser les coordonnées (coin supérieur gauche et inférieur droit)
        # Normalize coordinates (upper left and lower right corners)
        x1 = min(start_x, end_x)
        y1 = min(start_y, end_y)
        x2 = max(start_x, end_x)
        y2 = max(start_y, end_y)
        
        # Supprimer le rectangle de sélection / Delete selection rectangle
        if self.multi_selection_rect:
            self.delete(self.multi_selection_rect)
            self.multi_selection_rect = None
        
        self.multi_selection_active = False
        self.multi_selection_start = None
        
        # Trouver tous les éléments dans le rectangle / Find all elements in rectangle
        self._select_elements_in_rect(x1, y1, x2, y2)
    
    def _select_elements_in_rect(self, x1: float, y1: float, x2: float, y2: float):
        """Sélectionne tous les éléments dont le centre est dans le rectangle / Select all elements whose center is in rectangle"""
        # Sélectionner les nœuds - utiliser les vraies coordonnées canvas
        # Select nodes - use actual canvas coordinates
        for node_id, node in self.flow_model.nodes.items():
            if node_id in self.node_canvas_objects:
                objs = self.node_canvas_objects[node_id]
                if 'rect' in objs and objs['rect']:
                    coords = self.coords(objs['rect'])
                    if coords and len(coords) >= 4:
                        # Centre du rectangle / Rectangle center
                        nx = (coords[0] + coords[2]) / 2
                        ny = (coords[1] + coords[3]) / 2
                        if x1 <= nx <= x2 and y1 <= ny <= y2:
                            self.selected_nodes.add(node_id)
                            self._highlight_element("node", node_id)
        
        # Sélectionner les opérateurs - utiliser les vraies coordonnées canvas
        # Select operators - use actual canvas coordinates
        for operator_id, operator in self.flow_model.operators.items():
            if operator_id in self.operator_canvas_objects:
                objs = self.operator_canvas_objects[operator_id]
                if 'circle' in objs and objs['circle']:
                    coords = self.coords(objs['circle'])
                    if coords and len(coords) >= 4:
                        ox = (coords[0] + coords[2]) / 2
                        oy = (coords[1] + coords[3]) / 2
                        if x1 <= ox <= x2 and y1 <= oy <= y2:
                            self.selected_operators.add(operator_id)
                            self._highlight_element("operator", operator_id)
        
        # Sélectionner les pipettes - utiliser les vraies coordonnées canvas
        # Select probes - use actual canvas coordinates
        for probe_id, probe in self.flow_model.probes.items():
            if probe_id in self.probe_canvas_objects:
                objs = self.probe_canvas_objects[probe_id]
                if 'circle' in objs and objs['circle']:
                    coords = self.coords(objs['circle'])
                    if coords and len(coords) >= 4:
                        px = (coords[0] + coords[2]) / 2
                        py = (coords[1] + coords[3]) / 2
                        if x1 <= px <= x2 and y1 <= py <= y2:
                            self.selected_probes.add(probe_id)
                            self._highlight_element("probe", probe_id)
        
        # Sélectionner les annotations - utiliser les vraies coordonnées canvas
        # Select annotations - use actual canvas coordinates
        for annotation_id, annotation in self.flow_model.annotations.items():
            if annotation_id in self.annotation_canvas_objects:
                objs = self.annotation_canvas_objects[annotation_id]
                if 'rect' in objs and objs['rect']:
                    coords = self.coords(objs['rect'])
                    if coords and len(coords) >= 4:
                        # Centre de l'annotation / Annotation center
                        ax = (coords[0] + coords[2]) / 2
                        ay = (coords[1] + coords[3]) / 2
                        if x1 <= ax <= x2 and y1 <= ay <= y2:
                            self.selected_annotations.add(annotation_id)
                            self._highlight_element("annotation", annotation_id)
                self.selected_annotations.add(annotation_id)
                self._highlight_element("annotation", annotation_id)
        
        # Log pour debug / Log for debug
        total_selected = len(self.selected_nodes) + len(self.selected_operators) + len(self.selected_probes) + len(self.selected_annotations)
        if total_selected > 0 and self.app_config.DEBUG_MODE:
            print(f"[MULTI_SELECT] Sélectionné: {len(self.selected_nodes)} nœuds, {len(self.selected_operators)} opérateurs, {len(self.selected_probes)} pipettes, {len(self.selected_annotations)} annotations")
    
    def _highlight_element(self, element_type: str, element_id: str):
        """Surligne un élément pour indiquer qu'il fait partie de la sélection multiple / Highlight an element to indicate it's part of multi-selection"""
        if element_type == "node":
            if element_id in self.node_canvas_objects:
                objs = self.node_canvas_objects[element_id]
                if 'rect' in objs and objs['rect']:
                    self.itemconfig(objs['rect'], outline="#0078D4", width=4)
        
        elif element_type == "operator":
            if element_id in self.operator_canvas_objects:
                objs = self.operator_canvas_objects[element_id]
                if 'circle' in objs and objs['circle']:
                    self.itemconfig(objs['circle'], outline="#0078D4", width=4)
        
        elif element_type == "probe":
            if element_id in self.probe_canvas_objects:
                objs = self.probe_canvas_objects[element_id]
                if 'circle' in objs and objs['circle']:
                    self.itemconfig(objs['circle'], outline="#0078D4", width=3)
        
        elif element_type == "annotation":
            if element_id in self.annotation_canvas_objects:
                objs = self.annotation_canvas_objects[element_id]
                if 'rect' in objs and objs['rect']:
                    self.itemconfig(objs['rect'], outline="#0078D4", width=4)
    
    def _unhighlight_element(self, element_type: str, element_id: str):
        """Retire le surlignage d'un élément / Remove highlighting from an element"""
        if element_type == "node":
            if element_id in self.node_canvas_objects:
                objs = self.node_canvas_objects[element_id]
                if 'rect' in objs and objs['rect']:
                    self.itemconfig(objs['rect'], outline="#333333", width=2)
        
        elif element_type == "operator":
            if element_id in self.operator_canvas_objects:
                objs = self.operator_canvas_objects[element_id]
                if 'circle' in objs and objs['circle']:
                    operator = self.flow_model.get_operator(element_id)
                    if operator:
                        self.itemconfig(objs['circle'], outline="#333333", width=2)
        
        elif element_type == "probe":
            if element_id in self.probe_canvas_objects:
                objs = self.probe_canvas_objects[element_id]
                if 'circle' in objs and objs['circle']:
                    self.itemconfig(objs['circle'], outline="#333333", width=2)
        
        elif element_type == "annotation":
            if element_id in self.annotation_canvas_objects:
                objs = self.annotation_canvas_objects[element_id]
                if 'rect' in objs and objs['rect']:
                    annotation = self.flow_model.annotations.get(element_id)
                    if annotation:
                        self.itemconfig(objs['rect'], outline=annotation.color, width=self.annotation_line_width)
    
    def _move_multi_selection(self, dx: float, dy: float):
        """Déplace tous les éléments de la sélection multiple / Move all elements of multi-selection"""
        # Convertir le delta en coordonnées modèle / Convert delta to model coordinates
        dx_model = dx / self.zoom_level
        dy_model = dy / self.zoom_level
        
        # Déplacer les nœuds / Move nodes
        for node_id in self.selected_nodes:
            node = self.flow_model.get_node(node_id)
            if node:
                node.x += dx_model
                node.y += dy_model
                # Déplacer les objets canvas / Move canvas objects
                if node_id in self.node_canvas_objects:
                    for obj in self.node_canvas_objects[node_id].values():
                        if obj:
                            self.move(obj, dx, dy)
        
        # Déplacer les opérateurs / Move operators
        for operator_id in self.selected_operators:
            operator = self.flow_model.get_operator(operator_id)
            if operator:
                operator.x += dx_model
                operator.y += dy_model
                # Déplacer les objets canvas / Move canvas objects
                if operator_id in self.operator_canvas_objects:
                    for obj in self.operator_canvas_objects[operator_id].values():
                        if obj:
                            self.move(obj, dx, dy)
        
        # Déplacer les pipettes / Move probes
        for probe_id in self.selected_probes:
            probe = self.flow_model.probes.get(probe_id)
            if probe:
                probe.x += dx_model
                probe.y += dy_model
                # Déplacer les objets canvas / Move canvas objects
                if probe_id in self.probe_canvas_objects:
                    for obj in self.probe_canvas_objects[probe_id].values():
                        if obj:
                            self.move(obj, dx, dy)
        
        # Déplacer les annotations / Move annotations
        for annotation_id in self.selected_annotations:
            annotation = self.flow_model.annotations.get(annotation_id)
            if annotation:
                annotation.x += dx_model
                annotation.y += dy_model
                # Déplacer les objets canvas / Move canvas objects
                if annotation_id in self.annotation_canvas_objects:
                    for obj in self.annotation_canvas_objects[annotation_id].values():
                        if obj:
                            self.move(obj, dx, dy)
        
        # Redessiner les connexions affectées par les nœuds déplacés
        # Redraw connections affected by moved nodes
        for node_id in self.selected_nodes:
            node = self.flow_model.get_node(node_id)
            if node:
                # Redessiner les connexions sortantes / Redraw outgoing connections
                for conn_id in node.output_connections:
                    conn = self.flow_model.get_connection(conn_id)
                    if conn:
                        self.redraw_connection(conn)
                # Redessiner les connexions entrantes / Redraw incoming connections
                for conn in self.flow_model.connections.values():
                    if conn.target_id == node_id:
                        self.redraw_connection(conn)
    
    def _toggle_element_in_multi_selection(self, x: float, y: float) -> bool:
        """
        Ajoute ou retire un élément de la sélection multiple (Ctrl+clic sur élément).
        Retourne True si un élément a été trouvé et traité.
        Add or remove element from multi-selection (Ctrl+click on element).
        Returns True if an element was found and processed.
        """
        # Chercher une pipette - utiliser les vraies coordonnées canvas
        # Look for a probe - use actual canvas coordinates
        for probe_id, probe in self.flow_model.probes.items():
            if probe_id in self.probe_canvas_objects:
                objs = self.probe_canvas_objects[probe_id]
                if 'circle' in objs and objs['circle']:
                    coords = self.coords(objs['circle'])
                    if coords and len(coords) >= 4:
                        px = (coords[0] + coords[2]) / 2
                        py = (coords[1] + coords[3]) / 2
                        radius = (coords[2] - coords[0]) / 2
                        if ((x - px) ** 2 + (y - py) ** 2) ** 0.5 <= radius:
                            if probe_id in self.selected_probes:
                                self.selected_probes.remove(probe_id)
                                self._unhighlight_element("probe", probe_id)
                            else:
                                self.selected_probes.add(probe_id)
                                self._highlight_element("probe", probe_id)
                            return True
        
        # Chercher un opérateur - utiliser les vraies coordonnées canvas
        for operator_id, operator in self.flow_model.operators.items():
            if operator_id in self.operator_canvas_objects:
                objs = self.operator_canvas_objects[operator_id]
                if 'circle' in objs and objs['circle']:
                    coords = self.coords(objs['circle'])
                    if coords and len(coords) >= 4:
                        ox = (coords[0] + coords[2]) / 2
                        oy = (coords[1] + coords[3]) / 2
                        radius = (coords[2] - coords[0]) / 2
                        if ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 <= radius:
                            if operator_id in self.selected_operators:
                                self.selected_operators.remove(operator_id)
                                self._unhighlight_element("operator", operator_id)
                            else:
                                self.selected_operators.add(operator_id)
                                self._highlight_element("operator", operator_id)
                            return True
        
        # Chercher un nœud - utiliser les vraies coordonnées canvas
        # Look for a node - use actual canvas coordinates
        for node_id, node in self.flow_model.nodes.items():
            if node_id in self.node_canvas_objects:
                objs = self.node_canvas_objects[node_id]
                if 'rect' in objs and objs['rect']:
                    coords = self.coords(objs['rect'])
                    if coords and len(coords) >= 4:
                        bx1, by1, bx2, by2 = coords[0], coords[1], coords[2], coords[3]
                        if bx1 <= x <= bx2 and by1 <= y <= by2:
                            if node_id in self.selected_nodes:
                                self.selected_nodes.remove(node_id)
                                self._unhighlight_element("node", node_id)
                            else:
                                self.selected_nodes.add(node_id)
                                self._highlight_element("node", node_id)
                            return True
        
        # Chercher une annotation - utiliser les vraies coordonnées canvas
        # Look for an annotation - use actual canvas coordinates
        for annotation_id, annotation in self.flow_model.annotations.items():
            if annotation_id in self.annotation_canvas_objects:
                objs = self.annotation_canvas_objects[annotation_id]
                if 'rect' in objs and objs['rect']:
                    coords = self.coords(objs['rect'])
                    if coords and len(coords) >= 4:
                        ax1, ay1, ax2, ay2 = coords[0], coords[1], coords[2], coords[3]
                        if ax1 <= x <= ax2 and ay1 <= y <= ay2:
                            if annotation_id in self.selected_annotations:
                                self.selected_annotations.remove(annotation_id)
                                self._unhighlight_element("annotation", annotation_id)
                            else:
                                self.selected_annotations.add(annotation_id)
                                self._highlight_element("annotation", annotation_id)
                            return True
        
        return False
    
    def _delete_multi_selection(self):
        """Supprime tous les éléments de la sélection multiple / Delete all elements of multi-selection"""
        # Supprimer les pipettes / Delete probes
        for probe_id in list(self.selected_probes):
            self.remove_probe(probe_id)
        
        # Supprimer les opérateurs / Delete operators
        for operator_id in list(self.selected_operators):
            self.flow_model.remove_operator(operator_id)
            self.remove_operator(operator_id)
        
        # Supprimer les annotations / Delete annotations
        for annotation_id in list(self.selected_annotations):
            self.remove_annotation(annotation_id)
        
        # Supprimer les nœuds (et leurs connexions)
        # Delete nodes (and their connections)
        for node_id in list(self.selected_nodes):
            node = self.flow_model.get_node(node_id)
            if node:
                # Supprimer les connexions entrantes et sortantes
                # Delete incoming and outgoing connections
                for conn_id in list(node.input_connections + node.output_connections):
                    if conn_id in self.flow_model.connections:
                        self.flow_model.remove_connection(conn_id)
                # Supprimer le nœud / Delete the node
                self.flow_model.remove_node(node_id)
        
        # Vider les sets / Clear sets
        self.selected_nodes.clear()
        self.selected_operators.clear()
        self.selected_probes.clear()
        self.selected_annotations.clear()
        
        # Redessiner / Redraw
        self.redraw_all()
    
    # ==================== IMPORT PLACEMENT MODE / MODE PLACEMENT IMPORT ====================
    
    def start_import_placement_mode(self, imported_nodes: set, imported_operators: set, 
                                     imported_probes: set, imported_annotations: set):
        """
        Démarre le mode de placement interactif pour les éléments importés.
        Les éléments suivent le curseur jusqu'au clic.
        Start interactive placement mode for imported elements.
        Elements follow the cursor until click.
        """
        # Activer le mode placement / Enable placement mode / Enable placement mode
        self.import_placement_mode = True
        
        # Sélectionner tous les éléments importés / Select all imported elements
        self.selected_nodes = imported_nodes.copy()
        self.selected_operators = imported_operators.copy()
        self.selected_probes = imported_probes.copy()
        self.selected_annotations = imported_annotations.copy()
        
        # Stocker le centre initial des éléments importés (pour référence)
        # Store initial center of imported elements (for reference)
        self.import_placement_offset = self._calculate_selection_center()
        # NE PAS initialiser import_last_mouse_pos ici - attendre le premier mouvement
        # DO NOT initialize import_last_mouse_pos here - wait for first movement
        self.import_last_mouse_pos = None
        
        # Surligner les éléments sélectionnés / Highlight selected elements
        for node_id in self.selected_nodes:
            self._highlight_element("node", node_id)
        for op_id in self.selected_operators:
            self._highlight_element("operator", op_id)
        for probe_id in self.selected_probes:
            self._highlight_element("probe", probe_id)
        for ann_id in self.selected_annotations:
            self._highlight_element("annotation", ann_id)
    
    def _calculate_selection_center(self) -> Tuple[float, float]:
        """Calcule le centre géométrique de tous les éléments sélectionnés / Calculate geometric center of all selected elements"""
        all_x = []
        all_y = []
        
        # Nœuds / Nodes
        for node_id in self.selected_nodes:
            node = self.flow_model.get_node(node_id)
            if node:
                all_x.append(node.x * self.zoom_level + self.NODE_WIDTH * self.zoom_level / 2)
                all_y.append(node.y * self.zoom_level + self.NODE_HEIGHT * self.zoom_level / 2)
        
        # Opérateurs / Operators
        for op_id in self.selected_operators:
            op = self.flow_model.get_operator(op_id)
            if op:
                all_x.append(op.x * self.zoom_level)
                all_y.append(op.y * self.zoom_level)
        
        # Pipettes / Probes
        for probe_id in self.selected_probes:
            probe = self.flow_model.probes.get(probe_id)
            if probe:
                all_x.append(probe.x * self.zoom_level)
                all_y.append(probe.y * self.zoom_level)
        
        # Annotations
        for ann_id in self.selected_annotations:
            ann = self.flow_model.annotations.get(ann_id)
            if ann:
                all_x.append(ann.x * self.zoom_level)
                all_y.append(ann.y * self.zoom_level)
        
        if all_x and all_y:
            return (sum(all_x) / len(all_x), sum(all_y) / len(all_y))
        return (0, 0)
    
    def _update_import_placement_position(self, mouse_x: float, mouse_y: float):
        """Met à jour la position des éléments importés pour suivre le curseur / Update position of imported elements to follow cursor"""
        # Premier mouvement : initialiser la position sans déplacer
        # First movement: initialize position without moving
        if self.import_last_mouse_pos is None:
            self.import_last_mouse_pos = (mouse_x, mouse_y)
            return
        
        # Calculer le delta depuis la dernière position du curseur
        # Calculate delta from last cursor position
        dx = mouse_x - self.import_last_mouse_pos[0]
        dy = mouse_y - self.import_last_mouse_pos[1]
        
        # Déplacer les éléments si le mouvement est significatif
        # Move elements if movement is significant
        if abs(dx) > 2 or abs(dy) > 2:
            self._move_multi_selection(dx, dy)
            # Mettre à jour la dernière position / Update last position
            self.import_last_mouse_pos = (mouse_x, mouse_y)
    
    def _finalize_import_placement(self):
        """Finalise le placement des éléments importés / Finalize placement of imported elements"""
        # Désactiver le mode placement / Disable placement mode
        self.import_placement_mode = False
        self.import_placement_offset = None
        self.import_last_mouse_pos = None
        
        # Désélectionner tous les éléments / Deselect all elements
        self._clear_multi_selection()
