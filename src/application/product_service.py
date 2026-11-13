"""
CAPA DE APLICACION — Servicio de productos.

Orquesta los casos de uso relacionados a productos:
- CRUD basico (crear, leer, actualizar, eliminar)
- Busqueda por nombre (para el autocomplete en ventas)
- Recalculo de precios segun margen y USD actuales

Depende de IProductRepository para persistencia y de SettingsService
para obtener el margen y tipo de cambio al recalcular.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from src.domain.entities import Product
from src.domain.interfaces import IProductRepository
from src.application.settings_service import SettingsService

PRECIO = Decimal("0.01")  # Precision de 2 decimales para precios


class ProductService:
    """Casos de uso del catalogo de productos."""

    def __init__(
        self, product_repo: IProductRepository, settings_service: SettingsService
    ):
        self._product_repo = product_repo
        self._settings = settings_service

    def create_product(
        self,
        name: str,
        category: str,
        supplier: str,
        list_date: date,
        supplier_price: Decimal,
        selling_price: Decimal,
        unit_quantity: int,
        unit_price: Decimal,
        price_usd: Decimal,
        selling_price_usd: Decimal,
        code: str = '',
    ) -> Product:
        """Crea un nuevo producto con todas las validaciones de negocio."""
        if not name or not name.strip():
            raise ValueError("El nombre del producto no puede estar vacio")
        if supplier_price <= 0:
            raise ValueError("El precio de proveedor debe ser mayor a cero")
        if selling_price <= 0:
            raise ValueError("El precio de venta debe ser mayor a cero")
        if unit_quantity < 1:
            raise ValueError("La cantidad por unidad debe ser al menos 1")

        product = Product(
            name=name.strip(),
            category=category.strip(),
            supplier=supplier.strip(),
            list_date=list_date,
            supplier_price=supplier_price,
            selling_price=selling_price,
            unit_quantity=unit_quantity,
            unit_price=unit_price,
            price_usd=price_usd,
            selling_price_usd=selling_price_usd,
            code=code.strip(),
        )
        return self._product_repo.add(product)

    def get_product(self, product_id: int) -> Product:
        product = self._product_repo.get_by_id(product_id)
        if product is None:
            raise ValueError(f"Producto con ID {product_id} no encontrado")
        return product

    def get_all_products(self) -> List[Product]:
        """Retorna todos los productos ordenados alfabeticamente."""
        return self._product_repo.get_all_sorted()

    def search_products(self, query: str, supplier: str = '', limit: int = 0) -> List[Product]:
        """Busca productos por texto + opcional filtro de proveedor + limite."""
        q = query.strip() if query else ''
        return self._product_repo.search_by_name(q, supplier, limit)

    def get_suppliers(self) -> List[str]:
        return self._product_repo.get_suppliers()

    def update_product(
        self,
        product_id: int,
        name: str,
        category: str,
        supplier: str,
        list_date: date,
        supplier_price: Decimal,
        selling_price: Decimal,
        unit_quantity: int,
        unit_price: Decimal,
        price_usd: Decimal,
        selling_price_usd: Decimal,
        code: str = '',
    ) -> Product:
        """Actualiza un producto existente con validaciones."""
        product = self.get_product(product_id)
        if not name or not name.strip():
            raise ValueError("El nombre del producto no puede estar vacio")
        if supplier_price <= 0:
            raise ValueError("El precio de proveedor debe ser mayor a cero")
        if selling_price <= 0:
            raise ValueError("El precio de venta debe ser mayor a cero")
        if unit_quantity < 1:
            raise ValueError("La cantidad por unidad debe ser al menos 1")

        product.name = name.strip()
        product.category = category.strip()
        product.supplier = supplier.strip()
        product.list_date = list_date
        product.supplier_price = supplier_price
        product.selling_price = selling_price
        product.unit_quantity = unit_quantity
        product.unit_price = unit_price
        product.price_usd = price_usd
        product.selling_price_usd = selling_price_usd
        product.code = code.strip()
        self._product_repo.update(product)
        return product

    def recalculate_from_supplier_price(self, product: Product) -> Product:
        """
        Recalcula selling_price, price_usd, selling_price_usd y unit_price
        a partir del supplier_price actual del producto, usando el margen
        y tipo de cambio USD configurados en SettingsService.
        """
        rate = self._settings.get_usd_rate()
        margin = self._settings.get_profit_margin()
        margin_mult = margin / Decimal("100")

        # Precio de venta = precio proveedor * margen%
        product.selling_price = (product.supplier_price * margin_mult).quantize(
            PRECIO, rounding=ROUND_HALF_UP
        )

        # Precio en USD = precio proveedor / tipo de cambio
        product.price_usd = (product.supplier_price / rate).quantize(
            PRECIO, rounding=ROUND_HALF_UP
        )

        # Precio venta USD = precio USD * margen%
        product.selling_price_usd = (product.price_usd * margin_mult).quantize(
            PRECIO, rounding=ROUND_HALF_UP
        )

        # Precio por unidad individual
        if product.unit_quantity > 1:
            product.unit_price = (
                product.selling_price / Decimal(product.unit_quantity)
            ).quantize(PRECIO, rounding=ROUND_HALF_UP)
        else:
            product.unit_price = product.selling_price

        self._product_repo.update(product)
        return product

    def delete_product(self, product_id: int) -> None:
        self._product_repo.delete(product_id)

    def delete_products_by_supplier(self, supplier: str) -> int:
        if not supplier or not supplier.strip():
            raise ValueError("Debe especificar un proveedor")
        return self._product_repo.delete_by_supplier(supplier.strip())
