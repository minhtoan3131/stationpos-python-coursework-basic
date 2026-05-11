import pytest

from app.modules.product.dtos.product_delete_dto import ProductDeleteDTO
from app.modules.product.dtos.product_filter_dto import ProductFilterDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO
from app.modules.product.entities.product import Product
from app.modules.product.entities.unit_conversion import UnitConversion
from app.modules.product.services.impl.product_service_impl import ProductServiceImpl
from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.core.exceptions.validation_exception import ValidationException


# ==========================================
# (MOCKING DEPENDENCIES)
# ==========================================

@pytest.fixture
def mock_db_connection(mocker):
    """Mock kết nối DB và hàm close()"""
    mock_conn = mocker.Mock()
    # Patch hàm get_connection để nó trả về mock_conn
    mocker.patch(
        'app.modules.product.services.impl.product_service_impl.DatabaseConnection.get_connection',
        return_value=mock_conn
    )
    return mock_conn


@pytest.fixture
def mock_transaction(mocker):
    """Mock TransactionManager để theo dõi commit/rollback"""
    mock_trans = mocker.Mock()
    mocker.patch(
        'app.modules.product.services.impl.product_service_impl.TransactionManager',
        return_value=mock_trans
    )
    return mock_trans


@pytest.fixture
def mock_product_repo(mocker):
    mock_repo = mocker.Mock()
    mocker.patch(
        'app.modules.product.services.impl.product_service_impl.ProductRepositoryImpl',
        return_value=mock_repo
    )
    return mock_repo


@pytest.fixture
def mock_unit_conv_repo(mocker):
    mock_repo = mocker.Mock()
    mocker.patch(
        'app.modules.product.services.impl.product_service_impl.UnitConversionRepositoryImpl',
        return_value=mock_repo
    )
    return mock_repo


@pytest.fixture
def mock_validator(mocker):
    mock_val = mocker.Mock()
    mocker.patch(
        'app.modules.product.services.impl.product_service_impl.ProductValidator',
        return_value=mock_val
    )
    return mock_val


@pytest.fixture
def product_service():
    return ProductServiceImpl()


# Dữ liệu DTO mẫu
@pytest.fixture
def create_dto_with_conversion():
    return ProductCreateDTO(
        sku="SP1", name="Bút", barcode=None, category_id=1, supplier_id=1,
        base_unit_id=1, cost_price=10, retail_price=20, wholesale_price=15,
        min_stock=5, description=None, conversion_unit_id=2, conversion_ratio=12
    )

@pytest.fixture
def mock_inventory_repo(mocker):
    mock_repo = mocker.Mock()
    mocker.patch(
        'app.modules.product.services.impl.product_service_impl.InventoryRepositoryImpl',
        return_value=mock_repo
    )
    return mock_repo

@pytest.fixture
def update_dto_with_conversion():
    return ProductUpdateDTO(
        product_id=1, sku="SP1", name="Bút", barcode=None, category_id=1, supplier_id=1,
        base_unit_id=1, cost_price=10, retail_price=20, wholesale_price=15,
        min_stock=5, description=None, conversion_unit_id=2, conversion_ratio=12, is_active=True
    )

@pytest.fixture
def delete_dto():
    return ProductDeleteDTO(product_id=1)

@pytest.fixture
def mock_product_entity():
    """Mock đối tượng Product dùng cho các hàm GET"""
    return Product(
        id=1, sku="SP1", name="Bút", barcode="123", category_id=1, supplier_id=1,
        base_unit_id=1, cost_price=10, retail_price=20, wholesale_price=15,
        min_stock=5, description="Test", is_active=True, created_at=None
    )

@pytest.fixture
def sample_filter_dto():
    return ProductFilterDTO(
        keyword="Bút",
        category_id=1,
        supplier_id=None,
        is_active=True
    )


# ==========================================
# TEST CASES: CREATE
# ==========================================

def test_create_product_success(
        product_service, create_dto_with_conversion,
        mock_db_connection, mock_transaction, mock_product_repo, mock_unit_conv_repo, mock_validator
):
    """Kiểm tra kịch bản Happy Path: Mọi thứ suôn sẻ"""

    # GIVEN: Cấu hình mock repo trả về ID sản phẩm vừa tạo là 99
    mock_product_repo.create_product.return_value = 99

    # WHEN: Gọi service
    result_id = product_service.create_product(create_dto_with_conversion)

    # THEN:
    # Trả về đúng ID
    assert result_id == 99

    # Đảm bảo Validator ĐƯỢC GỌI
    mock_validator.validate_create.assert_called_once_with(create_dto_with_conversion)

    # Đảm bảo 2 Repo ĐƯỢC GỌI (Vì DTO có unit conversion)
    assert mock_product_repo.create_product.call_count == 1
    assert mock_unit_conv_repo.create_unit_conversion.call_count == 1

    # Đảm bảo TRANSACTION CÓ COMMIT
    mock_transaction.commit.assert_called_once()
    mock_transaction.rollback.assert_not_called()

    # Đảm bảo LUÔN LUÔN CLOSE CONNECTION
    mock_db_connection.close.assert_called_once()


