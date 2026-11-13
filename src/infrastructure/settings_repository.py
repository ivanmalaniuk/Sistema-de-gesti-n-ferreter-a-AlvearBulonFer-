"""
CAPA DE INFRAESTRUCTURA — Repositorio de configuraciones (SQLite).

Implementa ISettingsRepository usando la tabla 'settings' con formato
clave-valor. Se usa para persistir el tipo de cambio USD y el margen
de ganancia.
"""

from src.domain.interfaces import ISettingsRepository
from src.infrastructure.database import get_connection


class SQLiteSettingsRepository(ISettingsRepository):
    """Guarda y recupera configuraciones desde SQLite."""

    def get(self, key: str, default: str = "") -> str:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
        conn.close()
