class SystemSettingDTO:
    def __init__(self, key: str, value: str, description: str = ""):
        self.key = key
        self.value = value
        self.description = description