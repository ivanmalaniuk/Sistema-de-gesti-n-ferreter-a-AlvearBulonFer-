import os
import subprocess
import sys


def test_arranque_no_carga_openpyxl_ni_xlrd():
    """Fija el criterio de aceptacion 'arranque sin cargar openpyxl/xlrd'.

    Este test es un cerrojo de regresion: la importacion perezosa ya estaba
    implementada en load_list_view._read_file_rows, por lo que pasa antes de
    cualquier cambio en la vista. Lo dejamos para que futuras ediciones no
    carguen openpyxl ni xlrd al importar la ventana principal.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, '.'); "
        "import src.presentation.main_window; "
        "sys.exit(0 if ('openpyxl' not in sys.modules and 'xlrd' not in sys.modules) else 1)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
