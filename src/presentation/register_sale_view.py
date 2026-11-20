"""
CAPA DE PRESENTACION — Pestana: Registrar Venta.

Permite buscar productos por nombre (autocomplete), seleccionarlos,
especificar cantidad y agregarlos a una lista de items. Al finalizar,
registra la venta completa.

El precio usado para calcular es el unit_price del producto (precio
por unidad individual). Para productos en bulk (ej: bolsa de 100
tornillos), este precio es menor al selling_price.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from decimal import Decimal
from datetime import date, timedelta

from src.application.sale_service import SaleService
from src.application.product_service import ProductService
from src.application.settings_service import SettingsService
from src.presentation.pdf_boleta import generate_boleta_pdf, items_from_sale_view

_MAX_SEARCH_RESULTS = 20
_SEARCH_DEBOUNCE_MS = 250

# Columnas de resultados de busqueda: (id interno, titulo, ancho)
_RESULT_COLUMNS = (
    ("name", "Nombre", 320),
    ("supplier", "Proveedor", 130),
    ("price", "Precio", 100),
    ("list_date", "Lista", 100),
    ("unit", "Unidad", 70),
)

# Columnas de items de la venta: (id interno, titulo, ancho)
_ITEM_COLUMNS = (
    ("product", "Producto", 260),
    ("supplier", "Proveedor", 130),
    ("cost", "P. Proveedor", 110),
    ("list_date", "Lista", 100),
    ("qty", "Cant.", 70),
    ("price", "P. Unitario", 110),
    ("subtotal", "Subtotal", 110),
)


class RegisterSaleView(ctk.CTkFrame):
    """Formulario de registro de ventas con busqueda de productos."""

    def __init__(
        self, master, sale_service: SaleService,
        product_service: ProductService, settings_service: SettingsService,
    ):
        super().__init__(master)
        self._sale_service = sale_service
        self._product_service = product_service
        self._settings_service = settings_service
        self._sale_items = []  # Lista de (Product, cantidad, custom_unit_price_or_None)
        self._selected_product = None
        self._result_products = {}  # iid del Treeview -> Product
        self._item_iids = {}  # iid del Treeview -> indice en _sale_items
        self._search_after_id = None

        self._build_ui()

    def _build_ui(self):
        """Construye los widgets de la interfaz."""
        # Titulo
        title = ctk.CTkLabel(
            self, text="Registrar Nueva Venta", font=("Arial", 20, "bold")
        )
        title.pack(pady=10)

        # === Seccion de busqueda y seleccion de producto ===
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(search_frame, text="Buscar Producto:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )

        # Campo de texto para buscar (filtra resultados en tiempo real)
        self._search_entry = ctk.CTkEntry(search_frame, width=400)
        self._search_entry.grid(row=0, column=1, padx=5, pady=5)
        self._search_entry.bind("<KeyRelease>", self._schedule_search)
        self._search_entry.bind("<Return>", self._on_search)

        ctk.CTkLabel(search_frame, text="Proveedor:").grid(
            row=0, column=2, padx=(15, 2), pady=5
        )
        self._supplier_var = ctk.StringVar(value="Todos")
        self._supplier_combo = ctk.CTkComboBox(
            search_frame, values=["Todos"], variable=self._supplier_var,
            width=120, state="readonly",
        )
        self._supplier_combo.grid(row=0, column=3, padx=2, pady=5)
        self._supplier_var.trace_add("write", self._on_supplier_change)

        # Resultados de busqueda (se actualizan al escribir)
        self._results_frame = ctk.CTkFrame(search_frame)
        self._results_frame.grid(row=1, column=0, columnspan=7, sticky="ew", pady=2)

        self._results_note = ctk.CTkLabel(
            self._results_frame, text="", font=("Arial", 10, "italic"),
            text_color="gray",
        )
        self._results_note.pack(side="bottom", fill="x", padx=4)

        self._results_tree = ttk.Treeview(
            self._results_frame,
            columns=[c[0] for c in _RESULT_COLUMNS],
            show="headings",
            selectmode="browse",
            height=8,
        )
        for col_id, title, width in _RESULT_COLUMNS:
            self._results_tree.heading(col_id, text=title)
            self._results_tree.column(
                col_id, width=width, anchor="w", stretch=True
            )
        results_scroll = ttk.Scrollbar(
            self._results_frame, orient="vertical",
            command=self._results_tree.yview,
        )
        self._results_tree.configure(yscrollcommand=results_scroll.set)
        self._results_tree.pack(side="left", fill="both", expand=True)
        results_scroll.pack(side="right", fill="y")
        self._results_tree.bind("<<TreeviewSelect>>", self._on_result_select)
        self._results_tree.tag_configure("old", foreground="#c62828")
        search_frame.grid_columnconfigure(1, weight=1)

        # Cantidad a vender (en unidades, no paquetes)
        ctk.CTkLabel(search_frame, text="Cantidad:").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self._qty_entry = ctk.CTkEntry(search_frame, width=80)
        self._qty_entry.insert(0, "1")
        self._qty_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(search_frame, text="P. Unitario:").grid(
            row=2, column=2, padx=(15, 2), pady=5
        )
        self._unit_price_entry = ctk.CTkEntry(search_frame, width=120)
        self._unit_price_entry.grid(row=2, column=3, padx=2, pady=5)

        ctk.CTkLabel(search_frame, text="Cliente:").grid(
            row=2, column=4, padx=(15, 2), pady=5
        )
        self._customer_entry = ctk.CTkEntry(search_frame, width=150)
        self._customer_entry.grid(row=2, column=5, padx=2, pady=5)

        # Boton para agregar a la venta actual
        self._add_btn = ctk.CTkButton(
            search_frame,
            text="Agregar a Venta",
            command=self._add_item,
            state="disabled",
            width=140,
            height=35,
            font=("Arial", 13, "bold"),
        )
        self._add_btn.grid(row=2, column=6, padx=15, pady=5)

        # Informacion del producto seleccionado
        self._selected_info = ctk.CTkLabel(
            search_frame,
            text="",
            font=("Arial", 11),
            anchor="w",
        )
        self._selected_info.grid(
            row=3, column=0, columnspan=7, padx=5, pady=2, sticky="w"
        )

        # === Seccion de producto libre (sin catalogo) ===
        free_frame = ctk.CTkFrame(self)
        free_frame.pack(fill="x", padx=20, pady=2)

        ctk.CTkLabel(
            free_frame, text="Producto Libre:", font=("Arial", 13, "bold")
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(free_frame, text="Nombre:").grid(
            row=1, column=0, padx=5, pady=3, sticky="w"
        )
        self._free_name_entry = ctk.CTkEntry(free_frame, width=250)
        self._free_name_entry.insert(0, "Tornillos Varios")
        self._free_name_entry.grid(row=1, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(free_frame, text="Cantidad:").grid(
            row=1, column=2, padx=5, pady=3, sticky="w"
        )
        self._free_qty_entry = ctk.CTkEntry(free_frame, width=60)
        self._free_qty_entry.insert(0, "1")
        self._free_qty_entry.grid(row=1, column=3, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(free_frame, text="Precio Total:").grid(
            row=1, column=4, padx=5, pady=3, sticky="w"
        )
        self._free_price_entry = ctk.CTkEntry(free_frame, width=120)
        self._free_price_entry.grid(row=1, column=5, padx=5, pady=3, sticky="w")

        self._free_add_btn = ctk.CTkButton(
            free_frame,
            text="Agregar",
            command=self._add_free_item,
            fg_color="#1565c0",
            width=120,
            height=35,
            font=("Arial", 13),
        )
        self._free_add_btn.grid(row=1, column=6, padx=15, pady=5)

        # Linea separadora
        divider = ctk.CTkFrame(self, height=2, fg_color="#cccccc")
        divider.pack(fill="x", padx=20, pady=5)

        # === Tabla de items de la venta actual ===
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)

        item_toolbar = ctk.CTkFrame(table_frame)
        item_toolbar.pack(side="top", fill="x")
        self._remove_btn = ctk.CTkButton(
            item_toolbar,
            text="Quitar ítem",
            command=self._remove_selected_item,
            width=110,
            height=30,
            font=("Arial", 12),
        )
        self._remove_btn.pack(side="right", padx=4, pady=2)

        self._items_tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in _ITEM_COLUMNS],
            show="headings",
            selectmode="browse",
        )
        for col_id, title, width in _ITEM_COLUMNS:
            self._items_tree.heading(col_id, text=title)
            self._items_tree.column(col_id, width=width, anchor="w", stretch=True)
        items_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self._items_tree.yview
        )
        self._items_tree.configure(yscrollcommand=items_scroll.set)
        self._items_tree.pack(side="left", fill="both", expand=True)
        items_scroll.pack(side="right", fill="y")

        # === Barra inferior con total y botones ===
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=20, pady=10)

        self._total_label = ctk.CTkLabel(
            bottom,
            text="Total: $0.00",
            font=("Arial", 18, "bold"),
        )
        self._total_label.pack(side="left", padx=10)

        ctk.CTkButton(
            bottom, text="Cancelar", command=self._clear_sale,
            width=100, height=35, font=("Arial", 13),
        ).pack(side="right", padx=8)

        self._boleta_btn = ctk.CTkButton(
            bottom,
            text="Crear Boleta",
            command=self._export_boleta,
            fg_color="#1565c0",
            state="disabled",
            width=130,
            height=35,
            font=("Arial", 13),
        )
        self._boleta_btn.pack(side="right", padx=8)

        self._register_btn = ctk.CTkButton(
            bottom,
            text="Registrar Venta",
            command=self._register_sale,
            fg_color="#2e7d32",
            state="disabled",
            width=160,
            height=38,
            font=("Arial", 14, "bold"),
        )
        self._register_btn.pack(side="right", padx=8)

        self._load_suppliers()

    def _load_suppliers(self):
        suppliers = self._product_service.get_suppliers()
        vals = ["Todos"] + suppliers
        self._supplier_combo.configure(values=vals)

    def _on_supplier_change(self, *args):
        query = self._search_entry.get().strip()
        if query:
            self._do_search(query)

    def _schedule_search(self, event=None):
        """Programa una busqueda con debounce mientras el usuario escribe."""
        if event is not None and event.keysym == "Return":
            return
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(
            _SEARCH_DEBOUNCE_MS, self._run_scheduled_search
        )

    def _run_scheduled_search(self):
        self._search_after_id = None
        self._on_search()

    def _clear_results(self):
        for iid in self._results_tree.get_children():
            self._results_tree.delete(iid)
        self._result_products.clear()
        self._results_note.configure(text="")

    def _on_search(self, event=None):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None

        query = self._search_entry.get().strip()
        self._clear_results()

        if not query:
            self._selected_product = None
            self._selected_info.configure(text="")
            self._add_btn.configure(state="disabled")
            return

        self._do_search(query)

    def _do_search(self, query):
        current = self._search_entry.get().strip()
        if current != query:
            return
        supplier = self._supplier_var.get()
        supplier_filter = '' if supplier == 'Todos' else supplier
        matches = self._product_service.search_products(query, supplier_filter, limit=_MAX_SEARCH_RESULTS + 1)

        self._clear_results()

        if not matches:
            self._results_note.configure(text="Sin resultados")
            self._search_entry.focus_set()
            return

        # Si la busqueda contiene "bulon", mostrar "enfer" primero
        if "bulon" in query.lower():
            matches.sort(key=lambda p: (p.supplier.lower() != "enfer", p.name.lower()))

        cutoff = date.today() - timedelta(days=61)
        for product in matches[:_MAX_SEARCH_RESULTS]:
            up = self._product_unit_price(product)
            tags = ("old",) if product.list_date < cutoff else ()
            iid = self._results_tree.insert(
                "",
                "end",
                values=(
                    product.name,
                    product.supplier,
                    f"${up:,.2f}",
                    str(product.list_date),
                    str(product.unit_quantity),
                ),
                tags=tags,
            )
            self._result_products[iid] = product

        if len(matches) > _MAX_SEARCH_RESULTS:
            self._results_note.configure(
                text="... y mas resultados. Sea mas especifico."
            )

        self._search_entry.focus_set()

    def _on_result_select(self, event=None):
        selection = self._results_tree.selection()
        if not selection:
            return
        product = self._result_products.get(selection[0])
        if product is not None:
            self._select_result(product)

    def _select_result(self, product):
        """Selecciona un producto de los resultados de busqueda."""
        self._selected_product = product
        self._search_entry.delete(0, "end")
        self._search_entry.insert(0, product.name)

        # Prellenar precio unitario
        up = self._product_unit_price(product)
        self._unit_price_entry.delete(0, "end")
        self._unit_price_entry.insert(0, f"{up:,.2f}")

        # Mostrar informacion detallada del producto
        info = (
            f"Codigo: {product.code}  |  "
            f"P. Proveedor: ${product.supplier_price:,.2f}  |  "
            f"P. Venta: ${product.selling_price:,.2f}  |  "
            f"P. Unitario: ${up:,.2f}  |  "
            f"Stock: {product.unit_quantity} ud. x paquete  |  "
            f"Lista: {product.list_date}"
        )
        self._selected_info.configure(text=info)
        self._add_btn.configure(state="normal")

    @staticmethod
    def _product_unit_price(product) -> Decimal:
        return product.selling_price if product.unit_quantity <= 1 else product.unit_price

    def _get_custom_unit_price(self) -> Decimal:
        try:
            raw = self._unit_price_entry.get().strip()
            if not raw:
                return Decimal("0")
            return Decimal(raw.replace(",", ""))
        except Exception:
            return Decimal("0")

    def _add_item(self):
        """Agrega el producto seleccionado a la lista de items de la venta."""
        if not self._selected_product:
            messagebox.showwarning(
                "Advertencia", "Seleccione un producto de la busqueda"
            )
            return

        try:
            qty = Decimal(self._qty_entry.get().replace(",", "."))
            if qty <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning(
                "Advertencia", "Ingrese una cantidad valida mayor a cero"
            )
            return

        custom_price = self._get_custom_unit_price()
        if custom_price <= 0:
            messagebox.showwarning(
                "Advertencia", "Ingrese un precio unitario valido mayor a cero"
            )
            return

        self._sale_items.append((self._selected_product, qty, custom_price))
        self._render_items()

        # Resetear seleccion
        self._selected_product = None
        self._selected_info.configure(text="")
        self._add_btn.configure(state="disabled")
        self._search_entry.delete(0, "end")
        self._qty_entry.delete(0, "end")
        self._qty_entry.insert(0, "1")
        self._unit_price_entry.delete(0, "end")
        self._clear_results()

    def _add_free_item(self):
        name = self._free_name_entry.get().strip()
        if not name:
            name = "Tornillos Varios"

        try:
            qty = Decimal(self._free_qty_entry.get().replace(",", "."))
            if qty <= 0:
                qty = Decimal("1")
        except Exception:
            qty = Decimal("1")

        try:
            total_price = Decimal(self._free_price_entry.get().replace(",", ""))
            if total_price <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Advertencia", "Ingrese un precio total valido")
            return

        unit_price = (total_price / Decimal(str(qty))).quantize(Decimal("0.01"))

        # Estimar el costo a partir del margen de ganancia actual
        margin = self._settings_service.get_profit_margin()  # ej: 160
        margin_mult = Decimal(str(margin)) / Decimal("100")  # ej: 1.6
        estimated_cost = (unit_price / margin_mult).quantize(Decimal("0.01"))

        # Create in-memory product (id=0 marca que no esta en DB)
        from datetime import date
        from src.domain.entities import Product
        product = Product(
            name=name,
            category="",
            supplier="Generico",
            list_date=date.today(),
            supplier_price=estimated_cost,
            selling_price=unit_price,
            unit_quantity=1,
            unit_price=unit_price,
            price_usd=Decimal("0"),
            selling_price_usd=Decimal("0"),
            code='',
        )

        self._sale_items.append((product, qty, unit_price))
        self._render_items()

        self._free_name_entry.delete(0, "end")
        self._free_name_entry.insert(0, "Tornillos Varios")
        self._free_qty_entry.delete(0, "end")
        self._free_qty_entry.insert(0, "1")
        self._free_price_entry.delete(0, "end")

    def _render_items(self):
        """Renderiza la tabla de productos en la venta actual."""
        for iid in self._items_tree.get_children():
            self._items_tree.delete(iid)
        self._item_iids.clear()

        total = Decimal("0")
        for i, (product, qty, custom_price) in enumerate(self._sale_items):
            up = custom_price if custom_price else self._product_unit_price(product)
            subtotal = up * qty
            total += subtotal

            iid = self._items_tree.insert(
                "",
                "end",
                values=(
                    product.name,
                    product.supplier,
                    f"${product.supplier_price:,.2f}",
                    str(product.list_date),
                    str(qty),
                    f"${up:,.2f}",
                    f"${subtotal:,.2f}",
                ),
            )
            self._item_iids[iid] = i

        self._total_label.configure(text=f"Total: ${total:,.2f}")
        state = "normal" if self._sale_items else "disabled"
        self._register_btn.configure(state=state)
        self._boleta_btn.configure(state=state)

    def _remove_selected_item(self):
        """Elimina el item seleccionado en la tabla de la venta actual."""
        selection = self._items_tree.selection()
        if not selection:
            return
        index = self._item_iids.get(selection[0])
        if index is None or not (0 <= index < len(self._sale_items)):
            return
        self._sale_items.pop(index)
        self._render_items()

    def _clear_sale(self):
        """Limpia todos los items de la venta actual."""
        self._sale_items.clear()
        self._selected_product = None
        self._selected_info.configure(text="")
        self._add_btn.configure(state="disabled")
        self._search_entry.delete(0, "end")
        self._qty_entry.delete(0, "end")
        self._qty_entry.insert(0, "1")
        self._unit_price_entry.delete(0, "end")
        self._customer_entry.delete(0, "end")
        self._render_items()

    def _export_boleta(self):
        if not self._sale_items:
            return

        from datetime import date
        client = self._customer_entry.get().strip()
        client_name = client or "Consumidor Final"
        safe_name = "".join(c for c in client_name if c.isalnum() or c in " _-")[:40]
        path = filedialog.asksaveasfilename(
            title="Guardar Boleta PDF",
            defaultextension=".pdf",
            initialfile=f"Boleta {safe_name}.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return

        pdf_items = items_from_sale_view(self._sale_items)
        try:
            generate_boleta_pdf(path, pdf_items, client, date.today().isoformat())
            messagebox.showinfo("Exportado", f"Boleta guardada en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el PDF:\n{str(e)}")

    def _register_sale(self):
        """Persiste la venta en la base de datos."""
        if not self._sale_items:
            return

        try:
            items_data = []
            unit_prices = []
            for product, qty, custom_price in self._sale_items:
                if product.id is None or product.id == 0:
                    product = self._product_service.create_product(
                        name=product.name,
                        category=product.category,
                        supplier=product.supplier,
                        list_date=product.list_date,
                        supplier_price=product.supplier_price,
                        selling_price=product.selling_price,
                        unit_quantity=product.unit_quantity,
                        unit_price=product.unit_price,
                        price_usd=product.price_usd,
                        selling_price_usd=product.selling_price_usd,
                        code=product.code,
                    )
                items_data.append((product.id, qty))
                unit_prices.append(custom_price if custom_price else None)

            customer = self._customer_entry.get().strip()
            sale = self._sale_service.record_sale(items_data, customer, unit_prices)
            msg = f"Venta registrada correctamente.\nTotal: ${sale.total_amount:,.2f}"
            if customer:
                msg += f"\nCliente: {customer}"
            messagebox.showinfo("Exito", msg)
            self._clear_sale()
        except Exception as e:
            messagebox.showerror("Error", str(e))
