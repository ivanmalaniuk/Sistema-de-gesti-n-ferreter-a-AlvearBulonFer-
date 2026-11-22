# Build de Ferretería en Windows (PyInstaller --onedir)

Genera `dist/Ferreteria/` con `Ferreteria.exe` y sus DLLs. Esa carpeta completa se
copia a la PC del local y la app corre sin instalar Python.

## Camino rápido

1. Compilar en **Windows 11** con **Python 3.12 o 3.13** y **Tk 8.6**.
2. Instalar PyInstaller en la máquina de build:
   `python -m pip install -r requirements-build.txt`
3. Generar el bundle:
   `python -m PyInstaller Ferreteria.spec --noconfirm`
4. Probar: ejecutar `dist/Ferreteria/Ferreteria.exe`.
5. Copiar la carpeta `dist/Ferreteria` completa a la PC del local.

## Instalación en la PC del local

- Copiar **toda** la carpeta `dist/Ferreteria`, no solo el `.exe`.
- No usar `C:\Program Files`: la base y los backups se escriben junto al `.exe` y
  esa carpeta necesita permiso de escritura. Usar por ejemplo `C:\Ferreteria`.
- No hace falta instalar Python en la PC del local.
- Si ya hay datos, copiar `ferreteria.db` dentro de la carpeta del `.exe` para
  conservarlos. Los backups se crean en la subcarpeta configurada.

## Detalles

| Tema | Decisión |
|---|---|
| Modo | `--onedir` (spec `Ferreteria.spec`). **Nunca `--onefile`**: descomprime en cada arranque y es lento en la PC vieja. |
| Datos | El spec incluye `src/recursos` y los assets de CustomTkinter. |
| Imports perezosos | Declara `openpyxl`, `xlrd`, `fpdf`, `tkinterdnd2`, `PIL.ImageTk` y `darkdetect`. |
| Consola | `console=True`: `main.py` imprime el traceback y espera Enter si falla al arrancar. |
| UPX | Desactivado (`upx=False`) por compatibilidad y velocidad. |

## Checklist

- [ ] Build hecho en Windows 11 con Python 3.12/3.13 y Tk 8.6.
- [ ] `dist/Ferreteria/Ferreteria.exe` abre la app.
- [ ] La base `ferreteria.db` se crea junto al `.exe`.
- [ ] `src/recursos/boleta.pdf` y las imágenes están dentro del bundle.
- [ ] La carpeta completa se copió a la PC del local en una ruta con escritura.
