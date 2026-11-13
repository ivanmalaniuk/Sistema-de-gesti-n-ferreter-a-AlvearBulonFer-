"""
CAPA DE PRESENTACION — Dialogo de Configuracion.

Permite al usuario modificar:
- Tipo de cambio USD (para calcular precios en dolares)
- Margen de ganancia (porcentaje aplicado al precio proveedor)

Al guardar, si los valores cambiaron, pregunta si desea recalcular
los precios de todos los productos con los nuevos valores.
"""

import customtkinter as ctk
from tkinter import messagebox
from decimal import Decimal, InvalidOperation

from src.application.settings_service import SettingsService
from src.application.product_service import ProductService


class SettingsDialog(ctk.CTkToplevel):
    """Dialogo modal de configuracion global."""

    def __init__(
        self, master, settings_service: SettingsService, product_service: ProductService
    ):
        super().__init__(master)
        self._settings = settings_service
        self._product_service = product_service

        self.title("Configuracion")
        self.geometry("450x300")
        self.resizable(False, False)
        self.transient(master)  # Dialogo modal sobre la ventana padre
        self.grab_set()  # Bloquea interaccion con otras ventanas

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        """Construye el formulario de configuracion."""
        ctk.CTkLabel(
            self, text="Configuracion General", font=("Arial", 18, "bold")
        ).pack(pady=15)

        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=30, pady=10)

        # Tipo de cambio USD
        ctk.CTkLabel(frame, text="Tipo de Cambio USD ($):").grid(
            row=0,
            column=0,
            padx=5,
            pady=8,
            sticky="w",
        )
        self._usd_entry = ctk.CTkEntry(frame, width=150)
        self._usd_entry.grid(row=0, column=1, padx=5, pady=8)

        # Margen de ganancia (en porcentaje, ej: 160 = 160%)
        ctk.CTkLabel(frame, text="Margen de Ganancia (%):").grid(
            row=1,
            column=0,
            padx=5,
            pady=8,
            sticky="w",
        )
        self._margin_entry = ctk.CTkEntry(frame, width=150)
        self._margin_entry.grid(row=1, column=1, padx=5, pady=8)

        ctk.CTkLabel(
            frame,
            text="El margen se aplica automaticamente\nal cargar listas de precios.",
            font=("Arial", 10),
            text_color="gray",
            justify="left",
        ).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame, text="Guardar", command=self._save,
            width=110, height=35, font=("Arial", 13),
        ).pack(side="left", padx=12)
        ctk.CTkButton(
            btn_frame, text="Cancelar", command=self.destroy,
            width=110, height=35, font=("Arial", 13),
        ).pack(side="left", padx=12)

    def _load_values(self):
        """Carga los valores actuales en los campos del formulario."""
        self._usd_entry.insert(0, str(self._settings.get_usd_rate()))
        self._margin_entry.insert(0, str(self._settings.get_profit_margin()))

    def _save(self):
        """Valida y guarda la configuracion. Opcionalmente recalcula precios."""
        try:
            usd = Decimal(self._usd_entry.get().strip())
            margin = Decimal(self._margin_entry.get().strip())
        except InvalidOperation:
            messagebox.showwarning(
                "Error", "Ingrese valores numericos validos", parent=self
            )
            return

        # Detectar cambios
        try:
            old_rate = self._settings.get_usd_rate()
            old_margin = self._settings.get_profit_margin()
            self._settings.set_usd_rate(usd)
            self._settings.set_profit_margin(margin)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        # Preguntar si desea recalcular todos los productos
        if usd != old_rate or margin != old_margin:
            recalc = messagebox.askyesno(
                "Recalcular",
                "Desea recalcular los precios de todos los productos\ncon los nuevos valores?",
                parent=self,
            )
            if recalc:
                count = 0
                errors = 0
                for p in self._product_service.get_all_products():
                    try:
                        self._product_service.recalculate_from_supplier_price(p)
                        count += 1
                    except Exception:
                        errors += 1
                messagebox.showinfo(
                    "Recalculados",
                    f"Precios recalculados: {count}\nErrores: {errors}",
                    parent=self,
                )

        messagebox.showinfo("Exito", "Configuracion guardada", parent=self)
        self.destroy()
