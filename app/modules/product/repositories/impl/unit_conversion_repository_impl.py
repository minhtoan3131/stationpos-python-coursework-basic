from typing import Optional
from app.core.database.base_repository import BaseRepository
from app.modules.product.repositories.unit_conversion_repository import UnitConversionRepository
from app.modules.product.entities.unit_conversion import UnitConversion


class UnitConversionRepositoryImpl(BaseRepository, UnitConversionRepository):

    def get_unit_conversion(self, product_id: int) -> Optional[UnitConversion]:
        query = "SELECT * FROM unit_conversions WHERE product_id = %s"
        self.cursor.execute(query, (product_id,))
        row = self.cursor.fetchone()
        return UnitConversion(**row) if row else None

    def create_unit_conversion(self, conversion: UnitConversion) -> int:
        query = "INSERT INTO unit_conversions (product_id, from_unit_id, to_unit_id, ratio) VALUES (%s, %s, %s, %s)"
        values = (conversion.product_id, conversion.from_unit_id, conversion.to_unit_id, conversion.ratio)
        self.cursor.execute(query, values)
        return self.cursor.lastrowid

    def update_unit_conversion(self, conversion: UnitConversion) -> bool:
        query = "UPDATE unit_conversions SET from_unit_id = %s, to_unit_id = %s, ratio = %s WHERE product_id = %s"
        values = (conversion.from_unit_id, conversion.to_unit_id, conversion.ratio, conversion.product_id)
        self.cursor.execute(query, values)
        return self.cursor.rowcount > 0