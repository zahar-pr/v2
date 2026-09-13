from abc import ABC, abstractmethod

from catalog import City


class SupplierSource(ABC):
    id: str
    title: str

    def ready(self) -> bool:
        return True

    @abstractmethod
    async def collect(self, session, city: City) -> list[dict]:
        pass
