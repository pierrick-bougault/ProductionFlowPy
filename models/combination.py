"""
Système de combinaisons pour les nœuds de traitement
Permet de définir des combinaisons d'items en entrée qui produisent un type d'item spécifique en sortie

Combination system for processing nodes
Defines input item combinations that produce a specific item type as output
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class CombinationIngredient:
    """Ingrédient d'une combinaison : type d'item + quantité requise / Combination ingredient: item type + required quantity"""
    type_id: str  # ID du type d'item / Item type ID (ex: "carotte_orange")
    quantity: int  # Quantité requise / Required quantity (ex: 1)
    
    def to_dict(self) -> dict:
        return {
            'type_id': self.type_id,
            'quantity': self.quantity
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'CombinationIngredient':
        return CombinationIngredient(
            type_id=data['type_id'],
            quantity=data['quantity']
        )


@dataclass
class Combination:
    """
    Une combinaison définit un assemblage d'ingrédients qui produit un output spécifique
    A combination defines an assembly of ingredients that produces a specific output
    
    Exemple / Example:
        ingrédients = [
            CombinationIngredient("carotte_orange", 1),
            CombinationIngredient("oignon_rouge", 2)
        ]
        output_type_id = "tapenade_orange"
        output_quantity = 1
    """
    combination_id: str  # Identifiant unique / Unique identifier
    name: str  # Nom de la combinaison / Combination name (ex: "Tapenade Orange")
    ingredients: List[CombinationIngredient] = field(default_factory=list)
    output_type_id: str = ""  # Type d'item produit en sortie / Output item type
    output_quantity: int = 1  # Quantité produite / Quantity produced
    
    def get_total_items_required(self) -> int:
        """Retourne le nombre total d'items requis pour cette combinaison / Returns total items required for this combination"""
        return sum(ing.quantity for ing in self.ingredients)
    
    def matches(self, items: List[dict]) -> bool:
        """
        Vérifie si une liste d'items correspond à cette combinaison
        Check if an item list matches this combination
        
        Args:
            items: Liste d'items avec leur 'type' ou 'item_type' / Item list with 'type' or 'item_type'
        
        Returns:
            True si les items correspondent exactement aux ingrédients requis
            True if items exactly match required ingredients
        """
        # Compter les types d'items disponibles / Count available item types
        item_counts = {}
        for item in items:
            # Supporter les deux formats: 'type' et 'item_type' / Support both formats
            item_type = item.get('type', item.get('item_type', ''))
            item_counts[item_type] = item_counts.get(item_type, 0) + 1
        
        # Vérifier que chaque ingrédient est satisfait / Check each ingredient is satisfied
        for ingredient in self.ingredients:
            if item_counts.get(ingredient.type_id, 0) < ingredient.quantity:
                return False
        
        # Vérifier qu'il n'y a pas d'items en surplus / Check there are no surplus items
        total_required = self.get_total_items_required()
        if len(items) != total_required:
            return False
        
        return True
    
    def to_dict(self) -> dict:
        return {
            'combination_id': self.combination_id,
            'name': self.name,
            'ingredients': [ing.to_dict() for ing in self.ingredients],
            'output_type_id': self.output_type_id,
            'output_quantity': self.output_quantity
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Combination':
        return Combination(
            combination_id=data.get('combination_id', data.get('recipe_id', '')),  # Backward compat
            name=data['name'],
            ingredients=[CombinationIngredient.from_dict(ing) for ing in data.get('ingredients', [])],
            output_type_id=data.get('output_type_id', ''),
            output_quantity=data.get('output_quantity', 1)
        )


class CombinationSet:
    """
    Ensemble de combinaisons pour un nœud
    Contient toutes les combinaisons possibles et gère la correspondance avec les items
    
    Combination set for a node
    Contains all possible combinations and manages item matching
    """
    
    def __init__(self):
        self.combinations: List[Combination] = []
    
    def add_combination(self, combination: Combination):
        """Ajoute une combinaison à l'ensemble / Add combination to set"""
        self.combinations.append(combination)
    
    def remove_combination(self, combination_id: str):
        """Retire une combinaison de l'ensemble / Remove combination from set"""
        self.combinations = [c for c in self.combinations if c.combination_id != combination_id]
    
    def get_combination(self, combination_id: str) -> Optional[Combination]:
        """Récupère une combinaison par son ID / Get combination by ID"""
        for combination in self.combinations:
            if combination.combination_id == combination_id:
                return combination
        return None
    
    def find_matching_combination(self, items: List[dict]) -> Optional[Combination]:
        """
        Trouve la combinaison qui correspond aux items fournis
        Lève une exception si plusieurs combinaisons correspondent (conflit)
        
        Find matching combination for provided items
        Raises exception if multiple combinations match (conflict)
        
        Args:
            items: Liste d'items à matcher / Items to match
        
        Returns:
            La combinaison correspondante ou None / Matching combination or None
        
        Raises:
            RuntimeError: Si plusieurs combinaisons correspondent aux items (conflit)
                          If multiple combinations match items (conflict)
        """
        matching_combinations = []
        
        for combination in self.combinations:
            if combination.matches(items):
                matching_combinations.append(combination)
        
        if len(matching_combinations) > 1:
            names = ', '.join([f"'{c.name}'" for c in matching_combinations])
            raise RuntimeError(
                f"ERREUR: Conflit détecté - Plusieurs combinaisons correspondent aux items collectés: {names}. "
                f"Veuillez modifier vos combinaisons pour qu'elles soient mutuellement exclusives."
            )
        
        return matching_combinations[0] if matching_combinations else None
    
    def to_dict(self) -> dict:
        return {
            'combinations': [combination.to_dict() for combination in self.combinations]
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'CombinationSet':
        combination_set = CombinationSet()
        # Support ancien format 'recipes' pour backward compatibility
        # Support old 'recipes' format for backward compatibility
        items = data.get('combinations', data.get('recipes', []))
        for combination_data in items:
            combination_set.add_combination(Combination.from_dict(combination_data))
        return combination_set
    
    def __len__(self):
        return len(self.combinations)
    
    def __iter__(self):
        return iter(self.combinations)
