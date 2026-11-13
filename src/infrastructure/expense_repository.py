"""
CAPA DE INFRAESTRUCTURA — Repositorio de gastos (SQLite).

Implementa IExpenseRepository. Los gastos son registros simples con
descripcion, monto, fecha y categoria.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from src.domain.entities import Expense
from src.domain.interfaces import IExpenseRepository
from src.infrastructure.database import get_connection


class SQLiteExpenseRepository(IExpenseRepository):
    """CRUD de gastos sobre SQLite con filtro por rango de fechas."""

    def add(self, expense: Expense) -> Expense:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO expenses (description, amount, date, category, supplier, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                expense.description,
                float(expense.amount),
                expense.date.isoformat(),
                expense.category,
                expense.supplier,
                now,
            ),
        )
        conn.commit()
        expense.id = cursor.lastrowid
        expense.created_at = datetime.fromisoformat(now)
        conn.close()
        return expense

    def get_by_id(self, expense_id: int) -> Optional[Expense]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return Expense(
            id=row["id"],
            description=row["description"],
            amount=Decimal(str(row["amount"])),
            date=datetime.fromisoformat(row["date"]),
            category=row["category"],
            supplier=row["supplier"] if row["supplier"] else '',
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_all(self) -> List[Expense]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
        rows = cursor.fetchall()
        conn.close()
        return [
            Expense(
                id=row["id"],
                description=row["description"],
                amount=Decimal(str(row["amount"])),
                date=datetime.fromisoformat(row["date"]),
                category=row["category"],
                supplier=row["supplier"] if row["supplier"] else '',
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_by_date_range(self, start: datetime, end: datetime) -> List[Expense]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM expenses WHERE date >= ? AND date < ? ORDER BY date",
            (start.isoformat(), end.isoformat()),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            Expense(
                id=row["id"],
                description=row["description"],
                amount=Decimal(str(row["amount"])),
                date=datetime.fromisoformat(row["date"]),
                category=row["category"],
                supplier=row["supplier"] if row["supplier"] else '',
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]
