import pytest
from decimal import Decimal
from app.modules.tax.dtos.tax_dto import TaxConfigDTO
from app.modules.tax.repositories.impl.tax_repository_impl import TaxConfigRepository, TaxReportRepository


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def tax_config_repo(db_test_connection):
    """Khởi tạo Repo thật với connection từ conftest"""
    return TaxConfigRepository(db_test_connection)


@pytest.fixture
def tax_report_repo(db_test_connection):
    """Khởi tạo Repo thật với connection từ conftest"""
    return TaxReportRepository(db_test_connection)


def test_sql_upsert_tax_config_works_correctly(tax_config_repo, db_test_connection):
    """
    Kỳ vọng:
    Lần 1: Gọi save -> Phải thực hiện INSERT bản ghi mới.
    Lần 2: Gọi save với cùng số NĂM -> Phải thực hiện UPDATE đè lên bản ghi cũ (Không đẻ thêm dòng mới).
    """
    year = 2026

    # ----------------------------------------
    # HÀNH ĐỘNG 1: INSERT (Lần đầu tiên cấu hình)
    # ----------------------------------------
    config_v1 = TaxConfigDTO(
        apply_year=year,
        threshold_amount=Decimal('1000'),
        vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5')
    )

    assert tax_config_repo.save_config(config_v1) is True

    # Kiểm tra dưới DB thật
    saved_v1 = tax_config_repo.get_config_by_year(year)
    assert saved_v1.threshold_amount == Decimal('1000.00')
    original_id = saved_v1.id

    # ----------------------------------------
    # HÀNH ĐỘNG 2: UPDATE (Thay đổi thông số năm 2026)
    # ----------------------------------------
    config_v2 = TaxConfigDTO(
        apply_year=year,
        threshold_amount=Decimal('5000'),
        vat_percent=Decimal('2.0'),
        pit_percent=Decimal('1.0')
    )

    assert tax_config_repo.save_config(config_v2) is True

    # ----------------------------------------
    # KIỂM CHỨNG TRẠNG THÁI CUỐI (Trực tiếp bằng SQL)
    # ----------------------------------------
    cursor = db_test_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tax_config WHERE apply_year = 2026")
    rows = cursor.fetchall()
    cursor.close()

    # BẮT BUỘC chỉ có 1 dòng, không bị trùng lặp dữ liệu
    assert len(rows) == 1
    # BẮT BUỘC ID phải giữ nguyên (Là Update, không phải Delete-Insert)
    assert rows[0]['id'] == original_id
    # Dữ liệu phải là dữ liệu mới
    assert rows[0]['threshold_amount'] == Decimal('5000.00')



def test_sql_view_calculates_monthly_revenue_correctly(tax_report_repo, db_test_connection):
    """
    Kỳ vọng: Lệnh SELECT từ vw_report_invoice_summary phải GROUP BY đúng theo tháng
    và CHỈ CỘNG TIỀN của những hóa đơn có trạng thái 'COMPLETED'.
    """
    # 1. ARRANGE: Bơm dữ liệu thô thẳng vào bảng 'invoices'
    cursor = db_test_connection.cursor()

    # Tháng 1/2026: Có 2 hóa đơn thành công (Tổng = 150k)
    cursor.execute("""
            INSERT INTO invoices (code, created_at, total_amount, final_amount, status) 
            VALUES 
            ('INV-01', '2026-01-10', 100000, 100000, 'COMPLETED'),
            ('INV-02', '2026-01-25', 50000, 50000, 'COMPLETED')
        """)

    # Tháng 2/2026: 1 hóa đơn thành công (200k) và 1 hóa đơn HỦY (500k - phải bị bỏ qua)
    cursor.execute("""
            INSERT INTO invoices (code, created_at, total_amount, final_amount, status) 
            VALUES 
            ('INV-03', '2026-02-05', 200000, 200000, 'COMPLETED'),
            ('INV-04', '2026-02-20', 500000, 500000, 'CANCELLED')
        """)

    # Tháng 12/2025: Khác năm (phải bị lọc bỏ)
    cursor.execute("""
            INSERT INTO invoices (code, created_at, total_amount, final_amount, status) 
            VALUES ('INV-05', '2025-12-31', 999999, 999999, 'COMPLETED')
        """)

    db_test_connection.commit()
    cursor.close()

    # 2. ACT: Gọi hàm Repo để query qua View
    revenues = tax_report_repo.get_monthly_revenue_by_year(2026)

    # 3. ASSERT: Kiểm chứng SQL View chạy đúng logic gom nhóm và lọc
    assert len(revenues) == 2  # Chỉ có dữ liệu của 2 tháng (Tháng 1 và Tháng 2)

    # Kiểm chứng Tháng 1
    assert revenues[0].month == 1
    assert revenues[0].revenue == Decimal('150000.00')  # 100k + 50k

    # Kiểm chứng Tháng 2
    assert revenues[1].month == 2
    assert revenues[1].revenue == Decimal('200000.00')  # Chỉ lấy 200k, phớt lờ 500k của CANCELLED