from abc import ABC, abstractmethod
from app.modules.report.dtos.report_dto import DashboardReportDTO

class ReportService(ABC):
    @abstractmethod
    def get_dashboard_report(self, start_date: str, end_date: str) -> DashboardReportDTO:
        """
        Lấy toàn bộ dữ liệu báo cáo cho màn hình Dashboard trong một khoảng thời gian.
        Trả về một đối tượng DashboardReportDTO duy nhất chứa đầy đủ KPI, Biểu đồ, và Bảng.
        """
        pass