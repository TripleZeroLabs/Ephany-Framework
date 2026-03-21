class UnitConverter:
    """
    Handles conversion between Base Storage Units (Metric) and User Preferred Units.
    
    Base Storage Units:
    - Length: Millimeters (mm)
    - Area: Square Meters (sq_m)
    - Volume: Cubic Meters (cu_m)
    - Mass: Kilograms (kg)
    """

    # Conversion factors TO Base Unit (e.g., 1 foot * 304.8 = 304.8 mm)
    TO_BASE = {
        'length': {
            'mm': 1.0,
            'cm': 10.0,
            'm': 1000.0,
            'in': 25.4,
            'ft': 304.8,
        },
        'area': {
            'sq_m': 1.0,
            'sq_ft': 0.092903,
        },
        'volume': {
            'cu_m': 1.0,
            'cu_ft': 0.0283168,
        },
        'mass': {
            'kg': 1.0,
            'lb': 0.453592,
        }
    }

    @classmethod
    def to_storage(cls, value, user_unit, category):
        """
        Convert FROM User Unit TO Storage Unit (Base).
        Example: 10 ft -> 3048 mm
        """
        if value is None:
            return None
            
        try:
            factor = cls.TO_BASE[category][user_unit]
            return float(value) * factor
        except KeyError:
            # Fallback if unit not found
            return value

    @classmethod
    def from_storage(cls, value, user_unit, category):
        """
        Convert FROM Storage Unit (Base) TO User Unit.
        Example: 3048 mm -> 10 ft
        """
        if value is None:
            return None
            
        try:
            factor = cls.TO_BASE[category][user_unit]
            return float(value) / factor
        except KeyError:
            # Fallback
            return value
