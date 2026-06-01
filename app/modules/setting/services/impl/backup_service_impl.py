import os
import subprocess
import platform
from datetime import datetime

from app.modules.setting.services.backup_service import BackupService
from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO
from app.modules.setting.constants.setting_key import SettingKey

from app.core.config.settings import DB_CONFIG

DB_HOST = DB_CONFIG.get("host", "localhost")
DB_USER = DB_CONFIG.get("user", "root")
DB_PASS = DB_CONFIG.get("password", "")
DB_NAME = DB_CONFIG.get("database", "pos_vpp")




class BackupServiceImpl(BackupService):
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def get_backup_config(self) -> BackupConfigDTO:
        with self.uow_factory() as uow:
            settings = uow.setting_repo.get_all_settings()
            default_folder = os.path.join(os.path.expanduser("~"), "Documents", "POS_Backup")

            return BackupConfigDTO(
                auto_enabled=settings.get(SettingKey.BACKUP_AUTO_ENABLED.value, 'false').lower() == 'true',
                backup_time=settings.get(SettingKey.BACKUP_TIME.value, '22:00'),
                folder_path=settings.get(SettingKey.BACKUP_FOLDER_PATH.value, default_folder)
            )

    def save_backup_config(self, config: BackupConfigDTO) -> bool:
        with self.uow_factory() as uow:
            enabled_str = 'true' if config.auto_enabled else 'false'
            uow.setting_repo.update_setting(SettingKey.BACKUP_AUTO_ENABLED.value, enabled_str)
            uow.setting_repo.update_setting(SettingKey.BACKUP_TIME.value, config.backup_time)
            uow.setting_repo.update_setting(SettingKey.BACKUP_FOLDER_PATH.value, config.folder_path)

            status_text = "Bật" if config.auto_enabled else "Tắt"
            log_desc = f"Tự động: {status_text} | Giờ quét: {config.backup_time}"
            uow.activity_log_repo.add_log(action_type='SYSTEM', reference_code='BACKUP', description=log_desc)

            return True

    def execute_backup(self) -> str:
        config = self.get_backup_config()
        folder = config.folder_path

        if not os.path.exists(folder):
            os.makedirs(folder)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        file_name = f"pos_backup_{timestamp}.sql"
        dest_file_path = os.path.join(folder, file_name)

        command = f'mysqldump -h {DB_HOST} -u {DB_USER} -p{DB_PASS} {DB_NAME} > "{dest_file_path}"'

        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(command, shell=True, creationflags=creation_flags, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Lỗi thực thi mysqldump: {result.stderr}")

        with self.uow_factory() as uow:
            log_desc = f"Sao lưu dữ liệu thành công | Tệp: {file_name}"
            uow.activity_log_repo.add_log(action_type='SYSTEM', reference_code='BACKUP', description=log_desc)

        return dest_file_path

    def execute_restore(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            raise FileNotFoundError("Tập tin sao lưu phục hồi không tồn tại!")

        command = f'mysql -h {DB_HOST} -u {DB_USER} -p{DB_PASS} {DB_NAME} < "{file_path}"'

        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(command, shell=True, creationflags=creation_flags, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Lỗi thực thi khôi phục cơ sở dữ liệu: {result.stderr}")

        with self.uow_factory() as uow:
            base_name = os.path.basename(file_path)
            log_desc = f"Phục hồi dữ liệu thành công | Tệp: {base_name}"
            uow.activity_log_repo.add_log(action_type='SYSTEM', reference_code='RESTORE', description=log_desc)

        return True