from app.core.database.base_repository import BaseRepository
from app.modules.sale.repositories.sale_repository import SaleRepository
from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from datetime import datetime
from typing import List

class SaleRepositoryImpl(BaseRepository, SaleRepository):
    def create_invoice(self, checkout_data: CheckoutDTO) -> int:
        sql = """
            INSERT INTO invoices (
                code, created_at, total_amount, discount, 
                final_amount, payment_method, cash_received, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'COMPLETED')
        """
        params = (
            checkout_data.code,
            datetime.now(),
            checkout_data.total_amount,
            checkout_data.discount,
            checkout_data.final_amount,
            checkout_data.payment_method,
            checkout_data.cash_received
        )
        self.cursor.execute(sql, params)
        return self.cursor.lastrowid

    def create_invoice_items(self, invoice_id: int, items: List[CartItemDTO]) -> None:
        sql = """
            INSERT INTO invoice_items (
                invoice_id, product_id, unit_id, cost_price,
                quantity, unit_price, total_price
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params_list = [
            (invoice_id, item.product_id, item.unit_id, item.cost_price,
             item.quantity, item.price, item.total)
            for item in items
        ]
        self.cursor.executemany(sql, params_list)


    def add_invoice_log(self, invoice_id: int, action: str, note: str) -> None:
        sql = """
            INSERT INTO invoice_logs (invoice_id, action, note, created_at)
            VALUES (%s, %s, %s, %s)
        """
        self.cursor.execute(sql, (invoice_id, action, note, datetime.now()))