import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import create_autospec

from src.domain.entities import Product, Sale, SaleItem
from src.domain.interfaces import ISaleRepository, IProductRepository
from src.application.sale_service import SaleService


def make_product(**kw):
    defaults = dict(
        name="Martillo",
        category="Herramientas",
        supplier="Prov",
        list_date=date(2026, 7, 1),
        supplier_price=Decimal("100"),
        selling_price=Decimal("160"),
        unit_quantity=1,
        unit_price=Decimal("160"),
        price_usd=Decimal("100"),
        selling_price_usd=Decimal("160"),
    )
    defaults.update(kw)
    return Product(id=1, **defaults)


@pytest.fixture
def product_repo():
    return create_autospec(IProductRepository)


@pytest.fixture
def sale_repo():
    return create_autospec(ISaleRepository)


@pytest.fixture
def sale_service(sale_repo, product_repo):
    return SaleService(sale_repo, product_repo)


class TestRecordSale:
    def test_single_product(self, sale_service, sale_repo, product_repo):
        product_repo.get_by_id.return_value = make_product()
        sale_repo.add.side_effect = lambda s: Sale(
            id=1, items=s.items, created_at=s.created_at
        )

        result = sale_service.record_sale([(1, Decimal("2"))])

        assert len(result.items) == 1
        assert result.items[0].quantity == Decimal("2")
        assert result.items[0].unit_price == Decimal("160")
        assert result.total_amount == Decimal("320")

    def test_multiple_products(self, sale_service, sale_repo, product_repo):
        products = {
            1: make_product(
                name="M", selling_price=Decimal("200"), unit_price=Decimal("200")
            ),
            2: make_product(
                name="C", selling_price=Decimal("80"), unit_price=Decimal("80")
            ),
        }
        product_repo.get_by_id.side_effect = lambda pid: products.get(pid)
        sale_repo.add.side_effect = lambda s: Sale(
            id=1, items=s.items, created_at=s.created_at
        )

        result = sale_service.record_sale([(1, Decimal("2")), (2, Decimal("4"))])

        assert len(result.items) == 2
        assert result.total_amount == Decimal("720")

    def test_bulk_product_uses_unit_price(self, sale_service, sale_repo, product_repo):
        p = make_product(
            selling_price=Decimal("8000"),
            unit_quantity=100,
            unit_price=Decimal("80"),
        )
        product_repo.get_by_id.return_value = p
        sale_repo.add.side_effect = lambda s: Sale(
            id=1, items=s.items, created_at=s.created_at
        )

        result = sale_service.record_sale([(1, Decimal("5"))])

        assert result.items[0].unit_price == Decimal("80")
        assert result.total_amount == Decimal("400")

    def test_empty_items_raises_error(self, sale_service, sale_repo, product_repo):
        with pytest.raises(ValueError, match="al menos un producto"):
            sale_service.record_sale([])


class TestCalculateTotal:
    def test_calculate_total(self, sale_service, product_repo):
        products = {
            1: make_product(unit_price=Decimal("160")),
            2: make_product(name="C", unit_price=Decimal("80")),
        }
        product_repo.get_by_id.side_effect = lambda pid: products.get(pid)

        total = sale_service.calculate_total([(1, Decimal("2")), (2, Decimal("4"))])

        assert total == Decimal("640")