def test_create_product_rollback_on_repository_error(
        product_service, create_dto_with_conversion,
        mock_db_connection, mock_transaction, mock_product_repo, mock_validator
):
    """Kiểm tra kịch bản Exception: DB chết giữa chừng phải Rollback"""

    # GIVEN: Giả lập lưu Product bị lỗi Database Error
    mock_product_repo.create_product.side_effect = Exception("DB Crash!")

    # WHEN & THEN
    with pytest.raises(Exception) as exc:
        product_service.create_product(create_dto_with_conversion)

    assert "DB Crash!" in str(exc.value)

    # không được commit
    mock_transaction.commit.assert_not_called()
    # phải rollback
    mock_transaction.rollback.assert_called_once()
    # connection phải được đóng
    mock_db_connection.close.assert_called_once()


def test_create_product_rollback_on_validation_error(
        product_service, create_dto_with_conversion,
        mock_db_connection, mock_transaction, mock_product_repo,
        mock_unit_conv_repo, mock_validator
):
    """Kiểm tra kịch bản Exception: Validator ném lỗi, Service phải bắt, rollback và raise tiếp"""

    # GIVEN: Giả lập Validator phát hiện lỗi và ném ValidationException
    mock_validator.validate_create.side_effect = ValidationException("Bất kỳ exception nào")

    # WHEN & THEN: Service PHẢI đẩy lỗi này lên trên (chứng minh dev không quên lệnh `raise`)
    with pytest.raises(ValidationException) as exc:
        product_service.create_product(create_dto_with_conversion)

    assert "Bất kỳ exception nào" in str(exc.value)

    mock_product_repo.create_product.assert_not_called()
    mock_unit_conv_repo.create_unit_conversion.assert_not_called()

    mock_transaction.commit.assert_not_called()
    mock_transaction.rollback.assert_called_once()

    mock_db_connection.close.assert_called_once()


# ==========================================
# TEST CASES: UPDATE
# ==========================================

def test_update_product_success_with_existing_conversion(
        product_service, update_dto_with_conversion,
        mock_db_connection, mock_transaction, mock_product_repo,
        mock_unit_conv_repo, mock_validator
):
    """Kịch bản: Update sản phẩm đã có sẵn quy đổi đơn vị từ trước"""
    mock_product_repo.update_product.return_value = True
    # Giả lập CÓ SẴN thông tin quy đổi trong DB
    mock_unit_conv_repo.get_unit_conversion.return_value = UnitConversion(
        id=1, product_id=1, from_unit_id=1, to_unit_id=2, ratio=10
    )

    result = product_service.update_product(update_dto_with_conversion)

    assert result is True
    mock_validator.validate_update.assert_called_once_with(update_dto_with_conversion)
    mock_product_repo.update_product.assert_called_once()

    # Vì đã có sẵn quy đổi -> Gọi hàm UPDATE chứ không phải CREATE
    mock_unit_conv_repo.update_unit_conversion.assert_called_once()
    mock_unit_conv_repo.create_unit_conversion.assert_not_called()

    mock_transaction.commit.assert_called_once()
    mock_db_connection.close.assert_called_once()


def test_update_product_success_with_new_conversion(
        product_service, update_dto_with_conversion,
        mock_db_connection, mock_transaction, mock_product_repo,
        mock_unit_conv_repo, mock_validator
):
    """Kịch bản: Update sản phẩm CHƯA CÓ quy đổi đơn vị (mới thêm vào)"""
    mock_product_repo.update_product.return_value = True
    # Giả lập CHƯA CÓ quy đổi trong DB
    mock_unit_conv_repo.get_unit_conversion.return_value = None

    product_service.update_product(update_dto_with_conversion)

    # Vì chưa có sẵn -> Gọi hàm CREATE
    mock_unit_conv_repo.create_unit_conversion.assert_called_once()
    mock_unit_conv_repo.update_unit_conversion.assert_not_called()


