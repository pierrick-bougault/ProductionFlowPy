"""Gestion des types d'items multiples / Multi-item type management"""
from enum import Enum
from typing import Dict, List, Optional
import random
import numpy as np

class ItemGenerationMode(Enum):
    """Modes de génération d'items multiples / Multiple item generation modes"""
    SINGLE_TYPE = "Type unique"
    SEQUENCE = "Séquence définie"
    RANDOM_FINITE = "Aléatoire fini (hypergéométrique)"
    RANDOM_INFINITE = "Aléatoire infini (catégoriel)"

class ItemType:
    """Définit un type d'item avec ses caractéristiques / Defines an item type with its characteristics"""
    
    def __init__(self, type_id: str, name: str, color: str = "#4CAF50"):
        self.type_id = type_id  # ID unique du type / Unique type ID
        self.name = name  # Nom affiché (ex: "Carotte", "Oignon") / Display name
        self.color = color  # Couleur pour visualisation / Color for visualization
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sauvegarde / Convert to dictionary for saving"""
        return {
            'type_id': self.type_id,
            'name': self.name,
            'color': self.color
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ItemType':
        """Crée depuis un dictionnaire / Create from dictionary"""
        return ItemType(
            data['type_id'],
            data['name'],
            data.get('color', '#4CAF50')
        )

class ItemTypeConfig:
    """Configuration des types d'items pour une source / Item types configuration for a source"""
    
    def __init__(self):
        self.generation_mode = ItemGenerationMode.SINGLE_TYPE
        self.item_types: List[ItemType] = []
        
        # Générateur aléatoire INDEPENDANT pour cette source (crucial pour éviter interférences)
        # INDEPENDENT random generator for this source (crucial to avoid interference)
        self._rng = random.Random()
        
        # Mode SINGLE_TYPE
        self.single_type_id: Optional[str] = None  # Type d'item à utiliser en mode unique / Item type to use in single mode
        
        # Mode SEQUENCE
        self.sequence: List[str] = []  # Liste de type_ids dans l'ordre / List of type_ids in order
        self.sequence_loop = True  # Boucler à l'infini ou s'arrêter / Loop infinitely or stop
        self.sequence_index = 0  # Index actuel dans la séquence / Current index in sequence
        
        # Mode RANDOM_FINITE (hypergéométrique / hypergeometric)
        self.finite_counts: Dict[str, int] = {}  # type_id -> quantité initiale / initial quantity
        self.finite_remaining: Dict[str, int] = {}  # type_id -> quantité restante / remaining quantity
        
        # Mode RANDOM_INFINITE (catégoriel / categorical)
        self.proportions: Dict[str, float] = {}  # type_id -> proportion (doit sommer à 1.0) / must sum to 1.0
    
    def get_next_item_type(self) -> Optional[str]:
        """Retourne le prochain type_id à générer selon le mode / Returns next type_id to generate according to mode"""
        if self.generation_mode == ItemGenerationMode.SINGLE_TYPE:
            # Utiliser single_type_id si défini, sinon le premier type
            # Use single_type_id if defined, otherwise first type
            if self.single_type_id:
                return self.single_type_id
            return self.item_types[0].type_id if self.item_types else None
        
        elif self.generation_mode == ItemGenerationMode.SEQUENCE:
            if not self.sequence:
                return None
            
            if self.sequence_index >= len(self.sequence):
                if self.sequence_loop:
                    self.sequence_index = 0
                else:
                    return None  # Séquence terminée / Sequence ended
            
            type_id = self.sequence[self.sequence_index]
            self.sequence_index += 1
            return type_id
        
        elif self.generation_mode == ItemGenerationMode.RANDOM_FINITE:
            # Loi hypergéométrique multivariée / Multivariate hypergeometric law
            remaining_types = [tid for tid, count in self.finite_remaining.items() if count > 0]
            if not remaining_types:
                return None  # Plus d'items disponibles / No more items available
            
            # Calculer probabilités selon quantités restantes
            # Calculate probabilities based on remaining quantities
            total_remaining = sum(self.finite_remaining.values())
            probabilities = [self.finite_remaining[tid] / total_remaining for tid in remaining_types]
            
            # Tirer aléatoirement avec le générateur indépendant
            # Draw randomly with independent generator
            chosen_type = self._rng.choices(remaining_types, weights=probabilities, k=1)[0]
            self.finite_remaining[chosen_type] -= 1
            
            return chosen_type
        
        elif self.generation_mode == ItemGenerationMode.RANDOM_INFINITE:
            # Loi catégorielle / Categorical distribution
            if not self.proportions:
                return None
            
            types = list(self.proportions.keys())
            probs = list(self.proportions.values())
            
            # Normaliser au cas où / Normalize just in case
            total = sum(probs)
            if total > 0:
                probs = [p / total for p in probs]
            
            # Debug désactivé pour réduire verbosité
            if False:
                print(f"🎲 [RANDOM_DEBUG] Avant self._rng.choices:")
                print(f"   - types disponibles: {types}")
                print(f"   - probabilités normalisées: {probs}")
                print(f"   - self._rng ID: {id(self._rng)}")
            
            chosen_type = self._rng.choices(types, weights=probs, k=1)[0]
            
            if False:
                print(f"   - Type tiré: {chosen_type}")
            
            return chosen_type
        
        return None
    
    def reset(self):
        """Réinitialise les compteurs pour une nouvelle simulation / Reset counters for new simulation"""
        self.sequence_index = 0
        if self.generation_mode == ItemGenerationMode.RANDOM_FINITE:
            self.finite_remaining = self.finite_counts.copy()
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sauvegarde / Convert to dictionary for saving"""
        return {
            'generation_mode': self.generation_mode.value,
            'item_types': [it.to_dict() for it in self.item_types],
            'single_type_id': self.single_type_id,
            'sequence': self.sequence,
            'sequence_loop': self.sequence_loop,
            'finite_counts': self.finite_counts,
            'proportions': self.proportions
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ItemTypeConfig':
        """Crée depuis un dictionnaire / Create from dictionary"""
        config = ItemTypeConfig()
        config.generation_mode = ItemGenerationMode(data.get('generation_mode', ItemGenerationMode.SINGLE_TYPE.value))
        config.item_types = [ItemType.from_dict(it) for it in data.get('item_types', [])]
        config.single_type_id = data.get('single_type_id')
        config.sequence = data.get('sequence', [])
        config.sequence_loop = data.get('sequence_loop', True)
        config.finite_counts = data.get('finite_counts', {})
        config.proportions = data.get('proportions', {})
        return config

class ProcessingConfig:
    """Configuration du traitement par type d'item / Processing configuration by item type"""
    
    def __init__(self):
        # Temps de traitement par type_id (en centisecondes)
        # Processing time by type_id (in centiseconds)
        self.processing_times_cs: Dict[str, float] = {}
        
        # Modes de traitement par type_id / Processing modes by type_id
        self.processing_modes: Dict[str, str] = {}  # type_id -> "CONSTANT", "NORMAL", "SKEW_NORMAL"
        
        # Paramètres pour lois normales par type_id / Parameters for normal distributions by type_id
        self.std_devs_cs: Dict[str, float] = {}
        self.skewnesses: Dict[str, float] = {}
        
        # Transformation de type : type_id_input -> type_id_output
        # Type transformation: type_id_input -> type_id_output
        # Si None ou absent, garde le même type / If None or absent, keeps same type
        self.output_type_mapping: Dict[str, Optional[str]] = {}
    
    def get_processing_time_cs(self, input_type_id: str) -> float:
        """Retourne le temps de traitement pour un type d'item / Returns processing time for an item type"""
        return self.processing_times_cs.get(input_type_id, 100.0)
    
    def get_output_type(self, input_type_id: str) -> str:
        """Retourne le type de sortie pour un type d'entrée / Returns output type for an input type"""
        return self.output_type_mapping.get(input_type_id, input_type_id)
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sauvegarde / Convert to dictionary for saving"""
        return {
            'processing_times_cs': self.processing_times_cs,
            'processing_modes': self.processing_modes,
            'std_devs_cs': self.std_devs_cs,
            'skewnesses': self.skewnesses,
            'output_type_mapping': self.output_type_mapping
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ProcessingConfig':
        """Crée depuis un dictionnaire / Create from dictionary"""
        config = ProcessingConfig()
        config.processing_times_cs = data.get('processing_times_cs', {})
        config.processing_modes = data.get('processing_modes', {})
        config.std_devs_cs = data.get('std_devs_cs', {})
        config.skewnesses = data.get('skewnesses', {})
        config.output_type_mapping = data.get('output_type_mapping', {})
        return config
