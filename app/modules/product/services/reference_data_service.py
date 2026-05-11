from app.core.database.connection import DatabaseConnection
from app.core.exceptions.validation_exception import ValidationException


class ReferenceDataService:
    """Service dùng chung để quản lý các danh mục từ điển (Category, Supplier, Unit)"""

    # ==========================================
    # DANH MỤC (CATEGORIES)
    # ==========================================
    def get_all_categories(self):
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            return cursor.fetchall()
        finally:
            conn.close()

    def create_category(self, name: str) -> int:
        return self._quick_create("categories", name)

    # ==========================================
    # NHÀ CUNG CẤP (SUPPLIERS)
    # ==========================================
    def get_all_suppliers(self):
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
            return cursor.fetchall()
        finally:
            conn.close()

    def create_supplier(self, name: str) -> int:
        return self._quick_create("suppliers", name)

    # ==========================================
    # ĐƠN VỊ TÍNH (UNITS)
    # ==========================================
    def get_all_units(self):
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM units ORDER BY name")
            return cursor.fetchall()
        finally:
            conn.close()

    def create_unit(self, name: str) -> int:
        return self._quick_create("units", name)

    # ==========================================
    # HÀM DÙNG CHUNG (Tái sử dụng code)
    # ==========================================
    def _quick_create(self, table_name: str, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValidationException("Tên không được để trống!")

        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Check trùng lặp
            cursor.execute(f"SELECT id FROM {table_name} WHERE name = %s", (name,))
            if cursor.fetchone():
                raise ValidationException(f"Tên '{name}' đã tồn tại trong hệ thống!")

            # Thêm mới
            cursor.execute(f"INSERT INTO {table_name} (name) VALUES (%s)", (name,))
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()