from typing import Dict

class PurchaseCartItem:
    """Đại diện cho 1 dòng sản phẩm trong giỏ hàng"""
    def __init__(self, product_id: int, qty: int, price: float):
        self.product_id = product_id
        self.qty = qty
        self.price = price

    @property
    def line_total(self) -> float:
        """
        Toán học 1 dòng: Số lượng x Đơn giá
        """
        return self.qty * self.price

class PurchaseCart:
    """Đại diện cho toàn bộ Giỏ hàng nhập kho"""
    def __init__(self):
        # Dùng Dictionary mapping product_id -> PurchaseCartItem để dễ cập nhật
        self.items: Dict[int, PurchaseCartItem] = {}

    def update_item(self, product_id: int, qty: int, price: float):
        """Thêm mới hoặc cập nhật số lượng/giá của 1 mặt hàng"""
        if product_id not in self.items:
            self.items[product_id] = PurchaseCartItem(product_id, qty, price)
        else:
            self.items[product_id].qty = qty
            self.items[product_id].price = price

    def remove_item(self, product_id: int):
        if product_id in self.items:
            del self.items[product_id]

    def clear(self):
        self.items.clear()

    @property
    def total_amount(self) -> float:
        """
        Toán học tổng: Cộng dồn tất cả các dòng
        """
        sub_total = sum(item.line_total for item in self.items.values())
        return sub_total