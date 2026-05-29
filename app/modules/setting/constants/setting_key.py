from enum import Enum

class SettingKey(str, Enum):
    """
    Quản lý tập trung toàn bộ Key cấu hình hệ thống.
    """
    # 1. Nhóm thông tin cửa hàng & In ấn hóa đơn
    STORE_NAME = 'STORE_NAME'
    STORE_PHONE = 'STORE_PHONE'
    STORE_ADDRESS = 'STORE_ADDRESS'
    PRINT_PAPER_SIZE = 'PRINT_PAPER_SIZE'
    RECEIPT_FOOTER = 'RECEIPT_FOOTER'

    # 2. Nhóm Bảo mật
    APP_PIN = 'APP_PIN'

    # 3. Nhóm Cấu hình sao lưu (Backup)
    BACKUP_AUTO_ENABLED = 'BACKUP_AUTO_ENABLED'
    BACKUP_TIME = 'BACKUP_TIME'
    BACKUP_FOLDER_PATH = 'BACKUP_FOLDER_PATH'

    # 4. Nhóm giới hạn Thuế (Đã khai báo sẵn trong schema.sql)
    TAX_MID_SCALE_LIMIT = 'TAX_MID_SCALE_LIMIT'
    TAX_LARGE_SCALE_LIMIT = 'TAX_LARGE_SCALE_LIMIT'