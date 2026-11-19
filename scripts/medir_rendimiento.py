#!/usr/bin/env python3
"""
Mide el tiempo de arranque y de apertura de cada pestana de la aplicacion.

Uso:
    python scripts/medir_rendimiento.py
    python scripts/medir_rendimiento.py --reps 5 --salida informe.md

Solo mide: no optimiza ni cambia comportamiento. Usa la base real, pero
unica operacion de escritura es init_db() (idempotente, ya ejecutado por
la app). El cierre NO dispara el backup automatico.
"""

import argparse
import os
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

# Marca de arranque del proceso, ANTES de los imports pesados.
_T0 = time.perf_counter()

# Referencia viva a la ventana: evita que el recolector la destruya (y se
# trabe) antes de emitir el informe. El proceso sale con os._exit(0).
_APP = None

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _ms(desde):
    """Milisegundos redondeados desde la marca `desde` hasta ahora."""
    return round((time.perf_counter() - desde) * 1000, 1)


def _carga_sistema():
    """Carga promedio de 1 min; None si el sistema no la expone."""
    try:
        return round(os.getloadavg()[0], 2)
    except (OSError, AttributeError):
        return None


def _memoria_libre_mb():
    """Memoria disponible en MB (Linux); None en otros sistemas."""
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for linea in fh:
                if linea.startswith("MemAvailable:"):
                    return round(int(linea.split()[1]) / 1024)
    except (OSError, ValueError, IndexError):
        return None
    return None


def _cambiar_pestana(app, nombre):
    """Selecciona una pestana y procesa eventos pendientes; devuelve ms."""
    t = time.perf_counter()
    app.main_window.set(nombre)
    app.update()
    return _ms(t)


def medir(reps=3):
    """Ejecuta la medicion completa y devuelve los datos como diccionario."""
    import tkinter

    import customtkinter as ctk

    import main as composicion
    from src.infrastructure.database import get_connection
    from src.presentation.main_window import _EAGER_TABS

    # Importacion: desde el arranque del proceso hasta aqui ya entro todo lo
    # pesado (customtkinter, PIL, services, presentacion), igual que main.py.
    fases = [("Importacion (customtkinter, PIL, src)", _ms(_T0))]

    t = time.perf_counter()
    app = composicion.construir_app()
    fases.append(("Construccion (DB + servicios + ventana)", _ms(t)))

    t = time.perf_counter()
    app.update()
    fases.append(("Primer dibujo en pantalla", _ms(t)))

    fases.append(("Total arranque", _ms(_T0)))

    # Volumen de datos: explica por que los tiempos pueden variar
    conn = get_connection()
    productos = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    ventas = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    conn.close()

    # Cada pestana: 1 medicion "fria" (crea la vista si es lazy) y `reps`
    # repeticiones "calientes" volviendo siempre a la pestana base.
    win = app.main_window
    base = "Registrar Venta"
    pestanas = []
    for nombre in list(win._tab_dict.keys()):
        win.set(base)
        frio = _cambiar_pestana(app, nombre)
        calientes = []
        for _ in range(reps):
            win.set(base)
            calientes.append(_cambiar_pestana(app, nombre))
        pestanas.append({
            "nombre": nombre,
            "tipo": "inicial" if nombre in _EAGER_TABS else "demanda",
            "frio": frio,
            "repetidas": calientes,
        })

    # Se cierra despues de imprimir el informe: destruir la ventana puede
    # demorar mucho en maquinas lentas y no debe perder la medicion.
    global _APP
    _APP = app

    return {
        "entorno": {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "sistema": platform.platform(),
            "python": platform.python_version(),
            "tk": str(tkinter.TkVersion),
            "customtkinter": ctk.__version__,
            "productos": productos,
            "ventas": ventas,
            "reps": reps,
            "carga": _carga_sistema(),
            "memoria_libre_mb": _memoria_libre_mb(),
        },
        "fases": fases,
        "pestanas": pestanas,
    }


def construir_informe(datos):
    """Arma el informe en Markdown a partir de las mediciones (parte pura)."""
    e = datos["entorno"]
    lineas = [
        f"# Medicion de rendimiento — {e['fecha']}",
        "",
        f"- Equipo: {e['sistema']}",
        f"- Python {e['python']} | Tk {e['tk']} | CustomTkinter {e['customtkinter']}",
        f"- Base: {e['productos']} productos, {e['ventas']} ventas",
        f"- Carga del sistema: {e.get('carga')} | Memoria disponible: "
        f"{e.get('memoria_libre_mb')} MB",
        "",
        "## Arranque",
        "",
        "| Fase | ms |",
        "|---|---:|",
    ]
    for fase, ms in datos["fases"]:
        lineas.append(f"| {fase} | {ms} |")

    lineas += [
        "",
        f"## Apertura de pestanas ({e['reps']} repeticiones)",
        "",
        "| Pestana | Tipo | 1a apertura (ms) | Repetida min (ms) | Repetida media (ms) |",
        "|---|---|---:|---:|---:|",
    ]
    for p in datos["pestanas"]:
        reps = p["repetidas"]
        minimo = round(min(reps), 1) if reps else "-"
        media = round(sum(reps) / len(reps), 1) if reps else "-"
        lineas.append(
            f"| {p['nombre']} | {p['tipo']} | {p['frio']} | {minimo} | {media} |"
        )

    lineas += [
        "",
        "Notas: no incluye el arranque del interprete Python ni el dialogo de "
        "aviso de entorno. '1a apertura' crea la vista si la pestana es lazy.",
        "",
    ]
    return "\n".join(lineas)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mide arranque y apertura de pestanas (solo medicion)."
    )
    parser.add_argument(
        "--reps", type=int, default=3,
        help="repeticiones 'calientes' por pestana (default: 3)",
    )
    parser.add_argument(
        "--salida", default=None,
        help="archivo donde guardar el informe en Markdown",
    )
    args = parser.parse_args(argv)

    datos = medir(args.reps)
    informe = construir_informe(datos)
    # end="" para que lo impreso sea identico al archivo guardado
    print(informe, end="")
    if args.salida:
        salida = Path(args.salida)
        salida.write_text(informe, encoding="utf-8")
        print(f"Informe guardado en {salida}", file=sys.stderr)

    sys.stdout.flush()
    sys.stderr.flush()
    # Salida directa: destruir la ventana puede trabarse en PC lentas y el
    # informe ya esta emitido. Igual que App._on_close.
    os._exit(0)


if __name__ == "__main__":
    main()
