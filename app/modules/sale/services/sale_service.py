from abc import ABC, abstractmethod
from app.modules.sale.dtos.sale_dto import CheckoutDTO

class SaleService(ABC):
    @abstractmethod
    def process_checkout(self, checkout_data: CheckoutDTO) -> str:
        """
        Xử lý quy trình thanh toán (Validate, Lưu Hóa đơn, Trừ kho, Ghi Log).
        Trả về mã hóa đơn (invoice_code) nếu thành công.
        """
        pass