from typing import Dict
from app.core.database.base_repository import BaseRepository
from app.modules.setting.repositories.setting_repository import SettingRepository


class SettingRepositoryImpl(BaseRepository, SettingRepository):

    def get_all_settings(self) -> Dict[str, str]:
        sql = "SELECT setting_key, setting_value FROM system_settings"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        return {row['setting_key']: row['setting_value'] for row in rows}

    def update_setting(self, key: str, new_value: str) -> bool:
        sql = """
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
        """
        self.cursor.execute(sql, (new_value if key == 'APP_PIN' else key,
                                  key if key == 'APP_PIN' else new_value))

        sql = """
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE setting_value = %s
        """
        self.cursor.execute(sql, (key, new_value, new_value))
        return self.cursor.rowcount > 0