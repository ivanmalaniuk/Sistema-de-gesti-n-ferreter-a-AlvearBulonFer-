"""
CAPA DE APLICACION — Servicio de reportes.

Genera reportes financieros mensuales combinando datos de ventas e gastos.
Calcula: Ingresos Brutos, Gastos Totales, y Ganancia Neta (= ingresos - gastos).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.domain.interfaces import ISaleRepository, IExpenseRepository


@dataclass
class MonthlyReport:
    """Reporte financiero de un mes especifico."""

    year: int
    month: int
    gross_revenue: Decimal  # Ingresos brutos (total de ventas)
    cost_of_goods: Decimal  # Costo de los productos vendidos
    total_expenses: Decimal  # Gastos totales
    net_profit: Decimal  # Ganancia neta = ingresos - costos - gastos


class ReportService:
    """Genera reportes financieros mensuales."""

    def __init__(self, sale_repo: ISaleRepository, expense_repo: IExpenseRepository):
        self._sale_repo = sale_repo
        self._expense_repo = expense_repo

    def get_monthly_report(self, year: int, month: int) -> MonthlyReport:
        """
        Genera el reporte del mes especificado.

        Calcula el rango de fechas [inicio del mes, inicio del mes siguiente)
        y suma todas las ventas y gastos en ese periodo.
        """
        start = datetime(year, month, 1)

        # El fin del rango es el primer dia del mes siguiente
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        sales = self._sale_repo.get_by_date_range(start, end)
        expenses = self._expense_repo.get_by_date_range(start, end)

        gross_revenue = sum((sale.total_amount for sale in sales), Decimal("0"))
        cost_of_goods = sum(
            item.cost_price * item.quantity
            for sale in sales
            for item in sale.items
        )
        total_expenses = sum((expense.amount for expense in expenses), Decimal("0"))
        net_profit = gross_revenue - cost_of_goods - total_expenses

        return MonthlyReport(
            year=year,
            month=month,
            gross_revenue=gross_revenue,
            cost_of_goods=cost_of_goods,
            total_expenses=total_expenses,
            net_profit=net_profit,
        )
