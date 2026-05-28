import pytest
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from app.modules.tax.dtos.tax_dto import TaxLedgerDTO, MonthlyRevenueDTO
from app.modules.tax.services.impl.tax_service_impl import TaxService



class FakeTaxLedgerRepository:
    def __init__(self):
        self.ledgers = {}  # Key: year -> TaxLedgerDTO
        self.ledger_details = {}  # Key: ledger_id -> List
        self.id_counter = 0

    def get_ledger_by_year(self, year: int) -> Optional[TaxLedgerDTO]:
        return self.ledgers.get(year)

    def get_all_ledgers(self) -> List[TaxLedgerDTO]:
        return list(self.ledgers.values())

    def save_ledger(self, ledger: TaxLedgerDTO) -> int:
        if ledger.id is None:
            self.id_counter += 1
            ledger.id = self.id_counter
        self.ledgers[ledger.apply_year] = ledger
        return ledger.id

    def update_ledger_status(self, year: int, status: str, finalized_at: Optional[datetime]) -> bool:
        ledger = self.ledgers.get(year)
        if ledger and ledger.status == 'DRAFT':
            ledger.status = status
            ledger.finalized_at = finalized_at
            return True
        return False

    def get_ledger_details(self, ledger_id: int) -> List:
        return self.ledger_details.get(ledger_id, [])

    def save_ledger_details(self, ledger_id: int, details: List) -> bool:
        self.ledger_details[ledger_id] = details
        return True


class FakeTaxReportRepository:
    def __init__(self):
        self.db_revenues = {}

    def get_monthly_revenue_by_year(self, year: int) -> List[MonthlyRevenueDTO]:
        return self.db_revenues.get(year, [])


class FakeSettingRepository:
    def __init__(self):
        self.settings = {
            'TAX_MID_SCALE_LIMIT': '3000000000',
            'TAX_LARGE_SCALE_LIMIT': '50000000000'
        }

    def get_all_settings(self) -> dict:
        return self.settings


class FakeUnitOfWork:
    def __init__(self, ledger_repo, report_repo, setting_repo):
        self.tax_ledger_repo = ledger_repo
        self.tax_report_repo = report_repo
        self.setting_repo = setting_repo

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


# =====================================================================================
# FIXTURES KHỞI TẠO ĐIỂM TỰA CỬA NGÕ KIỂM THỬ CÔNG KHAI
# =====================================================================================

@pytest.fixture
def mem_ledger_repo():
    return FakeTaxLedgerRepository()


@pytest.fixture
def mem_report_repo():
    return FakeTaxReportRepository()


@pytest.fixture
def mem_setting_repo():
    return FakeSettingRepository()


@pytest.fixture
def tax_service(mem_ledger_repo, mem_report_repo, mem_setting_repo):
    uow_factory = lambda: FakeUnitOfWork(mem_ledger_repo, mem_report_repo, mem_setting_repo)
    return TaxService(uow_factory)


# =====================================================================================
# KIỂM THỬ ĐIỀU KIỆN TIÊN QUYẾT (PRE-CONDITIONS)
# =====================================================================================

@pytest.mark.parametrize("bad_vat, bad_pit, bad_threshold", [
    (Decimal('-1.0'), Decimal('0.5'), Decimal('1000000000')),  # Thuế suất GTGT âm bóp méo dòng tiền
    (Decimal('1.0'), Decimal('-0.5'), Decimal('1000000000')),  # Thuế suất TNCN âm trái luật
    (Decimal('1.0'), Decimal('0.5'), Decimal('-500000000')),  # Mức ngưỡng miễn thuế âm vô lý
])
def test_precondition_negative_configuration_values_must_be_rejected(tax_service, bad_vat, bad_pit, bad_threshold):
    """
    TC_Pre_01: Tiên quyết tính hợp lệ của tham số số học (Input Param Validation).
    RÀNG BUỘC TIÊN QUYẾT: Tránh lỗ hổng tràn số hoặc lỗi tính ngược dòng tiền thuế nộp về âm.
    KỲ VỌNG HỘP ĐEN: Khi người dùng gõ hoặc cố tình truyền các con số cấu hình định biên nhỏ hơn 0,
    Use Case tại cửa ngõ dịch vụ bắt buộc phải chủ động ném ra lỗi `ValueError` để chặn đứng từ đầu.
    """
    # 1. Arrange: Thiết lập đầu vào cấu hình độc hại thông qua tham số parametrize
    year = 2026

    # 2. Act & 3. Assert: Ép kiểm tra rào chắn ném lỗi ValueError lập tức
    with pytest.raises(ValueError, match=".*không được phép nhỏ hơn 0.*"):
        tax_service.generate_yearly_tax_report_live(
            year=year, threshold=bad_threshold, vat_percent=bad_vat,
            pit_percent=bad_pit, pit_method='FLAT_RATE'
        )


