import pytest
from decimal import Decimal
from datetime import datetime
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl


# ==========================================
# XÂY DỰNG FAKE DATABASE & REPOSITORY (BỘ NHỚ RAM)
# ==========================================
class FakeReportRepository:
    def __init__(self):
        # Mô phỏng bảng dữ liệu hóa đơn (vw_report_invoice_summary & vw_report_transaction_history)
        self.raw_invoices = [
            # Ngày 2026-05-15 (Nằm trong khoảng lọc)
            {"invoice_id": 1, "invoice_code": "HD001", "created_at": datetime(2026, 5, 15, 8, 30),
             "sale_date": datetime(2026, 5, 15).date(), "revenue": Decimal("100000"), "gross_profit": Decimal("40000"),
             "payment_method_text": "Tiền mặt"},
            {"invoice_id": 2, "invoice_code": "HD002", "created_at": datetime(2026, 5, 15, 14, 15),
             "sale_date": datetime(2026, 5, 15).date(), "revenue": Decimal("250000"), "gross_profit": Decimal("110000"),
             "payment_method_text": "Chuyển khoản"},

            # Ngày 2026-05-16 (Nằm trong khoảng lọc)
            {"invoice_id": 3, "invoice_code": "HD003", "created_at": datetime(2026, 5, 16, 10, 0),
             "sale_date": datetime(2026, 5, 16).date(), "revenue": Decimal("150000"), "gross_profit": Decimal("60000"),
             "payment_method_text": "Tiền mặt"},

            # Ngày 2026-05-20 (NẰM NGOÀI KHOẢNG LỌC)
            {"invoice_id": 4, "invoice_code": "HD004", "created_at": datetime(2026, 5, 20, 9, 0),
             "sale_date": datetime(2026, 5, 20).date(), "revenue": Decimal("500000"), "gross_profit": Decimal("200000"),
             "payment_method_text": "Chuyển khoản"}
        ]

        # Mô phỏng bảng doanh số sản phẩm (vw_report_product_sales) trong khoảng 2026-05-15 -> 2026-05-16
        self.raw_product_sales = [
            {"product_name": "Bút bi Thiên Long", "total_qty": 100},
            {"product_name": "Sách giáo khoa Toán 12", "total_qty": 20},
            {"product_name": "Vở kẻ ngang", "total_qty": 85},
            {"product_name": "Bút chì 2B", "total_qty": 10},
            {"product_name": "Tẩy Gôm", "total_qty": 5},
            {"product_name": "Thước kẻ", "total_qty": 2}  # Sản phẩm thứ 6, dùng để test giới hạn Top 5
        ]

        # Mô phỏng bảng tồn kho hiện tại (vw_report_inventory_valuation) - SNAPSHOT THỜI GIAN THỰC
        self.raw_inventory = [
            {"product_name": "Vở kẻ ngang", "unit_name": "Cuốn", "stock_quantity": 50, "mac_price": Decimal("6000"),
             "total_inventory_value": Decimal("300000")},
            {"product_name": "Bút bi Thiên Long", "unit_name": "Cây", "stock_quantity": 200,
             "mac_price": Decimal("4000"), "total_inventory_value": Decimal("800000")}
        ]

    def get_kpi_metrics(self, start_date: str, end_date: str):
        # TC_Post_01: Lọc hóa đơn theo ngày để tính thẻ KPI
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        filtered = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]

        # Thẻ tổng giá trị kho lấy snapshot không phụ thuộc vào khoảng ngày lọc
        total_stock = sum(item["total_inventory_value"] for item in self.raw_inventory)

        return {
            "total_orders": len(filtered),
            "total_revenue": sum(i["revenue"] for i in filtered),
            "total_profit": sum(i["gross_profit"] for i in filtered),
            "total_stock_value": total_stock
        }

    def get_revenue_trend(self, start_date: str, end_date: str):
        # TC_Post_02: Gom nhóm theo ngày, sắp xếp sale_date ASC và định dạng dd/mm
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Lấy các hóa đơn trong khoảng
        filtered = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]

        # Group by ngày trên RAM
        trend_dict = {}
        for i in filtered:
            date_str = i["created_at"].strftime("%d/%m")
            trend_dict[date_str] = trend_dict.get(date_str, Decimal("0")) + i["revenue"]

        # Trả về list sort theo ngày tăng dần
        return [{"date": k, "revenue": v} for k, v in sorted(trend_dict.items())]

    def get_top_products(self, start_date: str, end_date: str, limit: int = 5):
        # TC_Post_03: Sắp xếp giảm dần theo total_qty và giới hạn số lượng (mặc định limit=5)
        sorted_products = sorted(self.raw_product_sales, key=lambda x: x["total_qty"], reverse=True)
        return [
            {"product_name": p["product_name"], "quantity": p["total_qty"]}
            for p in sorted_products[:limit]
        ]

    def get_transaction_history(self, start_date: str, end_date: str):
        # TC_Post_04: Lọc theo khoảng ngày, format YYYY-MM-DD HH:MM và sort created_at DESC
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        filtered = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]
        sorted_trans = sorted(filtered, key=lambda x: x["created_at"], reverse=True)

        return [
            {
                "invoice_code": t["invoice_code"],
                "created_at": t["created_at"].strftime("%Y-%m-%d %H:%M"),
                "final_amount": t["revenue"],
                "payment_method": t["payment_method_text"]
            }
            for t in sorted_trans
        ]

    def get_inventory_valuation(self):
        # TC_Post_05: Sắp xếp tồn kho theo đặt tên product_name từ A-Z
        sorted_inv = sorted(self.raw_inventory, key=lambda x: x["product_name"])
        return sorted_inv


