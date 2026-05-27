import pytest
from decimal import Decimal
from datetime import datetime, date
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl


# =========================================================================
# XÂY DỰNG FAKE DATABASE & REPOSITORY (RAM - PHIÊN BẢN KIỂM TOÁN TỔNG LỰC)
# =========================================================================
class FakeReportRepository:
    def __init__(self):
        # 1. Mô phỏng bảng dữ liệu hóa đơn (vw_report_invoice_summary & vw_report_transaction_history)
        self.raw_invoices = [
            # Ngày 2026-05-15 (Nằm trong khoảng lọc) -> Doanh thu: 100k, Lợi nhuận: 40k
            {"invoice_id": 1, "invoice_code": "HD001", "created_at": datetime(2026, 5, 15, 8, 30),
             "sale_date": date(2026, 5, 15), "revenue": Decimal("100000"), "gross_profit": Decimal("40000"),
             "payment_method": "Tiền mặt", "payment_method_text": "Tiền mặt"},

            # Ngày 2026-05-15 (Nằm trong khoảng lọc) -> Doanh thu: 250k, Lợi nhuận: 110k
            {"invoice_id": 2, "invoice_code": "HD002", "created_at": datetime(2026, 5, 15, 14, 15),
             "sale_date": date(2026, 5, 15), "revenue": Decimal("250000"), "gross_profit": Decimal("110000"),
             "payment_method": "Chuyển khoản", "payment_method_text": "Chuyển khoản"},

            # Ngày 2026-05-16 (Nằm trong khoảng lọc) -> Doanh thu: 150k, Lợi nhuận: 60k
            {"invoice_id": 3, "invoice_code": "HD003", "created_at": datetime(2026, 5, 16, 10, 0),
             "sale_date": date(2026, 5, 16), "revenue": Decimal("150000"), "gross_profit": Decimal("60000"),
             "payment_method": "Tiền mặt", "payment_method_text": "Tiền mặt"},

            # Ngày 2026-05-20 (NẰM NGOÀI KHOẢNG LỌC BỘ TIÊU CHÍ)
            {"invoice_id": 4, "invoice_code": "HD004", "created_at": datetime(2026, 5, 20, 9, 0),
             "sale_date": date(2026, 5, 20), "revenue": Decimal("500000"), "gross_profit": Decimal("200000"),
             "payment_method": "Chuyển khoản", "payment_method_text": "Chuyển khoản"}
        ]

        # MÔ PHỎNG LUỒNG 4: Bảng hóa đơn dính trạng thái CANCELLED phát sinh trong khoảng lọc thời gian
        # Hóa đơn này trị giá 50k đã trả lại tiền mặt cho khách hàng -> Buộc hệ thống báo cáo KPIs phải khấu trừ doanh thu
        self.mock_cancelled_invoices = [
            {"id": 5, "code": "HD005_CANCELLED", "final_amount": Decimal("50000"),
             "created_at": datetime(2026, 5, 16, 16, 0)}
        ]

        # MÔ PHỎNG LUỒNG 1 & 4: Bảng ghi nhận vết rác tài chính triệt tiêu mang ra sổ cái
        # Hệ thống phát hiện kho rỗng đọng sai số float lẻ lịch sử, sinh log DATA_CORRECTION làm giảm -2.000đ lợi nhuận rác
        self.mock_variance_transactions = [
            {"id": 99, "type": "DATA_CORRECTION", "variance_amount": Decimal("-2000"),
             "created_at": datetime(2026, 5, 15, 11, 0)}
        ]

        # 2. Mô phỏng bảng doanh số sản phẩm (vw_report_product_sales) trong khoảng 2026-05-15 -> 2026-05-16
        self.raw_product_sales = [
            {"product_name": "Bút bi Thiên Long", "total_qty": 100},
            {"product_name": "Sách giáo khoa Toán 12", "total_qty": 20},
            {"product_name": "Vở kẻ ngang", "total_qty": 85},
            {"product_name": "Bút chì 2B", "total_qty": 10},
            {"product_name": "Tẩy Gôm", "total_qty": 5},
            {"product_name": "Thước kẻ", "total_qty": 2}  # Sản phẩm thứ 6, dùng để test giới hạn nghiêm ngặt Top 5
        ]

        # 3. Mô phỏng bảng tồn kho hiện tại (vw_report_inventory_valuation) - SNAPSHOT THỜI GIAN THỰC
        self.raw_inventory = [
            {"product_name": "Vở kẻ ngang", "unit_name": "Cuốn", "stock_quantity": 50, "mac_price": Decimal("6000"),
             "total_inventory_value": Decimal("300000")},
            {"product_name": "Bút bi Thiên Long", "unit_name": "Cây", "stock_quantity": 200,
             "mac_price": Decimal("4000"), "total_inventory_value": Decimal("800000")}
        ]

        # 4. Mô phỏng bảng phiếu nhập kho hoàn thành (Phục vụ cho luồng Activity Feed)
        self.raw_purchase_orders = [
            {"code": "PN001", "created_at": datetime(2026, 5, 15, 9, 15), "total_amount": Decimal("400000"),
             "supplier_name": "Nhà sách Fahasa"}
        ]

    def get_kpi_metrics(self, start_date: str, end_date: str) -> dict:
        """TC_Post_01: Kiểm toán toán học nghịch đảo dọn rác và trừ hàng hủy tại 4 thẻ KPI"""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Lọc hóa đơn COMPLETED theo khoảng thời gian
        filtered_sales = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]
        sales_revenue = sum(i["revenue"] for i in filtered_sales)
        sales_profit = sum(i["gross_profit"] for i in filtered_sales)

        # Kiểm toán Luồng 4: Tính tổng số tiền trả lại khách từ hóa đơn hủy
        returned_cash = sum(
            i["final_amount"] for i in self.mock_cancelled_invoices if start <= i["created_at"].date() <= end)

        # Kiểm toán Luồng 1: Tính tổng giá trị rác chênh lệch trích xuất sổ cái
        garbage_variance = sum(
            t["variance_amount"] for t in self.mock_variance_transactions if start <= t["created_at"].date() <= end)

        # Thẻ tổng giá trị kho lấy snapshot không phụ thuộc vào khoảng ngày lọc của bộ tiêu chí
        total_stock = sum(item["total_inventory_value"] for item in self.raw_inventory)

        # Áp dụng chính xác bộ máy công thức kiểm toán toán học nghịch đảo của Luồng 2 & Luồng 4
        net_revenue = sales_revenue - returned_cash  # Doanh thu thuần thực tế tại két
        net_profit = sales_profit + garbage_variance  # Lợi nhuận thuần sạch rác kế toán

        return {
            "total_orders": len(filtered_sales),
            "total_revenue": net_revenue,
            "total_profit": net_profit,
            "total_stock_value": total_stock
        }

    def get_revenue_trend(self, start_date: str, end_date: str) -> list:
        """TC_Post_02: Gom nhóm theo ngày, sắp xếp sale_date ASC và định dạng dd/mm"""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        filtered = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]

        trend_dict = {}
        for i in filtered:
            date_str = i["created_at"].strftime("%d/%m")
            trend_dict[date_str] = trend_dict.get(date_str, Decimal("0")) + i["revenue"]

        return [{"date": k, "revenue": v} for k, v in sorted(trend_dict.items())]

    def get_top_products(self, start_date: str, end_date: str, limit: int = 5) -> list:
        """TC_Post_03: Sắp xếp giảm dần theo total_qty và giới hạn số lượng (mặc định limit=5)"""
        sorted_products = sorted(self.raw_product_sales, key=lambda x: x["total_qty"], reverse=True)
        return [
            {"product_name": p["product_name"], "quantity": p["total_qty"]}
            for p in sorted_products[:limit]
        ]

    def get_transaction_history(self, start_date: str, end_date: str) -> list:
        """TC_Post_04: Lọc theo khoảng ngày, format YYYY-MM-DD HH:MM và sort created_at DESC"""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        filtered = [i for i in self.raw_invoices if start <= i["sale_date"] <= end]
        sorted_trans = sorted(filtered, key=lambda x: x["created_at"], reverse=True)

        return [
            {
                "invoice_code": t["invoice_code"],
                "created_at": t["created_at"],  # Giữ nguyên object gốc phục vụ Mapper kiểm toán kiểu dữ liệu
                "final_amount": t["revenue"],
                "payment_method": t["payment_method_text"]
            }
            for t in sorted_trans
        ]

    def get_inventory_valuation(self) -> list:
        """TC_Post_05: Sắp xếp tồn kho theo đặt tên product_name từ A-Z"""
        return sorted(self.raw_inventory, key=lambda x: x["product_name"])

    def get_daily_purchase_orders(self, date_str: str) -> list:
        """Phục vụ cho kiểm chứng luồng Activity Feed tổng hợp"""
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return [po for po in self.raw_purchase_orders if po["created_at"].date() == target_date]


