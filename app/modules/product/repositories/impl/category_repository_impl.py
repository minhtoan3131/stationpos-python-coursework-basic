from app.core.database.base_repository import BaseRepository
from app.modules.product.repositories.category_repository import CategoryRepository

# Kế thừa BaseRepository để nhận db_connection từ MainWindow
class CategoryRepositoryImpl(BaseRepository, CategoryRepository):
    def get_all(self):
        # Sử dụng self.cursor đã được BaseRepository khởi tạo
        self.cursor.execute("SELECT id, name FROM categories ORDER BY name")
        return self.cursor.fetchall()

    def exists_by_name(self, name: str) -> bool:
        self.cursor.execute("SELECT COUNT(1) AS total FROM categories WHERE name = %s", (name,))
        result = self.cursor.fetchone()
        return result["total"] > 0 if result else False

    def exists_by_id(self, category_id: int) -> bool:
        self.cursor.execute("SELECT COUNT(1) AS total FROM categories WHERE id = %s", (category_id,))
        result = self.cursor.fetchone()
        return result["total"] > 0 if result else False

    def create(self, name: str) -> int:
        self.cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
        # Trả về ID vừa tạo từ cursor hiện tại
        return self.cursor.lastrowid