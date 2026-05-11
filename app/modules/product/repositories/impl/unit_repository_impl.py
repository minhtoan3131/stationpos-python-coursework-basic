from app.modules.product.repositories.unit_repository import UnitRepository
from app.core.database.connection import DatabaseConnection

class UnitRepositoryImpl(UnitRepository):
    def get_all(self):
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM units ORDER BY name")
            return cursor.fetchall()
        finally:
            conn.close()

    def exists_by_name(self, name: str) -> bool:
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(1) FROM units WHERE name = %s", (name,))
            return cursor.fetchone()[0] > 0
        finally:
            conn.close()

    def exists_by_id(self, unit_id: int) -> bool:
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(1) FROM units WHERE id = %s", (unit_id,))
            return cursor.fetchone()[0] > 0
        finally:
            conn.close()

    def create(self, name: str) -> int:
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO units (name) VALUES (%s)", (name,))
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()