import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from app.modules.tax.dtos.tax_dto import TaxLedgerDTO, TaxLedgerDetailDTO
from app.modules.tax.repositories.impl.tax_repository_impl import TaxLedgerRepository, TaxReportRepository


# ==========================================
# FIXTURES KHỞI TẠO REPOSITORY THỰC TẾ
# ==========================================

@pytest.fixture
def tax_ledger_repo(db_test_connection):
    """Bơm connection thực tế để kiểm thử hộp đen tầng tương tác MySQL Sổ cái"""
    return TaxLedgerRepository(db_test_connection)


@pytest.fixture
def tax_report_repo(db_test_connection):
    """Bơm connection thực tế để kiểm thử các hàm View báo cáo doanh thu sống"""
    return TaxReportRepository(db_test_connection)


# =================================================================
# 1. KIỂM THỬ VÒNG ĐỜI CHỨNG TỪ MASTER (MASTER LIFECYCLE & UPSERT)
# =================================================================

def test_save_ledger_lifecycle_insert_vs_update(tax_ledger_repo, db_test_connection):
    """
    SĂN LỖI: Trùng lặp dữ liệu (Data Duplication) & Tràn khóa Master.
    KỲ VỌNG NGHIỆP VỤ:
    - Lần đầu kết xuất (Chưa có ID): Hệ thống phải INSERT bản ghi và cấp phát ID tự tăng.
    - Lần sau kết xuất đè (Đã có ID): Hệ thống phải UPDATE đè số liệu lên dòng cũ, GIỮ NGUYÊN ID gốc.
    """
    year = 2026

    # ---- HÀNH ĐỘNG 1: Kết xuất lần đầu (INSERT dòng nháp) ----
    ledger_v1 = TaxLedgerDTO(
        id=None,
        apply_year=year,
        total_revenue=Decimal('1500000000'),
        total_cost=Decimal('800000000'),
        final_vat_amount=Decimal('15000000'),
        final_pit_amount=Decimal('3500000'),
        pit_method='FLAT_RATE',
        status='DRAFT',
        threshold_amount=Decimal('1000000000'),
        vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5'),
        finalized_at=None
    )

    generated_id = tax_ledger_repo.save_ledger(ledger_v1)
    assert generated_id > 0, "LỖI: MySQL phải sinh mã ID tự tăng cho chứng từ mới."

    # ---- HÀNH ĐỘNG 2: Kết xuất đè (UPDATE dòng nháp đang mở) ----
    ledger_v2 = TaxLedgerDTO(
        id=generated_id,  # Truyền ID gốc để kích hoạt lệnh Update
        apply_year=year,
        total_revenue=Decimal('1800000000'),  # Doanh thu tăng lên do phát sinh hóa đơn mới
        total_cost=Decimal('900000000'),
        final_vat_amount=Decimal('18000000'),
        final_pit_amount=Decimal('4000000'),
        pit_method='BOOKKEEPING',  # Người dùng chủ động đổi phương pháp thuế trên UI
        status='DRAFT',
        threshold_amount=Decimal('1000000000'),
        vat_percent=Decimal('1.0'),
        pit_percent=Decimal('15.0'),  # Thuế suất tự nhảy theo luật sổ sách
        finalized_at=None
    )

    updated_id = tax_ledger_repo.save_ledger(ledger_v2)
    assert updated_id == generated_id, "LỖI KIẾN TRÚC: Kết xuất đè bản nháp phải giữ nguyên ID chứng từ, không được tạo dòng mới."

    # ---- KIỂM CHỨNG TOÀN VẸN CƠ SỞ DỮ LIỆU ĐẰNG SAU ----
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tax_ledger WHERE apply_year = %s", (year,))
    rows = cursor.fetchall()
    cursor.close()

    assert len(
        rows) == 1, "LỖI DỮ LIỆU: Phát sinh hiện tượng trùng lặp (Duplicate) chứng từ cho cùng một năm tài chính."
    assert rows[0]['total_revenue'] == Decimal('1800000000.00'), "LỖI: Số liệu doanh thu mới chưa được cập nhật đè."
    assert rows[0]['pit_method'] == 'BOOKKEEPING', "LỖI: Thông số cấu hình tích hợp ở Header chứng từ bị mất dấu vết."


# =================================================================
# 2. KIỂM THỬ RÀNG BUỘC PHÂN BỔ CHI TIẾT (DETAIL INTEGRITY & ORPHANS CLEANING)
# =================================================================

