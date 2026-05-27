import pytest
from decimal import Decimal
from datetime import datetime, date
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl
from app.modules.report.dtos.report_dto import DashboardReportDTO


# =========================================================================
# KHỞI TẠO HỘP ĐEN CƠ SỞ DỮ LIỆU GIẢ LẬP TRÊN RAM (PHIÊN BẢN 8 CHỈ SỐ)
# =========================================================================
class FakeReportRepository:
    def __init__(self):
        # 1. Bảng dữ liệu hóa đơn gốc (Gồm cả đơn sống nằm trong / ngoài khoảng lọc)
        self.raw_invoices = [
            # Ngày 15/05: Doanh thu: 100k, Giá vốn: 60k (Lợi nhuận gộp: 40k)
            {"invoice_id": 1, "invoice_code": "HD001", "created_at": datetime(2026, 5, 15, 8, 30),
             "sale_date": date(2026, 5, 15), "revenue": Decimal("100000"), "gross_profit": Decimal("40000"),
             "payment_method_text": "Tiền mặt"},

            # Ngày 15/05: Doanh thu: 250k, Giá vốn: 140k (Lợi nhuận gộp: 110k)
            {"invoice_id": 2, "invoice_code": "HD002", "created_at": datetime(2026, 5, 15, 14, 15),
             "sale_date": date(2026, 5, 15), "revenue": Decimal("250000"), "gross_profit": Decimal("110000"),
             "payment_method_text": "Chuyển khoản"},

            # Ngày 16/05: Doanh thu: 150k, Giá vốn: 90k (Lợi nhuận gộp: 60k)
            {"invoice_id": 3, "invoice_code": "HD003", "created_at": datetime(2026, 5, 16, 10, 0),
             "sale_date": date(2026, 5, 16), "revenue": Decimal("150000"), "gross_profit": Decimal("60000"),
             "payment_method_text": "Tiền mặt"},

            # Giao dịch nằm ngoài khoảng lọc ngày của bộ tiêu chí báo cáo -> Bị loại bỏ khi tính toán kỳ lọc
            {"invoice_id": 4, "invoice_code": "HD004", "created_at": datetime(2026, 5, 20, 9, 0),
             "sale_date": date(2026, 5, 20), "revenue": Decimal("500000"), "gross_profit": Decimal("200000"),
             "payment_method_text": "Chuyển khoản"}
        ]

        # 2. Chứng từ HỦY BÁN HÀNG thực tế phát sinh trong kỳ (Luồng 4)
        self.mock_cancelled_invoices = [
            {"id": 5, "code": "HD005_CANCELLED", "total_amount": Decimal("50000"),
             "created_at": datetime(2026, 5, 16, 16, 0)}
        ]

        # 3. Giao dịch điều chỉnh dọn rác kế toán tài chính phát sinh trong kỳ (Luồng 1 & Luồng 3)
        self.mock_variance_transactions = [
            {"id": 99, "type": "DATA_CORRECTION", "variance_amount": Decimal("-2000"),
             "created_at": datetime(2026, 5, 15, 11, 0)}
        ]

        # 4. Doanh số sản phẩm bán ra phục vụ vẽ biểu đồ Top
        self.raw_product_sales = [
            {"product_name": "Bút bi Thiên Long", "total_qty": 100},
            {"product_name": "Vở kẻ ngang", "total_qty": 85},
            {"product_name": "Sách giáo khoa Toán 12", "total_qty": 20},
            {"product_name": "Bút chì 2B", "total_qty": 10},
            {"product_name": "Tẩy Gôm", "total_qty": 5},
            {"product_name": "Thước kẻ", "total_qty": 2}  # Sản phẩm thứ 6 dùng để thử thách chốt chặn giới hạn Top 5
        ]

        # 5. Snapshot giá trị tồn kho vật lý thời gian thực (Độc lập bộ lọc ngày)
        self.raw_inventory = [
            {"product_name": "Bút bi Thiên Long", "unit_name": "Cây", "stock_quantity": 200,
             "mac_price": Decimal("4000"), "total_inventory_value": Decimal("800000")},
            {"product_name": "Vở kẻ ngang", "unit_name": "Cuốn", "stock_quantity": 50, "mac_price": Decimal("6000"),
             "total_inventory_value": Decimal("300000")}
        ]

        # 6. Phiếu nhập kho gốc phục vụ luồng trộn hoạt động Activity Feed
        self.raw_purchase_orders = [
            {"code": "PN001", "created_at": datetime(2026, 5, 15, 9, 15), "total_amount": Decimal("400000"),
             "supplier_name": "Nhà sách Fahasa"}
        ]

    def get_kpi_metrics(self, start_date: str, end_date: str) -> dict:
        """Mô phỏng toán học từ View tích hợp daily chia nhỏ về 8 chỉ số"""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        completed_in_range = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]
        cancelled_in_range = [i for i in self.mock_cancelled_invoices if start <= i["created_at"].date() <= end]
        variance_in_range = [t for t in self.mock_variance_transactions if start <= t["created_at"].date() <= end]

        # Thực hiện thuật toán kế toán phễu doanh thu sạch
        total_orders_completed = len(completed_in_range)
        total_orders_cancelled = len(cancelled_in_range)
        total_orders_created = total_orders_completed + total_orders_cancelled

        net_revenue = sum(i["revenue"] for i in completed_in_range)
        cancelled_value = sum(i["total_amount"] for i in cancelled_in_range)
        gross_revenue = net_revenue + cancelled_value

        total_cogs = sum(i["revenue"] - i["gross_profit"] for i in completed_in_range)
        gross_profit = net_revenue - total_cogs
        variance_garbage = sum(t["variance_amount"] for t in variance_in_range)
        net_profit = gross_profit + variance_garbage

        return {
            "total_orders_created": total_orders_created,
            "total_orders_completed": total_orders_completed,
            "total_orders_cancelled": total_orders_cancelled,
            "gross_revenue": float(gross_revenue),
            "cancelled_value": float(cancelled_value),
            "net_revenue": float(net_revenue),
            "total_cogs": float(total_cogs),
            "gross_profit": float(gross_profit),
            "variance_garbage": float(variance_garbage),
            "net_profit": float(net_profit)
        }

    def get_revenue_trend(self, start_date: str, end_date: str) -> list:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        filtered = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]

        trend_dict = {}
        for i in filtered:
            date_str = i["created_at"].strftime("%d/%m")
            trend_dict[date_str] = trend_dict.get(date_str, Decimal("0")) + i["revenue"]
        return [{"date": k, "revenue": v} for k, v in sorted(trend_dict.items())]

    def get_top_products(self, start_date: str, end_date: str, limit: int = 5) -> list:
        sorted_products = sorted(self.raw_product_sales, key=lambda x: x["total_qty"], reverse=True)
        return [{"product_name": p["product_name"], "quantity": p["total_qty"]} for p in sorted_products[:limit]]

    def get_transaction_history(self, start_date: str, end_date: str) -> list:
        """TC_Post_04: Lọc theo khoảng ngày, format YYYY-MM-DD HH:MM và sort created_at DESC"""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        filtered = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]
        sorted_trans = sorted(filtered, key=lambda x: x["created_at"], reverse=True)

        return [
            {
                "invoice_code": t["invoice_code"],
                "created_at": t["created_at"],
                "total_amount": float(t["revenue"]),
                 Đổi tên Key từ 'payment_method_text' thành 'payment_method' để khớp hợp đồng dữ liệu Repo thật
                "payment_method": t["payment_method_text"]
            }
            for t in sorted_trans
        ]

    def get_inventory_valuation(self) -> list:
        return sorted(self.raw_inventory, key=lambda x: x["product_name"])

    def get_daily_purchase_orders(self, date_str: str) -> list:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return [po for po in self.raw_purchase_orders if po["created_at"].date() == target_date]


