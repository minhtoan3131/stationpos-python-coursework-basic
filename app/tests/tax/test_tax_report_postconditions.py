import pytest
from decimal import Decimal
from app.modules.tax.dtos.tax_dto import TaxConfigDTO, MonthlyRevenueDTO
from app.modules.tax.services.impl.tax_service_impl import TaxService


# ==========================================
# SETUP FAKE REPOSITORIES & UOW
# ==========================================
class FakeTaxConfigRepo:
    def __init__(self):
        self.configs = {}

    def get_config_by_year(self, year: int):
        return self.configs.get(year)

    def save_config(self, config: TaxConfigDTO):
        # Lưu vào RAM (Dictionary) để giả lập cơ chế UPSERT
        self.configs[config.apply_year] = config
        return True


class FakeTaxReportRepo:
    def __init__(self):
        # Lưu trữ doanh thu theo năm. Format: { year: [MonthlyRevenueDTO, ...] }
        self.yearly_revenues = {}

    def get_monthly_revenue_by_year(self, year: int):
        return self.yearly_revenues.get(year, [])


class FakeUnitOfWork:
    """Giả lập Context Manager của DB, chứa các Fake Repos"""

    def __init__(self):
        self.tax_config_repo = FakeTaxConfigRepo()
        self.tax_report_repo = FakeTaxReportRepo()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# ==========================================
# FIXTURES
# ==========================================
@pytest.fixture
def uow():
    """Cung cấp UOW để bài test có thể chọc thẳng vào RAM kiểm chứng dữ liệu"""
    return FakeUnitOfWork()


@pytest.fixture
def tax_service(uow):
    """Khởi tạo Service với Fake UOW"""
    return TaxService(lambda: uow)


# ==========================================
# TEST CASES CHO NHÓM POST-CONDITIONS
# ==========================================

def test_generate_report_under_threshold_yields_zero_tax(tax_service, uow):
    """
    TC_Post_01: Dưới ngưỡng miễn thuế.
    Kỳ vọng: Cờ is_over_threshold = False, toàn bộ tiền thuế các tháng phải bằng 0.
    """
    # GIVEN: Cấu hình ngưỡng là 100 triệu
    year = 2024
    uow.tax_config_repo.configs[year] = TaxConfigDTO(
        apply_year=year,
        threshold_amount=Decimal('100000000'),
        vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5')
    )

    # Doanh thu tháng 10 bán được 80 triệu (Vẫn dưới ngưỡng 100tr)
    uow.tax_report_repo.yearly_revenues[year] = [
        MonthlyRevenueDTO(month=10, revenue=Decimal('80000000'))
    ]

    # WHEN: Kích hoạt luồng tạo báo cáo
    report = tax_service.generate_yearly_tax_report(year)

    # THEN: Kiểm chứng kết quả tổng quan
    assert report.total_revenue == Decimal('80000000')
    assert report.is_over_threshold is False
    assert report.total_tax_amount == Decimal('0')

    # THEN: Kiểm chứng chi tiết tháng 10 (Dù có doanh thu nhưng đóng thuế 0 đồng)
    month_10 = next(m for m in report.monthly_details if m.month == 10)
    assert month_10.revenue == Decimal('80000000')
    assert month_10.vat_amount == Decimal('0')
    assert month_10.pit_amount == Decimal('0')
    assert month_10.total_tax == Decimal('0')


def test_generate_report_over_threshold_calculates_and_distributes_correctly(tax_service, uow):
    """
    TC_Post_02: Vượt ngưỡng miễn thuế (Happy Path).
    Kỳ vọng: Tính đúng tổng thuế theo phần vượt, và chia tiền thuế về các tháng theo đúng tỷ trọng doanh thu.
    """
    # GIVEN: Cấu hình ngưỡng 100 triệu. VAT 1%, PIT 0.5% (Tổng 1.5%)
    year = 2024
    uow.tax_config_repo.configs[year] = TaxConfigDTO(
        apply_year=year,
        threshold_amount=Decimal('100000000'),
        vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5')
    )

    # Kịch bản: Bán 2 tháng, mỗi tháng 100 triệu -> Tổng doanh thu 200 triệu
    # Tỷ trọng: Mỗi tháng đóng góp 50% doanh thu, do đó phải gánh 50% tiền thuế.
    uow.tax_report_repo.yearly_revenues[year] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('100000000')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('100000000')),
    ]

    # WHEN
    report = tax_service.generate_yearly_tax_report(year)

    # THEN: Kiểm chứng Toán học Tổng
    # Doanh thu chịu thuế = 200tr - 100tr = 100 triệu
    # Tổng thuế = 100 triệu * 1.5% = 1,500,000 VND
    assert report.total_revenue == Decimal('200000000')
    assert report.is_over_threshold is True
    assert report.total_tax_amount == Decimal('1500000')

    # THEN: Kiểm chứng Phân bổ (Mỗi tháng chịu 50% tổng thuế = 750,000 VND)
    month_1 = next(m for m in report.monthly_details if m.month == 1)

    # Kiểm tra số chia nhỏ của từng loại thuế cho tháng 1
    # VAT = 100 triệu * 1.0% * 50% tỷ trọng = 500,000 VND
    # PIT = 100 triệu * 0.5% * 50% tỷ trọng = 250,000 VND
    assert month_1.vat_amount == Decimal('500000')
    assert month_1.pit_amount == Decimal('250000')
    assert month_1.total_tax == Decimal('750000')


def test_generate_report_auto_creates_default_config_if_missing(tax_service, uow):
    """
    TC_Post_03: Báo cáo cho một năm chưa từng được cấu hình.
    Kỳ vọng: Hệ thống tự sinh cấu hình mặc định (Ngưỡng 1 Tỷ) lưu xuống DB và tính toán dựa trên cấu hình đó.
    """
    year = 2025

    # GIVEN: Khẳng định DB hiện tại HOÀN TOÀN KHÔNG CÓ CẤU HÌNH THUẾ CHO NĂM 2025
    assert uow.tax_config_repo.get_config_by_year(year) is None

    # Bơm doanh thu 2 Tỷ vào năm 2025
    uow.tax_report_repo.yearly_revenues[year] = [
        MonthlyRevenueDTO(month=12, revenue=Decimal('2000000000'))
    ]

    # WHEN
    report = tax_service.generate_yearly_tax_report(year)

    # THEN: Hệ quả 1 (Side-effect) - Cấu hình Mặc định phải được sinh ra và lưu vào Fake DB
    saved_config = uow.tax_config_repo.get_config_by_year(year)
    assert saved_config is not None
    assert saved_config.threshold_amount == Decimal('1000000000')  # Mặc định 1 Tỷ
    assert saved_config.vat_percent == Decimal('1.0')
    assert saved_config.pit_percent == Decimal('0.5')

    # THEN: Hệ quả 2 - Kết quả báo cáo phải được tính đúng theo cấu hình mặc định vừa sinh ra
    # Chịu thuế = 2 Tỷ - 1 Tỷ (ngưỡng mặc định) = 1 Tỷ
    # Tổng thuế = 1 Tỷ * 1.5% = 15 Triệu
    assert report.total_revenue == Decimal('2000000000')
    assert report.is_over_threshold is True
    assert report.total_tax_amount == Decimal('15000000')