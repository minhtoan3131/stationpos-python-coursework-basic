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

    # WHEN - Đã cập nhật đón nhận thêm tham số thứ 4: garbage_value
    new_qty, new_val, new_mac, garbage_value = MACCalculator.calculate_standard_mac(
        current_qty, current_val, import_qty, import_val
    )

    # THEN: 10.7692307... làm tròn Half Up 4 số sẽ thành 10.7692
    assert new_qty == 13
    assert new_val == Decimal('140.0000')
    assert new_mac == Decimal('10.7692')
    assert garbage_value is None  # Kho đang dương, không có rác tài chính phát sinh


def test_mac_calculate_exact_round_half_up():
    """Kiểm tra chính xác quy tắc làm tròn lên (Round Half Up) ở chữ số thứ 5"""
    # GIVEN: Cố tinh tạo ra số MAC có đuôi là ...5
    # (10.0000 + 10.0001) / 2 = 20.0001 / 2 = 10.00005
    current_qty, current_val = 1, Decimal('10.0000')
    import_qty, import_val = 1, Decimal('10.0001')

    # WHEN - Đã cập nhật đón nhận thêm tham số thứ 4: garbage_value
    new_qty, new_val, new_mac, garbage_value = MACCalculator.calculate_standard_mac(
        current_qty, current_val, import_qty, import_val
    )

    # THEN: Đuôi 5 phải được làm tròn lên thành 1
    assert new_mac == Decimal('10.0001')
    assert garbage_value is None


def test_mac_calculate_from_empty_inventory():
    """Tính MAC khi kho đang trống trơn sạch sẽ (Tồn = 0, Tiền = 0)"""
    current_qty, current_val = 0, Decimal('0')
    import_qty, import_val = 10, Decimal('50000')

    # WHEN - Đã cập nhật đón nhận thêm tham số thứ 4: garbage_value
    new_qty, new_val, new_mac, garbage_value = MACCalculator.calculate_standard_mac(
        current_qty, current_val, import_qty, import_val
    )

    assert new_qty == 10
    assert new_val == Decimal('50000.0000')
    assert new_mac == Decimal('5000.0000')
    assert garbage_value is None  # Kho bằng 0, tiền bằng 0 -> Môi trường sạch, không có rác


def test_mac_calculate_with_garbage_clearance_when_qty_zero():
    """Trường hợp A: Kho bằng 0 nhưng tiền đọng > 0, phải hốt rác và reset môi trường sạch"""
    # GIVEN: Số lượng tồn kho bằng 0 nhưng tiền còn kẹt 50.000đ (do lệch làm tròn từ các hóa đơn cũ).
    # Nhập mới 10 cái với tổng tiền thực trả là 100.000đ.
    current_qty, current_val = 0, Decimal('50000.0000')
    import_qty, import_val = 10, Decimal('100000.0000')

    # ACT
    new_qty, new_total_value, new_mac, garbage_value = MACCalculator.calculate_standard_mac(
        current_qty, current_val, import_qty, import_val
    )

    # ASSERT - Kiểm chứng thuật toán định giá thông minh
    assert garbage_value == Decimal('50000.0000')  # Nhận diện chính xác 100% lượng rác đọng
    assert new_qty == 10
    assert new_total_value == Decimal('100000.0000')  # Tiền mới phải ép về 0 trước rồi mới cộng tiền nhập mới
    assert new_mac == Decimal('10000.0000')  # MAC chuẩn = 100k / 10 cái, không bị méo mó bởi rác tài chính cũ


# ==========================================
# KỊCH BẢN THẤT BẠI (EXCEPTIONS)
# ==========================================
def test_mac_raise_error_when_inventory_is_negative():
    """Trường hợp B: Cấm tuyệt đối tính MAC khi kho đang bị âm (Chốt chặn mô hình bán khống)"""
    with pytest.raises(ValueError) as exc_info:
        MACCalculator.calculate_standard_mac(-5, Decimal('-20000'), 10, Decimal('50000'))

     Kiểm tra mã lỗi nghiệp vụ chuẩn thay vì câu chữ cũ
    assert "KHO_AM_CHAN_NGHIEP_VU" in str(exc_info.value)


def test_mac_raise_error_when_new_qty_is_zero():
    """Trường hợp C: Cấm nhập hàng nếu số lượng sau tính toán vẫn nhỏ hơn hoặc bằng 0"""
    with pytest.raises(ValueError) as exc_info:
        # Kho trống, cố tình nhập thêm 0 hoặc số âm (nếu có)
        MACCalculator.calculate_standard_mac(0, Decimal('0'), 0, Decimal('0'))

     Kiểm tra mã lỗi nghiệp vụ chuẩn thay vì câu chữ cũ
    assert "NHAP_KHO_VAN_AM_CHAN_NGHIEP_VU" in str(exc_info.value)