"""
CAPA DE INFRAESTRUCTURA — Verificacion del entorno de ejecucion.

El entorno recomendado para esta aplicacion es Python 3.12/3.13 con Tk 8.6
(incluido en esas versiones de Python). Las versiones mas nuevas, como
Python 3.14 con Tk 9.0, tienen incompatibilidades conocidas con CustomTkinter.

Este modulo solo genera un aviso de texto: no bloquea el arranque, no modifica
el entorno y no importa tkinter (la version de Tk se recibe como parametro).
"""

PYTHON_RECOMENDADO = ((3, 12), (3, 13))
TK_RECOMENDADO = 8.6


def get_environment_warning(python_version, tk_version) -> str | None:
    """
    Devuelve un aviso si Python o Tk no son las versiones recomendadas.

    `python_version` es una secuencia tipo `sys.version_info` y `tk_version`
    un numero tipo `tkinter.TkVersion`. Se comparan solo (major, minor) de
    Python y Tk redondeado a un decimal. Retorna None si todo coincide.
    """
    problemas = []

    python_actual = (python_version[0], python_version[1])
    if python_actual not in PYTHON_RECOMENDADO:
        detectado = f"{python_actual[0]}.{python_actual[1]}"
        recomendado = " o ".join(
            f"{mayor}.{menor}" for mayor, menor in PYTHON_RECOMENDADO
        )
        problemas.append(
            f"- Python {detectado} detectado (recomendado: {recomendado})"
        )

    tk_actual = round(float(tk_version), 1)
    if tk_actual != TK_RECOMENDADO:
        problemas.append(
            f"- Tk {tk_actual} detectado (recomendado: {TK_RECOMENDADO})"
        )

    if not problemas:
        return None

    return "Entorno no recomendado:\n" + "\n".join(problemas)
