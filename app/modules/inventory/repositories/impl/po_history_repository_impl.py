from app.core.database.base_repository import BaseRepository
from app.modules.inventory.repositories.po_history_repository import PurchaseOrderHistoryRepository


class PurchaseOrderHistoryRepositoryImpl(BaseRepository, PurchaseOrderHistoryRepository):

    def search_purchase_orders(self, from_date: str, to_date: str, keyword: str = None, status: str = 'ALL') -> list:
        query = """
            SELECT 
                po.id, po.code, po.created_at, 
                IFNULL(s.name, 'N/A') AS supplier_name,
                po.total_amount, po.status, po.note, po.cancel_reason
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.id
            WHERE DATE(po.created_at) BETWEEN %s AND %s
        """
        params = [from_date, to_date]

        if status and status != 'ALL':
            query += " AND po.status = %s"
            params.append(status)

        if keyword:
            query += " AND (po.code LIKE %s OR s.name LIKE %s)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        query += " ORDER BY po.created_at DESC"

        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def get_purchase_order_by_id(self, po_id: int) -> dict:
        query = """
            SELECT * FROM purchase_orders WHERE id = %s
        """
        self.cursor.execute(query, (po_id,))
        return self.cursor.fetchone()

    def get_purchase_order_items(self, po_id: int) -> list:
        query = """
            SELECT 
                poi.product_id,
                poi.unit_id,
                p.sku, 
                p.name AS product_name, 
                u.name AS unit_name,
                poi.quantity, 
                poi.unit_price, 
                poi.total_price
            FROM purchase_order_items poi
            JOIN products p ON poi.product_id = p.id
            JOIN units u ON poi.unit_id = u.id
            WHERE poi.purchase_order_id = %s
        """
        self.cursor.execute(query, (po_id,))
        return self.cursor.fetchall()

    def update_purchase_order_status(self, po_id: int, new_status: str, cancel_reason: str = None) -> None:
        query = """
            UPDATE purchase_orders 
            SET status = %s, cancel_reason = %s 
            WHERE id = %s
        """
        self.cursor.execute(query, (new_status, cancel_reason, po_id))

    def has_subsequent_delivery_transactions(self, product_id: int, po_created_at) -> bool:
        """
        Kiểm tra xem có bất kỳ giao dịch XUẤT KHO nào
        phát sinh SAU thời điểm (timestamp) của phiếu nhập này không.
        """
        query = """
            SELECT 1 FROM stock_transactions 
            WHERE product_id = %s 
              AND created_at > %s 
              AND type = 'SALE'
            LIMIT 1
        """
        self.cursor.execute(query, (product_id, po_created_at))
        return self.cursor.fetchone() is not None
