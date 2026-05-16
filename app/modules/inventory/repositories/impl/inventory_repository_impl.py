from typing import Optional
from app.core.database.base_repository import BaseRepository
from app.modules.inventory.repositories.inventory_repository import InventoryRepository

class InventoryRepositoryImpl(BaseRepository, InventoryRepository):

    def get_inventory_status(self, product_id: int) -> dict:
        """Lấy tồn kho và tổng giá trị, CÓ KHÓA DÒNG (FOR UPDATE) để chống đụng độ"""
        query = "SELECT quantity, total_value FROM inventory WHERE product_id = %s FOR UPDATE"
        self.cursor.execute(query, (product_id,))
        row = self.cursor.fetchone()

        if row:
            return {
                "quantity": row["quantity"],
                "total_value": row["total_value"] if row["total_value"] is not None else 0
            }
        # Nếu chưa từng nhập kho bao giờ
        return {"quantity": 0, "total_value": 0}

    def create_purchase_order(self, po_data):
        sql = "INSERT INTO purchase_orders (code, supplier_id, total_amount, note) VALUES (%s, %s, %s, %s)"
        # Đã đổi thành self.cursor
        self.cursor.execute(sql, (po_data['code'], po_data['supplier_id'], po_data['total_amount'], po_data['note']))
        return self.cursor.lastrowid

    def create_purchase_order_item(self, item_data):
        sql = """INSERT INTO purchase_order_items (purchase_order_id, product_id, unit_id, quantity, unit_price, total_price)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        # Đã đổi thành self.cursor
        self.cursor.execute(sql, (item_data['po_id'], item_data['product_id'], item_data['unit_id'],
                             item_data['qty'], item_data['price'], item_data['total']))

    def add_stock_transaction(self, trans_data):
        sql = """
            INSERT INTO stock_transactions (product_id, change_quantity, type, reference_id) 
            VALUES (%s, %s, %s, %s)
        """
        self.cursor.execute(sql, (
            trans_data['product_id'],
            trans_data['qty'],     # Đọc key 'qty'
            trans_data['type'],    # Đọc key 'type' (VD: 'IMPORT' hoặc 'SALE')
            trans_data['ref_id']   # Đọc key 'ref_id'
        ))

    def update_inventory_status(self, product_id: int, new_qty: int, new_total_value):
        """Cập nhật đè trực tiếp Số lượng và Tổng giá trị mới nhất"""
        sql = """INSERT INTO inventory (product_id, quantity, total_value, updated_at) 
                 VALUES (%s, %s, %s, NOW())
                 ON DUPLICATE KEY UPDATE 
                    quantity = %s, 
                    total_value = %s, 
                    updated_at = NOW()"""
        # Truyền 5 tham số: 3 cho INSERT, 2 cho trường hợp UPDATE
        self.cursor.execute(sql, (product_id, new_qty, new_total_value, new_qty, new_total_value))

    def get_inventory_list_data(self, search_keyword: str = None) -> list:
        query = """
            SELECT 
                p.id AS product_id, p.sku, p.name AS product_name, p.min_stock,
                u1.name AS base_unit_name, 
                u2.name AS conversion_unit_name, 
                uc.ratio AS conversion_ratio,
                COALESCE(i.quantity, 0) AS total_base_quantity
            FROM products p
            LEFT JOIN units u1 ON p.base_unit_id = u1.id
            LEFT JOIN unit_conversions uc ON p.id = uc.product_id
            LEFT JOIN units u2 ON uc.to_unit_id = u2.id
            LEFT JOIN inventory i ON p.id = i.product_id
            WHERE p.is_active = 1
        """
        params = []
        if search_keyword:
            query += " AND (p.sku LIKE %s OR p.name LIKE %s OR p.barcode LIKE %s)"
            params.extend([f"%{search_keyword}%", f"%{search_keyword}%", f"%{search_keyword}%"])

        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def get_inventory_report_data(self) -> list:
        """
        Thực thi câu lệnh SQL lấy dữ liệu cho báo cáo.
        """
        query = """
            SELECT 
                p.sku, 
                p.name AS product_name, 
                u.name AS unit_name,
                p.cost_price, 
                p.min_stock,
                COALESCE(i.quantity, 0) AS quantity,
                COALESCE(i.total_value, 0) AS total_value
            FROM products p
            LEFT JOIN units u ON p.base_unit_id = u.id
            LEFT JOIN inventory i ON p.id = i.product_id
            WHERE p.is_active = 1
            ORDER BY p.name ASC
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()