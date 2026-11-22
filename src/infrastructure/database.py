"""
CAPA DE INFRAESTRUCTURA — Conexion y esquema de la base de datos SQLite.

SQLite es una base de datos embebida (sin servidor) ideal para aplicaciones
de escritorio. Usamos WAL mode para mejor concurrencia y foreign keys para
integridad referencial.

El archivo ferreteria.db se crea automaticamente en la raiz del proyecto.
"""

import sqlite3
import os
import re
import sys

from src.infrastructure.backup import create_backup


def _dir_datos() -> str:
    """Carpeta de datos: junto al .exe si la app esta congelada, si no la raiz."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Ruta absoluta a la base de datos (en la raiz del proyecto o junto al .exe)
DB_DIR = _dir_datos()
DB_PATH = os.path.join(DB_DIR, "ferreteria.db")


def get_connection() -> sqlite3.Connection:
    """Retorna una conexion a SQLite con configuracion basica."""
    conn = sqlite3.connect(DB_PATH)

    # Las filas se comportan como diccionarios (acceso por nombre de columna)
    conn.row_factory = sqlite3.Row

    # WAL = Write-Ahead Logging: permite lecturas concurrentes sin bloqueo
    conn.execute("PRAGMA journal_mode=WAL")

    # Con WAL, NORMAL reduce escrituras al disco sin perder durabilidad
    conn.execute("PRAGMA synchronous=NORMAL")

    # Activa restricciones de clave foranea (ON DELETE CASCADE, etc.)
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


# Columnas de dinero que se guardan en centavos enteros (INTEGER)
_COLUMNAS_DINERO = {
    "products": (
        "supplier_price",
        "selling_price",
        "unit_price",
        "price_usd",
        "selling_price_usd",
    ),
    "sales": ("total_amount",),
    "sale_items": ("unit_price", "subtotal", "cost_price"),
    "expenses": ("amount",),
}

# Indices que un rebuild de tabla puede borrar; se recrean al terminar
_SQL_INDICES = (
    "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)",
    "CREATE INDEX IF NOT EXISTS idx_sales_created_at ON sales(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)",
    "CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier)",
    "CREATE INDEX IF NOT EXISTS idx_products_supplier_date ON products(supplier, list_date)",
)


def _tablas_con_dinero_real(cursor) -> list:
    """Tablas que todavia declaran alguna columna de dinero como REAL."""
    tablas = []
    for tabla, columnas in _COLUMNAS_DINERO.items():
        for fila in cursor.execute(f"PRAGMA table_info({tabla})"):
            if fila["name"] in columnas and (fila["type"] or "").upper() == "REAL":
                tablas.append(tabla)
                break
    return tablas


def _leer_config_backup(cursor) -> tuple:
    """Lee backup_dir y backup_keep de settings, con los mismos defaults."""
    valores = {}
    try:
        for fila in cursor.execute(
            "SELECT key, value FROM settings WHERE key IN ('backup_dir', 'backup_keep')"
        ):
            valores[fila["key"]] = fila["value"]
    except sqlite3.Error:
        pass

    backup_dir = valores.get("backup_dir") or "backups"
    try:
        keep_last = int(valores.get("backup_keep", "10"))
    except (TypeError, ValueError):
        keep_last = 10
    return backup_dir, keep_last


def _sql_tabla_en_centavos(conn, tabla: str) -> str:
    """
    Devuelve el CREATE TABLE de `tabla` con otro nombre y las columnas de
    dinero declaradas como INTEGER. Conserva el resto de la estructura.
    """
    fila = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
    ).fetchone()
    sql = fila[0]

    # Cambia el nombre de la tabla destino (evita crear la misma tabla)
    sql = re.sub(
        r"(?i)^(\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?)"
        + re.escape(tabla)
        + r"\b",
        r"\g<1>" + tabla + "_centavos",
        sql,
        count=1,
    )

    # Cambia el tipo declarado de las columnas de dinero
    for columna in _COLUMNAS_DINERO[tabla]:
        sql = re.sub(
            r"(?i)(\b" + re.escape(columna) + r"\b\s+)REAL\b",
            r"\g<1>INTEGER",
            sql,
        )
    return sql


def _reconstruir_tabla_en_centavos(conn, tabla: str) -> None:
    """Crea la tabla nueva con dinero INTEGER y copia los datos convertidos."""
    destino = f"{tabla}_centavos"
    columnas = [fila["name"] for fila in conn.execute(f"PRAGMA table_info({tabla})")]

    conn.execute(f"DROP TABLE IF EXISTS {destino}")
    conn.execute(_sql_tabla_en_centavos(conn, tabla))

    lista_columnas = ", ".join(columnas)
    lista_valores = ", ".join(
        f"CAST(ROUND({columna} * 100.0) AS INTEGER)"
        if columna in _COLUMNAS_DINERO[tabla]
        else columna
        for columna in columnas
    )
    conn.execute(
        f"INSERT INTO {destino} ({lista_columnas}) "
        f"SELECT {lista_valores} FROM {tabla}"
    )
    conn.execute(f"DROP TABLE {tabla}")
    conn.execute(f"ALTER TABLE {destino} RENAME TO {tabla}")


def _migrar_dinero_a_centavos(conn) -> None:
    """
    Convierte las columnas de dinero de REAL (pesos) a INTEGER (centavos).

    Es idempotente: solo actua si alguna columna sigue declarada REAL. Antes
    de tocar datos crea un backup; si el backup falla, la migracion se aborta
    y los datos originales quedan intactos. Las claves foraneas ya rotas antes
    de migrar se conservan; solo se aborta si aparece una violacion nueva.
    """
    cursor = conn.cursor()
    tablas = _tablas_con_dinero_real(cursor)
    if not tablas:
        return

    violaciones_antes = {
        tuple(fila) for fila in cursor.execute("PRAGMA foreign_key_check")
    }

    backup_dir, keep_last = _leer_config_backup(cursor)
    # Si el backup falla, la excepcion se propaga antes de modificar datos
    create_backup(DB_PATH, backup_dir, keep_last)

    # Las FK se desactivan fuera de la transaccion (dentro no tienen efecto)
    cursor.execute("PRAGMA foreign_keys=OFF")
    try:
        cursor.execute("BEGIN")
        for tabla in tablas:
            _reconstruir_tabla_en_centavos(conn, tabla)

        # El rebuild borra los indices de las tablas reconstruidas
        for sql in _SQL_INDICES:
            cursor.execute(sql)

        violaciones_despues = {
            tuple(fila) for fila in cursor.execute("PRAGMA foreign_key_check")
        }
        if violaciones_despues - violaciones_antes:
            raise sqlite3.IntegrityError(
                "La migracion a centavos dejaria claves foraneas invalidas"
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.execute("PRAGMA foreign_keys=ON")


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
            supplier_price INTEGER NOT NULL DEFAULT 0,
            selling_price INTEGER NOT NULL DEFAULT 0,
            unit_quantity INTEGER NOT NULL DEFAULT 1,
            unit_price INTEGER NOT NULL DEFAULT 0,
            price_usd INTEGER NOT NULL DEFAULT 0,
            selling_price_usd INTEGER NOT NULL DEFAULT 0,
            code TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        -- Cabecera de ventas
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Detalle/items de cada venta
        CREATE TABLE IF NOT EXISTS sale_items (
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
            amount INTEGER NOT NULL,
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

        -- Indices para busquedas y listados frecuentes
        CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
        CREATE INDEX IF NOT EXISTS idx_sales_created_at ON sales(created_at);
        CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id);
        CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);

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

    # Migracion final: dinero de REAL (pesos) a INTEGER (centavos)
    try:
        _migrar_dinero_a_centavos(conn)
    finally:
        conn.close()
