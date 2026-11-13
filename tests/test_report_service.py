import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import create_autospec

from src.domain.entities import Sale, SaleItem, Product, Expense
from src.domain.interfaces import ISaleRepository, IExpenseRepository
from src.application.report_service import ReportService


def make_product(**kw):
    defaults = dict(
        name="X",
        category="T",
        supplier="P",
        list_date=date.today(),
        supplier_price=Decimal("10"),
        selling_price=Decimal("16"),
        unit_quantity=1,
        unit_price=Decimal("16"),
        price_usd=Decimal("10"),
        selling_price_usd=Decimal("16"),
    )
    defaults.update(kw)
    return Product(**defaults)


def make_sale(total: Decimal) -> Sale:
    p = make_product(selling_price=total, unit_price=total)
    item = SaleItem(product=p, quantity=1, unit_price=total)
    return Sale(items=[item])


def make_expense(amount: Decimal) -> Expense:
    return Expense(description="T", amount=amount, date=datetime.now(), category="T")


@pytest.fixture
def sale_repo():
    return create_autospec(ISaleRepository)


@pytest.fixture
def expense_repo():
    return create_autospec(IExpenseRepository)


@pytest.fixture
def report_service(sale_repo, expense_repo):
    return ReportService(sale_repo, expense_repo)


class TestMonthlyReport:
    def test_report_with_sales_and_expenses(
        self, report_service, sale_repo, expense_repo
    ):
        sale_repo.get_by_date_range.return_value = [
            make_sale(Decimal("10000")),
            make_sale(Decimal("5000")),
        ]
        expense_repo.get_by_date_range.return_value = [
            make_expense(Decimal("3000")),
            make_expense(Decimal("2000")),
        ]

        report = report_service.get_monthly_report(2026, 7)

        assert report.gross_revenue == Decimal("15000")
        assert report.total_expenses == Decimal("5000")
        assert report.net_profit == Decimal("10000")

    def test_report_with_no_data(self, report_service, sale_repo, expense_repo):
        sale_repo.get_by_date_range.return_value = []
        expense_repo.get_by_date_range.return_value = []

        report = report_service.get_monthly_report(2026, 7)

        assert report.net_profit == Decimal("0")

    def test_negative_net_profit(self, report_service, sale_repo, expense_repo):
        sale_repo.get_by_date_range.return_value = [make_sale(Decimal("1000"))]
        expense_repo.get_by_date_range.return_value = [make_expense(Decimal("3000"))]

        report = report_service.get_monthly_report(2026, 7)

        assert report.net_profit == Decimal("-2000")
