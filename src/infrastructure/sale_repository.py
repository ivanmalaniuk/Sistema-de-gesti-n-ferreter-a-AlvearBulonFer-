from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from src.domain.entities import Product, Sale, SaleItem
from src.domain.interfaces import ISaleRepository, IProductRepository
from src.infrastructure.database import get_connection


class SQLiteSaleRepository(ISaleRepository):
    """CRUD de ventas con sus items asociados."""

    def __init__(self, product_repo: IProductRepository):
        self._product_repo = product_repo

    def add(self, sale: Sale) -> Sale:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            "INSERT INTO sales (total_amount, created_at, customer) VALUES (?, ?, ?)",
            (float(sale.total_amount), now, sale.customer),
        )
        sale_id = cursor.lastrowid

        for item in sale.items:
            cursor.execute(
                """
                INSERT INTO sale_items
                    (sale_id, product_id, quantity, unit_price, subtotal, cost_price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    item.product.id,
                    float(item.quantity),
                    float(item.unit_price),
                    float(item.subtotal),
                    float(item.cost_price),
                ),
            )

        conn.commit()
        conn.close()
        sale.id = sale_id
        sale.created_at = datetime.fromisoformat(now)
        return sale

    def get_by_id(self, sale_id: int) -> Optional[Sale]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
        sale_row = cursor.fetchone()
        if sale_row is None:
            conn.close()
            return None

        item_rows = self._fetch_items(cursor, [sale_id])
        conn.close()

        items = self._build_items(item_rows, sale_id)
        return Sale(
            id=sale_row["id"],
            items=items,
            customer=sale_row["customer"] if sale_row["customer"] else '',
            created_at=datetime.fromisoformat(sale_row["created_at"]),
        )

    def _fetch_items(self, cursor, sale_ids: List[int]):
        if not sale_ids:
            return []
        placeholders = ",".join("?" for _ in sale_ids)
        cursor.execute(
            f"""
            SELECT si.*, p.name, p.category, p.supplier, p.supplier_price, p.code,
                   p.list_date, p.unit_quantity
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id IN ({placeholders})
            """,
            sale_ids,
        )
        return cursor.fetchall()

    def _build_items(self, item_rows, sale_id: int) -> List[SaleItem]:
        items = []
        for row in item_rows:
            unit_price = Decimal(str(row["unit_price"]))
            cost_price = Decimal(str(row["cost_price"])) if row["cost_price"] else Decimal("0")

            try:
                list_date = date.fromisoformat(row["list_date"]) if row["list_date"] else date.today()
            except Exception:
                list_date = date.today()

            product = Product(
                id=row["product_id"],
                name=row["name"],
                category=row["category"],
                supplier=row["supplier"] if row["supplier"] else '',
                list_date=list_date,
                supplier_price=Decimal(str(row["supplier_price"])) if row["supplier_price"] else cost_price,
                selling_price=unit_price,
                unit_quantity=row["unit_quantity"] if row["unit_quantity"] else 1,
                unit_price=unit_price,
                price_usd=Decimal("0"),
                selling_price_usd=Decimal("0"),
                code=row["code"] if row["code"] else '',
            )
            items.append(
                SaleItem(
                    product=product,
                    quantity=Decimal(str(row["quantity"])),
                    unit_price=unit_price,
                    cost_price=cost_price,
                )
            )
        return items

    def get_all(self) -> List[Sale]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales ORDER BY created_at DESC")
        sale_rows = cursor.fetchall()
        sale_ids = [r["id"] for r in sale_rows]
        item_rows = self._fetch_items(cursor, sale_ids)
        conn.close()

        items_by_sale: dict = {}
        for row in item_rows:
            items_by_sale.setdefault(row["sale_id"], []).append(row)

        result = []
        for srow in sale_rows:
            sid = srow["id"]
            items = self._build_items(items_by_sale.get(sid, []), sid)
            result.append(Sale(
                id=sid,
                items=items,
                customer=srow["customer"] if srow["customer"] else '',
                created_at=datetime.fromisoformat(srow["created_at"]),
            ))
        return result

    def get_by_date_range(self, start: datetime, end: datetime) -> List[Sale]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sales WHERE created_at >= ? AND created_at < ? ORDER BY created_at",
            (start.isoformat(), end.isoformat()),
        )
        sale_rows = cursor.fetchall()
        sale_ids = [r["id"] for r in sale_rows]
        item_rows = self._fetch_items(cursor, sale_ids)
        conn.close()

        items_by_sale: dict = {}
        for row in item_rows:
            items_by_sale.setdefault(row["sale_id"], []).append(row)

        result = []
        for srow in sale_rows:
            sid = srow["id"]
            items = self._build_items(items_by_sale.get(sid, []), sid)
            result.append(Sale(
                id=sid,
                items=items,
                customer=srow["customer"] if srow["customer"] else '',
                created_at=datetime.fromisoformat(srow["created_at"]),
            ))
        return result

    def delete(self, sale_id: int) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
        cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        conn.commit()
        conn.close()
