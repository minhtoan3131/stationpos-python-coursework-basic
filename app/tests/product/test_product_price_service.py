# app/tests/product/test_product_price_service.py
import pytest
from unittest.mock import MagicMock
from app.modules.product.services.impl.product_service_impl import ProductServiceImpl


# ==============================================================================
# IN-MEMORY STATE STORE (Kho trạng thái RAM dùng chung cho luồng test hòa đồng)
# ==============================================================================
class FakeProductState:
    def __init__(self):
        prod = MagicMock(id=1, sku="SP001", cost_price=4000.0, retail_price=5000.0, wholesale_price=4500.0)
        prod.name = "Bút bi Thiên Long"

        self.products = {1: prod}
        self.logs = []
        self.committed = False
        self.rolled_back = False


# ==============================================================================
# PYTEST FIXTURES (Setup môi trường giả lập liên kết phân lớp)
# ==============================================================================
@pytest.fixture
def fake_state():
    return FakeProductState()


@pytest.fixture
def service(mocker, fake_state):
    """Fixture đánh chặn kết nối và biến đổi Repo thật thành Fake RAM Store"""
    mocker.patch("app.modules.product.services.impl.product_service_impl.DatabaseConnection")

    mock_tx_class = mocker.patch("app.modules.product.services.impl.product_service_impl.TransactionManager")
    mock_tx = mock_tx_class.return_value
    mock_tx.commit.side_effect = lambda: setattr(fake_state, 'committed', True)
    mock_tx.rollback.side_effect = lambda: setattr(fake_state, 'rolled_back', True)

    mock_repo_class = mocker.patch("app.modules.product.services.impl.product_service_impl.ProductRepositoryImpl")
    mock_product_repo = mock_repo_class.return_value

    mock_product_repo.get_product_by_id.side_effect = lambda p_id: fake_state.products.get(p_id)

    def fake_update_prices(p_id, retail, wholesale):
        if p_id in fake_state.products:
            fake_state.products[p_id].retail_price = retail
            fake_state.products[p_id].wholesale_price = wholesale
            return True
        return False

    mock_product_repo.update_selling_prices.side_effect = fake_update_prices

    mock_log_class = mocker.patch(
        "app.modules.dashboard.repositories.impl.activity_log_repository_impl.ActivityLogRepositoryImpl")
    mock_activity_log_repo = mock_log_class.return_value

    def fake_add_log(action_type, reference_code, description):
        fake_state.logs.append({
            'action_type': action_type,
            'reference_code': reference_code,
            'description': description
        })
        return True

    mock_activity_log_repo.add_log.side_effect = fake_add_log

    return ProductServiceImpl()


# ==============================================================================
# TEST CASES
# ==============================================================================

def test_update_product_prices_happy_path_state_changes(service, fake_state):
    """
    HẬU QUYẾT (Happy Path): Thay đổi giá bán nhanh thành công.
    Kiểm chứng nghiêm ngặt:
    1. Hàm trả về True điều hướng UI tải lại bảng.
    2. Đột biến trạng thái giá mới đè lên RAM Store thành công.
    3. Giao dịch được CHỐT (Commit = True).
    4. Tự động kết xuất 1 dòng Nhật ký Event sang Dashboard đúng Schema.
    """
    product_id = 1
    new_retail = 6000.0
    new_wholesale = 5500.0

    result = service.update_product_prices(product_id, new_retail, new_wholesale)

    assert result is True

    assert fake_state.products[1].retail_price == 6000.0
    assert fake_state.products[1].wholesale_price == 5500.0

    assert fake_state.committed is True
    assert fake_state.rolled_back is False

    assert len(fake_state.logs) == 1
    audit_log = fake_state.logs[0]
    assert audit_log['action_type'] == 'SYSTEM'
    assert audit_log['reference_code'] == 'SP001'
    assert "Thay đổi giá bán mặt hàng [Bút bi Thiên Long]" in audit_log['description']
    assert "Lẻ: 6,000" in audit_log['description']
    assert "Sỉ: 5,500" in audit_log['description']


def test_update_product_prices_should_rollback_on_repository_crash(service, fake_state, mocker):
    """
    BẤT BIẾN (ACID Transaction): Gặp sự cố treo kết nối DB vật lý giữa chừng.
    Kiểm chứng nghiêm ngặt:
    1. Khi câu lệnh SQL update quăng lỗi hệ thống, Service phải bắt được.
    2. Kích hoạt lệnh hoàn tác dữ liệu (Rollback = True) để chống rò rỉ hoặc kẹt trạng thái kết nối.
    3. Không được commit bậy bạ dữ liệu lỗi.
    """
    mock_repo_class = mocker.patch("app.modules.product.services.impl.product_service_impl.ProductRepositoryImpl")
    mock_product_repo = mock_repo_class.return_value
    mock_product_repo.get_product_by_id.return_value = fake_state.products[1]

    mock_product_repo.update_selling_prices.side_effect = RuntimeError("Database connection timed out!")

    with pytest.raises(RuntimeError, match="Database connection timed out"):
        service.update_product_prices(product_id=1, retail_price=7000.0, wholesale_price=6500.0)

    assert fake_state.rolled_back is True
    assert fake_state.committed is False
    assert len(fake_state.logs) == 0