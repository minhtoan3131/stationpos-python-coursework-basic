from app.core.exceptions.validation_exception import ValidationException
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO
from app.modules.product.repositories.product_repository import ProductRepository
from app.modules.product.repositories.supplier_repository import SupplierRepository

class InventoryValidator:
    def __init__(self, product_repo: ProductRepository, supplier_repo: SupplierRepository):
        self.product_repo = product_repo
        self.supplier_repo = supplier_repo

    def validate_purchase_order(self, dto: PurchaseOrderCreateDTO) -> None:
        if dto.supplier_id:
            if not self.supplier_repo.exists_by_id(dto.supplier_id):
                raise ValidationException("Nhà cung cấp không tồn tại hoặc đã bị xóa.")

        if not dto.items:
            raise ValidationException("Phiếu nhập không có sản phẩm nào.")

        product_ids = set()
        for item in dto.items:
            if item.product_id in product_ids:
                raise ValidationException(f"Sản phẩm ID {item.product_id} bị lặp lại nhiều dòng.")
            product_ids.add(item.product_id)

            if item.quantity <= 0:
                raise ValidationException("Số lượng nhập phải lớn hơn 0.")
            if item.unit_price < 0:
                raise ValidationException("Giá nhập không được nhỏ hơn 0.")

            product_dict = self.product_repo.get_product_detail_for_import(item.product_id)
            if not product_dict or not product_dict.get('is_active'):
                raise ValidationException(f"Sản phẩm (ID: {item.product_id}) không tồn tại hoặc đã ngừng kinh doanh.")

            valid_units = [product_dict.get('base_unit_id')]
            if product_dict.get('conversion_unit_id'):
                valid_units.append(product_dict.get('conversion_unit_id'))

            if item.unit_id not in valid_units:
                raise ValidationException(f"Đơn vị tính chọn cho sản phẩm '{product_dict.get('name')}' không hợp lệ.")