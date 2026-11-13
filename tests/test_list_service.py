import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import create_autospec

from src.domain.entities import Product
from src.domain.interfaces import IProductRepository
from src.application.list_service import ListService


@pytest.fixture
def product_repo():
    return create_autospec(IProductRepository)


@pytest.fixture
def list_service(product_repo):
    return ListService(product_repo)


def fake_product(**kw):
    """Helper para crear un producto con valores por defecto."""
    defaults = dict(
        id=1,
        name="P",
        category="C",
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
    return Product(**defaults)


class TestImportFromXLS:
    def test_import_valid_rows(self, list_service, product_repo):
        product_repo.add.side_effect = lambda p: fake_product(name=p.name)
        product_repo.find_by_name_and_supplier.return_value = None

        rows = [
            {"name": "Martillo", "category": "Herramientas", "supplier_price": "100"},
            {"name": "Clavos", "category": "Ferreteria", "supplier_price": "50"},
        ]
        result = list_service.import_from_xls_rows(
            rows,
            "ProveedorX",
            date(2026, 7, 1),
            Decimal("100"),
            Decimal("160"),
        )

        assert result["imported"] == 2
        assert result["updated"] == 0
        assert result["skipped"] == 0

    def test_skip_empty_name(self, list_service, product_repo):
        product_repo.find_by_name_and_supplier.return_value = None
        rows = [
            {"name": "", "category": "X", "supplier_price": "100"},
            {"name": "  ", "category": "X", "supplier_price": "100"},
        ]
        result = list_service.import_from_xls_rows(
            rows,
            "P",
            date.today(),
            Decimal("100"),
            Decimal("160"),
        )
        assert result["imported"] == 0

    def test_skip_invalid_price(self, list_service, product_repo):
        product_repo.find_by_name_and_supplier.return_value = None
        rows = [{"name": "Martillo", "category": "X", "supplier_price": "abc"}]
        result = list_service.import_from_xls_rows(
            rows,
            "P",
            date.today(),
            Decimal("100"),
            Decimal("160"),
        )
        assert result["imported"] == 0

    def test_price_calculation(self, list_service, product_repo):
        captured = []
        product_repo.add.side_effect = lambda p: fake_product(
            id=1, **{k: v for k, v in p.__dict__.items() if k != "id"}
        )
        product_repo.find_by_name_and_supplier.return_value = None

        list_service.import_from_xls_rows(
            [{"name": "P1", "category": "C", "supplier_price": "100"}],
            "Prov",
            date(2026, 7, 15),
            Decimal("200"),
            Decimal("160"),
        )

        call = product_repo.add.call_args[0][0]
        assert call.supplier == "Prov"
        assert call.list_date == date(2026, 7, 15)
        assert call.supplier_price == Decimal("100")
        assert call.selling_price == Decimal("160.00")
        assert call.price_usd == Decimal("0.50")
        assert call.selling_price_usd == Decimal("0.80")

    def test_update_when_new_list_is_newer(self, list_service, product_repo):
        """Si existe el mismo producto con fecha anterior, se actualiza."""
        existing = fake_product(
            list_date=date(2026, 6, 1), supplier_price=Decimal("50")
        )
        product_repo.find_by_name_and_supplier.return_value = existing

        result = list_service.import_from_xls_rows(
            [{"name": "P1", "category": "C", "supplier_price": "100"}],
            "Prov",
            date(2026, 7, 1),
            Decimal("100"),
            Decimal("160"),
        )

        assert result["imported"] == 0
        assert result["updated"] == 1
        assert result["skipped"] == 0
        product_repo.update.assert_called_once()
        updated = product_repo.update.call_args[0][0]
        assert updated.supplier_price == Decimal("100")

    def test_skip_when_existing_is_newer(self, list_service, product_repo):
        """Si existe el mismo producto con fecha mas reciente, se salta."""
        existing = fake_product(
            list_date=date(2026, 8, 1), supplier_price=Decimal("200")
        )
        product_repo.find_by_name_and_supplier.return_value = existing

        result = list_service.import_from_xls_rows(
            [{"name": "P1", "category": "C", "supplier_price": "100"}],
            "Prov",
            date(2026, 7, 1),
            Decimal("100"),
            Decimal("160"),
        )

        assert result["skipped"] == 1
        assert result["updated"] == 0
        product_repo.update.assert_not_called()

    def test_update_when_same_date(self, list_service, product_repo):
        """Si la fecha es igual, se actualiza (misma lista re-importada)."""
        existing = fake_product(
            list_date=date(2026, 7, 1), supplier_price=Decimal("50")
        )
        product_repo.find_by_name_and_supplier.return_value = existing

        result = list_service.import_from_xls_rows(
            [{"name": "P1", "category": "C", "supplier_price": "100"}],
            "Prov",
            date(2026, 7, 1),
            Decimal("100"),
            Decimal("160"),
        )

        assert result["updated"] == 1
