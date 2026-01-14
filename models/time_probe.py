"""Loupes de mesure pour collecter les temps / Time probes for collecting times (processing, inter-arrivals, etc.)"""
from typing import List, Dict
from collections import deque
from enum import Enum

class TimeProbeType(Enum):
    """Type de mesure de temps / Time measurement type"""
    PROCESSING = "Temps de traitement"  # Processing time
    INTER_EVENTS = "Temps inter-événements"  # Inter-event time (inter-arrivals for sources, inter-departures for other nodes)

class TimeProbe:
    """Représente une loupe de mesure de temps sur un nœud / Represents a time measurement probe on a node"""
    
    def __init__(self, probe_id: str, name: str, node_id: str, probe_type: TimeProbeType = TimeProbeType.PROCESSING):
        self.probe_id = probe_id
        self.name = name
        self.node_id = node_id
        self.probe_type = probe_type
        self.measure_mode = "buffer"  # "buffer" ou "cumulative" / "buffer" or "cumulative"
        
        # Historique des temps mesurés (sans limite)
        # History of measured times (no limit)
        self.time_measurements: List[float] = []
        
        # Propriétés visuelles / Visual properties
        self.x = 0.0  # Position X de l'icône / Icon X position
        self.y = 0.0  # Position Y de l'icône / Icon Y position
        self.color = "#FF6B6B"  # Couleur du graphique / Graph color (red default)
        self.visible = True  # Afficher le graphique / Show graph
        
        # Statistiques / Statistics
        self.count = 0
        self.sum_time = 0.0
        self.min_time = float('inf')
        self.max_time = 0.0
        self.mean_time = 0.0
    
    def add_measurement(self, time_value: float):
        """Ajoute une mesure de temps / Adds a time measurement"""
        if time_value < 0:
            return  # Ignorer les valeurs négatives / Ignore negative values
        
        self.time_measurements.append(time_value)
        self.count += 1
        self.sum_time += time_value
        self.min_time = min(self.min_time, time_value)
        self.max_time = max(self.max_time, time_value)
        self.mean_time = self.sum_time / self.count
    
    def get_measurements(self) -> List[float]:
        """Retourne la liste des mesures / Returns the list of measurements"""
        return list(self.time_measurements)
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques calculées / Returns calculated statistics"""
        if self.count == 0:
            return {
                'count': 0,
                'mean': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
        
        # Calculer l'écart-type / Calculate standard deviation
        measurements = list(self.time_measurements)
        variance = sum((x - self.mean_time) ** 2 for x in measurements) / len(measurements)
        std_dev = variance ** 0.5
        
        return {
            'count': self.count,
            'mean': self.mean_time,
            'min': self.min_time,
            'max': self.max_time,
            'std_dev': std_dev
        }
    
    def clear_data(self):
        """Efface les données collectées / Clears collected data"""
        self.time_measurements.clear()
        self.count = 0
        self.sum_time = 0.0
        self.min_time = float('inf')
        self.max_time = 0.0
        self.mean_time = 0.0
