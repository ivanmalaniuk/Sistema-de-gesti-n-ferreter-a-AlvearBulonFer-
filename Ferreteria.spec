# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller en modo --onedir para Ferreteria.

Nunca usar --onefile: descomprime todo en cada arranque y la PC del local es lenta.
Genera dist/Ferreteria/ con Ferreteria.exe y sus DLLs al lado.
"""

from PyInstaller.utils.hooks import collect_data_files

# Recursos propios de la app (imagenes, PDF de boleta) + assets de CustomTkinter
datas = [
    ("src/recursos", "src/recursos"),
]
datas += collect_data_files("customtkinter")

# Imports perezosos u opcionales que PyInstaller no detecta por si solo
hiddenimports = [
    "openpyxl",
    "xlrd",
    "fpdf",
    "tkinterdnd2",
    "PIL.ImageTk",
    "darkdetect",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Ferreteria",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Ferreteria",
)