class FakeUnitOfWork:
    def __init__(self, repo): self.report_repo = repo

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


@pytest.fixture
def fake_repo(): return FakeReportRepository()


@pytest.fixture
def report_service(fake_repo):
    uow_factory = lambda: FakeUnitOfWork(fake_repo)
    return ReportServiceImpl(uow_factory)


# =========================================================================
# CÁC KỊCH BẢN KIỂM TOÁN HỘP ĐEN TÍNH ĐÚNG ĐẮN CỦA SẢN PHẨM
# =========================================================================

def test_kpi_pipeline_financial_correctness_happy_path(report_service):
    """
    KỊCH BẢN: Lọc dữ liệu phát sinh bình thường trong khoảng ngày 15/05 -> 16/05.
    MỤC TIÊU: Xác minh phễu tài chính bóc tách 8 chỉ số tính toán khớp cơ sở dữ liệu.
    """
    report_data: DashboardReportDTO = report_service.get_dashboard_report("2026-05-15", "2026-05-16")
    kpis = report_data.kpis

    # 1. Kiểm toán cụm số lượng đơn hàng (ĐÚNG)
    assert kpis.total_orders_created == 4     # 3 thành công + 1 hủy
    assert kpis.total_orders_completed == 3
    assert kpis.total_orders_cancelled == 1

    # 2. Kiểm toán cụm dòng tiền Doanh thu
    assert kpis.gross_revenue == Decimal("550000")   # (100k + 250k + 150k) + 50k đơn hủy
    assert kpis.cancelled_value == Decimal("50000")  # Tiền hoàn trả đơn hủy
     Lấy 550k (Gross) - 50k (Hủy) phải bằng 500k (Net Revenue)
    assert kpis.net_revenue == Decimal("500000")

    # 3. Kiểm toán cụm Chi phí & Lợi nhuận sạch rác kế toán
    assert kpis.total_cogs == Decimal("290000")      # Tổng giá vốn (60k + 140k + 90k)
     Lợi nhuận gộp kỹ thuật = Doanh thu thuần (500k) - Giá vốn (290k) = 210k
    assert kpis.gross_profit == Decimal("210000")
    assert kpis.variance_garbage == Decimal("-2000")  # Ghi sổ tiền dọn rác kho trống
     Lợi nhuận thực tế đưa vào két = Lợi nhuận gộp (210k) + Tiền rác (-2k) = 208k
    assert kpis.net_profit == Decimal("208000")

