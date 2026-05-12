from app.core.database.base_repository import BaseRepository
from app.modules.product.repositories.unit_repository import UnitRepository

# Đảm bảo kế thừa BaseRepository để xử lý tham số db_connection trong __init__
class UnitRepositoryImpl(BaseRepository, UnitRepository):
    def get_all(self):
        self.cursor.execute("SELECT id, name FROM units ORDER BY name")
        return self.cursor.fetchall()

    def exists_by_name(self, name: str) -> bool:
        self.cursor.execute("SELECT COUNT(1) AS total FROM units WHERE name = %s", (name,))
        result = self.cursor.fetchone()
        return result["total"] > 0 if result else False

    def exists_by_id(self, unit_id: int) -> bool:
        self.cursor.execute("SELECT COUNT(1) AS total FROM units WHERE id = %s", (unit_id,))
        result = self.cursor.fetchone()
        return result["total"] > 0 if result else False

    def create(self, name: str) -> int:
        # Thực thi lệnh INSERT trên cursor dùng chung của Transaction
        self.cursor.execute("INSERT INTO units (name) VALUES (%s)", (name,))
        return self.cursor.lastrowid