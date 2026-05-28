from abc import ABC, abstractmethod
from typing import List, Optional

from app.modules.tax.dtos.tax_dto import TaxConfigDTO, MonthlyRevenueDTO


class ITaxConfigRepository(ABC):
    @abstractmethod
    def get_config_by_year(self, year: int) -> Optional[TaxConfigDTO]:
        """Lấy cấu hình thuế theo năm (bao gồm cả phương pháp tính thuế TNCN). Trả về None nếu chưa có."""
        pass

    @abstractmethod
    def save_config(self, config: TaxConfigDTO) -> bool:
        """Lưu mới hoặc cập nhật cấu hình thuế cho một năm (bao gồm cả phương pháp tính thuế TNCN)."""
        pass

class ITaxReportRepository(ABC):
    @abstractmethod
    def get_monthly_revenue_by_year(self, year: int) -> List[MonthlyRevenueDTO]:
        """Lấy danh sách doanh thu gộp và tổng giá vốn (COGS) theo từng tháng trong một năm cụ thể."""
        pass