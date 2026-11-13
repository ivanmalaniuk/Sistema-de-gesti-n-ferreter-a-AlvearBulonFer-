from datetime import datetime, date
from typing import List, Optional

from src.domain.entities import UploadedList
from src.domain.interfaces import IUploadedListRepository
from src.infrastructure.database import get_connection


def _row_to_uploaded_list(row) -> UploadedList:
    return UploadedList(
        id=row["id"],
        filename=row["filename"],
        supplier=row["supplier"],
        list_date=date.fromisoformat(row["list_date"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class SQLiteUploadedListRepository(IUploadedListRepository):

    def add(self, uploaded_list: UploadedList) -> UploadedList:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO uploaded_lists (filename, supplier, list_date, created_at) VALUES (?, ?, ?, ?)",
            (uploaded_list.filename, uploaded_list.supplier, uploaded_list.list_date.isoformat(), now),
        )
        conn.commit()
        uploaded_list.id = cursor.lastrowid
        uploaded_list.created_at = datetime.fromisoformat(now)
        conn.close()
        return uploaded_list

    def get_all(self) -> List[UploadedList]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM uploaded_lists ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [_row_to_uploaded_list(row) for row in rows]

    def get_by_supplier_and_date(self, supplier: str, list_date: date) -> Optional[UploadedList]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM uploaded_lists WHERE supplier = ? AND list_date = ?",
            (supplier, list_date.isoformat()),
        )
        row = cursor.fetchone()
        conn.close()
        return _row_to_uploaded_list(row) if row else None

    def delete(self, list_id: int) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM uploaded_lists WHERE id = ?", (list_id,))
        conn.commit()
        conn.close()
