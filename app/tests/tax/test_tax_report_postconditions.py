import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Optional

from app.modules.tax.dtos.tax_dto import TaxLedgerDTO, TaxLedgerDetailDTO, MonthlyRevenueDTO
from app.modules.tax.services.impl.tax_service_impl import TaxService


class FakeTaxLedgerRepository:
    def __init__(self):
        self.ledgers = {}  # Key: year -> TaxLedgerDTO
        self.ledger_details = {}  # Key: ledger_id -> List[TaxLedgerDetailDTO]
        self.id_counter = 0

    def get_ledger_by_year(self, year: int) -> Optional[TaxLedgerDTO]:
        return self.ledgers.get(year)

    def get_all_ledgers(self) -> List[TaxLedgerDTO]:
        return sorted(list(self.ledgers.values()), key=lambda x: x.apply_year, reverse=True)

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

    def get_ledger_details(self, ledger_id: int) -> List[TaxLedgerDetailDTO]:
        return self.ledger_details.get(ledger_id, [])

    def save_ledger_details(self, ledger_id: int, details: List[TaxLedgerDetailDTO]) -> bool:
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
# FIXTURES
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
# TEST CASES ĐIỀU KIỆN HẬU QUYẾT (POST-CONDITIONS / HAPPY PATH)
# =====================================================================================

def test_postcondition_generate_live_report_flat_rate_happy_path(tax_service, mem_report_repo):
    """
    TC_Post_01: Hậu quyết Tạo báo cáo live - Phương pháp Khoán thành công vượt mong đợi.
    KỲ VỌNG HỘP ĐEN: Khi nạp tham số chuẩn, doanh thu vượt ngưỡng, phương pháp FLAT_RATE:
    - Hàm phải trả về đúng cấu trúc YearlyTaxReportDTO chứa chính xác số liệu năm tài chính.
    - Thuế GTGT tính từ đồng doanh thu đầu tiên. Thuế TNCN tính trên phần chênh lệch vượt ngưỡng.
    - Mảng chi tiết trả về cam kết đủ 12 phần tử, không được rách lưới.
    """
    year = 2026
    # 1. Arrange: Tổng doanh thu 2 Tỷ phát sinh đều đặn ở Tháng 1 và Tháng 2 (Mỗi tháng 1 Tỷ)
    mem_report_repo.db_revenues[year] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('1000000000'), total_cost=Decimal('0')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('1000000000'), total_cost=Decimal('0'))
    ]

    # 2. Act: Gọi hàm tính toán live tại Cửa ngõ
    report = tax_service.generate_yearly_tax_report_live(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5'), pit_method='FLAT_RATE'
    )

    # 3. Assert: Kiểm chứng cam kết đầu ra (Post-conditions khẳng định)
    assert report.year == year
    assert report.total_revenue == Decimal('2000000000')
    assert report.is_over_threshold is True

    # Tính toán kinh tế vĩ mô:
    # Tổng VAT = 2 Tỷ * 1% = 20,000,000 VND
    # Tổng PIT = (2 Tỷ - 1 Tỷ Ngưỡng) * 0.5% = 5,000,000 VND
    # Tổng thuế năm = 25,000,000 VND
    assert report.total_tax_amount == Decimal('25000000')

    # Cam kết cấu hình hiển thị 12 dòng bảng biểu
    assert len(report.monthly_details) == 12

    # Kiểm tra tỷ trọng phân bổ của Tháng 1 (Gánh 50% doanh thu năm -> Gánh 50% tiền thuế = 12.5M)
    m1_detail = report.monthly_details[0]
    assert m1_detail.month == 1
    assert m1_detail.revenue == Decimal('1000000000')
    assert m1_detail.vat_amount == Decimal('10000000')  # 20M * 50%
    assert m1_detail.pit_amount == Decimal('2500000')  # 5M * 50%
    assert m1_detail.total_tax == Decimal('12500000')


