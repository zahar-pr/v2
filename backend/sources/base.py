from abc import ABC, abstractmethod

from catalog import Category
from domain import Supplier


class SupplierSource(ABC):
    id: str
    title: str

    @abstractmethod
    async def search(self, category: Category, place: str) -> list[Supplier]:
        pass
