from datetime import datetime
from typing import List

from src.domain.entities import MissingItem
from src.domain.interfaces import IMissingItemRepository


class MissingItemService:
    def __init__(self, repo: IMissingItemRepository):
        self._repo = repo

    def add_item(self, name: str, supplier: str = '', notes: str = '') -> MissingItem:
        if not name or not name.strip():
            raise ValueError("El nombre del articulo no puede estar vacio")
        item = MissingItem(name=name.strip(), supplier=supplier.strip(), notes=notes.strip())
        return self._repo.add(item)

    def get_all_items(self) -> List[MissingItem]:
        return self._repo.get_all()

    def delete_item(self, item_id: int) -> None:
        self._repo.delete(item_id)
