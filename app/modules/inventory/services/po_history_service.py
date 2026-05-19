from abc import ABC, abstractmethod
from typing import List

from app.modules.inventory.dtos.po_history_dto import (
    PurchaseOrderHistoryFilterDTO,
    PurchaseOrderMasterDTO,
    PurchaseOrderDetailDTO
)

class PurchaseOrderHistoryService(ABC):

    @abstractmethod
    def search_history(self, filter_dto: PurchaseOrderHistoryFilterDTO) -> List[PurchaseOrderMasterDTO]:
        """Truy vấn danh sách phiếu nhập dựa trên bộ lọc"""
        pass

    @abstractmethod
    def get_details(self, po_id: int) -> List[PurchaseOrderDetailDTO]:
        """Lấy danh sách các mặt hàng chi tiết của một phiếu nhập"""
        pass

    @abstractmethod
    def cancel_purchase_order(self, po_id: int, cancel_reason: str) -> None:
        """
        Nghiệp vụ Hủy phiếu nhập:
        1. Kiểm tra phiếu có tồn tại và đang ở trạng thái COMPLETED không.
        2. Kiểm tra tồn kho hiện tại có đủ để trừ ngược lại không.
        3. Cập nhật trạng thái phiếu thành CANCELLED.
        4. Trừ tồn kho và ghi log hủy.
        (Phải bọc trong Transaction)
        """
        pass