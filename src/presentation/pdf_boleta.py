from decimal import Decimal
from datetime import date
import math
import os

RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recursos")


def generate_boleta_pdf(path, items, client, date_str, resources_dir=None):
    """Generate a PDF invoice.

    items: list of {"name": str, "qty": Decimal|int, "unit_price": Decimal}
    client: str (may be empty)
    date_str: str (ISO format)
    """
    res = resources_dir or RESOURCES
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()

    logo_path = os.path.join(res, "logo.jpeg")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)
        pdf.set_xy(42, 10)
    else:
        pdf.set_xy(10, 10)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Ferretería Alvear Bulón Fer", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Boleta / Presupuesto", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    y_start = pdf.get_y()
    pdf.line(10, y_start, 200, y_start)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(100, 5, f"Cliente: {client if client else 'Consumidor Final'}", align="L")
    pdf.cell(0, 5, f"Fecha: {date_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    col_w = [10, 78, 22, 30, 30]
    headers = ["Item", "Producto", "Cant.", "P. Unit.", "Total"]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 7, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    grand_total = Decimal("0")
    for idx, item in enumerate(items):
        qty = Decimal(str(item["qty"]))
        unit_price = Decimal(str(item["unit_price"]))
        total = qty * unit_price
        grand_total += total

        product_name = item["name"]
        name_width = pdf.get_string_width(product_name)
        avail_width = col_w[1] - 2
        num_lines = max(1, math.ceil(name_width / avail_width) if avail_width > 0 else 1)
        row_h = num_lines * 6

        y0 = pdf.get_y()
        x0 = pdf.get_x()

        if y0 + row_h > pdf.h - 55:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(230, 230, 230)
            for h, w in zip(headers, col_w):
                pdf.cell(w, 7, h, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)
            y0 = pdf.get_y()

        pdf.cell(col_w[0], row_h, str(idx + 1), border=1, align="C")

        x1 = pdf.get_x()
        pdf.set_xy(x1 + 1, y0 + 0.5)
        pdf.multi_cell(col_w[1] - 2, 6, product_name, border=0, align="L")
        y_after = pdf.get_y()
        actual_h = y_after - y0
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x1, y0, col_w[1], actual_h)
        pdf.set_fill_color(230, 230, 230)

        pdf.set_xy(x1 + col_w[1], y0)
        pdf.cell(col_w[2], actual_h, str(qty), border=1, align="R")
        pdf.cell(col_w[3], actual_h, f"${unit_price:,.2f}", border=1, align="R")
        pdf.cell(col_w[4], actual_h, f"${total:,.2f}", border=1, align="R")

        pdf.set_xy(x0, y0 + actual_h)

    pdf.set_font("Helvetica", "B", 10)
    total_cols = col_w[0] + col_w[1] + col_w[2] + col_w[3]
    pdf.cell(total_cols, 8, "TOTAL", border=1, align="R")
    pdf.cell(col_w[4], 8, f"${grand_total:,.2f}", border=1, align="R")
    pdf.ln(12)

    y_footer = pdf.h - 45
    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, y_footer, 200, y_footer)
    y_footer += 4

    logo_footer = os.path.join(res, "logo.jpeg")
    if os.path.exists(logo_footer):
        pdf.image(logo_footer, x=10, y=y_footer, w=22)

    ivan_footer = os.path.join(res, "logoIvan.png")
    if os.path.exists(ivan_footer):
        pdf.image(ivan_footer, x=94, y=y_footer, w=22)

    otto_footer = os.path.join(res, "otto.jpeg")
    if os.path.exists(otto_footer):
        pdf.image(otto_footer, x=178, y=y_footer, w=22)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(35, y_footer + 5)
    pdf.cell(0, 5, "Ingeniero Lange 491", align="L")

    pdf.output(path)


def items_from_sale_view(sale_items):
    """Convert RegisterSaleView _sale_items format to PDF items format.

    sale_items: list of (Product, qty, custom_unit_price_or_None)
    """
    result = []
    for product, qty, custom_price in sale_items:
        up = custom_price if custom_price else product.selling_price
        result.append({
            "name": product.name,
            "qty": qty,
            "unit_price": up,
        })
    return result
