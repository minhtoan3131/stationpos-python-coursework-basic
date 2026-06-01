import pytest
import copy
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.services.impl.store_config_service_impl import StoreConfigServiceImpl
from app.modules.setting.constants.setting_key import SettingKey


# ==============================================================================
# FAKE OBJECTS
# ==============================================================================

class FakeSettingRepository:
    """Fake Repository lưu trữ dữ liệu gọn nhẹ trong bộ nhớ tạm RAM"""

    def __init__(self, data_store: dict):
        self.data_store = data_store

    def get_all_settings(self) -> dict:
        return self.data_store

    def update_setting(self, key: str, new_value: str) -> bool:
        self.data_store[key] = str(new_value)
        return True


class FakeUnitOfWork:
    """Fake Unit of Work quản lý phiên giao dịch an toàn với cơ chế Snapshot"""

    def __init__(self, shared_db: dict):
        self.shared_db = shared_db
        self.snapshot = None

    def __enter__(self):
        # Chụp ảnh trạng thái trước khi Use Case chỉnh sửa
        self.snapshot = copy.deepcopy(self.shared_db)
        self.setting_repo = FakeSettingRepository(self.shared_db)
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            # LƯU Ý BẢO VỆ: Nếu xảy ra crash văng lỗi nghiệp vụ -> Quay xe khôi phục ngay
            self.shared_db.clear()
            self.shared_db.update(self.snapshot)


# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================

@pytest.fixture
def memory_db():
    """Khởi tạo một DB RAM trống trơn trước mỗi bài test"""
    return {}


@pytest.fixture
def fake_uow_factory(memory_db):
    """Cấp phát phân mảnh giao dịch chia sẻ chung bộ nhớ memory_db"""
    return lambda: FakeUnitOfWork(memory_db)


@pytest.fixture
def store_config_service(fake_uow_factory):
    """Bơm hạ tầng Fake vào cửa ngõ Service cần kiểm thử"""
    return StoreConfigServiceImpl(uow_factory=fake_uow_factory)


# ==============================================================================
# PRE-CONDITIONS TEST CASES
# ==============================================================================

@pytest.mark.parametrize("blank_name", [
    "",  # Chuỗi rỗng tuyệt đối
    "   ",  # Chuỗi chứa toàn ký tự khoảng trắng space
    "\t\t",  # Chuỗi chứa ký tự Tab hệ thống
    "\n\n\r"  # Chuỗi chứa ký tự xuống dòng phá layout
])
def test_save_store_config_should_fail_immediately_when_name_is_blank(blank_name, store_config_service, memory_db):
    """
    RÀNG BUỘC TIÊN QUYẾT (Use Case 2): Lưu thông tin cấu hình cửa hàng
    - Given: Người dùng nhập vào Form một tên shop trống hoặc chứa toàn kí tự vô nghĩa.
    - When: Hệ thống gọi lệnh save_store_config().
    - Then: Bắt buộc phải chặn đứng lập tức, ném lỗi ValueError, và tuyệt đối không làm biến động DB.
    """
    # GIVEN: Chuẩn bị DTO mang tên bẩn (vi phạm giao kèo nghiệp vụ)
    invalid_dto = StoreConfigDTO(
        name=blank_name,
        phone="0912345678",
        address="123 Đường ABC",
        paper_size="K80",
        footer="Hẹn gặp lại quý khách!"
    )

    # Đảm bảo ban đầu bộ lưu trữ đang trống sạch
    assert len(memory_db) == 0

    # WHEN & THEN: Áp dụng Bài 2, dùng rào chắn pytest.raises để bắt lỗi văng ra ngoài
    with pytest.raises(ValueError) as exc_info:
        store_config_service.save_store_config(invalid_dto)

    # 1. Xác minh thông điệp cảnh báo trả ngược lên UI hiển thị cho chủ quán là chuẩn xác
    assert str(exc_info.value) == "Tên cửa hàng không được để trống!"

    # 2. KIỂM CHỨNG CHỐNG LỌT LƯỚI (Safety State Assertion):
    # Chứng minh tuyệt đối rằng vì bị chặn ngay ở hàng rào tiên quyết,
    # Database RAM hoàn toàn không bị đột biến bẩn, độ dài các cặp cấu hình vẫn bằng 0!
    assert len(memory_db) == 0