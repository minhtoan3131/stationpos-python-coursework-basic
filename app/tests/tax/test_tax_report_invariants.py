import pytest
import copy
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
        self.configs[config.apply_year] = config
        return True


class FakeTaxReportRepo:
    def __init__(self):
        self.yearly_revenues = {}

    def get_monthly_revenue_by_year(self, year: int):
        # Trả về một bản sao sâu (deep copy) để mô phỏng việc query từ DB lên.
        # Đảm bảo Service không can thiệp trực tiếp vào reference data trong RAM.
        return copy.deepcopy(self.yearly_revenues.get(year, []))


class FakeUnitOfWork:
    def __init__(self):
        self.tax_config_repo = FakeTaxConfigRepo()
        self.tax_report_repo = FakeTaxReportRepo()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# ==========================================
# FIXTURES (DEPENDENCY)
# ==========================================
@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def tax_service(uow):
    return TaxService(lambda: uow)


# ==========================================
# TEST CASES CHO NHÓM INVARIANTS (BẤT BIẾN)
# ==========================================

def test_invariant_tax_sum_exactly_matches_total(tax_service, uow):
    """
    TC_Inv_01: Tính Toàn Vẹn Tổng.
    Kỳ vọng: Tổng thuế của 12 tháng cộng lại phải BẰNG CHÍNH XÁC tổng thuế cả năm. Không được rớt 1 đồng do làm tròn.
    """
    year = 2026
    uow.tax_config_repo.configs[year] = TaxConfigDTO(
        apply_year=year, threshold_amount=Decimal('100000000'),
        vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5')
    )

    # GIVEN: Tạo ra một kịch bản với con số chia không hết để "thử thách" bộ máy làm tròn.
    # Ngưỡng 100tr. Doanh thu 133,333,333. Vượt ngưỡng = 33,333,333
    # Chia cho 3 tháng lệch nhau 1 đồng để ép tỷ lệ phần trăm ra số thập phân dài ngoằng.
    uow.tax_report_repo.yearly_revenues[year] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('44444444')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('44444444')),
        MonthlyRevenueDTO(month=3, revenue=Decimal('44444445')),
    ]

    # WHEN
    report = tax_service.generate_yearly_tax_report(year)

    # THEN: Tổng số tiền thuế phân bổ cho 12 tháng
    sum_monthly_tax = sum(month.total_tax for month in report.monthly_details)

    # BẮT BUỘC phải khớp hoàn toàn tuyệt đối với tổng thuế ở Header báo cáo
    assert sum_monthly_tax == report.total_tax_amount


def test_invariant_zero_revenue_means_zero_tax(tax_service, uow):
    """
    TC_Inv_02: Thuế gắn liền với doanh thu.
    Kỳ vọng: Những tháng không bán được hàng (0 VND) tuyệt đối không bị gánh thuế.
    """
    year = 2026
    uow.tax_config_repo.configs[year] = TaxConfigDTO(
        apply_year=year, threshold_amount=Decimal('100000000'),
        vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5')
    )

    # GIVEN: Tổng doanh thu 150tr (Vượt ngưỡng 100tr chắc chắn phải nộp thuế).
    # Nhưng Tháng 2 và 3 lại không bán được đồng nào.
    uow.tax_report_repo.yearly_revenues[year] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('150000000')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('0')),
        MonthlyRevenueDTO(month=3, revenue=Decimal('0')),
    ]

    # WHEN
    report = tax_service.generate_yearly_tax_report(year)

    # Đảm bảo bài test có ý nghĩa (Thực sự có phát sinh tiền thuế cả năm)
    assert report.total_tax_amount > Decimal('0')

    # THEN: Quét qua toàn bộ các tháng, tháng nào doanh thu 0 thì thuế phải 0
    for month_detail in report.monthly_details:
        if month_detail.revenue == Decimal('0'):
            assert month_detail.total_tax == Decimal('0')
            assert month_detail.vat_amount == Decimal('0')
            assert month_detail.pit_amount == Decimal('0')


def test_invariant_no_mutation_of_original_revenue_data(tax_service, uow):
    """
    TC_Inv_03: Luật Bất Can Thiệp (No Side-effects trên dữ liệu gốc).
    Kỳ vọng: Quá trình lập báo cáo không được vô tình biến đổi (mutate) dữ liệu gốc trong CSDL.
    """
    year = 2026
    # GIVEN: Khởi tạo dữ liệu mồi
    original_data = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('150000000')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('50000000'))
    ]
    uow.tax_report_repo.yearly_revenues[year] = original_data

    # SNAPSHOT: Chụp ảnh trạng thái của Database TRƯỚC KHI gọi hàm
    db_snapshot_before = copy.deepcopy(uow.tax_report_repo.yearly_revenues[year])

    # WHEN: Gọi hàm tạo báo cáo (Luồng xử lý có thể rất phức tạp)
    _ = tax_service.generate_yearly_tax_report(year)

    # THEN: Kiểm chứng trạng thái của Database SAU KHI gọi hàm
    db_state_after = uow.tax_report_repo.yearly_revenues[year]

    # Không bị xóa/thêm record (Không dùng DELETE/INSERT bậy bạ)
    assert len(db_state_after) == len(db_snapshot_before)

    # Dữ liệu bên trong từng record vẫn vẹn nguyên, không bị UPDATE nhầm
    for i in range(len(db_state_after)):
        assert db_state_after[i].month == db_snapshot_before[i].month
        assert db_state_after[i].revenue == db_snapshot_before[i].revenue