from dataclasses import dataclass
from typing import Optional
from decimal import Decimal

@dataclass
class TaxConfigDTO:
    """DTO lưu trữ cấu hình thuế của một năm cụ thể"""
    apply_year: int
    threshold_amount: Decimal
    vat_percent: Decimal
    pit_percent: Decimal
    id: Optional[int] = None

@dataclass
class MonthlyRevenueDTO:
    """DTO lưu trữ doanh thu tổng hợp theo từng tháng"""
    month: int
    revenue: Decimal

@dataclass
class MonthlyTaxDetailDTO:
    """DTO chứa kết quả tính thuế chi tiết của từng tháng"""
    month: int
    revenue: Decimal
    vat_amount: Decimal
    pit_amount: Decimal
    total_tax: Decimal

@dataclass
class YearlyTaxReportDTO:
    """DTO chứa báo cáo tổng quan thuế của cả năm để Controller hiển thị"""
    year: int
    total_revenue: Decimal
    is_over_threshold: bool
    total_tax_amount: Decimal
    monthly_details: list[MonthlyTaxDetailDTO]