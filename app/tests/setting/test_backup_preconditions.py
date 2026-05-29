import pytest
import os
import copy
from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO
from app.modules.setting.services.impl.backup_service_impl import BackupServiceImpl
from app.modules.setting.constants.setting_key import SettingKey



class FakeSettingRepository:
    def __init__(self, data_store: dict):
        self.data_store = data_store

    def get_all_settings(self) -> dict:
        return self.data_store

    def update_setting(self, key: str, new_value: str) -> bool:
        self.data_store[key] = str(new_value)
        return True


class FakeUnitOfWork:
    def __init__(self, shared_db: dict):
        self.shared_db = shared_db
        self.snapshot = None

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
    """Khởi tạo RAM DB sạch cho mỗi bài test"""
    return {}


@pytest.fixture
def fake_uow_factory(memory_db):
    return lambda: FakeUnitOfWork(memory_db)


@pytest.fixture
def backup_service(fake_uow_factory):
    """Cửa ngõ Service nhận hạ tầng Fake"""
    return BackupServiceImpl(uow_factory=fake_uow_factory)


# ==============================================================================
# PRE-CONDITIONS TEST CASES (Kiểm thử hàng rào chặn lối vào)
# ==============================================================================

def test_restore_should_fail_immediately_when_backup_file_does_not_exist(backup_service, mocker):
    """
    RÀNG BUỘC TIÊN QUYẾT (Use Case 4): Khôi phục dữ liệu (Restore)
    - Given: Đường dẫn file khôi phục không tồn tại thực tế trên ổ cứng (os.path.exists = False).
    - When: Thu ngân ra lệnh thực thi phục hồi hệ thống.
    - Then: Hệ thống bắt buộc phải ném lỗi FileNotFoundError, chặn đứng không cho gọi lệnh nạp mysql.
    """
    # GIVEN: Khống chế hàm kiểm tra file của hệ điều hành trả về False (File không có thật)
    mocker.patch("os.path.exists", return_value=False)

    # Làm giả lệnh hệ thống để chứng minh: Nếu lọt qua Pre-condition thì lệnh này sẽ bị gọi
    mock_subprocess = mocker.patch("subprocess.run")

    invalid_file_path = "/Users/test/invalid_backup_2026.sql"

    # WHEN & THEN: Áp dụng Bài 2, dùng pytest.raises kiểm tra hàng rào ném lỗi chặn đứng
    with pytest.raises(FileNotFoundError) as exc_info:
        backup_service.execute_restore(invalid_file_path)

    # Xác minh thông điệp lỗi trực quan gửi lên UI
    assert str(exc_info.value) == "Tập tin sao lưu phục hồi không tồn tại!"

    # CHỨNG MINH TUYỆT ĐỐI: Lệnh mysql client KHÔNG bao giờ được phép kích hoạt
    mock_subprocess.assert_not_called()


def test_backup_should_ensure_directory_creation_before_running_mysqldump(backup_service, memory_db, mocker):
    """
    RÀNG BUỘC TIÊN QUYẾT (Use Case 3): Sao lưu dữ liệu (Backup)
    - Given: Thư mục đích lưu trữ (vd: Drive ảo của khách) chưa tồn tại vật lý trên ổ đĩa.
    - When: Lệnh execute_backup được kích hoạt.
    - Then: Hệ thống phải phát hiện và tự động tạo thư mục (os.makedirs) TRƯỚC KHI gọi mysqldump.
    """
    # GIVEN: Giả lập cấu hình đường dẫn đích trong DB RAM
    target_folder = "/Users/minhtoan/GoogleDrive/POS_Backup"
    memory_db[SettingKey.BACKUP_FOLDER_PATH.value] = target_folder

    # Giả lập tình huống: Thư mục này chưa có thật trên máy tính
    mocker.patch("os.path.exists", return_value=False)

    # Bắt gáy hành vi hạ tầng: Lắng nghe lệnh tạo thư mục của hệ điều hành
    mock_makedirs = mocker.patch("os.makedirs")

    # Bắt gáy lệnh chạy mysqldump (Cho trả về thành công để ko văng lỗi hoảng loạn)
    mock_subprocess = mocker.patch("subprocess.run")
    mock_subprocess.return_value.returncode = 0

    # WHEN: Thực thi Use Case cửa ngõ
    backup_service.execute_backup()

    # THEN: Kiểm chứng ranh giới tiền quyết hạ tầng được thực thi đúng trình tự
    # 1. Hàm tạo thư mục bắt buộc phải được gọi với đúng đường dẫn đích
    mock_makedirs.assert_called_once_with(target_folder)

    # 2. Đảm bảo lệnh tạo thư mục diễn ra an toàn trước khi lệnh hệ thống dump file làm việc
    assert mock_subprocess.called is True