# File: app/modules/report/services/impl/report_service_impl.py
import datetime
from app.modules.report.services.report_service import ReportService
from app.modules.report.dtos.report_dto import DashboardReportDTO
from app.modules.report.utils.report_mapper import ReportMapper
from app.core.exceptions.validation_exception import ValidationException


class ReportServiceImpl(ReportService):
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def get_dashboard_report(self, start_date: str, end_date: str) -> DashboardReportDTO:
        try:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValidationException("Định dạng ngày bộ lọc không hợp lệ. Phải có dạng YYYY-MM-DD.")

        if start > end:
            raise ValidationException(
                "Ngày bắt đầu không được lớn hơn ngày kết thúc trên bộ lọc!")

        with self.uow_factory() as uow:
            raw_kpis = uow.report_repo.get_kpi_metrics(start_date, end_date)
            raw_trend = uow.report_repo.get_revenue_trend(start_date, end_date)
            raw_top = uow.report_repo.get_top_products(start_date, end_date)
            raw_trans = uow.report_repo.get_transaction_history(start_date, end_date)
            raw_inventory = uow.report_repo.get_inventory_valuation()

            return DashboardReportDTO(
                kpis=ReportMapper.map_kpi(raw_kpis),
                revenue_trend=ReportMapper.map_revenue_trend(raw_trend),
                top_products=ReportMapper.map_top_products(raw_top),
                transactions=ReportMapper.map_transaction_history(raw_trans),
                inventory_valuation=ReportMapper.map_inventory_valuation(raw_inventory)
            )

    def get_daily_activity_feed(self, date_str: str) -> list:
        """Trộn luồng và chuẩn hóa 100% kiểu dữ liệu String cho trục thời gian để chống sập thuật toán sort"""
        with self.uow_factory() as uow:
            raw_transactions = uow.report_repo.get_transaction_history(date_str, date_str)
            raw_purchase_orders = uow.report_repo.get_daily_purchase_orders(date_str)

            combined = []
            for trans in raw_transactions:
                # Trích xuất chuỗi thời gian an toàn
                dt_field = trans.get('created_at', '')
                dt_str = dt_field.strftime("%Y-%m-%d %H:%M") if isinstance(dt_field, datetime.datetime) else str(
                    dt_field)

                combined.append({
                    'type': 'SALE',
                    'code': trans.get('invoice_code', ''),
                    'created_at': dt_str,
                    'amount': float(trans.get('total_amount', 0)),
                    'detail': trans.get('payment_method', '')
                })

            for po in raw_purchase_orders:
                # Ép chặt đối tượng datetime trong bảng purchase_orders về chuỗi văn bản trùng khớp
                dt_field = po.get('created_at')
                dt_str = dt_field.strftime("%Y-%m-%d %H:%M") if isinstance(dt_field, datetime.datetime) else str(
                    dt_field)

                combined.append({
                    'type': 'IMPORT',
                    'code': po.get('code', ''),
                    'created_at': dt_str,
                    'amount': float(po.get('total_amount') or 0),
                    'detail': po.get('supplier_name') or "Không rõ"
                })

            # Thuật toán sắp xếp tuyến tính chạy trơn tru tuyệt đối vì toàn bộ key 'created_at' đều là String
            combined.sort(key=lambda x: x['created_at'], reverse=True)
            return combined