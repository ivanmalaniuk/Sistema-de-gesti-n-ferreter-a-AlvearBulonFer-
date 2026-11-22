import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import date, timedelta

from src.application.missing_item_service import MissingItemService
from src.application.product_service import ProductService


# Columnas del resultado de busqueda en catalogo: (id interno, titulo, ancho)
_RESULT_COLUMNS = (
    ("name", "Articulo", 300),
    ("supplier", "Proveedor", 150),
    ("list_date", "Lista", 120),
)

# Columnas de la lista de faltantes: (id interno, titulo, ancho)
_ITEM_COLUMNS = (
    ("name", "Articulo", 260),
    ("supplier", "Proveedor", 140),
    ("notes", "Notas", 200),
    ("created", "Fecha", 120),
)


class FaltantesView(ctk.CTkFrame):
    def __init__(self, master, missing_service: MissingItemService, product_service: ProductService):
        super().__init__(master)
        self._missing_service = missing_service
        self._product_service = product_service
        self._result_products = {}  # iid del Treeview -> Product
        self._items_by_iid = {}  # iid del Treeview -> item faltante
        self._selected_item_id = None
        self._build_ui()
        self.bind("<Map>", lambda e: self._refresh_list())

    def _build_ui(self):
        title = ctk.CTkLabel(self, text="Articulos Faltantes", font=("Arial", 20, "bold"))
        title.pack(pady=10)

        # === Seccion: agregar desde catalogo ===
        catalog_frame = ctk.CTkFrame(self)
        catalog_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(catalog_frame, text="Agregar desde Catalogo:", font=("Arial", 13, "bold")).grid(
            row=0, column=0, columnspan=4, padx=5, pady=5, sticky="w"
        )

        ctk.CTkLabel(catalog_frame, text="Buscar:").grid(row=1, column=0, padx=5, pady=3, sticky="w")
        self._search_entry = ctk.CTkEntry(catalog_frame, width=300)
        self._search_entry.grid(row=1, column=1, padx=5, pady=3, sticky="w")
        self._search_entry.bind("<Return>", self._on_search)

        results_wrap = ctk.CTkFrame(catalog_frame)
        results_wrap.grid(row=2, column=0, columnspan=4, sticky="ew", pady=2, padx=5)

        self._search_results_tree = ttk.Treeview(
            results_wrap,
            columns=[c[0] for c in _RESULT_COLUMNS],
            show="headings",
            selectmode="browse",
            height=6,
        )
        for col_id, title, width in _RESULT_COLUMNS:
            self._search_results_tree.heading(col_id, text=title)
            self._search_results_tree.column(col_id, width=width, anchor="w", stretch=True)
        self._search_results_tree.tag_configure("old", foreground="#c62828")
        self._search_results_tree.bind("<<TreeviewSelect>>", self._on_result_select)

        results_scroll = ttk.Scrollbar(
            results_wrap, orient="vertical", command=self._search_results_tree.yview
        )
        self._search_results_tree.configure(yscrollcommand=results_scroll.set)
        self._search_results_tree.pack(side="left", fill="both", expand=True)
        results_scroll.pack(side="right", fill="y")

        self._search_info_label = ctk.CTkLabel(
            catalog_frame, text="", font=("Arial", 10, "italic"),
        )
        self._search_info_label.grid(row=3, column=0, columnspan=4, sticky="w", padx=5)

        # === Seccion: agregar manualmente ===
        manual_frame = ctk.CTkFrame(self)
        manual_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(manual_frame, text="Agregar Manualmente:", font=("Arial", 13, "bold")).grid(
            row=0, column=0, columnspan=4, padx=5, pady=5, sticky="w"
        )

        ctk.CTkLabel(manual_frame, text="Articulo:").grid(row=1, column=0, padx=5, pady=3, sticky="w")
        self._name_entry = ctk.CTkEntry(manual_frame, width=300)
        self._name_entry.grid(row=1, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(manual_frame, text="Proveedor:").grid(row=1, column=2, padx=(15, 2), pady=3, sticky="w")
        self._supplier_entry = ctk.CTkEntry(manual_frame, width=150)
        self._supplier_entry.grid(row=1, column=3, padx=2, pady=3, sticky="w")

        ctk.CTkLabel(manual_frame, text="Notas:").grid(row=2, column=0, padx=5, pady=3, sticky="w")
        self._notes_entry = ctk.CTkEntry(manual_frame, width=300)
        self._notes_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        self._add_manual_btn = ctk.CTkButton(
            manual_frame, text="Agregar", command=self._add_manual,
            fg_color="#1565c0", width=130, height=35,
            font=("Arial", 13),
        )
        self._add_manual_btn.grid(row=2, column=3, padx=15, pady=5)

        # === Lista de faltantes actuales ===
        divider = ctk.CTkFrame(self, height=2, fg_color="#cccccc")
        divider.pack(fill="x", padx=20, pady=5)

        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)

        actions = ctk.CTkFrame(list_frame, fg_color="transparent")
        actions.pack(side="bottom", fill="x", pady=(0, 5))

        self._empty_label = ctk.CTkLabel(
            actions, text="", font=("Arial", 11, "italic"),
        )
        self._empty_label.pack(side="left", padx=5)

        self._delete_btn = ctk.CTkButton(
            actions, text="Eliminar seleccionado", fg_color="#c62828",
            width=150, height=28, font=("Arial", 11), state="disabled",
            command=self._delete_selected,
        )
        self._delete_btn.pack(side="right", padx=5)

        tree_wrap = ctk.CTkFrame(list_frame)
        tree_wrap.pack(fill="both", expand=True, pady=5)

        self._items_tree = ttk.Treeview(
            tree_wrap,
            columns=[c[0] for c in _ITEM_COLUMNS],
            show="headings",
            selectmode="browse",
        )
        for col_id, title, width in _ITEM_COLUMNS:
            self._items_tree.heading(col_id, text=title)
            self._items_tree.column(col_id, width=width, anchor="w", stretch=True)

        items_scroll = ttk.Scrollbar(
            tree_wrap, orient="vertical", command=self._items_tree.yview
        )
        self._items_tree.configure(yscrollcommand=items_scroll.set)
        self._items_tree.pack(side="left", fill="both", expand=True)
        items_scroll.pack(side="right", fill="y")
        self._items_tree.bind("<<TreeviewSelect>>", self._on_item_select)

    def _on_search(self, event=None):
        query = self._search_entry.get().strip()
        self._clear_results()
        if not query:
            return
        self._do_search(query)

    def _clear_results(self):
        for iid in self._search_results_tree.get_children():
            self._search_results_tree.delete(iid)
        self._result_products.clear()
        self._search_info_label.configure(text="")

    def _do_search(self, query):
        current = self._search_entry.get().strip()
        if current != query:
            return
        matches = self._product_service.search_products(query)
        if not matches:
            self._search_info_label.configure(text="Sin resultados")
            self._search_entry.focus_set()
            return
        cutoff = date.today() - timedelta(days=61)
        for product in matches:
            tags = ("old",) if product.list_date < cutoff else ()
            iid = self._search_results_tree.insert(
                "",
                "end",
                values=(product.name, product.supplier, str(product.list_date)),
                tags=tags,
            )
            self._result_products[iid] = product
        self._search_entry.focus_set()

    def _on_result_select(self, event=None):
        selection = self._search_results_tree.selection()
        if not selection:
            return
        product = self._result_products.get(selection[0])
        if product is not None:
            self._add_from_catalog(product)

    def _add_from_catalog(self, product):
        try:
            self._missing_service.add_item(
                name=product.name,
                supplier=product.supplier,
                notes=f"Cod: {product.code}  Lista: {product.list_date}",
            )
            self._search_entry.delete(0, "end")
            self._clear_results()
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _add_manual(self):
        name = self._name_entry.get().strip()
        if not name:
            messagebox.showwarning("Advertencia", "Ingrese el nombre del articulo")
            return
        try:
            self._missing_service.add_item(
                name=name,
                supplier=self._supplier_entry.get().strip(),
                notes=self._notes_entry.get().strip(),
            )
            self._name_entry.delete(0, "end")
            self._supplier_entry.delete(0, "end")
            self._notes_entry.delete(0, "end")
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _refresh_list(self):
        for iid in self._items_tree.get_children():
            self._items_tree.delete(iid)
        self._items_by_iid.clear()
        self._selected_item_id = None
        self._delete_btn.configure(state="disabled")

        items = self._missing_service.get_all_items()
        if not items:
            self._empty_label.configure(
                text="No hay articulos faltantes registrados"
            )
            return
        self._empty_label.configure(text="")
        for item in items:
            created = item.created_at.strftime("%d/%m/%Y") if item.created_at else ""
            iid = self._items_tree.insert(
                "",
                "end",
                values=(item.name, item.supplier, item.notes, created),
            )
            self._items_by_iid[iid] = item

    def _on_item_select(self, event=None):
        selection = self._items_tree.selection()
        if not selection:
            self._selected_item_id = None
            self._delete_btn.configure(state="disabled")
            return
        item = self._items_by_iid.get(selection[0])
        self._selected_item_id = item.id if item else None
        self._delete_btn.configure(
            state="normal" if self._selected_item_id is not None else "disabled"
        )

    def _delete_selected(self):
        if self._selected_item_id is None:
            return
        try:
            self._missing_service.delete_item(self._selected_item_id)
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))
