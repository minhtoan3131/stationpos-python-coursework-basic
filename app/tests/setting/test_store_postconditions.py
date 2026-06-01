from unittest.mock import MagicMock

import pytest
import copy
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.services.impl.store_config_service_impl import StoreConfigServiceImpl
from app.modules.setting.constants.setting_key import SettingKey


# ==============================================================================
# FAKE OBJECTS
# ==============================================================================

class FakeSettingRepository:
    """Fake Repository quản lý bộ nhớ Key-Value phẳng trên RAM"""
    def __init__(self, data_store: dict):
        self.data_store = data_store

    def get_all_settings(self) -> dict:
        return self.data_store

    def update_setting(self, key: str, new_value: str) -> bool:
        self.data_store[key] = str(new_value)
        return True


class FakeUnitOfWork:
    """Fake Unit of Work quản lý transaction an toàn bằng Deepcopy"""
    def __init__(self, shared_db: dict):
        self.shared_db = shared_db
        self.snapshot = None
        self.setting_repo = None
        self.activity_log_repo = MagicMock()


    def __enter__(self):
        self.snapshot = copy.deepcopy(self.shared_db)
        self.setting_repo = FakeSettingRepository(self.shared_db)
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            self.shared_db.clear()
            self.shared_db.update(self.snapshot)


# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================

@pytest.fixture
def memory_db():
    """Khởi tạo một DB RAM sạch cho mỗi bài test"""
    return {}


@pytest.fixture
def fake_uow_factory(memory_db):
    return lambda: FakeUnitOfWork(memory_db)


@pytest.fixture
def store_config_service(fake_uow_factory):
    return StoreConfigServiceImpl(uow_factory=fake_uow_factory)


# ==============================================================================
# POST-CONDITIONS TEST CASES
# ==============================================================================

def test_get_store_config_should_return_fallback_defaults_when_db_is_empty(store_config_service, memory_db):
    """
    HẬU QUYẾT (Use Case 1 - Happy Path rỗng): Đọc cấu hình khi app mới cài đặt lần đầu
    """
    assert len(memory_db) == 0

    # WHEN: Kích hoạt cửa ngõ đọc dữ liệu
    config = store_config_service.get_store_config()

    # THEN: Xác minh đúng các chuỗi fallback thực tế của dự án
    assert isinstance(config, StoreConfigDTO)
    assert config.name == "Văn phòng phẩm"
    assert config.phone == ""
    assert config.address == "Hà Nội"
    assert config.paper_size == "K80"
    assert config.footer == "Cảm ơn quý khách, hẹn gặp lại!"


def test_get_store_config_should_populate_dto_correctly_from_stored_data(store_config_service, memory_db):
    """
    HẬU QUYẾT (Use Case 1 - Happy Path chuẩn): Đọc cấu hình khi shop đã hoạt động và lưu data
    """
    # GIVEN: Khởi tạo mồi dữ liệu cấu hình theo đúng tên định danh Enum chuẩn của hệ thống
    memory_db[SettingKey.STORE_NAME.value] = "Văn phòng phẩm Tuổi Thơ"
    memory_db[SettingKey.STORE_PHONE.value] = "0987654321"
    memory_db[SettingKey.STORE_ADDRESS.value] = "Số 45, Đường XYZ, Hà Nội"
    memory_db[SettingKey.PRINT_PAPER_SIZE.value] = "K58"
    memory_db[SettingKey.RECEIPT_FOOTER.value] = "Chúc các em học tốt!"

    # WHEN: Triệu hồi nghiệp vụ đọc
    config = store_config_service.get_store_config()

    # THEN: Xác minh tính toàn vẹn của dữ liệu nạp lên DTO
    assert isinstance(config, StoreConfigDTO)
    assert config.name == "Văn phòng phẩm Tuổi Thơ"
    assert config.phone == "0987654321"
    assert config.address == "Số 45, Đường XYZ, Hà Nội"
    assert config.paper_size == "K58"
    assert config.footer == "Chúc các em học tốt!"


def test_save_store_config_should_mutate_db_with_exact_string_mappings_and_return_true(store_config_service, memory_db):
    """
    HẬU QUYẾT (Use Case 2): Thực hiện lưu thông số hiệu chỉnh thông tin cửa hàng thành công
    """
    # GIVEN: Chuẩn bị dữ liệu DTO sạch (đã qua xử lý cắt khoảng trắng từ Controller)
    valid_dto = StoreConfigDTO(
        name="Nhà Sách Trí Tuệ",
        phone="0243.123.456",
        address="Đường Láng, Đống Đa",
        paper_size="K80",
        footer="Hẹn gặp lại!"
    )

    # WHEN: Thực thi tác vụ ghi đè dữ liệu xuống hệ thống
    result = store_config_service.save_store_config(valid_dto)

    # THEN: Kiểm chứng đột biến trạng thái cơ sở dữ liệu (State Mutations) khớp 100%
    assert result is True
    assert memory_db[SettingKey.STORE_NAME.value] == "Nhà Sách Trí Tuệ"
    assert memory_db[SettingKey.STORE_PHONE.value] == "0243.123.456"
    assert memory_db[SettingKey.STORE_ADDRESS.value] == "Đường Láng, Đống Đa"
    assert memory_db[SettingKey.PRINT_PAPER_SIZE.value] == "K80"
    assert memory_db[SettingKey.RECEIPT_FOOTER.value] == "Hẹn gặp lại!"