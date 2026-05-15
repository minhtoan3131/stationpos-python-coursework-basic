from dataclasses import dataclass, field
from typing import List, Optional

# ==========================================
# DTO CHO NGHIỆP VỤ NHẬP KHO (PURCHASE ORDER)
# ==========================================

@dataclass
class PurchaseOrderItemDTO:
    """Đại diện cho 1 dòng sản phẩm trên bảng Phiếu Nhập"""
    product_id: int
    unit_id: int          # ID của Đơn vị tính (Phân biệt Lẻ/Sỉ)
    quantity: int         # Số lượng nhập (Tính theo unit_id)
    unit_price: float     # Giá nhập của 1 đơn vị (Tính theo unit_id)

@dataclass
class PurchaseOrderCreateDTO:
    """Đại diện cho toàn bộ Form Phiếu Nhập gửi xuống Service"""
    supplier_id: Optional[int]
    note: Optional[str]
    items: List[PurchaseOrderItemDTO] = field(default_factory=list)

# ==========================================
# DTO CHO MÀN HÌNH DANH SÁCH TỒN KHO
# ==========================================

@dataclass
class InventoryListDTO:
    """Đại diện cho 1 dòng hiển thị trên Bảng Tồn Kho"""
    product_id: int
    sku: str
    product_name: str
    base_unit_name: str
    total_base_quantity: int          # Tổng tồn kho hiện tại (Tính bằng đơn vị cơ bản)
    conversion_quantity_str: str      # Chuỗi hiển thị quy đổi (VD: "10 Hộp + 5 Cây")
    min_stock: int
    is_low_stock: bool