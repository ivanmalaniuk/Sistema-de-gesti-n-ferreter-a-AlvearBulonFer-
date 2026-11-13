"""
Tests del backup automatico de la base de datos al cerrar la app.

Se usa siempre una base temporal (tmp_path); nunca la ferreteria.db real.
"""

import os
import sqlite3
from unittest.mock import create_autospec

import pytest

from src.domain.interfaces import ISettingsRepository
from src.application.settings_service import SettingsService
from src.infrastructure.backup import create_backup


def _crear_base_temporal(ruta: str) -> None:
    """Crea una base SQLite minima con una fila de prueba."""
    conn = sqlite3.connect(ruta)
    conn.execute("CREATE TABLE prueba (id INTEGER PRIMARY KEY, nombre TEXT)")
    conn.execute("INSERT INTO prueba (nombre) VALUES ('martillo')")
    conn.commit()
    conn.close()


def _backups_en(carpeta) -> list:
    """Lista ordenada de backups presentes en la carpeta."""
    return sorted(
        f for f in os.listdir(carpeta)
        if f.startswith("ferreteria_") and f.endswith(".db")
    )


class TestCreateBackup:
    def test_crea_backup_valido_con_los_mismos_datos(self, tmp_path):
        origen = str(tmp_path / "origen.db")
        _crear_base_temporal(origen)
        carpeta = str(tmp_path / "backups")

        destino = create_backup(origen, carpeta, keep_last=10)

        assert os.path.exists(destino)
        conn = sqlite3.connect(destino)
        fila = conn.execute("SELECT nombre FROM prueba").fetchone()
        conn.close()
        assert fila[0] == "martillo"

    def test_poda_conserva_solo_los_ultimos_backups(self, tmp_path):
        origen = str(tmp_path / "origen.db")
        _crear_base_temporal(origen)
        carpeta = tmp_path / "backups"
        carpeta.mkdir()

        # Tres backups viejos, con nombres anteriores al de hoy
        for nombre in (
            "ferreteria_20000101_000000.db",
            "ferreteria_20000102_000000.db",
            "ferreteria_20000103_000000.db",
        ):
            (carpeta / nombre).touch()

        nuevo = create_backup(origen, str(carpeta), keep_last=2)

        restantes = _backups_en(carpeta)
        assert len(restantes) == 2
        assert os.path.basename(nuevo) in restantes
        assert "ferreteria_20000103_000000.db" in restantes

    def test_crea_la_carpeta_si_no_existe(self, tmp_path):
        origen = str(tmp_path / "origen.db")
        _crear_base_temporal(origen)
        carpeta = tmp_path / "no_existe" / "sub"

        destino = create_backup(origen, str(carpeta), keep_last=10)

        assert carpeta.exists()
        assert os.path.exists(destino)

    def test_ruta_relativa_se_resuelve_junto_a_la_base(self, tmp_path):
        origen = str(tmp_path / "origen.db")
        _crear_base_temporal(origen)

        destino = create_backup(origen, "backups_relativos", keep_last=10)

        assert os.path.dirname(destino) == str(tmp_path / "backups_relativos")


@pytest.fixture
def settings_repo():
    repo = create_autospec(ISettingsRepository)
    repo.get.side_effect = lambda k, d="": {
        "backup_dir": "mis_backups",
        "backup_keep": "5",
    }.get(k, d)
    return repo


@pytest.fixture
def settings_service(settings_repo):
    return SettingsService(settings_repo)


class TestSettingsBackup:
    def test_get_backup_dir(self, settings_service):
        assert settings_service.get_backup_dir() == "mis_backups"

    def test_get_backup_keep(self, settings_service):
        assert settings_service.get_backup_keep() == 5

    def test_defaults_cuando_no_hay_configuracion(self):
        repo = create_autospec(ISettingsRepository)
        repo.get.side_effect = lambda k, d="": d
        service = SettingsService(repo)
        assert service.get_backup_dir() == "backups"
        assert service.get_backup_keep() == 10

    def test_set_backup_dir(self, settings_service, settings_repo):
        settings_service.set_backup_dir("C:/respaldos")
        settings_repo.set.assert_called_once_with("backup_dir", "C:/respaldos")

    def test_set_backup_keep(self, settings_service, settings_repo):
        settings_service.set_backup_keep(5)
        settings_repo.set.assert_called_once_with("backup_keep", "5")

    def test_set_backup_keep_invalido_raise_error(self, settings_service):
        with pytest.raises(ValueError, match="al menos 1"):
            settings_service.set_backup_keep(0)
