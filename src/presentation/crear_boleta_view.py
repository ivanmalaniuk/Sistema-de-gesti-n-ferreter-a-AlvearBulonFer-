import math
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
import os

from src.application.product_service import ProductService
from src.presentation.pdf_boleta import generate_boleta_pdf
from src.presentation.wheel_scroll import register_scrollable

RESOURCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos")


class CrearBoletaView(ctk.CTkFrame):
    def __init__(self, master, product_service: ProductService):
        super().__init__(master)
        self._product_service = product_service
        self._items = []
        self._total_labels = []
        self._build_ui()

    def _build_ui(self):
        # === HEADER: logo + titulo ===
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(10, 2))

        logo_path = os.path.join(RESOURCES, "logo.jpeg")
        if os.path.exists(logo_path):
            pil_img = Image.open(logo_path)
            pil_img.thumbnail((80, 80))
            self._logo_ctk = ctk.CTkImage(pil_img, size=pil_img.size)
            ctk.CTkLabel(header, image=self._logo_ctk, text="").pack(side="left", padx=(0, 10))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            title_frame, text="Ferretería Alvear Bulón Fer",
            font=("Arial", 22, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="Crear Boleta / Presupuesto",
            font=("Arial", 14),
            text_color="#555555",
        ).pack(anchor="w")

        # === CLIENTE + FECHA ===
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(5, 0))

        ctk.CTkLabel(info_frame, text="Cliente:", font=("Arial", 13, "bold")).pack(side="left", padx=(0, 5))
        self._client_entry = ctk.CTkEntry(info_frame, width=250)
        self._client_entry.pack(side="left", padx=5)

        ctk.CTkLabel(info_frame, text="Fecha:", font=("Arial", 13, "bold")).pack(side="left", padx=(20, 5))
        self._date_entry = ctk.CTkEntry(info_frame, width=130)
        self._date_entry.insert(0, date.today().isoformat())
        self._date_entry.pack(side="left", padx=5)

        # === SECCION DE BUSQUEDA ===
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(search_frame, text="Agregar producto:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self._search_entry = ctk.CTkEntry(search_frame, width=350)
        self._search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self._search_entry.bind("<Return>", self._on_search)

        ctk.CTkLabel(search_frame, text="o manual:").grid(
            row=0, column=2, padx=(20, 2), pady=5
        )
        self._manual_entry = ctk.CTkEntry(search_frame, width=200)
        self._manual_entry.grid(row=0, column=3, padx=2, pady=5, sticky="w")
        self._manual_entry.bind("<Return>", lambda e: self._add_manual())

        self._add_manual_btn = ctk.CTkButton(
            search_frame, text="Agregar", width=80, command=self._add_manual,
        )
        self._add_manual_btn.grid(row=0, column=4, padx=5, pady=5)

        self._search_results = ctk.CTkScrollableFrame(search_frame, height=120)
        self._search_results.grid(row=1, column=0, columnspan=6, sticky="ew", pady=2, padx=5)
        register_scrollable(self._search_results)

        # === TABLA DE ITEMS ===
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=2)

        _W = [36, 1, 80, 110, 110, 35]
        _H = ["Item", "Producto", "Cantidad", "P. Unitario", "Total", ""]
        hdr = ctk.CTkFrame(table_frame)
        hdr.pack(fill="x", pady=2)
        for h, w in zip(_H, _W):
            kw = dict(text=h, font=("Arial", 11, "bold"), anchor="w")
            if w == 1:
                ctk.CTkLabel(hdr, **kw).pack(side="left", padx=3, fill="x", expand=True)
            else:
                ctk.CTkLabel(hdr, width=w, **kw).pack(side="left", padx=3)

        self._items_container = ctk.CTkScrollableFrame(table_frame)
        self._items_container.pack(fill="both", expand=True, pady=2)
        register_scrollable(self._items_container)

        # === TOTAL + BOTONES ===
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=20, pady=5)

        self._total_label = ctk.CTkLabel(
            bottom, text="Total: $0.00", font=("Arial", 18, "bold"),
        )
        self._total_label.pack(side="left", padx=10)

        ctk.CTkButton(
            bottom, text="Limpiar Todo", fg_color="#757575",
            command=self._clear_all, width=120, height=35,
            font=("Arial", 13),
        ).pack(side="right", padx=8)

        self._export_btn = ctk.CTkButton(
            bottom, text="Exportar PDF", fg_color="#2e7d32",
            command=self._export_pdf, width=140, height=38,
            font=("Arial", 14, "bold"),
        )
        self._export_btn.pack(side="right", padx=8)
        self._export_btn.configure(state="disabled")

        # === FOOTER (estatico para referencia) ===
        footer_frame = ctk.CTkFrame(self, fg_color="#f5f5f5", height=50)
        footer_frame.pack(fill="x", padx=20, pady=5)
        footer_frame.pack_propagate(False)

        footer_text = ctk.CTkFrame(footer_frame, fg_color="transparent")
        footer_text.pack(side="left", padx=10, fill="y", expand=True)
        ctk.CTkLabel(footer_text, text="Ingeniero Lange 491", font=("Arial", 10)).pack(anchor="w")
        ctk.CTkLabel(footer_text, text="Alvear Bulon Fer", font=("Arial", 10)).pack(anchor="w")
        ctk.CTkLabel(footer_text, text="", font=("Arial", 4)).pack(anchor="w")
        ctk.CTkLabel(footer_text, text="Otto Impresiones", font=("Arial", 10)).pack(anchor="w")

        otto_path = os.path.join(RESOURCES, "otto.jpeg")
        if os.path.exists(otto_path):
            pil_otto = Image.open(otto_path)
            pil_otto.thumbnail((40, 50))
            self._otto_ctk = ctk.CTkImage(pil_otto, size=pil_otto.size)
            ctk.CTkLabel(footer_frame, image=self._otto_ctk, text="").pack(side="right", padx=10)

    # ---- Busqueda ----

    def _on_search(self, event=None):
        query = self._search_entry.get().strip()
        for w in self._search_results.winfo_children():
            w.destroy()
        if not query:
            return
        self._do_search(query)

    def _do_search(self, query):
        current = self._search_entry.get().strip()
        if current != query:
            return
        matches = self._product_service.search_products(query)
        if not matches:
            ctk.CTkLabel(
                self._search_results,
                text="Sin resultados", font=("Arial", 10, "italic"),
            ).pack(pady=5)
            self._search_entry.focus_set()
            return
        cutoff = date.today() - timedelta(days=61)
        for product in matches[:15]:
            is_old = product.list_date < cutoff
            btn = ctk.CTkButton(
                self._search_results,
                text=f"{product.name}  |  ${product.selling_price:,.2f}  |  {product.supplier}",
                anchor="w",
                fg_color="transparent",
                text_color=("#c62828", "#ef5350") if is_old else ("black", "white"),
                hover_color=("#e0e0e0", "#333333"),
                command=lambda p=product: self._add_from_catalog(p),
            )
            btn.pack(fill="x", pady=1)
        self._search_entry.focus_set()

    # ---- Agregar items ----

    def _add_from_catalog(self, product):
        self._items.append({
            "name": product.name,
            "qty": Decimal("1"),
            "unit_price": product.selling_price,
        })
        self._search_entry.delete(0, "end")
        for w in self._search_results.winfo_children():
            w.destroy()
        self._render_items()

    def _add_manual(self):
        name = self._manual_entry.get().strip()
        if not name:
            messagebox.showwarning("Advertencia", "Ingrese el nombre del producto")
            return
        self._items.append({
            "name": name,
            "qty": Decimal("1"),
            "unit_price": Decimal("0"),
        })
        self._manual_entry.delete(0, "end")
        self._render_items()

    # ---- Render items ----

    def _render_items(self):
        for w in self._items_container.winfo_children():
            w.destroy()
        self._total_labels.clear()

        grand_total = Decimal("0")
        for idx, item in enumerate(self._items):
            total = item["qty"] * item["unit_price"]
            grand_total += total

            row = ctk.CTkFrame(self._items_container)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, width=36, text=str(idx + 1), anchor="w").pack(side="left", padx=3)

            name_entry = ctk.CTkEntry(row, font=("Arial", 11))
            name_entry.pack(side="left", padx=3, fill="x", expand=True)
            name_entry.insert(0, item["name"])
            name_entry.bind("<FocusOut>", lambda e, i=idx: self._on_field_change(i, "name", e.widget))

            qty_entry = ctk.CTkEntry(row, width=80, font=("Arial", 11))
            qty_entry.pack(side="left", padx=3)
            qty_entry.insert(0, str(item["qty"]))
            qty_entry.bind("<FocusOut>", lambda e, i=idx: self._on_qty_change(i, e.widget))
            qty_entry.bind("<Return>", lambda e, i=idx: self._on_qty_change(i, e.widget))

            price_text = f"${item['unit_price']:,.2f}" if item["unit_price"] else "0"
            price_entry = ctk.CTkEntry(row, width=110, font=("Arial", 11))
            price_entry.pack(side="left", padx=3)
            price_entry.insert(0, price_text)
            price_entry.bind("<FocusOut>", lambda e, i=idx: self._on_price_change(i, e.widget))
            price_entry.bind("<Return>", lambda e, i=idx: self._on_price_change(i, e.widget))

            total_lbl = ctk.CTkLabel(row, width=110, text=f"${total:,.2f}", anchor="e", font=("Arial", 11, "bold"))
            total_lbl.pack(side="left", padx=3)
            self._total_labels.append(total_lbl)

            ctk.CTkButton(
                row, text="X", width=35, fg_color="#c62828",
                command=lambda i=idx: self._remove_item(i),
            ).pack(side="right", padx=3)

        self._total_label.configure(text=f"Total: ${grand_total:,.2f}")
        self._export_btn.configure(state="normal" if self._items else "disabled")

    # ---- Edicion de campos ----

    def _on_field_change(self, idx, field, widget):
        if 0 <= idx < len(self._items):
            self._items[idx][field] = widget.get().strip()

    def _on_qty_change(self, idx, widget):
        if 0 <= idx < len(self._items):
            try:
                qty = Decimal(widget.get().replace(",", "."))
                if qty < 0:
                    qty = Decimal("0")
                self._items[idx]["qty"] = qty
            except Exception:
                widget.delete(0, "end")
                widget.insert(0, str(self._items[idx]["qty"]))
            self._recalc_row(idx)

    def _on_price_change(self, idx, widget):
        if 0 <= idx < len(self._items):
            raw = widget.get().replace("$", "").replace(",", "").strip()
            try:
                price = Decimal(raw)
                if price < 0:
                    price = Decimal("0")
                self._items[idx]["unit_price"] = price
                widget.delete(0, "end")
                widget.insert(0, f"${price:,.2f}")
            except Exception:
                widget.delete(0, "end")
                widget.insert(0, f"${self._items[idx]['unit_price']:,.2f}")
            self._recalc_row(idx)

    def _recalc_row(self, idx):
        if 0 <= idx < len(self._items):
            item = self._items[idx]
            total = item["qty"] * item["unit_price"]
            if idx < len(self._total_labels):
                self._total_labels[idx].configure(text=f"${total:,.2f}")
            grand = sum(it["qty"] * it["unit_price"] for it in self._items)
            self._total_label.configure(text=f"Total: ${grand:,.2f}")

    def _remove_item(self, idx):
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._render_items()

    def _clear_all(self):
        self._items.clear()
        self._render_items()

    # ---- Exportar PDF ----

    def _export_pdf(self):
        if not self._items:
            messagebox.showwarning("Advertencia", "No hay items en la boleta")
            return

        client = self._client_entry.get().strip()
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

        pdf_items = [{"name": it["name"], "qty": it["qty"], "unit_price": it["unit_price"]} for it in self._items]
        try:
            generate_boleta_pdf(path, pdf_items, client, self._date_entry.get().strip())
            messagebox.showinfo("Exportado", f"Boleta guardada en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el PDF:\n{str(e)}")
