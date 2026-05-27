# File: app/modules/sale/repositories/impl/invoice_history_repository_impl.py
from app.core.database.base_repository import BaseRepository
from datetime import date
from typing import List, Dict, Any
from app.modules.sale.repositories.invoice_history_repository import InvoiceHistoryRepository


class InvoiceHistoryRepositoryImpl(BaseRepository, InvoiceHistoryRepository):

    def fetch_invoices_master(self, keyword: str = None, date_from: date = None,
                              date_to: date = None, payment_method: str = None,
                              status: str = None) -> List[Dict[str, Any]]:
        """Khai thác dữ liệu bộ lọc động từ bảng invoices"""
        query = """
            SELECT code, created_at, total_amount, discount, final_amount, payment_method, status, cancel_reason
            FROM invoices
            WHERE DATE(created_at) BETWEEN %s AND %s
        """
        params = [date_from, date_to]

        if payment_method:
            query += " AND payment_method = %s"
            params.append(payment_method)

        if status:
            query += " AND status = %s"
            params.append(status)

        if keyword:
            query += " AND code LIKE %s"
            params.append(f"%{keyword}%")

        query += " ORDER BY created_at DESC"
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def fetch_invoice_details(self, invoice_code: str) -> List[Dict[str, Any]]:
        """Truy vấn các mặt hàng chi tiết đi kèm snapshot COGS lịch sử"""
        query = """
            SELECT 
                ii.product_id, ii.unit_id, p.sku, p.name AS product_name, 
                u.name AS unit_name, ii.quantity, ii.unit_price, ii.total_price, 
                ii.cost_price, ii.total_cogs_amount
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN products p ON ii.product_id = p.id
            JOIN units u ON ii.unit_id = u.id
            WHERE i.code = %s
        """
        self.cursor.execute(query, (invoice_code,))
        return self.cursor.fetchall()

    def fetch_invoice_metadata(self, invoice_code: str) -> Dict[str, Any]:
        """Lấy Header snapshot của hóa đơn phục vụ hiển thị Panel bên phải"""
        query = "SELECT * FROM invoices WHERE code = %s"
        self.cursor.execute(query, (invoice_code,))
        return self.cursor.fetchone() or {}

    def update_invoice_status(self, invoice_code: str, status: str, cancel_reason: str = None) -> bool:
        """Đổi trạng thái hóa đơn gốc"""
        query = "UPDATE invoices SET status = %s, cancel_reason = %s WHERE code = %s"
        self.cursor.execute(query, (status, cancel_reason, invoice_code))
        return True

    def restore_inventory_stock(self, invoice_code: str) -> None:
        """
        Hàm này được để trống (pass) vì toàn bộ logic tính toán pha loãng phức tạp
        và dọn rác của Luồng 4 sẽ do tầng Service xử lý tập trung, phối hợp giữa
        inventory_repo và product_repo qua Unit Of Work để đảm bảo tính đóng gói.
        """
        pass