from abc import ABC, abstractmethod
from typing import Optional

class InventoryRepository(ABC):
    @abstractmethod
    def get_inventory_status(self, product_id: int) -> int: pass

    @abstractmethod
    def create_purchase_order(self, po_data: dict) -> int: pass

    @abstractmethod
    def create_purchase_order_item(self, item_data: dict) -> None: pass

    @abstractmethod
    def add_stock_transaction(self, trans_data: dict) -> None: pass

    @abstractmethod
    def update_inventory_status(self, product_id: int, new_qty: int, new_total_value) -> None: pass

    @abstractmethod
    def get_inventory_list_data(self, search_keyword: str = None) -> list: pass

    @abstractmethod
    def get_inventory_report_data(self) -> list:
        """
        Lấy dữ liệu Tồn kho kèm Giá trị tài chính (Giá vốn, Tổng tiền)
        để phục vụ việc xuất báo cáo Excel.
        """
        pass