"""Annotations pour le canvas - rectangles avec texte pour indiquer des légendes
Annotations for canvas - rectangles with text to indicate legends"""

class Annotation:
    """Représente une annotation visuelle (rectangle en pointillés avec texte)
    Represents a visual annotation (dashed rectangle with text)"""
    
    def __init__(self, annotation_id: str, x: float, y: float, width: float, height: float, text: str = ""):
        self.annotation_id = annotation_id
        self.x = x  # Coordonnée X du coin supérieur gauche / Top-left X coordinate
        self.y = y  # Coordonnée Y du coin supérieur gauche / Top-left Y coordinate
        self.width = width
        self.height = height
        self.text = text
        self.color = "#888888"  # Couleur par défaut (gris) / Default color (gray)
        self.dash_pattern = (5, 3)  # Motif de pointillés / Dash pattern
        self.text_size = 12
        self.text_color = "#333333"
    
    def to_dict(self):
        """Convertit l'annotation en dictionnaire pour sauvegarde / Convert annotation to dictionary for saving"""
        return {
            'annotation_id': self.annotation_id,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'text': self.text,
            'color': self.color,
            'dash_pattern': self.dash_pattern,
            'text_size': self.text_size,
            'text_color': self.text_color
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Annotation':
        """Crée une annotation depuis un dictionnaire / Create annotation from dictionary"""
        annotation = Annotation(
            data['annotation_id'],
            data['x'],
            data['y'],
            data['width'],
            data['height'],
            data.get('text', '')
        )
        annotation.color = data.get('color', '#888888')
        annotation.dash_pattern = tuple(data.get('dash_pattern', (5, 3)))
        annotation.text_size = data.get('text_size', 12)
        annotation.text_color = data.get('text_color', '#333333')
        return annotation
