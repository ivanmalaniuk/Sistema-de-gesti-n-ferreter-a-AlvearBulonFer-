import os
import shutil
import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import date
from decimal import Decimal

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LISTAS_ORIGINALES = os.path.join(_SRC_DIR, "listas_originales")
_LISTAS_SUBIDAS = os.path.join(_SRC_DIR, "listas_subidas")

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from src.application.list_service import ListService
from src.application.settings_service import SettingsService
from src.presentation.wheel_scroll import register_scrollable


HEADER_KEYWORD_MAP = [
    ("detalle articulo", "name"),
    ("detalle artículo", "name"),
    ("detalle", "name"),
    ("descripcion del producto", "name"),
    ("descripción del producto", "name"),
    ("descripcion", "name"),
    ("descripción", "name"),
    ("producto", "name"),
    ("nombre", "name"),
    ("subrubro", "category"),
    ("sub rubro", "category"),
    ("rubro", "category"),
    ("categoria", "category"),
    ("categoría", "category"),
    ("precio lista", "price"),
    ("precio con iva", "price"),
    ("precio de venta", "price"),
    ("p.venta", "price"),
    ("precio", "price"),
    ("importe", "price"),
    ("codigo", "code"),
    ("código", "code"),
    ("cod", "code"),
    ("articulo", None),
    ("artículo", None),
]

FGP_COLUMN_HINTS = {"detalle"}

COMMON_SUPPLIERS = [
    "DistriDelSur",
    "Enfer",
    "FGP",
    "Mercar",
]

SUPPLIER_PRESETS = {
    "DistriDelSur": {
        "header_row": 2,
        "name_col": "B",
        "cat_col": "Ninguna",
        "price_col": "G",
        "code_col": "Ninguna",
        "use_two_names": True,
        "desc_col": "C",
        "size_col": "D",
    },
    "Enfer": {
        "header_row": 11,
        "name_col": "C",
        "cat_col": "Ninguna",
        "price_col": "F",
        "code_col": "A",
        "use_two_names": True,
        "desc_col": "Ninguna",
        "size_col": "Ninguna",
    },
    "Mercar": {
        "header_row": 10,
        "name_col": "B",
        "cat_col": "Ninguna",
        "price_col": "D",
        "code_col": "A",
        "use_two_names": False,
        "desc_col": "Ninguna",
        "size_col": "Ninguna",
    },
    "FGP": {
        "header_row": 18,
        "name_col": "B",
        "cat_col": "C",
        "price_col": "F",
        "code_col": "A",
        "use_two_names": True,
        "desc_col": "C",
        "size_col": "Ninguna",
    },
}


