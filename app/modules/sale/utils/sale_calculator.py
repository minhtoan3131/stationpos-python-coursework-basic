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