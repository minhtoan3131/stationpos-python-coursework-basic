from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class PurchaseOrderHistoryFilterDTO:
    """Tham số bộ lọc từ UI gửi xuống Service"""
    from_date: str  # Định dạng 'YYYY-MM-DD'
    to_date: str    # Định dạng 'YYYY-MM-DD'
    keyword: Optional[str] = None
    status: Optional[str] = 'ALL'  # 'ALL', 'COMPLETED', 'CANCELLED'

@dataclass
class PurchaseOrderMasterDTO:
    """Thông tin tổng quan 1 Phiếu nhập (Dùng cho Bảng Master)"""
    id: int
    code: str
    created_at: datetime
    supplier_name: str
    total_amount: float
    status: str
    note: Optional[str] = None
    cancel_reason: Optional[str] = None

@dataclass
class PurchaseOrderDetailDTO:
    """Thông tin chi tiết 1 mặt hàng trong Phiếu nhập (Dùng cho Bảng Detail)"""
    product_id: int  # Cần thiết để Service lấy ID đi trừ tồn kho khi hủy phiếu
    sku: str
    product_name: str
    unit_name: str
    quantity: int
    unit_price: float
    total_price: float