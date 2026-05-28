from decimal import Decimal
from typing import Callable, List, Optional
from datetime import datetime

from app.core.database.unit_of_work import UnitOfWork
from app.modules.tax.dtos.tax_dto import (
    YearlyTaxReportDTO, MonthlyTaxDetailDTO, TaxLedgerDTO, TaxLedgerDetailDTO
)
from app.modules.tax.services.tax_service import ITaxService
from app.modules.tax.utils.tax_calculator import TaxCalculator


class TaxService(ITaxService):
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self.uow_factory = uow_factory

    def get_active_draft_ledger_config(self, year: int) -> Optional[TaxLedgerDTO]:
        with self.uow_factory() as uow:
            return uow.tax_ledger_repo.get_ledger_by_year(year)

    def get_tax_scale_limits(self) -> tuple[Decimal, Decimal]:
        with self.uow_factory() as uow:
            settings = uow.setting_repo.get_all_settings()
            limit_mid = Decimal(settings.get('TAX_MID_SCALE_LIMIT', '3000000000'))
            limit_large = Decimal(settings.get('TAX_LARGE_SCALE_LIMIT', '50000000000'))
            return limit_mid, limit_large

    def _validate_inputs(self, threshold: Decimal, vat_percent: Decimal, pit_percent: Decimal, pit_method: str):
        """Hàm private hỗ trợ rà soát tập trung các điều kiện tiên quyết rào chặn dữ liệu bẩn"""
        if threshold < Decimal('0'):
            raise ValueError("Mức ngưỡng miễn thuế cơ sở không được phép nhỏ hơn 0.")
        if vat_percent < Decimal('0'):
            raise ValueError("Thuế suất GTGT định biên không được phép nhỏ hơn 0.")
        if pit_percent < Decimal('0'):
            raise ValueError("Thuế suất TNCN định biên không được phép nhỏ hơn 0.")
        if pit_method not in ['FLAT_RATE', 'BOOKKEEPING']:
            raise ValueError(f"Phương pháp tính thuế không hợp lệ: {pit_method}")

    def generate_yearly_tax_report_live(self, year: int, threshold: Decimal, vat_percent: Decimal, pit_percent: Decimal,
                                        pit_method: str) -> YearlyTaxReportDTO:
        # Kích hoạt rào chặn điều kiện tiên quyết đầu vào
        self._validate_inputs(threshold, vat_percent, pit_percent, pit_method)

        with self.uow_factory() as uow:
            revenue_dtos = uow.tax_report_repo.get_monthly_revenue_by_year(year)

        monthly_revenues = [Decimal('0') for _ in range(12)]
        monthly_costs = [Decimal('0') for _ in range(12)]

        for record in revenue_dtos:
            monthly_revenues[record.month - 1] = record.revenue
            monthly_costs[record.month - 1] = record.total_cost

        total_revenue = TaxCalculator.calculate_total_revenue(monthly_revenues)
        is_over = TaxCalculator.is_over_threshold(total_revenue, threshold)

        tax_distributions = TaxCalculator.calculate_monthly_tax_distribution(
            monthly_revenues=monthly_revenues,
            monthly_costs=monthly_costs,
            total_revenue=total_revenue,
            threshold=threshold,
            vat_rate_percent=vat_percent,
            pit_rate_percent=pit_percent,
            pit_method=pit_method
        )

        monthly_details = []
        total_tax_amount = Decimal('0')

        for i in range(12):
            vat, pit, total_month_tax = tax_distributions[i]
            total_tax_amount += total_month_tax

            monthly_details.append(MonthlyTaxDetailDTO(
                month=i + 1,
                revenue=monthly_revenues[i],
                vat_amount=vat,
                pit_amount=pit,
                total_tax=total_month_tax
            ))

        return YearlyTaxReportDTO(
            year=year,
            total_revenue=total_revenue,
            is_over_threshold=is_over,
            total_tax_amount=total_tax_amount,
            monthly_details=monthly_details
        )

    def stage_temporary_ledger(self, year: int, threshold: Decimal, vat_percent: Decimal, pit_percent: Decimal,
                               pit_method: str) -> bool:
        # 1. Kiểm tra tiên quyết an toàn số học ngay từ cửa ngõ RAM
        self._validate_inputs(threshold, vat_percent, pit_percent, pit_method)

        # 2. MỞ PHIÊN GIAO DỊCH DUY NHẤT - Triệt tiêu hoàn toàn lỗi lãng phí Connection Pool
        with self.uow_factory() as uow:
            # Kiểm tra trạng thái đóng băng kỳ thuế (Tiên quyết thực thể)
            existing_ledger = uow.tax_ledger_repo.get_ledger_by_year(year)
            if existing_ledger and existing_ledger.status == 'CLOSED':
                return False

            # CHỐT HIỆU NĂNG: Chỉ quét SELECT duy nhất một lần từ VIEW hóa đơn bán hàng
            revenue_dtos = uow.tax_report_repo.get_monthly_revenue_by_year(year)

            monthly_revenues = [Decimal('0') for _ in range(12)]
            monthly_costs_map = {m: Decimal('0') for m in range(1, 13)}

            for record in revenue_dtos:
                monthly_revenues[record.month - 1] = record.revenue
                monthly_costs_map[record.month] = record.total_cost

            # 3. Đẩy mảng dữ liệu sạch chạy trực tiếp vào core toán học
            total_revenue = TaxCalculator.calculate_total_revenue(monthly_revenues)
            tax_distributions = TaxCalculator.calculate_monthly_tax_distribution(
                monthly_revenues=monthly_revenues,
                monthly_costs=list(monthly_costs_map.values()),
                total_revenue=total_revenue,
                threshold=threshold,
                vat_rate_percent=vat_percent,
                pit_rate_percent=pit_percent,
                pit_method=pit_method
            )

            # Tính toán tổng hợp số tiền Header Master
            total_vat_amount = sum(dist[0] for dist in tax_distributions)
            total_pit_amount = sum(dist[1] for dist in tax_distributions)

            ledger_dto = TaxLedgerDTO(
                id=existing_ledger.id if existing_ledger else None,
                apply_year=year,
                total_revenue=total_revenue,
                total_cost=sum(monthly_costs_map.values()),
                final_vat_amount=total_vat_amount,
                final_pit_amount=total_pit_amount,
                pit_method=pit_method,
                status='DRAFT',
                threshold_amount=threshold,
                vat_percent=vat_percent,
                pit_percent=pit_percent,
                finalized_at=None
            )

            # Thực thi lưu/cập nhật Master xuống DB vật lý
            ledger_id = uow.tax_ledger_repo.save_ledger(ledger_dto)

            # Đóng gói mảng 12 tháng con lưu chi tiết
            ledger_details = []
            for i in range(12):
                month = i + 1
                vat_month, pit_month, _ = tax_distributions[i]
                ledger_details.append(TaxLedgerDetailDTO(
                    id=None,
                    tax_ledger_id=ledger_id,
                    month=month,
                    revenue=monthly_revenues[i],
                    cost=monthly_costs_map[month],
                    vat_amount=vat_month,
                    pit_amount=pit_month
                ))

            # Thực thi lưu hàng loạt chi tiết (Đã bao gồm cơ chế tự dọn dẹp rác nháp cũ)
            uow.tax_ledger_repo.save_ledger_details(ledger_id, ledger_details)
            return True

    def get_all_ledgers(self) -> List[TaxLedgerDTO]:
        with self.uow_factory() as uow:
            return uow.tax_ledger_repo.get_all_ledgers()

    def get_ledger_details(self, ledger_id: int) -> List[TaxLedgerDetailDTO]:
        with self.uow_factory() as uow:
            return uow.tax_ledger_repo.get_ledger_details(ledger_id)

    def close_and_freeze_ledger(self, year: int) -> bool:
        with self.uow_factory() as uow:
            existing = uow.tax_ledger_repo.get_ledger_by_year(year)
            if not existing or existing.status != 'DRAFT':
                return False

            return uow.tax_ledger_repo.update_ledger_status(year, 'CLOSED', datetime.now())

    def get_tax_warning_status(self, year: int) -> dict:
        ledger_draft = self.get_active_draft_ledger_config(year)
        threshold = ledger_draft.threshold_amount if ledger_draft else Decimal('1000000000')

        with self.uow_factory() as uow:
            revenue_dtos = uow.tax_report_repo.get_monthly_revenue_by_year(year)

        monthly_revenues = [Decimal('0') for _ in range(12)]
        for record in revenue_dtos:
            monthly_revenues[record.month - 1] = record.revenue

        total_revenue = TaxCalculator.calculate_total_revenue(monthly_revenues)

        percent = (total_revenue / threshold * Decimal('100')) if threshold > 0 else Decimal('0')
        if percent > Decimal('100'):
            percent = Decimal('100')

        is_near = total_revenue >= (threshold * Decimal('0.85'))

        return {
            "revenue": float(total_revenue),
            "threshold": float(threshold),
            "percent": float(percent),
            "is_near_threshold": is_near
        }