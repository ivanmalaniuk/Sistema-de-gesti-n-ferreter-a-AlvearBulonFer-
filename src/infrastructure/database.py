"""
CAPA DE INFRAESTRUCTURA — Conexion y esquema de la base de datos SQLite.

SQLite es una base de datos embebida (sin servidor) ideal para aplicaciones
de escritorio. Usamos WAL mode para mejor concurrencia y foreign keys para
integridad referencial.

El archivo ferreteria.db se crea automaticamente en la raiz del proyecto.
"""

import sqlite3
import os

# Ruta absoluta a la base de datos (en la raiz del proyecto)
DB_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(DB_DIR, "ferreteria.db")


def get_connection() -> sqlite3.Connection:
    """Retorna una conexion a SQLite con configuracion basica."""
    conn = sqlite3.connect(DB_PATH)

    # Las filas se comportan como diccionarios (acceso por nombre de columna)
    conn.row_factory = sqlite3.Row

    # WAL = Write-Ahead Logging: permite lecturas concurrentes sin bloqueo
    conn.execute("PRAGMA journal_mode=WAL")

    # Activa restricciones de clave foranea (ON DELETE CASCADE, etc.)
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


def init_db() -> None:
    """
    Crea las tablas si no existen e inserta valores por defecto.
    Es seguro ejecutar esto multiples veces (usa IF NOT EXISTS).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        -- Configuraciones globales (clave-valor)
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- Catalogo de productos
        CREATE TABLE IF NOT EXISTS products (
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

        -- Cabecera de ventas
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Detalle/items de cada venta
        CREATE TABLE IF NOT EXISTS sale_items (
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

        -- Articulos faltantes / a reponer
        CREATE TABLE IF NOT EXISTS missing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            supplier TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        -- Registro de gastos operativos
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Registro de listas de precios subidas
        CREATE TABLE IF NOT EXISTS uploaded_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            supplier TEXT NOT NULL,
            list_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Valores por defecto de configuracion
        INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_rate', '1500');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('profit_margin', '160');
    """)

    # Migraciones
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN code TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE sale_items ADD COLUMN cost_price REAL NOT NULL DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE sales ADD COLUMN customer TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN supplier TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier)")
    except Exception:
        pass
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_supplier_date ON products(supplier, list_date)")
    except Exception:
        pass
    try:
        cursor.execute("SELECT quantity FROM sale_items LIMIT 1")
        row = cursor.fetchone()
        if row is not None:
            if isinstance(row["quantity"], int):
                has_cost = False
                try:
                    cursor.execute("SELECT cost_price FROM sale_items LIMIT 1")
                    has_cost = True
                except Exception:
                    pass
                cursor.execute("ALTER TABLE sale_items RENAME TO sale_items_old")
                cursor.execute("""
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
                    )
                """)
                if has_cost:
                    cursor.execute("""
                        INSERT INTO sale_items
                            (id, sale_id, product_id, quantity, unit_price, subtotal, cost_price)
                        SELECT id, sale_id, product_id, quantity, unit_price, subtotal, cost_price
                        FROM sale_items_old
                    """)
                else:
                    cursor.execute("""
                        INSERT INTO sale_items
                            (id, sale_id, product_id, quantity, unit_price, subtotal)
                        SELECT id, sale_id, product_id, quantity, unit_price, subtotal
                        FROM sale_items_old
                    """)
                cursor.execute("DROP TABLE sale_items_old")
                conn.commit()
    except Exception:
        pass

    conn.commit()
    conn.close()
