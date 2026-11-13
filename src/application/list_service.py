"""
CAPA DE APLICACION — Servicio de listas de precios.

Procesa los datos extraidos de un archivo XLSX/XLS y crea o actualiza
los productos en la base de datos con los calculos de precios.

Regla de duplicados:
  Si ya existe un producto del mismo proveedor con el mismo nombre,
  se compara la fecha de lista: la mas reciente prevalece.
  Si la nueva lista es mas reciente → se actualiza el producto existente.
  Si la lista existente es mas reciente → se conserva el precio anterior.

La logica de calculo aplica:
  selling_price = supplier_price * (profit_margin / 100)
  price_usd = supplier_price / usd_rate
  selling_price_usd = price_usd * (profit_margin / 100)
  unit_price = selling_price (por defecto unit_quantity = 1)
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict

from src.domain.entities import Product, UploadedList
from src.domain.interfaces import IProductRepository, IUploadedListRepository

PRECIO = Decimal("0.01")


class ListService:
    """Importacion de listas de precios desde datos tabulares (XLSX/XLS)."""

    def __init__(self, product_repo: IProductRepository, uploaded_list_repo: Optional[IUploadedListRepository] = None):
        self._product_repo = product_repo
        self._uploaded_list_repo = uploaded_list_repo

    def import_from_xls_rows(
        self,
        rows: List[dict],
        supplier: str,
        list_date: date,
        usd_rate: Decimal,
        profit_margin: Decimal,
        filename: str = "",
    ) -> Dict[str, int]:
        """
        Procesa las filas creando o actualizando productos.

        Si un producto del mismo proveedor con igual nombre ya existe,
        se compara la fecha de lista: el precio mas reciente prevalece.

        Args:
            rows: Lista de diccionarios con name, category, supplier_price.
            supplier: Nombre del proveedor.
            list_date: Fecha de la lista actual.
            usd_rate: Tipo de cambio USD.
            profit_margin: Margen de ganancia en % (ej: 160).
            filename: Nombre del archivo importado (opcional, para trackear listas subidas).

        Returns:
            Dict con claves: imported, updated, skipped.
        """
        result = {"imported": 0, "updated": 0, "skipped": 0}
        margin_multiplier = profit_margin / Decimal("100")

        for row in rows:
            name = row.get("name", "").strip()
            category = row.get("category", "").strip()
            code = str(row.get("code", "")).strip() if row.get("code") else ""
            raw_price = row.get("supplier_price", "0")

            if not name:
                continue

            try:
                supplier_price = Decimal(str(raw_price)).quantize(
                    PRECIO, rounding=ROUND_HALF_UP
                )
            except Exception:
                continue

            if supplier_price <= 0:
                continue

            # Calcular precios derivados
            selling_price = (supplier_price * margin_multiplier).quantize(
                PRECIO, rounding=ROUND_HALF_UP
            )
            price_usd = (supplier_price / usd_rate).quantize(
                PRECIO, rounding=ROUND_HALF_UP
            )
            selling_price_usd = (price_usd * margin_multiplier).quantize(
                PRECIO, rounding=ROUND_HALF_UP
            )
            unit_quantity = 1
            unit_price = selling_price

            # Buscar si ya existe un producto del mismo proveedor con igual nombre
            existing = self._product_repo.find_by_name_and_supplier(name, supplier)
            if not existing and category:
                base = name.removesuffix(f" - {category}").strip()
                if base:
                    existing = self._product_repo.find_by_name_and_supplier(base, supplier)

            if existing:
                # Ya existe: comparar fechas para decidir si actualizar
                if list_date >= existing.list_date:
                    # La nueva lista es mas reciente (o igual): actualizar
                    existing.name = name
                    existing.category = category
                    existing.code = code
                    existing.list_date = list_date
                    existing.supplier_price = supplier_price
                    existing.selling_price = selling_price
                    existing.unit_quantity = unit_quantity
                    existing.unit_price = unit_price
                    existing.price_usd = price_usd
                    existing.selling_price_usd = selling_price_usd
                    self._product_repo.update(existing)
                    result["updated"] += 1
                else:
                    # La lista existente es mas reciente: conservar precio anterior
                    result["skipped"] += 1
            else:
                # No existe: crear nuevo producto
                product = Product(
                    name=name,
                    category=category,
                    supplier=supplier,
                    list_date=list_date,
                    supplier_price=supplier_price,
                    selling_price=selling_price,
                    unit_quantity=unit_quantity,
                    unit_price=unit_price,
                    price_usd=price_usd,
                    selling_price_usd=selling_price_usd,
                    code=code,
                )
                self._product_repo.add(product)
                result["imported"] += 1

        if filename and self._uploaded_list_repo:
            existing = self._uploaded_list_repo.get_by_supplier_and_date(supplier, list_date)
            if not existing:
                self._uploaded_list_repo.add(UploadedList(filename=filename, supplier=supplier, list_date=list_date))

        return result

    def get_suppliers(self) -> List[str]:
        """Retorna la lista de proveedores existentes (ordenada)."""
        return self._product_repo.get_suppliers()

    def get_uploaded_lists(self) -> List[UploadedList]:
        """Retorna todas las listas subidas registradas."""
        if not self._uploaded_list_repo:
            return []
        return self._uploaded_list_repo.get_all()

    def delete_uploaded_list(self, list_id: int) -> int:
        """Elimina una lista subida y todos sus productos. Retorna cantidad de productos eliminados."""
        if not self._uploaded_list_repo:
            return 0
        ul = self._uploaded_list_repo.get_all()
        target = next((u for u in ul if u.id == list_id), None)
        if not target:
            return 0
        deleted = self._product_repo.delete_by_supplier_and_date(target.supplier, target.list_date)
        self._uploaded_list_repo.delete(list_id)
        return deleted
