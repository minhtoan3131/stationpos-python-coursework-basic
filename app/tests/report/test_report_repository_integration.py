import pytest
from decimal import Decimal
from app.modules.report.repositories.impl.report_repository_impl import ReportRepositoryImpl


# ==========================================
# BÀI TEST TÍCH HỢP SỬ DỤNG HẠ TẦNG GỐC DỰ ÁN
# ==========================================
def test_repository_sql_execution_with_real_db(db_test_connection):
    """
    Mũi khoan sâu nhất: Sử dụng trực tiếp db_test_connection từ conftest.py.
    Bơm data vật lý vào DB thật để kiểm chứng SQL thô và Database Views (vw_report_...).
    """
    # Khởi tạo một cursor độc lập để thực hiện nhiệm vụ Seed dữ liệu mồi (GIVEN)
    seed_cursor = db_test_connection.cursor(dictionary=True)

    # --- GIVEN: Seed dữ liệu mồi vào các bảng cơ sở ---
    # 1. Đơn vị tính và Sản phẩm
    seed_cursor.execute("INSERT INTO units (id, name) VALUES (1, 'Cây'), (2, 'Cuốn');")
    seed_cursor.execute("""
        INSERT INTO products (id, sku, name, base_unit_id, cost_price) 
        VALUES (10, 'SP01', 'Bút bi Thiên Long', 1, 4000.0000);
    """)
    # 2. Tồn kho hiện tại
    seed_cursor.execute("INSERT INTO inventory (product_id, quantity, total_value) VALUES (10, 150, 600000.0000);")

    # 3. Hóa đơn hợp lệ ('COMPLETED') và Hóa đơn bị hủy ('CANCELLED') để kiểm tra bộ lọc của View
    seed_cursor.execute("""
        INSERT INTO invoices (id, code, created_at, total_amount, discount, final_amount, payment_method, status)
        VALUES 
        (1, 'HD_OK', '2026-05-16 10:00:00', 150000.00, 10000.00, 140000.00, 'CASH', 'COMPLETED'),
        (2, 'HD_ERR', '2026-05-16 11:00:00', 500000.00, 0.00, 500000.00, 'TRANSFER', 'CANCELLED');
    """)
    # 4. Chi tiết hóa đơn để View tính ra tổng giá vốn (COGS) và Lợi nhuận gộp
    seed_cursor.execute("""
        INSERT INTO invoice_items (invoice_id, product_id, unit_id, quantity, cost_price, unit_price, total_price)
        VALUES (1, 10, 1, 10, 4000.0000, 15000.0000, 150000.0000);
    """)
    db_test_connection.commit()
    seed_cursor.close()  # Đóng cursor seed sau khi hoàn thành nhiệm vụ chuẩn bị data

    # --- ACT: Khởi tạo Repo thật bằng cách truyền vào connection thật ---
    # BaseRepository sẽ tự tạo thuộc tính self.connection và self.cursor bên trong repo object
    repo = ReportRepositoryImpl(db_test_connection)

    # --- THEN: Thực thi kiểm thử hàm lấy KPI ---
    kpis = repo.get_kpi_metrics("2026-05-16", "2026-05-16")

    # Hóa đơn HD_ERR bị hủy trạng thái 'CANCELLED' -> View bắt buộc phải lọc bỏ ra ngoài
    assert kpis["total_orders"] == 1
    # Doanh thu hóa đơn HD_OK sau khi trừ chiết khấu phải là 140,000 VND
    assert kpis["total_revenue"] == Decimal("140000.00")
    # Lợi nhuận gộp = Doanh thu (140,000) - Giá vốn (10 cây x 4,000đ = 40,000đ) = 100,000đ
    assert kpis["total_profit"] == Decimal("100000.00")
    # Giá trị tồn kho Snapshot: 150 cây x 4,000đ = 600,000đ
    assert kpis["total_stock_value"] == Decimal("600000.00")

    # --- THEN: Kiểm thử hàm lịch sử giao dịch ---
    history = repo.get_transaction_history("2026-05-16", "2026-05-16")
    assert len(history) == 1
    assert history[0]["invoice_code"] == "HD_OK"
    # Đảm bảo mệnh đề CASE WHEN dưới View DB đã dịch chính xác ngôn ngữ sang Tiếng Việt
    assert history[0]["payment_method"] == "Tiền mặt"