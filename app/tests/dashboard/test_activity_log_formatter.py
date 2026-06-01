import pytest
import datetime
from app.modules.dashboard.dtos.activity_log_dto import ActivityLogDTO
from app.modules.dashboard.utils.activity_log_formatter import ActivityLogFormatter


@pytest.mark.parametrize("action_type, ref_code, desc, expected_prefix", [
    ("SALE", "HD-01", "Bán lẻ", "🛒 Hóa đơn #HD-01"),
    ("CANCEL_SALE", "HD-02", "Hủy đơn", "❌ HỦY HÓA ĐƠN #HD-02"),
    ("IMPORT", "PO-01", "Nhập giấy", "📦 Phiếu nhập #PO-01"),
    ("CANCEL_IMPORT", "PO-02", "Hủy phiếu", "🗑️ HỦY PHIẾU NHẬP #PO-02"),
    ("SYSTEM", "CFG", "Đổi PIN", "🔔 Hệ thống #CFG"),
    ("UNKNOWN_CODE", None, "Biến động", "📝 Sự kiện | Biến động"),
])
def test_should_compile_exact_emoji_and_metadata_variants(action_type, ref_code, desc, expected_prefix):
    """ Vét sạch các nhánh định dạng văn bản hiển thị lên danh sách UI"""
    log_dto = ActivityLogDTO(
        id=1, action_type=action_type, reference_code=ref_code,
        description=desc, created_at=datetime.datetime(2026, 5, 29, 12, 0, 0)
    )
    ui_string = ActivityLogFormatter.format_to_ui_string(log_dto)

    assert "[12:00:00]" in ui_string
    assert expected_prefix in ui_string