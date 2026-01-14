"""Modèle pour les opérateurs qui contrôlent les machines / Model for operators controlling machines"""
from typing import Dict, List, Tuple
from enum import Enum
from collections import deque

class DistributionType(Enum):
    """Types de distributions pour les temps de déplacement / Distribution types for travel times"""
    CONSTANT = "Constant"
    NORMAL = "Normal"
    SKEW_NORMAL = "Skew Normal"

class Operator:
    """Représente un opérateur qui contrôle plusieurs machines / Represents an operator controlling multiple machines"""
    
    def __init__(self, operator_id: str, name: str = ""):
        self.operator_id = operator_id
        self.name = name or f"Opérateur {operator_id}"
        self.color = "#FF9800"  # Orange par défaut / Default orange
        self.x = 100  # Position X sur le canvas / X position on canvas
        self.y = 100  # Position Y sur le canvas / Y position on canvas
        
        # Machines assignées (liste de node_ids) / Assigned machines (list of node_ids)
        self.assigned_machines: List[str] = []
        
        # Temps de déplacement entre machines / Travel times between machines
        # Format: {(machine_id_from, machine_id_to): {'type': DistributionType, 'params': {...}}}
        self.travel_times: Dict[Tuple[str, str], Dict] = {}
        
        # Loupes de mesure de temps pour les trajets / Time measurement probes for routes
        # Format: {(machine_id_from, machine_id_to): {'enabled': bool, 'measurements': []}}
        self.travel_probes: Dict[Tuple[str, str], Dict] = {}
        
        # État actuel de simulation / Current simulation state
        self.current_machine_id = None  # Machine où se trouve l'opérateur / Machine where operator is
        self.is_available = True
    
    def add_machine(self, machine_id: str):
        """Ajoute une machine à la liste des machines assignées / Add machine to assigned machines list"""
        if machine_id not in self.assigned_machines:
            self.assigned_machines.append(machine_id)
    
    def remove_machine(self, machine_id: str):
        """Retire une machine de la liste / Remove machine from list"""
        if machine_id in self.assigned_machines:
            self.assigned_machines.remove(machine_id)
            
            # Nettoyer les temps de trajet associés / Clean associated travel times
            keys_to_remove = []
            for key in self.travel_times.keys():
                if machine_id in key:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self.travel_times[key]
    
    def set_travel_time(self, from_machine: str, to_machine: str, 
                       distribution_type: DistributionType, params: Dict):
        """Configure le temps de déplacement entre deux machines / Configure travel time between two machines
        
        Args:
            from_machine: ID de la machine source / Source machine ID
            to_machine: ID de la machine destination / Destination machine ID
            distribution_type: Type de distribution (CONSTANT, NORMAL, SKEW_NORMAL)
            params: Paramètres de la distribution / Distribution parameters
                - CONSTANT: {'value': float}
                - NORMAL: {'mean': float, 'std_dev': float}
                - SKEW_NORMAL: {'location': float, 'scale': float, 'shape': float}
        """
        self.travel_times[(from_machine, to_machine)] = {
            'type': distribution_type,
            'params': params
        }
    
    def get_travel_time(self, from_machine: str, to_machine: str):
        """Récupère les paramètres de temps de déplacement entre deux machines / Get travel time parameters between two machines"""
        return self.travel_times.get((from_machine, to_machine))
    
    def to_dict(self):
        """Convertit l'opérateur en dictionnaire pour sauvegarde / Convert operator to dictionary for saving"""
        return {
            'operator_id': self.operator_id,
            'name': self.name,
            'color': self.color,
            'x': self.x,
            'y': self.y,
            'assigned_machines': self.assigned_machines,
            'travel_times': {
                f"{k[0]}_to_{k[1]}": {
                    'type': v['type'].value,
                    'params': v['params']
                }
                for k, v in self.travel_times.items()
            },
            'travel_probes': {
                f"{k[0]}_to_{k[1]}": {
                    'enabled': v.get('enabled', False)
                }
                for k, v in self.travel_probes.items()
            }
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Operator':
        """Crée un opérateur depuis un dictionnaire / Create operator from dictionary"""
        operator = Operator(
            data['operator_id'],
            data.get('name', '')
        )
        operator.color = data.get('color', '#FF9800')
        operator.x = data.get('x', 100)
        operator.y = data.get('y', 100)
        operator.assigned_machines = data.get('assigned_machines', [])
        
        # Reconstruire travel_times / Rebuild travel_times
        travel_times_dict = data.get('travel_times', {})
        for key, value in travel_times_dict.items():
            # Parser la clé "machine1_to_machine2" / Parse key
            parts = key.split('_to_')
            if len(parts) == 2:
                from_machine, to_machine = parts
                dist_type = DistributionType(value['type'])
                operator.travel_times[(from_machine, to_machine)] = {
                    'type': dist_type,
                    'params': value['params']
                }
        
        # Reconstruire travel_probes / Rebuild travel_probes
        travel_probes_dict = data.get('travel_probes', {})
        for key, value in travel_probes_dict.items():
            parts = key.split('_to_')
            if len(parts) == 2:
                from_machine, to_machine = parts
                # Utiliser liste sans limite pour garder toutes les mesures
                # Use unlimited list to keep all measurements
                operator.travel_probes[(from_machine, to_machine)] = {
                    'enabled': value.get('enabled', False),
                    'measurements': []
                }
        
        return operator
