import pytest
from decimal import Decimal
from app.modules.tax.dtos.tax_dto import TaxConfigDTO, MonthlyRevenueDTO
from app.modules.tax.services.impl.tax_service_impl import TaxService


# ==========================================
# SETUP FAKE REPOSITORIES & UOW (BỘ NHỚ RAM)
# ==========================================
class FakeTaxConfigRepo:
    def __init__(self):
        self.configs = {}

    def get_config_by_year(self, year: int):
        return self.configs.get(year)

    def save_config(self, config: TaxConfigDTO):
        self.configs[config.apply_year] = config
        return True


class FakeTaxReportRepo:
    def __init__(self):
        # Lưu trữ doanh thu theo năm. Format: { year: [MonthlyRevenueDTO, ...] }
        self.yearly_revenues = {}

    def get_monthly_revenue_by_year(self, year: int):
        return self.yearly_revenues.get(year, [])


class FakeUnitOfWork:
    def __init__(self):
        self.tax_config_repo = FakeTaxConfigRepo()
        self.tax_report_repo = FakeTaxReportRepo()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES
# ==========================================
@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def tax_service(uow):
    # Khởi tạo Service với uow_factory
    return TaxService(lambda: uow)


# ==========================================
# TEST CASES CHO NHÓM PRE-CONDITIONS
# ==========================================

def test_generate_report_handles_invalid_year_safely(tax_service):
    """
    TC_Pre_01: Truyền vào năm không hợp lệ (năm âm).
    Kỳ vọng: Hệ thống không crash, tự khởi tạo cấu hình mặc định và trả về báo cáo trắng (0 VND).
    """
    # GIVEN: Không cần setup data vì DB đang trống rỗng

    # WHEN: Gọi tạo báo cáo với năm -1
    report = tax_service.generate_yearly_tax_report(-1)

    # THEN: Kiểm tra hệ thống xử lý an toàn
    assert report.year == -1
    assert report.total_revenue == Decimal('0')
    assert report.total_tax_amount == Decimal('0')
    assert report.is_over_threshold is False

    # Vẫn phải đảm bảo cấu trúc trả về đủ 12 tháng để UI vẽ bảng không bị lỗi
    assert len(report.monthly_details) == 12
    for detail in report.monthly_details:
        assert detail.revenue == Decimal('0')
        assert detail.total_tax == Decimal('0')


def test_generate_report_avoids_zero_division_when_no_revenue(tax_service, uow):
    """
    TC_Pre_02: Năm kinh doanh ế ẩm, tổng doanh thu = 0.
    Kỳ vọng: Lớp TaxCalculator bên dưới không được văng lỗi chia cho 0 (ZeroDivisionError).
    """
    # GIVEN: Khởi tạo dữ liệu năm 2023 có vài tháng nhưng doanh thu đều bằng 0
    uow.tax_report_repo.yearly_revenues[2023] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('0')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('0')),
    ]

    # Cố tình setup một cấu hình thuế có sẵn cho năm 2023
    uow.tax_config_repo.configs[2023] = TaxConfigDTO(
        apply_year=2023, threshold_amount=Decimal('100000000'),
        vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5')
    )

    # WHEN: Thực thi tính toán báo cáo
    # Nếu hệ thống dở, dòng này sẽ văng ZeroDivisionError vì cố tính tỷ lệ: 0 / 0
    report = tax_service.generate_yearly_tax_report(2023)

    # THEN: Báo cáo tính toán thành công, thuế phải nộp = 0
    assert report.total_revenue == Decimal('0')
    assert report.total_tax_amount == Decimal('0')

    # Trích xuất tháng 1 để kiểm chứng
    month_1 = next(m for m in report.monthly_details if m.month == 1)
    assert month_1.revenue == Decimal('0')
    assert month_1.vat_amount == Decimal('0')
    assert month_1.pit_amount == Decimal('0')