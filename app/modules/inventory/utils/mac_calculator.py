from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple


class MACCalculator:

    @staticmethod
    def calculate_standard_mac(
            current_qty: int, current_total_value: Decimal,
            import_qty: int, import_total_value: Decimal
    ) -> Tuple[int, Decimal, Decimal]:
        """Công thức: Tính MAC khi kho đang dương (Cộng dồn hoàn toàn)"""

        if current_qty < 0:
            raise ValueError("Hàm này không dùng cho kho âm")

        new_qty = current_qty + import_qty
        if new_qty <= 0:
            raise ValueError("Số lượng mới sau khi nhập tiêu chuẩn không thể <= 0.")

        new_total_value = current_total_value + import_total_value
        new_mac = new_total_value / Decimal(str(new_qty))

        return new_qty, new_total_value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP), new_mac.quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP)

