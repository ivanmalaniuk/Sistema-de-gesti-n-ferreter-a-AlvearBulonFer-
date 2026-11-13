"""
CAPA DE DOMINIO — Entidades del negocio.

Estas clases representan los objetos fundamentales del sistema:
Producto, Venta, Item de Venta y Gasto. Contienen la logica de
negocio basica (calculo de subtotales, totales) sin depender de
ninguna capa externa (Python puro + dataclasses).

Principio: Single Responsibility — cada entidad solo modela su estado
y comportamiento esencial.
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional


@dataclass
class Product:
    """
    Producto del catalogo de la ferreteria.

    - supplier_price: precio que cobra el proveedor (en pesos arg.)
    - selling_price: precio de venta al publico (calculado = supplier * margen)
    - unit_quantity: cantidad de unidades por paquete (1 = unitario,
      100 = bolsa de 100 tornillos, etc.)
    - unit_price: precio por unidad individual (selling_price / unit_quantity)
    - price_usd: precio del proveedor convertido a dolares
    - selling_price_usd: precio de venta en dolares
    """

    name: str
    category: str
    supplier: str
    list_date: date
    supplier_price: Decimal
    selling_price: Decimal
    unit_quantity: int
    unit_price: Decimal
    price_usd: Decimal
    selling_price_usd: Decimal
    code: str = ''
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class SaleItem:
    """
    Linea de una venta: asocia un producto, cantidad y precios.
    - unit_price: precio de venta por unidad
    - cost_price: precio de costo (supplier_price) al momento de la venta
    El subtotal se calcula automaticamente como quantity * unit_price.
    quantity puede ser fraccionario (ej: 0.5 kg de electrodos).
    """

    product: Product
    quantity: Decimal
    unit_price: Decimal
    cost_price: Decimal = Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Sale:
    """
    Venta compuesta por uno o mas SaleItem.
    El total_amount se calcula sumando los subtotales de los items.
    """

    items: List[SaleItem]
    customer: str = ''
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    @property
    def total_amount(self) -> Decimal:
        return sum((item.subtotal for item in self.items), Decimal("0"))


@dataclass
class MissingItem:
    name: str
    supplier: str = ''
    notes: str = ''
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class UploadedList:
    filename: str
    supplier: str
    list_date: date
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class Expense:
    """
    Gasto operativo: descripcion, monto, fecha, categoria y proveedor.
    Ej: "Compra de cemento", $5000, 01/07/2026, Insumos, FGP.
    """

    description: str
    amount: Decimal
    date: datetime
    category: str
    supplier: str = ''
    id: Optional[int] = None
    created_at: Optional[datetime] = None
