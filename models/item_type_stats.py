"""Statistiques et mesures par type d'item / Statistics and measurements by item type"""
from typing import Dict, List, Tuple
from collections import defaultdict

class ItemTypeStats:
    """Classe pour suivre les statistiques par type d'item / Class to track statistics by item type"""
    
    def __init__(self):
        # Répartition globale du tirage (type_id -> count)
        # Global draw distribution (type_id -> count)
        self.generation_counts: Dict[str, int] = defaultdict(int)
        
        # Timeline: (timestamp, type_id) pour chaque génération
        # Timeline: (timestamp, type_id) for each generation
        self.generation_timeline: List[Tuple[float, str]] = []
        
        # Items par nœud: node_id -> type_id -> count
        # Items per node: node_id -> type_id -> count
        self.items_by_node: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Items arrivés sur nœud: node_id -> [(timestamp, type_id)]
        # Items arrived on node: node_id -> [(timestamp, type_id)]
        self.arrivals_by_node: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        
        # Items sortis de nœud: node_id -> [(timestamp, type_id)]
        # Items departed from node: node_id -> [(timestamp, type_id)]
        self.departures_by_node: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
    
    def record_generation(self, timestamp: float, type_id: str):
        """Enregistre la génération d'un item d'un certain type / Record generation of an item of a certain type"""
        self.generation_counts[type_id] += 1
        self.generation_timeline.append((timestamp, type_id))
    
    def record_arrival(self, timestamp: float, node_id: str, type_id: str):
        """Enregistre l'arrivée d'un item sur un nœud / Record item arrival on a node"""
        self.items_by_node[node_id][type_id] += 1
        self.arrivals_by_node[node_id].append((timestamp, type_id))
    
    def record_departure(self, timestamp: float, node_id: str, type_id: str):
        """Enregistre le départ d'un item d'un nœud / Record item departure from a node"""
        self.departures_by_node[node_id].append((timestamp, type_id))
    
    def get_generation_distribution(self) -> Dict[str, int]:
        """Retourne la répartition des types générés / Returns distribution of generated types"""
        return dict(self.generation_counts)
    
    def get_generation_timeline(self) -> List[Tuple[float, str]]:
        """Retourne la timeline complète des générations / Returns complete generation timeline"""
        return self.generation_timeline.copy()
    
    def get_node_distribution(self, node_id: str) -> Dict[str, int]:
        """Retourne la répartition des types pour un nœud / Returns type distribution for a node"""
        return dict(self.items_by_node.get(node_id, {}))
    
    def get_node_arrivals(self, node_id: str) -> List[Tuple[float, str]]:
        """Retourne la timeline des arrivées pour un nœud / Returns arrival timeline for a node"""
        return self.arrivals_by_node.get(node_id, []).copy()
    
    def get_node_departures(self, node_id: str) -> List[Tuple[float, str]]:
        """Retourne la timeline des départs pour un nœud / Returns departure timeline for a node"""
        return self.departures_by_node.get(node_id, []).copy()
    
    def reset(self):
        """Réinitialise toutes les statistiques / Reset all statistics"""
        self.generation_counts.clear()
        self.generation_timeline.clear()
        self.items_by_node.clear()
        self.arrivals_by_node.clear()
        self.departures_by_node.clear()
    
    def export_to_dict(self) -> dict:
        """Exporte toutes les données en dictionnaire / Export all data to dictionary"""
        return {
            'generation_counts': dict(self.generation_counts),
            'generation_timeline': self.generation_timeline,
            'items_by_node': {node_id: dict(counts) for node_id, counts in self.items_by_node.items()},
            'arrivals_by_node': {node_id: arrivals for node_id, arrivals in self.arrivals_by_node.items()},
            'departures_by_node': {node_id: departures for node_id, departures in self.departures_by_node.items()}
        }
