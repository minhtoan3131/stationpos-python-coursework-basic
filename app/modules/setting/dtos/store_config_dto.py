class StoreConfigDTO:
    def __init__(self, name: str = "", phone: str = "", address: str = "", paper_size: str = "K80", footer: str = ""):
        self.name = name
        self.phone = phone
        self.address = address
        self.paper_size = paper_size  # Giá trị lưu trữ: 'K80' hoặc 'K58'
        self.footer = footer