def test_precondition_invalid_pit_method_string_must_be_rejected(tax_service):
    """
    TC_Pre_02: Tiên quyết tính hợp lệ của danh mục phương pháp (Domain Bound Validation).
    RÀNG BUỘC TIÊN QUYẾT: Phương pháp tính thuế TNCN đẩy xuống bắt buộc phải nằm trong danh mục luật định.
    KỲ VỌNG HỘP ĐEN: Nếu truyền một chuỗi văn bản lạ hoắc (Ví dụ: 'LUY_TIEN_BAC_THANG'),
    hệ thống từ chối xử lý và quăng lỗi ValueError để bảo vệ tính nhất quán của State Machine dữ liệu.
    """
    # 1. Arrange: Đầu vào sai danh mục
    year = 2026

    # 2. Act & 3. Assert: Gọi hàm và bắt lỗi tiên quyết
    with pytest.raises(ValueError, match=".*Phương pháp tính thuế không hợp lệ.*"):
        tax_service.generate_yearly_tax_report_live(
            year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
            pit_percent=Decimal('0.5'), pit_method='LUY_TIEN_BAC_THANG'
        )


def test_precondition_stage_ledger_fails_immediately_if_target_year_is_already_closed(tax_service, mem_ledger_repo,
                                                                                      mem_report_repo):
    """
    TC_Pre_03: Tiên quyết rào chặn trạng thái thực thể (State Guard Pre-condition).
    RÀNG BUỘC TIÊN QUYẾT: Kiểm tra tính toàn vẹn trạng thái an toàn của năm tài chính trước khi thực thi Use Case ghi dữ liệu.
    KỲ VỌNG HỘP ĐEN: Nếu kỳ thuế năm đó đã được chốt và khóa chặt vĩnh viễn ('CLOSED') bằng mã PIN từ trước,
    thì hành động gọi hàm `stage_temporary_ledger` phải thất bại ngay lập tức (`return False`),
    không được phép gọi xuống bất kỳ câu lệnh SQL chỉnh sửa dữ liệu con nào phía dưới.
    """
    year = 2026
    # 1. Arrange: Cố tình đặt trạng thái kỳ thuế năm 2026 đã CLOSED cứng trong DB RAM
    mem_ledger_repo.ledgers[year] = TaxLedgerDTO(
        id=12, apply_year=year, total_revenue=Decimal('100'), total_cost=Decimal('0'),
        final_vat_amount=Decimal('1'), final_pit_amount=Decimal('1'), pit_method='FLAT_RATE',
        status='CLOSED', threshold_amount=Decimal('1000000000'), vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5'),
        finalized_at=datetime.now()
    )

    # Giả định hóa đơn sống có biến động mới
    mem_report_repo.db_revenues[year] = [MonthlyRevenueDTO(month=1, revenue=Decimal('5000000000'))]

    # 2. Act: Gọi Use Case kết xuất đè lên năm đã khóa vĩnh viễn
    is_allowed = tax_service.stage_temporary_ledger(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5'), pit_method='FLAT_RATE'
    )

    # 3. Assert: Kiểm chứng rào chắn tiên quyết trả về False chặn can thiệp số liệu
    assert is_allowed is False, "LỖI TIÊN QUYẾT: Hệ thống cho phép khởi động tiến trình kết xuất dữ liệu vào một năm đã khóa sổ vĩnh viễn."


def test_precondition_close_and_freeze_ledger_fails_if_no_ledger_record_exists_in_database(tax_service,
                                                                                           mem_ledger_repo):
    """
    TC_Pre_04: Tiên quyết sự tồn tại của thực thể chứng từ (Entity Existence Pre-condition).
    RÀNG BUỘC TIÊN QUYẾT: Bạn không thể chốt sổ hay đóng băng một kỳ thuế rỗng tuếch khi nó chưa từng được người dùng kết xuất tạm thời sang Tab 2.
    KỲ VỌNG HỘP ĐEN: Khi gọi hàm `close_and_freeze_ledger` cho một năm chưa hề tồn tại trong DB,
    Use Case phải từ chối hành động lập tức và trả về `False`.
    """
    # 1. Arrange: Làm sạch bóng DB RAM, năm 2028 chưa từng phát sinh chứng từ
    year = 2028
    assert mem_ledger_repo.get_ledger_by_year(year) is None

    # 2. Act: Cố tình gọi lệnh chốt sổ vĩnh viễn kỳ thuế trống
    result = tax_service.close_and_freeze_ledger(year=year)

    # 3. Assert: Trả về False an toàn, không sinh lỗi NullPointerException hay sập app
    assert result is False, "LỖI TIÊN QUYẾT: Hệ thống cho phép kích hoạt quy trình phê duyệt đóng băng một chứng từ không tồn tại."