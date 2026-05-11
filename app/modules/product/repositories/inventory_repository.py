from abc import ABC, abstractmethod

class InventoryRepository(ABC):
    @abstractmethod
    def get_inventory_quantity(self, product_id: int) -> int: pass