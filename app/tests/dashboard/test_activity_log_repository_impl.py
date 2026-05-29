# app/tests/dashboard/test_activity_log_repository_impl.py
import pytest
from app.modules.dashboard.repositories.impl.activity_log_repository_impl import ActivityLogRepositoryImpl


# ==========================================
# FIXTURE KHỞI TẠO REPO DÀNH RIÊNG CHO DASHBOARD
# ==========================================
@pytest.fixture
def log_repo(db_test_connection):
    """Khởi tạo Repository thực tế kế thừa từ BaseRepository"""
    return ActivityLogRepositoryImpl(db_test_connection)


# ==========================================
# TEST CASES
# ==========================================

def test_add_log_stores_activity_successfully(log_repo, db_test_connection):
    """Kiểm tra câu lệnh SQL INSERT lưu vết biến động sự kiện thành công"""

    # ACT - Thực thi hành động ghi dữ liệu qua repo
    log_repo.add_log(action_type="SALE", reference_code="HD-100", description="Kiểm thử câu lệnh SQL")
    db_test_connection.commit()

    # ASSERT - Sử dụng fetchall() đồng bộ 100% với phong cách các repo khác
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM activity_logs WHERE reference_code = 'HD-100'")
    logs = cursor.fetchall()
    cursor.close()

    assert len(logs) == 1
    assert logs[0]['action_type'] == "SALE"
    assert logs[0]['description'] == "Kiểm thử câu lệnh SQL"
    assert logs[0]['created_at'] is not None


def test_get_logs_by_date_returns_ordered_results(log_repo, db_test_connection):
    """Kiểm tra hàm SELECT truy vấn danh sách log theo ngày và sắp xếp mới nhất lên đầu"""

    # GIVEN - Mồi dữ liệu thô thẳng xuống DB, giả lập thời gian tạo lệch nhau
    cursor = db_test_connection.cursor()
    cursor.execute(
        "INSERT INTO activity_logs (action_type, reference_code, description, created_at) "
        "VALUES ('IMPORT', 'PO-01', 'Nhập sách sỉ', '2026-05-29 10:00:00')"
    )
    cursor.execute(
        "INSERT INTO activity_logs (action_type, reference_code, description, created_at) "
        "VALUES ('CANCEL_IMPORT', 'PO-02', 'Hủy nhập kho', '2026-05-29 11:00:00')"
    )
    db_test_connection.commit()
    cursor.close()

    # ACT - Gọi hàm của Repository để quét lịch sử ngày hôm nay
    results = log_repo.get_logs_by_date("2026-05-29")

    # ASSERT - Đảm bảo kết quả trả về đúng định dạng DTO sạch và xếp chuẩn thời gian giảm dần (DESC)
    assert len(results) == 2

    # Bản ghi tạo lúc 11:00 (Mới hơn) bắt buộc phải đứng đầu danh sách
    assert results[0].reference_code == "PO-02"
    assert results[0].action_type == "CANCEL_IMPORT"
    assert results[0].description == "Hủy nhập kho"

    # Bản ghi tạo lúc 10:00 (Cũ hơn) đứng ở vị trí tiếp theo
    assert results[1].reference_code == "PO-01"
    assert results[1].action_type == "IMPORT"
    assert results[1].description == "Nhập sách sỉ"