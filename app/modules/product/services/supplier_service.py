from abc import ABC, abstractmethod
from typing import List, Dict, Any

class SupplierService(ABC):
    @abstractmethod
    def get_all_suppliers(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_supplier(self, name: str) -> int:
        pass