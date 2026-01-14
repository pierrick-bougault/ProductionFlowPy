"""Système de gestion des unités de temps / Time unit management system"""
from enum import Enum

class TimeUnit(Enum):
    """Unités de temps supportées / Supported time units"""
    SECONDS = "secondes"  # seconds
    CENTISECONDS = "centisecondes"  # centiseconds

class TimeConverter:
    """Convertit les temps entre différentes unités / Converts times between different units"""
    
    # Tous les facteurs sont relatifs aux centisecondes (unité de base)
    # All factors are relative to centiseconds (base unit)
    CONVERSION_FACTORS = {
        TimeUnit.CENTISECONDS: 1.0,
        TimeUnit.SECONDS: 100.0
    }
    
    @staticmethod
    def to_centiseconds(value: float, from_unit: TimeUnit) -> float:
        """Convertit une valeur vers les centisecondes / Converts a value to centiseconds (base unit)"""
        return value * TimeConverter.CONVERSION_FACTORS[from_unit]
    
    @staticmethod
    def from_centiseconds(value: float, to_unit: TimeUnit) -> float:
        """Convertit depuis les centisecondes / Converts from centiseconds to requested unit"""
        return value / TimeConverter.CONVERSION_FACTORS[to_unit]
    
    @staticmethod
    def convert(value: float, from_unit: TimeUnit, to_unit: TimeUnit) -> float:
        """Convertit entre deux unités quelconques / Converts between any two units"""
        centiseconds = TimeConverter.to_centiseconds(value, from_unit)
        return TimeConverter.from_centiseconds(centiseconds, to_unit)
    
    @staticmethod
    def format_time(value: float, unit: TimeUnit) -> str:
        """Formate un temps avec son unité / Formats a time with its unit"""
        if unit == TimeUnit.SECONDS:
            return f"{value:.2f} s"
        else:  # CENTISECONDS
            return f"{value:.2f} cs"
    
    @staticmethod
    def get_unit_symbol(unit: TimeUnit) -> str:
        """Retourne le symbole de l'unité / Returns the unit symbol"""
        symbols = {
            TimeUnit.SECONDS: "s",
            TimeUnit.CENTISECONDS: "cs"
        }
        return symbols[unit]
