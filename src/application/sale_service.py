"""
CAPA DE APLICACION — Servicio de ventas.

Orquesta el registro de ventas:
- Valida que haya productos y cantidades validas
- Usa unit_price del producto para calcular subtotales
- Delega la persistencia a ISaleRepository

Nota: No hay control de stock. Solo registramos transacciones monetarias.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from src.domain.entities import Sale, SaleItem
from src.domain.interfaces import ISaleRepository, IProductRepository


class SaleService:
    """Casos de uso del modulo de ventas."""

    def __init__(self, sale_repo: ISaleRepository, product_repo: IProductRepository):
        self._sale_repo = sale_repo
        self._product_repo = product_repo

    def record_sale(
        self, items_data: List[Tuple[int, Decimal]], customer: str = '',
        unit_prices: Optional[List[Decimal]] = None,
    ) -> Sale:
        """
        Registra una venta.

        Args:
            items_data: Lista de tuplas (product_id, quantity).
                        La cantidad se expresa en UNIDADES (no paquetes).
                        Ej: para vender 2 tornillos de una bolsa de 100,
                        quantity=2, y se usa el unit_price del producto.
                        Puede ser fraccionario (ej: 0.5 kg de electrodos).
            unit_prices: Lista opcional de precios unitarios personalizados.
                         Si se provee, debe tener la misma longitud que items_data.
                         Cada elemento reemplaza el unit_price del producto para esa venta.

        Returns:
            Sale con id y created_at asignados.
        """
        if not items_data:
            raise ValueError("La venta debe tener al menos un producto")

        items = []
        for idx, (product_id, quantity) in enumerate(items_data):
            if quantity <= 0:
                raise ValueError(
                    f"La cantidad debe ser mayor a cero para el producto ID {product_id}"
                )
            product = self._product_repo.get_by_id(product_id)
            if product is None:
                raise ValueError(f"Producto con ID {product_id} no encontrado")

            # Usamos unit_price: para productos unitarios es igual al selling_price,
            # para productos en bulk es el precio por unidad individual.
            unit_price = unit_prices[idx] if unit_prices and idx < len(unit_prices) and unit_prices[idx] is not None else product.unit_price
            cost_price = product.supplier_price / Decimal(str(product.unit_quantity))
            if product.unit_quantity > 1:
                cost_price = cost_price.quantize(Decimal("0.01"))
            items.append(
                SaleItem(
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    cost_price=cost_price,
                )
            )

        sale = Sale(items=items, customer=customer, created_at=datetime.now())
        return self._sale_repo.add(sale)

    def get_sale(self, sale_id: int) -> Sale:
        sale = self._sale_repo.get_by_id(sale_id)
        if sale is None:
            raise ValueError(f"Venta con ID {sale_id} no encontrada")
        return sale

    def get_all_sales(self) -> List[Sale]:
        return self._sale_repo.get_all()

    def get_sales_by_date_range(self, start: datetime, end: datetime) -> List[Sale]:
        return self._sale_repo.get_by_date_range(start, end)

    def delete_sale(self, sale_id: int) -> None:
        self._sale_repo.delete(sale_id)

    def calculate_total(self, items_data: List[Tuple[int, Decimal]]) -> Decimal:
        """
        Calcula el total sin persistir (util para mostrar en UI antes de registrar).
        """
        total = Decimal("0")
        for product_id, quantity in items_data:
            product = self._product_repo.get_by_id(product_id)
            if product is None:
                raise ValueError(f"Producto con ID {product_id} no encontrado")
            total += product.unit_price * quantity
        return total
