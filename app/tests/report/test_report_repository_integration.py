import pytest
from datetime import datetime, date
from decimal import Decimal
from app.modules.report.repositories.impl.report_repository_impl import ReportRepositoryImpl


# =========================================================================
# BÀI TEST TÍCH HỢP SỬ DỤNG HẠ TẦNG GỐC DỰ ÁN (MŨI KHOAN SÂU TRÊN DB THẬT)
# =========================================================================

def test_repository_sql_execution_with_real_db(db_test_connection):
    """
    Mũi khoan sâu nhất: Sử dụng trực tiếp db_test_connection từ conftest.py.
    Bơm data vật lý vào DB thật để kiểm chứng SQL thô và Database Views (vw_report_...).

    RÀNG BUỘC KIỂM TOÁN MỚI (LUỒNG 4 & LUỒNG 1):
    - Doanh thu thuần tổng đài KPIs bắt buộc phải lấy tổng doanh thu hoàn thành TRỪ ĐI
      số tiền mặt đã hoàn trả cho khách hàng từ các hóa đơn bị hủy (Luồng 4).
    - Lợi nhuận thuần bắt buộc phải tính cả phần điều chỉnh rác tài chính (DATA_CORRECTION)
      đã triệt tiêu ra ánh sáng từ sổ cái (Luồng 1).
    """
    # Khởi tạo một cursor độc lập để thực hiện nhiệm vụ Seed dữ liệu mồi (GIVEN)
    seed_cursor = db_test_connection.cursor(dictionary=True)

    # --- GIVEN: Seed dữ liệu mồi vào các bảng cơ sở ---
    # 1. Đơn vị tính và Danh mục sản phẩm
    seed_cursor.execute("INSERT INTO units (id, name) VALUES (1, 'Cây'), (2, 'Cuốn');")
    seed_cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'Văn phòng phẩm');")

    # 2. Chi tiết danh mục sản phẩm (Độc lập giá vốn MAC ban đầu = 4.000đ)
    seed_cursor.execute("""
        INSERT INTO products (id, sku, name, category_id, base_unit_id, cost_price) 
        VALUES (10, 'SP01', 'Bút bi Thiên Long', 1, 1, 4000.0000);
    """)

    # 3. Két sắt số dư tồn kho hiện tại (Snapshot thời gian thực)
    seed_cursor.execute("INSERT INTO inventory (product_id, quantity, total_value) VALUES (10, 150, 600000.0000);")

    # 4. Hóa đơn hợp lệ ('COMPLETED') và Hóa đơn bị hủy ('CANCELLED') của ngày 16/05 để kiểm tra bộ lọc
    # - HD_OK: Doanh thu thực nhận sau giảm giá là 140.000đ
    seed_cursor.execute("""
        INSERT INTO invoices (id, code, created_at, total_amount, discount, final_amount, payment_method, status)
        VALUES 
        (1, 'HD_OK', '2026-05-16 10:00:00', 150000.00, 10000.00, 140000.00, 'CASH', 'COMPLETED'),
        (2, 'HD_ERR', '2026-05-16 11:00:00', 500000.00, 0.00, 500000.00, 'TRANSFER', 'CANCELLED');
    """)

    # 5. Chi tiết hóa đơn (Line Items) để View tính ra tổng giá vốn (COGS) và Lợi nhuận gộp ban đầu
    # Số lượng bán = 10 cây, giá vốn chốt snapshot = 4.000đ -> Tổng COGS chốt = 40.000đ
    seed_cursor.execute("""
        INSERT INTO invoice_items (invoice_id, product_id, unit_id, quantity, cost_price, unit_price, total_price, total_cogs_amount)
        VALUES (1, 10, 1, 10, 4000.0000, 15000.0000, 150000.0000, 40000.0000);
    """)

    # 6. BƠM DỮ LIỆU LUỒNG 4 NÂNG CAO: Chèn thêm 1 hóa đơn bị CANCELLED phát sinh đúng ngày 16/05
    # Hóa đơn này trị giá 30.000đ tiền mặt trả lại cho khách do trả hàng
    seed_cursor.execute("""
        INSERT INTO invoices (id, code, created_at, total_amount, discount, final_amount, payment_method, status, cancel_reason)
        VALUES (3, 'HD_RETURNED_L4', '2026-05-16 14:20:00', 30000.00, 0.00, 30000.00, 'CASH', 'CANCELLED', 'Khách đổi trả hàng');
    """)

    # 7. BƠM DỮ LIỆU LUỒNG 1 NÂNG CAO: Chèn thêm 1 dòng bút toán dọn rác tài chính phát sinh đúng ngày 16/05
    # Bản ghi log DATA_CORRECTION triệt tiêu khoản rác kế toán dư thừa làm giảm -5.000đ lợi nhuận
    seed_cursor.execute("""
        INSERT INTO stock_transactions (product_id, change_quantity, type, variance_amount, note, reference_id, created_at)
        VALUES (10, 0, 'DATA_CORRECTION', -5000.0000, 'Điều chỉnh dọn rác giá trị tồn đọng khi kho trống', 1, '2026-05-16 15:30:00');
    """)

    db_test_connection.commit()
    seed_cursor.close()  # Đóng kết nối tạm thời

    # --- ACT: Khởi tạo Repo thật bằng cách truyền vào connection thật ---
    repo = ReportRepositoryImpl(db_test_connection)

    # --- THEN: Thực thi kiểm thử hàm lấy chỉ số KPIs tổng quan ---
    kpis = repo.get_kpi_metrics("2026-05-16", "2026-05-16")

    # Kiểm tra bộ lọc số hóa đơn: Chỉ đếm các hóa đơn ở trạng thái COMPLETED thực sự
    # Hóa đơn HD_ERR và HD_RETURNED_L4 dính trạng thái CANCELLED -> View/Repo bắt buộc phải loại bỏ không tính vào tổng đơn
    assert kpis["total_orders"] == 1

    # Kiểm tra tính toán Doanh thu thuần thực tế tại quầy tiền mặt:
    # Doanh thu COMPLETED (140.000đ) - Tiền hoàn trả khách CANCELLED Luồng 4 (30.000đ) = 110.000đ
    assert kpis["total_revenue"] == Decimal("110000.00")

    # Kiểm tra tính toán Lợi nhuận thuần sạch rác kế toán:
    # Lợi nhuận gộp gốc = Doanh thu COMPLETED (140.000đ) - COGS (40.000đ) = 100.000đ
    # Lợi nhuận thuần = Lợi nhuận gộp gốc (100.000đ) + Tiền rác triệt tiêu Luồng 1 (-5.000đ) = 95.000đ
    assert kpis["total_profit"] == Decimal("95000.00")

    # Giá trị tồn kho Snapshot thời gian thực: 150 cây x 4.000đ = 600.000đ (Bất biến với bộ lọc ngày)
    assert kpis["total_stock_value"] == Decimal("600000.00")

    # --- THEN: Kiểm thử hàm truy vấn lịch sử giao dịch hóa đơn ---
    history = repo.get_transaction_history("2026-05-16", "2026-05-16")
    # View vw_report_transaction_history chỉ quét qua hóa đơn COMPLETED
    assert len(history) == 1
    assert history[0]["invoice_code"] == "HD_OK"
    # Đảm bảo mệnh đề CASE WHEN dưới View DB đã dịch chính xác ngôn ngữ sang Tiếng Việt chuẩn
    assert history[0]["payment_method"] == "Tiền mặt"


