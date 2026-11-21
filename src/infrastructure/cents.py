"""
CAPA DE INFRAESTRUCTURA — Conversión de dinero a centavos enteros.

El dinero se almacena en SQLite como centavos enteros (INTEGER). Estas
funciones son el único punto de conversión entre el dominio (Decimal en
pesos) y el almacenamiento.
"""

from decimal import Decimal, ROUND_HALF_UP


def to_cents(valor: Decimal) -> int:
    """Convierte pesos (Decimal) a centavos enteros, con redondeo HALF_UP."""
    return int((valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_cents(centavos: int) -> Decimal:
    """Convierte centavos enteros a pesos (Decimal)."""
    return Decimal(centavos) / 100
