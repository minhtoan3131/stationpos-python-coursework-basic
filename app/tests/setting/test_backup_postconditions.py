import platform
from unittest.mock import MagicMock

import pytest
import os
import copy
import subprocess
from datetime import datetime
from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO
from app.modules.setting.services.impl.backup_service_impl import BackupServiceImpl
from app.modules.setting.constants.setting_key import SettingKey
from app.core.config.settings import DB_CONFIG


# ==============================================================================
# FAKE OBJECTS
# ==============================================================================

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
# PYTEST FIXTURES (Setup môi trường độc lập)
# ==============================================================================

@pytest.fixture
def memory_db():
    return {}


@pytest.fixture
def fake_uow_factory(memory_db):
    return lambda: FakeUnitOfWork(memory_db)


@pytest.fixture
def backup_service(fake_uow_factory):
    return BackupServiceImpl(uow_factory=fake_uow_factory)


# ==============================================================================
# POST-CONDITIONS TEST CASES (Kiểm thử đầu ra và đột biến trạng thái)
# ==============================================================================

# --- NHÓM 1: KIỂM SOÁT ĐỘT BIẾN TRẠNG THÁI DB (State Mutations) ---

def test_get_backup_config_should_populate_dto_correctly_when_db_has_data(backup_service, memory_db):
    """
    HẬU QUYẾT (Use Case 1): Đọc cấu hình khi DB đã có dữ liệu
    - Given: Database đã lưu sẵn thông số sao lưu cấu hình.
    - When: Hệ thống gọi hàm get_backup_config().
    - Then: Trả về DTO chứa dữ liệu chính xác tuyệt đối, bóc tách chuỗi phẳng thành đúng kiểu dữ liệu.
    """
    # GIVEN: Khởi tạo dữ liệu sẵn trong DB RAM
    memory_db[SettingKey.BACKUP_AUTO_ENABLED.value] = "true"
    memory_db[SettingKey.BACKUP_TIME.value] = "23:30"
    memory_db[SettingKey.BACKUP_FOLDER_PATH.value] = "/Users/minhtoan/OneDrive/Backup"

    # WHEN: Gọi cửa ngõ nghiệp vụ
    config = backup_service.get_backup_config()

    # THEN: Xác minh cấu trúc hậu quyết trả về
    assert isinstance(config, BackupConfigDTO)
    assert config.auto_enabled is True  # Chuỗi "true" phải biến đổi thành kiểu bool True
    assert config.backup_time == "23:30"
    assert config.folder_path == "/Users/minhtoan/OneDrive/Backup"


def test_save_backup_config_should_mutate_db_with_exact_string_mappings(backup_service, memory_db):
    """
    HẬU QUYẾT (Use Case 2): Lưu cấu hình xuống hệ thống
    - Given: Thu ngân truyền vào một đối tượng BackupConfigDTO hợp lệ.
    - When: Hệ thống thực thi save_backup_config().
    - Then: Hàm trả về True, dữ liệu phức tạp trong DTO phải được ánh xạ thành chuỗi phẳng chuẩn xác dưới DB.
    """
    # GIVEN: Tạo đối tượng DTO đầu vào
    dto = BackupConfigDTO(auto_enabled=True, backup_time="12:00", folder_path="/Backup_Drive")

    # WHEN: Thực thi lưu
    result = backup_service.save_backup_config(dto)

    # THEN: Xác minh kết quả trả về và đột biến trạng thái RAM DB
    assert result is True
    assert memory_db[
               SettingKey.BACKUP_AUTO_ENABLED.value] == "true"  # Kiểu bool True bắt buộc phải chuyển sang chuỗi "true"
    assert memory_db[SettingKey.BACKUP_TIME.value] == "12:00"
    assert memory_db[SettingKey.BACKUP_FOLDER_PATH.value] == "/Backup_Drive"


# --- NHÓM 2: KIỂM SOÁT THAM SỐ LỆNH HỆ THỐNG (Infrastructure Interaction) ---

