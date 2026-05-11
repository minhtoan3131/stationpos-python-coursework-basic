from app.modules.product.services.supplier_service import SupplierService
from app.modules.product.repositories.supplier_repository import SupplierRepository
from app.core.exceptions.validation_exception import ValidationException

class SupplierServiceImpl(SupplierService):
    def __init__(self, supplier_repo: SupplierRepository):
        self.supplier_repo = supplier_repo

    def get_all_suppliers(self):
        return self.supplier_repo.get_all()

    def create_supplier(self, name: str) -> int:
        # Validation Bề mặt
        clean_name = name.strip() if name else ""
        if not clean_name:
            raise ValidationException("Tên nhà cung cấp không được để trống!")

        #  Validation Business (Check trùng)
        if self.supplier_repo.exists_by_name(clean_name):
            raise ValidationException(f"Nhà cung cấp '{clean_name}' đã tồn tại trong hệ thống!")

        # Chuyển cho Repo lưu xuống DB
        return self.supplier_repo.create(clean_name)