from abc import ABC, abstractmethod
from typing import List

from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO
from app.modules.product.dtos.product_delete_dto import ProductDeleteDTO
from app.modules.product.dtos.product_filter_dto import ProductFilterDTO
from app.modules.product.dtos.product_list_dto import ProductListDTO
from app.modules.product.dtos.product_detail_dto import ProductDetailDTO

class ProductService(ABC):

    @abstractmethod
    def get_product_list(
            self
    ) -> List[ProductListDTO]:
        pass

    @abstractmethod
    def search_products(
            self,
            filter_dto: ProductFilterDTO
    ) -> List[ProductListDTO]:
        pass

    @abstractmethod
    def get_product_by_id(
            self,
            product_id: int
    ) -> ProductDetailDTO:
        pass

    @abstractmethod
    def create_product(
            self,
            dto: ProductCreateDTO
    ) -> int:
        pass

    @abstractmethod
    def update_product(
            self,
            dto: ProductUpdateDTO
    ) -> bool:
        pass

    @abstractmethod
    def delete_product(
            self,
            dto: ProductDeleteDTO
    ) -> bool:
        pass