def _col_letter(n):
    """Convierte un indice numerico (0-based) a letra de columna Excel (0->A, 1->B, ...)."""
    if n < 26:
        return chr(65 + n)
    return chr(64 + n // 26) + chr(65 + n % 26)


def _col_index(letter):
    """Convierte una letra de columna Excel a indice numerico 0-based (A->0, B->1, ...)."""
    letter = letter.strip().upper()
    if not letter:
        return 0
    if len(letter) == 1:
        return ord(letter) - 65
    return (ord(letter[0]) - 64) * 26 + (ord(letter[1]) - 65)


_COL_LETTERS = [_col_letter(i) for i in range(20)]


def _fgp_looks_valid(rows, header_idx):
    """Verifica que el formato FGP sea real (tiene Detalle + Descripcion)."""
    header = rows[header_idx] if header_idx < len(rows) else []
    hints = [str(c).strip().lower() for c in (header[1:4] if header else [])]
    has_detalle = any("detalle" in h for h in hints)
    has_desc = any("descripc" in h for h in hints)  # cubre "descripcion" y "descripción"
    return has_detalle and has_desc


class LoadListView(ctk.CTkFrame):
    """Panel de carga de listas de precios con mapeo de columnas."""

    def __init__(
        self, master, list_service: ListService, settings_service: SettingsService
    ):
        super().__init__(master)
        self._list_service = list_service
        self._settings = settings_service
        self._preview_rows = []
        self._file_path = ""
        self._raw_rows = []
        self._col_mapping = None
        self._wb = None
        self._sheet_names = []
        self._ignore_trace = False
        self._build_ui()
        self.bind("<Map>", lambda e: (self._load_suppliers(), self._refresh_uploaded_lists()))

    def _build_ui(self):
        self._drop_frame = ctk.CTkFrame(
            self,
            fg_color="#f0f4f8",
            border_width=2,
            border_color="#90a4ae",
            corner_radius=12,
        )
        self._drop_frame.pack(fill="x", padx=20, pady=(10, 5))

        drop_inner = ctk.CTkFrame(self._drop_frame, fg_color="transparent")
        drop_inner.pack(expand=True, fill="both", padx=10, pady=25)

        ctk.CTkLabel(
            drop_inner,
            text="\U0001f4c1",
            font=("Arial", 36),
            fg_color="transparent",
        ).pack()

        ctk.CTkLabel(
            drop_inner,
            text="Arrastre su archivo Excel aqui",
            font=("Arial", 16, "bold"),
            fg_color="transparent",
        ).pack(pady=(5, 0))

        ctk.CTkLabel(
            drop_inner,
            text="o haga clic para seleccionar un archivo  ·  Formatos: .xlsx, .xls",
            font=("Arial", 11),
            text_color="gray",
            fg_color="transparent",
        ).pack(pady=(2, 0))

        self._file_label = ctk.CTkLabel(
            self._drop_frame,
            text="",
            font=("Arial", 12, "bold"),
            text_color="#1565c0",
            fg_color="transparent",
        )

        self._cancel_btn = ctk.CTkButton(
            self._drop_frame,
            text="Cancelar",
            command=self._cancel_selection,
            width=90,
            height=28,
            font=("Arial", 11),
            fg_color="#c62828",
        )
        self._file_select_frame = ctk.CTkFrame(self._drop_frame, fg_color="transparent")

        for widget in [self._drop_frame, drop_inner]:
            widget.bind("<Button-1>", lambda e: self._select_file())
            for child in widget.winfo_children():
                try:
                    child.bind("<Button-1>", lambda e: self._select_file())
                except Exception:
                    pass

        if _HAS_DND and isinstance(self.winfo_toplevel(), TkinterDnD.Tk):
            try:
                self._drop_frame.drop_target_register(DND_FILES)
                self._drop_frame.dnd_bind("<<Drop>>", self._on_drop)
                self._drop_frame.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                self._drop_frame.dnd_bind("<<DragLeave>>", self._on_drag_leave)
                self._drop_frame.dnd_bind("<<DragPos>>", self._on_drag_pos)
            except Exception:
                pass

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(form, text="Proveedor:").grid(
            row=0, column=0, padx=5, pady=8, sticky="w"
        )
        self._supplier_var = ctk.StringVar(value="")
        self._supplier_combo = ctk.CTkComboBox(
            form, values=[""], variable=self._supplier_var,
            width=300, state="readonly",
        )
        self._supplier_combo.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        self._supplier_var.trace_add("write", self._on_supplier_selected)

        self._supplier_other_entry = ctk.CTkEntry(form, width=300)

        self._load_suppliers()

        ctk.CTkLabel(form, text="Fecha de Lista:").grid(
            row=1, column=0, padx=5, pady=8, sticky="w"
        )
        self._date_entry = ctk.CTkEntry(form, width=150)
        self._date_entry.insert(0, date.today().isoformat())
        self._date_entry.grid(row=1, column=1, padx=5, pady=8, sticky="w")

        ctk.CTkLabel(form, text="Hoja:").grid(
            row=2, column=0, padx=5, pady=8, sticky="w"
        )
        self._sheet_var = ctk.StringVar(value="")
        self._sheet_combo = ctk.CTkComboBox(
            form, values=[""], variable=self._sheet_var,
            width=200, state="readonly",
        )
        self._sheet_combo.grid(row=2, column=1, padx=5, pady=8, sticky="w")
        self._sheet_var.trace_add("write", self._on_sheet_change)

        default_margin = self._settings.get_profit_margin() - 100
        ctk.CTkLabel(form, text="Margen de Ganancia (%):").grid(
            row=3, column=0, padx=5, pady=8, sticky="w"
        )
        self._margin_entry = ctk.CTkEntry(form, width=100)
        self._margin_entry.insert(0, str(default_margin))
        self._margin_entry.grid(row=3, column=1, padx=5, pady=8, sticky="w")

        # ===== Top section: mapping, summary, import button (NOT inside scroll) =====
        self._mapping_frame = ctk.CTkFrame(self)
        self._mapping_frame.pack(fill="x", padx=20, pady=0)
        self._build_mapping_ui()

        summary_frame = ctk.CTkFrame(self)
        summary_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            summary_frame,
            text="Resumen de Importacion:",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self._summary_label = ctk.CTkLabel(
            summary_frame,
            text="Seleccione un archivo Excel para comenzar",
            font=("Arial", 12),
            justify="left",
        )
        self._summary_label.pack(anchor="w", padx=10, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 10))

        self._import_btn = ctk.CTkButton(
            btn_frame,
            text="Importar Productos",
            command=self._import_list,
            fg_color="#2e7d32",
            state="disabled",
            width=250,
            height=40,
            font=("Arial", 13, "bold"),
        )
        self._import_btn.pack(pady=5)

        # ===== Scrollable section: uploaded lists only =====
        uploaded_frame = ctk.CTkFrame(self)
        uploaded_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            uploaded_frame,
            text="Listas subidas:",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self._uploaded_scroll = ctk.CTkScrollableFrame(uploaded_frame, height=150)
        self._uploaded_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        register_scrollable(self._uploaded_scroll)

    def _build_mapping_ui(self):
        ctk.CTkLabel(
            self._mapping_frame,
            text="Configurar Columnas:",
            font=("Arial", 13, "bold"),
        ).grid(row=0, column=0, columnspan=4, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(self._mapping_frame, text="Fila encabezado:").grid(
            row=1, column=0, padx=5, pady=3, sticky="w"
        )
        self._header_var = ctk.StringVar(value="0")
        self._header_spinbox = ctk.CTkEntry(
            self._mapping_frame, width=60, textvariable=self._header_var
        )
        self._header_spinbox.grid(row=1, column=1, padx=5, pady=3, sticky="w")

        col_opts = _COL_LETTERS[:]
        cat_opts = ["Ninguna"] + col_opts

        ctk.CTkLabel(self._mapping_frame, text="Columna Nombre:").grid(
            row=2, column=0, padx=5, pady=3, sticky="w"
        )
        self._name_col_var = ctk.StringVar(value="A")
        self._name_col_combo = ctk.CTkComboBox(
            self._mapping_frame, values=col_opts, variable=self._name_col_var,
            width=80, state="readonly",
        )
        self._name_col_combo.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(self._mapping_frame, text="Columna Categoria:").grid(
            row=2, column=2, padx=5, pady=3, sticky="w"
        )
        self._cat_col_var = ctk.StringVar(value="Ninguna")
        self._cat_col_combo = ctk.CTkComboBox(
            self._mapping_frame, values=cat_opts, variable=self._cat_col_var,
            width=80, state="readonly",
        )
        self._cat_col_combo.grid(row=2, column=3, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(self._mapping_frame, text="Columna Precio:").grid(
            row=3, column=0, padx=5, pady=3, sticky="w"
        )
        self._price_col_var = ctk.StringVar(value="C")
        self._price_col_combo = ctk.CTkComboBox(
            self._mapping_frame, values=col_opts, variable=self._price_col_var,
            width=80, state="readonly",
        )
        self._price_col_combo.grid(row=3, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(
            self._mapping_frame, text="Columna Codigo (opcional):"
        ).grid(row=3, column=2, padx=5, pady=3, sticky="w")
        self._code_col_var = ctk.StringVar(value="Ninguna")
        self._code_col_combo = ctk.CTkComboBox(
            self._mapping_frame, values=cat_opts, variable=self._code_col_var,
            width=80, state="readonly",
        )
        self._code_col_combo.grid(row=3, column=3, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(
            self._mapping_frame, text="Nombre = Detalle + Descripcion:"
        ).grid(row=4, column=0, padx=5, pady=3, sticky="w")
        self._name_from_two_var = ctk.BooleanVar(value=False)
        self._name_two_check = ctk.CTkCheckBox(
            self._mapping_frame, text="Usar 2 o 3 columnas",
            variable=self._name_from_two_var,
        )
        self._name_two_check.grid(row=4, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(self._mapping_frame, text="Columna Descripcion:").grid(
            row=4, column=2, padx=5, pady=3, sticky="w"
        )
        self._desc_col_var = ctk.StringVar(value="Ninguna")
        self._desc_col_combo = ctk.CTkComboBox(
            self._mapping_frame, values=cat_opts, variable=self._desc_col_var,
            width=80, state="readonly",
        )
        self._desc_col_combo.grid(row=4, column=3, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(self._mapping_frame, text="Columna Tamaño (opcional):").grid(
            row=5, column=0, padx=5, pady=3, sticky="w"
        )
        self._size_col_var = ctk.StringVar(value="Ninguna")
        self._size_col_combo = ctk.CTkComboBox(
            self._mapping_frame, values=cat_opts, variable=self._size_col_var,
            width=80, state="readonly",
        )
        self._size_col_combo.grid(row=5, column=1, padx=5, pady=3, sticky="w")

        self._auto_btn = ctk.CTkButton(
            self._mapping_frame,
            text="Detectar Columnas",
            command=self._auto_detect_from_headers,
            width=140,
        )
        self._auto_btn.grid(row=5, column=2, padx=5, pady=5)

        self._map_btn = ctk.CTkButton(
            self._mapping_frame,
            text="Aplicar y Previsualizar",
            command=self._apply_mapping,
            fg_color="#1565c0",
        )
        self._map_btn.grid(row=5, column=3, padx=5, pady=5)

        self._add_mapping_traces()

        preview_frame = ctk.CTkFrame(self._mapping_frame)
        preview_frame.grid(row=6, column=0, columnspan=4, sticky="ew", padx=5, pady=2)
        preview_frame.grid_columnconfigure(0, weight=1)

        self._preview_text = ctk.CTkTextbox(preview_frame, height=100, font=("Courier", 10))
        self._preview_text.pack(fill="x", pady=2)

        for i in range(4):
            self._mapping_frame.grid_columnconfigure(i, weight=1)

        self._hide_mapping()

    def _add_mapping_traces(self):
        for var in [self._header_var, self._name_col_var, self._cat_col_var,
                     self._price_col_var, self._code_col_var, self._desc_col_var,
                     self._size_col_var]:
            var.trace_add("write", self._on_mapping_change)
        self._name_from_two_var.trace_add("write", self._on_mapping_change)
        self._desc_col_combo.configure(command=self._on_mapping_change)

    def _on_mapping_change(self, *args):
        if self._ignore_trace:
            return
        if not self._raw_rows:
            return
        self._apply_mapping()

    def _show_mapping(self):
        self._mapping_frame.pack(fill="x", pady=5, before=self._summary_label.master)

    def _hide_mapping(self):
        self._mapping_frame.pack_forget()

    def _load_suppliers(self):
        db_suppliers = self._list_service.get_suppliers()
        seen = set(db_suppliers)
        all_suppliers = list(dict.fromkeys(COMMON_SUPPLIERS + db_suppliers))
        current = self._supplier_var.get()
        vals = all_suppliers + ["Otro"]
        self._supplier_combo.configure(values=vals)
        if current not in vals:
            self._supplier_var.set("")

    def _on_supplier_selected(self, *args):
        selected = self._supplier_var.get()
        if selected == "Otro":
            self._supplier_other_entry.grid(row=0, column=1, padx=5, pady=(0, 8), sticky="w")
            self._supplier_other_entry.delete(0, "end")
            return
        self._supplier_other_entry.grid_remove()
        preset = SUPPLIER_PRESETS.get(selected)
        if preset:
            self._ignore_trace = True
            self._header_var.set(str(preset["header_row"]))
            self._name_col_var.set(preset["name_col"])
            self._cat_col_var.set(preset.get("cat_col", "Ninguna"))
            self._price_col_var.set(preset["price_col"])
            self._code_col_var.set(preset.get("code_col", "Ninguna"))
            self._name_from_two_var.set(preset.get("use_two_names", False))
            self._desc_col_var.set(preset.get("desc_col", "Ninguna"))
            self._size_col_var.set(preset.get("size_col", "Ninguna"))
            self._ignore_trace = False
            if self._raw_rows:
                self._apply_mapping()

    def _on_drop(self, event):
        raw = event.data
        path = raw.strip().strip("{}").strip()
        if not path:
            return
        self._file_path = path
        self._show_file_selected()
        self._after_file_select()

    def _on_drag_enter(self, event):
        self._drop_frame.configure(fg_color="#e3f2fd", border_color="#1565c0")

    def _on_drag_leave(self, event):
        self._drop_frame.configure(fg_color="#f0f4f8", border_color="#90a4ae")

    def _on_drag_pos(self, event):
        pass

    def _select_file(self):
        initial = _LISTAS_ORIGINALES if os.path.isdir(_LISTAS_ORIGINALES) else os.getcwd()
        path = filedialog.askopenfilename(
            title="Seleccionar archivo XLSX",
            initialdir=initial,
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos", "*.*")],
        )
        if not path:
            return
        self._file_path = path
        self._show_file_selected()
        self._after_file_select()

    def _show_file_selected(self):
        fname = self._file_path.split("/")[-1]
        self._file_label.configure(text=f"Archivo: {fname}")
        self._file_label.pack(pady=(0, 10))
        self._cancel_btn.pack(side="right", padx=(0, 10), pady=(0, 10))
        self._drop_frame.configure(fg_color="#e8f5e9", border_color="#2e7d32")

    def _close_wb(self):
        if self._wb is not None:
            try:
                if hasattr(self._wb, 'close'):
                    self._wb.close()
            except Exception:
                pass
            self._wb = None
        self._sheet_names = []

    def _reset_drop_zone(self):
        self._close_wb()
        self._file_path = ""
        self._file_label.pack_forget()
        self._cancel_btn.pack_forget()
        self._drop_frame.configure(fg_color="#f0f4f8", border_color="#90a4ae")

    def _cancel_selection(self):
        self._reset_drop_zone()
        self._preview_rows = []
        self._raw_rows = []
        self._import_btn.configure(state="disabled")
        self._summary_label.configure(text="Seleccione un archivo Excel para comenzar")
        self._supplier_var.set("")
        self._supplier_other_entry.grid_remove()
        self._supplier_other_entry.delete(0, "end")
        self._date_entry.delete(0, "end")
        self._date_entry.insert(0, date.today().isoformat())
        self._hide_mapping()

    def _read_file_rows(self, sheet_name=None):
        ext = self._file_path.lower()
        if ext.endswith(".xlsx"):
            import openpyxl
            self._wb = openpyxl.load_workbook(self._file_path, read_only=True, data_only=True)
            self._sheet_names = self._wb.sheetnames
            if sheet_name and sheet_name in self._sheet_names:
                ws = self._wb[sheet_name]
            else:
                ws = self._wb.active
            rows = list(ws.iter_rows(values_only=True))
            return rows
        elif ext.endswith(".xls"):
            import xlrd
            self._wb = xlrd.open_workbook(self._file_path)
            self._sheet_names = self._wb.sheet_names()
            if sheet_name and sheet_name in self._sheet_names:
                ws = self._wb.sheet_by_name(sheet_name)
            else:
                ws = self._wb.sheet_by_index(0)
            return [tuple(ws.row_values(r)) for r in range(ws.nrows)]
        else:
            raise ValueError("Formato no soportado. Use .xlsx o .xls")

    def _after_file_select(self):
        try:
            rows = self._read_file_rows()
        except ImportError as e:
            lib = "openpyxl" if self._file_path.lower().endswith(".xlsx") else "xlrd"
            messagebox.showerror("Error", f"Debe instalar {lib}: pip install {lib}")
            return
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{str(e)}")
            return

        if not rows:
            messagebox.showwarning("Advertencia", "El archivo esta vacio")
            return

        self._raw_rows = rows

        # Populate sheet selector (always use first sheet)
        if len(self._sheet_names) > 1:
            self._sheet_combo.configure(values=self._sheet_names)
            self._sheet_var.set(self._sheet_names[0])
            self._sheet_combo.grid()
        else:
            self._sheet_var.set("")
            self._sheet_combo.configure(values=[""])
            self._sheet_combo.grid_remove()

        try:
            self._auto_detect_from_headers()
        except Exception:
            pass
        self._show_mapping()
        self._update_raw_preview()

    def _on_sheet_change(self, *args):
        sheet = self._sheet_var.get()
        if not sheet or not self._file_path:
            return
        self._close_wb()
        try:
            rows = self._read_file_rows(sheet_name=sheet)
        except Exception:
            return
        if not rows:
            return
        self._raw_rows = rows
        try:
            self._auto_detect_from_headers()
        except Exception:
            pass
        self._update_raw_preview()

    def _update_raw_preview(self):
        """Muestra las primeras filas del archivo en la previsualizacion."""
        max_rows = min(8, len(self._raw_rows))
        max_cols = 0
        for r in range(max_rows):
            row = self._raw_rows[r]
            if row:
                max_cols = max(max_cols, len(row))
        max_cols = min(max_cols, 12)

        lines = []
        for r in range(max_rows):
            vals = []
            row = self._raw_rows[r]
            for c in range(max_cols):
                v = row[c] if row and c < len(row) and row[c] is not None else ""
                vals.append(f"{_col_letter(c)}:{str(v)[:25]}")
            lines.append(f"  F{r}: " + "  |  ".join(vals))

        self._preview_text.delete("1.0", "end")
        self._preview_text.insert("1.0", "\n".join(lines))

    def _detect_fgp_format(self, rows):
        for i, row in enumerate(rows):
            if row and len(row) > 0:
                val = str(row[0]).strip().lower()
                if val == "codigo" or val.startswith("código"):
                    return i
        return None

    def _auto_detect_from_headers(self):
        """Detecta columnas buscando encabezados conocidos."""
        rows = self._raw_rows
        if not rows:
            return

        self._ignore_trace = True
        try:
            # Try FGP first (must have Codigo + Detalle + Descripcion)
            fgp_idx = self._detect_fgp_format(rows)
            if fgp_idx is not None and _fgp_looks_valid(rows, fgp_idx):
                    self._header_var.set(str(fgp_idx))
                    self._name_col_var.set("C")
                    self._cat_col_var.set("B")
                    self._price_col_var.set("F")
                    self._name_from_two_var.set(True)
                    self._desc_col_var.set("C")
                    self._code_col_var.set("Ninguna")
                    self._size_col_var.set("Ninguna")
                    self._apply_mapping()
                    return

            # Try to find a header row with known keywords
            best_row = None
            best_score = 0
            best_mapping = {}

            for i, row in enumerate(rows[:20]):
                if not row:
                    continue
                score = 0
                mapping = {}
                for c, val in enumerate(row[:10]):
                    if val is None:
                        continue
                    label = str(val).strip().lower()
                    if not label:
                        continue
                    for keyword, target in HEADER_KEYWORD_MAP:
                        if keyword in label:
                            if target and target not in mapping:
                                mapping[target] = c
                                score += 1
                            elif target is None:
                                score += 0.5
                            break
                if score > best_score:
                    best_score = score
                    best_row = i
                    best_mapping = mapping

            if best_row is not None and best_score > 0:
                self._header_var.set(str(best_row))
                if "name" in best_mapping:
                    self._name_col_var.set(_col_letter(best_mapping["name"]))
                if "category" in best_mapping:
                    self._cat_col_var.set(_col_letter(best_mapping["category"]))
                else:
                    self._cat_col_var.set("Ninguna")
                if "price" in best_mapping:
                    self._price_col_var.set(_col_letter(best_mapping["price"]))
                else:
                    self._detect_price_column(rows, best_row)
                if "code" in best_mapping:
                    self._code_col_var.set(_col_letter(best_mapping["code"]))
                else:
                    self._code_col_var.set("Ninguna")
                if "size" in best_mapping:
                    self._size_col_var.set(_col_letter(best_mapping["size"]))
                else:
                    self._size_col_var.set("Ninguna")
            else:
                self._header_var.set("0")
                self._name_col_var.set("A")
                self._cat_col_var.set("Ninguna")
                self._price_col_var.set("C")
                self._code_col_var.set("Ninguna")
                self._size_col_var.set("Ninguna")

            self._name_from_two_var.set(False)
            self._desc_col_var.set("Ninguna")
        finally:
            self._ignore_trace = False

        self._apply_mapping()

    def _detect_price_column(self, rows, header_row):
        """Busca la columna que parece contener precios (numeros chicos con decimales)."""
        start = header_row + 1
        max_cols = min(10, len(rows[0]) if rows else 1)
        max_items = min(30, len(rows) - start)

        best_col = None
        best_score = 0

        for col in range(max_cols):
            vals = []
            for r in range(start, start + max_items):
                val = rows[r][col] if rows[r] and col < len(rows[r]) else None
                if val is not None:
                    try:
                        f = float(str(val))
                        vals.append(f)
                    except ValueError:
                        pass
            if len(vals) < max_items // 2:
                continue
            avg = sum(vals) / len(vals)
            has_decimals = any(v != int(v) for v in vals)
            score = len(vals) + (50 if has_decimals else 0)
            if 0.01 < avg < 1000000:
                score += 100
            if best_col is None or score > best_score:
                best_col = col
                best_score = score

        if best_col is not None:
            self._price_col_var.set(_col_letter(best_col))

    def _get_mapping(self):
        try:
            header_row = int(self._header_var.get())
        except ValueError:
            header_row = 0

        name_col = _col_index(self._name_col_var.get())
        cat_raw = self._cat_col_var.get()
        cat_col = _col_index(cat_raw) if cat_raw != "Ninguna" else None
        price_col = _col_index(self._price_col_var.get())
        use_two = self._name_from_two_var.get()
        desc_raw = self._desc_col_var.get()
        desc_col = _col_index(desc_raw) if desc_raw != "Ninguna" else None
        code_raw = self._code_col_var.get()
        code_col = _col_index(code_raw) if code_raw != "Ninguna" else None
        size_raw = self._size_col_var.get()
        size_col = _col_index(size_raw) if size_raw != "Ninguna" else None

        return {
            "header_row": header_row,
            "name_col": name_col,
            "cat_col": cat_col,
            "price_col": price_col,
            "use_two_names": use_two,
            "desc_col": desc_col,
            "code_col": code_col,
            "size_col": size_col,
        }

    def _apply_mapping(self, event=None):
        """Aplica el mapeo actual y genera el preview de importacion."""
        mapping = self._get_mapping()
        rows = self._raw_rows
        if not rows:
            return

        header_row = mapping["header_row"]
        start = header_row + 1 if header_row >= 0 else 0
        name_col = mapping["name_col"]
        cat_col = mapping["cat_col"]
        price_col = mapping["price_col"]
        use_two = mapping["use_two_names"]
        desc_col = mapping["desc_col"]
        code_col = mapping["code_col"]
        size_col = mapping["size_col"]

        parsed = []
        for row in rows[start:]:
            if not row:
                continue

            row_name = str(row[name_col]).strip() if name_col < len(row) and row[name_col] is not None else ""
            if not row_name or row_name.lower() in ("total", "subtotal"):
                continue

            if use_two and desc_col is not None:
                detalle = str(row[cat_col]).strip() if cat_col is not None and cat_col < len(row) and row[cat_col] is not None else ""
                descripcion = str(row[desc_col]).strip() if desc_col < len(row) and row[desc_col] is not None else ""
                tamaño = str(row[size_col]).strip() if size_col is not None and size_col < len(row) and row[size_col] is not None else ""
                if name_col == desc_col:
                    # FGP style: name_col is same as desc_col, use "detalle - descripcion"
                    parts = [p for p in [detalle, descripcion, tamaño] if p]
                    name = " - ".join(parts) if parts else row_name
                else:
                    # Standard style: prepend name_col base + append descripcion + tamaño
                    extra = [p for p in [descripcion, tamaño] if p]
                    name = f"{row_name} - {' - '.join(extra)}" if extra else row_name
                category = detalle
            else:
                name = row_name
                if cat_col is not None and cat_col < len(row) and row[cat_col] is not None:
                    category = str(row[cat_col]).strip()
                    if category and name != category:
                        name = f"{category} - {name}"
                else:
                    category = ""

            if price_col < len(row):
                try:
                    sp = Decimal(str(row[price_col]))
                except Exception:
                    continue
            else:
                continue

            if sp <= 0:
                continue

            codigo = str(row[code_col]).strip() if code_col is not None and code_col < len(row) and row[code_col] is not None else ""

            parsed.append({"name": name, "category": category, "supplier_price": sp, "code": codigo})

        self._preview_rows = parsed
        self._show_summary()

    def _get_margin_value(self):
        try:
            pct = int(self._margin_entry.get().strip())
            return max(0, pct) + 100
        except ValueError:
            return self._settings.get_profit_margin()

    def _show_summary(self):
        """Muestra el resumen de los datos parseados."""
        if not self._preview_rows:
            self._summary_label.configure(text="No se encontraron productos validos con ese mapeo.")
            self._import_btn.configure(state="disabled")
            return

        rate = self._settings.get_usd_rate()
        margin = self._get_margin_value()

        margen_pct = margin - 100
        prices = [r["supplier_price"] for r in self._preview_rows]
        total = len(self._preview_rows)
        min_p = min(prices)
        max_p = max(prices)
        avg_p = sum(prices) / total

        ejemplos = "\n".join(
            f"  - $ {r['supplier_price']:>10,.2f}  |  {r['name']}"
            for r in self._preview_rows[:3]
        )

        fname = self._file_path.split("/")[-1]
        summary = (
            f"Archivo: {fname}\n"
            f"Productos encontrados: {total}\n"
            f"Rango de precios: $ {min_p:,.2f} a $ {max_p:,.2f}\n"
            f"Precio promedio: $ {avg_p:,.2f}\n"
            f"Margen de ganancia: +{margen_pct}%\n\n"
            f"Ejemplos:\n{ejemplos}\n"
            f"{'  ...' if total > 3 else ''}"
        )
        self._summary_label.configure(text=summary)
        self._import_btn.configure(state="normal")

    def _get_supplier(self):
        selected = self._supplier_var.get()
        if selected == "Otro":
            return self._supplier_other_entry.get().strip()
        return selected.strip()

    def _import_list(self):
        supplier = self._get_supplier()
        date_str = self._date_entry.get().strip()

        if not supplier:
            messagebox.showwarning("Advertencia", "Ingrese el nombre del proveedor")
            return

        try:
            list_date = date.fromisoformat(date_str)
        except ValueError:
            messagebox.showwarning(
                "Advertencia", "Ingrese una fecha valida (YYYY-MM-DD)"
            )
            return

        if not self._preview_rows:
            messagebox.showwarning("Advertencia", "No hay datos para importar")
            return

        rate = self._settings.get_usd_rate()
        margin = self._get_margin_value()

        try:
            fname = os.path.basename(self._file_path)
            result = self._list_service.import_from_xls_rows(
                self._preview_rows,
                supplier,
                list_date,
                rate,
                margin,
                filename=fname,
            )
            msg = (
                f"Proveedor: {supplier}\n"
                f"Fecha lista: {list_date}\n"
                f"Margen: +{margin - 100}%\n\n"
                f" Nuevos: {result['imported']}\n"
                f" Actualizados: {result['updated']}\n"
                f" Saltados (ya hay precio mas reciente): {result['skipped']}\n"
                f" Total procesados: {sum(result.values())}"
            )
            messagebox.showinfo("Importacion completada", msg)

            self._close_wb()
            os.makedirs(_LISTAS_SUBIDAS, exist_ok=True)
            fname = os.path.basename(self._file_path)
            dest = os.path.join(_LISTAS_SUBIDAS, fname)
            try:
                shutil.move(self._file_path, dest)
            except Exception:
                pass
            self._file_path = ""

            self._preview_rows = []
            self._import_btn.configure(state="disabled")
            self._summary_label.configure(
                text="Seleccione un archivo Excel para comenzar"
            )
            self._supplier_var.set("")
            self._supplier_other_entry.grid_remove()
            self._supplier_other_entry.delete(0, "end")
            self._load_suppliers()
            self._refresh_uploaded_lists()
            self._date_entry.delete(0, "end")
            self._date_entry.insert(0, date.today().isoformat())
            default_margin = self._settings.get_profit_margin() - 100
            self._margin_entry.delete(0, "end")
            self._margin_entry.insert(0, str(default_margin))
            self._hide_mapping()
            self._reset_drop_zone()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _refresh_uploaded_lists(self):
        for w in self._uploaded_scroll.winfo_children():
            w.destroy()
        lists = self._list_service.get_uploaded_lists()
        if not lists:
            ctk.CTkLabel(self._uploaded_scroll, text="No hay listas subidas.", text_color="gray").pack(pady=10)
            return
        for ul in lists:
            row = ctk.CTkFrame(self._uploaded_scroll, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)
            info = f"{ul.filename}  |  {ul.supplier}  |  {ul.list_date}"
            ctk.CTkLabel(row, text=info, anchor="w", font=("Arial", 11)).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="Eliminar", fg_color="#c62828", width=80, height=26,
                font=("Arial", 10),
                command=lambda lid=ul.id: self._confirm_delete_list(lid),
            ).pack(side="right", padx=5)

    def _confirm_delete_list(self, list_id: int):
        lists = self._list_service.get_uploaded_lists()
        target = next((u for u in lists if u.id == list_id), None)
        if not target:
            return
        ok = messagebox.askyesno(
            "Eliminar lista",
            f"Eliminar todos los productos de {target.supplier} "
            f"con fecha {target.list_date} (archivo: {target.filename})?",
        )
        if not ok:
            return
        deleted = self._list_service.delete_uploaded_list(list_id)
        self._refresh_uploaded_lists()
        self._load_suppliers()
        messagebox.showinfo("Lista eliminada", f"Se eliminaron {deleted} productos.")
