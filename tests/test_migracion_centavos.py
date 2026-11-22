"""
Tests de la migracion de dinero de REAL (pesos) a INTEGER (centavos).

Se usa siempre una base temporal (tmp_path); nunca la ferreteria.db real.
"""

import sqlite3

import pytest

from src.infrastructure import database


# Esquema viejo: el dinero se guardaba como REAL en pesos.
_ESQUEMA_VIEJO = """
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
    created_at TEXT NOT NULL
);

CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_amount REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# sale_items con el dinero en REAL (esquema previo a esta migracion).
_SALE_ITEMS_VIEJO = """
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

# sale_items mas antiguo: quantity INTEGER y sin cost_price.
_SALE_ITEMS_ANTIGUO = """
CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


def _conectar(ruta):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    return conn


def _tipos(conn, tabla):
    """Mapa columna -> tipo declarado (en mayusculas) via PRAGMA table_info."""
    return {
        fila["name"]: (fila["type"] or "").upper()
        for fila in conn.execute(f"PRAGMA table_info({tabla})")
    }


def _crear_base_vieja(ruta, sale_items_sql=_SALE_ITEMS_VIEJO, con_costo=True):
    """Crea una base con el esquema viejo (dinero REAL) y una fila por tabla."""
    conn = sqlite3.connect(ruta)
    conn.executescript(_ESQUEMA_VIEJO + sale_items_sql)

    conn.execute(
        """INSERT INTO products
               (id, name, category, supplier, list_date, supplier_price,
                selling_price, unit_quantity, unit_price, price_usd,
                selling_price_usd, created_at)
           VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Martillo",
            "Herramientas",
            "Proveedor",
            "2026-01-01",
            0.1 + 0.2,
            12.345,
            6,
            1234.5670000000001,
            1.0,
            2.5,
            "2026-01-01T10:00:00",
        ),
    )
    conn.execute(
        "INSERT INTO sales (id, total_amount, created_at) VALUES (1, ?, ?)",
        (12.345, "2026-01-01T10:05:00"),
    )
    if con_costo:
        conn.execute(
            """INSERT INTO sale_items
                   (id, sale_id, product_id, quantity, unit_price, subtotal, cost_price)
               VALUES (1, 1, 1, ?, ?, ?, ?)""",
            (2.0, 0.1 + 0.2, 12.345, 1234.5670000000001),
        )
    else:
        conn.execute(
            """INSERT INTO sale_items
                   (id, sale_id, product_id, quantity, unit_price, subtotal)
               VALUES (1, 1, 1, ?, ?, ?)""",
            (3, 1.5, 4.5),
        )
    conn.execute(
        """INSERT INTO expenses
               (id, description, amount, date, category, created_at)
           VALUES (1, ?, ?, ?, ?, ?)""",
        ("Insumos", 0.1 + 0.2, "2026-01-02", "Insumos", "2026-01-02T09:00:00"),
    )
    conn.commit()
    conn.close()


