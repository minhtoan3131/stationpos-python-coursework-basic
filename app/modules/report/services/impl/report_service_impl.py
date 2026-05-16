import datetime

from app.modules.report.services.report_service import ReportService
from app.modules.report.dtos.report_dto import DashboardReportDTO
from app.modules.report.utils.report_mapper import ReportMapper

class ReportServiceImpl(ReportService):
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def get_dashboard_report(self, start_date: str, end_date: str) -> DashboardReportDTO:

        try:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError("Định dạng ngày không hợp lệ. Phải có dạng YYYY-MM-DD.")

            # Kiểm tra logic đảo lộn thời gian
        if start > end:
            raise ValueError("Ngày bắt đầu không được lớn hơn ngày kết thúc!")

        with self.uow_factory() as uow:
            # Gọi Repository lấy Raw Data
            raw_kpis = uow.report_repo.get_kpi_metrics(start_date, end_date)
            raw_trend = uow.report_repo.get_revenue_trend(start_date, end_date)
            raw_top = uow.report_repo.get_top_products(start_date, end_date)
            raw_trans = uow.report_repo.get_transaction_history(start_date, end_date)
            raw_inventory = uow.report_repo.get_inventory_valuation()

            # Gọi Mapper để đóng gói thành DTO
            return DashboardReportDTO(
                kpis=ReportMapper.map_kpi(raw_kpis),
                revenue_trend=ReportMapper.map_revenue_trend(raw_trend),
                top_products=ReportMapper.map_top_products(raw_top),
                transactions=ReportMapper.map_transaction_history(raw_trans),
                inventory_valuation=ReportMapper.map_inventory_valuation(raw_inventory)
            )