def test_postcondition_generate_live_report_bookkeeping_happy_path(tax_service, mem_report_repo):
    """
    TC_Post_02: Hậu quyết Tạo báo cáo live - Phương pháp Sổ sách thành công vượt mong đợi.
    KỲ VỌNG HỘP ĐEN: Khi chọn BOOKKEEPING, Thuế TNCN phải tính trên Lợi nhuận (Doanh thu - Chi phí) * %, không trừ ngưỡng.
    """
    year = 2026
    # 1. Arrange: Doanh thu 2 Tỷ, Chi phí vận hành cửa hàng hết 1 Tỷ -> Lợi nhuận phát sinh = 1 Tỷ
    mem_report_repo.db_revenues[year] = [
        MonthlyRevenueDTO(month=4, revenue=Decimal('2000000000'), total_cost=Decimal('1000000000'))
    ]

    # 2. Act: Thực thi Use Case dự toán live
    report = tax_service.generate_yearly_tax_report_live(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('15.0'), pit_method='BOOKKEEPING'
    )

    # 3. Assert: Kiểm chứng đầu ra
    # Tổng VAT = 2 Tỷ * 1% = 20,000,000 VND
    # Tổng PIT = (2 Tỷ Doanh thu - 1 Tỷ Chi phí) * 15% Thuế suất Sổ sách = 150,000,000 VND
    # Tổng nghĩa vụ thuế năm = 170,000,000 VND
    assert report.total_tax_amount == Decimal('170000000')


def test_postcondition_stage_temporary_ledger_new_record_happy_path(tax_service, mem_report_repo, mem_ledger_repo):
    """
    TC_Post_03: Hậu quyết Kết xuất chứng từ mới vào kho Sổ cái lịch sử thành công.
    KỲ VỌNG HỘP ĐEN: Khi năm tài chính chưa từng tồn tại chứng từ nháp, lệnh gọi phải:
    - Trả về True thông báo kết xuất thành công.
    - Tự động sinh một dòng Master trong bảng `tax_ledger` ở trạng thái 'DRAFT'.
    - Đóng gói trọn vẹn bộ 3 thông số định biên chỉnh tự do trên UI găm chặt vào các cột Header Master.
    - Sinh chính xác 12 dòng con đóng băng mảng chi tiết tháng trong bảng `tax_ledger_details`.
    """
    year = 2026
    # 1. Arrange: Khẳng định DB ban đầu trống rỗng hoàn toàn cho năm 2026
    assert mem_ledger_repo.get_ledger_by_year(year) is None
    mem_report_repo.db_revenues[year] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('2000000000'), total_cost=Decimal('500000000'))]

    # 2. Act: Gọi hành động kết xuất sang Tab 2
    is_success = tax_service.stage_temporary_ledger(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5'), pit_method='FLAT_RATE'
    )

    # 3. Assert: Kiểm chứng toàn vẹn kho dữ liệu sau kết xuất
    assert is_success is True

    # Kiểm chứng dòng Master
    inserted_master = mem_ledger_repo.get_ledger_by_year(year)
    assert inserted_master is not None
    assert inserted_master.apply_year == year
    assert inserted_master.status == 'DRAFT'  # Bắt buộc ở trạng thái mở duyệt nháp
    assert inserted_master.total_revenue == Decimal('2000000000')
    assert inserted_master.total_cost == Decimal('500000000')

    # Chốt chặn hậu quyết: Đóng gói thành công bộ thông số chứng từ cấu hình
    assert inserted_master.threshold_amount == Decimal('1000000000')
    assert inserted_master.vat_percent == Decimal('1.0')
    assert inserted_master.pit_percent == Decimal('0.5')
    assert inserted_master.pit_method == 'FLAT_RATE'
    assert inserted_master.finalized_at is None

    # Kiểm chứng mảng 12 dòng con Details đóng băng
    inserted_lines = mem_ledger_repo.get_ledger_details(inserted_master.id)
    assert len(inserted_lines) == 12


