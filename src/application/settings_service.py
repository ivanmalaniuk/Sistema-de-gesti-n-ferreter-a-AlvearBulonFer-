"""
CAPA DE APLICACION — Servicio de configuracion.

Administra las configuraciones globales del sistema:
- Tipo de cambio USD (para calcular precios en dolares)
- Margen de ganancia (porcentaje aplicado al precio proveedor)

Los valores se persisten en la tabla 'settings' de SQLite.
"""

from decimal import Decimal

from src.domain.interfaces import ISettingsRepository


class SettingsService:
    """Gestion de configuraciones globales (USD rate, margen)."""

    def __init__(self, settings_repo: ISettingsRepository):
        self._settings_repo = settings_repo

    def get_usd_rate(self) -> Decimal:
        """Retorna el tipo de cambio USD actual."""
        raw = self._settings_repo.get("usd_rate", "1500")
        return Decimal(raw)

    def set_usd_rate(self, rate: Decimal) -> None:
        """Actualiza el tipo de cambio USD."""
        if rate <= 0:
            raise ValueError("El tipo de cambio USD debe ser mayor a cero")
        self._settings_repo.set("usd_rate", str(rate))

    def get_profit_margin(self) -> Decimal:
        """
        Retorna el margen de ganancia en porcentaje.
        Ej: 160 significa 160% (precio venta = precio proveedor * 1.6)
        """
        raw = self._settings_repo.get("profit_margin", "160")
        return Decimal(raw)

    def set_profit_margin(self, margin: Decimal) -> None:
        """Actualiza el margen de ganancia."""
        if margin <= 0:
            raise ValueError("El margen de ganancia debe ser mayor a cero")
        self._settings_repo.set("profit_margin", str(margin))

    def get_backup_dir(self) -> str:
        """Retorna la carpeta donde se guardan los backups automaticos."""
        return self._settings_repo.get("backup_dir", "backups")

    def set_backup_dir(self, path: str) -> None:
        """Actualiza la carpeta de backups automaticos."""
        self._settings_repo.set("backup_dir", path)

    def get_backup_keep(self) -> int:
        """Retorna cuantos backups se conservan (default 10)."""
        return int(self._settings_repo.get("backup_keep", "10"))

    def set_backup_keep(self, keep: int) -> None:
        """Actualiza la cantidad de backups a conservar."""
        if keep < 1:
            raise ValueError("La cantidad de backups debe ser al menos 1")
        self._settings_repo.set("backup_keep", str(keep))
