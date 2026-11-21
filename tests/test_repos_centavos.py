"""
Tests del límite repositorio con dinero en centavos enteros (INTEGER).

Los repositorios escriben to_cents(...) y leen from_cents(...): el dominio
trabaja siempre con Decimal en pesos. Nunca toca la ferreteria.db real.
"""

import sqlite3
from datetime import date, datetime
from decimal import Decimal

from src.domain.entities import Expense, Product, Sale, SaleItem
from src.infrastructure import expense_repository as modulo_gastos
from src.infrastructure import product_repository as modulo_productos
from src.infrastructure import sale_repository as modulo_ventas
from src.infrastructure.cents import from_cents, to_cents
from src.infrastructure.expense_repository import SQLiteExpenseRepository
from src.infrastructure.product_repository import SQLiteProductRepository
from src.infrastructure.sale_repository import SQLiteSaleRepository

# Espejo del esquema de producción: columnas de dinero INTEGER (centavos).
ESQUEMA = """
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    supplier TEXT NOT NULL DEFAULT '',
    list_date TEXT NOT NULL DEFAULT '',
    supplier_price INTEGER NOT NULL DEFAULT 0,
    selling_price INTEGER NOT NULL DEFAULT 0,
    unit_quantity INTEGER NOT NULL DEFAULT 1,
    unit_price INTEGER NOT NULL DEFAULT 0,
    price_usd INTEGER NOT NULL DEFAULT 0,
    selling_price_usd INTEGER NOT NULL DEFAULT 0,
    code TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_amount INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    customer TEXT NOT NULL DEFAULT ''
);
CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit_price INTEGER NOT NULL,
    subtotal INTEGER NOT NULL,
    cost_price INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    amount INTEGER NOT NULL,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    supplier TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _crear_base(tmp_path):
    """Crea una base temporal y devuelve la ruta."""
    ruta = str(tmp_path / "centavos.db")
    conn = sqlite3.connect(ruta)
    conn.executescript(ESQUEMA)
    conn.commit()
    conn.close()
    return ruta


def _conexion(ruta):
    """Conexión con Row, igual que get_connection de producción."""
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    return conn


def _producto(precio=Decimal("12.345")):
    return Product(
        name="Tornillo",
        category="Fijaciones",
        supplier="Prov",
        list_date=date(2026, 7, 1),
        supplier_price=precio,
        selling_price=Decimal("10.10"),
        unit_quantity=1,
        unit_price=Decimal("5.05"),
        price_usd=Decimal("0.01"),
        selling_price_usd=Decimal("99.99"),
    )


def test_producto_roundtrip_centavos(tmp_path, monkeypatch):
    ruta = _crear_base(tmp_path)
    monkeypatch.setattr(modulo_productos, "get_connection", lambda: _conexion(ruta))
    repo = SQLiteProductRepository()

    producto = repo.add(_producto())

    # Escritura: centavos enteros, con HALF_UP en el medio centavo.
    crudo = _conexion(ruta)
    fila = crudo.execute(
        "SELECT supplier_price, selling_price, unit_price, price_usd, "
        "selling_price_usd FROM products WHERE id = ?",
        (producto.id,),
    ).fetchone()
    crudo.close()
    assert isinstance(fila["supplier_price"], int)
    assert fila["supplier_price"] == 1235  # 12.345 -> HALF_UP
    assert fila["selling_price"] == 1010
    assert fila["unit_price"] == 505
    assert fila["price_usd"] == 1
    assert fila["selling_price_usd"] == 9999

    # Lectura: Decimal en pesos.
    leido = repo.get_by_id(producto.id)
    assert leido.supplier_price == Decimal("12.35")
    assert leido.selling_price == Decimal("10.10")
    assert leido.unit_price == Decimal("5.05")
    assert leido.price_usd == Decimal("0.01")
    assert leido.selling_price_usd == Decimal("99.99")


def test_gasto_roundtrip_centavos(tmp_path, monkeypatch):
    ruta = _crear_base(tmp_path)
    monkeypatch.setattr(modulo_gastos, "get_connection", lambda: _conexion(ruta))
    repo = SQLiteExpenseRepository()

    gasto = Expense(
        description="Cemento",
        amount=Decimal("12.345"),
        date=datetime(2026, 7, 1, 10, 0),
        category="Insumos",
        supplier="FGP",
    )
    repo.add(gasto)

    crudo = _conexion(ruta)
    valor = crudo.execute("SELECT amount FROM expenses WHERE id = ?", (gasto.id,)).fetchone()[0]
    crudo.close()
    assert isinstance(valor, int)
    assert valor == 1235  # medio centavo -> HALF_UP

    leido = repo.get_by_id(gasto.id)
    assert leido.amount == Decimal("12.35")


def test_gasto_importe_exacto_se_conserva(tmp_path, monkeypatch):
    ruta = _crear_base(tmp_path)
    monkeypatch.setattr(modulo_gastos, "get_connection", lambda: _conexion(ruta))
    repo = SQLiteExpenseRepository()

    gasto = Expense(
        description="Alquiler",
        amount=Decimal("5000"),
        date=datetime(2026, 7, 1, 10, 0),
        category="Alquiler",
    )
    repo.add(gasto)

    leido = repo.get_by_id(gasto.id)
    assert leido.amount == Decimal("5000")
    assert to_cents(leido.amount) == 500000
    assert from_cents(to_cents(leido.amount)) == leido.amount


def test_venta_subtotal_fraccionario_consistente_en_centavos(tmp_path, monkeypatch):
    ruta = _crear_base(tmp_path)
    monkeypatch.setattr(modulo_productos, "get_connection", lambda: _conexion(ruta))
    monkeypatch.setattr(modulo_ventas, "get_connection", lambda: _conexion(ruta))
    producto = SQLiteProductRepository().add(_producto(Decimal("8.00")))

    item = SaleItem(
        product=producto,
        quantity=Decimal("0.333"),  # kg: no es dinero, sigue REAL
        unit_price=Decimal("10.10"),
        cost_price=Decimal("8.00"),
    )
    venta = Sale(items=[item])

    # Subtotal y total siempre en centavos exactos.
    assert item.subtotal == Decimal("3.36")  # 0.333 * 10.10 = 3.3633 -> 3.36
    assert to_cents(venta.total_amount) == 336

    SQLiteSaleRepository(product_repo=None).add(venta)

    crudo = _conexion(ruta)
    fila = crudo.execute(
        "SELECT total_amount FROM sales WHERE id = ?", (venta.id,)
    ).fetchone()
    item_crudo = crudo.execute(
        "SELECT quantity, unit_price, subtotal, cost_price FROM sale_items "
        "WHERE sale_id = ?",
        (venta.id,),
    ).fetchone()
    crudo.close()
    assert isinstance(fila["total_amount"], int)
    assert fila["total_amount"] == 336
    assert isinstance(item_crudo["unit_price"], int)
    assert item_crudo["unit_price"] == 1010
    assert item_crudo["subtotal"] == 336
    assert item_crudo["cost_price"] == 800
    assert item_crudo["quantity"] == 0.333  # quantity no es dinero

    leido = SQLiteSaleRepository(product_repo=None).get_by_id(venta.id)
    assert leido.total_amount == Decimal("3.36")
    assert leido.items[0].subtotal == Decimal("3.36")
    assert leido.items[0].unit_price == Decimal("10.10")
    assert leido.items[0].quantity == Decimal("0.333")
    # Consistencia: total en centavos = suma de subtotales en centavos.
    assert to_cents(leido.total_amount) == sum(
        to_cents(i.subtotal) for i in leido.items
    )
