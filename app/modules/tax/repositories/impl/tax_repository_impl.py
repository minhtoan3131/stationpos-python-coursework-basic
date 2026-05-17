from decimal import Decimal
from typing import Optional, List

from app.core.database.base_repository import BaseRepository
from app.modules.tax.dtos.tax_dto import TaxConfigDTO, MonthlyRevenueDTO
from app.modules.tax.repositories.tax_repository import ITaxConfigRepository, ITaxReportRepository


class TaxConfigRepository(BaseRepository, ITaxConfigRepository):

    def get_config_by_year(self, year: int) -> Optional[TaxConfigDTO]:
        query = """
            SELECT id, apply_year, threshold_amount, vat_percent, pit_percent 
            FROM tax_config 
            WHERE apply_year = %s
        """
        self.cursor.execute(query, (year,))
        row = self.cursor.fetchone()

        if row:
            return TaxConfigDTO(
                id=row['id'],
                apply_year=row['apply_year'],
                threshold_amount=Decimal(str(row['threshold_amount'])),
                vat_percent=Decimal(str(row['vat_percent'])),
                pit_percent=Decimal(str(row['pit_percent']))
            )
        return None

    def save_config(self, config: TaxConfigDTO) -> bool:
        # Sử dụng cơ chế UPSERT của MySQL (INSERT ... ON DUPLICATE KEY UPDATE)
        # Giả định cột apply_year đã được set là UNIQUE trong database
        query = """
            INSERT INTO tax_config (apply_year, threshold_amount, vat_percent, pit_percent)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                threshold_amount = VALUES(threshold_amount),
                vat_percent = VALUES(vat_percent),
                pit_percent = VALUES(pit_percent),
                updated_at = CURRENT_TIMESTAMP
        """
        try:
            self.cursor.execute(query, (
                config.apply_year,
                config.threshold_amount,
                config.vat_percent,
                config.pit_percent
            ))
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"[TaxConfigRepository] Error saving config: {e}")
            return False


class TaxReportRepository(BaseRepository, ITaxReportRepository):

    def get_monthly_revenue_by_year(self, year: int) -> List[MonthlyRevenueDTO]:
        # Truy vấn trực tiếp vào View vw_report_invoice_summary đã có sẵn
        query = """
            SELECT 
                MONTH(sale_date) AS month, 
                SUM(revenue) AS total_revenue
            FROM vw_report_invoice_summary
            WHERE YEAR(sale_date) = %s
            GROUP BY MONTH(sale_date)
            ORDER BY month ASC
        """
        self.cursor.execute(query, (year,))
        rows = self.cursor.fetchall()

        result = []
        for row in rows:
            result.append(MonthlyRevenueDTO(
                month=row['month'],
                revenue=Decimal(str(row['total_revenue'] or 0))
            ))
        return result