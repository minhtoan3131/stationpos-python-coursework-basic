import pytest
import copy
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Optional

from app.modules.tax.dtos.tax_dto import TaxLedgerDTO, TaxLedgerDetailDTO, MonthlyRevenueDTO
from app.modules.tax.services.impl.tax_service_impl import TaxService




class FakeTaxLedgerRepository:
    def __init__(self):
        self.ledgers = {}  # Bộ nhớ đệm lưu Master. Key: year -> TaxLedgerDTO
        self.ledger_details = {}  # Bộ nhớ đệm lưu Lines. Key: ledger_id -> List[TaxLedgerDetailDTO]
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
        self.db_revenues = {}  # Bộ nhớ đệm lưu hóa đơn mẫu. Key: year -> List[MonthlyRevenueDTO]

    def get_monthly_revenue_by_year(self, year: int) -> List[MonthlyRevenueDTO]:
        # Trả về deepcopy để mô phỏng chính xác hành vi bóc tách bộ nhớ của hệ quản trị DB vật lý
        return copy.deepcopy(self.db_revenues.get(year, []))


class FakeSettingRepository:
    def __init__(self):
        self.settings = {
            'TAX_MID_SCALE_LIMIT': '3000000000',
            'TAX_LARGE_SCALE_LIMIT': '50000000000'
        }

    def get_all_settings(self) -> dict:
        return self.settings


class FakeUnitOfWork:
    """Mô phỏng lớp quản lý giao dịch an toàn, tự động kích hoạt qua Context Manager"""

    def __init__(self, ledger_repo, report_repo, setting_repo):
        self.tax_ledger_repo = ledger_repo
        self.tax_report_repo = report_repo
        self.setting_repo = setting_repo

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


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
    # Tiêm nhà máy sản xuất UOW khép kín luồng xử lý
    uow_factory = lambda: FakeUnitOfWork(mem_ledger_repo, mem_report_repo, mem_setting_repo)
    return TaxService(uow_factory)


# =====================================================================================
# DANH SÁCH CÁC BÀI KIỂM THỬ BẤT BIẾN (SYSTEM INVARIANTS VET CẠN)
# =====================================================================================

def test_invariant_tax_amounts_cannot_be_negative_on_net_loss(tax_service, mem_report_repo):
    """
    BẤT BIẾN 1: Tiền thuế nghĩa vụ không được âm (Non-negative Tax Amount Invariant).
    RÀNG BUỘC NGHIỆP VỤ: Tại Use Case tính toán live, khi áp dụng phương pháp Sổ sách (BOOKKEEPING),
    nếu hộ kinh doanh bị thua lỗ nặng (Chi phí > Doanh thu), số tiền thuế TNCN phát sinh bắt buộc phải ghim bằng 0.
    Tuyệt đối không được xuất hiện số tiền thuế âm trên bảng biểu giao diện.
    """
    year = 2026
    # Arrange: Doanh thu 100M nhưng Giá vốn/Chi phí vận hành vọt lên tới 150M (Lỗ 50M)
    mem_report_repo.db_revenues[year] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('100000000'), total_cost=Decimal('150000000'))
    ]

    # Act: Gọi duy nhất 1 hàm tính toán live tại Cửa ngõ
    report = tax_service.generate_yearly_tax_report_live(
        year=year, threshold=Decimal('0'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('15.0'), pit_method='BOOKKEEPING'
    )

    # Assert: Kiểm chứng chốt chặn bất biến số không âm
    assert report.total_tax_amount >= Decimal('0')
    assert report.monthly_details[0].pit_amount == Decimal(
        '0'), "LỖI BIÊN: Thuế TNCN bị tính ra số âm khi hộ kinh doanh thua lỗ."
    assert report.monthly_details[0].vat_amount == Decimal('1000000'), "VAT vẫn phải thu trên doanh thu thực tế."


def test_invariant_live_recalculation_must_never_mutate_source_database_data(tax_service, mem_report_repo):
    """
    BẤT BIẾN 2: Bảo vệ dữ liệu gốc (No Side-effects / Read-only Source Invariant).
    RÀNG BUỘC NGHIỆP VỤ: Quá trình co kéo thông số để mô phỏng tính toán live diễn ra liên tục trên RAM.
    Hành động này tuyệt đối không được phép làm biến đổi, thêm, bớt hoặc sai lệch mảng dữ liệu hóa đơn gốc dưới DB.
    """
    year = 2026
    original_invoices = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('500000000'), total_cost=Decimal('100000000')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('300000000'), total_cost=Decimal('50000000'))
    ]
    mem_report_repo.db_revenues[year] = original_invoices

    # Chụp ảnh snapshot trạng thái DB RAM trước khi gọi hàm
    db_snapshot_before = copy.deepcopy(mem_report_repo.db_revenues[year])

    # Act: Kích hoạt Use Case dự toán live
    _ = tax_service.generate_yearly_tax_report_live(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5'), pit_method='FLAT_RATE'
    )

    # Assert: Đối chiếu chéo trạng thái sau khi tính toán
    db_state_after = mem_report_repo.db_revenues[year]
    assert len(db_state_after) == len(db_snapshot_before)
    for i in range(len(db_state_after)):
        assert db_state_after[i].revenue == db_snapshot_before[
            i].revenue, "LỖI HỆ THỐNG: Dữ liệu hóa đơn gốc bị biến đổi trong RAM khi tính toán live."
        assert db_state_after[i].total_cost == db_snapshot_before[i].total_cost


