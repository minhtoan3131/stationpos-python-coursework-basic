import datetime
import random

class InvoiceCodeGenerator:
    @staticmethod
    def generate() -> str:
        """
        Tạo mã hóa đơn theo định dạng: HD-YYYYMMDD-HHMMSS-RND
        Ví dụ: HD-20231027-143045-812
        """
        now = datetime.datetime.now()
        timestamp = now.strftime('%Y%m%d-%H%M%S')
        random_suffix = random.randint(100, 999)
        return f"HD-{timestamp}-{random_suffix}"