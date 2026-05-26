from abc import ABC, abstractmethod
from typing import List, Dict, Any

class InvoiceHistoryService(ABC):
    @abstractmethod
    def search_invoices(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_invoice_full_details(self, invoice_code: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def execute_cancel_invoice(self, invoice_code: str, reason: str) -> bool:
        pass

    @abstractmethod
    def process_reprint_invoice(self, invoice_code: str) -> bool:
        pass

    @abstractmethod
    def export_invoice_to_excel(self, invoice_code: str) -> str:
        pass