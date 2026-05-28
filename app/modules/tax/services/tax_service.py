from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional
from app.modules.tax.dtos.tax_dto import YearlyTaxReportDTO, TaxLedgerDTO, TaxLedgerDetailDTO

class ITaxService(ABC):
    @abstractmethod
    def get_active_draft_ledger_config(self, year: int) -> Optional[TaxLedgerDTO]:
        """Đọc thông số cấu hình từ bản ghi DRAFT của sổ cái nếu có để điền lên UI Tab 1"""
        pass

    @abstractmethod
    def generate_yearly_tax_report_live(self, year: int, threshold: Decimal, vat_percent: Decimal, pit_percent: Decimal, pit_method: str) -> YearlyTaxReportDTO:
        """Tính toán báo cáo động tức thời theo các thông số tự do trên UI phục vụ tính năng phản ứng live"""
        pass

    @abstractmethod
    def stage_temporary_ledger(self, year: int, threshold: Decimal, vat_percent: Decimal, pit_percent: Decimal, pit_method: str) -> bool:
        """Tab 1 -> Tab 2: Lưu/Cập nhật dữ liệu tạm thời vào Sổ cái Master-Detail (Mặc định ở trạng thái DRAFT)"""
        pass

    @abstractmethod
    def get_all_ledgers(self) -> List[TaxLedgerDTO]:
        """Tab 2: Lấy danh sách toàn bộ chứng từ Master Sổ cái đổ lên bảng bên trái"""
        pass

    @abstractmethod
    def get_ledger_details(self, ledger_id: int) -> List[TaxLedgerDetailDTO]:
        """Tab 2: Lấy chi tiết 12 tháng đóng băng của năm tài chính tương ứng"""
        pass

    @abstractmethod
    def close_and_freeze_ledger(self, year: int) -> bool:
        """Tab 2: Xác thực mã PIN thành công, đóng băng vĩnh viễn kỳ tính thuế (CLOSED)"""
        pass

    @abstractmethod
    def get_tax_scale_limits(self) -> tuple[Decimal, Decimal]:
        """Đọc mốc phân khúc quy mô ngầm (Vừa và Lớn) từ bảng system_settings"""
        pass