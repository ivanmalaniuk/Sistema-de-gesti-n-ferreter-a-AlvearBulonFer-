import customtkinter as ctk
from tkinter import messagebox
from decimal import Decimal

from src.application.sale_service import SaleService
from src.presentation.wheel_scroll import register_scrollable

MAX_DISPLAY = 200


class SalesHistoryView(ctk.CTkFrame):
    """Pestana: Historial de Ventas registradas con detalle y eliminacion."""

    def __init__(self, master, sale_service: SaleService):
        super().__init__(master)
        self._sale_service = sale_service
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text="Historial de Ventas", font=("Arial", 20, "bold")
        )
        title.pack(pady=10)

        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(
            toolbar, text="Refrescar", command=self._refresh,
            width=100, height=32, font=("Arial", 12),
        ).pack(side="right", padx=8)

        self._info_label = ctk.CTkLabel(toolbar, text="", font=("Arial", 12))
        self._info_label.pack(side="left", padx=10)

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=20, pady=5)
        register_scrollable(self._scroll)

        self._refresh()

    def _refresh(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        try:
            sales = self._sale_service.get_all_sales()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        total_ventas = sum(s.total_amount for s in sales)
        self._info_label.configure(
            text=f"{len(sales)} ventas  ·  Total: ${total_ventas:,.2f}"
        )

        display = sales[:MAX_DISPLAY]
        for sale in display:
            self._render_sale(sale)

        if len(sales) > MAX_DISPLAY:
            ctk.CTkLabel(
                self._scroll,
                text=f"... y {len(sales) - MAX_DISPLAY} ventas mas",
                font=("Arial", 10, "italic"),
                text_color="gray",
            ).pack(pady=5)

    def _render_sale(self, sale):
        fecha = sale.created_at.strftime("%Y-%m-%d %H:%M") if sale.created_at else "-"

        card = ctk.CTkFrame(self._scroll, fg_color="#f8f9fa", corner_radius=8)
        card.pack(fill="x", pady=4, padx=5)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            header, text=f"Venta #{sale.id}", font=("Arial", 13, "bold")
        ).pack(side="left", padx=2)

        if sale.customer:
            ctk.CTkLabel(
                header, text=f"Cliente: {sale.customer}", font=("Arial", 11),
                text_color="#1565c0",
            ).pack(side="left", padx=10)

        ctk.CTkLabel(
            header, text=fecha, font=("Arial", 11), text_color="gray"
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            header,
            text=f"Total: ${sale.total_amount:,.2f}",
            font=("Arial", 13, "bold"),
            text_color="#2e7d32",
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            header, text=f"{len(sale.items)} items", font=("Arial", 11)
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            header,
            text="Eliminar",
            width=90,
            height=30,
            fg_color="#c62828",
            hover_color="#b71c1c",
            font=("Arial", 12),
            command=lambda s=sale: self._delete_sale(s),
        ).pack(side="right", padx=8)

        for item in sale.items:
            self._render_item(card, item)

    def _render_item(self, parent, item):
        p = item.product
        up = item.unit_price
        subtotal = up * item.quantity
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=(25, 10), pady=1)

        ctk.CTkLabel(
            row,
            text=f"{p.name[:60]}",
            font=("Arial", 11),
            anchor="w",
        ).pack(side="left", padx=2, fill="x", expand=True)

        ctk.CTkLabel(
            row,
            text=f"x{item.quantity}",
            font=("Arial", 11),
            width=50,
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            row,
            text=f"${up:,.2f}",
            font=("Arial", 11),
            width=90,
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            row,
            text=f"${subtotal:,.2f}",
            font=("Arial", 11, "bold"),
            width=100,
        ).pack(side="left", padx=5)

    def _delete_sale(self, sale):
        confirm = messagebox.askyesno(
            "Confirmar eliminacion",
            f"Eliminar venta #{sale.id} por ${sale.total_amount:,.2f}?\n\n"
            "Esto no se puede deshacer.",
        )
        if not confirm:
            return
        try:
            self._sale_service.delete_sale(sale.id)
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))
