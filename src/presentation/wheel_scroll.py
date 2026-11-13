"""
Utilidad de presentacion — scroll con la rueda del raton.

CTkScrollableFrame registra su propio handler de rueda via bind_all por
cada instancia. Esto falla en entornos con Tk 9.0 y puede provocar doble
scroll. Esta utilidad reemplaza todos esos handlers con UN SOLO handler
global que detecta cual scrollable esta bajo el mouse y lo desplaza.

Como bind_all sin add=True reemplaza el bindtag "all", volver a registrar
el handler global al crear cada scrollable garantiza que nunca quede el
handler por defecto activo (evita doble scroll) y que los contenidos
generados dinamicamente tambien respondan a la rueda.
"""

import sys

_scrollables = []


def register_scrollable(sf):
    """Reemplaza el handler global de rueda y registra el scrollable."""
    _scrollables.append(sf)
    root = sf.winfo_toplevel()
    root.bind_all("<MouseWheel>", _on_wheel)
    root.bind_all("<Button-4>", _on_wheel)
    root.bind_all("<Button-5>", _on_wheel)


def _on_wheel(event):
    target = _innermost_scrollable(event.widget)
    if target is None:
        return
    canvas = target._parent_canvas
    if canvas.yview() == (0.0, 1.0):
        return
    if sys.platform.startswith("win"):
        canvas.yview_scroll(-int(event.delta / 6), "units")
    elif sys.platform == "darwin":
        canvas.yview_scroll(-event.delta, "units")
    else:
        delta = getattr(event, "delta", 0) or 0
        if delta != 0:
            canvas.yview_scroll(-1 if delta > 0 else 1, "units")
        elif event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")


def _innermost_scrollable(widget):
    best = None
    w = widget
    while w is not None:
        for sf in _scrollables:
            if w is sf or w is sf._parent_canvas or w is sf._parent_frame:
                best = sf
        w = getattr(w, "master", None)
    return best