def test_invariant_master_and_detail_tax_sums_must_be_perfectly_synchronized(tax_service, mem_report_repo,
                                                                             mem_ledger_repo):
    """
    BẤT BIẾN 3: Đồng bộ toàn vẹn toán học song phương (Master-Detail Sum Integrity).
    RÀNG BUỘC NGHIỆP VỤ: Khi chốt chứng từ tạm thời, tổng số tiền thuế (VAT và PIT) lưu trữ tại dòng Header Master (tax_ledger)
    bắt buộc phải bằng chính xác tuyệt đối tổng mảng 12 tháng con cộng lại ở bảng Detail (tax_ledger_details).
    Chặn đứng lỗi lệch 1 đồng do thuật toán chia tỷ trọng làm rách hàng thập phân.
    """
    year = 2026
    # Mồi doanh thu số lẻ cực hạn chia không hết cho 3 tháng để ép lỗi làm tròn số thập phân
    mem_report_repo.db_revenues[year] = [
        MonthlyRevenueDTO(month=1, revenue=Decimal('333333333')),
        MonthlyRevenueDTO(month=2, revenue=Decimal('333333333')),
        MonthlyRevenueDTO(month=3, revenue=Decimal('333333334'))
    ]

    # Act: Gọi Use Case kết xuất chứng từ nháp
    success = tax_service.stage_temporary_ledger(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5'), pit_method='FLAT_RATE'
    )
    assert success is True

    # Assert: Thu hồi thực thể từ DB RAM ra kiểm tra tính cân đối
    master = mem_ledger_repo.ledgers[year]
    details = mem_ledger_repo.ledger_details[master.id]

    sum_details_vat = sum(d.vat_amount for d in details)
    sum_details_pit = sum(d.pit_amount for d in details)

    assert sum_details_vat == master.final_vat_amount, "LỖI TOÁN HỌC: Tổng phân bổ VAT 12 tháng không khớp khít với Header chứng từ."
    assert sum_details_pit == master.final_pit_amount, "LỖI TOÁN HỌC: Tổng phân bổ PIT 12 tháng không khớp khít với Header chứng từ."


