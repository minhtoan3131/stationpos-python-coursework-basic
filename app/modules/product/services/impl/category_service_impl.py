from typing import List, Dict, Any
from app.core.database.connection import DatabaseConnection
from app.core.database.transaction import TransactionManager
from app.core.exceptions.validation_exception import ValidationException
from app.modules.product.repositories.impl.category_repository_impl import CategoryRepositoryImpl
from app.modules.product.services.category_service import CategoryService


class CategoryServiceImpl(CategoryService):
    def __init__(self):
        pass

    def get_all_categories(self) -> List[Dict[str, Any]]:
        connection = DatabaseConnection.get_connection()
        try:
            repo = CategoryRepositoryImpl(connection)
            return repo.get_all()
        finally:
            connection.close()

    def create_category(self, name: str) -> int:
        # Validation cơ bản
        clean_name = name.strip() if name else ""
        if not clean_name:
            raise ValidationException("Tên danh mục không được để trống!")

        # Quản lý Transaction cho thao tác ghi (WRITE)
        connection = DatabaseConnection.get_connection()
        transaction = TransactionManager(connection)

        try:
            repo = CategoryRepositoryImpl(connection)

            # Kiểm tra trùng tên
            if repo.exists_by_name(clean_name):
                raise ValidationException(f"Danh mục '{clean_name}' đã tồn tại!")

            new_id = repo.create(clean_name)

            transaction.commit()  # Chốt giao dịch
            return new_id
        except Exception as e:
            transaction.rollback()  # Hoàn tác nếu lỗi
            raise e
        finally:
            connection.close()