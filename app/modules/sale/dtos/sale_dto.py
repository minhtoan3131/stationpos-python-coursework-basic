from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal

@dataclass
class CartItemDTO:
    product_id: int
    sku: str
    name: str
    unit_id: int
    unit_name: str
    quantity: int
    price: Decimal
    total: Decimal

@dataclass
class CheckoutDTO:
    code: str
    total_amount: Decimal
    discount: Decimal
    final_amount: Decimal
    payment_method: str  # 'CASH' hoặc 'TRANSFER'
    cash_received: Decimal
    items: List[CartItemDTO]
    note: Optional[str] = None

@dataclass
class PosItemDTO:
    """DTO chứa dữ liệu đã được tính toán sẵn, Controller chỉ việc hiển thị"""
    product_id: int
    sku: str
    name: str
    unit_id: int
    unit_name: str
    price: float
    stock_qty: int
    is_conversion: bool = False