# Ferreteria Alvear Bulon Fer — Sistema de Gestion

## Descripcion General

Aplicacion de escritorio para gestion de flujo de caja y ventas de una ferreteria.
Desarrollada en Python con CustomTkinter (GUI) y SQLite (base de datos local).
Sin dependencia de internet, sin servidores, sin instalacion compleja.

**Usuario objetivo:** El encargado del negocio, sin conocimientos de programacion.
**Idioma:** Espanol (interfaz y codigo fuente).

---

## Arquitectura — Capas (Layered Architecture)

```
┌──────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                    │
│                    (Interfaz de Usuario)                 │
│  CustomTkinter — Ventanas, formularios, tablas, dialogos │
│  Depende de: Application Layer (servicios inyectados)   │
├──────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                     │
│                    (Casos de Uso / Servicios)            │
│  ProductService  │  SaleService  │  ExpenseService       │
│  ListService     │  SettingsService  │  ReportService    │
│  Orquesta la logica, valida reglas de negocio            │
│  Depende de: Domain Layer (interfaces de repositorio)   │
├──────────────────────────────────────────────────────────┤
│                    DOMAIN LAYER                          │
│                    (Modelo de Negocio)                   │
│  Entities: Product, SaleItem, Sale, Expense             │
│  Interfaces: IProductRepo, ISaleRepo, IExpenseRepo,     │
│              ISettingsRepo                              │
│  Sin dependencias externas (Python puro + dataclasses)  │
├──────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE LAYER                  │
│                    (Persistencia / Datos)                │
│  SQLite3 (WAL mode, foreign keys ON)                    │
│  Implementaciones concretas de cada repositorio         │
│  Depende de: Domain Layer (interfaces)                  │
└──────────────────────────────────────────────────────────┘
```

### Flujo de datos tipico

```
[UI Evento] → [Service.validate()] → [Repository Interface]
    → [SQLiteRepository] → [SQLite DB]
    → [Domain Entity] ← [Service] ← [Repository returns Entity]
    → [UI actualiza con datos de la entidad]
```

---

## Principios SOLID aplicados

| Principio | Donde se aplica |
|---|---|
| **S**ingle Responsibility | Cada clase tiene una responsabilidad clara: Entities solo modelan datos, Services solo orquestan casos de uso, Repositories solo persisten |
| **O**pen/Closed | Las interfaces de repositorio permiten agregar nuevas implementaciones (SQLite, memoria, archivo) sin modificar el dominio |
| **L**iskov Substitution | Cualquier implementacion de repositorio es intercambiable |
| **I**nterface Segregation | 4 interfaces pequeñas (Product, Sale, Expense, Settings) en lugar de una enorme |
| **D**ependency Inversion | El dominio define las interfaces; las capas superiores dependen de abstracciones, no de concreciones |

---

## Estructura del Proyecto

```
proyecto_ferreteria/
│
├── main.py                     # Punto de entrada — ensambla el grafo de dependencias
├── requirements.txt            # Dependencias Python (pip install -r)
├── ferreteria.db               # Base de datos SQLite (se genera automaticamente)
├── CONTEXT.md                  # Este archivo — documentacion viva del proyecto
│
├── src/
│   ├── __init__.py
│   │
│   ├── domain/                 # CAPA DE DOMINIO — El corazon del negocio
│   │   ├── __init__.py
│   │   ├── entities.py         # Product, SaleItem, Sale, Expense (dataclasses)
│   │   └── interfaces.py       # IProductRepo, ISaleRepo, IExpenseRepo, ISettingsRepo
│   │
│   ├── application/            # CAPA DE APLICACION — Casos de uso
│   │   ├── __init__.py
│   │   ├── product_service.py  # CRUD + busqueda + recalculo de precios
│   │   ├── sale_service.py     # Registrar venta, calcular totales
│   │   ├── expense_service.py  # Registrar gastos
│   │   ├── report_service.py   # Reportes mensuales (ingresos/gastos/ganancia)
│   │   ├── list_service.py     # Importacion de listas de precios desde XLSX
│   │   └── settings_service.py # Configuracion (USD, margen de ganancia)
│   │
│   ├── infrastructure/         # CAPA DE INFRAESTRUCTURA — Persistencia
│   │   ├── __init__.py
│   │   ├── database.py         # Conexion SQLite, creacion de tablas
│   │   ├── product_repository.py
│   │   ├── sale_repository.py
│   │   ├── expense_repository.py
│   │   └── settings_repository.py
│   │
│   └── presentation/           # CAPA DE PRESENTACION — Interfaz grafica
│       ├── __init__.py
│       ├── app.py              # Ventana principal (CustomTkinter)
│       ├── main_window.py      # Tabs del programa
│       ├── register_sale_view.py   # Pestana: Registrar Venta
│       ├── register_expense_view.py# Pestana: Registrar Gasto
│       ├── manage_products_view.py # Pestana: Productos
│       ├── reports_view.py         # Pestana: Reportes
│       ├── load_list_view.py       # Pestana: Cargar Lista de Precios
│       └── settings_dialog.py      # Dialogo: Configuracion (USD, margen)
│
└── tests/                      # TESTS UNITARIOS (TDD)
    ├── __init__.py
    ├── test_product_service.py
    ├── test_sale_service.py
    ├── test_expense_service.py
    ├── test_report_service.py
    ├── test_settings_service.py
    └── test_list_service.py
```

