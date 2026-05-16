import pytest
from datetime import date as real_date  # Đổi tên để không trùng với mock
from app.modules.report.utils.date_helper import DateHelper


def test_date_helper_ranges(mocker):
    """Kiểm chứng xem toán học ngày tháng trả ra khoảng chuỗi chuẩn xác hay không."""
    # GIVEN: Khống chế lớp date của module đích
    mock_date = mocker.patch("app.modules.report.utils.date_helper.date")

    # 1. Cố định giá trị trả về của hàm .today() thành ngày thật 16/05/2026
    mock_date.today.return_value = real_date(2026, 5, 16)

    # 2. Cấu hình "đóng vai": Khi gọi date(year, month, day), trả về đối tượng date thật
    mock_date.side_effect = lambda *args, **kwargs: real_date(*args, **kwargs)

    # ==========================================
    # ACT & THEN: THỰC THI KIỂM CHỨNG THEO HỘP ĐEN
    # ==========================================

    # 1. Kiểm tra khoảng ngày hôm nay
    today_start, today_end = DateHelper.get_today_range()
    assert today_start == "2026-05-16"
    assert today_end == "2026-05-16"

    # 2. Kiểm tra khoảng ngày hôm qua (16 - 1 = 15)
    yesterday_start, yesterday_end = DateHelper.get_yesterday_range()
    assert yesterday_start == "2026-05-15"
    assert yesterday_end == "2026-05-15"

    # 3. Kiểm tra khoảng tháng này (Từ mùng 1 đầu tháng đến hôm nay)
    month_start, month_end = DateHelper.get_this_month_range()
    assert month_start == "2026-05-01"
    assert month_end == "2026-05-16"