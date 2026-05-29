import pytest
import copy
from app.modules.setting.services.impl.security_service_impl import SecurityServiceImpl
from app.modules.setting.constants.setting_key import SettingKey


# ==============================================================================
# FAKE OBJECTS (Hạ tầng RAM cô lập hoàn toàn Database phục vụ State-based Test)
# ==============================================================================

class FakeSettingRepository:
    """Fake Repository chạy hoàn toàn trên RAM giúp kiểm thử trạng thái siêu tốc"""

    def __init__(self, data_store: dict):
        self.data_store = data_store

    def get_all_settings(self) -> dict:
        return self.data_store

    def update_setting(self, key: str, new_value: str) -> bool:
        self.data_store[key] = str(new_value)
        return True


class FakeUnitOfWork:
    """Fake Unit of Work quản lý phiên giao dịch an toàn với cơ chế Snapshot Rollback trên RAM"""

    def __init__(self, shared_db: dict):
        self.shared_db = shared_db
        self._snapshot = None
        self.setting_repo = None

    def __enter__(self):
        # Chụp ảnh trạng thái dữ liệu (Snapshot) đề phòng Use Case xảy ra lỗi nghiệp vụ
        self._snapshot = copy.deepcopy(self.shared_db)
        self.setting_repo = FakeSettingRepository(self.shared_db)
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            # LÁ CHẮN BẤT BIẾN: Nếu Use Case văng lỗi -> Quay xe khôi phục ngay lập tức
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
    """Cấp phát phân mảnh giao dịch chia sẻ chung bộ nhớ memory_db"""
    return lambda: FakeUnitOfWork(memory_db)


@pytest.fixture
def security_service(fake_uow_factory):
    """Bơm hạ tầng Fake vào cửa ngõ Service cần kiểm thử"""
    return SecurityServiceImpl(uow_factory=fake_uow_factory)


# ==============================================================================
# PRE-CONDITIONS TEST CASES (Đồng bộ hóa 100% với Production Code)
# ==============================================================================

@pytest.mark.parametrize(
    "current_pin, new_pin, confirm_pin, expected_error_msg",
    [
        # --- TẦNG 1: XÁC THỰC MÃ PIN CŨ & CHẶN TRỐNG ---
        ("9999", "5678", "5678", "Mã PIN hiện tại không chính xác!"),  # Sai mã cũ hoàn toàn
        ("", "5678", "5678", "Vui lòng nhập đầy đủ tất cả các ô mã PIN!"),  # Mã cũ bỏ trống

        # --- TẦNG 2: ĐỊNH DẠNG MÃ PIN MỚI (CHẤP NHẬN TỪ 4 ĐẾN 6 CHỮ SỐ) ---
        ("1234", "abcd", "abcd", "Mã PIN mới phải có độ dài từ 4 đến 6 chữ số và chỉ chứa ký tự số!"),  # Chứa chữ
        ("1234", "567", "567", "Mã PIN mới phải có độ dài từ 4 đến 6 chữ số và chỉ chứa ký tự số!"),  # Ngắn quá (3 số)
        ("1234", "56 8", "56 8", "Mã PIN mới phải có độ dài từ 4 đến 6 chữ số và chỉ chứa ký tự số!"),
        # Chứa khoảng trắng
        ("1234", "", "", "Vui lòng nhập đầy đủ tất cả các ô mã PIN!"),  # Mã mới bỏ trống rỗng

        # --- TẦNG 3: KHỚP MÃ XÁC NHẬN ---
        ("1234", "5678", "9999", "Xác nhận mã PIN mới không khớp, vui lòng kiểm tra lại!"),  # Gõ lệch mã confirm
    ]
)
def test_change_pin_validation_layers_should_fail_immediately_and_prevent_db_mutation(
        current_pin, new_pin, confirm_pin, expected_error_msg, security_service, memory_db
):
    """
    RÀNG BUỘC TIÊN QUYẾT (Use Case 2): Thay đổi mã PIN bảo mật
    - Given: Cơ sở dữ liệu đang thiết lập mã PIN hiện tại là "1234".
    - When: Người dùng nhập dữ liệu Form vi phạm vào hàm change_pin().
    - Then: Hệ thống bắt buộc phải phát hiện, chặn đứng lối vào, ném lỗi ValueError,
            và đặc biệt trạng thái DB gốc không được phép bị thay đổi.
    """
    # GIVEN: Thiết lập mầm dữ liệu mã PIN gốc an toàn trong DB RAM là "1234"
    initial_pin = "1234"
    memory_db[SettingKey.APP_PIN.value] = initial_pin

    # WHEN & THEN: Kích hoạt rào chắn kiểm duyệt lỗi lối vào
    with pytest.raises(ValueError) as exc_info:
        security_service.change_pin(
            current_pin=current_pin,
            new_pin=new_pin,
            confirm_pin=confirm_pin
        )

    assert str(exc_info.value) == expected_error_msg
    assert memory_db[SettingKey.APP_PIN.value] == initial_pin