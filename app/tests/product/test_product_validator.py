import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from app.core.exceptions.validation_exception import ValidationException
from app.modules.product.validators.product_validator import ProductValidator
from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO
from app.modules.product.dtos.product_delete_dto import ProductDeleteDTO


# ==========================================
# MOCK ENTITY
# ==========================================
@dataclass
class MockProduct:
    id: int
    is_active: bool


# ==========================================
# FIXTURES (Setup dữ liệu dùng chung)
# ==========================================

@pytest.fixture
def mock_product_repo():
    return MagicMock()

@pytest.fixture
def mock_inventory_repo():
    return MagicMock()

@pytest.fixture
def validator(mock_product_repo, mock_inventory_repo):
    return ProductValidator(product_repository=mock_product_repo, inventory_repository=mock_inventory_repo)


@pytest.fixture
def valid_create_dto():
    """Tạo một DTO Create chuẩn, hợp lệ mọi điều kiện"""
    return ProductCreateDTO(
        sku="SP_001",
        name="Bút bi Thiên Long",
        barcode="8935001700010",
        category_id=1,
        supplier_id=1,
        base_unit_id=1,
        cost_price=3000,
        retail_price=5000,
        wholesale_price=4500,
        min_stock=10,
        description="Mô tả",
        conversion_unit_id=2,
        conversion_ratio=12
    )


@pytest.fixture
def valid_update_dto():
    """Tạo một DTO Update chuẩn, hợp lệ mọi điều kiện"""
    return ProductUpdateDTO(
        product_id=1,
        sku="SP_001",
        name="Bút bi Thiên Long",
        barcode="8935001700010",
        category_id=1,
        supplier_id=1,
        base_unit_id=1,
        cost_price=3000,
        retail_price=5000,
        wholesale_price=4500,
        min_stock=10,
        description="Mô tả",
        conversion_unit_id=2,
        conversion_ratio=12,
        is_active=True
    )


@pytest.fixture
def valid_delete_dto():
    return ProductDeleteDTO(product_id=1)


# ==========================================
# TESTS: BASIC INFO (Tên, SKU, Barcode)
# ==========================================

def test_validate_basic_info_name_empty(validator, valid_create_dto):
    valid_create_dto.name = "   "
    with pytest.raises(ValidationException, match="Tên sản phẩm không được để trống"):
        validator._validate_identity_and_classification(valid_create_dto)


def test_validate_basic_info_name_too_long(validator, valid_create_dto):
    valid_create_dto.name = "A" * 256
    with pytest.raises(ValidationException, match="Tên sản phẩm không được vượt quá 255 ký tự"):
        validator._validate_identity_and_classification(valid_create_dto)


def test_validate_basic_info_sku_empty(validator, valid_create_dto):
    valid_create_dto.sku = ""
    with pytest.raises(ValidationException, match="SKU"):
        validator._validate_identity_and_classification(valid_create_dto)


def test_validate_basic_info_sku_too_long(validator, valid_create_dto):
    valid_create_dto.sku = "A" * 51
    with pytest.raises(ValidationException, match="SKU"):
        validator._validate_identity_and_classification(valid_create_dto)


def test_validate_basic_info_sku_invalid_format(validator, valid_create_dto):
    invalid_skus = ["SP 001", "SP@001", "SP/001", "Tiếng Việt"]
    for sku in invalid_skus:
        valid_create_dto.sku = sku
        with pytest.raises(ValidationException, match="chỉ được chứa chữ cái không dấu, chữ số, dấu '-' hoặc '_'. Không chứa khoảng trắng."):
            validator._validate_identity_and_classification(valid_create_dto)


def test_validate_basic_info_barcode_not_digits(validator, valid_create_dto):
    valid_create_dto.barcode = "123456789012A"
    with pytest.raises(ValidationException, match="chỉ được chứa các chữ số"):
        validator._validate_identity_and_classification(valid_create_dto)


def test_validate_basic_info_barcode_invalid_length(validator, valid_create_dto):
    valid_create_dto.barcode = "12345"  # Quá ngắn
    with pytest.raises(ValidationException, match="phải có độ dài chuẩn xác là 13 chữ số"):
        validator._validate_identity_and_classification(valid_create_dto)


def test_validate_basic_info_no_barcode(validator, valid_create_dto):
    valid_create_dto.barcode = None
    # Nếu không có barcode, sẽ không lỗi (Pass)
    validator._validate_identity_and_classification(valid_create_dto)


