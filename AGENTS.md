# AGENTS.md — Ferretería Alvear Bulon Fer

> Leer este archivo completo al iniciar la sesión. Es la fuente de verdad del proyecto.
> `CONTEXT.md` es documentación histórica para humanos: NO leerlo salvo que se pida. Si difieren, manda este archivo.
> Última actualización: 2026-11-13

## 1. Qué es

App de escritorio para gestionar caja y ventas de una ferretería. Python + CustomTkinter (GUI) + SQLite local.
Sin internet, sin servidores, instalación mínima. Código e interfaz en **español**.
Repo: https://github.com/ivanmalaniuk/Sistema-de-gesti-n-ferreter-a-AlvearBulonFer- (usuario GitHub: `ivanmalaniuk`).

## 2. Prioridades (en este orden)

1. **Confiabilidad**: nunca perder ni corromper datos de ventas/gastos.
2. **Rapidez**: la PC del local es lenta. Arranque y cada pestaña deben abrir rápido.
3. **Simplicidad**: el usuario final no sabe programar; la interfaz debe ser obvia.
4. Todo lo demás (estética, features extra) va después.

## 3. Entorno y uso real

- **PC del local**: Windows 11, hardware lento (poca potencia). Probar ahí, no solo en el equipo de desarrollo.
- **Desarrollo**: Fedora Linux, Python 3.14.x, Tk 9.0, CustomTkinter 6.0.0 (versiones muy nuevas → origen de varios bugs, ver §7).
- **Usuario final**: el encargado del negocio, un solo usuario, un solo equipo, uso diario (ventas al mostrador, gastos, listas de precios del proveedor, reportes mensuales).
- **Empaquetado a Windows** (cuando toque): PyInstaller en modo `--onedir`, NO `--onefile` (onefile se descomprime en cada arranque y es lento en PC vieja).
- Verificar versión de Tk con `python -c "import tkinter; print(tkinter.TkVersion)"`.

## 4. Reglas de trabajo para el agente

**Anti-sobreingeniería (importante)**
- Hacer lo mínimo que resuelve la tarea. Sin capas, patrones, clases base ni abstracciones nuevas.
- No agregar dependencias sin preguntar. No usar pandas ni librerías pesadas.
- No refactorizar código que no está en la tarea. No reformatear archivos enteros.
- Si hay dos soluciones, elegir la más simple y más liviana, y decir en una línea por qué.


**Ahorro de tokens**
- Leer solo los archivos necesarios para la tarea; usar búsqueda (grep) antes de abrir archivos grandes.
- No releer lo que ya se leyó en la sesión. No pegar archivos completos en las respuestas; mostrar solo el diff o la parte cambiada.
- Respuestas cortas: qué se hizo, qué archivos, cómo probarlo.
- Usar el orquestador/subagentes solo para features que tocan varias capas a la vez.
- Modo plan solo para tareas grandes; para bugs y cambios chicos ir directo.
- Explicaciones sensillas

