from datetime import date, timedelta
from typing import Tuple


class DateHelper:
    """Utility class chịu trách nhiệm tính toán khoảng thời gian (Date Math).
    Trả về định dạng chuẩn chuỗi 'yyyy-MM-dd' cho Database/Service.
    """

    @staticmethod
    def get_today_range() -> Tuple[str, str]:
        today_str = date.today().strftime("%Y-%m-%d")
        return today_str, today_str

    @staticmethod
    def get_yesterday_range() -> Tuple[str, str]:
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        return yesterday_str, yesterday_str

    @staticmethod
    def get_this_month_range() -> Tuple[str, str]:
        today = date.today()
        first_day = date(today.year, today.month, 1)
        return first_day.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")