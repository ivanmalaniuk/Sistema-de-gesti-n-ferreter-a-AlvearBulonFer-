import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.application.expense_service import ExpenseService
from src.application.product_service import ProductService

CATEGORIES = ["Insumos", "Servicios", "Alquiler", "Sueldos", "Impuestos", "Otros"]

OTHER = "Otro"


class RegisterExpenseView(ctk.CTkFrame):
    def __init__(self, master, expense_service: ExpenseService, product_service: ProductService):
        self._product_service = product_service
        super().__init__(master)
        self._expense_service = expense_service
        self._build_ui()
        self.bind("<Map>", lambda e: self._on_tab_shown())

    def _on_tab_shown(self):
        if self._cat_combo.get() == "Insumos":
            self._refresh_suppliers()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text="Registrar Nuevo Gasto", font=("Arial", 20, "bold")
        )
        title.pack(pady=10)

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(form, text="Descripcion:").grid(
            row=0, column=0, padx=5, pady=8, sticky="w"
        )
        self._desc_entry = ctk.CTkEntry(form, width=450)
        self._desc_entry.grid(row=0, column=1, padx=5, pady=8)

        ctk.CTkLabel(form, text="Monto ($):").grid(
            row=1, column=0, padx=5, pady=8, sticky="w"
        )
        self._amount_entry = ctk.CTkEntry(form, width=200)
        self._amount_entry.grid(row=1, column=1, padx=5, pady=8, sticky="w")

        ctk.CTkLabel(form, text="Fecha (YYYY-MM-DD):").grid(
            row=2, column=0, padx=5, pady=8, sticky="w"
        )
        self._date_entry = ctk.CTkEntry(form, width=200)
        self._date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self._date_entry.grid(row=2, column=1, padx=5, pady=8, sticky="w")

        ctk.CTkLabel(form, text="Categoria:").grid(
            row=3, column=0, padx=5, pady=8, sticky="w"
        )
        self._cat_combo = ctk.CTkComboBox(
            form, values=CATEGORIES, width=200, state="readonly"
        )
        self._cat_combo.set(CATEGORIES[0])
        self._cat_combo.grid(row=3, column=1, padx=5, pady=8, sticky="w")
        self._cat_combo.configure(command=self._on_category_change)

        self._supplier_label = ctk.CTkLabel(form, text="Proveedor:")
        self._supplier_label.grid(row=4, column=0, padx=5, pady=8, sticky="w")

        self._supplier_combo = ctk.CTkComboBox(
            form, values=self._get_supplier_options(), width=200, state="readonly"
        )
        self._supplier_combo.set("")
        self._supplier_combo.grid(row=4, column=1, padx=5, pady=8, sticky="w")
        self._supplier_combo.configure(command=self._on_supplier_change)

        self._custom_supplier_entry = ctk.CTkEntry(form, width=200)

        if self._cat_combo.get() != "Insumos":
            self._supplier_label.grid_remove()
            self._supplier_combo.grid_remove()

        self._register_btn = ctk.CTkButton(
            form,
            text="Registrar Gasto",
            command=self._register_expense,
            fg_color="#e65100",
            hover_color="#bf360c",
            width=200,
            height=40,
            font=("Arial", 14, "bold"),
        )
        self._register_btn.grid(row=6, column=0, columnspan=2, pady=20)

    def _get_supplier_options(self) -> list:
        suppliers = self._product_service.get_suppliers()
        if OTHER in suppliers:
            suppliers = [s for s in suppliers if s != OTHER]
        return [""] + suppliers + [OTHER]

    def _refresh_suppliers(self):
        options = self._get_supplier_options()
        self._supplier_combo.configure(values=options)
        if self._supplier_combo.get() not in options:
            self._supplier_combo.set("")

    def _on_category_change(self, choice):
        if choice == "Insumos":
            self._refresh_suppliers()
            self._supplier_label.grid()
            self._supplier_combo.grid()
        else:
            self._supplier_label.grid_remove()
            self._supplier_combo.grid_remove()
            self._custom_supplier_entry.grid_remove()

    def _on_supplier_change(self, choice):
        if choice == OTHER:
            self._custom_supplier_entry.grid(
                row=5, column=1, padx=5, pady=(0, 8), sticky="w"
            )
            self._custom_supplier_entry.delete(0, "end")
        else:
            self._custom_supplier_entry.grid_remove()

    def _get_supplier(self) -> str:
        if self._cat_combo.get() != "Insumos":
            return ''
        choice = self._supplier_combo.get()
        if choice == OTHER:
            return self._custom_supplier_entry.get().strip()
        return choice.strip()

    def _register_expense(self):
        description = self._desc_entry.get().strip()
        amount_str = self._amount_entry.get().strip()
        date_str = self._date_entry.get().strip()
        category = self._cat_combo.get().strip()
        supplier = self._get_supplier()

        if not description:
            messagebox.showwarning("Advertencia", "Ingrese una descripcion")
            return

        try:
            amount = Decimal(amount_str)
        except InvalidOperation:
            messagebox.showwarning("Advertencia", "Ingrese un monto valido")
            return

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning(
                "Advertencia", "Ingrese una fecha valida (YYYY-MM-DD)"
            )
            return

        try:
            expense = self._expense_service.record_expense(
                description, amount, date, category, supplier
            )
            msg = f"Gasto registrado correctamente.\n${expense.amount:,.2f} - {expense.description}"
            if supplier:
                msg += f"\nProveedor: {supplier}"
            messagebox.showinfo("Exito", msg)
            self._desc_entry.delete(0, "end")
            self._amount_entry.delete(0, "end")
            self._date_entry.delete(0, "end")
            self._date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
            self._supplier_combo.set("")
            self._custom_supplier_entry.grid_remove()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
