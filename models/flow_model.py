"""Modèles pour les éléments du flux de production / Models for production flow elements"""
from typing import List, Dict, Optional
from enum import Enum
from models.time_converter import TimeUnit, TimeConverter
from models.item_type import ItemTypeConfig, ProcessingConfig

class NodeType(Enum):
    """Types de nœuds dans le flux / Node types in the flow"""
    SOURCE = "Flux entrant (Source)"
    SINK = "Sortie (Sink)"
    SPLITTER = "Diviseur (Splitter)"
    MERGER = "Concatenateur (Merger)"
    RECEPTIONIST = "Receptionist"
    WAITING_ROOM = "Waiting Room"
    NURSES_STATION = "Nurses' Station"
    EXAMINATION_ROOM = "Examination Room"
    DECISION = "Decision"
    APPOINTMENT = "Appointment"
    CUSTOM = "Custom"

class SourceMode(Enum):
    """Modes de génération pour les sources / Generation modes for sources"""
    CONSTANT = "Constant (intervalle fixe)"  # Fixed interval / Intervalle fixe
    NORMAL = "Loi Normale"  # Normal distribution
    SKEW_NORMAL = "Loi Normale Asymétrique"  # Skew-normal distribution

class SyncMode(Enum):
    """Mode de synchronisation pour les flux multiples / Sync mode for multiple flows"""
    WAIT_N_FROM_BRANCH = "Attendre N unités d'une branche"  # Wait for N units from a branch
    FIRST_AVAILABLE = "Premier disponible"  # First available

class FirstAvailablePriority(Enum):
    """Mode de priorité pour FIRST_AVAILABLE / Priority mode for FIRST_AVAILABLE"""
    ORDER = "Ordre des connexions"  # Connection order
    ROUND_ROBIN = "Alternance (round-robin)"  # Round-robin alternation
    RANDOM = "Aléatoire"  # Random

class SplitterMode(Enum):
    """Mode de distribution pour les diviseurs / Distribution mode for splitters"""
    ROUND_ROBIN = "Round-robin (alternance)"  # Round-robin alternation
    FIRST_AVAILABLE = "Premier disponible"  # First available
    RANDOM = "Aléatoire"  # Random

class FirstAvailableMode(Enum):
    """Sous-mode pour FIRST_AVAILABLE / Sub-mode for FIRST_AVAILABLE - how to determine availability"""
    BY_BUFFER = "Par buffer (connexion avec place)"  # By buffer (connection with space)
    BY_NODE_STATE = "Par état du nœud (nœud inactif)"  # By node state (inactive node)

class ProcessingTimeMode(Enum):
    """Mode de distribution pour les temps de traitement / Distribution mode for processing times"""
    CONSTANT = "Constant"  # Constant (fixed)
    NORMAL = "Loi Normale"  # Normal distribution
    SKEW_NORMAL = "Loi Normale Asymétrique"  # Skew-normal distribution

