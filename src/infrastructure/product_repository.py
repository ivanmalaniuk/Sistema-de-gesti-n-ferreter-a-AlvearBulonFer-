"""
CAPA DE INFRAESTRUCTURA — Repositorio de productos (SQLite).

Implementa IProductRepository. Convierte entre filas SQLite (con REAL
para precios) y objetos Product del dominio (con Decimal para precision).
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from src.domain.entities import Product
from src.domain.interfaces import IProductRepository
from src.infrastructure.database import get_connection


def _row_to_product(row) -> Product:
    """Convierte una fila SQLite en un objeto Product del dominio."""
    return Product(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        supplier=row["supplier"],
        list_date=date.fromisoformat(row["list_date"])
        if row["list_date"]
        else date.today(),
        supplier_price=Decimal(str(row["supplier_price"])),
        selling_price=Decimal(str(row["selling_price"])),
        unit_quantity=row["unit_quantity"],
        unit_price=Decimal(str(row["unit_price"])),
        price_usd=Decimal(str(row["price_usd"])),
        selling_price_usd=Decimal(str(row["selling_price_usd"])),
        code=row["code"] if row["code"] else '',
        created_at=datetime.fromisoformat(row["created_at"])
        if row["created_at"]
        else None,
    )


class SQLiteProductRepository(IProductRepository):
    """CRUD de productos sobre SQLite con busqueda por nombre."""

    def add(self, product: Product) -> Product:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO products
                (name, category, supplier, list_date, supplier_price, selling_price,
                 unit_quantity, unit_price, price_usd, selling_price_usd, code, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product.name,
                product.category,
                product.supplier,
                product.list_date.isoformat(),
                float(product.supplier_price),
                float(product.selling_price),
                product.unit_quantity,
                float(product.unit_price),
                float(product.price_usd),
                float(product.selling_price_usd),
                product.code,
                now,
            ),
        )
        conn.commit()
        product.id = cursor.lastrowid
        product.created_at = datetime.fromisoformat(now)
        conn.close()
        return product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        return _row_to_product(row) if row else None

    def get_all(self) -> List[Product]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [_row_to_product(row) for row in rows]

    def get_all_sorted(self) -> List[Product]:
        return self.get_all()

    def search_by_name(self, query: str, supplier: str = '', limit: int = 0) -> List[Product]:
        """Busqueda por palabras sueltas. Opcionalmente filtra por proveedor.
        Si limit > 0, acota los resultados (evita traer 30K filas para nada)."""
        words = query.strip().split()
        conn = get_connection()
        cursor = conn.cursor()
        conditions = []
        params = []
        if words:
            for word in words:
                conditions.append("(name LIKE ? OR category LIKE ? OR code LIKE ?)")
                params.extend([f"%{word}%"] * 3)
        if supplier:
            conditions.append("supplier = ?")
            params.append(supplier)
        if not conditions:
            sql = "SELECT * FROM products ORDER BY name"
        else:
            sql = f"SELECT * FROM products WHERE {' AND '.join(conditions)} ORDER BY name"
        if limit > 0:
            sql += f" LIMIT {limit}"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [_row_to_product(row) for row in rows]

    def get_suppliers(self) -> List[str]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT supplier FROM products WHERE supplier != '' ORDER BY supplier")
        rows = cursor.fetchall()
        conn.close()
        return [r["supplier"] for r in rows]

    def find_by_name_and_supplier(self, name: str, supplier: str) -> Optional[Product]:
        """Busca producto por nombre exacto + proveedor (case-insensitive)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE LOWER(name) = LOWER(?) AND LOWER(supplier) = LOWER(?)",
            (name, supplier),
        )
        row = cursor.fetchone()
        conn.close()
        return _row_to_product(row) if row else None

    def update(self, product: Product) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE products SET
                name=?, category=?, supplier=?, list_date=?,
                supplier_price=?, selling_price=?, unit_quantity=?,
                unit_price=?, price_usd=?, selling_price_usd=?, code=?
            WHERE id=?
            """,
            (
                product.name,
                product.category,
                product.supplier,
                product.list_date.isoformat(),
                float(product.supplier_price),
                float(product.selling_price),
                product.unit_quantity,
                float(product.unit_price),
                float(product.price_usd),
                float(product.selling_price_usd),
                product.code,
                product.id,
            ),
        )
        conn.commit()
        conn.close()

    def delete(self, product_id: int) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()

    def delete_by_supplier(self, supplier: str) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE supplier = ?", (supplier,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def delete_by_supplier_and_date(self, supplier: str, list_date: date) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM products WHERE supplier = ? AND list_date = ?",
            (supplier, list_date.isoformat()),
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