def test_double_deduction_prevention_on_total_cancellation():
    """
    KỊCH BẢN BIÊN (SỬA LỖI DOANH THU ÂM): Giả lập trường hợp hủy toàn bộ hóa đơn phát sinh trong kỳ.
    KỲ VỌNG SẢN PHẨM: Doanh thu thuần và lợi nhuận thuần thực tế phải cán mốc 0 VND tuyệt đối,
    không bao giờ được phép âm vì đã loại trừ việc bị trừ kép dòng tiền.
    """
    repo = FakeReportRepository()
    # Ép môi trường kho trống/hủy sạch: Không có đơn thành công nào, chỉ có 1 đơn hủy trị giá 200k
    repo.raw_invoices = []
    repo.mock_cancelled_invoices = [
        {"id": 10, "code": "HD_XA_RAC", "total_amount": Decimal("200000"), "created_at": datetime(2026, 5, 15, 10, 0)}
    ]
    repo.mock_variance_transactions = []

    service = ReportServiceImpl(lambda: FakeUnitOfWork(repo))
    report_data = service.get_dashboard_report("2026-05-15", "2026-05-15")
    kpis = report_data.kpis

    assert kpis.total_orders_created == 1
    assert kpis.total_orders_completed == 0
    assert kpis.total_orders_cancelled == 1
    assert kpis.gross_revenue == Decimal("200000")
    assert kpis.cancelled_value == Decimal("200000")

    # CHỐT CHẶN BẢO VỆ: Không âm dòng tiền
    assert kpis.net_revenue == Decimal("0")
    assert kpis.net_profit == Decimal("0")


def test_empty_financial_period_should_return_zero_without_crashing(report_service):
    """
    KỊCH BẢN: Người dùng chọn khoảng ngày xa xôi trong tương lai hoàn toàn không có dữ liệu chứng từ.
    KỲ VỌNG SẢN PHẨM: Hệ thống tự động điền số 0 an toàn lên tất cả 8 chỉ số, không được tung lỗi chia cho 0.
    """
    report_data: DashboardReportDTO = report_service.get_dashboard_report("2026-12-01", "2026-12-31")
    kpis = report_data.kpis

    assert kpis.total_orders_created == 0
    assert kpis.gross_revenue == Decimal("0")
    assert kpis.net_profit == Decimal("0")


def test_chart_and_history_limits_and_sorting(report_service):
    """
    KỊCH BẢN: Kiểm tra tính đúng đắn cấu trúc hiển thị của Biểu đồ và Bảng lịch sử.
    KỲ VỌNG: Biểu đồ Top lấy đúng tối đa 5 phần tử (loại bỏ phần tử thứ 6). Bảng lịch sử xếp đơn mới nhất lên đầu.
    """
    report_data: DashboardReportDTO = report_service.get_dashboard_report("2026-05-15", "2026-05-16")

    # 1. Kiểm tra giới hạn Top 5 sản phẩm
    top_products = report_data.top_products
    assert len(top_products) == 5
    assert top_products[0].product_name == "Bút bi Thiên Long"
    assert all(p.product_name != "Thước kẻ" for p in top_products)  # Thước kẻ có qty thấp nhất nên phải bay màu

    # 2. Kiểm tra sắp xếp lịch sử giao dịch (Mới nhất đứng đầu)
    transactions = report_data.transactions
    assert transactions[0].invoice_code == "HD003"  # Đơn ngày 16/05 xếp trên ngày 15/05


def test_activity_feed_chronological_string_sorting(report_service):
    """
    KỊCH BẢN: Tổng hợp dòng nhật ký hoạt động Activity Feed tại màn hình Home.
    KỲ VỌNG: Sắp xếp trộn luồng chuỗi thời gian hoàn chỉnh từ mới nhất đến cũ nhất.
    """
    feed = report_service.get_daily_activity_feed("2026-05-15")
    assert len(feed) == 3
    # Mốc thời gian xếp hạng giảm dần: 14:15 -> 09:15 -> 08:30
    assert feed[0]['code'] == "HD002"
    assert feed[1]['code'] == "PN001"
    assert feed[2]['code'] == "HD001"