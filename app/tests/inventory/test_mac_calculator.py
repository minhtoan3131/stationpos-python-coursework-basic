import pytest
from decimal import Decimal
from app.modules.inventory.utils.mac_calculator import MACCalculator


# ==========================================
# KỊCH BẢN THÀNH CÔNG
# ==========================================
def test_mac_calculate_standard_with_infinite_decimals():
    """Tính MAC với kết quả chia ra số lẻ vô hạn, phải làm tròn đúng 4 chữ số"""
    # GIVEN: Tồn 10 giá 100. Nhập thêm 3 giá 40.
    # Tổng tiền = 140. Tổng lượng = 13. MAC = 140 / 13 = 10.7692307...
    current_qty, current_val = 10, Decimal('100.0000')
    import_qty, import_val = 3, Decimal('40.0000')

    # WHEN
    new_qty, new_val, new_mac = MACCalculator.calculate_standard_mac(
        current_qty, current_val, import_qty, import_val
    )

    # THEN: 10.7692307... làm tròn Half Up 4 số sẽ thành 10.7692
    assert new_qty == 13
    assert new_val == Decimal('140.0000')
    assert new_mac == Decimal('10.7692')


def test_mac_calculate_exact_round_half_up():
    """Kiểm tra chính xác quy tắc làm tròn lên (Round Half Up) ở chữ số thứ 5"""
    # GIVEN: Cố tình tạo ra số MAC có đuôi là ...5
    # (10.0000 + 10.0001) / 2 = 20.0001 / 2 = 10.00005
    current_qty, current_val = 1, Decimal('10.0000')
    import_qty, import_val = 1, Decimal('10.0001')

    # WHEN
    new_qty, new_val, new_mac = MACCalculator.calculate_standard_mac(
        current_qty, current_val, import_qty, import_val
    )

    # THEN: Đuôi 5 phải được làm tròn lên thành 1
    assert new_mac == Decimal('10.0001')


def test_mac_calculate_from_empty_inventory():
    """Tính MAC khi kho đang trống trơn (Tồn = 0)"""
    current_qty, current_val = 0, Decimal('0')
    import_qty, import_val = 10, Decimal('50000')

    new_qty, new_val, new_mac = MACCalculator.calculate_standard_mac(
        current_qty, current_val, import_qty, import_val
    )

    assert new_qty == 10
    assert new_val == Decimal('50000.0000')
    assert new_mac == Decimal('5000.0000')


# ==========================================
# KỊCH BẢN THẤT BẠI (EXCEPTIONS)
# ==========================================
def test_mac_raise_error_when_inventory_is_negative():
    """Cấm tuyệt đối tính MAC khi kho đang bị âm"""
    with pytest.raises(ValueError) as exc_info:
        MACCalculator.calculate_standard_mac(-5, Decimal('-20000'), 10, Decimal('50000'))

    assert "Hàm này không dùng cho kho âm" in str(exc_info.value)


def test_mac_raise_error_when_new_qty_is_zero():
    """Cấm chia cho 0 khi số lượng mới <= 0"""
    with pytest.raises(ValueError) as exc_info:
        # Kho trống, nhập thêm 0 cái
        MACCalculator.calculate_standard_mac(0, Decimal('0'), 0, Decimal('0'))

    assert "không thể <= 0" in str(exc_info.value)