def test_migra_datos_reales_a_centavos(tmp_path, monkeypatch):
    ruta = str(tmp_path / "vieja.db")
    _crear_base_vieja(ruta)
    monkeypatch.setattr(database, "DB_PATH", ruta)

    database.init_db()

    conn = _conectar(ruta)
    try:
        # Las columnas de dinero quedan declaradas como INTEGER
        assert _tipos(conn, "products")["supplier_price"] == "INTEGER"
        assert _tipos(conn, "products")["selling_price"] == "INTEGER"
        assert _tipos(conn, "products")["unit_price"] == "INTEGER"
        assert _tipos(conn, "products")["price_usd"] == "INTEGER"
        assert _tipos(conn, "products")["selling_price_usd"] == "INTEGER"
        assert _tipos(conn, "sales")["total_amount"] == "INTEGER"
        assert _tipos(conn, "sale_items")["unit_price"] == "INTEGER"
        assert _tipos(conn, "sale_items")["subtotal"] == "INTEGER"
        assert _tipos(conn, "sale_items")["cost_price"] == "INTEGER"
        assert _tipos(conn, "expenses")["amount"] == "INTEGER"

        # Valores convertidos a centavos exactos
        p = conn.execute("SELECT * FROM products WHERE id = 1").fetchone()
        assert p["id"] == 1
        assert p["supplier_price"] == 30 and isinstance(p["supplier_price"], int)
        assert p["selling_price"] == 1235 and isinstance(p["selling_price"], int)
        assert p["unit_price"] == 123457 and isinstance(p["unit_price"], int)
        assert p["price_usd"] == 100
        assert p["selling_price_usd"] == 250

        # Columnas que no son dinero quedan intactas
        assert p["name"] == "Martillo"
        assert p["category"] == "Herramientas"
        assert p["supplier"] == "Proveedor"
        assert p["list_date"] == "2026-01-01"
        assert p["unit_quantity"] == 6
        assert p["created_at"] == "2026-01-01T10:00:00"

        s = conn.execute("SELECT * FROM sales WHERE id = 1").fetchone()
        assert s["id"] == 1
        assert s["total_amount"] == 1235
        assert s["created_at"] == "2026-01-01T10:05:00"

        item = conn.execute("SELECT * FROM sale_items WHERE id = 1").fetchone()
        assert item["id"] == 1
        assert item["sale_id"] == 1
        assert item["product_id"] == 1
        assert item["quantity"] == 2.0
        assert item["unit_price"] == 30
        assert item["subtotal"] == 1235
        assert item["cost_price"] == 123457

        e = conn.execute("SELECT * FROM expenses WHERE id = 1").fetchone()
        assert e["id"] == 1
        assert e["amount"] == 30
        assert e["description"] == "Insumos"
        assert e["date"] == "2026-01-02"
        assert e["category"] == "Insumos"

        # Las claves foraneas de sale_items se conservan
        refs = {
            fila["table"]
            for fila in conn.execute("PRAGMA foreign_key_list(sale_items)")
        }
        assert refs == {"sales", "products"}

        # Los indices borrados por el rebuild se recrean
        indices = {
            fila[0]
            for fila in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }
        assert {
            "idx_products_name",
            "idx_products_supplier",
            "idx_products_supplier_date",
            "idx_sales_created_at",
            "idx_sale_items_sale_id",
            "idx_expenses_date",
        } <= indices
    finally:
        conn.close()


def test_crea_backup_antes_de_migrar(tmp_path, monkeypatch):
    ruta = str(tmp_path / "vieja.db")
    _crear_base_vieja(ruta)
    monkeypatch.setattr(database, "DB_PATH", ruta)

    database.init_db()

    # El backup por defecto va a la carpeta "backups" junto a la base
    archivos = list((tmp_path / "backups").glob("ferreteria_*.db"))
    assert len(archivos) == 1

    # El backup conserva el estado PRE-migracion: dinero todavia en REAL
    conn = _conectar(str(archivos[0]))
    try:
        assert _tipos(conn, "products")["supplier_price"] == "REAL"
        p = conn.execute(
            "SELECT supplier_price FROM products WHERE id = 1"
        ).fetchone()
        assert isinstance(p["supplier_price"], float)
        assert p["supplier_price"] == pytest.approx(0.1 + 0.2)

        item = conn.execute(
            "SELECT unit_price FROM sale_items WHERE id = 1"
        ).fetchone()
        assert item["unit_price"] == pytest.approx(0.1 + 0.2)
    finally:
        conn.close()


def test_migracion_es_idempotente(tmp_path, monkeypatch):
    ruta = str(tmp_path / "vieja.db")
    _crear_base_vieja(ruta)
    monkeypatch.setattr(database, "DB_PATH", ruta)

    database.init_db()
    conn = _conectar(ruta)
    antes = tuple(
        conn.execute(
            "SELECT supplier_price, selling_price, unit_price FROM products WHERE id = 1"
        ).fetchone()
    )
    conn.close()

    # Segunda ejecucion: no debe volver a convertir ni crear otro backup
    database.init_db()

    conn = _conectar(ruta)
    try:
        despues = tuple(
            conn.execute(
                "SELECT supplier_price, selling_price, unit_price FROM products WHERE id = 1"
            ).fetchone()
        )
        total = conn.execute(
            "SELECT total_amount FROM sales WHERE id = 1"
        ).fetchone()["total_amount"]
    finally:
        conn.close()

    assert antes == (30, 1235, 123457)
    assert despues == antes
    assert total == 1235
    assert len(list((tmp_path / "backups").glob("ferreteria_*.db"))) == 1


