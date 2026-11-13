"""
CAPA DE PRESENTACION — Pestana: Productos.

Administracion completa del catalogo de productos:
- Tabla con todos los productos (ordenados alfabeticamente)
- Campo de busqueda para filtrar
- Formulario completo con todos los campos del producto
- Botones: Agregar, Editar, Eliminar, Recalcular, Limpiar

El boton "Recalcular" actualiza los precios del producto seleccionado
usando el margen de ganancia y tipo de cambio USD actuales.
"""

import customtkinter as ctk
from tkinter import messagebox
from datetime import date
from decimal import Decimal, InvalidOperation

from src.application.product_service import ProductService
from src.presentation.wheel_scroll import register_scrollable


MAX_DISPLAY_ALL = 50
MAX_DISPLAY_SEARCH = 50


class ManageProductsView(ctk.CTkFrame):
    """CRUD de productos con tabla, busqueda y formulario."""

    def __init__(self, master, product_service: ProductService):
        super().__init__(master)
        self._product_service = product_service
        self._selected_id = None  # ID del producto seleccionado en la tabla
        self._build_ui()
        self.bind("<Map>", lambda e: self._on_tab_shown())
        self._load_suppliers()
        self._refresh_table()

    def _build_ui(self):
        """Construye la interfaz con tabla, busqueda y formulario."""
        title = ctk.CTkLabel(
            self, text="Gestion de Productos", font=("Arial", 20, "bold")
        )
        title.pack(pady=10)

        # === Barra de herramientas (busqueda) ===
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(toolbar, text="Buscar:").pack(side="left", padx=5)
        self._search_entry = ctk.CTkEntry(toolbar, width=300)
        self._search_entry.pack(side="left", padx=5)
        self._search_entry.bind("<Return>", self._on_search_key)

        ctk.CTkLabel(toolbar, text="Proveedor:").pack(side="left", padx=(15, 2))
        self._supplier_var = ctk.StringVar(value="Todos")
        self._supplier_combo = ctk.CTkComboBox(
            toolbar, values=["Todos"], variable=self._supplier_var,
            width=120, state="readonly",
        )
        self._supplier_combo.pack(side="left", padx=2)
        self._supplier_var.trace_add("write", self._on_supplier_change)

        self._delete_supplier_btn = ctk.CTkButton(
            toolbar, text="Borrar por proveedor",
            command=self._delete_by_supplier,
            fg_color="#c62828",
            width=170, height=32,
            font=("Arial", 12),
        )
        self._delete_supplier_btn.pack(side="right", padx=8)

        self._refresh_btn = ctk.CTkButton(
            toolbar, text="Refrescar", command=self._refresh_table,
            width=100, height=32, font=("Arial", 12),
        )
        self._refresh_btn.pack(side="right", padx=8)

        # === Tabla de productos ===
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)

        headers = [
            "Nombre",
            "Categoria",
            "Proveedor",
            "P. Proveedor",
            "P. Venta",
            "Ud. x Paq.",
            "P. Unitario",
        ]
        for col, h in enumerate(headers):
            ctk.CTkLabel(table_frame, text=h, font=("Arial", 11, "bold")).grid(
                row=0,
                column=col,
                padx=3,
                pady=2,
                sticky="w",
            )
            table_frame.grid_columnconfigure(col, weight=1)

        self._scroll = ctk.CTkScrollableFrame(table_frame)
        self._scroll.grid(
            row=1, column=0, columnspan=len(headers), sticky="nsew", pady=5
        )
        register_scrollable(self._scroll)
        table_frame.grid_rowconfigure(1, weight=1)

        # === Formulario de producto (edicion/creacion) ===
        form = ctk.CTkScrollableFrame(self)
        form.pack(fill="x", padx=20, pady=5)
        register_scrollable(form)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)

        # Fila 0: Nombre, Codigo
        ctk.CTkLabel(form, text="Nombre:").grid(
            row=0, column=0, padx=5, pady=3, sticky="w"
        )
        self._name_entry = ctk.CTkEntry(form, width=250)
        self._name_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")

        ctk.CTkLabel(form, text="Codigo:").grid(
            row=0, column=2, padx=5, pady=3, sticky="w"
        )
        self._code_entry = ctk.CTkEntry(form, width=200)
        self._code_entry.grid(row=0, column=3, padx=5, pady=3, sticky="ew")

        # Fila 1: Categoria, Proveedor
        ctk.CTkLabel(form, text="Categoria:").grid(
            row=1, column=0, padx=5, pady=3, sticky="w"
        )
        self._cat_entry = ctk.CTkEntry(form, width=200)
        self._cat_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")

        ctk.CTkLabel(form, text="Proveedor:").grid(
            row=1, column=2, padx=5, pady=3, sticky="w"
        )
        self._supplier_entry = ctk.CTkEntry(form, width=250)
        self._supplier_entry.grid(row=1, column=3, padx=5, pady=3, sticky="ew")

        # Fila 2: Fecha Lista
        ctk.CTkLabel(form, text="Fecha Lista:").grid(
            row=2, column=0, padx=5, pady=3, sticky="w"
        )
        self._date_entry = ctk.CTkEntry(form, width=150)
        self._date_entry.insert(0, date.today().isoformat())
        self._date_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        # Fila 3: Precio Proveedor, Precio Venta
        ctk.CTkLabel(form, text="P. Proveedor ($):").grid(
            row=3, column=0, padx=5, pady=3, sticky="w"
        )
        self._sp_entry = ctk.CTkEntry(form, width=120)
        self._sp_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        # Auto-calcular precio de venta al escribir precio proveedor
        self._sp_entry.bind("<KeyRelease>", lambda e: self._auto_calc())

        ctk.CTkLabel(form, text="P. Venta ($):").grid(
            row=2, column=2, padx=5, pady=3, sticky="w"
        )
        self._sv_entry = ctk.CTkEntry(form, width=120)
        self._sv_entry.grid(row=2, column=3, padx=5, pady=3, sticky="w")

        # Fila 4: Cantidad x Paquete, Precio Unitario
        ctk.CTkLabel(form, text="Cant. x Paquete:").grid(
            row=4, column=0, padx=5, pady=3, sticky="w"
        )
        self._uq_entry = ctk.CTkEntry(form, width=80)
        self._uq_entry.insert(0, "1")
        self._uq_entry.grid(row=4, column=1, padx=5, pady=3, sticky="w")
        # Recalcular precio unitario al cambiar cantidad
        self._uq_entry.bind("<KeyRelease>", lambda e: self._auto_calc())

        ctk.CTkLabel(form, text="P. Unitario ($):").grid(
            row=4, column=2, padx=5, pady=3, sticky="w"
        )
        self._up_entry = ctk.CTkEntry(form, width=120)
        self._up_entry.grid(row=4, column=3, padx=5, pady=3, sticky="w")

        # Fila 5: Precio USD, Venta USD
        ctk.CTkLabel(form, text="Precio USD:").grid(
            row=5, column=0, padx=5, pady=3, sticky="w"
        )
        self._usd_entry = ctk.CTkEntry(form, width=120)
        self._usd_entry.grid(row=5, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(form, text="Venta USD:").grid(
            row=5, column=2, padx=5, pady=3, sticky="w"
        )
        self._susd_entry = ctk.CTkEntry(form, width=120)
        self._susd_entry.grid(row=5, column=3, padx=5, pady=3, sticky="w")

        # Fila 6: Botones de accion
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=4, pady=10)

        btn_kw = dict(width=110, height=35, font=("Arial", 13))
        self._add_btn = ctk.CTkButton(
            btn_frame,
            text="Agregar",
            command=self._add_product,
            fg_color="#2e7d32",
            **btn_kw,
        )
        self._add_btn.pack(side="left", padx=8)

        self._edit_btn = ctk.CTkButton(
            btn_frame,
            text="Editar",
            command=self._edit_product,
            state="disabled",
            **btn_kw,
        )
        self._edit_btn.pack(side="left", padx=8)

        self._delete_btn = ctk.CTkButton(
            btn_frame,
            text="Eliminar",
            command=self._delete_product,
            fg_color="#c62828",
            state="disabled",
            **btn_kw,
        )
        self._delete_btn.pack(side="left", padx=8)

        self._recalc_btn = ctk.CTkButton(
            btn_frame,
            text="Recalcular",
            command=self._recalc_selected,
            state="disabled",
            **btn_kw,
        )
        self._recalc_btn.pack(side="left", padx=8)

        self._clear_btn = ctk.CTkButton(
            btn_frame, text="Limpiar", command=self._clear_form, **btn_kw,
        )
        self._clear_btn.pack(side="left", padx=8)

    def _auto_calc(self):
        """
        Auto-calcula precio de venta y unitario cuando el usuario
        modifica el precio proveedor o la cantidad por paquete.
        Usa el margen por defecto (160%) como referencia rapida.
        """
        try:
            sp = Decimal(self._sp_entry.get().strip() or "0")
            uq = int(self._uq_entry.get().strip() or "1")
        except Exception:
            return
        if sp > 0:
            sv = sp * Decimal("1.6")
            self._sv_entry.delete(0, "end")
            self._sv_entry.insert(0, str(sv.quantize(Decimal("0.01"))))
            if uq > 1:
                up = sv / Decimal(uq)
                self._up_entry.delete(0, "end")
                self._up_entry.insert(0, str(up.quantize(Decimal("0.01"))))

    def _on_tab_shown(self):
        self._load_suppliers()

    def _load_suppliers(self):
        """Carga la lista de proveedores en el combo."""
        suppliers = self._product_service.get_suppliers()
        vals = ["Todos"] + suppliers
        current = self._supplier_var.get()
        self._supplier_combo.configure(values=vals)
        if current not in vals:
            self._supplier_var.set("Todos")

    def _on_supplier_change(self, *args):
        self._refresh_table()

    def _delete_by_supplier(self):
        supplier = self._supplier_var.get()
        if not supplier or supplier == "Todos":
            messagebox.showwarning("Advertencia", "Seleccione un proveedor en el filtro")
            return
        if not messagebox.askyesno(
            "Confirmar",
            f"¿Eliminar TODOS los productos del proveedor '{supplier}'?\n"
            "Esta accion no se puede deshacer.",
        ):
            return
        try:
            deleted = self._product_service.delete_products_by_supplier(supplier)
            messagebox.showinfo("Eliminado", f"Se eliminaron {deleted} productos de '{supplier}'")
            self._load_suppliers()
            self._supplier_var.set("Todos")
            self._refresh_table()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_search_key(self, event=None):
        self._refresh_table()

    def _refresh_table(self):
        """Actualiza la tabla con los productos (filtrados por busqueda y proveedor)."""
        for w in self._scroll.winfo_children():
            w.destroy()

        query = self._search_entry.get().strip()
        supplier = self._supplier_var.get()
        supplier_filter = '' if supplier == 'Todos' else supplier
        is_filtered = bool(query) or supplier_filter != ''
        fetch_limit = MAX_DISPLAY_SEARCH if is_filtered else MAX_DISPLAY_ALL
        products = self._product_service.search_products(query, supplier_filter, limit=fetch_limit + 1)

        total = len(products)
        display = products[:fetch_limit]

        for product in display:
            row = ctk.CTkFrame(self._scroll)
            row.pack(fill="x", pady=1)
            row.bind("<Button-1>", lambda e, p=product: self._select_product(p))

            up = (
                product.selling_price
                if product.unit_quantity <= 1
                else product.unit_price
            )
            vals = [
                product.name,
                product.category,
                product.supplier,
                f"${product.supplier_price:,.2f}",
                f"${product.selling_price:,.2f}",
                str(product.unit_quantity) if product.unit_quantity > 1 else "-",
                f"${up:,.2f}",
            ]
            for v in vals:
                lbl = ctk.CTkLabel(row, text=str(v), anchor="w")
                lbl.pack(side="left", padx=3, fill="x", expand=True)
                lbl.bind("<Button-1>", lambda e, p=product: self._select_product(p))

        if total > fetch_limit:
            ctk.CTkLabel(
                self._scroll,
                text=f"... y {total - fetch_limit} productos mas. Use la busqueda para filtrar.",
                font=("Arial", 10, "italic"),
                text_color="gray",
            ).pack(pady=5)
        elif not is_filtered and total == 0:
            ctk.CTkLabel(
                self._scroll,
                text="No hay productos. Use 'Cargar Lista' para importar.",
                font=("Arial", 10, "italic"),
                text_color="gray",
            ).pack(pady=5)

    def _select_product(self, product):
        """Selecciona un producto de la tabla y carga sus datos en el formulario."""
        self._selected_id = product.id

        self._name_entry.delete(0, "end")
        self._name_entry.insert(0, product.name)
        self._code_entry.delete(0, "end")
        self._code_entry.insert(0, product.code)
        self._cat_entry.delete(0, "end")
        self._cat_entry.insert(0, product.category)
        self._supplier_entry.delete(0, "end")
        self._supplier_entry.insert(0, product.supplier)
        self._date_entry.delete(0, "end")
        self._date_entry.insert(0, product.list_date.isoformat())
        self._sp_entry.delete(0, "end")
        self._sp_entry.insert(0, str(product.supplier_price))
        self._sv_entry.delete(0, "end")
        self._sv_entry.insert(0, str(product.selling_price))
        self._uq_entry.delete(0, "end")
        self._uq_entry.insert(0, str(product.unit_quantity))
        self._up_entry.delete(0, "end")
        self._up_entry.insert(0, str(product.unit_price))
        self._usd_entry.delete(0, "end")
        self._usd_entry.insert(0, str(product.price_usd))
        self._susd_entry.delete(0, "end")
        self._susd_entry.insert(0, str(product.selling_price_usd))

        self._edit_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")
        self._recalc_btn.configure(state="normal")

    def _get_form_data(self):
        """Extrae y valida todos los campos del formulario."""
        name = self._name_entry.get().strip()
        cat = self._cat_entry.get().strip()
        supplier = self._supplier_entry.get().strip()
        code = self._code_entry.get().strip()
        try:
            list_date = date.fromisoformat(self._date_entry.get().strip())
        except ValueError:
            raise ValueError("Fecha invalida (YYYY-MM-DD)")
        try:
            sp = Decimal(self._sp_entry.get().strip())
            sv = Decimal(self._sv_entry.get().strip())
            uq = int(self._uq_entry.get().strip())
            up = Decimal(self._up_entry.get().strip())
            pu = Decimal(self._usd_entry.get().strip())
            su = Decimal(self._susd_entry.get().strip())
        except (InvalidOperation, ValueError):
            raise ValueError(
                "Ingrese valores numericos validos en todos los campos de precio"
            )
        return name, cat, supplier, list_date, sp, sv, uq, up, pu, su, code

    def _add_product(self):
        """Crea un nuevo producto con los datos del formulario."""
        try:
            data = self._get_form_data()
            self._product_service.create_product(*data)
            self._clear_form()
            self._refresh_table()
            messagebox.showinfo("Exito", "Producto agregado correctamente")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _edit_product(self):
        """Actualiza el producto seleccionado."""
        if self._selected_id is None:
            return
        try:
            data = self._get_form_data()
            self._product_service.update_product(self._selected_id, *data)
            self._clear_form()
            self._refresh_table()
            messagebox.showinfo("Exito", "Producto actualizado correctamente")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _delete_product(self):
        """Elimina el producto seleccionado (con confirmacion)."""
        if self._selected_id is None:
            return
        if messagebox.askyesno("Confirmar", "Esta seguro de eliminar este producto?"):
            self._product_service.delete_product(self._selected_id)
            self._clear_form()
            self._refresh_table()
            messagebox.showinfo("Exito", "Producto eliminado")

    def _recalc_selected(self):
        """
        Recalcula los precios del producto seleccionado usando
        el margen de ganancia y tipo de cambio USD configurados.
        """
        if self._selected_id is None:
            return
        try:
            p = self._product_service.get_product(self._selected_id)
            self._product_service.recalculate_from_supplier_price(p)
            # Recargar el producto actualizado en el formulario
            self._select_product(self._product_service.get_product(self._selected_id))
            self._refresh_table()
            messagebox.showinfo("Exito", "Precios recalculados con margen y USD actual")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _clear_form(self):
        """Limpia el formulario y deselecciona el producto."""
        self._selected_id = None
        for e in [
            self._name_entry,
            self._code_entry,
            self._cat_entry,
            self._supplier_entry,
            self._sp_entry,
            self._sv_entry,
            self._up_entry,
            self._usd_entry,
            self._susd_entry,
        ]:
            e.delete(0, "end")
        self._uq_entry.delete(0, "end")
        self._uq_entry.insert(0, "1")
        self._date_entry.delete(0, "end")
        self._date_entry.insert(0, date.today().isoformat())
        self._edit_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._recalc_btn.configure(state="disabled")
