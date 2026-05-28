from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

@dataclass
class TaxConfigDTO:
    """DTO lưu trữ cấu hình thuế của một năm cụ thể"""
    apply_year: int
    threshold_amount: Decimal
    vat_percent: Decimal
    pit_percent: Decimal
    pit_method: str = 'FLAT_RATE'  # 'FLAT_RATE' (Khoán) hoặc 'BOOKKEEPING' (Sổ sách)
    id: Optional[int] = None

@dataclass
class MonthlyRevenueDTO:
    """DTO lưu trữ doanh thu tổng hợp theo từng tháng"""
    month: int
    revenue: Decimal
    total_cost: Decimal = Decimal('0')  # Trường để lưu giá vốn hàng bán (COGS) của tháng

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

@dataclass
class TaxLedgerDTO:
    """DTO đại diện cho bản ghi Master Sổ cái lưu vết cả thông số cấu hình của năm đó"""
    id: Optional[int]
    apply_year: int
    total_revenue: Decimal
    total_cost: Decimal
    final_vat_amount: Decimal
    final_pit_amount: Decimal
    pit_method: str              # 'FLAT_RATE' hoặc 'BOOKKEEPING'
    status: str              # 'DRAFT' hoặc 'CLOSED'
    threshold_amount: Decimal
    vat_percent: Decimal
    pit_percent: Decimal
    finalized_at: Optional[datetime] = None

@dataclass
class TaxLedgerDetailDTO:
    """DTO đại diện cho chi tiết đóng băng của một tháng cụ thể trong quá khứ"""
    id: Optional[int]
    tax_ledger_id: int
    month: int
    revenue: Decimal
    cost: Decimal
    vat_amount: Decimal
    pit_amount: Decimal