from app.core.database.base_repository import BaseRepository
from app.modules.product.repositories.inventory_repository import InventoryRepository

class InventoryRepositoryImpl(BaseRepository, InventoryRepository):

    def get_inventory_quantity(self, product_id: int) -> int:
        query = "SELECT quantity FROM inventory WHERE product_id = %s"
        self.cursor.execute(query, (product_id,))
        row = self.cursor.fetchone()
        return row["quantity"] if row else 0