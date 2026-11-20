import customtkinter as ctk
from tkinter import messagebox, ttk

from src.application.sale_service import SaleService

MAX_DISPLAY = 200
_SEARCH_DEBOUNCE_MS = 250

# Columnas de la tabla de ventas: (id interno, titulo, ancho)
_SALE_COLUMNS = (
    ("id", "ID", 70),
    ("fecha", "Fecha", 150),
    ("cliente", "Cliente", 240),
    ("total", "Total", 120),
    ("items", "Items", 80),
)

# Columnas del detalle: (id interno, titulo, ancho)
_ITEM_COLUMNS = (
    ("product", "Producto", 300),
    ("qty", "Cant.", 80),
    ("price", "Precio unit.", 120),
    ("subtotal", "Subtotal", 120),
)


class SalesHistoryView(ctk.CTkFrame):
    """Pestana: Historial de Ventas registradas con detalle y eliminacion."""

    def __init__(self, master, sale_service: SaleService):
        super().__init__(master)
        self._sale_service = sale_service
        self._sales_by_iid = {}  # iid del Treeview -> Sale
        self._selected_sale_id = None
        self._search_after_id = None
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text="Historial de Ventas", font=("Arial", 20, "bold")
        )
        title.pack(pady=10)

        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(toolbar, text="Buscar:").pack(side="left", padx=5)
        self._search_entry = ctk.CTkEntry(toolbar, width=250)
        self._search_entry.pack(side="left", padx=5)
        self._search_entry.bind("<KeyRelease>", self._schedule_refresh)
        self._search_entry.bind("<Return>", self._on_search_key)

        self._info_label = ctk.CTkLabel(toolbar, text="", font=("Arial", 12))
        self._info_label.pack(side="left", padx=10)

        ctk.CTkButton(
            toolbar, text="Refrescar", command=self._refresh,
            width=100, height=32, font=("Arial", 12),
        ).pack(side="right", padx=8)

        ctk.CTkButton(
            toolbar, text="Eliminar", command=self._delete_selected,
            fg_color="#c62828", hover_color="#b71c1c",
            width=100, height=32, font=("Arial", 12),
        ).pack(side="right", padx=8)

        # === Tabla de ventas ===
        sales_frame = ctk.CTkFrame(self)
        sales_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self._sales_tree = ttk.Treeview(
            sales_frame,
            columns=[c[0] for c in _SALE_COLUMNS],
            show="headings",
            selectmode="browse",
        )
        for col_id, title, width in _SALE_COLUMNS:
            self._sales_tree.heading(col_id, text=title)
            self._sales_tree.column(col_id, width=width, anchor="w", stretch=True)
        sales_scroll = ttk.Scrollbar(
            sales_frame, orient="vertical", command=self._sales_tree.yview
        )
        self._sales_tree.configure(yscrollcommand=sales_scroll.set)
        self._sales_tree.pack(side="left", fill="both", expand=True)
        sales_scroll.pack(side="right", fill="y")
        self._sales_tree.bind("<<TreeviewSelect>>", self._on_sale_select)

        # === Detalle de items de la venta seleccionada ===
        ctk.CTkLabel(
            self, text="Items de la venta seleccionada", font=("Arial", 13, "bold")
        ).pack(anchor="w", padx=20, pady=(5, 0))

        detail_frame = ctk.CTkFrame(self)
        detail_frame.pack(fill="x", padx=20, pady=5)

        self._items_tree = ttk.Treeview(
            detail_frame,
            columns=[c[0] for c in _ITEM_COLUMNS],
            show="headings",
            selectmode="browse",
            height=6,
        )
        for col_id, title, width in _ITEM_COLUMNS:
            self._items_tree.heading(col_id, text=title)
            self._items_tree.column(col_id, width=width, anchor="w", stretch=True)
        items_scroll = ttk.Scrollbar(
            detail_frame, orient="vertical", command=self._items_tree.yview
        )
        self._items_tree.configure(yscrollcommand=items_scroll.set)
        self._items_tree.pack(side="left", fill="both", expand=True)
        items_scroll.pack(side="right", fill="y")

        self._refresh()

    def _schedule_refresh(self, event=None):
        """Programa un refresco con debounce mientras el usuario escribe."""
        if event is not None and event.keysym == "Return":
            return
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(
            _SEARCH_DEBOUNCE_MS, self._run_scheduled_refresh
        )

    def _run_scheduled_refresh(self):
        self._search_after_id = None
        self._refresh()

    def _on_search_key(self, event=None):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._refresh()

    def _refresh(self):
        query = self._search_entry.get().strip()
        try:
            sales = self._sale_service.search_sales(query, limit=MAX_DISPLAY + 1)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        display = sales[:MAX_DISPLAY]
        total_ventas = sum(s.total_amount for s in display)
        if len(sales) > MAX_DISPLAY:
            self._info_label.configure(
                text=(
                    f"{MAX_DISPLAY}+ ventas (mostrando {MAX_DISPLAY})  ·  "
                    f"Total mostrado: ${total_ventas:,.2f}"
                )
            )
        else:
            self._info_label.configure(
                text=f"{len(sales)} ventas  ·  Total: ${total_ventas:,.2f}"
            )

        for iid in self._sales_tree.get_children():
            self._sales_tree.delete(iid)
        self._sales_by_iid.clear()

        target_iid = None
        for sale in display:
            fecha = (
                sale.created_at.strftime("%Y-%m-%d %H:%M")
                if sale.created_at
                else "-"
            )
            iid = self._sales_tree.insert(
                "",
                "end",
                values=(
                    sale.id,
                    fecha,
                    sale.customer or "-",
                    f"${sale.total_amount:,.2f}",
                    len(sale.items),
                ),
            )
            self._sales_by_iid[iid] = sale
            if sale.id == self._selected_sale_id:
                target_iid = iid

        if target_iid is not None:
            self._sales_tree.selection_set(target_iid)
            self._sales_tree.see(target_iid)
        else:
            self._selected_sale_id = None
            self._render_items(None)

    def _on_sale_select(self, event=None):
        selection = self._sales_tree.selection()
        if not selection:
            return
        sale = self._sales_by_iid.get(selection[0])
        self._selected_sale_id = sale.id if sale else None
        self._render_items(sale)

    def _render_items(self, sale):
        for iid in self._items_tree.get_children():
            self._items_tree.delete(iid)
        if sale is None:
            return
        for item in sale.items:
            p = item.product
            up = item.unit_price
            subtotal = up * item.quantity
            self._items_tree.insert(
                "",
                "end",
                values=(
                    p.name[:60],
                    item.quantity,
                    f"${up:,.2f}",
                    f"${subtotal:,.2f}",
                ),
            )

    def _delete_selected(self):
        selection = self._sales_tree.selection()
        if not selection:
            return
        sale = self._sales_by_iid.get(selection[0])
        if sale is None:
            return

        confirm = messagebox.askyesno(
            "Confirmar eliminacion",
            f"Eliminar venta #{sale.id} por ${sale.total_amount:,.2f}?\n\n"
            "Esto no se puede deshacer.",
        )
        if not confirm:
            return
        try:
            self._sale_service.delete_sale(sale.id)
            self._selected_sale_id = None
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))
