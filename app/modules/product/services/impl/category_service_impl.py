from app.modules.product.services.category_service import CategoryService
from app.modules.product.repositories.category_repository import CategoryRepository
from app.core.exceptions.validation_exception import ValidationException

class CategoryServiceImpl(CategoryService):
    def __init__(self, category_repo: CategoryRepository):
        self.category_repo = category_repo

    def get_all_categories(self):
        return self.category_repo.get_all()

    def create_category(self, name: str) -> int:
        clean_name = name.strip() if name else ""
        if not clean_name:
            raise ValidationException("Tên danh mục không được để trống!")

        if self.category_repo.exists_by_name(clean_name):
            raise ValidationException(f"Danh mục '{clean_name}' đã tồn tại trong hệ thống!")

        return self.category_repo.create(clean_name)