import pytest
from decimal import Decimal
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
# QUY ĐỔI SỈ/LẺ (CONVERSION DETAILS)
# ==========================================
@pytest.mark.parametrize("wholesale_price, base_stock, ratio, expected_price, expected_stock", [
    # Nhánh 1: Quy đổi chuẩn (Giá sỉ 50k/cái, 1 Hộp = 10 cái, Tồn 25 cái) -> Giá Hộp = 500k, Tồn Hộp = 2
    (50000, 25, 10, 500000.0, 2),

    # Nhánh 2: Tồn kho cơ bản không đủ chia thành 1 đơn vị Sỉ (Tồn 9 cái, 1 Hộp = 10 cái) -> Tồn Hộp = 0
    (50000, 9, 10, 500000.0, 0),

    # Nhánh 3: Tồn kho đang bằng 0 -> Tồn Hộp = 0
    (100000, 0, 5, 500000.0, 0),

    # Nhánh 4: Chặn lỗi rác (Ratio là None hoặc 0) -> Hàm phải có fallback an toàn (safe_ratio = 1.0)
    (50000, 20, None, 50000.0, 20),
    (50000, 20, 0, 50000.0, 20),
])
def test_calculate_conversion_details(wholesale_price, base_stock, ratio, expected_price, expected_stock):
    """Vét cạn các trường hợp chia số lượng và nhân giá trị cho ĐVT quy đổi"""
    actual_price, actual_stock = SaleCalculator.calculate_conversion_details(wholesale_price, base_stock, ratio)

    assert actual_price == expected_price
    assert actual_stock == expected_stock