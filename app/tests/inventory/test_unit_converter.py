import pytest
from app.modules.inventory.utils.unit_converter import UnitConverter


# ==========================================
# TEST DATA DRIVEN (VÉT CẠN CÁC NHÁNH QUY ĐỔI)
# ==========================================
@pytest.mark.parametrize("total_qty, ratio, conv_name, base_name, expected_string", [
    # TC_UC_01: Đủ cả Sỉ và Lẻ (Dư phép chia)
    (25, 20, "Hộp", "Cây", "1 Hộp + 5 Cây"),
    (45, 20, "Hộp", "Cây", "2 Hộp + 5 Cây"),

    # TC_UC_02: Chỉ có Sỉ (Chia hết, không dư Lẻ)
    (40, 20, "Hộp", "Cây", "2 Hộp"),

    # TC_UC_03: Chỉ có Lẻ (Số lượng nhỏ hơn tỷ lệ quy đổi)
    (15, 20, "Hộp", "Cây", "15 Cây"),

    # TC_UC_04: Cạnh biên (Edge Cases - Dữ liệu rác hoặc thiếu)
    (10, 0, "Hộp", "Cây", "---"),  # Tỷ lệ = 0
    (10, None, "Hộp", "Cây", "---"),  # Không có tỷ lệ
    (10, 20, None, "Cây", "---"),  # Không có tên ĐVT quy đổi
    (10, -5, "Hộp", "Cây", "---"),  # Tỷ lệ âm (Logic rác)
])
def test_format_conversion_string(total_qty, ratio, conv_name, base_name, expected_string):
    """Vét cạn các nhánh logic tạo chuỗi quy đổi Sỉ/Lẻ"""

    # WHEN
    actual_string = UnitConverter.format_conversion_string(total_qty, ratio, conv_name, base_name)

    # THEN
    assert actual_string == expected_string