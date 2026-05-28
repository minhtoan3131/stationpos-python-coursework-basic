from decimal import Decimal
from typing import Optional, List
from datetime import datetime

from app.core.database.base_repository import BaseRepository
from app.modules.tax.dtos.tax_dto import MonthlyRevenueDTO, TaxLedgerDTO, TaxLedgerDetailDTO
from app.modules.tax.repositories.tax_repository import ITaxReportRepository, ITaxLedgerRepository

class TaxReportRepository(BaseRepository, ITaxReportRepository):

    def get_monthly_revenue_by_year(self, year: int) -> List[MonthlyRevenueDTO]:
        """Truy vấn doanh thu tổng hợp sống và tổng giá vốn (COGS) từ VIEW hóa đơn bán hàng"""
        query = """
            SELECT 
                MONTH(sale_date) AS month, 
                SUM(revenue) AS total_revenue,
                SUM(total_cost) AS total_cost
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
                revenue=Decimal(str(row['total_revenue'] or 0)),
                total_cost=Decimal(str(row['total_cost'] or 0))
            ))
        return result


class TaxLedgerRepository(BaseRepository, ITaxLedgerRepository):

    def get_ledger_by_year(self, year: int) -> Optional[TaxLedgerDTO]:
        """Đọc thông tin chứng từ Master của một năm (Bao gồm cả thông số cấu hình tích hợp)"""
        query = """
            SELECT id, apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, 
                   pit_method, status, threshold_amount, vat_percent, pit_percent, finalized_at
            FROM tax_ledger
            WHERE apply_year = %s
        """
        self.cursor.execute(query, (year,))
        row = self.cursor.fetchone()

        if row:
            return TaxLedgerDTO(
                id=row['id'],
                apply_year=row['apply_year'],
                total_revenue=Decimal(str(row['total_revenue'])),
                total_cost=Decimal(str(row['total_cost'])),
                final_vat_amount=Decimal(str(row['final_vat_amount'])),
                final_pit_amount=Decimal(str(row['final_pit_amount'])),
                pit_method=row['pit_method'],
                status=row['status'],
                threshold_amount=Decimal(str(row['threshold_amount'])),
                vat_percent=Decimal(str(row['vat_percent'])),
                pit_percent=Decimal(str(row['pit_percent'])),
                finalized_at=row['finalized_at']
            )
        return None

    def get_all_ledgers(self) -> List[TaxLedgerDTO]:
        """Truy vấn danh sách toàn bộ nhật ký sổ cái phục vụ bảng Master bên trái (Tab 2)"""
        query = """
            SELECT id, apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, 
                   pit_method, status, threshold_amount, vat_percent, pit_percent, finalized_at
            FROM tax_ledger
            ORDER BY apply_year DESC
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        result = []
        for row in rows:
            result.append(TaxLedgerDTO(
                id=row['id'],
                apply_year=row['apply_year'],
                total_revenue=Decimal(str(row['total_revenue'])),
                total_cost=Decimal(str(row['total_cost'])),
                final_vat_amount=Decimal(str(row['final_vat_amount'])),
                final_pit_amount=Decimal(str(row['final_pit_amount'])),
                pit_method=row['pit_method'],
                status=row['status'],
                threshold_amount=Decimal(str(row['threshold_amount'])),
                vat_percent=Decimal(str(row['vat_percent'])),
                pit_percent=Decimal(str(row['pit_percent'])),
                finalized_at=row['finalized_at']
            ))
        return result

    def save_ledger(self, ledger: TaxLedgerDTO) -> int:
        """Lưu mới hoặc cập nhật bản ghi Master Sổ cái. Trả về ID tự tăng của MySQL"""
        if ledger.id:
            query = """
                UPDATE tax_ledger 
                SET total_revenue = %s, total_cost = %s, final_vat_amount = %s, final_pit_amount = %s, 
                    pit_method = %s, status = %s, threshold_amount = %s, vat_percent = %s, pit_percent = %s
                WHERE id = %s
            """
            self.cursor.execute(query, (
                ledger.total_revenue,
                ledger.total_cost,
                ledger.final_vat_amount,
                ledger.final_pit_amount,
                ledger.pit_method,
                ledger.status,
                ledger.threshold_amount,
                ledger.vat_percent,
                ledger.pit_percent,
                ledger.id
            ))
            return ledger.id
        else:
            query = """
                INSERT INTO tax_ledger (apply_year, total_revenue, total_cost, final_vat_amount, final_pit_amount, 
                                        pit_method, status, threshold_amount, vat_percent, pit_percent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (
                ledger.apply_year,
                ledger.total_revenue,
                ledger.total_cost,
                ledger.final_vat_amount,
                ledger.final_pit_amount,
                ledger.pit_method,
                ledger.status,
                ledger.threshold_amount,
                ledger.vat_percent,
                ledger.pit_percent
            ))
            return self.cursor.lastrowid

    def update_ledger_status(self, year: int, status: str, finalized_at: Optional[datetime]) -> bool:
        """Cập nhật trạng thái đóng băng vĩnh viễn kỳ quyết toán thuế sau khi nhập đúng mã PIN bảo mật"""
        query = """
            UPDATE tax_ledger 
            SET status = %s, finalized_at = %s 
            WHERE apply_year = %s AND status = 'DRAFT'
        """
        self.cursor.execute(query, (status, finalized_at, year))
        return self.cursor.rowcount > 0

    def get_ledger_details(self, ledger_id: int) -> List[TaxLedgerDetailDTO]:
        """Truy vấn mảng chi tiết 12 tháng đã được đóng băng của một chứng từ phục vụ bảng bên phải (Tab 2)"""
        query = """
            SELECT id, tax_ledger_id, month, revenue, cost, vat_amount, pit_amount
            FROM tax_ledger_details
            WHERE tax_ledger_id = %s
            ORDER BY month ASC
        """
        self.cursor.execute(query, (ledger_id,))
        rows = self.cursor.fetchall()

        result = []
        for row in rows:
            result.append(TaxLedgerDetailDTO(
                id=row['id'],
                tax_ledger_id=row['tax_ledger_id'],
                month=row['month'],
                revenue=Decimal(str(row['revenue'])),
                cost=Decimal(str(row['cost'])),
                vat_amount=Decimal(str(row['vat_amount'])),
                pit_amount=Decimal(str(row['pit_amount']))
            ))
        return result

    def save_ledger_details(self, ledger_id: int, details: List[TaxLedgerDetailDTO]) -> bool:
        """Lưu hàng loạt chi tiết 12 tháng đóng băng độc lập (Tự động dọn dẹp chi tiết nháp cũ)"""
        try:
            delete_query = "DELETE FROM tax_ledger_details WHERE tax_ledger_id = %s"
            self.cursor.execute(delete_query, (ledger_id,))

            insert_query = """
                INSERT INTO tax_ledger_details (tax_ledger_id, month, revenue, cost, vat_amount, pit_amount)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            batch_params = [
                (d.tax_ledger_id, d.month, d.revenue, d.cost, d.vat_amount, d.pit_amount)
                for d in details
            ]
            self.cursor.executemany(insert_query, batch_params)
            return True
        except Exception as e:
            print(f"[TaxLedgerRepository] Error saving ledger details: {e}")
            return False