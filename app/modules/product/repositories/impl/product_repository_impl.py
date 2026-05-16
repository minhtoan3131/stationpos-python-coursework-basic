from decimal import Decimal
from typing import List, Optional
from app.core.database.base_repository import BaseRepository
from app.modules.product.repositories.product_repository import ProductRepository
from app.modules.product.entities.product import Product


class ProductRepositoryImpl(BaseRepository, ProductRepository):

    def get_product_list(self) -> List[dict]:
        query = """
            SELECT p.id, p.sku, p.name, c.name AS category_name, u.name AS unit_name,
                   p.retail_price, p.wholesale_price, p.barcode, s.name AS supplier_name,
                   cu.name AS conversion_unit_name,
                   uc.ratio AS conversion_ratio
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            LEFT JOIN units u ON p.base_unit_id = u.id
            LEFT JOIN unit_conversions uc ON p.id = uc.product_id
            LEFT JOIN units cu ON uc.to_unit_id = cu.id
            WHERE p.is_active = TRUE
            ORDER BY p.created_at DESC
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def search_products(self, keyword: Optional[str], category_id: Optional[int], supplier_id: Optional[int],
                        is_active: Optional[bool]) -> List[dict]:
        query = """
            SELECT p.id, p.sku, p.name, c.name AS category_name, u.name AS unit_name,
                   p.retail_price, p.wholesale_price, p.barcode, s.name AS supplier_name,
                   cu.name AS conversion_unit_name,
                   uc.ratio AS conversion_ratio
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            LEFT JOIN units u ON p.base_unit_id = u.id
            LEFT JOIN unit_conversions uc ON p.id = uc.product_id
            LEFT JOIN units cu ON uc.to_unit_id = cu.id
            WHERE 1=1
        """
        params = []
        if keyword:
            query += " AND (p.sku LIKE %s OR p.name LIKE %s OR p.barcode LIKE %s)"
            like_kw = f"%{keyword}%"
            params.extend([like_kw, like_kw, like_kw])
        if category_id:
            query += " AND p.category_id = %s"
            params.append(category_id)
        if supplier_id:
            query += " AND p.supplier_id = %s"
            params.append(supplier_id)
        if is_active is not None:
            query += " AND p.is_active = %s"
            params.append(is_active)

        query += " ORDER BY p.created_at DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        query = "SELECT * FROM products WHERE id = %s"
        self.cursor.execute(query, (product_id,))
        row = self.cursor.fetchone()
        if not row: return None
        return Product(**row)

    def create_product(self, product: Product) -> int:
        query = """
            INSERT INTO products (sku, name, barcode, category_id, supplier_id, base_unit_id, cost_price, retail_price, wholesale_price, min_stock, description, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (product.sku, product.name, product.barcode, product.category_id, product.supplier_id,
                  product.base_unit_id, product.cost_price, product.retail_price, product.wholesale_price,
                  product.min_stock, product.description, product.is_active)
        self.cursor.execute(query, values)
        return self.cursor.lastrowid

    def update_product(self, product: Product) -> bool:
        query = """
            UPDATE products SET sku = %s, name = %s, barcode = %s, category_id = %s, supplier_id = %s, base_unit_id = %s, cost_price = %s, retail_price = %s, wholesale_price = %s, min_stock = %s, description = %s, is_active = %s WHERE id = %s
        """
        values = (product.sku, product.name, product.barcode, product.category_id, product.supplier_id,
                  product.base_unit_id, product.cost_price, product.retail_price, product.wholesale_price,
                  product.min_stock, product.description, product.is_active, product.id)
        self.cursor.execute(query, values)
        return self.cursor.rowcount > 0

    def soft_delete_product(self, product_id: int) -> bool:
        query = "UPDATE products SET is_active = FALSE WHERE id = %s"
        self.cursor.execute(query, (product_id,))
        return self.cursor.rowcount > 0

    def exists_by_sku(self, sku: str) -> bool:
        self.cursor.execute("SELECT COUNT(*) AS total FROM products WHERE sku = %s", (sku,))
        return self.cursor.fetchone()["total"] > 0

    def exists_by_sku_excluding_id(self, sku: str, product_id: int) -> bool:
        self.cursor.execute("SELECT COUNT(*) AS total FROM products WHERE sku = %s AND id != %s", (sku, product_id))
        return self.cursor.fetchone()["total"] > 0

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        self.cursor.execute("SELECT * FROM products WHERE barcode = %s", (barcode,))
        row = self.cursor.fetchone()
        return Product(**row) if row else None

    def exists_by_barcode(self, barcode: str) -> bool:
        self.cursor.execute("SELECT COUNT(*) AS total FROM products WHERE barcode = %s", (barcode,))
        return self.cursor.fetchone()["total"] > 0

    def exists_by_barcode_excluding_id(self, barcode: str, product_id: int) -> bool:
        self.cursor.execute("SELECT COUNT(*) AS total FROM products WHERE barcode = %s AND id != %s",
                            (barcode, product_id))
        return self.cursor.fetchone()["total"] > 0

    def get_product_import_detail(self, product_id: int) -> Optional[dict]:
        query = """
            SELECT p.id, p.sku, p.name, p.base_unit_id, p.cost_price,
                   u1.name AS base_unit_name,
                   u2.name AS conversion_unit_name,
                   uc.to_unit_id AS conversion_unit_id,
                   uc.ratio AS conversion_ratio
            FROM products p
            LEFT JOIN units u1 ON p.base_unit_id = u1.id
            LEFT JOIN unit_conversions uc ON p.id = uc.product_id
            LEFT JOIN units u2 ON uc.to_unit_id = u2.id
            WHERE p.id = %s
        """
        self.cursor.execute(query, (product_id,))
        return self.cursor.fetchone()

    def get_product_detail_for_import(self, product_id: int) -> Optional[dict]:
        """Hàm chuyên biệt trả về dict chứa đầy đủ thông tin JOIN cho DTO"""
        query = """
            SELECT p.*, 
                   u1.name AS base_unit_name,
                   u2.name AS conversion_unit_name,
                   uc.to_unit_id AS conversion_unit_id,
                   uc.ratio AS conversion_ratio
            FROM products p
            LEFT JOIN units u1 ON p.base_unit_id = u1.id
            LEFT JOIN unit_conversions uc ON p.id = uc.product_id
            LEFT JOIN units u2 ON uc.to_unit_id = u2.id
            WHERE p.id = %s
        """
        self.cursor.execute(query, (product_id,))
        return self.cursor.fetchone()  # Trả về dictionary thô

    def update_cost_price(self, product_id: int, new_cost_price: Decimal) -> None:
        """Cập nhật lại Giá vốn bình quân vào bảng products"""
        sql = "UPDATE products SET cost_price = %s WHERE id = %s"
        self.cursor.execute(sql, (new_cost_price, product_id))


    def get_product_sale_list(self, keyword: str = None) -> List[dict]:
        sql = """
            SELECT 
                p.id, p.sku, p.name, p.base_unit_id, p.retail_price, p.wholesale_price,
                u_base.name as base_unit_name,
                inv.quantity as stock_qty,
                uc.to_unit_id as conversion_unit_id,
                u_conv.name as conversion_unit_name,
                uc.ratio
            FROM products p
            JOIN units u_base ON p.base_unit_id = u_base.id
            LEFT JOIN inventory inv ON p.id = inv.product_id
            LEFT JOIN unit_conversions uc ON p.id = uc.product_id
            LEFT JOIN units u_conv ON uc.to_unit_id = u_conv.id
            WHERE p.is_active = TRUE
        """
        params = []
        if keyword:
            sql += " AND (p.name LIKE %s OR p.sku LIKE %s OR p.barcode LIKE %s)"
            search_term = f"%{keyword}%"
            params.extend([search_term, search_term, search_term])

        self.cursor.execute(sql, params)
        return self.cursor.fetchall()