def test_execute_backup_success_should_return_valid_path_and_invoke_mysqldump_with_env_config(backup_service, memory_db,
                                                                                              mocker):
    """
    HẬU QUYẾT (Use Case 3): Sao lưu thủ công thành công
    - Given: Thư mục lưu trữ đã tồn tại và hệ thống cấu hình sẵn. Khống chế mốc thời gian thực tại.
    - When: Thu ngân nhấn nút "Sao lưu ngay".
    - Then: Trả về đường dẫn chứa tên file chuẩn định dạng, đồng thời gọi câu lệnh mysqldump tàng hình ăn theo file .env.
    """
    # GIVEN: Thiết lập thư mục đích và giả lập nó đã tồn tại để vượt qua Pre-condition
    target_folder = "/Users/minhtoan/Documents/Backup"
    memory_db[SettingKey.BACKUP_FOLDER_PATH.value] = target_folder
    mocker.patch("os.path.exists", return_value=True)

    # ĐÓNG BĂNG THỜI GIAN: Giả lập đồng hồ hệ thống trả về chính xác một mốc giờ cố định để kiểm tra tên file
    fixed_now = datetime(2026, 5, 29, 23, 15, 0)
    mock_datetime = mocker.patch("app.modules.setting.services.impl.backup_service_impl.datetime")
    mock_datetime.now.return_value = fixed_now

    # MOCK SUBPROCESS: Đánh chặn lệnh CMD ngầm và cho kết quả trả về thành công (returncode = 0)
    mock_subprocess = mocker.patch("subprocess.run")
    mock_subprocess.return_value.returncode = 0

    # WHEN: Tiến hành bấm nút "Sao lưu ngay"
    file_path = backup_service.execute_backup()

    # THEN: Xác minh các điều kiện hậu quyết hạ tầng
    # 1. Đường dẫn file trả về phải khớp chính xác định dạng pos_backup_YYYYMMDD_HHMM.sql
    expected_file_name = "pos_backup_20260529_2315.sql"
    assert file_path == os.path.join(target_folder, expected_file_name)

    # 2. Bóc tách chuỗi câu lệnh gửi sang hệ điều hành xem có ăn theo cấu hình .env (DB_CONFIG) hay không
    expected_cmd = f'mysqldump -h {DB_CONFIG["host"]} -u {DB_CONFIG["user"]} -p{DB_CONFIG["password"]} {DB_CONFIG["database"]} > "{file_path}"'

    # Lấy các tham số thực tế mà hàm subprocess.run() đã nhận được khi chạy code
    called_args, called_kwargs = mock_subprocess.call_args

    assert called_args[0] == expected_cmd  # Câu lệnh SQL truyền vào bắt buộc phải đúng
    assert called_kwargs.get("shell") is True  # Phải kích hoạt môi trường shell

    # 3. TRẢI NGHIỆM TÀNG HÌNH: Đảm bảo nếu chạy trên môi trường Windows thì cờ ẩn cửa sổ CMD phải được đính kèm
    if platform.system() == "Windows":
        assert called_kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW


def test_execute_restore_success_should_return_true_and_invoke_mysql_client(backup_service, mocker):
    """
    HẬU QUYẾT (Use Case 4): Khôi phục dữ liệu thành công
    - Given: Tập tin phục hồi .sql có tồn tại thực tế trên ổ đĩa.
    - When: Tiến hành khôi phục.
    - Then: Trả về kết quả True và thực thi đúng cấu trúc câu lệnh nạp dòng vào mysql client.
    """
    # GIVEN: Vượt qua hàng rào Pre-condition kiểm tra file
    mocker.patch("os.path.exists", return_value=True)

    mock_subprocess = mocker.patch("subprocess.run")
    mock_subprocess.return_value.returncode = 0

    target_file = "/Users/minhtoan/Downloads/pos_backup_2026.sql"

    # WHEN: Gọi lệnh khôi phục
    result = backup_service.execute_restore(target_file)

    # THEN: Xác minh
    assert result is True

    # Kiểm tra tính chính xác của câu lệnh nạp dòng '<' phối hợp với thông số cấu hình .env
    expected_cmd = f'mysql -h {DB_CONFIG["host"]} -u {DB_CONFIG["user"]} -p{DB_CONFIG["password"]} {DB_CONFIG["database"]} < "{target_file}"'

    called_args, called_kwargs = mock_subprocess.call_args
    assert called_args[0] == expected_cmd
    assert called_kwargs.get("shell") is True