class FlowNode:
    """Représente un nœud (box) dans le flux de production / Represents a node (box) in the production flow"""
    
    def __init__(self, node_id: str, node_type: NodeType, name: str, x: float, y: float):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.x = x  # Position X sur le canvas / X position on canvas
        self.y = y  # Position Y sur le canvas / Y position on canvas
        
        # Temps de traitement (stocké en centisecondes - unité de base)
        # Processing time (stored in centiseconds - base unit)
        self.processing_time_cs = 0.0
        self.processing_time_mode = ProcessingTimeMode.CONSTANT  # Mode de distribution / Distribution mode
        self.processing_time_std_dev_cs = 0.0  # Écart-type en centisecondes / Standard deviation in centiseconds
        self.processing_time_skewness = 0.0  # Asymétrie (alpha) pour loi skew-normal / Skewness for skew-normal
        
        # Paramètres pour les nœuds sources / Parameters for source nodes
        self.is_source = node_type == NodeType.SOURCE
        self.source_mode = SourceMode.CONSTANT  # Mode de génération / Generation mode
        self.generation_interval_cs = 100.0  # Intervalle moyen en centisecondes / Mean interval in centiseconds
        self.generation_std_dev = 20.0  # Écart-type pour loi normale / Std dev for normal distribution
        self.generation_skewness = 0.0  # Asymétrie pour skew-normal / Skewness for skew-normal
        self.generation_lambda = 1.0  # Lambda pour Poisson/Exponentielle (obsolète) / Lambda (obsolete)
        self.max_items_to_generate = 100  # Max items à générer (0 = illimité) / Max items (0 = unlimited)
        self.items_generated = 0  # Compteur d'items générés / Generated items counter
        self.batch_size = 1  # Unités par lot / Units per batch
        
        # Configuration des types d'items multiples (pour sources)
        # Multiple item types configuration (for sources)
        self.item_type_config = ItemTypeConfig()  # Gestion de la génération multi-types / Multi-type generation
        
        # Configuration du traitement par type (pour nœuds de traitement)
        # Processing config by type (for processing nodes)
        self.processing_config = ProcessingConfig()  # Traitement différencié par type / Differentiated processing
        
        # Paramètres pour les nœuds sink (sortie) / Parameters for sink nodes (output)
        self.is_sink = node_type == NodeType.SINK
        self.items_received = 0  # Compteur d'items reçus / Received items counter
        
        # Paramètres pour les diviseurs (splitter) / Parameters for splitters
        self.is_splitter = node_type == NodeType.SPLITTER
        self.splitter_mode = SplitterMode.ROUND_ROBIN
        self.splitter_current_index = 0  # Pour round-robin / For round-robin
        self.first_available_mode = FirstAvailableMode.BY_BUFFER  # Sous-mode pour FIRST_AVAILABLE / Sub-mode
        
        # Paramètres pour les concatenateurs (merger) / Parameters for mergers
        self.is_merger = node_type == NodeType.MERGER
        
        # Multiplicateur de sortie : combien d'unités envoyer après traitement
        # Output multiplier: how many units to send after processing
        self.output_multiplier = 1  # 1 = même nombre / same number, 2 = double, 0.5 = moitié/half
        
        # Configuration du traitement par type d'item / Processing config by item type
        self.processing_config = ProcessingConfig()  # Temps et transformations par type / Times and transforms by type
        
        # État d'activité du nœud (utilisé pour l'affichage)
        # Node activity state (used for display)
        self.is_active = False  # True si le nœud traite / True if node is processing
        self._visual_changed = False  # Flag si l'état visuel a changé / Flag if visual state changed
        
        # Configuration pour les flux multiples / Configuration for multiple flows
        self.sync_mode = SyncMode.FIRST_AVAILABLE
        self.required_units: Dict[str, int] = {}  # branch_id -> units requis (legacy) / required units
        self.first_available_priority = FirstAvailablePriority.ORDER  # Mode de priorité / Priority mode
        self.round_robin_index = 0  # Index pour round-robin / Index for round-robin
        
        # Configuration de sortie pour le mode legacy (WAIT_N_FROM_BRANCH)
        # Output config for legacy mode (WAIT_N_FROM_BRANCH)
        self.legacy_output_quantity = 1  # Nombre d'items de sortie / Output items count
        self.legacy_output_type = ""  # Type de sortie (vide = garder) / Output type (empty = keep)
        
        # Système de combinaisons (pour WAIT_N_FROM_BRANCH)
        # Combination system (for WAIT_N_FROM_BRANCH)
        from models.combination import CombinationSet
        self.combination_set = CombinationSet()  # Ensemble de combinaisons / Combination set
        self.use_combinations = False  # True = mode combinaisons / combinations mode
        
        # Connexions / Connections
        self.input_connections: List[str] = []  # IDs des connexions entrantes / Input connection IDs
        self.output_connections: List[str] = []  # IDs des connexions sortantes / Output connection IDs
    
    def set_processing_time(self, time: float, unit: TimeUnit):
        """Définit le temps de traitement / Sets processing time in specified unit"""
        self.processing_time_cs = TimeConverter.to_centiseconds(time, unit)
    
    def get_processing_time(self, unit: TimeUnit) -> float:
        """Obtient le temps de traitement / Gets processing time in requested unit"""
        return TimeConverter.from_centiseconds(self.processing_time_cs, unit)
    
    def set_generation_interval(self, interval: float, unit: TimeUnit):
        """Définit l'intervalle de génération / Sets generation interval in specified unit"""
        self.generation_interval_cs = TimeConverter.to_centiseconds(interval, unit)
    
    def get_generation_interval(self, unit: TimeUnit) -> float:
        """Obtient l'intervalle de génération / Gets generation interval in requested unit"""
        return TimeConverter.from_centiseconds(self.generation_interval_cs, unit)
    
    def set_generation_std_dev(self, std_dev: float, unit: TimeUnit):
        """Définit l'écart-type de génération / Sets generation std dev in specified unit"""
        self.generation_std_dev = TimeConverter.to_centiseconds(std_dev, unit)
    
    def get_generation_std_dev(self, unit: TimeUnit) -> float:
        """Obtient l'écart-type de génération / Gets generation std dev in requested unit"""
        return TimeConverter.from_centiseconds(self.generation_std_dev, unit)

