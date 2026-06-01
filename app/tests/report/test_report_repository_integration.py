# File: app/tests/report/test_report_repository_integration.py
import pytest
from datetime import datetime, date
from decimal import Decimal
from app.modules.report.repositories.impl.report_repository_impl import ReportRepositoryImpl


# =========================================================================
# BÀI TEST TÍCH HỢP
# =========================================================================

def test_repository_sql_execution_with_real_db(db_test_connection):
    """
    Sử dụng trực tiếp db_test_connection từ conftest.py.
    Bơm data vật lý vào DB thật để kiểm chứng SQL thô và 8 chỉ số tài chính phát sinh từ View daily summary.
    """
    # Khởi tạo một cursor độc lập để thực hiện nhiệm vụ Seed dữ liệu mồi (GIVEN)
    seed_cursor = db_test_connection.cursor(dictionary=True)

    # --- GIVEN: Seed dữ liệu mồi vào các bảng cơ sở ---
    seed_cursor.execute("INSERT INTO units (id, name) VALUES (1, 'Cây'), (2, 'Cuốn');")
    seed_cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'Văn phòng phẩm');")

    seed_cursor.execute("""
        INSERT INTO products (id, sku, name, category_id, base_unit_id, cost_price) 
        VALUES (10, 'SP01', 'Bút bi Thiên Long', 1, 1, 4000.0000);
    """)

    seed_cursor.execute("INSERT INTO inventory (product_id, quantity, total_value) VALUES (10, 150, 600000.0000);")

    seed_cursor.execute("""
        INSERT INTO invoices (id, code, created_at, total_amount, discount, final_amount, payment_method, status)
        VALUES 
        (1, 'HD_OK', '2026-05-16 10:00:00', 150000.00, 10000.00, 140000.00, 'CASH', 'COMPLETED'),
        (2, 'HD_ERR', '2026-05-16 11:00:00', 500000.00, 0.00, 500000.00, 'TRANSFER', 'CANCELLED');
    """)

    seed_cursor.execute("""
        INSERT INTO invoice_items (invoice_id, product_id, unit_id, quantity, cost_price, unit_price, total_price, total_cogs_amount)
        VALUES (1, 10, 1, 10, 4000.0000, 15000.0000, 150000.0000, 40000.0000);
    """)

    seed_cursor.execute("""
        INSERT INTO invoices (id, code, created_at, total_amount, discount, final_amount, payment_method, status, cancel_reason)
        VALUES (3, 'HD_RETURNED_L4', '2026-05-16 14:20:00', 30000.00, 0.00, 30000.00, 'CASH', 'CANCELLED', 'Khách đổi trả hàng');
    """)

    seed_cursor.execute("""
        INSERT INTO stock_transactions (product_id, change_quantity, type, variance_amount, note, reference_id, created_at)
        VALUES (10, 0, 'DATA_CORRECTION', -5000.0000, 'Điều chỉnh dọn rác giá trị tồn đọng khi kho trống', 1, '2026-05-16 15:30:00');
    """)

    db_test_connection.commit()
    seed_cursor.close()

    # --- ACT: Khởi tạo Repo thật bằng cách truyền vào connection thật ---
    repo = ReportRepositoryImpl(db_test_connection)

    # --- THEN: Thực thi kiểm thử hàm lấy chỉ số KPIs tổng quan ---
    kpis = repo.get_kpi_metrics("2026-05-16", "2026-05-16")

    # Kiểm toán chi tiết bộ lọc số lượng đơn hàng theo cấu trúc chuẩn 8 chỉ số mới trên UI
    assert kpis["total_orders_created"] == 3      # 1 Completed + 2 Cancelled
    assert kpis["total_orders_completed"] == 1    # Chỉ có đơn HD_OK
    assert kpis["total_orders_cancelled"] == 2    # Gồm HD_ERR và HD_RETURNED_L4

    # Kiểm toán đối soát dòng tiền doanh thu thô và doanh thu thuần thực thu
    assert float(kpis["gross_revenue"]) == 680000.0   # Gross = 150k + 500k + 30k
    assert float(kpis["cancelled_value"]) == 530000.0 # Cancelled = 500k + 30k
    assert float(kpis["net_revenue"]) == 150000.0     # Net = 680k - 530k = 150k (Doanh thu thuần tuyệt đối không âm)

    # Kiểm toán chi phí giá vốn và các mốc lợi nhuận sạch rác tài chính phát sinh trong ngày
    assert float(kpis["total_cogs"]) == 40000.0       # Tổng COGS của các đơn COMPLETED
    assert float(kpis["gross_profit"]) == 110000.0    # Gross Profit = Net (150k) - COGS (40k)
    assert float(kpis["variance_garbage"]) == -5000.0 # Tiền rác kho hạch toán lùi từ sổ cái
    assert float(kpis["net_profit"]) == 105000.0      # Net Profit = Gross (110k) + Variance (-5k)

    # CHỐT CHẶN: Hoàn toàn không lấy hay so khớp 'total_stock_value' ở đây nữa!

    # --- THEN: Kiểm thử hàm truy vấn lịch sử giao dịch hóa đơn ---
    history = repo.get_transaction_history("2026-05-16", "2026-05-16")
    assert len(history) == 1
    assert history[0]["invoice_code"] == "HD_OK"
    assert history[0]["payment_method"] == "Tiền mặt"


def test_sql_get_daily_purchase_orders_returns_completed_only(db_test_connection):
    """Test màn Home: Nhật ký nạp hoạt động phiếu nhập trong ngày."""
    seed_cursor = db_test_connection.cursor(dictionary=True)
    seed_cursor.execute("INSERT INTO suppliers (id, name, phone, address) VALUES (1, 'NCC Thiên Long', '0987654321', 'Hà Nội');")

    seed_cursor.execute("""
        INSERT INTO purchase_orders (id, code, supplier_id, total_amount, note, status, created_at) 
        VALUES (1, 'PO-001', 1, 1500000.0000, 'Nhập hàng', 'COMPLETED', '2026-05-17 14:30:00');
    """)
    seed_cursor.execute("""
        INSERT INTO purchase_orders (id, code, supplier_id, total_amount, note, status, created_at) 
        VALUES (2, 'PO-002', 1, 2000000.0000, 'Nháp', 'CANCELLED', '2026-05-17 15:00:00');
    """)
    seed_cursor.execute("""
        INSERT INTO purchase_orders (id, code, supplier_id, total_amount, note, status, created_at) 
        VALUES (3, 'PO-003', 1, 5000000.0000, 'Hàng hôm qua', 'COMPLETED', '2026-05-16 10:00:00');
    """)
    db_test_connection.commit()
    seed_cursor.close()

    repo = ReportRepositoryImpl(db_test_connection)
    results = repo.get_daily_purchase_orders("2026-05-17")

    assert len(results) == 1
    assert results[0]['code'] == 'PO-001'
    assert results[0]['supplier_name'] == 'NCC Thiên Long'
    assert results[0]['total_amount'] == Decimal("1500000.0000")
    assert isinstance(results[0]['created_at'], datetime)