class FakeUnitOfWork:
    def __init__(self, repo): self.report_repo = repo

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

    # --- TC_Post_01: Kiểm chứng Thẻ KPI tổng quan (ĐÃ TÍCH HỢP KIỂM TOÁN LÙI VÀ NÚT RÁC) ---
    # Tổng hóa đơn hoàn thành trong khoảng: 3 (HD001, HD002, HD003). HD004 nằm ngoài khoảng nên bị loại.
    assert report_data.kpis.total_orders == 3

    # Tổng doanh thu gốc: 100k + 250k + 150k = 500k.
    # Khấu trừ Luồng 4: Trả lại tiền mặt 50k của HD005_CANCELLED -> Doanh thu thuần = 450k
    assert report_data.kpis.total_revenue == Decimal("450000")

    # Tổng lợi nhuận gộp gốc: 40k + 110k + 60k = 210k.
    # Triệt tiêu rác Luồng 1: Cộng luồng tiền rác thực tế -2k phát sinh từ két rác kho trống -> Lợi nhuận gộp sạch = 208k
    assert report_data.kpis.total_profit == Decimal("208000")

    # Tổng giá trị kho (Snapshot thời gian thực): 300k + 800k = 1.1M (Bất biến với khoảng ngày lọc thời gian)
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
    assert len(top) == 5  # Mặc dù hệ thống có 6 sản phẩm, chỉ lấy tối đa 5
    # Sắp xếp giảm dần theo số lượng bán (total_qty DESC)
    assert top[0].product_name == "Bút bi Thiên Long"
    assert top[0].quantity == 100
    assert top[1].product_name == "Vở kẻ ngang"
    assert top[1].quantity == 85
    # "Thước kẻ" (qty = 2) có số lượng thấp nhất nên bắt buộc phải bị loại bỏ khỏi danh sách top 5
    assert all(p.product_name != "Thước kẻ" for p in top)

    trans = report_data.transactions
    assert len(trans) == 3

    # Sắp xếp thời gian mới nhất lên đầu (created_at DESC) -> HD003 (10:00 ngày 16) phải đứng đầu
    assert trans[0].invoice_code == "HD003"

     Ép kiểu đối tượng datetime sang chuỗi văn bản bằng .strftime() trước khi dùng toán tử so sánh bằng tuyệt đối
    assert trans[0].created_at.strftime("%Y-%m-%d %H:%M") == "2026-05-16 10:00"
    assert trans[0].payment_method == "Tiền mặt"  # Đã được map tiếng việt thân thiện

    assert trans[1].invoice_code == "HD002"
    assert trans[1].created_at.strftime("%Y-%m-%d %H:%M") == "2026-05-15 14:15"
    assert trans[1].payment_method == "Chuyển khoản"

    # --- TC_Post_05: Kiểm chứng Bảng báo cáo giá trị tồn kho hiện tại ---
    inv = report_data.inventory_valuation
    assert len(inv) == 2
    # Sắp xếp tên sản phẩm từ A-Z (product_name ASC) -> "Bút bi Thiên Long" đứng trước "Vở kẻ ngang"
    assert inv[0].product_name == "Bút bi Thiên Long"
    assert inv[1].product_name == "Vở kẻ ngang"

    # Đảm bảo độ chính xác toán học tuyệt đối: Số lượng tồn x Giá vốn MAC = Tổng giá trị tồn
    for item in inv:
        assert item.total_inventory_value == item.stock_quantity * item.mac_price


