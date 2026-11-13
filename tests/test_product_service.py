import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import create_autospec, Mock

from src.domain.entities import Product
from src.domain.interfaces import IProductRepository, ISettingsRepository
from src.application.product_service import ProductService


@pytest.fixture
def settings_repo():
    repo = create_autospec(ISettingsRepository)
    repo.get.side_effect = lambda k, d="": {
        "usd_rate": "1.0",
        "profit_margin": "160",
    }.get(k, d)
    return repo


@pytest.fixture
def product_repo():
    return create_autospec(IProductRepository)


@pytest.fixture
def product_service(product_repo, settings_repo):
    from src.application.settings_service import SettingsService

    ss = SettingsService(settings_repo)
    return ProductService(product_repo, ss)


def make_product(**kw):
    defaults = dict(
        name="Martillo",
        category="Herramientas",
        supplier="Proveedor X",
        list_date=date(2026, 7, 1),
        supplier_price=Decimal("100"),
        selling_price=Decimal("160"),
        unit_quantity=1,
        unit_price=Decimal("160"),
        price_usd=Decimal("100"),
        selling_price_usd=Decimal("160"),
    )
    defaults.update(kw)
    return Product(**defaults)


class TestCreateProduct:
    def test_create_valid_product(self, product_service, product_repo):
        product_repo.add.side_effect = lambda p: Product(
            id=1,
            name=p.name,
            category=p.category,
            supplier=p.supplier,
            list_date=p.list_date,
            supplier_price=p.supplier_price,
            selling_price=p.selling_price,
            unit_quantity=p.unit_quantity,
            unit_price=p.unit_price,
            price_usd=p.price_usd,
            selling_price_usd=p.selling_price_usd,
        )

        result = product_service.create_product(
            "Martillo",
            "Herramientas",
            "ProvA",
            date(2026, 7, 1),
            Decimal("100"),
            Decimal("160"),
            1,
            Decimal("160"),
            Decimal("100"),
            Decimal("160"),
        )

        assert result.name == "Martillo"
        assert result.supplier_price == Decimal("100")
        assert result.selling_price == Decimal("160")

    def test_empty_name_raises_error(self, product_service, product_repo):
        with pytest.raises(ValueError, match="vac"):
            product_service.create_product(
                "",
                "X",
                "P",
                date.today(),
                Decimal("10"),
                Decimal("16"),
                1,
                Decimal("16"),
                Decimal("10"),
                Decimal("16"),
            )

    def test_zero_supplier_price_raises_error(self, product_service, product_repo):
        with pytest.raises(ValueError, match="mayor a cero"):
            product_service.create_product(
                "P",
                "X",
                "P",
                date.today(),
                Decimal("0"),
                Decimal("16"),
                1,
                Decimal("16"),
                Decimal("0"),
                Decimal("0"),
            )


class TestSearch:
    def test_search_by_name(self, product_service, product_repo):
        product_repo.search_by_name.return_value = [make_product(name="Martillo")]
        results = product_service.search_products("mart")
        assert len(results) == 1
        assert results[0].name == "Martillo"

    def test_search_empty_returns_all(self, product_service, product_repo):
        product_repo.search_by_name.return_value = [
            make_product(name="A"),
            make_product(name="B"),
        ]
        results = product_service.search_products("")
        assert len(results) == 2


class TestRecalculate:
    def test_recalculate_from_supplier_price(
        self, product_service, product_repo, settings_repo
    ):
        p = make_product(supplier_price=Decimal("200"), selling_price=Decimal("999"))
        product_repo.get_by_id.return_value = p

        result = product_service.recalculate_from_supplier_price(p)

        assert result.selling_price == Decimal("320.00")
        assert result.price_usd == Decimal("200.00")
        assert result.selling_price_usd == Decimal("320.00")
