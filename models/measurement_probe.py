"""Pipettes de mesure pour collecter des données de flux / Measurement probes for collecting flow data"""
from typing import List, Tuple
from collections import deque

class MeasurementProbe:
    """Représente une pipette de mesure sur une connexion / Represents a measurement probe on a connection"""
    
    def __init__(self, probe_id: str, name: str, connection_id: str, measure_mode: str = "buffer", max_points: int = 500000):
        self.probe_id = probe_id
        self.name = name
        self.connection_id = connection_id
        self.measure_mode = measure_mode  # "buffer" ou "cumulative" / "buffer" or "cumulative"
        
        # Historique des mesures (time, value) / Measurement history (time, value)
        # La limite est configurable via les paramètres généraux
        # Limit is configurable via general settings
        self.data_points: deque = deque(maxlen=max_points)
        
        # Historiques séparés pour export CSV (toujours les deux types)
        # Separate histories for CSV export (always both types)
        self.data_points_buffer: deque = deque(maxlen=max_points)  # Valeurs buffer instantanées / Instant buffer values
        self.data_points_cumulative: deque = deque(maxlen=max_points)  # Valeurs cumulatives / Cumulative values
        
        # Pour affichage détaillé par type : tracker les types d'items dans le buffer
        # For detailed display by type: track item types in buffer
        # Structure : {timestamp: {type_name: count, ...}}
        self.type_data_points: deque = deque(maxlen=max_points)
        
        # Tracking cumulatif par type (pour mode cumulative)
        # Cumulative tracking by type (for cumulative mode)
        self.cumulative_type_counts: dict = {}  # {type_name: total_count}
        
        # Événements d'entrée et sortie (time, quantity, event_type)
        # Input and output events (time, quantity, event_type)
        # event_type: 'in' pour entrée / for input, 'out' pour sortie / for output
        self.events: deque = deque(maxlen=100000)
        
        # Propriétés visuelles / Visual properties
        self.x = 0.0  # Position X de l'icône / Icon X position
        self.y = 0.0  # Position Y de l'icône / Icon Y position
        self.color = "#2196F3"  # Couleur du graphique / Graph color (blue default)
        self.visible = True  # Afficher le graphique / Show graph
        
        # Statistiques / Statistics
        self.total_items = 0
        self.total_items_out = 0  # Items sortis / Items out
        self.current_flow_rate = 0.0  # Items par unité de temps / Items per time unit
        
        # Suivi de la saturation des buffers de mesure
        # Measurement buffer saturation tracking
        self._capacity_warning_80_shown = False
        self._capacity_warning_90_shown = False
        self._capacity_warning_100_shown = False
        
        # Suivi de la saturation des buffers de mesure
        # Measurement buffer saturation tracking
        self._capacity_warning_80_shown = False
        self._capacity_warning_90_shown = False
        self._capacity_warning_100_shown = False
        
    def add_measurement(self, timestamp: float, buffer_count: int, type_counts: dict = None):
        """Ajoute une mesure / Adds a measurement
        
        Args:
            timestamp: Le temps de la mesure / Measurement time
            buffer_count: Nombre total d'items dans le buffer / Total items in buffer
            type_counts: Dictionnaire {type_name: count} / Dictionary for detailed display
        """
        # Calculer la valeur cumulative / Calculate cumulative value
        cumulative_value = max(self.total_items_out, self.total_items)
        
        # TOUJOURS enregistrer les deux types pour l'export CSV
        # ALWAYS record both types for CSV export
        self.data_points_buffer.append((timestamp, buffer_count))
        self.data_points_cumulative.append((timestamp, cumulative_value))
        
        # Enregistrer dans data_points selon le mode actif (pour affichage graphique)
        # Record in data_points based on active mode (for graph display)
        if self.measure_mode == "cumulative":
            self.data_points.append((timestamp, cumulative_value))
        else:
            # Mode buffer : enregistrer le nombre d'items dans le buffer
            # Buffer mode: record number of items in buffer
            self.data_points.append((timestamp, buffer_count))
        
        # Vérifier la saturation du buffer de mesures
        # Check measurement buffer saturation
        self._check_capacity_warning()
        
        # Enregistrer les types selon le mode / Record types based on mode
        if type_counts:
            if self.measure_mode == "cumulative":
                # Mode cumulatif : enregistrer le cumulatif par type
                # Cumulative mode: record cumulative by type
                self.type_data_points.append((timestamp, self.cumulative_type_counts.copy()))
            else:
                # Mode buffer : enregistrer le buffer actuel par type
                # Buffer mode: record current buffer by type
                self.type_data_points.append((timestamp, type_counts.copy()))
        else:
            if self.measure_mode == "cumulative":
                self.type_data_points.append((timestamp, self.cumulative_type_counts.copy()))
            else:
                self.type_data_points.append((timestamp, {}))
        
    def add_item_passing(self, timestamp: float, quantity: int = 1, item_type: str = None):
        """Enregistre le passage d'items (entrée dans la connexion)
           Records items passing (entering the connection)
        
        Args:
            timestamp: Le temps de la mesure / Measurement time
            quantity: Nombre d'unités qui passent / Number of passing units (default 1)
            item_type: Type de l'item / Item type (for cumulative tracking by type)
        """
        self.total_items += quantity
        self.events.append((timestamp, quantity, 'in'))
        
        # Incrémenter le compteur cumulatif par type
        # Increment cumulative counter by type
        # Utiliser 'default' si aucun type n'est spécifié / Use 'default' if no type specified
        type_key = item_type if item_type else 'default'
        self.cumulative_type_counts[type_key] = self.cumulative_type_counts.get(type_key, 0) + quantity
        
        # Calculer le débit sur une fenêtre glissante
        # Calculate flow rate over a sliding window
        if len(self.data_points) > 10:
            # Calculer le nombre d'items sur les 10 dernières mesures
            # Calculate items count over last 10 measurements
            time_window = timestamp - self.data_points[-10][0]
            if time_window > 0:
                items_in_window = sum(1 for t, _ in list(self.data_points)[-10:])
                self.current_flow_rate = items_in_window / time_window
    
    def add_item_consumed(self, timestamp: float, quantity: int = 1, types_consumed: dict = None):
        """Enregistre la consommation d'items (sortie de la connexion)
           Records items consumption (leaving the connection)
        
        Args:
            timestamp: Le temps de la mesure / Measurement time
            quantity: Nombre d'unités consommées / Number of consumed units (default 1)
            types_consumed: Dict {type_name: count} des types consommés / consumed types
        """
        self.total_items_out += quantity
        self.events.append((timestamp, quantity, 'out'))
        
        # Incrémenter le compteur cumulatif par type pour les sorties
        # Increment cumulative counter by type for outputs
        if types_consumed:
            for type_name, count in types_consumed.items():
                self.cumulative_type_counts[type_name] = self.cumulative_type_counts.get(type_name, 0) + count
    
    def get_data(self) -> List[Tuple[float, float]]:
        """Retourne les données pour le graphique / Returns data for graph (normal mode)"""
        return list(self.data_points)
    
    def get_type_data(self) -> List[Tuple[float, dict]]:
        """Retourne les données détaillées par type / Returns detailed data by type for stacked graph"""
        return list(self.type_data_points)
    
    def get_all_item_types(self) -> List[str]:
        """Retourne tous les types d'items observés / Returns all observed item types"""
        types = set()
        for _, type_counts in self.type_data_points:
            types.update(type_counts.keys())
        return sorted(list(types))
    
    def _check_capacity_warning(self):
        """Vérifie la limite du buffer et affiche un avertissement
           Checks if approaching buffer limit and shows warning"""
        current_size = len(self.data_points)
        max_size = self.data_points.maxlen
        
        if max_size is None:
            return
        
        capacity_percent = (current_size / max_size) * 100
        
        if capacity_percent >= 100 and not self._capacity_warning_100_shown:
            # Message d'alerte critique / Critical alert message
            message = (f"LIMITE MAXIMALE ATTEINTE! / MAX LIMIT REACHED!\n\n"
                      f"Pipette / Probe: {self.name}\n"
                      f"Points enregistrés / Recorded points: {max_size:,}\n\n"
                      f"⚠️ Les points les plus anciens sont SUPPRIMÉS automatiquement.\n"
                      f"   Oldest points are being DELETED automatically.\n"
                      f"   Vos graphiques montrent des valeurs incorrectes!\n"
                      f"   Your graphs show incorrect values!\n\n"
                      f"Actions possibles / Possible actions:\n"
                      f"• Réduire la durée d'analyse / Reduce analysis duration\n"
                      f"• Augmenter la limite dans Paramètres / Increase limit in Settings\n"
                      f"  (actuellement/currently: {max_size:,} points)")
            print(f"\n{'='*80}")
            print(f"⚠️  ⚠️  ⚠️  ALERTE CRITIQUE PIPETTE / CRITICAL PROBE ALERT [{self.name}] ⚠️  ⚠️  ⚠️")
            print(f"{'='*80}")
            print(f"LIMITE MAXIMALE ATTEINTE / MAX LIMIT REACHED: {max_size:,} points!")
            print(f"Les points les plus anciens sont SUPPRIMÉS / Oldest points are DELETED.")
            print(f"VOS GRAPHIQUES AFFICHENT DES VALEURS INCORRECTES / GRAPHS SHOW INCORRECT VALUES!")
            print(f"\n➡️  SOLUTION : Augmentez la limite dans Paramètres / Increase limit in Settings")
            print(f"{'='*80}\n")
            
            # Afficher une fenêtre d'alerte / Show alert dialog
            self._show_warning_dialog("⚠️ Limite de mesures atteinte / Measurement limit reached", message)
            self._capacity_warning_100_shown = True
        elif capacity_percent >= 90 and not self._capacity_warning_90_shown:
            print(f"\n⚠️  Avertissement/Warning Pipette [{self.name}] : {capacity_percent:.0f}% capacité/capacity ({current_size:,}/{max_size:,} points)")
            print(f"   Approche de la limite maximale / Approaching max limit.\n")
            self._capacity_warning_90_shown = True
        elif capacity_percent >= 80 and not self._capacity_warning_80_shown:
            print(f"ℹ️  Info Pipette [{self.name}] : {capacity_percent:.0f}% capacité/capacity ({current_size:,}/{max_size:,} points)")
            self._capacity_warning_80_shown = True
    
    def _show_warning_dialog(self, title, message):
        """Affiche une boîte de dialogue d'avertissement / Shows a warning dialog"""
        try:
            from tkinter import messagebox
            import tkinter as tk
            
            # Créer une fenêtre root temporaire si nécessaire
            # Create a temporary root window if needed
            root = tk._default_root
            if root is None:
                # Créer une fenêtre invisible temporaire
                # Create a temporary invisible window
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning(title, message)
                root.destroy()
            else:
                # Utiliser la fenêtre principale existante
                # Use existing main window
                messagebox.showwarning(title, message)
        except Exception as e:
            # Si l'affichage échoue (pas de GUI, thread secondaire, etc.), ignorer
            # If display fails (no GUI, secondary thread, etc.), ignore silently
            print(f"[INFO] Impossible d'afficher la fenêtre d'alerte / Cannot show alert dialog: {e}")
    
    def clear_data(self):
        """Efface les données collectées / Clears collected data"""
        self.data_points.clear()
        self.type_data_points.clear()
        self.events.clear()
        self.cumulative_type_counts.clear()
        self.total_items = 0
        self.total_items_out = 0
        self.current_flow_rate = 0.0
        
        # Réinitialiser les flags d'avertissement / Reset warning flags
        self._capacity_warning_80_shown = False
        self._capacity_warning_90_shown = False
        self._capacity_warning_100_shown = False
