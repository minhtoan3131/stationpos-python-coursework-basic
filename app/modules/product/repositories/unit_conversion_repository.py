from abc import ABC, abstractmethod
from typing import Optional
from app.modules.product.entities.unit_conversion import UnitConversion

class UnitConversionRepository(ABC):
    @abstractmethod
    def get_unit_conversion(self, product_id: int) -> Optional[UnitConversion]: pass

    @abstractmethod
    def create_unit_conversion(self, conversion: UnitConversion) -> int: pass

    @abstractmethod
    def update_unit_conversion(self, conversion: UnitConversion) -> bool: pass