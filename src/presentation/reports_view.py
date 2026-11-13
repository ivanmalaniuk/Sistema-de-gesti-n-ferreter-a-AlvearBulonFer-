"""
CAPA DE PRESENTACION — Pestana: Reportes.

Muestra el reporte financiero mensual con tres indicadores clave:
- Ingresos Brutos (suma de todas las ventas del mes)
- Gastos Totales (suma de todos los gastos del mes)
- Ganancia Neta (ingresos - gastos, puede ser negativa)

El usuario selecciona mes y anio mediante comboboxes y presiona
"Generar Reporte" para ver los resultados.
"""

import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tkinter import filedialog, messagebox

from src.application.report_service import ReportService

MONTHS = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


class ReportsView(ctk.CTkFrame):
    """Panel de reportes financieros mensuales."""

    def __init__(self, master, report_service: ReportService):
        super().__init__(master)
        self._report_service = report_service
        self._last_report = None
        self._build_ui()
        self._set_current_month()

    def _build_ui(self):
        """Construye la interfaz del reporte."""
        title = ctk.CTkLabel(
            self, text="Reportes Financieros", font=("Arial", 20, "bold")
        )
        title.pack(pady=10)

        # === Selector de mes y anio ===
        selector = ctk.CTkFrame(self)
        selector.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(selector, text="Mes:").grid(row=0, column=0, padx=5, pady=5)
        self._month_combo = ctk.CTkComboBox(
            selector,
            values=MONTHS,
            width=150,
            state="readonly",
        )
        self._month_combo.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(selector, text="Anio:").grid(row=0, column=2, padx=15, pady=5)
        self._year_combo = ctk.CTkComboBox(
            selector,
            values=[str(y) for y in range(2024, 2031)],
            width=100,
            state="readonly",
        )
        self._year_combo.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkButton(
            selector,
            text="Generar Reporte",
            command=self._generate_report,
            fg_color="#1565c0",
            width=150,
            height=35,
            font=("Arial", 13),
        ).grid(row=0, column=4, padx=15, pady=5)

        self._export_btn = ctk.CTkButton(
            selector,
            text="Exportar PDF",
            command=self._export_pdf,
            fg_color="#2e7d32",
            state="disabled",
            width=140,
            height=35,
            font=("Arial", 13),
        )
        self._export_btn.grid(row=0, column=5, padx=15, pady=5)

        # === Area de resultados ===
        self._report_frame = ctk.CTkFrame(self)
        self._report_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self._report_title = ctk.CTkLabel(
            self._report_frame,
            text="",
            font=("Arial", 16, "bold"),
        )
        self._report_title.pack(pady=15)

        # Tarjetas de indicadores con colores semanticos:
        # Verde = ingresos, Rojo = gastos, Azul = ganancia
        cards = ctk.CTkFrame(self._report_frame)
        cards.pack(fill="x", padx=40, pady=10)

        self._ingresos_card = self._make_card(
            cards,
            "Ingresos Brutos",
            "#e8f5e9",
            "#2e7d32",
        )
        self._ingresos_card.pack(fill="x", pady=5, padx=10)

        self._costo_card = self._make_card(
            cards,
            "Costo Productos Vendidos",
            "#fff3e0",
            "#e65100",
        )
        self._costo_card.pack(fill="x", pady=5, padx=10)

        self._gastos_card = self._make_card(
            cards,
            "Gastos Totales",
            "#fce4ec",
            "#c62828",
        )
        self._gastos_card.pack(fill="x", pady=5, padx=10)

        self._ganancia_card = self._make_card(
            cards,
            "Ganancia Neta",
            "#e3f2fd",
            "#1565c0",
        )
        self._ganancia_card.pack(fill="x", pady=5, padx=10)

        self._report_detail = ctk.CTkLabel(
            self._report_frame,
            text="",
            font=("Arial", 11),
            text_color="gray",
        )
        self._report_detail.pack(pady=(5, 10))

    def _make_card(self, parent, label, bg, fg):
        """
        Crea una tarjeta visual con un indicador financiero.

        Args:
            parent: Frame contenedor
            label: Texto del indicador (ej: "Ingresos Brutos")
            bg: Color de fondo (ej: verde claro)
            fg: Color del texto del monto (ej: verde oscuro)
        """
        frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10)
        ctk.CTkLabel(frame, text=label, font=("Arial", 14)).pack(pady=(10, 0))
        amount_label = ctk.CTkLabel(
            frame,
            text="$0.00",
            font=("Arial", 24, "bold"),
            text_color=fg,
        )
        amount_label.pack(pady=(0, 10))
        frame.amount_label = amount_label
        return frame

    def _set_current_month(self):
        """Pre-selecciona el mes y anio actuales y genera el reporte."""
        now = datetime.now()
        self._month_combo.set(MONTHS[now.month - 1])
        self._year_combo.set(str(now.year))
        self._report_title.configure(
            text=f"Reporte de {MONTHS[now.month - 1]} {now.year}",
        )
        self._auto_generate()

    def _auto_generate(self):
        """Genera el reporte automaticamente si hay mes/anio seleccionados."""
        if self._month_combo.get() and self._year_combo.get():
            self._generate_report()

    def _generate_report(self):
        """Genera y muestra el reporte del mes seleccionado."""
        month_str = self._month_combo.get()
        year_str = self._year_combo.get()

        if month_str not in MONTHS or not year_str:
            messagebox.showwarning("Advertencia", "Seleccione mes y anio")
            return

        month = MONTHS.index(month_str) + 1
        year = int(year_str)

        try:
            report = self._report_service.get_monthly_report(year, month)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._last_report = report
        self._export_btn.configure(state="normal")

        self._report_title.configure(text=f"Reporte de {month_str} {year}")
        self._ingresos_card.amount_label.configure(
            text=f"${report.gross_revenue:,.2f}",
        )
        self._costo_card.amount_label.configure(
            text=f"${report.cost_of_goods:,.2f}",
        )
        self._gastos_card.amount_label.configure(
            text=f"${report.total_expenses:,.2f}",
        )

        net_color = "#2e7d32" if report.net_profit >= 0 else "#c62828"
        self._ganancia_card.amount_label.configure(
            text=f"${report.net_profit:,.2f}",
            text_color=net_color,
        )
        self._report_detail.configure(
            text=f"${report.gross_revenue:,.2f} (ingresos)  −  ${report.cost_of_goods:,.2f} (costos)  −  ${report.total_expenses:,.2f} (gastos)"
        )

    def _export_pdf(self):
        report = self._last_report
        if report is None:
            messagebox.showwarning("Advertencia", "Genere un reporte primero")
            return

        default_name = f"reporte_{MONTHS[report.month - 1]}_{report.year}.pdf"
        path = filedialog.asksaveasfilename(
            title="Guardar reporte PDF",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return

        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 15, "Ferretería Alvear Bulón Fer", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, "Reporte Financiero", align="C", new_x="LMARGIN", new_y="NEXT")
        month_str = MONTHS[report.month - 1]
        pdf.cell(0, 8, f"{month_str} {report.year}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 10, "Resultados:", align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        pdf.set_font("Helvetica", "", 11)
        items = [
            ("Ingresos Brutos", f"${report.gross_revenue:,.2f}"),
            ("Costo Productos Vendidos", f"${report.cost_of_goods:,.2f}"),
            ("Gastos Totales", f"${report.total_expenses:,.2f}"),
        ]
        for label, value in items:
            pdf.cell(90, 9, f"  {label}", border=1)
            pdf.cell(50, 9, value, border=1, align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 13)
        net_color_text = "0,128,0" if report.net_profit >= 0 else "200,0,0"
        pdf.set_text_color(*[int(c) for c in net_color_text.split(",")])
        pdf.cell(90, 10, "  Ganancia Neta", border=1)
        pdf.cell(50, 10, f"${report.net_profit:,.2f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="R")

        try:
            pdf.output(path)
            messagebox.showinfo("Exportado", f"PDF guardado en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el PDF:\n{str(e)}")
