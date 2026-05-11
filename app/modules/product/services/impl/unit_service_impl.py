from app.modules.product.services.unit_service import UnitService
from app.modules.product.repositories.unit_repository import UnitRepository
from app.core.exceptions.validation_exception import ValidationException

class UnitServiceImpl(UnitService):
    def __init__(self, unit_repo: UnitRepository):
        self.unit_repo = unit_repo

    def get_all_units(self):
        return self.unit_repo.get_all()

    def create_unit(self, name: str) -> int:
        clean_name = name.strip() if name else ""
        if not clean_name:
            raise ValidationException("Tên đơn vị tính không được để trống!")

        if self.unit_repo.exists_by_name(clean_name):
            raise ValidationException(f"Đơn vị tính '{clean_name}' đã tồn tại trong hệ thống!")

        return self.unit_repo.create(clean_name)