def test_update_product_validation_error(
        product_service, update_dto_with_conversion,
        mock_db_connection, mock_transaction, mock_product_repo, mock_validator
):
    """Kịch bản: Validator ném lỗi khi update"""
    mock_validator.validate_update.side_effect = ValidationException("Sản phẩm không tồn tại")

    with pytest.raises(ValidationException) as exc:
        product_service.update_product(update_dto_with_conversion)

    assert "Sản phẩm không tồn tại" in str(exc.value)

    mock_product_repo.update_product.assert_not_called()
    mock_transaction.rollback.assert_called_once()
    mock_db_connection.close.assert_called_once()


# ==========================================
# TEST CASES: DELETE
# ==========================================

def test_delete_product_success(
        product_service, delete_dto,
        mock_db_connection, mock_transaction, mock_product_repo,
        mock_inventory_repo, mock_validator
):
    mock_product_repo.soft_delete_product.return_value = True

    result = product_service.delete_product(delete_dto)

    assert result is True
    # Kiểm tra gọi validator
    mock_validator.validate_delete.assert_called_once_with(delete_dto)
    mock_product_repo.soft_delete_product.assert_called_once_with(1)

    # Kiểm tra Transaction và Connection
    mock_transaction.commit.assert_called_once()
    mock_db_connection.close.assert_called_once()


def test_delete_product_error(
        product_service, delete_dto,
        mock_db_connection, mock_transaction, mock_validator
):
    """Kịch bản: Lỗi khi xóa (VD tồn kho còn)"""
    mock_validator.validate_delete.side_effect = ValidationException("Còn tồn kho")

    with pytest.raises(ValidationException):
        product_service.delete_product(delete_dto)

    mock_transaction.rollback.assert_called_once()
    mock_db_connection.close.assert_called_once()


# ==========================================
# TEST CASES: READ
# ==========================================

def test_get_product_list(
        product_service, mock_db_connection, mock_product_repo
):
    # GIVEN: Dữ liệu DB trả về (Mock dict phù hợp với ProductMapper)
    mock_db_rows = [{
        "id": 1, "sku": "SP1", "name": "Bút", "category_name": "VPP",
        "unit_name": "Cái", "retail_price": 20, "wholesale_price": 15,
        "barcode": "123", "supplier_name": "NSX"
    }]
    mock_product_repo.get_product_list.return_value = mock_db_rows

    # WHEN
    result = product_service.get_product_list()

    # THEN
    assert len(result) == 1
    assert result[0].sku == "SP1"
    # Đảm bảo connection đóng
    mock_db_connection.close.assert_called_once()


def test_get_product_by_id_success(
        product_service, mock_product_entity,
        mock_db_connection, mock_product_repo, mock_unit_conv_repo
):
    mock_product_repo.get_product_by_id.return_value = mock_product_entity
    mock_unit_conv_repo.get_unit_conversion.return_value = None

    result = product_service.get_product_by_id(1)

    assert result is not None
    assert result.sku == "SP1"
    mock_db_connection.close.assert_called_once()


def test_get_product_by_id_not_found(
        product_service, mock_db_connection, mock_product_repo
):
    """Kịch bản: Yêu cầu lấy chi tiết một SP không tồn tại"""
    # GIVEN: Repo trả về None
    mock_product_repo.get_product_by_id.return_value = None

    # WHEN & THEN
    with pytest.raises(Exception, match="Không tìm thấy sản phẩm"):
        product_service.get_product_by_id(999)

    # Đảm bảo dù lỗi nhưng Connection VẪN PHẢI ĐÓNG
    mock_db_connection.close.assert_called_once()


def test_search_products_success(
        product_service, sample_filter_dto,
        mock_db_connection, mock_product_repo
):
    """Kịch bản: Tìm kiếm sản phẩm thành công, map đúng dữ liệu và truyền đúng tham số"""

    mock_db_rows = [{
        "id": 1, "sku": "SP1", "name": "Bút bi", "category_name": "VPP",
        "unit_name": "Cái", "retail_price": 20, "wholesale_price": 15,
        "barcode": "123", "supplier_name": "NSX"
    }]
    mock_product_repo.search_products.return_value = mock_db_rows

    # WHEN: Gọi hàm search từ service
    result = product_service.search_products(sample_filter_dto)

    # THEN:
    # Đảm bảo dữ liệu được Mapper chuyển đổi đúng thành List[ProductListDTO]
    assert len(result) == 1
    assert result[0].sku == "SP1"
    assert result[0].name == "Bút bi"

    # Đảm bảo Service truyền đúng các tham số từ DTO xuống Repository
    mock_product_repo.search_products.assert_called_once_with(
        keyword="Bút",
        category_id=1,
        supplier_id=None,
        is_active=True
    )

    # Đảm bảo luôn đóng kết nối database
    mock_db_connection.close.assert_called_once()