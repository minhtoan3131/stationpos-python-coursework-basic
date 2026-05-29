import re
from app.core.exceptions.validation_exception import ValidationException
from app.modules.inventory.repositories.inventory_repository import InventoryRepository

from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO
from app.modules.product.dtos.product_delete_dto import ProductDeleteDTO
from app.modules.product.repositories.product_repository import ProductRepository


class ProductValidator:

    def __init__(
            self,
            product_repository: ProductRepository,
            inventory_repository: InventoryRepository = None
    ):
        self.product_repository = product_repository
        self.inventory_repository = inventory_repository

    # =========================
    # CREATE VALIDATION
    # =========================

    def validate_create(self, dto: ProductCreateDTO) -> None:
        # 1. Validate logic thuần (Không cần DB)
        self._validate_pure_logic(dto)

        # 2. Validate với Database (Check trùng lặp)
        self._validate_unique_sku(dto.sku)
        if dto.barcode and str(dto.barcode).strip():
            self._validate_unique_barcode(str(dto.barcode).strip())

    # =========================
    # UPDATE VALIDATION
    # =========================

    def validate_update(self, dto: ProductUpdateDTO) -> None:
        # 1. Kiểm tra sự tồn tại của sản phẩm
        existing_product = self.product_repository.get_product_by_id(dto.product_id)
        if existing_product is None:
            raise ValidationException("Sản phẩm không tồn tại trong hệ thống.")
        if not existing_product.is_active:
            raise ValidationException("Không thể cập nhật sản phẩm đã bị xóa.")

        # 2. Validate logic thuần
        self._validate_pure_logic(dto)

        # 3. Validate với Database (Loại trừ ID của chính nó)
        self._validate_unique_sku_for_update(dto.sku, dto.product_id)
        if dto.barcode and str(dto.barcode).strip():
            self._validate_unique_barcode_for_update(str(dto.barcode).strip(), dto.product_id)

    # =========================
    # DELETE VALIDATION
    # =========================

    def validate_delete(self, dto: ProductDeleteDTO) -> None:
        product = self.product_repository.get_product_by_id(dto.product_id)
        if product is None:
            raise ValidationException("Sản phẩm không tồn tại.")
        if not product.is_active:
            raise ValidationException("Sản phẩm đã bị xóa từ trước.")

        if self.inventory_repository is None:
            raise Exception("Chưa cấu hình InventoryRepository cho Validator.")

        inventory_qty = self.inventory_repository.get_inventory_quantity(dto.product_id)
        if inventory_qty > 0:
            raise ValidationException(
                f"Không thể xóa! Sản phẩm này vẫn còn {inventory_qty} đơn vị trong kho. "
                "Vui lòng xuất hủy tồn kho về 0 trước khi xóa để đảm bảo toàn vẹn dữ liệu."
            )

    # =========================
    # PURE LOGIC VALIDATION (Các ràng buộc tại chỗ)
    # =========================

    def _validate_pure_logic(self, dto) -> None:
        """Gộp các nhóm hàm kiểm tra logic để code gọn gàng"""
        self._validate_identity_and_classification(dto)
        self._validate_units_and_conversions(dto)
        self._validate_inventory_and_misc(dto)

    def _validate_identity_and_classification(self, dto) -> None:
        # 1. Tên sản phẩm
        if not dto.name or not dto.name.strip():
            raise ValidationException("Tên sản phẩm không được để trống.")
        if len(dto.name) > 255:
            raise ValidationException("Tên sản phẩm không được vượt quá 255 ký tự.")

        # 2. Mã sản phẩm (SKU) - BẮT BUỘC NHẬP
        if not dto.sku or not str(dto.sku).strip():
            raise ValidationException("Mã sản phẩm (SKU) bắt buộc phải nhập.")

        sku_clean = str(dto.sku).strip()
        if len(sku_clean) > 50:
            raise ValidationException("Mã sản phẩm (SKU) không được vượt quá 50 ký tự.")

        # Format SKU: Chỉ chữ cái, số, gạch ngang, gạch dưới. Không chứa khoảng trắng.
        if not re.match(r"^[A-Za-z0-9_-]+$", sku_clean):
            raise ValidationException(
                "Mã sản phẩm (SKU) chỉ được chứa chữ cái không dấu, chữ số, dấu '-' hoặc '_'. Không chứa khoảng trắng.")

        # 3. Mã vạch (Barcode) - Tùy chọn
        if dto.barcode and str(dto.barcode).strip():
            barcode_clean = str(dto.barcode).strip()
            if not barcode_clean.isdigit():
                raise ValidationException("Mã vạch (Barcode) chỉ được chứa các chữ số.")
            if len(barcode_clean) != 13:
                raise ValidationException("Mã vạch (Barcode) phải có độ dài chuẩn xác là 13 chữ số.")

        # 4. Danh mục (Bắt buộc)
        if not dto.category_id or dto.category_id <= 0:
            raise ValidationException("Vui lòng chọn một Danh mục hàng hóa hợp lệ.")

    def _validate_units_and_conversions(self, dto) -> None:

        # 5. Đơn vị cơ bản (Bắt buộc)
        if not dto.base_unit_id or dto.base_unit_id <= 0:
            raise ValidationException("Vui lòng chọn Đơn vị tính cơ bản (Ví dụ: Cái, Cây).")

        # 6. Ràng buộc Đơn vị quy đổi (Sỉ)
        if dto.conversion_unit_id is not None and dto.conversion_unit_id > 0:

            if dto.base_unit_id == dto.conversion_unit_id:
                raise ValidationException("Đơn vị sỉ KHÔNG ĐƯỢC TRÙNG với Đơn vị cơ bản.")

            if dto.conversion_ratio is None or dto.conversion_ratio <= 1:
                raise ValidationException("Tỷ lệ quy đổi phải lớn hơn 1 (Ví dụ: 1 Hộp = 12 Cái).")

    def _validate_inventory_and_misc(self, dto) -> None:
        # 7. Tồn kho tối thiểu
        if dto.min_stock is None or not (0 <= dto.min_stock <= 999999):
            raise ValidationException("Ngưỡng cảnh báo tồn kho tối thiểu phải nằm trong khoảng từ 0 đến 999,999.")

        # 8. Mô tả
        if dto.description and len(dto.description) > 1000:
            raise ValidationException("Mô tả sản phẩm quá dài (Tối đa 1000 ký tự).")

    # =========================
    # DB LOGIC VALIDATION
    # =========================

    def _validate_unique_sku(self, sku: str) -> None:
        if self.product_repository.exists_by_sku(sku):
            raise ValidationException(f"Mã sản phẩm (SKU) '{sku}' đã tồn tại trong hệ thống. Vui lòng nhập mã khác.")

    def _validate_unique_sku_for_update(self, sku: str, product_id: int) -> None:
        if self.product_repository.exists_by_sku_excluding_id(sku, product_id):
            raise ValidationException(f"Mã sản phẩm (SKU) '{sku}' đã được sử dụng bởi một mặt hàng khác.")

    def _validate_unique_barcode(self, barcode: str) -> None:
        if self.product_repository.exists_by_barcode(barcode):
            raise ValidationException(f"Mã vạch '{barcode}' đã tồn tại trong hệ thống. Hãy kiểm tra lại.")

    def _validate_unique_barcode_for_update(self, barcode: str, product_id: int) -> None:
        if self.product_repository.exists_by_barcode_excluding_id(barcode, product_id):
            raise ValidationException(f"Mã vạch '{barcode}' đã bị trùng với một mặt hàng khác.")