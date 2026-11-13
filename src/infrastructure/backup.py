"""
CAPA DE INFRAESTRUCTURA — Backup de la base de datos SQLite.

Copia la base a una carpeta configurable usando la API de backup de sqlite3
(segura con WAL porque copia una imagen consistente, no el archivo a mano)
y conserva solo los ultimos N respaldos.
"""

import os
import sqlite3
from datetime import datetime

_PREFIJO = "ferreteria_"
_SUFIJO = ".db"


def create_backup(db_path: str, backup_dir: str, keep_last: int) -> str:
    """
    Crea un backup de `db_path` dentro de `backup_dir` y poda los viejos.

    - Si `backup_dir` es relativa, se resuelve contra la carpeta de `db_path`.
    - Nombre: ferreteria_YYYYMMDD_HHMMSS.db. Si ya existe (dos backups en el
      mismo segundo), se agrega un sufijo numerico: _1, _2, ...
    - Conserva solo los `keep_last` backups mas nuevos (ordenados por nombre).

    Retorna la ruta del backup creado. Los errores se propagan al llamador.
    """
    if not os.path.isabs(backup_dir):
        base_dir = os.path.dirname(os.path.abspath(db_path))
        backup_dir = os.path.join(base_dir, backup_dir)

    os.makedirs(backup_dir, exist_ok=True)

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(backup_dir, f"{_PREFIJO}{marca}{_SUFIJO}")
    sufijo = 1
    while os.path.exists(destino):
        destino = os.path.join(backup_dir, f"{_PREFIJO}{marca}_{sufijo}{_SUFIJO}")
        sufijo += 1

    # API de backup de sqlite3: copia consistente incluso con WAL activo
    origen_conn = sqlite3.connect(db_path)
    destino_conn = sqlite3.connect(destino)
    try:
        origen_conn.backup(destino_conn)
    finally:
        destino_conn.close()
        origen_conn.close()

    # Poda: se ordenan por nombre (el timestamp hace que el orden sea cronologico)
    archivos = sorted(
        os.path.join(backup_dir, nombre)
        for nombre in os.listdir(backup_dir)
        if nombre.startswith(_PREFIJO) and nombre.endswith(_SUFIJO)
    )
    if keep_last >= 1 and len(archivos) > keep_last:
        for viejo in archivos[:-keep_last]:
            os.remove(viejo)

    return destino
