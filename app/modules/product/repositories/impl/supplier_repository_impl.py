from app.core.database.base_repository import BaseRepository
from app.modules.product.repositories.supplier_repository import SupplierRepository

class SupplierRepositoryImpl(BaseRepository, SupplierRepository):

    def get_all(self):
        self.cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
        return self.cursor.fetchall()

    def exists_by_name(self, name: str) -> bool:
        self.cursor.execute("SELECT COUNT(1) AS total FROM suppliers WHERE name = %s", (name,))
        result = self.cursor.fetchone()
        return result['total'] > 0 if result else False

    def exists_by_id(self, supplier_id: int) -> bool:
        self.cursor.execute("SELECT COUNT(1) AS total FROM suppliers WHERE id = %s", (supplier_id,))
        result = self.cursor.fetchone()
        return result['total'] > 0 if result else False

    def create(self, name: str) -> int:
        self.cursor.execute("INSERT INTO suppliers (name) VALUES (%s)", (name,))
        return self.cursor.lastrowid