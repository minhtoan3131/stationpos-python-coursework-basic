# File: app/modules/report/repositories/impl/report_repository_impl.py
from datetime import datetime
from typing import List, Dict, Any
from app.core.database.base_repository import BaseRepository
from app.modules.report.repositories.report_repository import ReportRepository


class ReportRepositoryImpl(BaseRepository, ReportRepository):

    def get_kpi_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Truy vấn dữ liệu từ View tổng hợp tích hợp mới để lấy ra 8 chỉ số cốt lõi.
        """
        sql_kpis = """
            SELECT 
                IFNULL(SUM(total_orders_created), 0)    AS total_orders_created,
                IFNULL(SUM(total_orders_completed), 0)  AS total_orders_completed,
                IFNULL(SUM(total_orders_cancelled), 0)  AS total_orders_cancelled,
                IFNULL(SUM(gross_revenue), 0)           AS gross_revenue,
                IFNULL(SUM(cancelled_value), 0)         AS cancelled_value,
                IFNULL(SUM(net_revenue), 0)             AS net_revenue,
                IFNULL(SUM(total_cogs), 0)              AS total_cogs,
                IFNULL(SUM(variance_garbage), 0)        AS variance_garbage
            FROM vw_report_daily_financial_summary
            WHERE report_date BETWEEN %s AND %s
        """
        self.cursor.execute(sql_kpis, (start_date, end_date))
        row = self.cursor.fetchone() or {}

        # Tính toán bắc cầu logic tài chính
        net_revenue = float(row.get("net_revenue") or 0)
        total_cogs = float(row.get("total_cogs") or 0)
        variance_garbage = float(row.get("variance_garbage") or 0)

        gross_profit = net_revenue - total_cogs
        net_profit = gross_profit + variance_garbage

        return {
            "total_orders_created": int(row.get("total_orders_created") or 0),
            "total_orders_completed": int(row.get("total_orders_completed") or 0),
            "total_orders_cancelled": int(row.get("total_orders_cancelled") or 0),
            "gross_revenue": row.get("gross_revenue") or 0,
            "cancelled_value": row.get("cancelled_value") or 0,
            "net_revenue": net_revenue,
            "total_cogs": total_cogs,
            "gross_profit": gross_profit,
            "variance_garbage": variance_garbage,
            "net_profit": net_profit
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
        return [{"date": row["sale_date"].strftime("%d/%m") if row.get("sale_date") else "",
                 "revenue": row.get("total_revenue", 0)} for row in rows]

    def get_top_products(self, start_date: str, end_date: str, limit: int = 5) -> List[Dict[str, Any]]:
        sql = """
            SELECT product_sku AS sku, product_name, SUM(total_quantity) AS total_qty
            FROM vw_report_product_sales
            WHERE sale_date BETWEEN %s AND %s
            GROUP BY product_sku, product_name
            ORDER BY total_qty DESC
            LIMIT %s
        """
        self.cursor.execute(sql, (start_date, end_date, limit))
        rows = self.cursor.fetchall()
        return [{"sku": row.get("sku", ""), "product_name": row.get("product_name", ""),
                 "quantity": row.get("total_qty", 0)} for row in rows]

    def get_transaction_history(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT invoice_code, created_at, total_amount, payment_method_text
            FROM vw_report_transaction_history
            WHERE DATE(created_at) BETWEEN %s AND %s
            ORDER BY created_at DESC
        """
        self.cursor.execute(sql, (start_date, end_date))
        rows = self.cursor.fetchall()
        return [{"invoice_code": row.get("invoice_code", ""),
                 "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M") if isinstance(row.get("created_at"),
                                                                                          datetime) else str(
                     row.get("created_at", "")), "total_amount": row.get("total_amount", 0),
                 "payment_method": row.get("payment_method_text", "")} for row in rows]

    def get_inventory_valuation(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT product_name, unit_name, stock_quantity, mac_price, total_inventory_value
            FROM vw_report_inventory_valuation
            ORDER BY product_name ASC
        """
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        return [{"product_name": row.get("product_name", ""), "unit_name": row.get("unit_name", ""),
                 "stock_quantity": row.get("stock_quantity", 0), "mac_price": row.get("mac_price", 0),
                 "total_inventory_value": row.get("total_inventory_value", 0)} for row in rows]

    def get_daily_purchase_orders(self, date_str: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT po.code, po.created_at, po.total_amount, s.name AS supplier_name
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.id
            WHERE DATE(po.created_at) = %s AND po.status = 'COMPLETED'
        """
        self.cursor.execute(sql, (date_str,))
        return self.cursor.fetchall()