"""
CAPA DE PRESENTACION — Ventana principal con pestanas (tabs).

Organiza la aplicacion en 9 pestanas principales.
Las pestanas mas usadas se cargan al inicio; las menos usadas
se cargan bajo demanda (lazy loading) al hacer clic.

Pestanas eager (carga inmediata):
   1. Registrar Venta
   2. Productos
   3. Reportes
   4. Historial Ventas

Pestanas lazy (carga al primer clic):
   5. Registrar Gasto
   6. Cargar Lista
   7. Crear Boleta
   8. Comparar Mercados
   9. Faltantes

Ademas incluye un boton de Configuracion (⚙) que abre un dialogo
para ajustar tipo de cambio USD y margen de ganancia.
"""

import customtkinter as ctk

from src.presentation.register_sale_view import RegisterSaleView
from src.presentation.register_expense_view import RegisterExpenseView
from src.presentation.manage_products_view import ManageProductsView
from src.presentation.reports_view import ReportsView
from src.presentation.load_list_view import LoadListView
from src.presentation.sales_history_view import SalesHistoryView
from src.presentation.faltantes_view import FaltantesView
from src.presentation.crear_boleta_view import CrearBoletaView
from src.presentation.comparar_mercados_view import CompararMercadosView
from src.presentation.settings_dialog import SettingsDialog


_LAZY_TABS = frozenset({
    "Registrar Gasto",
    "Cargar Lista",
    "Crear Boleta",
    "Comparar Mercados",
    "Faltantes",
})

_EAGER_TABS = [
    "Registrar Venta",
    "Productos",
    "Reportes",
    "Historial Ventas",
]


class MainWindow(ctk.CTkTabview):
    """
    Ventana principal con pestanas y boton de configuracion.

    Las pestanas poco usadas se crean bajo demanda (lazy loading)
    para reducir el tiempo de inicio y el consumo de memoria.
    """

    def __init__(
        self,
        master,
        product_service,
        sale_service,
        expense_service,
        report_service,
        list_service,
        settings_service,
        missing_service,
    ):
        super().__init__(master)

        self._segmented_button.configure(font=("Arial", 11))

        # Crear pestanas — eager first, then lazy
        for name in _EAGER_TABS:
            self.add(name)
        self._tab_gasto = self.add("Registrar Gasto")
        self._tab_cargar = self.add("Cargar Lista")
        self._tab_boleta = self.add("Crear Boleta")
        self._tab_mercados = self.add("Comparar Mercados")
        self._tab_faltantes = self.add("Faltantes")

        self.tab_venta = self.tab("Registrar Venta")
        self.tab_productos = self.tab("Productos")
        self.tab_reportes = self.tab("Reportes")
        self.tab_historial = self.tab("Historial Ventas")

        # Instanciar vistas eager dentro de su pestana
        self._register_sale_view = RegisterSaleView(
            self.tab_venta, sale_service, product_service, settings_service
        )
        self._register_sale_view.pack(fill="both", expand=True)

        self._manage_products_view = ManageProductsView(
            self.tab_productos, product_service
        )
        self._manage_products_view.pack(fill="both", expand=True)

        self._reports_view = ReportsView(self.tab_reportes, report_service)
        self._reports_view.pack(fill="both", expand=True)

        self._sales_history_view = SalesHistoryView(
            self.tab_historial, sale_service
        )
        self._sales_history_view.pack(fill="both", expand=True)

        # Lazy view factory — evita closures problematicos
        self._lazy_kwargs = {
            "Registrar Gasto": dict(expense_service=expense_service, product_service=product_service),
            "Cargar Lista": dict(list_service=list_service, settings_service=settings_service),
            "Crear Boleta": dict(product_service=product_service),
            "Comparar Mercados": dict(product_service=product_service),
            "Faltantes": dict(missing_service=missing_service, product_service=product_service),
        }
        self._lazy_views_created = set()

        # Boton de configuracion en la barra de pestanas
        self._settings_btn = ctk.CTkButton(
            self._segmented_button,
            text="⚙",
            width=30,
            command=self._open_settings,
        )
        self._settings_btn.grid(row=0, column=999, padx=(0, 5), sticky="e")

        self._product_service = product_service
        self._settings_service = settings_service

    def set(self, tab_name):
        """Override para crear vistas lazy al seleccionar la pestana programaticamente."""
        super().set(tab_name)
        self._ensure_lazy_view(tab_name)

    def _segmented_button_callback(self, selected_name):
        """Override para crear vistas lazy al hacer clic en una pestana."""
        super()._segmented_button_callback(selected_name)
        self._ensure_lazy_view(selected_name)

    def _ensure_lazy_view(self, tab_name):
        if tab_name in self._lazy_views_created:
            return
        if tab_name not in _LAZY_TABS:
            return

        self._lazy_views_created.add(tab_name)
        parent = self.tab(tab_name)
        kwargs = self._lazy_kwargs[tab_name]

        if tab_name == "Registrar Gasto":
            view = RegisterExpenseView(parent, **kwargs)
        elif tab_name == "Cargar Lista":
            view = LoadListView(parent, **kwargs)
        elif tab_name == "Crear Boleta":
            view = CrearBoletaView(parent, **kwargs)
        elif tab_name == "Comparar Mercados":
            view = CompararMercadosView(parent, **kwargs)
        elif tab_name == "Faltantes":
            view = FaltantesView(parent, **kwargs)
        else:
            return

        view.pack(fill="both", expand=True)

    def _open_settings(self):
        """Abre el dialogo de configuracion (USD rate y margen)."""
        SettingsDialog(self, self._settings_service, self._product_service)
