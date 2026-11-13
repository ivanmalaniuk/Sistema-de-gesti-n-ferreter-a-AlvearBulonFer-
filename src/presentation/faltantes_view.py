import customtkinter as ctk
from tkinter import messagebox
from datetime import date, timedelta

from src.application.missing_item_service import MissingItemService
from src.application.product_service import ProductService
from src.presentation.wheel_scroll import register_scrollable


class FaltantesView(ctk.CTkFrame):
    def __init__(self, master, missing_service: MissingItemService, product_service: ProductService):
        super().__init__(master)
        self._missing_service = missing_service
        self._product_service = product_service
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

        self._search_results_frame = ctk.CTkScrollableFrame(catalog_frame, height=150)
        self._search_results_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=2, padx=5)
        register_scrollable(self._search_results_frame)

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

        header_frame = ctk.CTkFrame(list_frame)
        header_frame.pack(fill="x", pady=2)
        headers = ["Articulo", "Proveedor", "Notas", "Fecha", ""]
        widths = [1, 140, 200, 120, 35]
        for h, w in zip(headers, widths):
            kw = dict(text=h, font=("Arial", 12, "bold"), anchor="w")
            if w == 1:
                ctk.CTkLabel(header_frame, **kw).pack(side="left", padx=4, fill="x", expand=True)
            else:
                ctk.CTkLabel(header_frame, width=w, **kw).pack(side="left", padx=4)

        self._items_container = ctk.CTkScrollableFrame(list_frame)
        self._items_container.pack(fill="both", expand=True, pady=5)
        register_scrollable(self._items_container)

    def _on_search(self, event=None):
        query = self._search_entry.get().strip()
        for w in self._search_results_frame.winfo_children():
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
                self._search_results_frame,
                text="Sin resultados", font=("Arial", 10, "italic"),
            ).pack(pady=5)
            self._search_entry.focus_set()
            return
        cutoff = date.today() - timedelta(days=61)
        for product in matches:
            is_old = product.list_date < cutoff
            btn = ctk.CTkButton(
                self._search_results_frame,
                text=f"{product.name}  |  {product.supplier}  |  Lista: {product.list_date}",
                anchor="w",
                fg_color="transparent",
                text_color=("#c62828", "#ef5350") if is_old else ("black", "white"),
                hover_color=("#e0e0e0", "#333333"),
                command=lambda p=product: self._add_from_catalog(p),
            )
            btn.pack(fill="x", pady=1)
        self._search_entry.focus_set()

    def _add_from_catalog(self, product):
        try:
            self._missing_service.add_item(
                name=product.name,
                supplier=product.supplier,
                notes=f"Cod: {product.code}  Lista: {product.list_date}",
            )
            self._search_entry.delete(0, "end")
            for w in self._search_results_frame.winfo_children():
                w.destroy()
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
        for w in self._items_container.winfo_children():
            w.destroy()
        items = self._missing_service.get_all_items()
        if not items:
            ctk.CTkLabel(
                self._items_container,
                text="No hay articulos faltantes registrados",
                font=("Arial", 11, "italic"),
            ).pack(pady=10)
            return
        for item in items:
            row = ctk.CTkFrame(self._items_container)
            row.pack(fill="x", pady=1)
            created = item.created_at.strftime("%d/%m/%Y") if item.created_at else ""
            vals = [item.name, item.supplier, item.notes, created]
            widths = [1, 140, 200, 120]
            for v, w in zip(vals, widths):
                kw = dict(text=v, anchor="w")
                if w == 1:
                    ctk.CTkLabel(row, **kw).pack(side="left", padx=4, fill="x", expand=True)
                else:
                    ctk.CTkLabel(row, width=w, **kw).pack(side="left", padx=4)
            ctk.CTkButton(
                row, text="X", width=35, fg_color="#c62828",
                command=lambda iid=item.id: self._delete_item(iid),
            ).pack(side="right", padx=4)

    def _delete_item(self, item_id):
        try:
            self._missing_service.delete_item(item_id)
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))