class Connection:
    """Représente une connexion entre deux nœuds / Represents a connection between two nodes"""
    
    def __init__(self, connection_id: str, source_id: str, target_id: str):
        self.connection_id = connection_id
        self.source_id = source_id
        self.target_id = target_id
        
        # Buffer sur la connexion / Buffer on the connection
        self.buffer_capacity = float('inf')
        self.current_buffer_count = 0
        self.initial_buffer_count = 0  # Unités présentes au démarrage / Units present at start
        self._buffer_changed = False  # Flag si le buffer a changé / Flag if buffer changed
        self._last_displayed_count = 0  # Dernier compte affiché / Last displayed count
        self.show_buffer = True  # Afficher le buffer visuellement / Show buffer visually
        self.highlight_until = 0  # Temps de clignotement / Highlight time (0 = no blink)
        
        # Items en transit (pour l'animation) / Items in transit (for animation)
        self.items_in_transit = []  # Liste de {item_id, progress: 0.0-1.0, timestamp}
        
        # Points de contrôle pour les courbes / Control points for curves
        self.control_points: List[tuple] = []
        
        # Propriétés visuelles pour le buffer / Visual properties for buffer
        self.buffer_visual_size = 20  # Taille de l'indicateur / Indicator size

class FlowModel:
    """Modèle complet du flux de production / Complete production flow model"""
    
    def __init__(self):
        self.nodes: Dict[str, FlowNode] = {}
        self.connections: Dict[str, Connection] = {}
        self.probes: Dict[str, 'MeasurementProbe'] = {}  # Pipettes de mesure / Measurement probes
        self.time_probes: Dict[str, 'TimeProbe'] = {}  # Loupes de temps / Time probes
        self.annotations: Dict[str, 'Annotation'] = {}  # Annotations visuelles / Visual annotations
        self.operators: Dict[str, 'Operator'] = {}  # Opérateurs / Operators
        self.current_time_unit = TimeUnit.SECONDS
        self._next_node_id = 0
        self._next_connection_id = 0
        self._next_probe_id = 0
        self._next_time_probe_id = 0
        self._next_annotation_id = 0
        self._next_operator_id = 0
    
    def generate_node_id(self) -> str:
        """Génère un ID unique pour un nœud / Generates a unique node ID"""
        node_id = f"node_{self._next_node_id}"
        self._next_node_id += 1
        return node_id
    
    def generate_connection_id(self) -> str:
        """Génère un ID unique pour une connexion / Generates a unique connection ID"""
        conn_id = f"conn_{self._next_connection_id}"
        self._next_connection_id += 1
        return conn_id
    
    def generate_probe_id(self) -> str:
        """Génère un ID unique pour une pipette / Generates a unique probe ID"""
        probe_id = f"probe_{self._next_probe_id}"
        self._next_probe_id += 1
        return probe_id
    
    def generate_time_probe_id(self) -> str:
        """Génère un ID unique pour une loupe de temps / Generates a unique time probe ID"""
        time_probe_id = f"time_probe_{self._next_time_probe_id}"
        self._next_time_probe_id += 1
        return time_probe_id
    
    def add_node(self, node: FlowNode):
        """Ajoute un nœud au modèle / Adds a node to the model"""
        self.nodes[node.node_id] = node
        
        # Initialiser les types par défaut pour les sources
        # Initialize default types for sources
        if node.is_source:
            self._ensure_default_item_types(node)
    
    def _ensure_default_item_types(self, node: FlowNode):
        """Assure qu'il existe au moins un type d'item par défaut / Ensures at least one default item type exists"""
        from models.item_type import ItemType, ItemGenerationMode
        
        if not node.item_type_config.item_types:
            # Créer un type par défaut / Create a default type
            default_type = ItemType('default', 'Item par défaut', '#4CAF50')
            node.item_type_config.item_types.append(default_type)
            node.item_type_config.generation_mode = ItemGenerationMode.SINGLE_TYPE
            node.item_type_config.single_type_id = 'default'
    
    def ensure_all_sources_have_default_types(self):
        """Assure que toutes les sources ont au moins un type / Ensures all sources have at least one type"""
        for node in self.nodes.values():
            if node.is_source:
                self._ensure_default_item_types(node)
    
    def remove_node(self, node_id: str):
        """Supprime un nœud et ses connexions / Removes a node and its connections"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if False:
                print(f"[MODEL] Suppression nœud / Removing node {node_id} ({node.name})")
            if False:
                print(f"[MODEL]   Input connections: {node.input_connections}")
            if False:
                print(f"[MODEL]   Output connections: {node.output_connections}")
            
            # Supprimer les connexions associées / Remove associated connections
            connections_to_remove = []
            for conn_id, conn in self.connections.items():
                if conn.source_id == node_id or conn.target_id == node_id:
                    connections_to_remove.append(conn_id)
            
            if False:
                print(f"[MODEL]   Connexions à supprimer / Connections to remove: {connections_to_remove}")
            
            # Utiliser remove_connection pour nettoyer proprement
            # Use remove_connection for proper cleanup
            for conn_id in connections_to_remove:
                self.remove_connection(conn_id)
            
            del self.nodes[node_id]
            if False:
                print(f"[MODEL]   ✓ Nœud / Node {node_id} supprimé / removed")
    
    def add_connection(self, connection: Connection):
        """Ajoute une connexion au modèle / Adds a connection to the model"""
        self.connections[connection.connection_id] = connection
        
        # Mettre à jour les références dans les nœuds (éviter les duplications)
        # Update references in nodes (avoid duplicates)
        if connection.source_id in self.nodes:
            if connection.connection_id not in self.nodes[connection.source_id].output_connections:
                self.nodes[connection.source_id].output_connections.append(connection.connection_id)
        if connection.target_id in self.nodes:
            if connection.connection_id not in self.nodes[connection.target_id].input_connections:
                self.nodes[connection.target_id].input_connections.append(connection.connection_id)
    
    def remove_connection(self, connection_id: str):
        """Supprime une connexion / Removes a connection"""
        if connection_id in self.connections:
            conn = self.connections[connection_id]
            if False:
                print(f"[MODEL] Suppression connexion / Removing connection {connection_id}: {conn.source_id} → {conn.target_id}")
            
            # Retirer des références dans les nœuds / Remove from node references
            if conn.source_id in self.nodes:
                if connection_id in self.nodes[conn.source_id].output_connections:
                    if False:
                        print(f"[MODEL]   Retrait de / Removing {connection_id} des outputs de / from outputs of {conn.source_id}")
                    self.nodes[conn.source_id].output_connections.remove(connection_id)
                else:
                    if False:
                        print(f"[MODEL]   ⚠️ {connection_id} n'était PAS dans / was NOT in outputs de / of {conn.source_id}")
            else:
                if False:
                    print(f"[MODEL]   ⚠️ Source {conn.source_id} n'existe plus / no longer exists")
                
            if conn.target_id in self.nodes:
                if connection_id in self.nodes[conn.target_id].input_connections:
                    if False:
                        print(f"[MODEL]   Retrait de / Removing {connection_id} des inputs de / from inputs of {conn.target_id}")
                    self.nodes[conn.target_id].input_connections.remove(connection_id)
                else:
                    if False:
                        print(f"[MODEL]   ⚠️ {connection_id} n'était PAS dans / was NOT in inputs de / of {conn.target_id}")
            else:
                if False:
                    print(f"[MODEL]   ⚠️ Target {conn.target_id} n'existe plus / no longer exists")
            
            # Supprimer les sondes associées à cette connexion
            # Remove probes associated with this connection
            probes_to_remove = [probe_id for probe_id, probe in self.probes.items() 
                               if probe.connection_id == connection_id]
            if probes_to_remove:
                if False:
                    print(f"[MODEL]   Suppression des sondes / Removing probes: {probes_to_remove}")
            for probe_id in probes_to_remove:
                del self.probes[probe_id]
            
            del self.connections[connection_id]
            if False:
                print(f"[MODEL]   ✓ Connexion / Connection {connection_id} supprimée / removed")
    
    def set_time_unit(self, new_unit: TimeUnit):
        """Change l'unité de temps globale / Changes global time unit (values auto-converted)"""
        self.current_time_unit = new_unit
    
    def add_probe(self, probe):
        """Ajoute une pipette de mesure / Adds a measurement probe"""
        self.probes[probe.probe_id] = probe
    
    def remove_probe(self, probe_id: str):
        """Supprime une pipette de mesure / Removes a measurement probe"""
        if probe_id in self.probes:
            del self.probes[probe_id]
    
    def get_probe(self, probe_id: str):
        """Récupère une pipette par son ID / Gets a probe by its ID"""
        return self.probes.get(probe_id)
    
    def add_time_probe(self, time_probe):
        """Ajoute une loupe de temps / Adds a time probe"""
        self.time_probes[time_probe.probe_id] = time_probe
    
    def remove_time_probe(self, time_probe_id: str):
        """Supprime une loupe de temps / Removes a time probe"""
        if time_probe_id in self.time_probes:
            del self.time_probes[time_probe_id]
    
    def get_time_probe(self, time_probe_id: str):
        """Récupère une loupe de temps par son ID / Gets a time probe by its ID"""
        return self.time_probes.get(time_probe_id)
    
    def generate_annotation_id(self) -> str:
        """Génère un ID unique pour une annotation / Generates a unique annotation ID"""
        annotation_id = f"annotation_{self._next_annotation_id}"
        self._next_annotation_id += 1
        return annotation_id
    
    def add_annotation(self, annotation):
        """Ajoute une annotation / Adds an annotation"""
        self.annotations[annotation.annotation_id] = annotation
    
    def generate_operator_id(self) -> str:
        """Génère un ID unique pour un opérateur / Generates a unique operator ID"""
        operator_id = f"op_{self._next_operator_id}"
        self._next_operator_id += 1
        return operator_id
    
    def add_operator(self, operator):
        """Ajoute un opérateur / Adds an operator"""
        self.operators[operator.operator_id] = operator
    
    def remove_operator(self, operator_id: str):
        """Supprime un opérateur / Removes an operator"""
        if operator_id in self.operators:
            del self.operators[operator_id]
    
    def get_operator(self, operator_id: str):
        """Récupère un opérateur par son ID / Gets an operator by its ID"""
        return self.operators.get(operator_id)
    
    def remove_annotation(self, annotation_id: str):
        """Supprime une annotation / Removes an annotation"""
        if annotation_id in self.annotations:
            del self.annotations[annotation_id]
    
    def get_annotation(self, annotation_id: str):
        """Récupère une annotation par son ID / Gets an annotation by its ID"""
        return self.annotations.get(annotation_id)
    
    def get_node(self, node_id: str) -> Optional[FlowNode]:
        """Récupère un nœud par son ID / Gets a node by its ID"""
        return self.nodes.get(node_id)
    
    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Récupère une connexion par son ID / Gets a connection by its ID"""
        return self.connections.get(connection_id)
    
    def generate_annotation_id(self) -> str:
        """Génère un ID unique pour une annotation / Generates a unique annotation ID"""
        annotation_id = f"annotation_{self._next_annotation_id}"
        self._next_annotation_id += 1
        return annotation_id
    
    def add_annotation(self, annotation):
        """Ajoute une annotation visuelle / Adds a visual annotation"""
        self.annotations[annotation.annotation_id] = annotation
    
    def remove_annotation(self, annotation_id: str):
        """Supprime une annotation / Removes an annotation"""
        if annotation_id in self.annotations:
            del self.annotations[annotation_id]
    
    def get_annotation(self, annotation_id: str):
        """Récupère une annotation par son ID / Gets an annotation by its ID"""
        return self.annotations.get(annotation_id)
