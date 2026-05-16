from typing import List, Dict, Any
from app.core.database.base_repository import BaseRepository
from app.modules.report.repositories.report_repository import ReportRepository


class ReportRepositoryImpl(BaseRepository, ReportRepository):

    def get_kpi_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        sql_sales = """
            SELECT 
                COUNT(invoice_id) AS total_orders, 
                SUM(revenue) AS total_revenue, 
                SUM(gross_profit) AS total_profit
            FROM vw_report_invoice_summary
            WHERE sale_date BETWEEN %s AND %s
        """
        self.cursor.execute(sql_sales, (start_date, end_date))
        sales_row = self.cursor.fetchone() or {}

        sql_stock = """
            SELECT SUM(total_inventory_value) AS total_stock_value 
            FROM vw_report_inventory_valuation
        """
        self.cursor.execute(sql_stock)
        stock_row = self.cursor.fetchone() or {}

        return {
            "total_orders": sales_row.get("total_orders") or 0,
            "total_revenue": sales_row.get("total_revenue") or 0,
            "total_profit": sales_row.get("total_profit") or 0,
            "total_stock_value": stock_row.get("total_stock_value") or 0
        }

    def get_revenue_trend(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT sale_date, SUM(revenue) AS total_revenue
            FROM vw_report_invoice_summary
            WHERE sale_date BETWEEN %s AND %s
            GROUP BY sale_date
            ORDER BY sale_date ASC
        """
        self.cursor.execute(sql, (start_date, end_date))
        rows = self.cursor.fetchall()

        return [
            {
                "date": row["sale_date"].strftime("%d/%m") if row.get("sale_date") else "",
                "revenue": row.get("total_revenue", 0)
            }
            for row in rows
        ]

    def get_top_products(self, start_date: str, end_date: str, limit: int = 5) -> List[Dict[str, Any]]:
        sql = """
            SELECT product_name, SUM(total_quantity) AS total_qty
            FROM vw_report_product_sales
            WHERE sale_date BETWEEN %s AND %s
            GROUP BY product_name
            ORDER BY total_qty DESC
            LIMIT %s
        """
        self.cursor.execute(sql, (start_date, end_date, limit))
        rows = self.cursor.fetchall()

        return [
            {
                "product_name": row.get("product_name", ""),
                "quantity": row.get("total_qty", 0)
            }
            for row in rows
        ]

    def get_transaction_history(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT invoice_code, created_at, final_amount, payment_method_text
            FROM vw_report_transaction_history
            WHERE DATE(created_at) BETWEEN %s AND %s
            ORDER BY created_at DESC
        """
        self.cursor.execute(sql, (start_date, end_date))
        rows = self.cursor.fetchall()

        return [
            {
                "invoice_code": row.get("invoice_code", ""),
                "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M") if row.get("created_at") else "",
                "final_amount": row.get("final_amount", 0),
                "payment_method": row.get("payment_method_text", "")
            }
            for row in rows
        ]

    def get_inventory_valuation(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT product_name, unit_name, stock_quantity, mac_price, total_inventory_value
            FROM vw_report_inventory_valuation
            ORDER BY product_name ASC
        """
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()

        return [
            {
                "product_name": row.get("product_name", ""),
                "unit_name": row.get("unit_name", ""),
                "stock_quantity": row.get("stock_quantity", 0),
                "mac_price": row.get("mac_price", 0),
                "total_inventory_value": row.get("total_inventory_value", 0)
            }
            for row in rows
        ]