def test_postcondition_stage_ledger_updates_existing_draft_in_place(tax_service, mem_ledger_repo, mem_report_repo):
    """
    TC_Post_04: Hậu quyết Kết xuất đè, cập nhật tại chỗ Bản nháp cũ thành công.
    KỲ VỌNG HỘP ĐEN: Nếu năm tài chính đã có sẵn một Bản nháp từ trước, lệnh kết xuất mới phải thực hiện
    cập nhật ghi đè số liệu trực tiếp lên dòng Master cũ, giữ nguyên ID gốc, tuyệt đối không đẻ thêm dòng mới gây trùng lặp dữ liệu.
    """
    year = 2026
    # 1. Arrange: Cài sẵn bản ghi nháp phiên bản cũ (V1) có ID gốc là 88
    old_draft = TaxLedgerDTO(
        id=88, apply_year=year, total_revenue=Decimal('100'), total_cost=Decimal('0'),
        final_vat_amount=Decimal('1'), final_pit_amount=Decimal('1'), pit_method='FLAT_RATE',
        status='DRAFT', threshold_amount=Decimal('1000000000'), vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5'),
        finalized_at=None
    )
    mem_ledger_repo.ledgers[year] = old_draft

    # Doanh thu sống mới thay đổi dưới xưởng hóa đơn
    mem_report_repo.db_revenues[year] = [MonthlyRevenueDTO(month=1, revenue=Decimal('3000000000'))]

    # 2. Act: Tiến hành gọi Use Case kết xuất ghi đè với thông số cấu hình mới tinh (V2)
    res = tax_service.stage_temporary_ledger(
        year=year, threshold=Decimal('1200000000'), vat_percent=Decimal('2.0'),
        pit_percent=Decimal('1.0'), pit_method='FLAT_RATE'
    )

    # 3. Assert: Khẳng định đầu ra cập nhật tại chỗ bảo toàn ID khóa
    assert res is True
    current_ledger = mem_ledger_repo.get_ledger_by_year(year)
    assert current_ledger.id == 88, "LỖI LỚN: Kết xuất đè làm gãy cấu trúc ID Master cũ (Yêu cầu giữ nguyên ID cập nhật tại chỗ)."
    assert current_ledger.threshold_amount == Decimal('1200000000'), "Số liệu cấu hình mới chưa ghi đè thành công."
    assert current_ledger.vat_percent == Decimal('2.0')


def test_postcondition_close_and_freeze_ledger_happy_path(tax_service, mem_ledger_repo):
    """
    TC_Post_05: Hậu quyết Khóa sổ vĩnh viễn kỳ quyết toán thuế thành công.
    KỲ VỌNG HỘP ĐEN: Sau khi Controller xác thực mã PIN bảo vệ chuẩn xác, lệnh gọi dịch vụ phải:
    - Chuyển trạng thái bảo mật của dòng Master từ 'DRAFT' thành từ khóa cứng 'CLOSED'.
    - Đóng dấu mốc thời gian hệ thống thực tế chốt sổ vĩnh viễn vào cột 'finalized_at'.
    - Trả về True thông báo đóng băng thành công.
    """
    year = 2026
    # 1. Arrange: Đưa năm 2026 về trạng thái mở nháp DRAFT chờ duyệt đóng
    mem_ledger_repo.ledgers[year] = TaxLedgerDTO(
        id=45, apply_year=year, total_revenue=Decimal('100'), total_cost=Decimal('0'),
        final_vat_amount=Decimal('1'), final_pit_amount=Decimal('1'), pit_method='FLAT_RATE',
        status='DRAFT', threshold_amount=Decimal('1000000000'), vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5'),
        finalized_at=None
    )

    # 2. Act: Kích hoạt Use Case khóa sổ
    is_frozen = tax_service.close_and_freeze_ledger(year=year)

    # 3. Assert: Kiểm chứng trạng thái hóa đá bất biến
    assert is_frozen is True

    finalized_record = mem_ledger_repo.get_ledger_by_year(year)
    assert finalized_record.status == 'CLOSED', "LỖI: Trạng thái chứng từ chưa được đóng băng cứng sang CLOSED."
    assert finalized_record.finalized_at is not None, "LỖI: Chưa ghi nhận vết dấu ngày giờ chốt sổ pháp lý vĩnh viễn."
    # Đảm bảo vết thời gian ghi nhận khớp khít với chu kỳ thực thi thời gian thực của RAM
    assert (datetime.now() - finalized_record.finalized_at) < timedelta(seconds=2)