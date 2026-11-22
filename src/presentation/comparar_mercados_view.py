import customtkinter as ctk
from decimal import Decimal
from datetime import date, timedelta
from tkinter import ttk
from typing import List

from src.application.product_service import ProductService
from src.domain.entities import Product


SORT_OPTIONS = {
    "Producto": "name",
    "Proveedor": "supplier",
    "Precio Proveedor": "supplier_price",
    "Precio Venta": "selling_price",
    "P. Unitario": "unit_price",
    "Fecha Lista": "list_date",
}

# Columnas de la tabla de resultados: (id interno, titulo, ancho)
_RESULT_COLUMNS = (
    ("name", "Producto", 260),
    ("supplier", "Proveedor", 130),
    ("category", "Categoria", 100),
    ("sp", "P. Proveedor", 120),
    ("sv", "P. Venta", 120),
    ("up", "P. Unitario", 100),
    ("ld", "Fecha Lista", 100),
)


class CompararMercadosView(ctk.CTkFrame):
    def __init__(self, master, product_service: ProductService):
        super().__init__(master)
        self._product_service = product_service
        self._sort_key = "name"
        self._sort_reverse = False
        self._current_results: List[Product] = []
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text="Comparar Mercados", font=("Arial", 20, "bold")
        )
        title.pack(pady=10)

        # === Busqueda ===
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(search_frame, text="Buscar producto:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self._search_entry = ctk.CTkEntry(search_frame, width=350)
        self._search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self._search_entry.bind("<Return>", self._on_search)

        ctk.CTkLabel(search_frame, text="Proveedor:").grid(
            row=0, column=2, padx=(15, 2), pady=5
        )
        self._supplier_var = ctk.StringVar(value="Todos")
        self._supplier_combo = ctk.CTkComboBox(
            search_frame, values=["Todos"], variable=self._supplier_var,
            width=130, state="readonly",
        )
        self._supplier_combo.grid(row=0, column=3, padx=2, pady=5)
        self._supplier_var.trace_add("write", self._on_filter_change)

        ctk.CTkLabel(search_frame, text="Ordenar por:").grid(
            row=0, column=4, padx=(15, 2), pady=5
        )
        self._sort_var = ctk.StringVar(value="Producto")
        self._sort_combo = ctk.CTkComboBox(
            search_frame, values=list(SORT_OPTIONS.keys()),
            variable=self._sort_var, width=140, state="readonly",
        )
        self._sort_combo.grid(row=0, column=5, padx=2, pady=5)
        self._sort_var.trace_add("write", self._on_sort_change)

        ctk.CTkLabel(search_frame, text="Orden:").grid(
            row=0, column=6, padx=(10, 2), pady=5
        )
        self._order_var = ctk.StringVar(value="Ascendente")
        self._order_combo = ctk.CTkComboBox(
            search_frame, values=["Ascendente", "Descendente"],
            variable=self._order_var, width=110, state="readonly",
        )
        self._order_combo.grid(row=0, column=7, padx=2, pady=5)
        self._order_var.trace_add("write", self._on_sort_change)

        # === Tabla de resultados ===
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self._results_tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in _RESULT_COLUMNS],
            show="headings",
            selectmode="browse",
        )
        for col_id, title, width in _RESULT_COLUMNS:
            self._results_tree.heading(col_id, text=title)
            self._results_tree.column(col_id, width=width, anchor="w", stretch=True)
        self._results_tree.tag_configure("old", foreground="#c62828")

        tree_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self._results_tree.yview
        )
        self._results_tree.configure(yscrollcommand=tree_scroll.set)
        self._results_tree.pack(side="left", fill="both", expand=True, pady=2)
        tree_scroll.pack(side="right", fill="y", pady=2)

        # Info label
        self._info_label = ctk.CTkLabel(
            self, text="Ingrese un termino de busqueda para comenzar",
            font=("Arial", 11, "italic"), text_color="#757575",
        )
        self._info_label.pack(pady=5)

        self._load_suppliers()

    def _load_suppliers(self):
        suppliers = self._product_service.get_suppliers()
        self._supplier_combo.configure(values=["Todos"] + suppliers)

    def _on_search(self, event=None):
        query = self._search_entry.get().strip()
        if not query:
            self._current_results.clear()
            self._render_results()
            return
        self._do_search(query)

    def _on_filter_change(self, *args):
        query = self._search_entry.get().strip()
        if query:
            self._do_search(query)

    def _on_sort_change(self, *args):
        if self._current_results:
            self._sort_and_render()

    def _do_search(self, query):
        current = self._search_entry.get().strip()
        if current != query:
            return
        supplier = self._supplier_var.get()
        supplier_filter = '' if supplier == 'Todos' else supplier
        self._current_results = self._product_service.search_products(query, supplier_filter)
        self._sort_and_render()
        self._search_entry.focus_set()

    def _sort_and_render(self):
        if not self._current_results:
            self._render_results()
            return
        sort_field = SORT_OPTIONS.get(self._sort_var.get(), "name")
        self._sort_reverse = self._order_var.get() == "Descendente"

        def sort_key(p):
            val = getattr(p, sort_field, "")
            if sort_field in ("supplier_price", "selling_price", "unit_price"):
                return val if isinstance(val, Decimal) else Decimal(str(val))
            if sort_field == "list_date":
                return str(val) if val else ""
            return str(val).lower() if val else ""

        self._current_results.sort(key=sort_key, reverse=self._sort_reverse)
        self._render_results()

    def _render_results(self):
        for iid in self._results_tree.get_children():
            self._results_tree.delete(iid)

        if not self._current_results:
            self._info_label.configure(
                text="Sin resultados. Intente con otro termino de busqueda."
            )
            return

        self._info_label.configure(
            text=f"{len(self._current_results)} producto(s) encontrado(s)"
        )

        cutoff = date.today() - timedelta(days=61)
        for product in self._current_results:
            tags = ("old",) if product.list_date < cutoff else ()
            self._results_tree.insert(
                "",
                "end",
                values=(
                    product.name,
                    product.supplier,
                    product.category,
                    f"${product.supplier_price:,.2f}",
                    f"${product.selling_price:,.2f}",
                    f"${product.unit_price:,.2f}",
                    str(product.list_date),
                ),
                tags=tags,
            )