def test_save_ledger_details_purges_old_records_to_prevent_leaks(tax_ledger_repo, db_test_connection):
    """
    SĂN LỖI: Rác dữ liệu (Orphan/Ghost Records Leak).
    KỲ VỌNG HIỂN THỊ:
    - Khi người dùng bấm kết xuất đè ở Tab 1, hệ thống bắt buộc phải dọn dẹp sạch sẽ toàn bộ chi tiết 12 tháng cũ
      của dòng Master đó rồi mới nạp mảng 12 tháng mới vào.
    - Nếu không xóa sạch chi tiết cũ, bảng bên phải ở Tab 2 sẽ bị cộng dồn thành 24 tháng hoặc hiển thị sai lệch số liệu.
    """
    # 1. Thiết lập sẵn một chứng từ Master giả lập trong DB
    cursor = db_test_connection.cursor()
    cursor.execute("""
        INSERT INTO tax_ledger (apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, pit_method, status)
        VALUES (2026, 100, 50, 5, 2, 'FLAT_RATE', 'DRAFT')
    """)
    ledger_id = cursor.lastrowid

    # 2. Bơm 12 tháng dữ liệu "CŨ" vào bảng Detail
    for month in range(1, 13):
        cursor.execute("""
            INSERT INTO tax_ledger_details (tax_ledger_id, month, revenue, cost, vat_amount, pit_amount)
            VALUES (%s, %s, 1000, 500, 10, 5)
        """, (ledger_id, month))
    db_test_connection.commit()
    cursor.close()

    # 3. HÀNH ĐỘNG HỘP ĐEN: Gọi hàm Repo lưu mảng chi tiết "MỚI" (Ví dụ: Số liệu thay đổi sau khi bán thêm hàng)
    new_details = []
    for month in range(1, 13):
        new_details.append(TaxLedgerDetailDTO(
            id=None,
            tax_ledger_id=ledger_id,
            month=month,
            revenue=Decimal('2000'),  # Số doanh thu mới cập nhật
            cost=Decimal('1000'),
            vat_amount=Decimal('20'),
            pit_amount=Decimal('10')
        ))

    assert tax_ledger_repo.save_ledger_details(ledger_id, new_details) is True

    # 4. KIỂM TRÁO CHỐT CHẶN BẢO VỆ TOÀN VẸN
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tax_ledger_details WHERE tax_ledger_id = %s", (ledger_id,))
    final_rows = cursor.fetchall()
    cursor.close()

    # Chốt chặn tối cao: Tổng số dòng chi tiết của chứng từ BẮT BUỘC phải là 12, không được dôi ra dòng nào
    assert len(
        final_rows) == 12, "LỖI TRÀN DỮ LIỆU: Hàm chưa dọn dẹp (Clean) các dòng dữ liệu nháp cũ, gây rác sổ sách."
    assert final_rows[0]['revenue'] == Decimal('2000.00'), "LỖI: Dữ liệu đóng băng mới chưa được ghi đè thành công."


# =================================================================
# 3. KIỂM THỬ CHỐT CHẶN BẢO MẬT KHÓA SỔ (STATE MACHINE🔒)
# =================================================================

def test_update_ledger_status_enforces_immutability_constraints(tax_ledger_repo, db_test_connection):
    """
    SĂN LỖI: Phá vỡ tính bất biến (Immutability Bypass) / Tấn công ghi đè lịch sử.
    KỲ VỌNG BẢO MẬT ENTERPRISE:
    - Hàm chuyển trạng thái chỉ được phép thành công khi bản ghi đang ở trạng thái nháp (`status = 'DRAFT'`).
    - Nếu chứng từ năm đó ĐÃ KHÓA SỔ VĨNH VIỄN (`status = 'CLOSED'`) từ trước,
      thì dù có cố tình gọi hàm ép khóa sổ một lần nữa, MySQL phải trả về kết quả từ chối (`rowcount == 0`).
      Điều này đảm bảo mốc thời gian chốt sổ pháp lý (`finalized_at`) đầu tiên không bao giờ bị ghi đè hay thay đổi trái phép.
    """
    year = 2024

     Sử dụng .replace(microsecond=0) để đồng bộ hóa tuyệt đối định dạng lưu trữ giữa Python và MySQL
    first_lock_time = datetime.now().replace(microsecond=0) - timedelta(days=10)

    # 1. Ghi cứng một chứng từ ĐÃ KHÓA SỔ (CLOSED) vào DB
    cursor = db_test_connection.cursor()
    cursor.execute("""
        INSERT INTO tax_ledger (apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, pit_method, status, finalized_at)
        VALUES (%s, 500, 200, 5, 2, 'BOOKKEEPING', 'CLOSED', %s)
    """, (year, first_lock_time))
    db_test_connection.commit()
    cursor.close()

    # 2. HÀNH ĐỘNG TẤN CÔNG: Cố tình gọi hàm yêu cầu cập nhật lại trạng thái chốt sổ một lần nữa
    malicious_re_lock_time = datetime.now()
    is_success = tax_ledger_repo.update_ledger_status(year, 'CLOSED', malicious_re_lock_time)

    # 3. KIỂM CHỨNG CHỐT CHẶN
    assert is_success is False, "LỖI BẢO MẬT CHÍ MẠNG: Hệ thống cho phép cập nhật đè trạng thái chứng từ đã đóng sổ vĩnh viễn!"

    # Kiểm tra vết thời gian dưới DB xem có bị thay đổi không
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("SELECT finalized_at FROM tax_ledger WHERE apply_year = %s", (year,))
    record = cursor.fetchone()
    cursor.close()

    # Dấu vết thời gian quyết toán gốc phải giữ nguyên bất biến tuyệt đối
    assert record['finalized_at'] == first_lock_time, "LỖI: Mốc thời gian quyết toán pháp lý bị phá hủy trái phép."

