from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Any

class InvoiceHistoryRepository(ABC):
    @abstractmethod
    def fetch_invoices_master(self, keyword: str = None, date_from: date = None,
                              date_to: date = None, payment_method: str = None,
                              status: str = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def fetch_invoice_details(self, invoice_code: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def fetch_invoice_metadata(self, invoice_code: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_invoice_status(self, invoice_code: str, status: str, cancel_reason: str = None) -> bool:
        pass

    @abstractmethod
    def restore_inventory_stock(self, invoice_code: str) -> None:
        pass