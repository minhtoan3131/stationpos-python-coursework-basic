import pytest
from decimal import Decimal

from app.modules.sale.dtos.sale_dto import CartItemDTO
from app.modules.sale.utils.sale_calculator import SaleCalculator


# ==========================================
# TÍNH TIỀN THỪA (CALCULATE CHANGE)
# ==========================================
@pytest.mark.parametrize("cash_received, final_amount, expected_change", [
    (Decimal('100000'), Decimal('100000'), Decimal('0')),  # Đưa vừa đủ
    (Decimal('500000'), Decimal('150000'), Decimal('350000')),  # Đưa thừa tiền
    (Decimal('50000'), Decimal('100000'), Decimal('-50000')),
    # Đưa thiếu tiền (Trường hợp này SaleValidator sẽ chặn, nhưng Calculator vẫn phải tính đúng âm)
])
def test_calculate_change(cash_received, final_amount, expected_change):
    """Đảm bảo phép trừ tiền thừa chính xác tuyệt đối với kiểu Decimal"""
    assert SaleCalculator.calculate_change(cash_received, final_amount) == expected_change

# ==========================================
# TÍNH TỔNG TIỀN GIỎ HÀNG
# ==========================================
def test_calculate_total_amount_with_decimal_precision():
    """Đảm bảo hàm tính tổng tiền hóa đơn cộng dồn chính xác, không lệch float"""
    items = [
         Thay thế '4k' và '8k' bằng chuỗi số chuẩn toán học để Decimal khởi tạo hợp lệ
        CartItemDTO(100, "SP01", "A", 10, "Cái", 1, Decimal('10000.0001'), Decimal('10000.0001'), Decimal('4000')),
        CartItemDTO(101, "SP02", "B", 10, "Cái", 1, Decimal('20000.0002'), Decimal('20000.0002'), Decimal('8000'))
    ]
    total = SaleCalculator.calculate_total_amount(items)
    assert total == Decimal('30000.0003')