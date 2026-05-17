import pytest
from decimal import Decimal
from app.modules.tax.dtos.tax_dto import TaxConfigDTO
from app.modules.tax.services.impl.tax_service_impl import TaxService


# ==========================================
# SETUP FAKE REPOSITORIES & UOW
# ==========================================
class FakeTaxConfigRepo:
    def __init__(self):
        self.configs = {}
        # Biến "gián điệp" để theo dõi xem hàm save có bị gọi bậy bạ không
        self.save_called_count = 0

    def get_config_by_year(self, year: int):
        return self.configs.get(year)

    def save_config(self, config: TaxConfigDTO):
        self.configs[config.apply_year] = config
        self.save_called_count += 1
        return True


class FakeUnitOfWork:
    def __init__(self):
        self.tax_config_repo = FakeTaxConfigRepo()
        # Không cần FakeTaxReportRepo vì Use Case 1 không đụng đến Doanh thu

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
    return TaxService(lambda: uow)


# ==========================================
# TEST CASES (PRE, POST, INVARIANTS)
# ==========================================

def test_get_config_handles_out_of_bound_year_safely(tax_service, uow):
    """
    TC_Pre_01: Truyền vào năm bất thường (VD: -99).
    Kỳ vọng: Hệ thống không crash, vẫn khởi tạo cấu hình mặc định cho năm đó.
    """
    abnormal_year = -99

    config = tax_service.get_or_create_config(abnormal_year)

    assert config.apply_year == abnormal_year
    assert config.threshold_amount == Decimal('1000000000')


def test_get_config_returns_existing_data(tax_service, uow):
    """
    TC_Post_01: Cấu hình đã tồn tại trong DB.
    Kỳ vọng: Trả về đúng cấu hình đó, không phải cấu hình mặc định.
    """
    year = 2024
    # GIVEN: Cố tình setup một cấu hình "dị" để dễ nhận biết
    uow.tax_config_repo.configs[year] = TaxConfigDTO(
        apply_year=year,
        threshold_amount=Decimal('500000000'),  # 500 triệu
        vat_percent=Decimal('2.5'),
        pit_percent=Decimal('1.5')
    )

    # WHEN
    config = tax_service.get_or_create_config(year)

    # THEN
    assert config.threshold_amount == Decimal('500000000')
    assert config.vat_percent == Decimal('2.5')


def test_get_config_creates_and_saves_default_if_missing(tax_service, uow):
    """
    TC_Post_02: Chưa có cấu hình.
    Kỳ vọng: Trả về cấu hình mặc định (1 Tỷ) VÀ phải LƯU xuống DB.
    """
    year = 2025
    assert uow.tax_config_repo.get_config_by_year(year) is None

    # WHEN
    config = tax_service.get_or_create_config(year)

    # THEN 1: Output trả về đúng chuẩn mặc định
    assert config.threshold_amount == Decimal('1000000000')
    assert config.vat_percent == Decimal('1.0')

    # THEN 2: Side-effect (Bắt buộc phải lưu)
    assert uow.tax_config_repo.save_called_count == 1
    assert uow.tax_config_repo.configs.get(year) is not None


def test_invariant_never_returns_none(tax_service, uow):
    """
    TC_Inv_01: Cam kết kiểu trả về.
    Kỳ vọng: Dù DB có dữ liệu hay không, tuyệt đối không bao giờ trả về None.
    """
    # Case 1: DB trống
    assert tax_service.get_or_create_config(2020) is not None

    # Case 2: DB có dữ liệu
    uow.tax_config_repo.configs[2021] = TaxConfigDTO(2021, Decimal('0'), Decimal('0'), Decimal('0'))
    assert tax_service.get_or_create_config(2021) is not None


def test_invariant_no_mutation_when_config_exists(tax_service, uow):
    """
    TC_Inv_02: Luật Bảo toàn Dữ liệu cũ.
    Kỳ vọng: Nếu đã có cấu hình, hàm chỉ ĐỌC, cấm tuyệt đối việc gọi hàm SAVE làm update thời gian.
    """
    year = 2022
    uow.tax_config_repo.configs[year] = TaxConfigDTO(
        apply_year=year, threshold_amount=Decimal('100'), vat_percent=Decimal('1'), pit_percent=Decimal('1')
    )

    # Ghi nhận số lần gọi hàm save ban đầu (chắc chắn là 0)
    initial_save_count = uow.tax_config_repo.save_called_count

    # WHEN
    _ = tax_service.get_or_create_config(year)

    # THEN: Đảm bảo bộ máy không hề lén lút gọi lệnh lưu dữ liệu
    assert uow.tax_config_repo.save_called_count == initial_save_count