---

## Base de Datos — Esquema SQLite

### Tabla: `products`

| Columna | Tipo | Descripcion |
|---|---|---|
| id | INTEGER PK | Identificador unico |
| name | TEXT | Nombre del producto |
| category | TEXT | Categoria (ej: Herramientas, Ferreteria) |
| supplier | TEXT | Nombre del proveedor |
| list_date | TEXT | Fecha de la lista de precios (ISO date) |
| supplier_price | REAL | Precio que paga el proveedor ($ arg.) |
| selling_price | REAL | Precio de venta al publico ($ arg.) |
| unit_quantity | INTEGER | Cantidad de unidades por paquete (1 = unitario) |
| unit_price | REAL | Precio por unidad individual |
| price_usd | REAL | Precio proveedor en dolares |
| selling_price_usd | REAL | Precio venta en dolares |
| created_at | TEXT | Fecha de creacion del registro (ISO datetime) |

### Tabla: `sales`

| Columna | Tipo | Descripcion |
|---|---|---|
| id | INTEGER PK | Identificador unico |
| total_amount | REAL | Monto total de la venta |
| created_at | TEXT | Fecha y hora de la venta |

### Tabla: `sale_items`

| Columna | Tipo | Descripcion |
|---|---|---|
| id | INTEGER PK | Identificador unico |
| sale_id | INTEGER FK → sales.id | Venta a la que pertenece |
| product_id | INTEGER FK → products.id | Producto vendido |
| quantity | INTEGER | Cantidad vendida (en unidades) |
| unit_price | REAL | Precio por unidad al momento de la venta |
| subtotal | REAL | quantity * unit_price |

### Tabla: `expenses`

| Columna | Tipo | Descripcion |
|---|---|---|
| id | INTEGER PK | Identificador unico |
| description | TEXT | Descripcion del gasto |
| amount | REAL | Monto del gasto |
| date | TEXT | Fecha del gasto |
| category | TEXT | Categoria (Insumos, Servicios, Alquiler, etc.) |
| created_at | TEXT | Fecha de creacion del registro |

### Tabla: `settings`

| Columna | Tipo | Descripcion |
|---|---|---|
| key | TEXT PK | Nombre de la configuracion |
| value | TEXT | Valor |

**Valores por defecto:**
- `usd_rate` = `1500` (tipo de cambio del dolar)
- `profit_margin` = `160` (margen de ganancia en porcentaje)

---

## Logica de Precios

### Formulas aplicadas al importar listas (y al recalcular)

```
selling_price = supplier_price * (profit_margin / 100)
price_usd     = supplier_price / usd_rate
selling_price_usd = price_usd * (profit_margin / 100)
unit_price    = selling_price / unit_quantity
```

- `profit_margin` por defecto = 160 (es decir, 160% = margen del 60%)
- `usd_rate` configurable manualmente desde el dialogo ⚙
- Para productos unitarios: `unit_quantity` = 1, `unit_price` = `selling_price`
- Para productos en bulk (ej: bolsa de 100 tornillos): `unit_quantity` = 100, `unit_price` = `selling_price / 100`

---

## Formato de Archivo para Importacion

### Formato Simple (XLSX)
El archivo Excel debe tener estas columnas (con o sin fila de encabezados):

| Columna 0 | Columna 1 | Columna 2 |
|---|---|---|
| Nombre del producto | Categoria | Precio Proveedor |

Ejemplo:
```
Martillo 20oz    | Herramientas | 4500
Clavos 2" x 100 | Ferreteria   | 3200
Tornillos 8x40   | Ferreteria   | 1800
```

### Formato FGP Mayorista (XLS)
Formato real usado por el proveedor FGP (archivos .xls viejos). Columnas:

| Col 0 | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 |
|---|---|---|---|---|---|
| Codigo | Detalle (categoria) | Descripcion del producto | Precio lista | IVA % | **Precio con IVA** |

- El header se detecta automaticamente buscando "Codigo" en col 0
- Se saltean las ~20 filas iniciales de info de la empresa
- **El precio que se toma es el de col 5** (Precio con IVA incluido), NO col 3 (precio de lista sin IVA)
- El nombre del producto se genera como `"{Detalle} - {Descripcion}"` ej: `"ABRAZADERA CIERRE RAPIDO - 10-20 MM F12 PERFECTO"`
- La categoria se toma de col 1 (Detalle)
- Si no se detecta formato FGP, se usa el formato simple como fallback

