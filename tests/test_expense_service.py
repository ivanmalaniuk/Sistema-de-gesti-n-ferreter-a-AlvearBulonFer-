import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import create_autospec

from src.domain.entities import Expense
from src.domain.interfaces import IExpenseRepository
from src.application.expense_service import ExpenseService


@pytest.fixture
def expense_repo():
    return create_autospec(IExpenseRepository)


@pytest.fixture
def expense_service(expense_repo):
    return ExpenseService(expense_repo)


class TestRecordExpense:
    def test_record_valid_expense(self, expense_service, expense_repo):
        expense_repo.add.side_effect = lambda e: Expense(
            id=1,
            description=e.description,
            amount=e.amount,
            date=e.date,
            category=e.category,
            supplier=e.supplier,
            created_at=e.created_at,
        )

        result = expense_service.record_expense(
            description="Compra de cemento",
            amount=Decimal("5000.00"),
            date=datetime(2026, 7, 1),
            category="Insumos",
        )

        assert result.description == "Compra de cemento"
        assert result.amount == Decimal("5000.00")

    def test_empty_description_raises_error(self, expense_service, expense_repo):
        with pytest.raises(ValueError, match="descripcion"):
            expense_service.record_expense("", Decimal("100"), datetime.now(), "T")

    def test_zero_amount_raises_error(self, expense_service, expense_repo):
        with pytest.raises(ValueError, match="monto"):
            expense_service.record_expense("T", Decimal("0"), datetime.now(), "T")