# ==========================================
# TESTS: PRICES & CONVERSION
# ==========================================

def test_validate_prices_out_of_range(validator, valid_create_dto):
    # Test âm
    valid_create_dto.cost_price = -1
    with pytest.raises(ValidationException, match="Giá nhập"):
        validator._validate_units_and_prices(valid_create_dto)

    # Test vượt quá giới hạn
    valid_create_dto.cost_price = 1000
    valid_create_dto.retail_price = 1000000000
    with pytest.raises(ValidationException, match="Giá bán lẻ"):
        validator._validate_units_and_prices(valid_create_dto)

    valid_create_dto.retail_price = 2000
    valid_create_dto.wholesale_price = 1000000000
    with pytest.raises(ValidationException, match="Giá bán sỉ"):
        validator._validate_units_and_prices(valid_create_dto)


def test_validate_prices_logic_errors(validator, valid_create_dto):
    valid_create_dto.cost_price = 5000

    # Bán lẻ lỗ
    valid_create_dto.retail_price = 4000
    with pytest.raises(ValidationException, match="không được thấp hơn giá nhập"):
        validator._validate_units_and_prices(valid_create_dto)

    valid_create_dto.retail_price = 6000

    # Bán sỉ lỗ
    valid_create_dto.wholesale_price = 4500
    with pytest.raises(ValidationException, match="không được thấp hơn giá nhập"):
        validator._validate_units_and_prices(valid_create_dto)

    # Sỉ đắt hơn Lẻ
    valid_create_dto.wholesale_price = 6500
    with pytest.raises(ValidationException, match="không được cao hơn giá bán lẻ"):
        validator._validate_units_and_prices(valid_create_dto)


def test_validate_conversion_no_conversion(validator, valid_create_dto):
    valid_create_dto.conversion_unit_id = None
    # Hàm chạy thành công, không làm gì cả
    validator._validate_units_and_prices(valid_create_dto)


def test_validate_conversion_same_unit(validator, valid_create_dto):
    valid_create_dto.base_unit_id = 1
    valid_create_dto.conversion_unit_id = 1
    with pytest.raises(ValidationException, match="KHÔNG ĐƯỢC TRÙNG"):
        validator._validate_units_and_prices(valid_create_dto)


def test_validate_conversion_missing_ratio(validator, valid_create_dto):
    valid_create_dto.conversion_ratio = None
    with pytest.raises(ValidationException, match="phải lớn hơn 1"):
        validator._validate_units_and_prices(valid_create_dto)


def test_validate_conversion_invalid_ratio(validator, valid_create_dto):
    valid_create_dto.conversion_ratio = 1
    with pytest.raises(ValidationException, match="lớn hơn 1"):
        validator._validate_units_and_prices(valid_create_dto)


# ==========================================
# TESTS: MIN STOCK (Tồn tối thiểu)
# ==========================================

def test_validate_min_stock_invalid(validator, valid_create_dto):
    valid_create_dto.min_stock = -5
    with pytest.raises(ValidationException, match="Ngưỡng cảnh báo tồn kho tối thiểu phải nằm trong khoảng"):
        validator._validate_inventory_and_misc(valid_create_dto)

    valid_create_dto.min_stock = 1000000
    with pytest.raises(ValidationException, match="Ngưỡng cảnh báo tồn kho tối thiểu phải nằm trong khoảng"):
        validator._validate_inventory_and_misc(valid_create_dto)


# ==========================================
# TESTS: DATABASE LOGIC (Trùng lặp DB)
# ==========================================

def test_validate_unique_sku(validator, mock_product_repo):
    mock_product_repo.exists_by_sku.return_value = True
    with pytest.raises(ValidationException, match="đã tồn tại trong hệ thống"):
        validator._validate_unique_sku("SP_001")


def test_validate_unique_sku_for_update(validator, mock_product_repo):
    mock_product_repo.exists_by_sku_excluding_id.return_value = True
    # Cập nhật chữ "sản phẩm khác" thành "mặt hàng khác" cho khớp code
    with pytest.raises(ValidationException, match="đã được sử dụng bởi một mặt hàng khác"):
        validator._validate_unique_sku_for_update("SP_001", 1)


def test_validate_unique_barcode(validator, mock_product_repo):
    mock_product_repo.exists_by_barcode.return_value = True
    with pytest.raises(ValidationException, match="đã tồn tại trong hệ thống"):
        validator._validate_unique_barcode("123")


