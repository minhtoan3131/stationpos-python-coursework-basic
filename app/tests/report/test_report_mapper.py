# File: app/tests/report/test_report_mapper.py
import pytest
from decimal import Decimal
from app.modules.report.utils.report_mapper import ReportMapper
from app.modules.report.dtos.report_dto import KPIDTO

def test_mapper_should_handle_perfect_db_data():
    """
    KỊCH BẢN: DB trả về đầy đủ và chuẩn xác cấu trúc 8 chỉ số của View tích hợp.
    KỲ VỌNG: Mapper phải chuyển đổi toàn bộ sang kiểu dữ liệu an toàn (int, Decimal)
    và giữ nguyên độ chính xác.
    """
    raw_db_row = {
        "total_orders_created": 15,
        "total_orders_completed": 12,
        "total_orders_cancelled": 3,
        "gross_revenue": 1500000.0000,
        "cancelled_value": 300000.0000,
        "net_revenue": 1200000.0000,
        "total_cogs": 700000.0000,
        "gross_profit": 500000.0000,
        "variance_garbage": -5000.0000,
        "net_profit": 495000.0000,
        "total_stock_value": 8500000.0000
    }

    dto: KPIDTO = ReportMapper.map_kpi(raw_db_row)

    # Kiểm tra tính toàn vẹn kiểu dữ liệu và giá trị
    assert dto.total_orders_created == 15
    assert dto.total_orders_completed == 12
    assert dto.total_orders_cancelled == 3
    assert dto.gross_revenue == Decimal("1500000")
    assert dto.cancelled_value == Decimal("300000")
    assert dto.net_revenue == Decimal("1200000")
    assert dto.total_cogs == Decimal("700000")
    assert dto.gross_profit == Decimal("500000")
    assert dto.variance_garbage == Decimal("-5000")
    assert dto.net_profit == Decimal("495000")


def test_mapper_should_gracefully_handle_none_and_missing_fields():
    """
    KỊCH BẢN: Khoảng thời gian lọc không có giao dịch nào phát sinh, DB trả về một loạt giá trị NULL (None).
    KỲ VỌNG: Hệ thống KHÔNG ĐƯỢC CRASH. Mapper phải tự động quy đổi các giá trị NULL về 0 hoặc 0 VND.
    """
    raw_bad_db_row = {
        "total_orders_created": None,
        "total_orders_completed": None,
        "total_orders_cancelled": None,
        "gross_revenue": None,
        "cancelled_value": None,
        "net_revenue": None,
        "total_cogs": None,
        "gross_profit": None,
        "variance_garbage": None,
        "net_profit": None,
        "total_stock_value": None
    }

    dto: KPIDTO = ReportMapper.map_kpi(raw_bad_db_row)

    # Dù DB trả về rác/Null, tầng hiển thị bắt buộc phải nhận về con số 0 an toàn
    assert dto.total_orders_created == 0
    assert dto.total_orders_completed == 0
    assert dto.total_orders_cancelled == 0
    assert dto.gross_revenue == Decimal("0")
    assert dto.cancelled_value == Decimal("0")
    assert dto.net_revenue == Decimal("0")
    assert dto.total_cogs == Decimal("0")
    assert dto.gross_profit == Decimal("0")
    assert dto.variance_garbage == Decimal("0")
    assert dto.net_profit == Decimal("0")


def test_mapper_should_handle_empty_dictionary():
    """
    KỊCH BẢN: Hàm Repository bị lỗi kết nối hoặc trả về một Dictionary hoàn toàn rỗng {}.
    KỲ VỌNG: Hệ thống tự động kích hoạt chốt chặn khẩn cấp, trả về thực thể DTO mặc định bằng 0.
    """
    dto: KPIDTO = ReportMapper.map_kpi({})
    assert dto.total_orders_created == 0
    assert dto.net_revenue == Decimal("0")
    assert dto.net_profit == Decimal("0")