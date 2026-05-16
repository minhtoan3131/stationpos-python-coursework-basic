from decimal import Decimal
from typing import List, Dict, Any
from app.modules.report.dtos.report_dto import (
    DashboardReportDTO, KPIDTO, RevenueTrendItemDTO,
    TopProductDTO, TransactionHistoryDTO, InventoryReportDTO
)


class ReportMapper:
    """Utility class chịu trách nhiệm chuyển đổi dữ liệu thô từ DB sang DTO."""

    @staticmethod
    def map_kpi(raw_data: Dict[str, Any]) -> KPIDTO:
        if not raw_data:
            return KPIDTO(0, Decimal('0'), Decimal('0'), Decimal('0'))

        return KPIDTO(
            total_orders=int(raw_data.get("total_orders") or 0),
            total_revenue=Decimal(str(raw_data.get("total_revenue") or 0)),
            total_profit=Decimal(str(raw_data.get("total_profit") or 0)),
            total_stock_value=Decimal(str(raw_data.get("total_stock_value") or 0))
        )

    @staticmethod
    def map_revenue_trend(raw_list: List[Dict[str, Any]]) -> List[RevenueTrendItemDTO]:
        return [
            RevenueTrendItemDTO(
                date=item["date"],
                revenue=Decimal(str(item["revenue"] or 0))
            ) for item in raw_list
        ]

    @staticmethod
    def map_top_products(raw_list: List[Dict[str, Any]]) -> List[TopProductDTO]:
        return [
            TopProductDTO(
                product_name=item["product_name"],
                quantity=int(item["quantity"] or 0)
            ) for item in raw_list
        ]

    @staticmethod
    def map_transaction_history(raw_list: List[Dict[str, Any]]) -> List[TransactionHistoryDTO]:
        return [
            TransactionHistoryDTO(
                invoice_code=item["invoice_code"],
                created_at=item["created_at"],
                final_amount=Decimal(str(item["final_amount"] or 0)),
                payment_method=item["payment_method"]
            ) for item in raw_list
        ]

    @staticmethod
    def map_inventory_valuation(raw_list: List[Dict[str, Any]]) -> List[InventoryReportDTO]:
        return [
            InventoryReportDTO(
                product_name=item["product_name"],
                unit_name=item["unit_name"],
                stock_quantity=int(item["stock_quantity"] or 0),
                mac_price=Decimal(str(item["mac_price"] or 0)),
                total_inventory_value=Decimal(str(item["total_inventory_value"] or 0))
            ) for item in raw_list
        ]