"""
Tests de la conversión entre pesos (Decimal) y centavos enteros.

El dinero se almacena en SQLite como centavos enteros; estas funciones
son el único punto de conversión en el límite repositorio.
"""

from decimal import Decimal

from src.infrastructure.cents import from_cents, to_cents


def test_to_cents_convierte_pesos_a_centavos():
    assert to_cents(Decimal("12.34")) == 1234
    assert to_cents(Decimal("0.30")) == 30
    assert to_cents(Decimal("0")) == 0
    assert to_cents(Decimal("100")) == 10000


def test_to_cents_redondea_medio_centavo_hacia_arriba():
    assert to_cents(Decimal("12.345")) == 1235
    assert to_cents(Decimal("0.005")) == 1
    assert to_cents(Decimal("-1.235")) == -124


def test_to_cents_con_artefactos_de_float():
    # Valores típicos que dejan los floats al sumar o multiplicar
    assert to_cents(Decimal("0.30000000000000004")) == 30
    assert to_cents(Decimal("1.2299999999999998")) == 123


def test_from_cents_convierte_centavos_a_pesos():
    assert from_cents(1234) == Decimal("12.34")
    assert from_cents(30) == Decimal("0.3")
    assert from_cents(0) == Decimal("0")


def test_roundtrip_pesos_centavos():
    for pesos in ("12.34", "0.01", "999999.99", "0.30"):
        assert from_cents(to_cents(Decimal(pesos))) == Decimal(pesos)
