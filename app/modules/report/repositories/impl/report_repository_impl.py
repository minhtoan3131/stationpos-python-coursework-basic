# File: app/modules/report/repositories/impl/report_repository_impl.py
from datetime import datetime
from typing import List, Dict, Any
from app.core.database.base_repository import BaseRepository
from app.modules.report.repositories.report_repository import ReportRepository


class ReportRepositoryImpl(BaseRepository, ReportRepository):

    def get_kpi_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Kiểm toán KPIs: Doanh thu thuần = Doanh thu COMPLETED - Tiền hoàn trả CANCELLED thực tế từ lịch sử.
        Lợi nhuận thuần = Lợi nhuận COMPLETED + Tiền dọn rác tồn đọng.
        """
        # 1. Thu thập doanh thu và lợi nhuận từ các hóa đơn COMPLETED chuẩn
        sql_sales = """
            SELECT 
                COUNT(invoice_id) AS total_orders, 
                IFNULL(SUM(revenue), 0) AS total_revenue, 
                IFNULL(SUM(gross_profit), 0) AS total_profit
            FROM vw_report_invoice_summary
            WHERE sale_date BETWEEN %s AND %s
        """
        self.cursor.execute(sql_sales, (start_date, end_date))
        sales_row = self.cursor.fetchone() or {}

        # 2. KIỂM TOÁN LÙI CHUẨN XÁC: Chỉ trừ tiền hoàn trả của hóa đơn hủy từ Nhật ký lịch sử (Luồng 4)
        # Đã cập nhật: Bổ sung "AND cancel_reason IS NOT NULL" để loại bỏ hóa đơn lỗi hệ thống
        sql_cancelled = """
            SELECT IFNULL(SUM(final_amount), 0) AS returned_cash
            FROM invoices 
            WHERE status = 'CANCELLED' 
              AND cancel_reason IS NOT NULL
              AND DATE(created_at) BETWEEN %s AND %s
        """
        self.cursor.execute(sql_cancelled, (start_date, end_date))
        cancelled_row = self.cursor.fetchone() or {}

        # 3. Thu thập tổng giá trị rác tài chính đã triệt tiêu mang ra sổ cái (Luồng 1 & Luồng 4)
        sql_variance = """
            SELECT IFNULL(SUM(variance_amount), 0) AS total_variance_garbage
            FROM stock_transactions
            WHERE type IN ('DATA_CORRECTION', 'ADJUST_VARIANCE')
              AND DATE(created_at) BETWEEN %s AND %s
        """
        self.cursor.execute(sql_variance, (start_date, end_date))
        variance_row = self.cursor.fetchone() or {}

        # 4. Lấy tổng giá trị kho vật lý hiện hành thời gian thực
        sql_stock = """
            SELECT IFNULL(SUM(total_inventory_value), 0) AS total_stock_value 
            FROM vw_report_inventory_valuation
        """
        self.cursor.execute(sql_stock)
        stock_row = self.cursor.fetchone() or {}

        # Tính toán dòng tiền sạch thực tế tại két
        net_revenue = sales_row.get("total_revenue", 0) - cancelled_row.get("returned_cash", 0)
        net_profit = sales_row.get("total_profit", 0) + variance_row.get("total_variance_garbage", 0)

        return {
            "total_orders": sales_row.get("total_orders", 0),
            "total_revenue": net_revenue,
            "total_profit": net_profit,
            "total_stock_value": stock_row.get("total_stock_value", 0)
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
            SELECT product_name, SUM(total_quantity) AS total_qty
            FROM vw_report_product_sales
            WHERE sale_date BETWEEN %s AND %s
            GROUP BY product_name
            ORDER BY total_qty DESC
            LIMIT %s
        """
        self.cursor.execute(sql, (start_date, end_date, limit))
        rows = self.cursor.fetchall()
        return [{"product_name": row.get("product_name", ""), "quantity": row.get("total_qty", 0)} for row in rows]

    def get_transaction_history(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT invoice_code, created_at, final_amount, payment_method_text
            FROM vw_report_transaction_history
            WHERE DATE(created_at) BETWEEN %s AND %s
            ORDER BY created_at DESC
        """
        self.cursor.execute(sql, (start_date, end_date))
        rows = self.cursor.fetchall()
        return [{"invoice_code": row.get("invoice_code", ""),
                 "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M") if isinstance(row.get("created_at"),
                                                                                          datetime) else str(
                     row.get("created_at", "")), "final_amount": row.get("final_amount", 0),
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