class FakeUnitOfWork:
    def __init__(self, repo):
        self.report_repo = repo

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES THIẾT LẬP MÔI TRƯỜNG KHỞI TẠO
# ==========================================
@pytest.fixture
def fake_repo():
    return FakeReportRepository()


@pytest.fixture
def report_service(fake_repo):
    uow_factory = lambda: FakeUnitOfWork(fake_repo)
    return ReportServiceImpl(uow_factory)


# ==========================================
# BÀI TEST CHÍNH: KIỂM CHỨNG TOÀN BỘ POST-CONDITIONS
# ==========================================
def test_get_dashboard_report_happy_path_state_changes(report_service, fake_repo):
    # GIVEN: Thiết lập khoảng thời gian xem báo cáo hợp lệ từ 15/05 đến 16/05
    start_date = "2026-05-15"
    end_date = "2026-05-16"

    # WHEN: Kích hoạt gọi hàm cửa ngõ duy nhất (Hộp đen thực thi)
    report_data = report_service.get_dashboard_report(start_date, end_date)

    # ==========================================
    # THEN: TRÍCH XUẤT ẢNH CHỤP DTO ĐỂ KIỂM CHỨNG (ASSERT STATE)
    # ==========================================

    # --- TC_Post_01: Kiểm chứng Thẻ KPI tổng quan ---
    # Tổng hóa đơn trong khoảng: 3 (HD001, HD002, HD003). HD004 nằm ngoài khoảng nên bị loại.
    assert report_data.kpis.total_orders == 3
    # Tổng doanh thu: 100k + 250k + 150k = 500k
    assert report_data.kpis.total_revenue == Decimal("500000")
    # Tổng lợi nhuận gộp: 40k + 110k + 60k = 210k
    assert report_data.kpis.total_profit == Decimal("210000")
    # Tổng giá trị kho (Snapshot thời gian thực): 300k + 800k = 1.1M (Bất biến với khoảng ngày lọc)
    assert report_data.kpis.total_stock_value == Decimal("1100000")

    # --- TC_Post_02: Kiểm chứng Biểu đồ xu hướng doanh thu ---
    trend = report_data.revenue_trend
    assert len(trend) == 2  # Chỉ có 2 ngày phát sinh: 15/05 và 16/05
    # Sắp xếp thời gian tăng dần (sale_date ASC) -> Ngày 15 đứng trước ngày 16
    assert trend[0].date == "15/05"
    assert trend[0].revenue == Decimal("350000")  # 100k + 250k
    assert trend[1].date == "16/05"
    assert trend[1].revenue == Decimal("150000")  # 150k

    # --- TC_Post_03: Kiểm chứng danh sách Top 5 sản phẩm bán chạy ---
    top = report_data.top_products
    assert len(top) == 5  # Mặc dù DB có 6 sản phẩm, chỉ lấy tối đa 5
    # Sắp xếp giảm dần theo số lượng bán (total_qty DESC)
    assert top[0].product_name == "Bút bi Thiên Long"
    assert top[0].quantity == 100
    assert top[1].product_name == "Vở kẻ ngang"
    assert top[1].quantity == 85
    # "Thước kẻ" (qty = 2) có số lượng thấp nhất nên bắt buộc phải bị loại bỏ khỏi danh sách top 5
    assert all(p.product_name != "Thước kẻ" for p in top)

    # --- TC_Post_04: Kiểm chứng Bảng lịch sử giao dịch ---
    trans = report_data.transactions
    assert len(trans) == 3
    # Sắp xếp thời gian mới nhất lên đầu (created_at DESC) -> HD003 (10:00 ngày 16) phải đứng đầu
    assert trans[0].invoice_code == "HD003"
    assert trans[0].created_at == "2026-05-16 10:00"
    assert trans[0].payment_method == "Tiền mặt"  # Đã được map tiếng việt thân thiện

    assert trans[1].invoice_code == "HD002"
    assert trans[1].created_at == "2026-05-15 14:15"
    assert trans[1].payment_method == "Chuyển khoản"

    # --- TC_Post_05: Kiểm chứng Bảng báo cáo giá trị tồn kho hiện tại ---
    inv = report_data.inventory_valuation
    assert len(inv) == 2
    # Sắp xếp tên sản phẩm từ A-Z (product_name ASC) -> "Bút bi Thiên Long" đứng trước "Vở kẻ ngang"
    assert inv[0].product_name == "Bút bi Thiên Long"
    assert inv[1].product_name == "Vở kẻ ngang"

    # Đảm bảo độ chính xác toán học: Số lượng tồn x Giá vốn MAC = Tổng giá trị tồn
    for item in inv:
        assert item.total_inventory_value == item.stock_quantity * item.mac_price