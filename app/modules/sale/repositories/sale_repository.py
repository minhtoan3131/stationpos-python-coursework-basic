from abc import ABC, abstractmethod
from typing import List
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO

class SaleRepository(ABC):
    @abstractmethod
    def create_invoice(self, checkout_data: CheckoutDTO) -> int:
        """Lưu thông tin chung hóa đơn và trả về invoice_id"""
        pass

    @abstractmethod
    def create_invoice_items(self, invoice_id: int, items: List[CartItemDTO]) -> None:
        """Lưu chi tiết các mặt hàng trong hóa đơn"""
        pass

    @abstractmethod
    def add_invoice_log(self, invoice_id: int, action: str, note: str) -> None:
        """Ghi lịch sử thao tác hóa đơn"""
        pass