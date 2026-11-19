"""Tests de la parte pura del script de medicion de rendimiento (issue #4)."""

from scripts.medir_rendimiento import construir_informe


def _datos():
    return {
        "entorno": {
            "fecha": "2026-11-19 10:00",
            "sistema": "TestOS-1.0",
            "python": "3.14.0",
            "tk": "9.0",
            "customtkinter": "6.0.0",
            "productos": 10,
            "ventas": 5,
            "reps": 2,
        },
        "fases": [
            ("Importacion (customtkinter, PIL, src)", 100.0),
            ("Construccion (DB + servicios + ventana)", 50.0),
            ("Primer dibujo en pantalla", 20.0),
            ("Total arranque", 170.0),
        ],
        "pestanas": [
            {
                "nombre": "Registrar Venta",
                "tipo": "inicial",
                "frio": 5.0,
                "repetidas": [4.0, 6.0],
            },
            {
                "nombre": "Faltantes",
                "tipo": "demanda",
                "frio": 80.0,
                "repetidas": [10.0, 12.0],
            },
        ],
    }


def test_informe_incluye_todas_las_pestanas():
    informe = construir_informe(_datos())
    assert "Registrar Venta" in informe
    assert "Faltantes" in informe


def test_informe_calcula_min_y_media_de_repeticiones():
    informe = construir_informe(_datos())
    assert "| Faltantes | demanda | 80.0 | 10.0 | 11.0 |" in informe


def test_informe_incluye_arranque_entorno_y_repeticiones():
    informe = construir_informe(_datos())
    assert "| Total arranque | 170.0 |" in informe
    assert "Python 3.14.0" in informe
    assert "2 repeticiones" in informe
    assert "TestOS-1.0" in informe
