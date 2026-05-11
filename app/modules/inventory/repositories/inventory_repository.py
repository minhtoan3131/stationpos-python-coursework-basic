from abc import ABC, abstractmethod
from typing import Optional

class InventoryRepository(ABC):
    @abstractmethod
    def get_inventory_quantity(self, product_id: int) -> int: pass

    @abstractmethod
    def create_purchase_order(self, po_data: dict) -> int: pass

    @abstractmethod
    def create_purchase_order_item(self, item_data: dict) -> None: pass

    @abstractmethod
    def add_stock_transaction(self, trans_data: dict) -> None: pass

    @abstractmethod
    def update_inventory_quantity(self, product_id: int, delta_qty: int) -> None: pass

    @abstractmethod
    def get_inventory_list_data(self, search_keyword: str = None) -> list: pass