**Skills**
- Hay skills descargadas en este equipo porque se usan en OTROS proyectos. **No son necesariamente útiles acá.** La unica que si se utilizara es caveman (npx skills add https://github.com/juliusbrussee/caveman --skill caveman)
- No listarlas, no leerlas y no invocarlas por defecto. Usar una solo si la tarea la requiere claramente o si el usuario lo pide.

**Código**
- Responder y comentar en español. Nombres de dominio ya existentes en inglés (Product, Sale…) se mantienen.
- Capas: `domain → application → infrastructure → presentation`. La UI nunca ejecuta SQL; los servicios dependen de las interfaces de `domain`.
- Listas largas: `ttk.Treeview` + SQL con `LIMIT`; nunca un widget por fila.
- Operaciones que tocan varias tablas (ej. venta + ítems): una sola transacción.
- Cada cambio de lógica de negocio lleva su test en `tests/`. Correr `python -m pytest tests/ -q` antes de cerrar la tarea.
- No tocar `ferreteria.db`, backups ni listas de precios reales.

## 5. Arquitectura (resumen)

```
main.py                      # ensambla dependencias
src/domain/                  # entities.py (Product, SaleItem, Sale, Expense), interfaces.py (IProductRepo, ISaleRepo, IExpenseRepo, ISettingsRepo)
src/application/             # product_, sale_, expense_, report_, list_, settings_service.py
src/infrastructure/          # database.py + un repositorio SQLite por entidad
src/presentation/            # app.py, main_window.py, vistas por pestaña, settings_dialog.py, wheel_scroll.py
tests/                       # un test por servicio (29 tests pasando a la fecha)
```

Pestañas: Registrar Venta, Registrar Gasto, Productos, Reportes, Cargar Lista, Configuración (⚙). Hay además vistas de Crear Boleta, Faltantes, historial de ventas y comparar mercados.

## 6. Datos

SQLite (WAL, foreign keys ON). Se crea sola en la raíz al primer arranque.

- `products`: id, name, category, supplier, list_date, supplier_price, selling_price, unit_quantity (1 = unitario), unit_price, price_usd, selling_price_usd, created_at
- `sales`: id, total_amount, created_at
- `sale_items`: id, sale_id→sales, product_id→products, quantity (en unidades), unit_price (al momento de la venta), subtotal
- `expenses`: id, description, amount, date, category (Insumos, Servicios, Alquiler…), created_at
- `settings`: key, value → `usd_rate` (default 1500), `profit_margin` (default 160), `backup_dir` (default `backups`), `backup_keep` (default 10)

Dinero hoy: `REAL` en SQLite, convertido a `Decimal` en Python. **Cambio planeado**: guardar en centavos enteros (ver §8).

**Fórmulas de precio** (al importar y al recalcular):
```
selling_price     = supplier_price * (profit_margin / 100)    # 160 = margen del 60%
price_usd         = supplier_price / usd_rate
selling_price_usd = price_usd * (profit_margin / 100)
unit_price        = selling_price / unit_quantity
```

**Importación de listas**
- Formato simple (XLSX): col0 nombre, col1 categoría, col2 precio proveedor; con o sin encabezado.
- Formato FGP mayorista (XLS viejo): header detectado buscando "Codigo" en col 0; se saltean ~20 filas iniciales; columnas: Codigo, Detalle (categoría), Descripcion, Precio lista, IVA %, **Precio con IVA**. **Se toma col 5 (con IVA), NO col 3.** Nombre = `"{Detalle} - {Descripcion}"`. Si no se detecta FGP, se usa el formato simple.

## 7. Problemas conocidos y soluciones

| Problema | Causa | Estado / solución |
|---|---|---|
| Crash al iniciar (`bgerror ... invalid command name`) | `tkinterdnd2` incompatible con Tk 9.0 como clase base de `App` | Resuelto: `app.py` fuerza `ctk.CTk`. Drag & drop de archivos deshabilitado |
| Rueda del ratón no scrolleaba | Handler de `CTkScrollableFrame` falla con Tk 9.0 | Resuelto con `wheel_scroll.py` (handler global). Se elimina al migrar a Treeview |
| Crash/lentitud en vista previa de listas | Cientos de `CTkLabel` | Resuelto: un solo label con resumen de texto |
| Lentitud general en PC del local | CustomTkinter dibuja cada widget en Canvas; tablas con widgets por fila; versiones nuevas de Python/Tk | Pendiente: Treeview, fijar versiones estables, medir (§8) |
| Sin respaldo de datos | No implementado | Resuelto (2026-11-13): backup automático al cerrar, API de sqlite3, carpeta/N configurables (issue #2) |

## 8. Backlog priorizado (crear un issue por ítem, en este orden)

1. ~~Backup automático al cerrar la app (API de backup de sqlite3, copia a otra carpeta/USB, conservar las últimas N).~~ Hecho (issue #2).
2. Fijar versiones estables (Python 3.12/3.13, Tk 8.6 si aplica) y documentarlas en `requirements.txt`.
3. Medir tiempo de arranque y de apertura de cada pestaña (idealmente en la PC del local) y registrar resultados aquí.
4. Reemplazar listas de widgets por `ttk.Treeview` (productos, ítems de venta, historial); búsqueda con SQL + `LIMIT` y *debounce*; borrar `wheel_scroll.py`.
5. Índices en `products.name`, `sales.created_at`, `sale_items.sale_id`, `expenses.date`; `PRAGMA synchronous=NORMAL` con WAL; ventas en una transacción.
6. Importación de listas: imports perezosos (`openpyxl`/`xlrd` solo al abrir la pestaña), procesar en hilo con progreso.
7. Dinero en centavos enteros (migración de datos incluida y probada con copia de la base).
8. Empaquetado PyInstaller `--onedir` para Windows 11.

Ideas futuras (NO hacer sin pedido): exportar reportes a PDF/Excel, gráficos mensuales, historial de listas por proveedor, control de stock.

## 9. Flujo Git / GitHub (usar `gh`)

- Un issue = una rama = un PR chico. Nunca push directo a `main`.
- Flujo: `gh issue create` → `git switch -c tipo/N-slug` (tipo: feat, fix, chore, docs) → commits convencionales (`feat:`, `fix:`, `chore:`, `docs:`) → `gh pr create` con `Closes #N` en el cuerpo.
- Antes del PR: tests en verde. Descripción del PR de 3–5 líneas: qué cambia, cómo probarlo.
- **No hacer merge sin confirmación del usuario.** Después del merge, volver a `main` y actualizar.
- Nunca commitear: `*.db`, `*.db-wal`, `*.db-shm`, backups, listas de precios (`.xls`/`.xlsx`), `.venv`, `__pycache__`. Verificar `.gitignore` antes del primer commit de cada sesión.
- Labels mínimos: `bug`, `feat`, `chore`, `docs`.

## 10. Mantenimiento de este archivo (el agente lo actualiza)

Al terminar cada tarea (antes de abrir el PR), actualizar este archivo en el mismo commit con prefijo `docs:`:
- §7: agregar problemas nuevos o marcar los resueltos.
- §8: tachar lo hecho y ajustar el orden si cambió algo.
- §3, §5, §6: reflejar cambios reales de entorno, estructura o esquema de datos.
- §11: agregar UNA línea de changelog (fecha, qué, issue/PR).
- Actualizar la fecha de "Última actualización".

Límites:
- Cambios mínimos y puntuales (editar la línea afectada, no reescribir secciones).
- **No modificar §2, §4 ni §9** sin aprobación explícita del usuario; si cree que hay que cambiarlas, proponerlo en la respuesta.
- Mantener el archivo por debajo de ~250 líneas: al superar §11 las 15 entradas, mover las más viejas a `CHANGELOG.md`.
- Solo registrar hechos verificados (tests corridos, cambios hechos), nunca suposiciones.

## 11. Changelog

- 2026-07-23 — Versión inicial: arquitectura en capas, CRUD de productos, ventas, gastos, reportes, importación XLSX y FGP, 29 tests.
- 2026-08-01 — Fix: rueda del ratón vía `wheel_scroll.py`.
- 2026-11-13 — Creado AGENTS.md; definido backlog de rendimiento y confiabilidad.
- 2026-11-13 — Backup automático al cerrar la app (issue #2): `backup.py`, settings `backup_dir`/`backup_keep`, 39 tests.
