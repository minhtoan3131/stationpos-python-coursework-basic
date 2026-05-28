from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.modules.tax.dtos.tax_dto import TaxConfigDTO, MonthlyRevenueDTO, TaxLedgerDTO, TaxLedgerDetailDTO


class ITaxReportRepository(ABC):
    @abstractmethod
    def get_monthly_revenue_by_year(self, year: int) -> List[MonthlyRevenueDTO]:
        """Lấy danh sách doanh thu gộp và tổng giá vốn (COGS) theo từng tháng trong một năm cụ thể."""
        pass

class ITaxLedgerRepository(ABC):
    @abstractmethod
    def get_ledger_by_year(self, year: int) -> Optional[TaxLedgerDTO]:
        """Tìm kiếm chứng từ tổng quan sổ cái theo năm tài chính."""
        pass

    @abstractmethod
    def get_all_ledgers(self) -> List[TaxLedgerDTO]:
        """Lấy toàn bộ danh sách các năm quyết toán thuế đổ lên bảng Master bên trái (Tab 2)."""
        pass

    @abstractmethod
    def save_ledger(self, ledger: TaxLedgerDTO) -> int:
        """Lưu mới hoặc cập nhật bản ghi Master Sổ cái. Trả về ID tự tăng của bản ghi vừa xử lý."""
        pass

    @abstractmethod
    def update_ledger_status(self, year: int, status: str, finalized_at: Optional[datetime]) -> bool:
        """Kích hoạt khi nhập đúng mã PIN: Chuyển trạng thái sang 'CLOSED' và lưu mốc thời gian khóa sổ."""
        pass

    @abstractmethod
    def get_ledger_details(self, ledger_id: int) -> List[TaxLedgerDetailDTO]:
        """Lấy danh sách chi tiết dữ liệu 12 tháng đã đóng băng cứng phục vụ bảng bên phải (Tab 2)."""
        pass

    @abstractmethod
    def save_ledger_details(self, ledger_id: int, details: List[TaxLedgerDetailDTO]) -> bool:
        """Lưu trữ hàng loạt 12 tháng đóng băng cứng (Tự động dọn dẹp chi tiết cũ nếu ghi đè Bản nháp)."""
        pass