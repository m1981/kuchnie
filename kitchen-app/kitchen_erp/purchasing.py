"""Purchasing strategies for material procurement"""
from abc import ABC, abstractmethod
from math import ceil


class PurchasingStrategy(ABC):
    """
    Abstract base class for purchasing strategies.
    
    Different materials are purchased in different ways:
    - Sheet materials (boards) come in fixed sizes
    - Linear materials (edgebanding) come in rolls
    - Countertops come in standard lengths
    - Hardware comes in exact quantities
    """
    
    @abstractmethod
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """
        Calculate the actual quantity to purchase based on net requirement.
        
        Args:
            net_quantity: The exact amount needed
            
        Returns:
            The amount to actually purchase (may be higher due to standard sizes)
        """
        pass
    
    @abstractmethod
    def get_waste_factor(self, net_quantity: float) -> float:
        """
        Calculate the waste factor for this purchase.
        
        Returns:
            Ratio of purchased to net quantity (e.g., 1.2 = 20% waste)
        """
        pass


class SheetMaterialStrategy(PurchasingStrategy):
    """
    Strategy for sheet materials (MDF, plywood, etc.) sold in full sheets.
    
    Example: Egger boards come in 2800x2070mm = 5.796 m²
    If you need 7.5 m², you must buy 2 full sheets = 11.592 m²
    """
    
    def __init__(self, sheet_size_m2: float = 5.796):
        """
        Initialize sheet material strategy.
        
        Args:
            sheet_size_m2: Size of one sheet in square meters (default: 2800x2070mm)
        """
        self.sheet_size_m2 = sheet_size_m2
    
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """Calculate number of full sheets needed"""
        sheets_needed = ceil(net_quantity / self.sheet_size_m2)
        return sheets_needed * self.sheet_size_m2
    
    def get_waste_factor(self, net_quantity: float) -> float:
        """Calculate waste factor based on sheet rounding"""
        purchase_qty = self.calculate_purchase_quantity(net_quantity)
        return purchase_qty / net_quantity if net_quantity > 0 else 1.0


class LinearMaterialStrategy(PurchasingStrategy):
    """
    Strategy for linear materials (edgebanding, profiles) sold in rolls.
    
    Example: Edgebanding comes in 50m rolls
    If you need 45m, you buy 1 roll = 50m
    If you need 55m, you buy 2 rolls = 100m
    """
    
    def __init__(self, roll_length_m: float = 50.0, waste_factor: float = 1.10):
        """
        Initialize linear material strategy.
        
        Args:
            roll_length_m: Length of one roll in meters
            waste_factor: Additional waste for cutting (default 10%)
        """
        self.roll_length_m = roll_length_m
        self.waste_factor = waste_factor
    
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """Calculate number of full rolls needed, including waste"""
        net_with_waste = net_quantity * self.waste_factor
        rolls_needed = ceil(net_with_waste / self.roll_length_m)
        return rolls_needed * self.roll_length_m
    
    def get_waste_factor(self, net_quantity: float) -> float:
        """Calculate total waste factor including cutting waste and roll rounding"""
        purchase_qty = self.calculate_purchase_quantity(net_quantity)
        return purchase_qty / net_quantity if net_quantity > 0 else 1.0


class CountertopStrategy(PurchasingStrategy):
    """
    Strategy for countertops sold in standard lengths.
    
    Example: HPL countertops come in 4100mm lengths
    If you need 3500mm, you buy 1 piece = 4100mm
    If you need 5000mm, you buy 2 pieces = 8200mm
    """
    
    def __init__(self, standard_length_mm: float = 4100.0, width_mm: float = 600.0):
        """
        Initialize countertop strategy.
        
        Args:
            standard_length_mm: Standard length in millimeters
            width_mm: Standard width in millimeters
        """
        self.standard_length_mm = standard_length_mm
        self.width_mm = width_mm
        self.standard_area_m2 = (standard_length_mm * width_mm) / 1_000_000
    
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """
        Calculate countertop purchase quantity.
        
        Args:
            net_quantity: Net area in m² or length in linear meters
            
        Returns:
            Purchase quantity in m²
        """
        # Assume net_quantity is in m² (area)
        pieces_needed = ceil(net_quantity / self.standard_area_m2)
        return pieces_needed * self.standard_area_m2
    
    def get_waste_factor(self, net_quantity: float) -> float:
        """Calculate waste factor for countertop"""
        purchase_qty = self.calculate_purchase_quantity(net_quantity)
        return purchase_qty / net_quantity if net_quantity > 0 else 1.0


class ExactQuantityStrategy(PurchasingStrategy):
    """
    Strategy for items purchased in exact quantities (hardware, hinges, etc.).
    
    No rounding to standard sizes, but may include a small waste factor
    for damaged/lost items.
    """
    
    def __init__(self, waste_factor: float = 1.05):
        """
        Initialize exact quantity strategy.
        
        Args:
            waste_factor: Small buffer for damaged items (default 5%)
        """
        self.waste_factor = waste_factor
    
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """Calculate purchase quantity with small waste buffer"""
        return ceil(net_quantity * self.waste_factor)
    
    def get_waste_factor(self, net_quantity: float) -> float:
        """Return the configured waste factor"""
        return self.waste_factor


def get_strategy_for_material(material_category: str) -> PurchasingStrategy:
    """
    Factory function to get appropriate purchasing strategy for material category.
    
    Args:
        material_category: Category of material (e.g., "Board", "Edgebanding", "Countertop")
        
    Returns:
        Appropriate PurchasingStrategy instance
    """
    strategies = {
        "Board": SheetMaterialStrategy(),
        "Panel": SheetMaterialStrategy(),
        "Edgebanding": LinearMaterialStrategy(),
        "Countertop": CountertopStrategy(),
        "Hardware": ExactQuantityStrategy(),
        "Equipment": ExactQuantityStrategy(waste_factor=1.0),  # No waste for equipment
    }
    
    return strategies.get(material_category, ExactQuantityStrategy())