---

## Como correr el programa

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar tests (opcional, recomendado)
python -m pytest tests/ -v

# 3. Iniciar la aplicacion
python main.py
```

---

## Guia de uso rapido

1. **Registrar Venta**: Escriba el nombre del producto en el campo de busqueda, seleccione de la lista, indique cantidad y presione "Agregar a Venta". Cuando tenga todos los productos, presione "Registrar Venta".
2. **Registrar Gasto**: Complete el formulario con descripcion, monto, fecha y categoria.
3. **Cargar Lista**: Seleccione un archivo XLSX, indique proveedor y fecha, revise la vista previa, y presione "Importar Productos". Los precios se calculan automaticamente con el margen y USD actuales.
4. **Productos**: Administre el catalogo completo. Use "Recalcular" para actualizar precios de un producto con el margen y USD actuales.
5. **Reportes**: Seleccione mes y anio para ver el resumen financiero (ingresos brutos, gastos totales, ganancia neta).
6. **Configuracion (⚙)**: Ajuste el tipo de cambio USD y el margen de ganancia. Al guardar, puede recalcular todos los productos.

---

## Changelog / Modificaciones

### 2026-07-23 — Version inicial
- Implementacion base con arquitectura en capas (Domain, Application, Infrastructure, Presentation)
- CRUD de productos con precios en $ y USD
- Registro de ventas con busqueda de productos
- Registro de gastos por categoria
- Carga de listas de precios desde archivos XLSX
- Reportes financieros mensuales
- Configuracion de tipo de cambio USD y margen de ganancia
- Tests unitarios (TDD) — 26 tests
- Documentacion completa en CONTEXT.md

### 2026-08-01 — Fix: scroll con rueda del raton
- **Rueda del raton en todos los scrollables**: se creo `src/presentation/wheel_scroll.py`
  que reemplaza el handler de rueda por defecto de `CTkScrollableFrame` (que fallaba con
  Tk 9.0) por un UNICO handler global registrado via `bind_all` en el root.
- El handler global detecta cual scrollable esta bajo el mouse y lo desplaza
  (funciona sobre contenido generado dinamicamente y sobre la barra deslizable).
- Se registran los 10 scrollables de la app: resultados de busqueda y tabla de items
  en Registrar Venta, Crear Boleta y Faltantes; tabla de productos y formulario en
  Productos; historial de ventas; comparar mercados; listas subidas en Cargar Lista.
- Como `bind_all` sin `add=True` reemplaza el bindtag "all", no hay doble scroll.

### 2026-07-23 — Fix: formato FGP, USD default, preview
- **USD default**: cambiado de 1.0 a 1500 (`database.py`, `settings_service.py`)
- **Soporte formato FGP**: archivos .xls del proveedor mayorista
  - Detecta automaticamente el formato buscando "Codigo" en col 0
  - Toma el precio de col 5 (Precio con IVA), NO col 3 (precio sin IVA)
  - Nombre del producto: `"{Detalle} - {Descripcion}"`
  - Categoria = col 1 (Detalle)
  - Saltea ~20 filas de encabezados de la empresa
- **Preview simplificado**: reemplazada la tabla de 300+ widgets CTkLabel
  por un unico CTkLabel con resumen de texto (para evitar crash con Tk 9.0)
- **Tests**: 29 tests unitarios pasando

### Bug conocido: crash al iniciar (FIX APPLICADO)
- La app crasheaba al ejecutarse con Python 3.14 + Tk 9.0 + CustomTkinter 6.0.0
- Sintomas: `bgerror failed to handle background error. Original error: invalid command name`
- Causa: incompatibilidad entre `tkinterdnd2` y Tk 9.0 al usarse como clase base de `App`
- **Fix**: `app.py` ahora fuerza `ctk.CTk` como clase base, ignorando tkinterdnd2
  (el drag & drop de archivos queda deshabilitado, pero la app inicia correctamente)

### Proximas mejoras posibles
- Historial de ventas con detalle
- Exportacion de reportes a PDF/Excel
- Graficos de rendimiento mensual
- Backup automatico de la base de datos
- Multiples listas de precios por proveedor con historial

---

## Notas Tecnicas

- Los precios se almacenan como REAL en SQLite pero se convierten a `Decimal` de Python al leer/escribir para evitar errores de redondeo.
- La GUI usa CustomTkinter con tema "light" y color azul. Es compatible con Linux, Windows y macOS.
- El archivo `ferreteria.db` se crea automaticamente en la raiz del proyecto al ejecutar `main.py` por primera vez.
- Para probar la importacion sin archivo real, los tests unitarios mockean el repositorio.
- Entorno de desarrollo: Python 3.14.6, Tk 9.0, CustomTkinter 6.0.0, Fedora Linux.
- La vista previa de carga de listas usa un simple `CTkLabel` con texto resumido en
  lugar de una tabla con widgets por fila, para evitar saturar Tk con miles de widgets.
