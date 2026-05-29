import pytest
import copy
from app.modules.setting.services.impl.security_service_impl import SecurityServiceImpl
from app.modules.setting.constants.setting_key import SettingKey


# ==============================================================================
# FAKE OBJECTS (Hạ tầng RAM phục vụ State-based Testing độc lập)
# ==============================================================================

class FakeSettingRepository:
    """Fake Repository quản lý dữ liệu bảo mật phẳng trong bộ nhớ tạm RAM"""
    def __init__(self, data_store: dict):
        self.data_store = data_store

    def get_all_settings(self) -> dict:
        return self.data_store

    def update_setting(self, key: str, new_value: str) -> bool:
        self.data_store[key] = str(new_value)
        return True


class FakeUnitOfWork:
    """Fake Unit of Work giả lập cơ chế tự động Rollback giao dịch bằng deepcopy"""
    def __init__(self, shared_db: dict):
        self.shared_db = shared_db
        self._snapshot = None
        self.setting_repo = None

    def __enter__(self):
        self._snapshot = copy.deepcopy(self.shared_db)
        self.setting_repo = FakeSettingRepository(self.shared_db)
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            self.shared_db.clear()
            self.shared_db.update(self._snapshot)


# ==============================================================================
# PYTEST FIXTURES (Cấp phát môi trường sạch cô lập cho từng kịch bản)
# ==============================================================================

@pytest.fixture
def memory_db():
    """Khởi tạo một DB RAM sạch cho mỗi bài test"""
    return {}


@pytest.fixture
def fake_uow_factory(memory_db):
    return lambda: FakeUnitOfWork(memory_db)


@pytest.fixture
def security_service(fake_uow_factory):
    return SecurityServiceImpl(uow_factory=fake_uow_factory)


# ==============================================================================
# POST-CONDITIONS TEST CASES (Kiểm thử đầu ra và đột biến trạng thái)
# ==============================================================================

# --- ENVELOPE 1: USE CASE XÁC THỰC MÃ PIN (verify_app_pin) ---

def test_verify_app_pin_should_return_true_when_entered_pin_matches_db(security_service, memory_db):
    """
    HẬU QUYẾT (Use Case 1): Xác thực mã PIN trùng khớp
    - Given: Cơ sở dữ liệu đang lưu trữ mã PIN hoạt động là "5678".
    - When: Thu ngân nhập chính xác chuỗi "5678" tại màn hình khóa.
    - Then: Hệ thống bắt buộc phải phê duyệt và trả về True cho phép mở khóa màn hình.
    """
    # GIVEN: Cài cắm mã PIN mồi vào DB RAM
    memory_db[SettingKey.APP_PIN.value] = "5678"

    # WHEN: Gọi cửa ngõ dịch vụ kiểm tra
    result = security_service.verify_app_pin("5678")

    # THEN: Hợp đồng hậu quyết kết quả đầu ra bắt buộc phải đồng ý
    assert result is True


def test_verify_app_pin_should_return_false_when_entered_pin_mismatches_db(security_service, memory_db):
    """
    HẬU QUYẾT (Use Case 1): Xác thực mã PIN sai lệch
    - Given: Cơ sở dữ liệu đang cấu hình mã PIN bảo vệ là "5678".
    - When: Có người cố tình mò mã PIN bằng cách gõ "9999".
    - Then: Hệ thống phải từ chối ngay lập tức, trả về False để chặn đứng màn hình khóa lại.
    """
    # GIVEN: Mã PIN hợp pháp dưới DB đang là "5678"
    memory_db[SettingKey.APP_PIN.value] = "5678"

    # WHEN: Nhập thử mã PIN sai lệch
    result = security_service.verify_app_pin("9999")

    # THEN: Hậu quyết bảo mật bắt buộc phải chặn đứng (False)
    assert result is False


def test_verify_app_pin_should_fallback_to_default_1234_when_db_is_empty(security_service, memory_db):
    """
    HẬU QUYẾT (Use Case 1 - Kịch bản cài mới): DB trống chưa từng đổi mã PIN
    - Given: Cơ sở dữ liệu trống hoàn toàn (len = 0).
    - When: Thu ngân nhập mã PIN phổ thông mặc định "1234".
    - Then: Cơ chế Fallback an toàn tự động kích hoạt, bốc chuỗi "1234" ra so sánh và phê duyệt True.
    """
    # GIVEN: Khẳng định DB trống sạch
    assert len(memory_db) == 0

    # WHEN: Người dùng gõ mã PIN gốc hệ thống tự cấp
    result = security_service.verify_app_pin("1234")

    # THEN: Phải vượt qua bộ lọc thành công
    assert result is True


# --- ENVELOPE 2: USE CASE THAY ĐỔI MÃ PIN (change_pin) ---

def test_change_pin_successfully_with_4_digits_should_mutate_db_correctly(security_service, memory_db):
    """
    HẬU QUYẾT (Use Case 2): Thay đổi sang mã PIN mới gồm 4 số thành công
    - Given: Mã PIN hiện tại là "1234".
    - When: Thu ngân nhập đúng quy trình đổi sang mã mới "5678" và xác nhận lại "5678".
    - Then: Hàm trả về True, dữ liệu APP_PIN dưới DB RAM lập tức bị đột biến ghi đè thành "5678".
    """
    # GIVEN: Mã PIN nền ban đầu
    memory_db[SettingKey.APP_PIN.value] = "1234"

    # WHEN: Thực thi hành động đổi mã PIN hợp lệ
    result = security_service.change_pin(current_pin="1234", new_pin="5678", confirm_pin="5678")

    # THEN: Kiểm chứng đầu ra và đột biến trạng thái cơ sở dữ liệu (State Mutations)
    assert result is True
    assert memory_db[SettingKey.APP_PIN.value] == "5678"  # Đã ghi đè thành công khóa mới


def test_change_pin_successfully_with_5_digits_should_mutate_db_correctly(security_service, memory_db):
    """
    HẬU QUYẾT (Use Case 2): Thay đổi sang mã PIN mới gồm 5 số thành công
    - Giao kèo thực tế: Hệ thống của bạn chấp nhận độ dài linh hoạt từ 4 đến 6 chữ số.
    - Given: Mã PIN hiện tại là "1234".
    - When: Đổi sang mã mới gồm 5 chữ số "56789" (Hợp lệ theo luật hệ thống).
    - Then: Hàm trả về True, đột biến thành công mã mới dưới DB RAM.
    """
    # GIVEN: Mã PIN nền ban đầu
    memory_db[SettingKey.APP_PIN.value] = "1234"

    # WHEN: Thực thi đổi sang mã 5 chữ số
    result = security_service.change_pin(current_pin="1234", new_pin="56789", confirm_pin="56789")

    # THEN: Hệ thống phê duyệt xuất sắc
    assert result is True
    assert memory_db[SettingKey.APP_PIN.value] == "56789"