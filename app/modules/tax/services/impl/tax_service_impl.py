from decimal import Decimal
from typing import Callable

from app.core.database.unit_of_work import UnitOfWork
from app.modules.tax.dtos.tax_dto import TaxConfigDTO, YearlyTaxReportDTO, MonthlyTaxDetailDTO
from app.modules.tax.services.tax_service import ITaxService
from app.modules.tax.utils.tax_calculator import TaxCalculator


class TaxService(ITaxService):
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self.uow_factory = uow_factory

    def get_or_create_config(self, year: int) -> TaxConfigDTO:
        with self.uow_factory() as uow:
            config = uow.tax_config_repo.get_config_by_year(year)
            if not config:
                config = TaxConfigDTO(
                    apply_year=year,
                    threshold_amount=Decimal('1000000000'),
                    vat_percent=Decimal('1.0'),
                    pit_percent=Decimal('0.5')
                )
                uow.tax_config_repo.save_config(config)
            return config

    def save_config(self, config: TaxConfigDTO) -> bool:
        with self.uow_factory() as uow:
            return uow.tax_config_repo.save_config(config)

    def generate_yearly_tax_report(self, year: int) -> YearlyTaxReportDTO:
        config = self.get_or_create_config(year)

        with self.uow_factory() as uow:
            revenue_dtos = uow.tax_report_repo.get_monthly_revenue_by_year(year)

        monthly_revenues = [Decimal('0') for _ in range(12)]
        for record in revenue_dtos:
            monthly_revenues[record.month - 1] = record.revenue

        total_revenue = TaxCalculator.calculate_total_revenue(monthly_revenues)
        is_over = TaxCalculator.is_over_threshold(total_revenue, config.threshold_amount)

        tax_distributions = TaxCalculator.calculate_monthly_tax_distribution(
            monthly_revenues=monthly_revenues,
            total_revenue=total_revenue,
            threshold=config.threshold_amount,
            vat_rate_percent=config.vat_percent,
            pit_rate_percent=config.pit_percent
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