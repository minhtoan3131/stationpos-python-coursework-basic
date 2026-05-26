from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Optional


class MACCalculator:

    @staticmethod
    def calculate_standard_mac(
            current_qty: int,
            current_total_value: Decimal,
            import_qty: int,
            import_total_value: Decimal
    ) -> Tuple[int, Decimal, Decimal, Optional[Decimal]]:
        """
        Tính toán thông số kho nhập tiêu chuẩn (Mức tăng tuyệt đối).

        Trả về bộ giá trị tuple:
        (new_qty, new_total_value, new_mac, garbage_value)
        """

        # Chốt chặn kho âm ngay từ đầu (Chưa cho phép bán khống)
        if current_qty < 0:
            raise ValueError("KHO_AM_CHAN_NGHIEP_VU")

        garbage_value = None
        cleaned_total_value = current_total_value

        # Nhận diện rác dữ liệu khi kho bằng 0 nhưng số tiền khác 0
        if current_qty == 0 and current_total_value != 0:
            garbage_value = current_total_value
            cleaned_total_value = Decimal('0')  # Làm sạch môi trường trước khi cộng dồn

        new_qty = current_qty + import_qty

        #  Chốt chặn sau tính toán, số lượng mới phải đảm bảo > 0
        if new_qty <= 0:
            raise ValueError("NHAP_KHO_VAN_AM_CHAN_NGHIEP_VU")

        # Tính toán giá trị mới dựa trên môi trường tiền đã được dọn rác
        new_total_value = cleaned_total_value + import_total_value
        new_mac = new_total_value / Decimal(str(new_qty))

        # Áp dụng làm tròn ROUND_HALF_UP tới 4 chữ số thập phân theo quy định
        return (
            new_qty,
            new_total_value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            new_mac.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            garbage_value
        )