"""
CAPA DE PRESENTACION — Punto de entrada de la interfaz grafica.

Ventana principal de la aplicacion usando CustomTkinter.
Configura el tema visual y crea el MainWindow con todas las pestanas.
"""

import os
import sys
import traceback
from PIL import Image
import customtkinter as ctk

from src.presentation.main_window import MainWindow

_RESOURCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos")


class App(ctk.CTk):
    """Ventana principal de la aplicacion.

    Nota: tkinterdnd2 no es compatible con Tk 9.0, por lo que se fuerza
    ctk.CTk como clase base. El drag & drop de archivos queda deshabilitado.
    """

    def __init__(
        self,
        product_service,
        sale_service,
        expense_service,
        report_service,
        list_service,
        settings_service,
        missing_service,
        backup_on_close=None,
    ):
        ctk.CTk.__init__(self)

        # Callback opcional que se ejecuta antes de cerrar (ej: backup de la base)
        self._backup_on_close = backup_on_close

        # Tema visual: claro (light) con color azul
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Configuracion de la ventana
        self.title("Ferretería Alvear Bulón Fer - Sistema de Gestion")
        self._icon_after_id = self.after(50, self._set_icon)
        self.minsize(1000, 600)
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

        # === Header con logos ===
        header = ctk.CTkFrame(self, fg_color="transparent", height=65)
        header.pack(fill="x", padx=10, pady=(8, 0))
        header.pack_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        logo_path = os.path.join(_RESOURCES, "logo.jpeg")
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img.thumbnail((60, 60))
            ctk.CTkLabel(left, image=ctk.CTkImage(img, size=img.size), text="").pack(side="left", padx=4)

        ivan_path = os.path.join(_RESOURCES, "logoIvan.png")
        if os.path.exists(ivan_path):
            img = Image.open(ivan_path)
            img.thumbnail((60, 60))
            ctk.CTkLabel(left, image=ctk.CTkImage(img, size=img.size), text="").pack(side="left", padx=4)

        otto_path = os.path.join(_RESOURCES, "otto.jpeg")
        if os.path.exists(otto_path):
            img = Image.open(otto_path)
            img.thumbnail((60, 60))
            ctk.CTkLabel(header, image=ctk.CTkImage(img, size=img.size), text="").pack(side="right", padx=4)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Crear y mostrar la ventana con pestanas
        self.main_window = MainWindow(
            self,
            product_service=product_service,
            sale_service=sale_service,
            expense_service=expense_service,
            report_service=report_service,
            list_service=list_service,
            settings_service=settings_service,
            missing_service=missing_service,
        )
        self.main_window.pack(fill="both", expand=True, padx=5)

    def _set_icon(self):
        if not self.winfo_exists():
            return
        icon_path = os.path.join(_RESOURCES, "ferreteria.png")
        if not os.path.exists(icon_path):
            return
        try:
            from PIL import ImageTk
            img = Image.open(icon_path).copy()
            img.thumbnail((32, 32))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            self._icon_photo = ImageTk.PhotoImage(img)
            self.wm_iconphoto(True, self._icon_photo)
        except Exception:
            pass

    def _on_close(self):
        # Backup automatico: un fallo NUNCA debe impedir el cierre
        if self._backup_on_close is not None:
            try:
                self._backup_on_close()
            except Exception:
                traceback.print_exc()
        try:
            if hasattr(self, '_icon_after_id') and self._icon_after_id:
                self.after_cancel(self._icon_after_id)
        except Exception:
            pass
        try:
            self.quit()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(0)
        except Exception:
            pass