# =========================================================================
# BÀI TEST TÍCH HỢP CHO HÀM MỚI (PHẦN TRANG CHỦ FEED HOẠT ĐỘNG)
# =========================================================================

def test_sql_get_daily_purchase_orders_returns_completed_only(db_test_connection):
    """
    Test cho màn Home: Lấy danh sách phiếu nhập kho trong ngày.
    Ràng buộc:
    1. Chỉ lấy phiếu có status = 'COMPLETED' và khớp đúng ngày truyền vào.
    2. SQL LEFT JOIN phải liên kết và lấy ra đúng tên nhà cung cấp từ bảng suppliers.
    """
    seed_cursor = db_test_connection.cursor(dictionary=True)

    # --- GIVEN: Seed dữ liệu mồi vào các bảng cơ sở ---
    # Tạo Nhà cung cấp (Để test mệnh đề LEFT JOIN)
    seed_cursor.execute(
        "INSERT INTO suppliers (id, name, phone, address) VALUES (1, 'NCC Thiên Long', '0987654321', 'Hà Nội');"
    )

    # Tạo Phiếu số 1: HỢP LỆ (Đúng ngày 17/05, trạng thái COMPLETED)
    seed_cursor.execute("""
        INSERT INTO purchase_orders (id, code, supplier_id, total_amount, note, status, created_at) 
        VALUES (1, 'PO-001', 1, 1500000.0000, 'Nhập hàng', 'COMPLETED', '2026-05-17 14:30:00');
    """)

    # Tạo Phiếu số 2: KHÔNG HỢP LỆ (Đúng ngày 17/05, nhưng trạng thái CANCELLED) -> Sẽ bị loại bỏ khỏi luồng trang chủ
    seed_cursor.execute("""
        INSERT INTO purchase_orders (id, code, supplier_id, total_amount, note, status, created_at) 
        VALUES (2, 'PO-002', 1, 2000000.0000, 'Nháp', 'CANCELLED', '2026-05-17 15:00:00');
    """)

    # Tạo Phiếu số 3: KHÔNG HỢP LỆ (Trạng thái COMPLETED, nhưng của ngày hôm qua 16/05) -> Sẽ bị loại bỏ khỏi luồng ngày 17/05
    seed_cursor.execute("""
        INSERT INTO purchase_orders (id, code, supplier_id, total_amount, note, status, created_at) 
        VALUES (3, 'PO-003', 1, 5000000.0000, 'Hàng hôm qua', 'COMPLETED', '2026-05-16 10:00:00');
    """)

    db_test_connection.commit()
    seed_cursor.close()  # Đóng cursor seed

    # --- ACT: Khởi tạo Repo thật bằng cách truyền vào connection thật ---
    repo = ReportRepositoryImpl(db_test_connection)

    # --- THEN: Thực thi kiểm thử hàm lấy Phiếu nhập kho trong ngày ---
    target_date = "2026-05-17"
    results = repo.get_daily_purchase_orders(target_date)

    # Phải chỉ có duy nhất 1 phiếu nhập kho (PO-001) vượt qua được mệnh đề bộ lọc WHERE của SQL
    assert len(results) == 1, "Lỗi SQL: Không lọc đúng trạng thái 'COMPLETED' hoặc sai ngày lọc."

    row = results[0]

    # Kiểm tra cột mã hóa định danh phiếu nhập
    assert row['code'] == 'PO-001'

    # Kiểm tra SQL LEFT JOIN hoạt động chuẩn xác (Cột supplier_name liên kết thành công, không bị NULL)
    assert row[
               'supplier_name'] == 'NCC Thiên Long', "Lỗi SQL: Mệnh đề LEFT JOIN bảng suppliers bị sai lệch thông tin liên kết."

    # Kiểm tra các trường dữ liệu số lượng/thời gian trả về đúng định dạng chuẩn của Database
    assert row['total_amount'] == Decimal("1500000.0000")
    assert isinstance(row['created_at'], datetime)