def test_validate_unique_barcode_for_update(validator, mock_product_repo):
    mock_product_repo.exists_by_barcode_excluding_id.return_value = True
    # Cập nhật chữ "sử dụng" thành "trùng với một mặt hàng khác" cho khớp code
    with pytest.raises(ValidationException, match="đã bị trùng với một mặt hàng khác"):
        validator._validate_unique_barcode_for_update("123", 1)


# ==========================================
# TESTS: VALIDATE CREATE (Main Method)
# ==========================================

def test_validate_create_success(validator, valid_create_dto, mock_product_repo):
    # Setup mock DB trả về False (Không trùng)
    mock_product_repo.exists_by_sku.return_value = False
    mock_product_repo.exists_by_barcode.return_value = False

    # Không raise lỗi => Pass
    validator.validate_create(valid_create_dto)


def test_validate_create_success_no_barcode(validator, valid_create_dto, mock_product_repo):
    valid_create_dto.barcode = None
    mock_product_repo.exists_by_sku.return_value = False

    # Sẽ pass và không bao giờ gọi hàm check trùng barcode
    validator.validate_create(valid_create_dto)
    mock_product_repo.exists_by_barcode.assert_not_called()


# ==========================================
# TESTS: VALIDATE UPDATE (Main Method)
# ==========================================

def test_validate_update_success(validator, valid_update_dto, mock_product_repo):
    # Tồn tại và đang active
    mock_product_repo.get_product_by_id.return_value = MockProduct(id=1, is_active=True)
    mock_product_repo.exists_by_sku_excluding_id.return_value = False
    mock_product_repo.exists_by_barcode_excluding_id.return_value = False

    validator.validate_update(valid_update_dto)


def test_validate_update_product_not_found(validator, valid_update_dto, mock_product_repo):
    mock_product_repo.get_product_by_id.return_value = None
    with pytest.raises(ValidationException, match="Sản phẩm không tồn tại trong hệ thống"):
        validator.validate_update(valid_update_dto)


def test_validate_update_product_inactive(validator, valid_update_dto, mock_product_repo):
    mock_product_repo.get_product_by_id.return_value = MockProduct(id=1, is_active=False)
    with pytest.raises(ValidationException, match="Không thể cập nhật sản phẩm đã bị xóa"):
        validator.validate_update(valid_update_dto)


# ==========================================
# TESTS: VALIDATE DELETE (Main Method)
# ==========================================

def test_validate_delete_success(validator, valid_delete_dto, mock_product_repo, mock_inventory_repo):
    # ProductRepo check tồn tại
    mock_product_repo.get_product_by_id.return_value = MockProduct(id=1, is_active=True)

    # InventoryRepo check tồn kho = 0 => Cho xóa
    mock_inventory_repo.get_inventory_quantity.return_value = 0

    validator.validate_delete(valid_delete_dto)


def test_validate_delete_not_found(validator, valid_delete_dto, mock_product_repo):
    mock_product_repo.get_product_by_id.return_value = None
    with pytest.raises(ValidationException, match="Sản phẩm không tồn tại"):
        validator.validate_delete(valid_delete_dto)


def test_validate_delete_already_inactive(validator, valid_delete_dto, mock_product_repo):
    mock_product_repo.get_product_by_id.return_value = MockProduct(id=1, is_active=False)
    with pytest.raises(ValidationException, match="Sản phẩm đã bị xóa từ trước"):
        validator.validate_delete(valid_delete_dto)


def test_validate_delete_inventory_not_empty(validator, valid_delete_dto, mock_product_repo, mock_inventory_repo):
    # ProductRepo check tồn tại
    mock_product_repo.get_product_by_id.return_value = MockProduct(id=1, is_active=True)

    # InventoryRepo báo đang còn tồn kho
    mock_inventory_repo.get_inventory_quantity.return_value = 50

    with pytest.raises(ValidationException, match="vẫn còn 50 đơn vị trong kho"):
        validator.validate_delete(valid_delete_dto)


#Test case đảm bảo Validator báo lỗi nếu quên truyền InventoryRepo
def test_validate_delete_missing_inventory_repo(valid_delete_dto, mock_product_repo):
    # Cố tình tạo validator thiếu inventory_repo
    bad_validator = ProductValidator(product_repository=mock_product_repo, inventory_repository=None)
    mock_product_repo.get_product_by_id.return_value = MockProduct(id=1, is_active=True)

    with pytest.raises(Exception, match="Chưa cấu hình InventoryRepository"):
        bad_validator.validate_delete(valid_delete_dto)