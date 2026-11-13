from datetime import datetime
from typing import List

from src.domain.entities import MissingItem
from src.domain.interfaces import IMissingItemRepository
from src.infrastructure.database import get_connection


class SQLiteMissingItemRepository(IMissingItemRepository):
    def add(self, item: MissingItem) -> MissingItem:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO missing_items (name, supplier, notes, created_at) VALUES (?, ?, ?, ?)",
            (item.name, item.supplier, item.notes, now),
        )
        conn.commit()
        item.id = cursor.lastrowid
        item.created_at = datetime.fromisoformat(now)
        conn.close()
        return item

    def get_all(self) -> List[MissingItem]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM missing_items ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [
            MissingItem(
                id=row["id"],
                name=row["name"],
                supplier=row["supplier"] if row["supplier"] else '',
                notes=row["notes"] if row["notes"] else '',
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def delete(self, item_id: int) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM missing_items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
