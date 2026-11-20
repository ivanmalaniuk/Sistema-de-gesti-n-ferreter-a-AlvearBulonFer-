"""
Tests de la configuracion de SQLite: indices y PRAGMA.
Se usa siempre una base temporal (tmp_path); nunca la ferreteria.db real.
"""

import sqlite3

from src.infrastructure import database


def test_indices_de_busqueda_creados(tmp_path, monkeypatch):
    ruta = str(tmp_path / "indices.db")
    monkeypatch.setattr(database, "DB_PATH", ruta)

    database.init_db()

    conn = sqlite3.connect(ruta)
    indices = {fila[0] for fila in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'"
    )}
    conn.close()

    assert {
        "idx_products_name",
        "idx_sales_created_at",
        "idx_sale_items_sale_id",
        "idx_expenses_date",
    } <= indices


def test_synchronous_normal_con_wal(tmp_path, monkeypatch):
    ruta = str(tmp_path / "pragma.db")
    monkeypatch.setattr(database, "DB_PATH", ruta)

    conn = database.get_connection()
    journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
    synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
    conn.close()

    assert journal == "wal"
    assert synchronous == 1  # NORMAL
