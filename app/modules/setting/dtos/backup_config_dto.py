class BackupConfigDTO:
    def __init__(self, auto_enabled: bool = False, backup_time: str = "22:00", folder_path: str = ""):
        self.auto_enabled = auto_enabled
        self.backup_time = backup_time  # Định dạng chuỗi: "HH:mm"
        self.folder_path = folder_path