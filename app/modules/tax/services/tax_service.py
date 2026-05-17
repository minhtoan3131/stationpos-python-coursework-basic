from abc import ABC, abstractmethod
from app.modules.tax.dtos.tax_dto import TaxConfigDTO, YearlyTaxReportDTO

class ITaxService(ABC):
    @abstractmethod
    def get_or_create_config(self, year: int) -> TaxConfigDTO:
        """Lấy cấu hình của một năm. Nếu chưa có, trả về cấu hình mặc định (VD: 1 Tỷ, 1% VAT, 0.5% PIT)"""
        pass

    @abstractmethod
    def save_config(self, config: TaxConfigDTO) -> bool:
        """Lưu lại cấu hình do người dùng thiết lập"""
        pass

    @abstractmethod
    def generate_yearly_tax_report(self, year: int) -> YearlyTaxReportDTO:
        """Tổng hợp doanh thu, áp dụng luật thuế và xuất ra báo cáo đầy đủ cho UI"""
        pass