# =================================================================
# 4. KIỂM THỬ KỲ VỌNG HIỂN THỊ TRÊN GIAO DIỆN (UI RENDER ORDERING)
# =================================================================

def test_get_all_ledgers_guarantees_strict_descending_chronological_order(tax_ledger_repo, db_test_connection):
    """
    KỲ VỌNG HIỂN THỊ (BẢNG DANH SÁCH BÊN TRÁI TAB 2):
    - Khi người dùng mở Nhật ký sổ cái, danh sách các năm bắt buộc phải sắp xếp theo thứ tự **Năm mới nhất nằm trên cùng** (Chính là `ORDER BY apply_year DESC`).
    - Lỗi đảo lộn thứ tự hiển thị sẽ khiến kế toán nhìn nhầm dòng bản ghi giữa các năm tài chính.
    """
    cursor = db_test_connection.cursor()
    # Chèn lộn xộn các năm vào database
    cursor.execute(
        "INSERT INTO tax_ledger (apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, pit_method, status) VALUES (2024, 0, 0, 0, 0, 'FLAT_RATE', 'CLOSED')")
    cursor.execute(
        "INSERT INTO tax_ledger (apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, pit_method, status) VALUES (2026, 0, 0, 0, 0, 'FLAT_RATE', 'DRAFT')")
    cursor.execute(
        "INSERT INTO tax_ledger (apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, pit_method, status) VALUES (2025, 0, 0, 0, 0, 'FLAT_RATE', 'CLOSED')")
    db_test_connection.commit()
    cursor.close()

    # HÀNH ĐỘNG HỘP ĐEN
    ledgers = tax_ledger_repo.get_all_ledgers()

    # KIỂM CHỨNG THỨ TỰ CANH LỀ HIỂN THỊ
    assert ledgers[0].apply_year == 2026, "LỖI UI: Năm mới nhất không được đẩy lên trên cùng bảng danh sách."
    assert ledgers[1].apply_year == 2025
    assert ledgers[2].apply_year == 2024


def test_get_ledger_details_guarantees_strict_ascending_monthly_order(tax_ledger_repo, db_test_connection):
    """
    KỲ VỌNG HIỂN THỊ (BẢNG CHI TIẾT BÊN PHẢI TAB 2):
    - Khi người dùng click chọn dòng Master, bảng chi tiết 12 tháng bắt buộc phải hiển thị thẳng hàng tuần tiến từ **Tháng 1 đến Tháng 12** (`ORDER BY month ASC`).
    - Nếu MySQL trả về mảng lộn xộn (ví dụ Tháng 5 hiện trước Tháng 1), layout đồ họa trên UI sẽ bị rách và hiển thị sai lệch dòng thời gian.
    """
    cursor = db_test_connection.cursor()
    cursor.execute(
        "INSERT INTO tax_ledger (apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, pit_method, status) VALUES (2026, 0, 0, 0, 0, 'FLAT_RATE', 'DRAFT')")
    ledger_id = cursor.lastrowid

    # Chèn dữ liệu tháng lộn xộn vào DB (Chèn tháng 12 trước rồi mới chèn tháng 1)
    cursor.execute(
        "INSERT INTO tax_ledger_details (tax_ledger_id, month, revenue, cost, vat_amount, pit_amount) VALUES (%s, 12, 0, 0, 0, 0)",
        (ledger_id,))
    cursor.execute(
        "INSERT INTO tax_ledger_details (tax_ledger_id, month, revenue, cost, vat_amount, pit_amount) VALUES (%s, 1, 0, 0, 0, 0)",
        (ledger_id,))
    db_test_connection.commit()
    cursor.close()

    # HÀNH ĐỘNG HỘP ĐEN
    details = tax_ledger_repo.get_ledger_details(ledger_id)

    # KIỂM CHỨNG THỨ TỰ TUẦN TIẾN ĐỒ HỌA
    assert details[
               0].month == 1, "LỖI HIỂN THỊ: Các tháng không tự động sắp xếp tuần tiến từ nhỏ đến lớn trên Grid bảng biểu."
    assert details[1].month == 12