def test_si_falla_el_backup_aborta_la_migracion(tmp_path, monkeypatch):
    ruta = str(tmp_path / "vieja.db")
    _crear_base_vieja(ruta)
    monkeypatch.setattr(database, "DB_PATH", ruta)

    def _backup_roto(*args, **kwargs):
        raise RuntimeError("backup roto")

    monkeypatch.setattr(database, "create_backup", _backup_roto)

    with pytest.raises(RuntimeError, match="backup roto"):
        database.init_db()

    # Los datos originales siguen intactos y en REAL
    conn = _conectar(ruta)
    try:
        assert _tipos(conn, "products")["supplier_price"] == "REAL"
        p = conn.execute(
            "SELECT supplier_price FROM products WHERE id = 1"
        ).fetchone()
        assert p["supplier_price"] == pytest.approx(0.1 + 0.2)
    finally:
        conn.close()


def test_base_nueva_crea_columnas_integer_sin_backup(tmp_path, monkeypatch):
    ruta = str(tmp_path / "nueva.db")
    monkeypatch.setattr(database, "DB_PATH", ruta)

    database.init_db()

    conn = _conectar(ruta)
    try:
        assert _tipos(conn, "products")["supplier_price"] == "INTEGER"
        assert _tipos(conn, "sales")["total_amount"] == "INTEGER"
        assert _tipos(conn, "sale_items")["subtotal"] == "INTEGER"
        assert _tipos(conn, "sale_items")["cost_price"] == "INTEGER"
        assert _tipos(conn, "expenses")["amount"] == "INTEGER"
        # quantity y las configuraciones de texto no cambian
        assert _tipos(conn, "sale_items")["quantity"] == "REAL"
        assert _tipos(conn, "settings")["value"] == "TEXT"
    finally:
        conn.close()

    # Sin migracion no se crea backup
    assert not (tmp_path / "backups").exists()


def test_ruta_legado_reconstruye_sale_items(tmp_path, monkeypatch):
    ruta = str(tmp_path / "antigua.db")
    _crear_base_vieja(ruta, sale_items_sql=_SALE_ITEMS_ANTIGUO, con_costo=False)
    monkeypatch.setattr(database, "DB_PATH", ruta)

    database.init_db()

    conn = _conectar(ruta)
    try:
        tipos = _tipos(conn, "sale_items")
        assert tipos["quantity"] == "REAL"
        assert "cost_price" in tipos
        assert tipos["cost_price"] == "INTEGER"
        assert tipos["unit_price"] == "INTEGER"
        assert tipos["subtotal"] == "INTEGER"

        item = conn.execute("SELECT * FROM sale_items WHERE id = 1").fetchone()
        assert item["quantity"] == 3.0
        assert item["unit_price"] == 150
        assert item["subtotal"] == 450
        assert item["cost_price"] == 0

        assert _tipos(conn, "products")["supplier_price"] == "INTEGER"
        assert _tipos(conn, "sales")["total_amount"] == "INTEGER"
        assert _tipos(conn, "expenses")["amount"] == "INTEGER"
    finally:
        conn.close()


def test_huerfanas_preexistentes_no_bloquean_la_migracion(tmp_path, monkeypatch):
    ruta = str(tmp_path / "huerfanas.db")
    _crear_base_vieja(ruta)

    # Fila heredada que apunta a un producto borrado con FK desactivadas.
    conn = sqlite3.connect(ruta)
    conn.execute(
        """INSERT INTO sale_items
               (id, sale_id, product_id, quantity, unit_price, subtotal, cost_price)
           VALUES (2, 1, 999, 1, 1.5, 1.5, 0)"""
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(database, "DB_PATH", ruta)

    database.init_db()

    conn = _conectar(ruta)
    try:
        assert _tipos(conn, "products")["supplier_price"] == "INTEGER"
        assert _tipos(conn, "sale_items")["unit_price"] == "INTEGER"
        item = conn.execute(
            "SELECT product_id, unit_price FROM sale_items WHERE id = 2"
        ).fetchone()
        assert item["product_id"] == 999
        assert item["unit_price"] == 150
        # La violacion vieja se conserva; la migracion no agrega ninguna.
        assert len(list(conn.execute("PRAGMA foreign_key_check"))) == 1
    finally:
        conn.close()