def test_invariant_ledger_details_must_always_contain_exactly_twelve_months(tax_service, mem_report_repo,
                                                                            mem_ledger_repo):
    """
    BẤT BIẾN 4: Ma trận cấu hình liên tục 12 tháng (Chronological Grid Matrix Invariant).
    RÀNG BUỘC NGHIỆP VỤ: Dù hộ kinh doanh có những tháng đóng cửa không bán hàng, mảng chi tiết lưu vào DB lịch sử
    bắt buộc luôn luôn phải có cấu trúc đầy đủ và liên tục đúng 12 dòng ứng với 12 tháng tuần tiến từ 1 đến 12.
    Đồng thời, hàm kết xuất đè phải dọn sạch (Purge) 12 dòng cũ, không để rò rỉ (leak) dữ liệu thành 24 dòng.
    """
    year = 2026
    # 1. Khởi tạo sẵn 12 tháng dữ liệu nháp cũ của dòng Master này trong DB RAM
    mem_ledger_repo.ledgers[year] = TaxLedgerDTO(
        id=1, apply_year=year, total_revenue=Decimal('0'), total_cost=Decimal('0'),
        final_vat_amount=Decimal('0'), final_pit_amount=Decimal('0'), pit_method='FLAT_RATE',
        status='DRAFT', threshold_amount=Decimal('1000000000'), vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5')
    )
    mem_ledger_repo.ledger_details[1] = [
        TaxLedgerDetailDTO(1, 1, m, Decimal('10'), Decimal('0'), Decimal('0'), Decimal('0')) for m in range(1, 13)]

    # Mồi dữ liệu mới: Cửa hàng đổi sang mô hình kinh doanh đặc thù, chỉ bán đúng tháng 7
    mem_report_repo.db_revenues[year] = [MonthlyRevenueDTO(month=7, revenue=Decimal('2000000000'))]

    # Act: Gọi hàm kết xuất đè lên Bản nháp có sẵn
    tax_service.stage_temporary_ledger(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5'), pit_method='FLAT_RATE'
    )

    # Assert: Đếm số lượng thực thể con sau khi ghi đè
    details = mem_ledger_repo.ledger_details[1]
    assert len(
        details) == 12, "LỖI CẤU TRÚC: Kết xuất đè bản nháp làm dôi ra dòng thừa hoặc leak rác bộ nhớ (Phải bằng đúng 12 dòng)."

    # Kiểm tra tính tuần tiến liên tục từ tháng 1 đến tháng 12
    for idx, d_row in enumerate(details):
        assert d_row.month == idx + 1, "LỖI GRID: Chỉ số dòng thời gian bị đứt gãy hoặc đảo lộn."
        if d_row.month != 7:
            assert d_row.revenue == Decimal('0'), "LỖI: Tháng trống không có doanh thu nhưng lại gánh số liệu rác cũ."


def test_invariant_frozen_ledger_state_is_absolutely_immutable(tax_service, mem_ledger_repo, mem_report_repo):
    """
    BẤT BIẾN 5: Tính Bất biến trạng thái Khóa sổ vĩnh viễn (State Machine Lockout Invariant).
    RÀNG BUỘC BẢO MẬT: Khi một năm tài chính đã được đóng băng bằng mã PIN bảo vệ thành công ('CLOSED'),
    toàn bộ trường dữ liệu số tiền, ngày giờ chốt sổ (`finalized_at`) ở Header Master trở thành Read-only.
    Mọi nỗ lực gọi hàm kết xuất đè từ Tab 1 bắt buộc phải bị hệ thống từ chối và trả về False ngay lập tức.
    """
    year = 2024
    locked_date = datetime(2024, 12, 31, 17, 0, 0)

    # Cài cắm sẵn chứng từ đã CLOSED vĩnh viễn vao DB RAM
    mem_ledger_repo.ledgers[year] = TaxLedgerDTO(
        id=5, apply_year=year, total_revenue=Decimal('5000000000'), total_cost=Decimal('1000000000'),
        final_vat_amount=Decimal('50000000'), final_pit_amount=Decimal('20000000'), pit_method='BOOKKEEPING',
        status='CLOSED', threshold_amount=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('17.0'),
        finalized_at=locked_date
    )

    # Mồi dữ liệu sống có doanh thu mới xuất hiện sau khi đã khóa sổ
    mem_report_repo.db_revenues[year] = [MonthlyRevenueDTO(month=1, revenue=Decimal('99999999999'))]

    # Act: Gọi hàm yêu cầu kết xuất đè lên chứng từ đã đóng sổ vĩnh viễn
    is_success = tax_service.stage_temporary_ledger(
        year=year, threshold=Decimal('1000000000'), vat_percent=Decimal('1.0'),
        pit_percent=Decimal('17.0'), pit_method='BOOKKEEPING'
    )

    # Assert: Khẳng định tính bất biến
    assert is_success is False, "⚠️ LỖI BẢO MẬT NGHIÊM TRỌNG: Hệ thống cho phép ghi đè/phá hủy kỳ tính thuế đã chốt sổ pháp lý vĩnh viễn."

    # Đảm bảo dữ liệu Master cũ không suy suyển 1 đồng
    current_ledger = mem_ledger_repo.ledgers[year]
    assert current_ledger.total_revenue == Decimal('5000000000')
    assert current_ledger.finalized_at == locked_date, "LỖI: Mốc thời gian chốt sổ pháp lý gốc bị thay đổi."