"""
Tests de SQLiteSaleRepository con base temporal (nunca la ferreteria.db real).
"""

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from src.domain.entities import Product, Sale, SaleItem
from src.infrastructure import sale_repository as modulo
from src.infrastructure.sale_repository import SQLiteSaleRepository


ESQUEMA = """
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    supplier TEXT NOT NULL DEFAULT '',
    list_date TEXT NOT NULL DEFAULT '',
    supplier_price REAL NOT NULL DEFAULT 0,
    selling_price REAL NOT NULL DEFAULT 0,
    unit_quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0,
    price_usd REAL NOT NULL DEFAULT 0,
    selling_price_usd REAL NOT NULL DEFAULT 0,
    code TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_amount REAL NOT NULL,
    created_at TEXT NOT NULL,
    customer TEXT NOT NULL DEFAULT ''
);
CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    cost_price REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


class ConexionEspia:
    """Delega todo salvo close(), para inspeccionar el estado despues del alta."""

    def __init__(self, real):
        self.real = real
        self.cerrada = False

    def cursor(self):
        return self.real.cursor()

    def commit(self):
        self.real.commit()

    def rollback(self):
        self.real.rollback()

    def close(self):
        self.cerrada = True
        # No cerrar la real: el test necesita leer su estado.


def make_product(pid):
    return Product(
        id=pid,
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


@pytest.fixture
def db(tmp_path):
    ruta = str(tmp_path / "ventas.db")
    conn = sqlite3.connect(ruta)
    conn.executescript(ESQUEMA)
    conn.execute(
        "INSERT INTO products (id, name, created_at) VALUES (1, 'Martillo', '2026-07-01')"
    )
    conn.commit()
    conn.close()
    return ruta


def conectar_espia(db, conexiones):
    real = sqlite3.connect(db)
    real.execute("PRAGMA foreign_keys=ON")
    espia = ConexionEspia(real)
    conexiones.append(espia)
    return espia


def test_venta_exitosa_guarda_cabecera_e_items(db, monkeypatch):
    conexiones = []
    monkeypatch.setattr(
        modulo, "get_connection", lambda: conectar_espia(db, conexiones)
    )
    repo = SQLiteSaleRepository(product_repo=None)

    item = SaleItem(
        product=make_product(1),
        quantity=Decimal("2"),
        unit_price=Decimal("160"),
    )

    resultado = repo.add(Sale(items=[item]))

    espia = conexiones[0]
    assert resultado.id == 1
    assert espia.cerrada is True
    assert espia.real.in_transaction is False
    assert espia.real.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 1
    assert espia.real.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 1


def test_fallo_en_item_hace_rollback(db, monkeypatch):
    conexiones = []
    monkeypatch.setattr(
        modulo, "get_connection", lambda: conectar_espia(db, conexiones)
    )
    repo = SQLiteSaleRepository(product_repo=None)

    items = [
        SaleItem(
            product=make_product(1),
            quantity=Decimal("1"),
            unit_price=Decimal("160"),
        ),
        SaleItem(
            product=make_product(999),  # no existe: viola la FK
            quantity=Decimal("1"),
            unit_price=Decimal("80"),
        ),
    ]

    with pytest.raises(sqlite3.IntegrityError):
        repo.add(Sale(items=items))

    espia = conexiones[0]
    assert espia.cerrada is True
    assert espia.real.in_transaction is False
    assert espia.real.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
    assert espia.real.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 0
