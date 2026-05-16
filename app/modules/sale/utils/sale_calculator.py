from decimal import Decimal
from typing import List, Literal, Tuple
from app.modules.sale.dtos.sale_dto import CartItemDTO


class SaleCalculator:
    @staticmethod
    def calculate_total_amount(items: List[CartItemDTO]) -> Decimal | Literal[0]:
        """Tính tổng tiền của giỏ hàng."""
        return sum([item.total for item in items])

    @staticmethod
    def calculate_change(cash_received: Decimal, final_amount: Decimal) -> Decimal:
        """Tính tiền thừa trả khách."""
        return cash_received - final_amount

    @staticmethod
    def calculate_conversion_details(wholesale_price, base_stock: int, ratio) -> Tuple[float, int]:
        """
        Tính toán giá và tồn kho cho đơn vị quy đổi (Sỉ).
        Trả về tuple: (Giá sỉ thực tế, Tồn kho quy đổi)
        """
        # Đảm bảo ratio luôn hợp lệ (tránh chia cho 0 hoặc None)
        safe_ratio = float(ratio) if ratio else 1.0

        # Tính giá: Giá sỉ cơ bản * Tỷ lệ quy đổi
        actual_price = float(wholesale_price or 0) * safe_ratio

        # Tính tồn kho: Tồn kho cơ bản // Tỷ lệ quy đổi
        converted_stock = int(base_stock // safe_ratio)

        return actual_price, converted_stock