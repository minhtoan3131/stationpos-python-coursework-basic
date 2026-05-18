from typing import Dict
from app.core.database.base_repository import BaseRepository
from app.modules.setting.repositories.setting_repository import SettingRepository


class SettingRepositoryImpl(BaseRepository, SettingRepository):

    def get_all_settings(self) -> Dict[str, str]:
        sql = "SELECT setting_key, setting_value FROM system_settings"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()

        # Đóng gói thành Dictionary để Controller dễ sử dụng
        # Ví dụ: settings['STORE_NAME']
        return {row['setting_key']: row['setting_value'] for row in rows}

    def update_setting(self, key: str, new_value: str) -> bool:
        sql = "UPDATE system_settings SET setting_value = %s WHERE setting_key = %s"
        self.cursor.execute(sql, (new_value, key))
        return self.cursor.rowcount > 0