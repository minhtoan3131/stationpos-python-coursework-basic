from app.modules.product.services.supplier_service import SupplierService
from app.modules.product.repositories.impl.supplier_repository_impl import SupplierRepositoryImpl
from app.core.exceptions.validation_exception import ValidationException
from app.core.database.connection import DatabaseConnection
from app.core.database.transaction import TransactionManager


class SupplierServiceImpl(SupplierService):
    def __init__(self):
        pass

    def get_all_suppliers(self):
        connection = DatabaseConnection.get_connection()
        try:
            repo = SupplierRepositoryImpl(connection)
            return repo.get_all()
        finally:
            connection.close()

    def create_supplier(self, name: str) -> int:
        clean_name = name.strip() if name else ""
        if not clean_name:
            raise ValidationException("Tên nhà cung cấp không được để trống!")

        # Mở connection và Transaction cho thao tác WRITE
        connection = DatabaseConnection.get_connection()
        transaction = TransactionManager(connection)

        try:
            repo = SupplierRepositoryImpl(connection)

            # Validation Business (Check trùng)
            if repo.exists_by_name(clean_name):
                raise ValidationException(f"Nhà cung cấp '{clean_name}' đã tồn tại trong hệ thống!")

            new_id = repo.create(clean_name)

            transaction.commit()
            return new_id

        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()