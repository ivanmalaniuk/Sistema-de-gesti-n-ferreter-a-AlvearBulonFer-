"""
PUNTO DE ENTRADA DE LA APLICACION.

Ensambla el grafo de dependencias siguiendo el patron de
Inyeccion de Dependencias (Dependency Injection).

Flujo de ensamblado:
1. Inicializar base de datos SQLite (crear tablas si no existen)
2. Crear repositorios (Infrastructure Layer)
3. Crear servicios inyectando los repositorios (Application Layer)
4. Crear la ventana principal inyectando los servicios (Presentation Layer)
5. Iniciar el bucle de eventos de la GUI

Este es el UNICO lugar donde se ensamblan las dependencias
(Composition Root). Ninguna otra parte del codigo crea instancias
de repositorios o servicios directamente.
"""

import sys
import os

# Asegurar que el directorio raiz esta en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.database import init_db, DB_PATH
from src.infrastructure.backup import create_backup
from src.infrastructure.product_repository import SQLiteProductRepository
from src.infrastructure.sale_repository import SQLiteSaleRepository
from src.infrastructure.expense_repository import SQLiteExpenseRepository
from src.infrastructure.settings_repository import SQLiteSettingsRepository
from src.infrastructure.missing_item_repository import SQLiteMissingItemRepository
from src.infrastructure.uploaded_list_repository import SQLiteUploadedListRepository
from src.application.product_service import ProductService
from src.application.sale_service import SaleService
from src.application.expense_service import ExpenseService
from src.application.report_service import ReportService
from src.application.list_service import ListService
from src.application.settings_service import SettingsService
from src.application.missing_item_service import MissingItemService
from src.presentation.app import App


def main():
    """Punto de entrada: inicializa DB, crea dependencias y lanza la GUI."""

    # 1. Asegurar que la base de datos y tablas existen
    init_db()

    # 2. Crear repositorios (implementaciones concretas de las interfaces)
    product_repo = SQLiteProductRepository()
    sale_repo = SQLiteSaleRepository(product_repo)  # SaleRepo necesita ProductRepo
    expense_repo = SQLiteExpenseRepository()
    settings_repo = SQLiteSettingsRepository()
    missing_repo = SQLiteMissingItemRepository()

    # 3. Crear servicios de aplicacion (inyectando repositorios)
    settings_service = SettingsService(settings_repo)
    product_service = ProductService(product_repo, settings_service)
    sale_service = SaleService(sale_repo, product_repo)
    expense_service = ExpenseService(expense_repo)
    report_service = ReportService(sale_repo, expense_repo)
    uploaded_list_repo = SQLiteUploadedListRepository()
    list_service = ListService(product_repo, uploaded_list_repo)
    missing_service = MissingItemService(missing_repo)

    # Backup automatico al cerrar: lee la configuracion y copia la base.
    # Si falla, App._on_close lo registra pero igual cierra la aplicacion.
    def _hacer_backup():
        create_backup(
            DB_PATH,
            settings_service.get_backup_dir(),
            settings_service.get_backup_keep(),
        )

    # 4. Crear y lanzar la interfaz grafica (inyectando servicios)
    app = App(
        product_service=product_service,
        sale_service=sale_service,
        expense_service=expense_service,
        report_service=report_service,
        list_service=list_service,
        settings_service=settings_service,
        missing_service=missing_service,
        backup_on_close=_hacer_backup,
    )

    # 5. Iniciar el bucle de eventos de CustomTkinter
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("\nPresione Enter para salir...")
