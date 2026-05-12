from typing import List, Dict, Any
from app.core.database.connection import DatabaseConnection
from app.core.database.transaction import TransactionManager
from app.core.exceptions.validation_exception import ValidationException
from app.modules.product.repositories.impl.unit_repository_impl import UnitRepositoryImpl
from app.modules.product.services.unit_service import UnitService


class UnitServiceImpl(UnitService):
    def __init__(self):
        pass

    def get_all_units(self) -> List[Dict[str, Any]]:
        connection = DatabaseConnection.get_connection()
        try:
            repo = UnitRepositoryImpl(connection)
            return repo.get_all()
        finally:
            connection.close()

    def create_unit(self, name: str) -> int:
        # Validation bề mặt
        clean_name = name.strip() if name else ""
        if not clean_name:
            raise ValidationException("Tên đơn vị tính không được để trống!")

        # Mở connection và khởi tạo Transaction Manager
        connection = DatabaseConnection.get_connection()
        transaction = TransactionManager(connection)

        try:
            repo = UnitRepositoryImpl(connection)

            # Kiểm tra logic nghiệp vụ
            if repo.exists_by_name(clean_name):
                raise ValidationException(f"Đơn vị tính '{clean_name}' đã tồn tại!")

            new_id = repo.create(clean_name)

            transaction.commit()
            return new_id
        except Exception as e:
            transaction.rollback()
            raise e
        finally:
            connection.close()