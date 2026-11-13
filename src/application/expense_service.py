"""
CAPA DE APLICACION — Servicio de gastos.

Registra gastos operativos con validacion de datos obligatorios.
Un gasto tiene: descripcion, monto, fecha y categoria.
"""

from datetime import datetime
from decimal import Decimal
from typing import List

from src.domain.entities import Expense
from src.domain.interfaces import IExpenseRepository


class ExpenseService:
    """Casos de uso del modulo de gastos."""

    def __init__(self, expense_repo: IExpenseRepository):
        self._expense_repo = expense_repo

    def record_expense(
        self, description: str, amount: Decimal, date: datetime, category: str,
        supplier: str = ''
    ) -> Expense:
        """Registra un gasto con validaciones de negocio."""
        if not description or not description.strip():
            raise ValueError("La descripcion del gasto no puede estar vacia")
        if amount <= 0:
            raise ValueError("El monto del gasto debe ser mayor a cero")
        if not category or not category.strip():
            raise ValueError("La categoria del gasto no puede estar vacia")

        expense = Expense(
            description=description.strip(),
            amount=amount,
            date=date,
            category=category.strip(),
            supplier=supplier.strip() if supplier else '',
        )
        return self._expense_repo.add(expense)

    def get_expenses_by_date_range(
        self, start: datetime, end: datetime
    ) -> List[Expense]:
        """Obtiene gastos en un rango de fechas."""
        return self._expense_repo.get_by_date_range(start, end)