def test_activity_feed_real_time_merging_logic(report_service):
    """
    TC_Post_06: Bổ sung kiểm toán luồng trộn hoạt động Activity Feed của ngày 15/05.
    Mục tiêu: Đảm bảo phiếu nhập kho (IMPORT) và hóa đơn (SALE) được ép về chuỗi String,
    sắp xếp chính xác theo mốc thời gian mới nhất lên đầu mà không gây lỗi xung đột kiểu dữ liệu.
    """
    # WHEN: Gọi trộn luồng hoạt động ngày 15/05
    feed = report_service.get_daily_activity_feed("2026-05-15")

    # THEN:
    # 1. Tổng số hoạt động phát sinh: 1 phiếu nhập (PN001) + 2 hóa đơn (HD001, HD002) = 3
    assert len(feed) == 3

    # 2. Sắp xếp thời gian giảm dần (created_at DESC):
    # - HD002 tạo lúc 14:15 -> Đứng đầu
    # - ANOMALY INTERSECTION: PN001 tạo lúc 09:15 -> Đứng thứ hai
    # - HD001 tạo lúc 08:30 -> Đứng cuối cùng
    assert feed[0]['code'] == "HD002"
    assert feed[0]['type'] == "SALE"
    assert feed[0]['created_at'] == "2026-05-15 14:15"

    assert feed[1]['code'] == "PN001"
    assert feed[1]['type'] == "IMPORT"
    assert feed[1]['created_at'] == "2026-05-15 09:15"
    assert feed[1]['detail'] == "Nhà sách Fahasa"

    assert feed[2]['code'] == "HD001"
    assert feed[2]['type'] == "SALE"
    assert feed[2]['created_at'] == "2026-05-15 08:30"