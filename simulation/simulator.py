"""Simulateur SimPy pour le flux de production / SimPy Simulator for production flow"""
import simpy
import random
import numpy as np
from scipy import stats
from typing import Dict, List, Optional
from models.flow_model import FlowModel, FlowNode, Connection, SyncMode, NodeType, FirstAvailablePriority
from models.time_converter import TimeConverter, TimeUnit
from models.item_type_stats import ItemTypeStats
from gui.translations import tr

class FlowSimulator:
    """Simulateur basé sur SimPy pour exécuter le flux de production
       SimPy-based simulator to run the production flow"""
    
    def __init__(self, flow_model: FlowModel, update_callback=None, speed_factor=1.0, time_unit='CENTISECONDS', fast_mode=False, simulation_duration=None, app_config=None):
        self.flow_model = flow_model
        self.update_callback = update_callback  # Callback pour mettre à jour l'interface / Callback to update UI
        self.speed_factor = speed_factor  # Facteur de vitesse / Speed factor (1.0 = real-time)
        self.time_unit = time_unit  # Unité de temps / Time unit (HOURS, SECONDS, CENTISECONDS)
        self.fast_mode = fast_mode  # Mode turbo pour analyses / Turbo mode for analyses (no real-time sync)
        self.simulation_duration = simulation_duration if simulation_duration is not None else float('inf')  # Durée / Duration
        self.env: Optional[simpy.Environment] = None
        self.resources: Dict[str, simpy.Resource] = {}
        self.stores: Dict[str, simpy.Store] = {}
        self.buffer_type_counts: Dict[str, Dict[str, int]] = {}  # Track type counts per connection / Suivi des types par connexion
        self.is_running = False
        self.is_paused = False
        
        # Configuration de l'application (paramètres de performance)
        # Application configuration (performance settings)
        self.app_config = app_config
        if self.app_config is None:
            # Valeurs par défaut si aucune config / Default values if no config
            class DefaultConfig:
                DEBUG_MODE = False
                UI_UPDATE_INTERVAL = 0.2
                OPERATOR_ANIMATION_STEPS = 7
                ENABLE_ANIMATIONS = True
                OPERATOR_PROBE_MAX_MEASUREMENTS = 1000
            self.app_config = DefaultConfig()
        
        # Statistiques / Statistics
        self.stats = {
            'items_processed': {},  # node_id -> count
            'waiting_times': {},    # node_id -> [times]
            'throughput': 0
        }
        
        # Suivi des temps inter-événements pour les sondes de temps
        # Inter-event time tracking for time probes
        self.last_event_times = {}  # node_id -> dernier temps / last event time
        
        # Gestion des opérateurs / Operator management
        self.operator_resources: Dict[str, simpy.Resource] = {}  # operator_id -> resource (capacity 1)
        self.operator_positions: Dict[str, str] = {}  # operator_id -> current_machine_id
        self.operator_busy_time: Dict[str, float] = {}  # operator_id -> temps total occupé / total busy time
        self.operator_busy_start: Dict[str, float] = {}  # operator_id -> début période / busy period start
        
        # Statistiques par type d'item / Item type statistics
        self.item_type_stats = ItemTypeStats()
    
    def start(self):
        """Démarre la simulation / Starts the simulation"""
        if not self.env:
            self._initialize_simulation()
        
        self.is_running = True
        self.is_paused = False
        
        # Lancer les processus SimPy dans un thread séparé
        # Launch SimPy processes in a separate thread
        import threading
        self.sim_thread = threading.Thread(target=self._run_simulation, daemon=True)
        self.sim_thread.start()
    
    def pause(self):
        """Met en pause la simulation / Pauses the simulation"""
        self.is_paused = True
    
    def set_speed(self, speed_factor: float):
        """Change la vitesse de simulation / Changes simulation speed"""
        self.speed_factor = max(0.1, min(5.0, speed_factor))  # Limiter entre 0.1x et 5x / Limit between 0.1x and 5x
    
    def _update_buffer_count(self, connection, new_count):
        """Met à jour le compteur de buffer et notifie le callback
           Updates buffer count and notifies the analysis callback"""
        if connection.current_buffer_count != new_count:
            connection._buffer_changed = True
        connection.current_buffer_count = new_count
        # Appeler le callback d'analyse si disponible / Call analysis callback if available
        if hasattr(self, '_capture_buffer_state') and self._capture_buffer_state:
            try:
                self._capture_buffer_state(connection.connection_id, self.env.now, new_count)
            except Exception as e:
                pass  # Ignorer les erreurs de callback / Ignore callback errors
    
    def stop(self):
        """Arrête la simulation / Stops the simulation"""
        # Marquer l'arrêt en premier pour sortir des boucles rapidement
        # Mark stop first to exit loops quickly
        self.is_running = False
        self.is_paused = False
        
        # Attendre brièvement que le thread se termine (max 1 seconde)
        # Wait briefly for thread to finish (max 1 second)
        if hasattr(self, 'sim_thread') and self.sim_thread and self.sim_thread.is_alive():
            self.sim_thread.join(timeout=1.0)
        
        # Réinitialiser l'état actif de tous les nœuds
        # Reset active state of all nodes
        for node in self.flow_model.nodes.values():
            if node.is_active:
                node._visual_changed = True
            node.is_active = False
        
        # Réinitialiser les buffers aux conditions initiales
        # Reset buffers to initial conditions
        for connection in self.flow_model.connections.values():
            connection.current_buffer_count = getattr(connection, 'initial_buffer_count', 0)
            # Vider les items en transit / Clear items in transit
            connection.items_in_transit.clear()
        
        if self.env:
            # Réinitialiser l'environnement pour la prochaine simulation
            # Reset environment for next simulation
            self.env = None
            self.resources.clear()
            self.stores.clear()
            self.buffer_type_counts.clear()
    
    def _initialize_simulation(self):
        """Initialise l'environnement SimPy / Initializes the SimPy environment"""
        self.env = simpy.Environment()
        
        # Réinitialiser le suivi des temps inter-événements
        # Reset inter-event time tracking
        self.last_event_times = {}
        
        # Réinitialiser les configurations de génération d'items pour les sources
        # Reset item generation configs for sources
        for node_id, node in self.flow_model.nodes.items():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                node.item_type_config.reset()
        
        # Initialiser les opérateurs / Initialize operators
        if self.app_config.DEBUG_MODE:
            print("\n" + "*"*80)
            if self.app_config.DEBUG_MODE:
                print("[SIM_INIT] Initialisation des opérateurs dans le simulateur / Initializing operators")
            if self.app_config.DEBUG_MODE:
                print("*"*80)
        
        self.operator_resources.clear()
        self.operator_positions.clear()
        self.operator_busy_time.clear()
        self.operator_busy_start.clear()
        self.operator_travel_time = {}  # Temps total de déplacement / Total travel time
        
        # Ne initialiser les opérateurs que s'il y en a dans le modèle
        # Only initialize operators if there are some in the model
        if not self.flow_model.operators:
            if self.app_config.DEBUG_MODE:
                print("[SIM_INIT] Aucun opérateur détecté / No operator detected, skip init")
        else:
            if self.app_config.DEBUG_MODE:
                print(f"[SIM_INIT] {len(self.flow_model.operators)} opérateur(s) détecté(s) / operator(s) detected: {list(self.flow_model.operators.keys())}")
            for operator_id, operator in self.flow_model.operators.items():
                if self.app_config.DEBUG_MODE:
                    print(f"\n[SIM_INIT] Initialisation de / Initializing {operator_id}:")
                    if self.app_config.DEBUG_MODE:
                        print(f"  - AVANT/BEFORE: x={getattr(operator, 'x', 'None')}, y={getattr(operator, 'y', 'None')}")
                    if self.app_config.DEBUG_MODE:
                        print(f"  - AVANT/BEFORE: current_machine_id={getattr(operator, 'current_machine_id', 'None')}")
                
                # Chaque opérateur est une ressource de capacité 1 (ne peut être qu'à un endroit)
                # Each operator is a capacity-1 resource (can only be at one place)
                self.operator_resources[operator_id] = simpy.Resource(self.env, capacity=1)
                self.operator_busy_time[operator_id] = 0.0
                self.operator_busy_start[operator_id] = None
                self.operator_travel_time[operator_id] = 0.0
                # Initialiser la position: première machine assignée ou None
                # Initialize position: first assigned machine or None
                if operator.assigned_machines:
                    first_machine_id = operator.assigned_machines[0]
                    self.operator_positions[operator_id] = first_machine_id
                    operator.current_machine_id = first_machine_id
                    # Positionner visuellement l'opérateur / Visually position operator
                    first_node = self.flow_model.get_node(first_machine_id)
                    if first_node:
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Nœud trouvé / Node found: {first_machine_id} at x={first_node.x}, y={first_node.y}")
                            if self.app_config.DEBUG_MODE:
                                print(f"  - MODIFICATION: operator.x={first_node.x}, operator.y={first_node.y}")
                        operator.x = first_node.x
                        operator.y = first_node.y
                        # Marquer pour mise à jour visuelle / Mark for visual update
                        operator._needs_initial_draw = True
                        if self.app_config.DEBUG_MODE:
                            print(f"  - APRÈS/AFTER: x={operator.x}, y={operator.y}")
                else:
                    self.operator_positions[operator_id] = None
                    operator.current_machine_id = None
                operator.is_available = True
                if self.app_config.DEBUG_MODE:
                    print(f"  - Opérateur initialisé / Operator initialized: current_machine_id={operator.current_machine_id}")
        
        if self.app_config.DEBUG_MODE:
            print("\n" + "*"*80)
            if self.app_config.DEBUG_MODE:
                print("[SIM_INIT] Fin de l'initialisation des opérateurs / End of operator init")
            if self.app_config.DEBUG_MODE:
                print("*"*80 + "\n")
        
        # Créer des ressources pour chaque nœud / Create resources for each node
        for node_id, node in self.flow_model.nodes.items():
            # Ressource pour le traitement (capacité 1 par défaut)
            # Resource for processing (capacity 1 by default)
            self.resources[node_id] = simpy.Resource(self.env, capacity=1)
            
            # Store pour le buffer du nœud (capacité illimitée par défaut)
            # Store for node buffer (unlimited capacity by default)
            self.stores[node_id] = simpy.Store(self.env)
            
            # Initialiser les statistiques / Initialize statistics
            self.stats['items_processed'][node_id] = 0
            self.stats['waiting_times'][node_id] = []
        
        # Créer des stores pour les connexions avec buffer
        # Create stores for connections with buffers
        for conn_id, connection in self.flow_model.connections.items():
            if connection.buffer_capacity != float('inf'):
                self.stores[conn_id] = simpy.Store(self.env, capacity=int(connection.buffer_capacity))
            else:
                self.stores[conn_id] = simpy.Store(self.env)
            
            # Initialiser le buffer avec les conditions initiales
            # Initialize buffer with initial conditions
            initial_count = getattr(connection, 'initial_buffer_count', 0)
            if initial_count > 0:
                if self.app_config.DEBUG_MODE and not self.fast_mode:
                    print(f"[DEBUG] Init: {initial_count} item(s) in connection {conn_id}")
                # Ajouter des items factices au buffer pour représenter les unités initiales
                # Add dummy items to buffer to represent initial units
                # IMPORTANT: Items must be dictionaries, not strings
                for i in range(initial_count):
                    initial_item = {
                        'id': f"initial_item_{conn_id}_{i}",
                        'created_at': 0,  # Temps 0 pour les items initiaux / Time 0 for initial items
                        'node_id': 'initial',
                        'parent_id': None
                    }
                    self.stores[conn_id].items.append(initial_item)
                # Mettre à jour le compteur visuel / Update visual counter
                connection.current_buffer_count = initial_count
                if self.app_config.DEBUG_MODE and not self.fast_mode:
                    print(f"[DEBUG] Store {conn_id} now contains {len(self.stores[conn_id].items)} item(s)")
    
    def _run_simulation(self):
        """Exécute la simulation / Runs the simulation"""
        # Trouver les nœuds sources / Find source nodes
        source_nodes = [
            node_id for node_id, node in self.flow_model.nodes.items()
            if node.is_source
        ]
        
        # Générer des items aux nœuds sources / Generate items at source nodes
        for node_id in source_nodes:
            self.env.process(self._generate_items(node_id))
        
        # Traiter les items dans chaque nœud / Process items in each node
        for node_id in self.flow_model.nodes.keys():
            node = self.flow_model.nodes[node_id]
            if not node.is_source:  # Les sources ne traitent pas / Sources don't process, they generate
                if node.is_sink:
                    self.env.process(self._process_sink(node_id))
                elif node.is_splitter:
                    self.env.process(self._process_splitter(node_id))
                elif node.is_merger:
                    self.env.process(self._process_merger(node_id))
                else:
                    self.env.process(self._process_node(node_id))
        
        # Processus de mise à jour de l'interface (toujours lancé pour les pipettes)
        # UI update process (always launched for probes)
        self.env.process(self._update_ui())
        
        # Exécuter en temps réel avec des pauses OU en mode turbo
        # Run in real-time with pauses OR in turbo mode
        import time
        try:
            # Utiliser la durée configurable (ou infini si non spécifiée)
            # Use configurable duration (or infinite if not specified)
            simulation_time_limit = self.simulation_duration
            
            if self.fast_mode:
                # MODE TURBO: Exécution directe sans synchronisation temps réel
                # TURBO MODE: Direct execution without real-time sync
                # Utilisé pour les analyses rapides / Used for fast analyses
                while self.is_running and self.env and self.env.now < simulation_time_limit:
                    self.env.run(until=simulation_time_limit)
                    break
            else:
                # MODE NORMAL: Synchronisation avec le temps réel pour animation
                # NORMAL MODE: Sync with real-time for animation
                last_real_time = time.time()
                last_sim_time = 0
                
                # Facteur de conversion: temps simulation (centisecondes) -> temps réel (secondes)
                # Conversion factor: simulation time (centiseconds) -> real time (seconds)
                if self.time_unit == 'HOURS':
                    # 1 centiseconde SimPy = 1 heure réelle = 3600 secondes
                    # 1 SimPy centisecond = 1 real hour = 3600 seconds
                    time_conversion = 3600.0
                elif self.time_unit == 'SECONDS':
                    # 1 centiseconde SimPy = 1 seconde réelle
                    # 1 SimPy centisecond = 1 real second
                    time_conversion = 1.0
                else:  # CENTISECONDS
                    # 1 centiseconde SimPy = 0.01 seconde réelle
                    # 1 SimPy centisecond = 0.01 real second
                    time_conversion = 0.01
                
                while self.is_running and self.env and self.env.now < simulation_time_limit:
                    # Vérifier si en pause / Check if paused
                    if self.is_paused:
                        time.sleep(0.05)  # Sleep réduit pour réactivité / Reduced sleep for responsiveness
                        continue
                    
                    # Sortie rapide si arrêt demandé / Quick exit if stop requested
                    if not self.is_running:
                        break
                    
                    # Avancer la simulation d'un petit pas / Advance simulation by small step
                    next_time = min(self.env.now + 0.1, simulation_time_limit)
                    self.env.run(until=next_time)
                    
                    # Double vérification d'arrêt après chaque step
                    # Double-check stop after each step
                    if not self.is_running or not self.env:
                        break
                    
                    # Calculer le temps réel écoulé pour ce pas
                    # Calculate elapsed real time for this step
                    sim_time_elapsed = self.env.now - last_sim_time
                    # Convertir le temps de simulation en temps réel selon l'unité choisie
                    # Convert simulation time to real time based on chosen unit
                    real_time_to_wait = (sim_time_elapsed * time_conversion) / self.speed_factor
                    
                    # Attendre le temps réel correspondant avec sleeps courts pour réactivité
                    # Wait corresponding real time with short sleeps for responsiveness
                    if real_time_to_wait > 0:
                        # Diviser en petits sleeps de max 50ms pour permettre arrêt rapide
                        # Split into small sleeps of max 50ms to allow quick stop
                        remaining = real_time_to_wait
                        while remaining > 0 and self.is_running:
                            sleep_time = min(remaining, 0.05)
                            time.sleep(sleep_time)
                            remaining -= sleep_time
                    
                    last_sim_time = self.env.now
                
        except AttributeError as e:
            # Ignorer les erreurs d'accès à env.now si l'environnement a été arrêté
            # Ignore errors accessing env.now if environment was stopped
            if "'NoneType' object has no attribute" not in str(e):
                if self.app_config.DEBUG_MODE:
                    print(f"Simulation error: {e}")
        except Exception as e:
            if self.app_config.DEBUG_MODE:
                print(f"Erreur de simulation: {e}")
        finally:
            self.is_running = False
    
    def _generate_items(self, node_id: str):
        """Génère des items au nœud source selon la loi configurée
           Generates items at source node according to configured distribution"""
        node = self.flow_model.get_node(node_id)
        if not node or not node.is_source:
            return
        
        if self.app_config.DEBUG_MODE:
            print(f"\n{'='*80}")
            print(f"[DEBUG_GENERATION] {node.name}: Starting generation at t={self.env.now:.2f}s")
            print(f"[DEBUG_GENERATION] {node.name}: max_items={node.max_items_to_generate}, batch_size={node.batch_size}")
            print(f"{'='*80}\n")
        
        item_count = 0
        max_items = node.max_items_to_generate
        batch_size = node.batch_size
        
        # Attendre l'intervalle de génération AVANT de générer le tout premier item
        # Wait for generation interval BEFORE generating the very first item
        # (sinon le premier item apparaît à t=0 / otherwise first item appears at t=0)
        try:
            wait_time = self._get_generation_interval(node)
            if self.app_config.DEBUG_MODE:
                print(f"[DEBUG_GENERATION] {node.name}: Wait {wait_time:.2f}s before first item")
            yield self.env.timeout(wait_time)
            if self.app_config.DEBUG_MODE:
                print(f"[DEBUG_GENERATION] {node.name}: Wait ended at t={self.env.now:.2f}s, starting generation")
        except simpy.Interrupt:
            return
        
        while self.is_running and self.env and (max_items == 0 or item_count < max_items):
            if not self.is_paused:
                # Calculer combien d'items générer dans ce lot
                # Calculate how many items to generate in this batch
                items_to_generate = batch_size
                if max_items > 0:
                    items_remaining = max_items - item_count
                    items_to_generate = min(batch_size, items_remaining)
                
                # Créer un lot d'items / Create a batch of items
                # TOUS les items du batch sont créés SIMULTANÉMENT (même instant t)
                # ALL items in batch are created SIMULTANEOUSLY (same time t)
                for item_index in range(items_to_generate):
                    if not self.env:
                        return
                    
                    # Marquer le nœud comme actif / Mark node as active
                    if not node.is_active:
                        node._visual_changed = True
                    node.is_active = True
                    
                    # Capturer le changement d'état pour l'analyse
                    # Capture state change for analysis
                    if hasattr(self, '_capture_node_active_change'):
                        self._capture_node_active_change(node_id, self.env.now, True)
                    # Sources: pas de problème d'état ON multiple / No multiple ON state issue
                    if hasattr(self, '_capture_machine_state'):
                        self._capture_machine_state(node_id, self.env.now, "ON")
                    
                    # Déterminer le type d'item à générer / Determine item type to generate
                    item_type_id = node.item_type_config.get_next_item_type()
                    
                    if item_type_id is None:
                        # Plus d'items à générer (séquence finie ou hypergéométrique épuisé)
                        # No more items to generate (sequence finished or hypergeometric exhausted)
                        if node.is_active:
                            node._visual_changed = True
                        node.is_active = False
                        if hasattr(self, '_capture_node_active_change'):
                            self._capture_node_active_change(node_id, self.env.now, False)
                        if hasattr(self, '_capture_machine_state'):
                            self._capture_machine_state(node_id, self.env.now, "OFF")
                        return
                    
                    # Récupérer le nom du type / Get the type name
                    item_type_name = self._get_item_type_name(node_id, item_type_id)
                    
                    item = {
                        'id': f"{node_id}_item_{item_count}",
                        'created_at': self.env.now,
                        'node_id': node_id,
                        'item_type': item_type_id,  # Type de l'item / Item type (ex: "carrot", "onion")
                        'item_type_name': item_type_name  # Nom du type pour l'affichage / Type name for display
                    }
                    
                    if self.app_config.DEBUG_MODE:
                        print(f"\n[DEBUG_GENERATION] {node.name}: *** GÉNÉRATION item {item['id']} à t={self.env.now:.2f}s ***")
                    
                    # DEBUG: Logger la génération (désactivé en mode turbo)
                    if self.app_config.DEBUG_MODE and not self.fast_mode:
                        print(f"[DEBUG] Source {node.name} génère item {item['id']}")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - Connexions de sortie: {len(node.output_connections)}")
                        if self.app_config.DEBUG_MODE:
                            print(f"  - IDs connexions: {node.output_connections}")
                    
                    # Capturer l'événement d'arrivée pour l'analyse
                    if hasattr(self, '_capture_arrival'):
                        self._capture_arrival(node_id, self.env.now)
                    
                    # Enregistrer la génération par type
                    if item.get('item_type'):
                        self.item_type_stats.record_generation(self.env.now, item['item_type'])
                        # Aussi enregistrer dans le panneau si disponible
                        if hasattr(self, '_record_item_generation'):
                            self._record_item_generation(self.env.now, item['item_type'])
                    
                    # Enregistrer le temps inter-événement pour les sondes de temps (sources = inter-arrivées)
                    current_time = self.env.now
                    if node_id in self.last_event_times:
                        inter_event_time = current_time - self.last_event_times[node_id]
                        self._record_time_probe_measurement(node_id, inter_event_time, 'INTER_EVENTS')
                    self.last_event_times[node_id] = current_time
                    
                    # Envoyer directement aux nœuds suivants
                    try:
                        if self.app_config.DEBUG_MODE:
                            print(f"\n[DEBUG_GENERATION] {node.name}: Envoi item {item['id']} sur {len(node.output_connections)} connexion(s) sortante(s) à t={self.env.now:.2f}s")
                        for conn_id in node.output_connections:
                            connection = self.flow_model.get_connection(conn_id)
                            if connection and self.env:
                                connection_store = self.stores.get(conn_id)
                                if connection_store:
                                    if self.app_config.DEBUG_MODE:
                                        print(f"[DEBUG_GENERATION] {node.name}: → Send on connection {conn_id} (target: {connection.target_id})")
                                    if not self.fast_mode and self.app_config.DEBUG_MODE:
                                        print(f"  → Send on conn {conn_id} (source: {connection.source_id}, target: {connection.target_id})")
                                    # Transférer l'item (peut bloquer si buffer plein)
                                    # Transfer item (may block if buffer full, but animation in parallel)
                                    yield self.env.process(self._transit_item(item, connection, connection_store))
                                    if self.app_config.DEBUG_MODE:
                                        print(f"[DEBUG_GENERATION] {node.name}: ✓ Item transferred to buffer {conn_id} at t={self.env.now:.2f}s")
                        
                        item_count += 1
                        node.items_generated = item_count
                        
                    except simpy.Interrupt:
                        if node.is_active:
                            node._visual_changed = True
                        node.is_active = False
                        return
                
                # Désactiver le nœud après la génération du lot
                # Deactivate node after batch generation
                if node.is_active:
                    node._visual_changed = True
                node.is_active = False
                
                # Capturer le changement d'état pour l'analyse
                # Capture state change for analysis
                if hasattr(self, '_capture_node_active_change'):
                    self._capture_node_active_change(node_id, self.env.now, False)
                if hasattr(self, '_capture_machine_state'):
                    self._capture_machine_state(node_id, self.env.now, "OFF")
                
                # Attendre avant le prochain lot (seulement si on a généré des items)
                # Wait before next batch (only if we generated items)
                if items_to_generate > 0:
                    try:
                        if not self.env:
                            break
                        wait_time = self._get_generation_interval(node)
                        yield self.env.timeout(wait_time)
                    except simpy.Interrupt:
                        break
            else:
                if self.env:
                    yield self.env.timeout(0.1)
                else:
                    break
    
    def _animate_transit(self, item, connection):
        """Anime visuellement le transit d'un item (processus non-bloquant)
           Visually animates item transit (non-blocking process)
        
        Args:
            item: L'item à animer (dict avec id, item_type, etc.) / Item to animate
            connection: La connexion sur laquelle animer / Connection to animate on
        """
        transit_time = 0.3  # Temps d'animation visuelle / Visual animation time (doesn't affect logic)
        steps = 5  # Réduit de 10 à 5 pour performances / Reduced from 10 to 5 for better perf
        step_time = transit_time / steps
        item_id = item['id']
        
        # Ajouter à la liste des items en transit avec le type d'item
        # Add to in-transit items list with item type
        connection.items_in_transit.append({
            'item_id': item_id,
            'item_type': item.get('item_type', None),
            'item_type_name': item.get('item_type_name', 'default'),  # Copier aussi le nom / Also copy name
            'progress': 0.0,
            'timestamp': self.env.now if self.env else 0
        })
        
        # Animer le déplacement / Animate movement
        for step in range(steps + 1):
            if not self.is_running or not self.env:
                break
            
            progress = step / steps
            
            # Mettre à jour la position dans la liste / Update position in list
            for transit_item in connection.items_in_transit:
                if transit_item['item_id'] == item_id:
                    transit_item['progress'] = progress
                    break
            
            if self.env:
                yield self.env.timeout(step_time)
            else:
                break
        
        # Retirer de la liste des items en transit (animation terminée)
        # Remove from in-transit list (animation finished)
        connection.items_in_transit = [
            t for t in connection.items_in_transit if t['item_id'] != item_id
        ]
    
    def _transit_item(self, item, connection, target_store, quantity=1):
        """Transfère des items dans le buffer et lance l'animation en parallèle
           Transfers items to buffer and launches animation in parallel
        
        Args:
            item: L'item à transiter / Item to transit (dict with id, created_at, etc.)
            connection: La connexion sur laquelle transiter / Connection to transit on
            target_store: Le store de destination / Destination store
            quantity: Nombre d'unités à ajouter au buffer / Units to add (default 1)
        """
        item_id = item['id']
        
        # ÉTAPE 1: Réserver l'espace dans le buffer (PEUT BLOQUER si capacité atteinte)
        # STEP 1: Reserve space in buffer (MAY BLOCK if capacity reached)
        try:
            for i in range(quantity):
                # IMPORTANT: Vérifier NOTRE compteur manuel avant le put()
                # IMPORTANT: Check OUR manual counter before put()
                # Car SimPy ne gère pas correctement les transferts directs
                # Because SimPy doesn't handle direct transfers correctly
                if connection.buffer_capacity != float('inf'):
                    # Attendre qu'il y ait de la place selon NOTRE compteur
                    # Wait for space according to OUR counter
                    while connection.current_buffer_count >= connection.buffer_capacity:
                        if self.app_config.DEBUG_MODE and not self.fast_mode:
                            print(f"[DEBUG_BUFFER] Connection {connection.connection_id}: BLOCKED - buffer full ({connection.current_buffer_count}/{connection.buffer_capacity})")
                        # Attendre un peu et réessayer / Wait a bit and retry
                        yield self.env.timeout(0.01)
                
                # Maintenant on peut mettre dans le store SimPy
                # Now we can put in SimPy store
                # (qui pourrait aussi bloquer, mais notre compteur est prioritaire)
                # (which could also block, but our counter has priority)
                item_copy = item.copy()
                
                # Incrémenter AVANT le put() pour réserver l'espace
                # Increment BEFORE put() to reserve space
                buffer_before = connection.current_buffer_count
                new_buffer = buffer_before + 1
                self._update_buffer_count(connection, new_buffer)
                
                # Incrémenter le compteur de types / Increment type counter
                item_type_name = item.get('item_type_name', 'default')
                if connection.connection_id not in self.buffer_type_counts:
                    self.buffer_type_counts[connection.connection_id] = {}
                type_counts = self.buffer_type_counts[connection.connection_id]
                old_count = type_counts.get(item_type_name, 0)
                type_counts[item_type_name] = old_count + 1
                
                # IMPORTANT: Enregistrer dans les pipettes AVANT le put()
                # IMPORTANT: Record in probes BEFORE put()
                # pour que la capture soit faite avant que la machine ne puisse prendre l'item
                # so capture happens before machine can take the item
                self._record_probe_measurement(connection.connection_id, 1, new_buffer, item_type_name)
                
                yield target_store.put(item_copy)
            
            # Vérification de cohérence entre buffer_count et type_counts
            # Consistency check between buffer_count and type_counts
            if self.app_config.DEBUG_MODE and not self.fast_mode:
                type_counts = self.buffer_type_counts.get(connection.connection_id, {})
                sum_types = sum(type_counts.values())
                if sum_types != connection.current_buffer_count:
                    print(f"[CONSISTENCY_WARNING] t={self.env.now:.4f} | {connection.connection_id} | Buffer={connection.current_buffer_count} but sum(types)={sum_types} | types={type_counts}")
        except Exception as e:
            if self.app_config.DEBUG_MODE:
                print(f"Error during buffering: {e}")
            return
        
        # ÉTAPE 2: Lancer l'animation visuelle EN PARALLÈLE (non-bloquant)
        if self.env:
            self.env.process(self._animate_transit(item, connection))
    
    def _get_item_type_name(self, node_id: str, type_id: str) -> str:
        """Récupère le nom d'un type depuis son ID / Get type name from its ID
        
        Args:
            node_id: ID du nœud (pour trouver la source) / Node ID (to find the source)
            type_id: ID du type / Type ID
            
        Returns:
            str: Nom du type ou l'ID si non trouvé / Type name or ID if not found
        """
        if not type_id:
            return 'default'
            
        # Chercher le type dans toutes les sources / Search for type in all sources
        for node in self.flow_model.nodes.values():
            if node.is_source and hasattr(node, 'item_type_config') and node.item_type_config:
                for item_type in node.item_type_config.item_types:
                    if item_type.type_id == type_id:
                        return item_type.name
        
        # Si non trouvé, retourner l'ID / If not found, return the ID
        return type_id
    
    def _decrement_buffer_type_count(self, connection_id: str, type_counts_to_decrement: dict):
        """Décrément le compteur de types pour des items consommés du buffer / Decrement type counter for items consumed from buffer
        
        Args:
            connection_id: ID de la connexion / Connection ID
            type_counts_to_decrement: Dictionnaire {type_name: count} des items à décrémenter / Dictionary {type_name: count} of items to decrement
        """
        if connection_id not in self.buffer_type_counts:
            return
        
        if not type_counts_to_decrement:
            return
        
        # Décrémenter les compteurs avec format uniforme [BUFFER_TYPE] / Decrement counters with uniform [BUFFER_TYPE] format
        type_counts = self.buffer_type_counts[connection_id]
        
        for item_type_name, count in type_counts_to_decrement.items():
            if item_type_name in type_counts:
                old_count = type_counts[item_type_name]
                type_counts[item_type_name] -= count
                new_count = type_counts[item_type_name]
                
                # Print format uniforme avec AJOUT
                
                if type_counts[item_type_name] <= 0:
                    del type_counts[item_type_name]

    
    def _get_buffer_type_counts(self, connection_id: str) -> dict:
        """Récupère le nombre d'items par type dans le buffer d'une connexion / Get item count by type in a connection's buffer
        
        Returns:
            Dictionnaire {type_name: count} où type_name est le nom du type (pas l'ID) / Dictionary {type_name: count} where type_name is the type name (not ID)
        """
        # Utiliser le dictionnaire manuel au lieu de store.items pour éviter les problèmes de timing SimPy / Use manual dictionary instead of store.items to avoid SimPy timing issues
        type_counts = self.buffer_type_counts.get(connection_id, {}).copy()
        return type_counts
    
    def _record_probe_measurement(self, connection_id, quantity: int, buffer_count: int, item_type_name: str = None):
        """Enregistre une mesure pour toutes les pipettes sur cette connexion / Record a measurement for all probes on this connection
        
        Args:
            connection_id: ID de la connexion / Connection ID
            quantity: Nombre d'unités qui transitent / Number of units in transit
            buffer_count: Nombre d'items dans le buffer (attendu après ajout) / Number of items in buffer (expected after addition)
            item_type_name: Nom du type de l'item qui passe (pour tracking cumulatif) / Item type name passing (for cumulative tracking)
        """
        if not self.env:
            return
        
        # Vérifier si la connexion va vers un sink (sortie du système) / Check if connection goes to a sink (system output)
        connection = self.flow_model.get_connection(connection_id)
        target_node = self.flow_model.get_node(connection.target_id) if connection else None
        is_output_connection = target_node and target_node.is_sink
        
        # Récupérer les types d'items dans le buffer pour le mode by_type / Get item types in buffer for by_type mode
        type_counts = self._get_buffer_type_counts(connection_id)
        
        
        for probe in self.flow_model.probes.values():
            if probe.connection_id == connection_id:
                # Pour les connexions vers des sinks, ne PAS enregistrer les "entrées"
                # car ce sont en réalité des sorties du système
                # On comptera uniquement via add_item_consumed dans _record_probe_consumption
                # For connections to sinks, do NOT record "entries"
                # because they are actually system outputs
                # We will only count via add_item_consumed in _record_probe_consumption
                if not is_output_connection:
                    # Enregistrer l'événement d'entrée avec le type (seulement si pas vers sink) / Record entry event with type (only if not to sink)
                    probe.add_item_passing(self.env.now, quantity, item_type_name)
                
                # Toujours enregistrer la mesure avec le buffer count et les types / Always record measurement with buffer count and types
                probe.add_measurement(self.env.now, buffer_count, type_counts)
                
                # Capturer pour l'analyse (export CSV) / Capture for analysis (CSV export)
                if hasattr(self, '_capture_probe_measurement'):
                    if probe.measure_mode == "cumulative":
                        value = max(probe.total_items_out, probe.total_items)
                    else:
                        value = buffer_count
                    self._capture_probe_measurement(probe.probe_id, self.env.now, value)
                
                if hasattr(self, '_capture_probe_measurement_both'):
                    cumulative_value = max(probe.total_items_out, probe.total_items)
                    self._capture_probe_measurement_both(probe.probe_id, self.env.now, buffer_count, cumulative_value)
                
                if self.app_config.DEBUG_MODE and not self.fast_mode:
                    sum_types = sum(type_counts.values()) if type_counts else 0
                    status = "✓" if sum_types == buffer_count else "⚠️ INCOHÉRENT"
                    print(f"[MESURE_ENTRÉE] t={self.env.now:.4f} | {probe.name} | buffer={buffer_count} | types={type_counts} | sum={sum_types} {status}")

    
    def _record_item_type_arrival(self, node_id: str, item: dict):
        """Enregistre l'arrivée d'un item typé sur un nœud / Record typed item arrival at a node"""
        item_type = item.get('item_type')
        if item_type and self.env:
            self.item_type_stats.record_arrival(self.env.now, node_id, item_type)
            # Enregistrer dans le panneau si disponible / Record in panel if available
            if hasattr(self, '_record_node_arrival'):
                self._record_node_arrival(node_id, item_type)
    
    def _record_item_type_departure(self, node_id: str, item_type: str):
        """Enregistre le départ d'un item typé d'un nœud / Record typed item departure from a node"""
        if item_type and self.env:
            self.item_type_stats.record_departure(self.env.now, node_id, item_type)
            # Enregistrer dans le panneau si disponible / Record in panel if available
            if hasattr(self, '_record_node_departure'):
                self._record_node_departure(node_id, item_type)
    
    def _record_probe_consumption(self, connection_id, quantity: int = 1, items_consumed: list = None):
        """Enregistre la consommation d'items pour toutes les pipettes sur cette connexion / Record item consumption for all probes on this connection
        
        Args:
            connection_id: ID de la connexion / Connection ID
            quantity: Nombre d'unités consommées (par défaut 1) / Number of units consumed (default 1)
            items_consumed: Liste des items réellement consommés (pour connaître leurs types) / List of actually consumed items (to know their types)
        """
        if not self.env:
            return
        
        connection = self.flow_model.get_connection(connection_id)
        if not connection:
            return
        
        # IMPORTANT: Déterminer quels types sont consommés / IMPORTANT: Determine which types are consumed
        # Si items_consumed est fourni, utiliser ces items / If items_consumed provided, use these items
        # Sinon, inspecter le store (peut être vide si déjà consommé) / Otherwise, inspect the store (may be empty if already consumed)
        types_to_decrement = {}
        
        if items_consumed:
            # Utiliser les items fournis pour connaître leurs types / Use provided items to know their types
            for item in items_consumed:
                item_type_name = item.get('item_type_name', 'default')
                types_to_decrement[item_type_name] = types_to_decrement.get(item_type_name, 0) + 1
        else:
            # Fallback: inspecter le store (peut être vide) / Fallback: inspect the store (may be empty)
            store = self.stores.get(connection_id)
            if store and hasattr(store, 'items') and len(store.items) >= quantity:
                # Compter les types des quantity premiers items qui vont être consommés / Count types of first 'quantity' items to be consumed
                for i in range(quantity):
                    item_type_name = store.items[i].get('item_type_name', 'default')
                    types_to_decrement[item_type_name] = types_to_decrement.get(item_type_name, 0) + 1
        

        
        # Décrémenter le compteur de types AVANT la consommation physique / Decrement type counter BEFORE physical consumption
        # Passer SEULEMENT les types des items réellement consommés / Pass ONLY the types of actually consumed items
        self._decrement_buffer_type_count(connection_id, types_to_decrement)
        
        # IMPORTANT: Décrémenter le buffer count AVANT d'enregistrer dans les pipettes / IMPORTANT: Decrement buffer count BEFORE recording in probes
        buffer_before = connection.current_buffer_count
        new_buffer_count = max(0, buffer_before - quantity)
        self._update_buffer_count(connection, new_buffer_count)
        connection._needs_visual_update = True
        
        # Récupérer les types APRÈS décrémentation (état actuel du buffer) / Get types AFTER decrement (current buffer state)
        type_counts_after = self._get_buffer_type_counts(connection_id)
        

        
        # Ajouter un epsilon pour séparer visuellement entrée et sortie au même instant / Add epsilon to visually separate entry and exit at same time
        # Cela permet à matplotlib de tracer correctement avec step='post' / This allows matplotlib to draw correctly with step='post'
        consumption_timestamp = self.env.now + 0.001
        
        # Vérifier si cette connexion mène vers un SINK (sortie système) / Check if this connection leads to a SINK (system output)
        target_node = self.flow_model.get_node(connection.target_id) if connection else None
        is_sink_connection = target_node and target_node.is_sink
        
        for probe in self.flow_model.probes.values():
            if probe.connection_id == connection_id:
                # SEULEMENT enregistrer les sorties si connexion vers SINK / ONLY record outputs if connection to SINK
                # Les consommations intermédiaires (nœud prend items pour traitement) ne doivent PAS incrémenter total_items_out
                # Intermediate consumptions (node takes items for processing) must NOT increment total_items_out
                if is_sink_connection:
                    probe.add_item_consumed(consumption_timestamp, quantity, types_to_decrement)
                
                # En mode buffer : enregistrer l'état APRÈS consommation / In buffer mode: record state AFTER consumption
                # En mode cumulative : on utilise le cumulatif, donc les types importent peu ici / In cumulative mode: we use cumulative, so types matter little here
                probe.add_measurement(consumption_timestamp, new_buffer_count, type_counts_after)
                
                # Capturer pour l'analyse (export CSV) / Capture for analysis (CSV export)
                if hasattr(self, '_capture_probe_measurement'):
                    if probe.measure_mode == "cumulative":
                        value = max(probe.total_items_out, probe.total_items)
                    else:
                        value = new_buffer_count
                    self._capture_probe_measurement(probe.probe_id, consumption_timestamp, value)
                
                if hasattr(self, '_capture_probe_measurement_both'):
                    cumulative_value = max(probe.total_items_out, probe.total_items)
                    self._capture_probe_measurement_both(probe.probe_id, consumption_timestamp, new_buffer_count, cumulative_value)
                
                if self.app_config.DEBUG_MODE and not self.fast_mode:
                    sum_types = sum(type_counts_after.values()) if type_counts_after else 0
                    status = "✓" if sum_types == new_buffer_count else "⚠️ INCOHÉRENT"
                    print(f"[MESURE_SORTIE] t={consumption_timestamp:.4f} | {probe.name} | buffer={new_buffer_count} | types={type_counts_after} | sum={sum_types} {status}")
    
    def _put_item_back(self, store, item, connection_id):
        """Remet un item dans un store (peut bloquer si plein) / Put an item back in a store (may block if full)
        
        Cette fonction est exécutée en arrière-plan pour ne pas bloquer le cycle principal.
        Utilisée quand AnyOf retire plusieurs items mais qu'un seul est nécessaire.
        
        This function runs in background to not block the main cycle.
        Used when AnyOf removes multiple items but only one is needed.
        
        Args:
            store: Le store SimPy où remettre l'item / The SimPy store to put the item back
            item: L'item à remettre / The item to put back
            connection_id: L'ID de la connexion pour mise à jour du compteur / Connection ID for counter update
        """
        try:
            # Attendre qu'il y ait de la place (peut bloquer) / Wait for space (may block)
            yield store.put(item)
            
            # Mettre à jour le compteur de buffer (INCRÉMENTER car item ajouté) / Update buffer counter (INCREMENT as item added)
            connection = self.flow_model.get_connection(connection_id)
            if connection:
                buffer_before = connection.current_buffer_count
                new_buffer = buffer_before + 1
                self._update_buffer_count(connection, new_buffer)
                connection._needs_visual_update = True
        except Exception as e:
            if self.app_config.DEBUG_MODE and not self.fast_mode:
                print(f"[DEBUG] Error putting item back in {connection_id}: {e}")
    
    def _record_time_probe_measurement(self, node_id: str, time_value: float, probe_type_name: str):
        """Enregistre une mesure de temps pour toutes les loupes sur ce nœud / Record a time measurement for all time probes on this node
        
        Args:
            node_id: ID du nœud / Node ID
            time_value: Valeur du temps mesuré (en unités de simulation) / Measured time value (in simulation units)
            probe_type_name: Type de mesure ('PROCESSING', 'INTER_EVENTS') / Measurement type ('PROCESSING', 'INTER_EVENTS')
        """
        if not self.env:
            return
        
        from models.time_probe import TimeProbeType
        
        # Debug: compter les appels (désactivé pour performance) / Debug: count calls (disabled for performance)
        # if not hasattr(self, '_probe_call_counter'):
        #     self._probe_call_counter = 0
        #     print(f"\n[SIM DEBUG] === Début du tracking des loupes ===")
        #     print(f"[SIM DEBUG] Loupes disponibles dans flow_model: {len(self.flow_model.time_probes)}")
        #     for pid, probe in self.flow_model.time_probes.items():
        #         print(f"[SIM DEBUG]   - {pid}: node_id={probe.node_id}, type={probe.probe_type.name}")
        #     print(f"[SIM DEBUG] =====================================\n")
        # 
        # self._probe_call_counter += 1
        # 
        # # Afficher les 5 premiers appels pour debug
        # if self._probe_call_counter <= 5:
        #     print(f"[SIM DEBUG] Appel #{self._probe_call_counter}: node_id={node_id}, type={probe_type_name}, value={time_value:.2f}")
        
        # recorded_count = 0
        for time_probe in self.flow_model.time_probes.values():
            if time_probe.node_id == node_id and time_probe.probe_type.name == probe_type_name:
                time_probe.add_measurement(time_value)
                # recorded_count += 1
                # if self._probe_call_counter <= 5:
                #     print(f"[SIM DEBUG]   ✓ Mesure enregistrée dans loupe {time_probe.probe_id}")
        
        # if self._probe_call_counter <= 5 and recorded_count == 0:
        #     print(f"[SIM DEBUG]   ✗ Aucune loupe correspondante trouvée")
        # 
        # # Debug: afficher un message toutes les 10 mesures
        # if recorded_count > 0:
        #     if not hasattr(self, '_probe_debug_counter'):
        #         self._probe_debug_counter = {}
        #     key = f"{node_id}_{probe_type_name}"
        #     self._probe_debug_counter[key] = self._probe_debug_counter.get(key, 0) + 1
        #     
        #     if self._probe_debug_counter[key] % 10 == 0:
        #         print(f"[SIM DEBUG] {recorded_count} loupe(s) enregistrée(s) sur {node_id} ({probe_type_name}): {time_value:.2f} - Total: {self._probe_debug_counter[key]}")
    
    def _update_all_probes(self):
        """Met à jour toutes les pipettes avec les valeurs actuelles des buffers / Update all probes with current buffer values"""
        if not self.env:
            return
        
        for probe in self.flow_model.probes.values():
            connection = self.flow_model.get_connection(probe.connection_id)
            if connection:
                # Récupérer les types d'items dans le buffer pour le mode by_type / Get item types in buffer for by_type mode
                type_counts = self._get_buffer_type_counts(probe.connection_id)
                probe.add_measurement(self.env.now, connection.current_buffer_count, type_counts)
                
                # Capturer pour l'analyse si le hook existe / Capture for analysis if hook exists
                if hasattr(self, '_capture_probe_measurement'):
                    if probe.measure_mode == "cumulative":
                        # Pour pipettes cumulatives : utiliser max(total_items_out, total_items)
                        # Cohérent avec measurement_probe.py ligne 60-65
                        # For cumulative probes: use max(total_items_out, total_items)
                        # Consistent with measurement_probe.py line 60-65
                        value = max(probe.total_items_out, probe.total_items)
                    else:
                        value = connection.current_buffer_count
                    self._capture_probe_measurement(probe.probe_id, self.env.now, value)
                
                # NOUVEAU: Capturer les deux types de valeurs pour l'export CSV / NEW: Capture both value types for CSV export
                if hasattr(self, '_capture_probe_measurement_both'):
                    buffer_value = connection.current_buffer_count
                    cumulative_value = max(probe.total_items_out, probe.total_items)
                    self._capture_probe_measurement_both(probe.probe_id, self.env.now, buffer_value, cumulative_value)
        
        # Capturer le WIP (Work In Progress) pour l'analyse / Capture WIP (Work In Progress) for analysis
        if hasattr(self, '_capture_wip'):
            self._capture_wip(self.env.now)
    
    def _get_generation_interval(self, node: FlowNode) -> float:
        """Calcule l'intervalle de génération selon la loi du nœud source / Calculate generation interval according to source node distribution"""
        from models.flow_model import SourceMode
        
        # Convertir l'intervalle en unités de simulation (secondes) / Convert interval to simulation units (seconds)
        base_interval = node.generation_interval_cs / 100.0
        
        # Récupérer le mode (avec fallback pour compatibilité) / Get mode (with fallback for compatibility)
        source_mode = getattr(node, 'source_mode', SourceMode.CONSTANT)
        
        if source_mode == SourceMode.CONSTANT:
            # Intervalle constant / Constant interval
            return base_interval
        
        elif source_mode == SourceMode.NORMAL:
            # Loi normale / Normal distribution
            std_dev = node.generation_std_dev / 100.0
            interval = random.gauss(base_interval, std_dev)
            return max(0.01, interval)  # Éviter les valeurs négatives / Avoid negative values
        
        elif source_mode == SourceMode.SKEW_NORMAL:
            # Loi normale asymétrique (skew-normal) / Skew-normal distribution
            std_dev = node.generation_std_dev / 100.0
            alpha = getattr(node, 'generation_skewness', 0.0)
            
            # Utiliser scipy.stats.skewnorm / Use scipy.stats.skewnorm
            interval = stats.skewnorm.rvs(alpha, loc=base_interval, scale=std_dev)
            return max(0.01, interval)  # Éviter les valeurs négatives / Avoid negative values
        
        # Modes obsolètes (compatibilité avec anciens fichiers) / Obsolete modes (compatibility with old files)
        elif source_mode == SourceMode.POISSON:
            # Loi de Poisson (via exponentielle pour les intervalles) / Poisson distribution (via exponential for intervals)
            lambda_param = node.generation_lambda
            if lambda_param > 0:
                return random.expovariate(lambda_param)
            return base_interval
        
        elif source_mode == SourceMode.EXPONENTIAL:
            # Loi exponentielle / Exponential distribution
            lambda_param = node.generation_lambda
            if lambda_param > 0:
                return random.expovariate(lambda_param)
            return base_interval
        
        return base_interval
    
    def _process_sink(self, node_id: str):
        """Traite les items dans un nœud sink (sortie) / Process items in a sink node (output)"""
        node = self.flow_model.get_node(node_id)
        if not node:
            return
        
        while self.is_running and self.env:
            if not self.is_paused:
                try:
                    # Lire depuis le store de la première connexion entrante / Read from first incoming connection's store
                    if node.input_connections:
                        conn_id = node.input_connections[0]
                        connection_store = self.stores.get(conn_id)
                        if connection_store:
                            # Attendre un item (bloque si vide) / Wait for an item (blocks if empty)
                            item = yield connection_store.get()
                            
                            # Décrémenter le buffer et notifier les pipettes / Decrement buffer and notify probes
                            # Passer l'item consommé pour connaître son type / Pass consumed item to know its type
                            self._record_probe_consumption(conn_id, 1, [item])
                            
                            # Activer le nœud pour montrer la réception / Activate node to show reception
                            if not node.is_active:
                                node._visual_changed = True
                            node.is_active = True
                            
                            # Capturer le changement d'état pour l'analyse / Capture state change for analysis
                            if hasattr(self, '_capture_node_active_change'):
                                self._capture_node_active_change(node_id, self.env.now, True)
                            if hasattr(self, '_capture_machine_state'):
                                self._capture_machine_state(node_id, self.env.now, "ON")
                            
                            # Compter l'item reçu / Count received item
                            node.items_received += 1
                            
                            # Capturer l'événement de sortie pour l'analyse / Capture output event for analysis
                            if hasattr(self, '_capture_output'):
                                self._capture_output(node_id, self.env.now)
                            
                            # Enregistrer le temps inter-événement pour les sondes de temps (sinks = inter-réceptions)
                            # AU MOMENT de la réception réelle, pas après le délai visuel
                            # Record inter-event time for time probes (sinks = inter-receptions)
                            # AT THE MOMENT of actual reception, not after visual delay
                            current_time = self.env.now
                            if node_id in self.last_event_times:
                                inter_event_time = current_time - self.last_event_times[node_id]
                                self._record_time_probe_measurement(node_id, inter_event_time, 'INTER_EVENTS')
                            self.last_event_times[node_id] = current_time
                            
                            # Garder actif pendant 0.25 unités de temps pour que ce soit visible (animation seulement)
                            # Keep active for 0.25 time units to be visible (animation only)
                            if self.env:
                                yield self.env.timeout(0.25)
                            
                            # Désactiver après le délai / Deactivate after delay
                            if node.is_active:
                                node._visual_changed = True
                            node.is_active = False
                            
                            # Capturer le changement d'état pour l'analyse / Capture state change for analysis
                            if hasattr(self, '_capture_node_active_change'):
                                self._capture_node_active_change(node_id, self.env.now, False)
                            if hasattr(self, '_capture_machine_state'):
                                self._capture_machine_state(node_id, self.env.now, "OFF")
                        else:
                            if self.env:
                                yield self.env.timeout(0.1)
                            else:
                                break
                    else:
                        if self.env:
                            yield self.env.timeout(0.1)
                        else:
                            break
                    
                except simpy.Interrupt:
                    break
                except Exception as e:
                    if self.app_config.DEBUG_MODE:
                        print(f"Error in sink {node_id}: {e}")
                    if self.env:
                        yield self.env.timeout(0.1)
                    else:
                        break
            else:
                if self.env:
                    yield self.env.timeout(0.1)
                else:
                    break
    
    def _process_splitter(self, node_id: str):
        """Traite un diviseur (splitter) - distribue les items vers plusieurs sorties / Process a splitter - distributes items to multiple outputs"""
        node = self.flow_model.get_node(node_id)
        if not node:
            return
        
        while self.is_running and self.env:
            if not self.is_paused:
                try:
                    # Attendre un item depuis l'entrée / Wait for an item from input
                    if node.input_connections:
                        conn_id = node.input_connections[0]
                        connection_store = self.stores.get(conn_id)
                        if connection_store:
                            # Attendre un item (bloque si vide) / Wait for an item (blocks if empty)
                            item = yield connection_store.get()
                            
                            # Capturer l'arrivée pour l'analyse / Capture arrival for analysis
                            if hasattr(self, '_capture_arrival'):
                                self._capture_arrival(node_id, self.env.now)
                            
                            # Décrémenter le buffer et notifier les pipettes / Decrement buffer and notify probes
                            # Passer l'item consommé pour connaître son type / Pass consumed item to know its type
                            self._record_probe_consumption(conn_id, 1, [item])
                            
                            # Activer le nœud / Activate the node
                            if not node.is_active:
                                node._visual_changed = True
                            node.is_active = True
                            if hasattr(self, '_capture_node_active_change'):
                                self._capture_node_active_change(node_id, self.env.now, True)
                            
                            # Sélectionner la sortie selon le mode / Select output according to mode
                            output_conn_id = None
                            from models.flow_model import SplitterMode
                            
                            if node.splitter_mode == SplitterMode.ROUND_ROBIN:
                                # Alternance entre les sorties / Alternate between outputs
                                if node.output_connections:
                                    output_conn_id = node.output_connections[node.splitter_current_index % len(node.output_connections)]
                                    node.splitter_current_index += 1
                            
                            elif node.splitter_mode == SplitterMode.FIRST_AVAILABLE:
                                # Chercher la première sortie disponible / Find first available output
                                from models.flow_model import FirstAvailableMode
                                
                                if node.first_available_mode == FirstAvailableMode.BY_BUFFER:
                                    # Mode 1: Vérifier buffer non plein (ancienne méthode) / Mode 1: Check non-full buffer (old method)
                                    for out_conn_id in node.output_connections:
                                        out_store = self.stores.get(out_conn_id)
                                        out_conn = self.flow_model.get_connection(out_conn_id)
                                        if out_store and out_conn:
                                            # Vérifier si le buffer a de la place / Check if buffer has space
                                            if len(out_store.items) < out_conn.buffer_capacity:
                                                output_conn_id = out_conn_id
                                                break
                                    # Si aucune n'est disponible, prendre la première (bloquera) / If none available, take first (will block)
                                    if not output_conn_id and node.output_connections:
                                        output_conn_id = node.output_connections[0]
                                
                                elif node.first_available_mode == FirstAvailableMode.BY_NODE_STATE:
                                    # Mode 2: Vérifier si le nœud cible est inactif / Mode 2: Check if target node is inactive
                                    for out_conn_id in node.output_connections:
                                        out_conn = self.flow_model.get_connection(out_conn_id)
                                        if out_conn:
                                            target_node = self.flow_model.get_node(out_conn.target_id)
                                            # Vérifier si le nœud cible n'est pas actif (pas en train de traiter) / Check if target node is not active (not processing)
                                            if target_node and not target_node.is_active:
                                                output_conn_id = out_conn_id
                                                break
                                    # Si tous les nœuds sont actifs, prendre le premier (bloquera) / If all nodes active, take first (will block)
                                    if not output_conn_id and node.output_connections:
                                        output_conn_id = node.output_connections[0]
                            
                            elif node.splitter_mode == SplitterMode.RANDOM:
                                # Distribution aléatoire / Random distribution
                                if node.output_connections:
                                    import random
                                    output_conn_id = random.choice(node.output_connections)
                            
                            # Envoyer l'item vers la sortie sélectionnée / Send item to selected output
                            if output_conn_id:
                                connection = self.flow_model.get_connection(output_conn_id)
                                connection_store = self.stores.get(output_conn_id)
                                if connection and connection_store:
                                    # Capturer la sortie pour l'analyse / Capture output for analysis
                                    if hasattr(self, '_capture_output'):
                                        self._capture_output(node_id, self.env.now)
                                    
                                    # Faire clignoter la connexion choisie / Flash the selected connection
                                    connection.highlight_until = self.env.now + 0.3  # Clignoter pendant 0.3 secondes / Flash for 0.3 seconds
                                    
                                    output_item = {
                                        'id': f"{node_id}_split_{item.get('id', 'unknown')}",
                                        'created_at': item.get('created_at', self.env.now),
                                        'node_id': node_id,
                                        'parent_id': item.get('id', 'unknown'),
                                        'item_type': item.get('item_type', None),  # Conserver le type / Keep the type
                                        'item_type_name': item.get('item_type_name', 'default')  # Conserver le nom / Keep the name
                                    }
                                    yield self.env.process(self._transit_item(output_item, connection, connection_store))
                            
                            # Désactiver le nœud / Deactivate the node
                            if node.is_active:
                                node._visual_changed = True
                            node.is_active = False
                            if hasattr(self, '_capture_node_active_change'):
                                self._capture_node_active_change(node_id, self.env.now, False)
                        else:
                            if self.env:
                                yield self.env.timeout(0.1)
                            else:
                                break
                    else:
                        if self.env:
                            yield self.env.timeout(0.1)
                        else:
                            break
                    
                except simpy.Interrupt:
                    break
                except Exception as e:
                    if self.app_config.DEBUG_MODE:
                        print(f"Error in splitter {node_id}: {e}")
                    if self.env:
                        yield self.env.timeout(0.1)
                    else:
                        break
            else:
                if self.env:
                    yield self.env.timeout(0.1)
                else:
                    break
    
    def _process_merger(self, node_id: str):
        """Traite un concatenateur (merger) - fusionne plusieurs entrées vers une sortie / Process a merger - combines multiple inputs to one output"""
        node = self.flow_model.get_node(node_id)
        if not node:
            return
        
        while self.is_running and self.env:
            if not self.is_paused:
                try:
                    # Attendre un item depuis N'IMPORTE QUELLE entrée (premier arrivé) / Wait for an item from ANY input (first arrived)
                    if node.input_connections:
                        # Créer une liste de requêtes pour toutes les entrées / Create request list for all inputs
                        get_events = []
                        for conn_id in node.input_connections:
                            connection_store = self.stores.get(conn_id)
                            if connection_store:
                                get_events.append(connection_store.get())
                        
                        if get_events:
                            # Attendre le premier item disponible de n'importe quelle entrée / Wait for first available item from any input
                            result = yield self.env.any_of(get_events)
                            
                            # Récupérer l'item qui est arrivé / Get the item that arrived
                            item = None
                            source_conn_id = None
                            for i, (conn_id, event) in enumerate(zip(node.input_connections, get_events)):
                                if event in result:
                                    item = result[event]
                                    source_conn_id = conn_id
                                    break
                            
                            if item:
                                # Capturer l'arrivée pour l'analyse / Capture arrival for analysis
                                if hasattr(self, '_capture_arrival'):
                                    self._capture_arrival(node_id, self.env.now)
                                
                                # Activer le nœud / Activate the node
                                if not node.is_active:
                                    node._visual_changed = True
                                node.is_active = True
                                if hasattr(self, '_capture_node_active_change'):
                                    self._capture_node_active_change(node_id, self.env.now, True)
                                
                                # Mettre à jour le buffer de la connexion d'entrée / Update input connection buffer
                                if source_conn_id:
                                    # Décrémenter le buffer et notifier les pipettes AVEC l'item / Decrement buffer and notify probes WITH item
                                    self._record_probe_consumption(source_conn_id, 1, [item])
                                    
                                    connection = self.flow_model.get_connection(source_conn_id)
                                    if connection:
                                        # Faire clignoter la connexion d'où vient l'item / Flash the connection where item came from
                                        connection.highlight_until = self.env.now + 0.3  # Clignoter pendant 0.3 secondes / Flash for 0.3 seconds
                                
                                # Envoyer l'item vers la sortie unique / Send item to single output
                                if node.output_connections:
                                    output_conn_id = node.output_connections[0]
                                    connection = self.flow_model.get_connection(output_conn_id)
                                    connection_store = self.stores.get(output_conn_id)
                                    if connection and connection_store:
                                        # Capturer la sortie pour l'analyse / Capture output for analysis
                                        if hasattr(self, '_capture_output'):
                                            self._capture_output(node_id, self.env.now)
                                        
                                        output_item = {
                                            'id': f"{node_id}_merge_{item.get('id', 'unknown')}",
                                            'created_at': item.get('created_at', self.env.now),
                                            'node_id': node_id,
                                            'parent_id': item.get('id', 'unknown'),
                                            'item_type': item.get('item_type', None),  # Conserver le type / Keep the type
                                            'item_type_name': item.get('item_type_name', 'default')  # Conserver le nom / Keep the name
                                        }
                                        yield self.env.process(self._transit_item(output_item, connection, connection_store))
                                
                                # Désactiver le nœud / Deactivate the node
                                if node.is_active:
                                    node._visual_changed = True
                                node.is_active = False
                                if hasattr(self, '_capture_node_active_change'):
                                    self._capture_node_active_change(node_id, self.env.now, False)
                        else:
                            if self.env:
                                yield self.env.timeout(0.1)
                            else:
                                break
                    else:
                        if self.env:
                            yield self.env.timeout(0.1)
                        else:
                            break
                    
                except simpy.Interrupt:
                    break
                except Exception as e:
                    if self.app_config.DEBUG_MODE:
                        print(f"Error in merger {node_id}: {e}")
                    if self.env:
                        yield self.env.timeout(0.1)
                    else:
                        break
            else:
                if self.env:
                    yield self.env.timeout(0.1)
                else:
                    break
    
    def _update_ui(self):
        """Processus pour mettre à jour l'interface périodiquement / Process to update interface periodically"""
        while self.is_running and self.env:
            if not self.is_paused:
                # Mettre à jour toutes les mesures des pipettes MOINS SOUVENT / Update all probe measurements LESS OFTEN
                # On ne le fait qu'1 fois sur 2 pour réduire la charge / Only do it 1 time out of 2 to reduce load
                if not hasattr(self, '_probe_update_counter'):
                    self._probe_update_counter = 0
                self._probe_update_counter += 1
                
                # Mise à jour des probes seulement 1 fois sur 2 (réduit charge de 50%) / Update probes only 1 time out of 2 (reduces load by 50%)
                if self._probe_update_counter % 2 == 0:
                    self._update_all_probes()
                
                # Appeler le callback de mise à jour si défini / Call update callback if defined
                if self.update_callback:
                    self.update_callback()
            
            # Mise à jour réduite pour meilleures performances / Reduced update for better performance
            # Utilise self.app_config.UI_UPDATE_INTERVAL de config.py (défaut: 0.5s) / Uses self.app_config.UI_UPDATE_INTERVAL from config.py (default: 0.5s)
            # Réduit la charge CPU tout en gardant une animation acceptable / Reduces CPU load while keeping acceptable animation
            if self.env:
                yield self.env.timeout(self.app_config.UI_UPDATE_INTERVAL)
            else:
                break
    
    def _find_operator_for_machine(self, node_id: str):
        """Trouve un opérateur assigné à une machine donnée et disponible / Find an operator assigned to a given machine and available
        
        Si plusieurs opérateurs peuvent contrôler cette machine, retourne le premier disponible.
        Si aucun n'est disponible, retourne le premier trouvé (qui sera en attente).
        
        If multiple operators can control this machine, returns the first available.
        If none available, returns the first found (which will be waiting).
        """
        available_operators = []
        busy_operators = []
        
        for operator_id, operator in self.flow_model.operators.items():
            if node_id in operator.assigned_machines:
                # Vérifier si l'opérateur est disponible (non utilisé par une autre machine) / Check if operator is available (not used by another machine)
                if self.operator_resources[operator_id].count == 0:
                    # L'opérateur est disponible / Operator is available
                    available_operators.append((operator_id, operator))
                else:
                    # L'opérateur est occupé / Operator is busy
                    busy_operators.append((operator_id, operator))
        
        # Priorité aux opérateurs disponibles / Priority to available operators
        if available_operators:
            return available_operators[0]
        elif busy_operators:
            # Tous les opérateurs sont occupés, retourner le premier / All operators are busy, return the first
            # (la machine attendra qu'il se libère) / (machine will wait for it to be free)
            return busy_operators[0]
        
        # Aucun opérateur n'est assigné à cette machine / No operator is assigned to this machine
        return None, None
    
    def _generate_travel_time(self, operator, from_machine: str, to_machine: str):
        """Génère un temps de déplacement selon la distribution configurée / Generate travel time according to configured distribution"""
        from models.operator import DistributionType
        
        # Obtenir la configuration du temps de déplacement / Get travel time configuration
        travel_config = operator.get_travel_time(from_machine, to_machine)
        if not travel_config:
            # Pas de configuration spécifique, utiliser un temps par défaut / No specific config, use default time
            return 1.0  # 1 centiseconde par défaut / 1 centisecond by default
        
        dist_type = travel_config['type']
        params = travel_config['params']
        
        if dist_type == DistributionType.CONSTANT:
            return params.get('value', 1.0)
        
        elif dist_type == DistributionType.NORMAL:
            mean = params.get('mean', 1.0)
            std_dev = params.get('std_dev', 0.1)
            return max(0.01, random.gauss(mean, std_dev))
        
        elif dist_type == DistributionType.SKEW_NORMAL:
            location = params.get('location', 1.0)
            scale = params.get('scale', 0.1)
            shape = params.get('shape', 0.0)
            return max(0.01, stats.skewnorm.rvs(shape, loc=location, scale=scale))
        
        return 1.0
    
    def _wait_for_operator(self, operator_id: str, operator, target_machine_id: str):
        """Attend que l'opérateur se déplace vers la machine cible et retourne la requête pour garder l'opérateur / Wait for operator to travel to target machine and return request to keep operator"""
        if self.app_config.DEBUG_MODE and not self.fast_mode:
            print(f"[DEBUG] Machine {target_machine_id} waiting for operator {operator.name}")
        
        # Demander l'opérateur comme ressource (sans with pour le garder) / Request operator as resource (without with to keep it)
        req = self.operator_resources[operator_id].request()
        yield req
        
        # L'opérateur est maintenant réservé pour cette machine / Operator is now reserved for this machine
        current_position = self.operator_positions.get(operator_id)
        
        if current_position != target_machine_id:
            # L'opérateur doit se déplacer / Operator must travel
            if current_position is not None:
                # Vérifier si c'est le déplacement initial (depuis la position initialisée) / Check if this is initial move (from initialized position)
                is_initial_move = not hasattr(operator, '_has_moved')
                
                # Calculer le temps de déplacement / Calculate travel time
                travel_time = self._generate_travel_time(operator, current_position, target_machine_id)
                
                # Accumuler le temps de déplacement pour statistiques (même premier déplacement) / Accumulate travel time for stats (even first move)
                self.operator_travel_time[operator_id] += travel_time
                
                # Enregistrer la mesure SEULEMENT si ce n'est PAS le premier déplacement
                # (car l'opérateur commence déjà sur sa première machine)
                # Record measurement ONLY if this is NOT the first move
                # (because operator starts already on their first machine)
                if not is_initial_move:
                    route_key = (current_position, target_machine_id)
                    if hasattr(operator, 'travel_probes') and route_key in operator.travel_probes:
                        probe = operator.travel_probes[route_key]
                        if probe.get('enabled', False):
                            if 'measurements' not in probe:
                                # Utiliser liste sans limite pour garder toutes les mesures / Use unlimited list to keep all measurements
                                probe['measurements'] = []
                            probe['measurements'].append(travel_time)
                
                # Marquer que l'opérateur a déjà bougé / Mark that operator has already moved
                operator._has_moved = True
                
                if not self.fast_mode and self.app_config.DEBUG_MODE:
                    print(f"[DEBUG] Operator {operator.name} traveling from {current_position} to {target_machine_id} (duration: {travel_time:.2f})")
                
                # Capturer l'état de l'opérateur (déplacement) / Capture operator state (traveling)
                if hasattr(self, '_capture_operator_state'):
                    from_node = self.flow_model.get_node(current_position)
                    from_name = from_node.name if from_node else current_position
                    to_node = self.flow_model.get_node(target_machine_id)
                    to_name = to_node.name if to_node else target_machine_id
                    self._capture_operator_state(operator_id, self.env.now, f"{tr('op_state_travel')} {from_name}→{to_name}", current_position)
                
                # Marquer l'opérateur comme indisponible pendant le déplacement / Mark operator as unavailable during travel
                operator.is_available = False
                
                # Obtenir les positions des machines / Get machine positions
                from_node = self.flow_model.get_node(current_position)
                to_node = self.flow_model.get_node(target_machine_id)
                
                # Animer le déplacement progressivement (en mode normal seulement) / Animate movement progressively (normal mode only)
                if not self.fast_mode and from_node and to_node:
                    # Stocker les infos d'animation pour interpolation / Store animation info for interpolation
                    operator.animation_from_node = current_position
                    operator.animation_to_node = target_machine_id
                    operator.animation_progress = 0.0
                    
                    # Animation progressive - nombre d'étapes configurable / Progressive animation - configurable number of steps
                    # Utilise self.app_config.OPERATOR_ANIMATION_STEPS de config.py (défaut: 5) / Uses self.app_config.OPERATOR_ANIMATION_STEPS from config.py (default: 5)
                    # Moins d'étapes = moins d'appels à update_callback = meilleures performances / Less steps = less update_callback calls = better performance
                    steps = self.app_config.OPERATOR_ANIMATION_STEPS
                    step_duration = travel_time / steps  # Temps par étape en unités de simulation / Time per step in simulation units
                    
                    for step in range(steps + 1):
                        progress = step / steps
                        operator.animation_progress = progress
                        
                        # Interpoler la position (en coordonnées modèle, pas canvas) / Interpolate position (in model coordinates, not canvas)
                        old_x, old_y = operator.x, operator.y
                        operator.x = from_node.x + (to_node.x - from_node.x) * progress
                        operator.y = from_node.y + (to_node.y - from_node.y) * progress
                        
                        # Forcer immédiatement la mise à jour du canvas pour animation fluide / Force immediate canvas update for smooth animation
                        if self.update_callback:
                            self.update_callback()
                        
                        if step < steps and self.env:
                            yield self.env.timeout(step_duration)
                    
                    # Animation terminée / Animation finished
                    operator.animation_from_node = None
                    operator.animation_to_node = None
                    operator.animation_progress = 1.0
                else:
                    # Mode rapide ou pas de nœuds : attente directe sans animation / Fast mode or no nodes: direct wait without animation
                    if self.env:
                        yield self.env.timeout(travel_time)
                
                # Mettre à jour la position finale / Update final position
                self.operator_positions[operator_id] = target_machine_id
                operator.current_machine_id = target_machine_id
                
                # Positionner l'opérateur sur la machine cible / Position operator at target machine
                target_node = self.flow_model.get_node(target_machine_id)
                if target_node:
                    operator.x = target_node.x
                    operator.y = target_node.y
                
                if not self.fast_mode:
                    print(f"[DEBUG] Operator {operator.name} arrived at {target_machine_id}")
                
                # Capturer l'arrivée à la machine / Capture arrival at machine
                if hasattr(self, '_capture_operator_state'):
                    target_node = self.flow_model.get_node(target_machine_id)
                    target_name = target_node.name if target_node else target_machine_id
                    self._capture_operator_state(operator_id, self.env.now, f"{tr('op_state_arrival')} {target_name}", target_machine_id)
            else:
                # Première utilisation, l'opérateur apparaît directement à la machine / First use, operator appears directly at machine
                self.operator_positions[operator_id] = target_machine_id
                operator.current_machine_id = target_machine_id
                
                # Capturer l'initialisation de position / Capture position initialization
                if hasattr(self, '_capture_operator_state'):
                    target_node = self.flow_model.get_node(target_machine_id)
                    target_name = target_node.name if target_node else target_machine_id
                    self._capture_operator_state(operator_id, self.env.now, f"{tr('op_state_init')} {target_name}", target_machine_id)
            
        # L'opérateur est maintenant disponible à la machine cible / Operator is now available at target machine
        operator.is_available = True
        
        if not self.fast_mode and self.app_config.DEBUG_MODE:
            print(f"[DEBUG] Operator {operator.name} ready to control {target_machine_id}")
        
        # Marquer le début de l'occupation de l'opérateur (APRÈS le déplacement)
        # Le temps de déplacement ne doit PAS être compté comme temps d'occupation
        # Mark start of operator busy time (AFTER travel)
        # Travel time must NOT be counted as busy time
        self.operator_busy_start[operator_id] = self.env.now
        
        # Capturer que l'opérateur contrôle la machine / Capture that operator controls the machine
        if hasattr(self, '_capture_operator_state'):
            target_node = self.flow_model.get_node(target_machine_id)
            target_name = target_node.name if target_node else target_machine_id
            self._capture_operator_state(operator_id, self.env.now, f"{tr('op_state_control')} {target_name}", target_machine_id)
        
        # Retourner la requête pour que l'appelant puisse la libérer après le traitement / Return request so caller can release it after processing
        return req
    
    def _process_node(self, node_id: str):
        """Traite les items dans un nœud / Process items in a node"""
        node = self.flow_model.get_node(node_id)
        if not node:
            return
        
        while self.is_running and self.env:
            if not self.is_paused:
                try:
                    # Attendre les items selon le mode de synchronisation / Wait for items according to synchronization mode
                    items = yield self.env.process(self._wait_for_items(node))
                    
                    if not items:
                        if self.env:
                            yield self.env.timeout(0.1)
                        else:
                            break
                        continue
                    
                    if not self.fast_mode:
                        print(f"[DEBUG] {node.name} (t={self.env.now:.2f}): {len(items)} item(s) received, starting processing")
                    
                    # Capturer l'arrivée des items pour l'analyse / Capture item arrivals for analysis
                    if hasattr(self, '_capture_arrival'):
                        for _ in items:
                            self._capture_arrival(node_id, self.env.now)
                    
                    # Enregistrer l'arrivée des items par type / Record item arrivals by type
                    for item in items:
                        self._record_item_type_arrival(node_id, item)
                    
                    # Vérifier si un opérateur est nécessaire pour cette machine / Check if operator is needed for this machine
                    operator_id, operator = self._find_operator_for_machine(node_id)
                    operator_req = None
                    if operator_id and operator:
                        # Attendre que l'opérateur arrive à cette machine ET le garder / Wait for operator to arrive at this machine AND keep it
                        if not self.fast_mode:
                            print(f"[DEBUG] {node.name} (t={self.env.now:.2f}): Waiting for operator {operator.name}...")
                        operator_req = yield self.env.process(self._wait_for_operator(operator_id, operator, node_id))
                        if not self.fast_mode:
                            print(f"[DEBUG] {node.name} (t={self.env.now:.2f}): Operator {operator.name} present")
                    
                    # Demander la ressource / Request the resource
                    if not self.fast_mode:
                        print(f"[DEBUG] {node.name} (t={self.env.now:.2f}): Requesting resource...")
                    with self.resources[node_id].request() as req:
                        yield req
                        if not self.fast_mode:
                            print(f"[DEBUG] {node.name} (t={self.env.now:.2f}): Resource obtained")
                        
                        # Marquer comme actif pendant le traitement / Mark as active during processing
                        if not node.is_active:
                            node._visual_changed = True
                        node.is_active = True
                        
                        # Capturer le changement d'état pour l'analyse / Capture state change for analysis
                        if hasattr(self, '_capture_node_active_change'):
                            self._capture_node_active_change(node_id, self.env.now, True)
                        
                        # Capturer machine ON: SEULEMENT si on a des items à traiter (len(items) > 0)
                        # ET si l'opérateur est présent (si requis)
                        # Note: À ce stade, items a déjà été récupéré donc on sait qu'il y en a
                        # Capture machine ON: ONLY if we have items to process (len(items) > 0)
                        # AND if operator is present (if required)
                        # Note: At this point, items has already been retrieved so we know there are some
                        if hasattr(self, '_capture_machine_state') and len(items) > 0:
                            if not operator_req:
                                # Pas d'opérateur requis, capturer normalement / No operator required, capture normally
                                self._capture_machine_state(node_id, self.env.now, "ON")
                            elif operator and operator.current_machine_id == node_id:
                                # Opérateur requis ET c'est sa machine actuelle / Operator required AND it's their current machine
                                self._capture_machine_state(node_id, self.env.now, "ON")
                                if not self.fast_mode and self.app_config.DEBUG_MODE:
                                    print(f"[DEBUG_STATE] Machine {node_id} ON - operator {operator.name} current_machine={operator.current_machine_id}")
                            elif not self.fast_mode and self.app_config.DEBUG_MODE:
                                print(f"[DEBUG_STATE] Machine {node_id} NO ON capture - operator {operator.name if operator else 'None'} current_machine={operator.current_machine_id if operator else 'N/A'}")
                        
                        # Temps de traitement (en centisecondes dans le modèle) / Processing time (in centiseconds in model)
                        # Déterminer le type d'item entrant (premier item du lot) / Determine incoming item type (first item in batch)
                        item_type_id = items[0].get('item_type', None) if items else None
                        
                        # Si on a un traitement par type configuré, l'utiliser / If type-specific processing is configured, use it
                        if item_type_id and node.processing_config.processing_times_cs:
                            mean_cs = node.processing_config.get_processing_time_cs(item_type_id)
                            mode_str = node.processing_config.processing_modes.get(item_type_id, 'CONSTANT')
                            from models.flow_model import ProcessingTimeMode
                            if mode_str == 'NORMAL':
                                mode = ProcessingTimeMode.NORMAL
                            elif mode_str == 'SKEW_NORMAL':
                                mode = ProcessingTimeMode.SKEW_NORMAL
                            else:
                                mode = ProcessingTimeMode.CONSTANT
                            std_dev_cs = node.processing_config.std_devs_cs.get(item_type_id, 0.0)
                            alpha = node.processing_config.skewnesses.get(item_type_id, 0.0)
                        else:
                            # Utiliser les paramètres par défaut du nœud / Use node's default parameters
                            from models.flow_model import ProcessingTimeMode
                            mode = getattr(node, 'processing_time_mode', ProcessingTimeMode.CONSTANT)
                            mean_cs = node.processing_time_cs
                            std_dev_cs = getattr(node, 'processing_time_std_dev_cs', 0.0)
                            alpha = getattr(node, 'processing_time_skewness', 0.0)
                            if alpha == 0.0:
                                alpha = getattr(node, 'processing_time_alpha', 0.0)
                        
                        # Générer selon le mode (CONSTANT, NORMAL ou SKEW_NORMAL) / Generate according to mode (CONSTANT, NORMAL or SKEW_NORMAL)
                        if mode == ProcessingTimeMode.NORMAL:
                            # Loi normale avec moyenne et écart-type / Normal distribution with mean and std dev
                            import random
                            processing_time_cs = max(0.01, random.gauss(mean_cs, std_dev_cs))
                        elif mode == ProcessingTimeMode.SKEW_NORMAL:
                            # Distribution skew-normal de scipy / Scipy skew-normal distribution
                            processing_time_cs = max(0.01, stats.skewnorm.rvs(alpha, loc=mean_cs, scale=std_dev_cs))
                        else:
                            # Temps constant / Constant time
                            processing_time_cs = mean_cs
                        
                        processing_time_sim = processing_time_cs / 100.0  # Convertir en unités de simulation / Convert to simulation units
                        
                        # Traiter / Process
                        if self.env:
                            yield self.env.timeout(processing_time_sim)
                        else:
                            if node.is_active:
                                node._visual_changed = True
                            node.is_active = False
                            break
                        
                        # Capturer le temps de traitement dans les loupes de temps (APRÈS le traitement) / Capture processing time in time probes (AFTER processing)
                        self._record_time_probe_measurement(node_id, processing_time_sim, 'PROCESSING')
                        
                        # Mettre à jour les statistiques / Update statistics
                        self.stats['items_processed'][node_id] += len(items)
                        
                        # Enregistrer le temps inter-événement pour les sondes de temps (nœuds traitement = inter-départs)
                        # Record inter-event time for time probes (processing nodes = inter-departures)
                        current_time = self.env.now
                        if node_id in self.last_event_times:
                            inter_event_time = current_time - self.last_event_times[node_id]
                            self._record_time_probe_measurement(node_id, inter_event_time, 'INTER_EVENTS')
                        self.last_event_times[node_id] = current_time
                        
                        # Calculer combien d'unités envoyer en sortie / Calculate how many units to send as output
                        # IMPORTANT: Si on utilise les combinaisons, les items retournés par _wait_for_items
                        # sont DÉJÀ les items de sortie transformés (soupes, etc.)
                        # IMPORTANT: If using combinations, items returned by _wait_for_items
                        # are ALREADY the transformed output items (soups, etc.)
                        if getattr(node, 'use_combinations', False) and node.sync_mode == SyncMode.WAIT_N_FROM_BRANCH:
                            # Mode combinaisons : les items retournés sont les items finaux / Combinations mode: returned items are final items
                            # On envoie exactement ces items (pas de output_multiplier) / Send exactly these items (no output_multiplier)
                            total_items_to_send = len(items)
                            if self.app_config.DEBUG_MODE:
                                print(f"[DEBUG] Node {node.name} - COMBINATIONS mode")
                                print(f"  - Transformed items received: {len(items)}")
                                print(f"  - Items to send: {total_items_to_send}")
                        elif node.sync_mode == SyncMode.WAIT_N_FROM_BRANCH and not getattr(node, 'use_combinations', False):
                            # Mode legacy: utiliser la configuration spécifique / Legacy mode: use specific configuration
                            output_multiplier = getattr(node, 'legacy_output_quantity', 1)
                            total_items_to_send = output_multiplier
                            if self.app_config.DEBUG_MODE:
                                print(f"[DEBUG] Node {node.name} - LEGACY mode")
                                print(f"  - Output multiplier: {output_multiplier}")
                        else:
                            # Mode standard / Standard mode
                            output_multiplier = getattr(node, 'output_multiplier', 1)
                            total_items_to_send = output_multiplier
                            if self.app_config.DEBUG_MODE:
                                print(f"[DEBUG] Node {node.name} - STANDARD mode")
                                print(f"  - Output multiplier: {output_multiplier}")
                        
                        # DEBUG: Logger les informations (désactivé en mode turbo) / DEBUG: Log information (disabled in turbo mode)
                        if not self.fast_mode and self.app_config.DEBUG_MODE:
                            print(f"[DEBUG] Node {node.name} (ID: {node_id}):")
                            if self.app_config.DEBUG_MODE:
                                print(f"  - Items processed: {len(items)}")
                            if self.app_config.DEBUG_MODE:
                                print(f"  - Output connections: {len(node.output_connections)}")
                            if self.app_config.DEBUG_MODE:
                                print(f"  - Connection IDs: {node.output_connections}")
                        num_full_items = int(total_items_to_send)
                        fractional_part = total_items_to_send - num_full_items
                        
                        if self.app_config.DEBUG_MODE:
                            print(f"  - TOTAL items to send: {total_items_to_send} ({num_full_items} full + {fractional_part:.2f} fractional)")
                        
                        # Envoyer le nombre absolu d'items configuré / Send configured absolute number of items
                        # Une seule animation par connexion, mais avec N unités / Single animation per connection, but with N units
                        source_item = items[0] if items else {'id': 'unknown', 'created_at': self.env.now}
                        
                        # Déterminer le type de sortie (transformation possible) / Determine output type (possible transformation)
                        input_type = source_item.get('item_type', None)
                        
                        # Pour le mode WAIT_N_FROM_BRANCH legacy, utiliser legacy_output_type si configuré / For legacy WAIT_N_FROM_BRANCH mode, use legacy_output_type if configured
                        if node.sync_mode == SyncMode.WAIT_N_FROM_BRANCH and not getattr(node, 'use_combinations', False):
                            legacy_output_type = getattr(node, 'legacy_output_type', '')
                            if legacy_output_type:
                                output_type = legacy_output_type
                            else:
                                # Pas de type spécifié, garder le type d'entrée / No type specified, keep input type
                                output_type = input_type
                        else:
                            # Mode standard: utiliser la transformation configurée ou garder le type d'entrée / Standard mode: use configured transformation or keep input type
                            output_type = node.processing_config.get_output_type(input_type) if input_type else input_type
                        
                        output_type_name = self._get_item_type_name(node_id, output_type) if output_type else 'default'
                        
                        # Capturer les sorties pour l'analyse / Capture outputs for analysis
                        if hasattr(self, '_capture_output'):
                            for _ in range(num_full_items):
                                self._capture_output(node_id, self.env.now)
                        
                        # Enregistrer le départ des items (transformation possible) / Record item departures (possible transformation)
                        if output_type:
                            for _ in range(num_full_items):
                                self._record_item_type_departure(node_id, output_type)
                        
                        for conn_id in node.output_connections:
                            connection = self.flow_model.get_connection(conn_id)
                            if connection and self.env:
                                connection_store = self.stores.get(conn_id)
                                if connection_store:
                                    # Créer un seul item de sortie (pour l'animation) / Create single output item (for animation)
                                    output_item = {
                                        'id': f"{node_id}_out_conn_{conn_id}",
                                        'created_at': source_item.get('created_at', self.env.now),
                                        'node_id': node_id,
                                        'parent_id': source_item.get('id', 'unknown'),
                                        'quantity': num_full_items,  # Quantité transportée / Quantity transported
                                        'item_type': output_type,  # Type de sortie (peut être transformé) / Output type (may be transformed)
                                        'item_type_name': output_type_name  # Nom du type pour l'affichage / Type name for display
                                    }
                                    if self.app_config.DEBUG_MODE:
                                        print(f"    → Sending {num_full_items} unit(s) via {output_item['id']} on connection {conn_id} (type: {output_type})")
                                    # Transférer les items (peut bloquer si buffer plein, mais animation en parallèle) / Transfer items (may block if buffer full, but animation in parallel)
                                    yield self.env.process(self._transit_item(output_item, connection, connection_store, quantity=num_full_items))
                        
                        # Gérer la partie fractionnaire avec probabilité / Handle fractional part with probability
                        if fractional_part > 0:
                            import random
                            if random.random() < fractional_part:
                                if self.app_config.DEBUG_MODE:
                                    print(f"  - Fractional part activated ({fractional_part:.2f})")
                                source_item = items[0] if items else {'id': 'unknown', 'created_at': self.env.now}
                                
                                for conn_id in node.output_connections:
                                    connection = self.flow_model.get_connection(conn_id)
                                    if connection and self.env:
                                        connection_store = self.stores.get(conn_id)
                                        if connection_store:
                                            output_item = {
                                                'id': f"{node_id}_out_frac_conn_{conn_id}",
                                                'created_at': source_item.get('created_at', self.env.now),
                                                'node_id': node_id,
                                                'parent_id': source_item.get('id', 'unknown'),
                                                'quantity': 1,
                                                'item_type': output_type,  # Même transformation de type / Same type transformation
                                                'item_type_name': output_type_name  # Nom du type pour l'affichage / Type name for display
                                            }
                                            if self.app_config.DEBUG_MODE:
                                                print(f"    → Sending fractional 1 unit via {output_item['id']} on connection {conn_id} (type: {output_type})")
                                            # Transférer l'item (peut bloquer si buffer plein, mais animation en parallèle) / Transfer item (may block if buffer full, but animation in parallel)
                                            yield self.env.process(self._transit_item(output_item, connection, connection_store, quantity=1))
                        
                        # Désactiver le nœud après envoi (pas de délai supplémentaire) / Deactivate node after sending (no additional delay)
                        # Le nœud était actif pendant toute la durée du traitement / Node was active during entire processing time
                        if node.is_active:
                            node._visual_changed = True
                        node.is_active = False
                        
                        # Capturer le changement d'état pour l'analyse / Capture state change for analysis
                        if hasattr(self, '_capture_node_active_change'):
                            self._capture_node_active_change(node_id, self.env.now, False)
                        # Capturer machine OFF avec même logique que ON / Capture machine OFF with same logic as ON
                        if hasattr(self, '_capture_machine_state'):
                            if not operator_req:
                                self._capture_machine_state(node_id, self.env.now, "OFF")
                            elif operator and operator.current_machine_id == node_id:
                                self._capture_machine_state(node_id, self.env.now, "OFF")
                                if self.app_config.DEBUG_MODE:
                                    print(f"[DEBUG_STATE] Machine {node_id} OFF - operator {operator.name} current_machine={operator.current_machine_id}")
                        
                        # Libérer l'opérateur maintenant que le traitement est terminé / Release operator now that processing is finished
                        if operator_req:
                            # Mettre à jour le temps d'occupation / Update busy time
                            if self.operator_busy_start[operator_id] is not None:
                                busy_duration = self.env.now - self.operator_busy_start[operator_id]
                                self.operator_busy_time[operator_id] += busy_duration
                                self.operator_busy_start[operator_id] = None
                            
                            # Capturer la libération de l'opérateur / Capture operator release
                            if hasattr(self, '_capture_operator_state'):
                                target_node = self.flow_model.get_node(node_id)
                                target_name = target_node.name if target_node else node_id
                                self._capture_operator_state(operator_id, self.env.now, tr('op_state_released'), node_id)
                            
                            self.operator_resources[operator_id].release(operator_req)
                            if not self.fast_mode and self.app_config.DEBUG_MODE:
                                print(f"[DEBUG] {node.name} (t={self.env.now:.2f}): Operator {operator.name} released")
                
                except simpy.Interrupt:
                    break
                except Exception as e:
                    if self.app_config.DEBUG_MODE:
                        print(f"Error in node {node_id}: {e}")
                    if self.env:
                        yield self.env.timeout(0.1)
                    else:
                        break
            else:
                if self.env:
                    yield self.env.timeout(0.1)
                else:
                    break
    
    def _collect_items_for_combinations(self, node: FlowNode):
        """
        Collecte les items selon le système de combinaisons / Collect items according to combination system
        Logique événementielle : à chaque arrivée d'item, scanner tous les buffers
        et vérifier si une combinaison peut être satisfaite
        Event-driven logic: on each item arrival, scan all buffers
        and check if a combination can be satisfied
        """
        if self.app_config.DEBUG_MODE:
            print(f"\n{'='*80}")
            print(f"[COMBINATION_DEBUG] {node.name}: Starting collection for combinations")
            print(f"[COMBINATION_DEBUG] Available combinations:")
            for combo in node.combination_set:
                ingredients_list = []
                for ing in combo.ingredients:
                    type_name = self._get_item_type_name(node.node_id, ing.type_id)
                    ingredients_list.append(f"{ing.quantity}x {type_name} (id={ing.type_id})")
                ingredients_str = ", ".join(ingredients_list)
                output_name = self._get_item_type_name(node.node_id, combo.output_type_id)
                print(f"  - '{combo.name}': {ingredients_str} -> {combo.output_quantity}x {output_name} (id={combo.output_type_id})")
            print(f"{'='*80}\n")
        
        # Créer une liste des stores disponibles / Create list of available stores
        stores_info = []
        stores_dict = {}  # {conn_id: store} pour accès rapide / for quick access
        for conn_id in node.input_connections:
            connection_store = self.stores.get(conn_id)
            if connection_store:
                stores_info.append((conn_id, connection_store))
                stores_dict[conn_id] = connection_store
                if self.app_config.DEBUG_MODE:
                    print(f"[COMBINATION_DEBUG] Connection {conn_id}: {len(connection_store.items)} item(s) available")
        
        if not stores_info:
            if self.app_config.DEBUG_MODE:
                print(f"[COMBINATION_DEBUG] {node.name}: No store available")
            return []
        
        # Boucle principale : attendre des items et vérifier les combinaisons / Main loop: wait for items and check combinations
        while True:
            # ÉTAPE 1 : Scanner tous les buffers pour voir ce qui est disponible / STEP 1: Scan all buffers to see what's available
            if self.app_config.DEBUG_MODE:
                print(f"\n[COMBINATION_DEBUG] Buffer scan at t={self.env.now:.2f}s")
            
            available_items_by_conn = {}  # {conn_id: [items]}
            available_items_by_type = {}  # {type_id: count}
            
            for conn_id, store in stores_info:
                items_list = list(store.items)  # Copie de la liste des items disponibles / Copy of available items list
                available_items_by_conn[conn_id] = items_list
                
                if self.app_config.DEBUG_MODE:
                    print(f"[COMBINATION_DEBUG]   conn_{conn_id}: {len(items_list)} item(s)")
                
                # Compter par type / Count by type
                for item in items_list:
                    item_type = item.get('type', item.get('item_type', 'unknown'))
                    available_items_by_type[item_type] = available_items_by_type.get(item_type, 0) + 1
            
            if self.app_config.DEBUG_MODE and available_items_by_type:
                type_summary = []
                for type_id, count in available_items_by_type.items():
                    type_name = self._get_item_type_name(node.node_id, type_id)
                    type_summary.append(f"{count}x {type_name} (id={type_id})")
                print(f"[COMBINATION_DEBUG]   Total: {', '.join(type_summary)}")
            
            # ÉTAPE 2 : Vérifier chaque combinaison dans l'ordre pour voir si elle peut être satisfaite / STEP 2: Check each combination in order to see if it can be satisfied
            matching_combination = None
            
            # Debug désactivé - Vérification des items disponibles par type / Debug disabled - Check available items by type
            if False:
                print(f"\n🔍 [DISPROPORTION_DEBUG] t={self.env.now:.2f}s | Items available by type:")
                for type_id, count in available_items_by_type.items():
                    type_name = self._get_item_type_name(node.node_id, type_id)
                    print(f"   - Type '{type_name}' (id={type_id}): {count} item(s)")
            
            for combination in node.combination_set:
                # Vérifier si cette combinaison peut être satisfaite avec les items disponibles / Check if this combination can be satisfied with available items
                can_satisfy = True
                for ingredient in combination.ingredients:
                    available_count = available_items_by_type.get(ingredient.type_id, 0)
                    if available_count < ingredient.quantity:
                        can_satisfy = False
                        break
                
                if can_satisfy:
                    matching_combination = combination
                    if self.app_config.DEBUG_MODE:
                        print(f"[COMBINATION_DEBUG] ✓ Combination '{combination.name}' can be satisfied!")
                    break
                elif self.app_config.DEBUG_MODE:
                    # Debug : afficher pourquoi la combinaison ne peut pas être satisfaite / Debug: show why combination cannot be satisfied
                    missing = []
                    for ingredient in combination.ingredients:
                        available_count = available_items_by_type.get(ingredient.type_id, 0)
                        if available_count < ingredient.quantity:
                            type_name = self._get_item_type_name(node.node_id, ingredient.type_id)
                            missing.append(f"{type_name}: {available_count}/{ingredient.quantity}")
                    print(f"[COMBINATION_DEBUG] ✗ Combination '{combination.name}' not satisfied - missing: {', '.join(missing)}")
            
            # ÉTAPE 3 : Si une combinaison est satisfaite, récupérer les items et transformer / STEP 3: If combination satisfied, get items and transform
            if matching_combination:
                if self.app_config.DEBUG_MODE:
                    print(f"\n{'='*80}")
                    print(f"[COMBINATION_SUCCESS] {node.name}: Combination '{matching_combination.name}' SATISFIED!")
                    print(f"{'='*80}")
                
                # Récupérer les items nécessaires depuis les stores / Get needed items from stores
                collected_items = []
                items_needed_by_type = {}  # {type_id: quantity_needed}
                
                for ingredient in matching_combination.ingredients:
                    items_needed_by_type[ingredient.type_id] = ingredient.quantity
                
                # Récupérer les items en parcourant les connexions / Get items by scanning connections
                # IMPORTANT : On doit récupérer les items du store et vérifier leur type
                # car store.get() retire le PREMIER item (FIFO), pas un item spécifique
                # IMPORTANT: We must get items from store and check their type
                # because store.get() removes the FIRST item (FIFO), not a specific item
                
                if False:  # Debug désactivé / Debug disabled
                    print(f"\n🎯 [DISPROPORTION_DEBUG] Start retrieval for combination '{matching_combination.name}'")
                    print(f"   Items required: {items_needed_by_type}")
                    print(f"   Connection scan order: {[conn_id for conn_id, _ in stores_info]}")
                
                for conn_id, store in stores_info:
                    # Récupérer tous les items de ce store et filtrer / Get all items from this store and filter
                    items_from_store = []
                    
                    if False:  # Debug désactivé / Debug disabled
                        print(f"   📦 [SCAN] Connection {conn_id}: {len(store.items)} item(s) in buffer")
                    
                    # CORRECTION: Vérifier combien d'items sont disponibles AVANT de les retirer
                    # pour éviter que store.get() bloque indéfiniment
                    # CORRECTION: Check how many items are available BEFORE removing them
                    # to avoid store.get() blocking indefinitely
                    while len(store.items) > 0:
                        # Vérifier AVANT de retirer si on a déjà tous les items nécessaires / Check BEFORE removing if we already have all needed items
                        all_found = all(items_needed_by_type.get(tid, 0) == 0 for tid in items_needed_by_type)
                        if all_found:
                            if False:  # Debug désactivé / Debug disabled
                                print(f"   ⚠️ [BREAK] All items found! Stop scan of {conn_id} BEFORE removal (remaining items: {len(store.items)})")
                            break
                        
                        retrieved_item = yield store.get()
                        item_type = retrieved_item.get('type', retrieved_item.get('item_type', 'unknown'))
                        
                        # Décrémenter IMMÉDIATEMENT si l'item est utile / Decrement IMMEDIATELY if item is useful
                        if item_type in items_needed_by_type and items_needed_by_type[item_type] > 0:
                            items_needed_by_type[item_type] -= 1
                            items_from_store.append(('keep', retrieved_item))
                            if False:  # Debug désactivé / Debug disabled
                                print(f"      ✅ Type {item_type} useful! Remaining to find: {items_needed_by_type[item_type]}")
                        else:
                            items_from_store.append(('return', retrieved_item))
                            if False:  # Debug désactivé / Debug disabled
                                print(f"      ↩️ Type {item_type} not needed, will be returned")
                    
                    # Trier : séparer les items utiles des autres (déjà classifiés) / Sort: separate useful items from others (already classified)
                    items_to_keep = []
                    items_to_return = []
                    
                    if False:  # Debug désactivé / Debug disabled
                        print(f"   📊 [SUMMARY] {conn_id}: {len(items_from_store)} item(s) removed from buffer")
                    
                    for action, item in items_from_store:
                        if action == 'keep':
                            # Item nécessaire pour la combinaison / Item needed for combination
                            items_to_keep.append(item)
                            collected_items.append(item)
                            
                            # Enregistrer la consommation AVEC l'item pour décrémenter le bon type / Record consumption WITH item to decrement correct type
                            self._record_probe_consumption(conn_id, 1, [item])
                            
                            if self.app_config.DEBUG_MODE:
                                item_type = item.get('type', item.get('item_type', 'unknown'))
                                item_type_name = self._get_item_type_name(node.node_id, item_type)
                                print(f"[COMBINATION_DEBUG] Item retrieved: {item_type_name} (id={item_type}) from {conn_id}")
                        else:
                            # Item non nécessaire, le remettre dans le store / Item not needed, put it back in store
                            items_to_return.append(item)
                    
                    # Remettre les items non utilisés dans le store (dans l'ordre pour préserver FIFO) / Put unused items back in store (in order to preserve FIFO)
                    for item in items_to_return:
                        yield store.put(item)
                        if self.app_config.DEBUG_MODE:
                            item_type = item.get('type', item.get('item_type', 'unknown'))
                            item_type_name = self._get_item_type_name(node.node_id, item_type)
                            print(f"[COMBINATION_DEBUG] Item put back in buffer: {item_type_name} (id={item_type}) in {conn_id}")
                
                # Transformer les items selon la combinaison / Transform items according to combination
                output_items = []
                for _ in range(matching_combination.output_quantity):
                    output_item = collected_items[0].copy()  # Copier les attributs de base / Copy base attributes
                    output_item['item_type'] = matching_combination.output_type_id
                    output_item['type'] = matching_combination.output_type_id
                    output_items.append(output_item)
                
                if self.app_config.DEBUG_MODE:
                    output_name = self._get_item_type_name(node.node_id, matching_combination.output_type_id)
                    print(f"[COMBINATION_SUCCESS] Output: {len(output_items)}x {output_name} (id={matching_combination.output_type_id})")
                    print(f"{'='*80}\n")
                
                return output_items
            
            # ÉTAPE 4 : Aucune combinaison satisfaite, attendre avant de rescanner / STEP 4: No combination satisfied, wait before rescanning
            if self.app_config.DEBUG_MODE:
                print(f"[COMBINATION_DEBUG] No combination satisfied, waiting before rescan...")
            
            # Attendre un court instant pour permettre aux nouveaux items d'arriver / Wait briefly to allow new items to arrive
            # Sans utiliser get() qui retirerait les items des buffers / Without using get() which would remove items from buffers
            yield self.env.timeout(0.1)
            
            # Reboucler pour rescanner les buffers avec les nouveaux items / Loop back to rescan buffers with new items
    
    def _wait_for_items(self, node: FlowNode):
        """Attend les items selon le mode de synchronisation / Wait for items according to synchronization mode"""
        if not node.input_connections or not self.env:
            return []
        
        if node.sync_mode == SyncMode.FIRST_AVAILABLE:
            # Attendre un item de N'IMPORTE quelle connexion (bloque jusqu'à disponibilité) / Wait for item from ANY connection (blocks until available)
            # Créer une liste de requêtes get() pour chaque store / Create list of get() requests for each store
            stores_list = []
            conn_ids_list = []
            for conn_id in node.input_connections:
                connection_store = self.stores.get(conn_id)
                if connection_store:
                    stores_list.append(connection_store)
                    conn_ids_list.append(conn_id)
            
            if not stores_list:
                return []
            
            # CAS SPÉCIAL: Round-robin strict - attendre la connexion spécifique selon l'ordre / SPECIAL CASE: Strict round-robin - wait for specific connection according to order
            if node.first_available_priority == FirstAvailablePriority.ROUND_ROBIN:
                # Attendre spécifiquement la connexion attendue selon round-robin / Wait specifically for expected connection according to round-robin
                target_idx = node.round_robin_index
                target_store = stores_list[target_idx]
                target_conn_id = conn_ids_list[target_idx]
                
                # Attendre un item de cette connexion spécifique / Wait for item from this specific connection
                item = yield target_store.get()
                
                # Mettre à jour l'index pour le prochain tour / Update index for next turn
                node.round_robin_index = (target_idx + 1) % len(stores_list)
                
                if not self.fast_mode:
                    print(f"[DEBUG] Node {node.name}: Item received from {target_conn_id} (mode: {node.first_available_priority.value})")
                
                # Enregistrer la consommation dans les pipettes (décrémente buffer) / Record consumption in probes (decrements buffer)
                # Passer l'item consommé pour connaître son type / Pass consumed item to know its type
                self._record_probe_consumption(target_conn_id, 1, [item])
                
                return [item]
            
            # CAS GÉNÉRAL: Order, Random, ou autre - utiliser AnyOf / GENERAL CASE: Order, Random, or other - use AnyOf
            # Créer les événements get() / Create get() events
            get_events = [store.get() for store in stores_list]
            result = yield simpy.events.AnyOf(self.env, get_events)
            
            # Récupérer tous les items qui ont été retirés / Get all items that were removed
            retrieved_items = []
            retrieved_indices = []
            for i, event in enumerate(get_events):
                if event in result:
                    retrieved_items.append(event.value)
                    retrieved_indices.append(i)
            
            # Prendre SEULEMENT un item selon la priorité, remettre les autres / Take ONLY one item according to priority, put back the others
            if retrieved_items:
                # Déterminer quel item garder selon le mode de priorité / Determine which item to keep according to priority mode
                selected_idx = None
                
                if node.first_available_priority == FirstAvailablePriority.ORDER:
                    # Prendre la connexion avec le plus petit index dans la liste originale / Take connection with smallest index in original list
                    selected_idx = min(retrieved_indices)
                    selected_position = retrieved_indices.index(selected_idx)
                    
                elif node.first_available_priority == FirstAvailablePriority.RANDOM:
                    # Choisir aléatoirement parmi les items disponibles / Choose randomly among available items
                    selected_position = random.randint(0, len(retrieved_items) - 1)
                    selected_idx = retrieved_indices[selected_position]
                
                else:
                    # Par défaut, prendre le premier / By default, take the first
                    selected_position = 0
                    selected_idx = retrieved_indices[0]
                
                # Garder l'item sélectionné / Keep selected item
                item = retrieved_items[selected_position]
                conn_id = conn_ids_list[selected_idx]
                
                # Remettre TOUS les autres items dans leurs stores respectifs EN ARRIÈRE-PLAN
                # CRITIQUE: Ne pas bloquer ici car les buffers peuvent être pleins
                # Put back ALL other items in their respective stores IN BACKGROUND
                # CRITICAL: Don't block here because buffers may be full
                for j, idx in enumerate(retrieved_indices):
                    if j != selected_position:
                        other_conn_id = conn_ids_list[idx]
                        if not self.fast_mode:
                            print(f"[DEBUG] Starting item return to {other_conn_id} (current buffer: {len(stores_list[idx].items)})")
                        # Lancer la remise en arrière-plan pour ne pas bloquer le cycle de traitement / Start return in background to not block processing cycle
                        self.env.process(self._put_item_back(stores_list[idx], retrieved_items[j], other_conn_id))
                
                # Enregistrer la consommation dans les pipettes (décrémente buffer) AVEC l'item / Record consumption in probes (decrements buffer) WITH item
                self._record_probe_consumption(conn_id, 1, [item])
                
                return [item]
            
            return []
        
        elif node.sync_mode == SyncMode.WAIT_N_FROM_BRANCH:
            # Mode combinaisons : attendre les ingrédients selon les combinaisons définies / Combinations mode: wait for ingredients according to defined combinations
            
            # Si le nœud a le mode combinaisons activé, utiliser le système de combinaisons / If node has combinations mode enabled, use combinations system
            if getattr(node, 'use_combinations', False):
                # Collecter les items nécessaires selon les combinaisons / Collect needed items according to combinations
                return (yield from self._collect_items_for_combinations(node))
            else:
                # Mode legacy : attendre N items de CHAQUE branche / Legacy mode: wait for N items from EACH branch
                # Vérifier que required_units est défini pour toutes les connexions / Verify required_units is defined for all connections
                if not node.required_units:
                    # Si aucune configuration, attendre 1 item de chaque branche / If no configuration, wait for 1 item from each branch
                    node.required_units = {conn_id: 1 for conn_id in node.input_connections}
                
                # Collecter exactement le nombre requis d'items de CHAQUE branche / Collect exactly required number of items from EACH branch
                # IMPORTANT: Utiliser AllOf pour attendre que TOUS les items soient disponibles / IMPORTANT: Use AllOf to wait for ALL items to be available
                # AVANT de les consommer (évite de consommer partiellement) / BEFORE consuming them (avoids partial consumption)
                
                all_get_events = []
                connection_info = []  # (conn_id, item_index, total_required)
                
                for conn_id in node.input_connections:
                    connection_store = self.stores.get(conn_id)
                    if not connection_store:
                        continue
                    
                    required_count = node.required_units.get(conn_id, 1)
                    
                    # Créer required_count événements get() pour cette branche / Create required_count get() events for this branch
                    for i in range(required_count):
                        get_event = connection_store.get()
                        all_get_events.append(get_event)
                        connection_info.append((conn_id, i, required_count))
                
                # Attendre que TOUS les événements soient prêts avec AllOf / Wait for ALL events to be ready with AllOf
                result = yield simpy.events.AllOf(self.env, all_get_events)
                
                # Récupérer tous les items et mettre à jour les compteurs / Get all items and update counters
                items = []
                items_by_conn = {}
                
                for idx, (conn_id, item_idx, total_required) in enumerate(connection_info):
                    item = all_get_events[idx].value
                    items.append(item)
                    
                    if conn_id not in items_by_conn:
                        items_by_conn[conn_id] = []
                    items_by_conn[conn_id].append(item)
                
                # Mettre à jour les compteurs de buffer et les pipettes / Update buffer counters and probes
                for conn_id in items_by_conn.keys():
                    # Enregistrer la consommation dans les pipettes (décrémente buffer) / Record consumption in probes (decrements buffer)
                    # Passer les items consommés pour la décrémentation des types / Pass consumed items for type decrement
                    consumed_items = items_by_conn[conn_id]
                    self._record_probe_consumption(conn_id, len(consumed_items), consumed_items)
                
                return items
        
        return []
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques de simulation / Return simulation statistics"""
        return self.stats
