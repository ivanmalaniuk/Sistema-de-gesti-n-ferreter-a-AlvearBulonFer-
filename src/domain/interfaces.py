"""
CAPA DE DOMINIO — Interfaces de repositorio (puertos).

Define los contratos que deben cumplir los repositorios de persistencia.
El dominio NO depende de implementaciones concretas (SQLite, memoria, etc.)
gracias a este patron de Inversion de Dependencias (DIP).

Las interfaces son pequenas y especificas (ISP): cada repositorio solo
expone los metodos que necesita su entidad correspondiente.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional

from src.domain.entities import Product, Sale, Expense, MissingItem, UploadedList


class IProductRepository(ABC):
    """Contrato para el repositorio de productos: CRUD + busqueda."""

    @abstractmethod
    def add(self, product: Product) -> Product:
        """Guarda un nuevo producto y devuelve con id asignado."""
        ...

    @abstractmethod
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Busca por ID. Retorna None si no existe."""
        ...

    @abstractmethod
    def get_all(self) -> List[Product]:
        """Retorna todos los productos (ordenados por nombre)."""
        ...

    @abstractmethod
    def get_all_sorted(self) -> List[Product]:
        """Retorna productos ordenados alfabeticamente."""
        ...

    @abstractmethod
    def search_by_name(self, query: str, supplier: str = '', limit: int = 0) -> List[Product]:
        """Busca productos por nombre u otros campos. Opcionalmente filtra por proveedor.
        Si limit > 0, retorna hasta ese maximo de resultados."""
        ...

    @abstractmethod
    def get_suppliers(self) -> List[str]:
        """Retorna lista de proveedores distintos ordenados."""
        ...

    @abstractmethod
    def find_by_name_and_supplier(self, name: str, supplier: str) -> Optional[Product]:
        """Busca un producto por nombre exacto + proveedor. Retorna None si no existe."""
        ...

    @abstractmethod
    def update(self, product: Product) -> None:
        """Actualiza los campos de un producto existente."""
        ...

    @abstractmethod
    def delete(self, product_id: int) -> None:
        """Elimina un producto por ID."""
        ...

    @abstractmethod
    def delete_by_supplier(self, supplier: str) -> int:
        """Elimina todos los productos de un proveedor. Retorna cantidad de eliminados."""
        ...

    @abstractmethod
    def delete_by_supplier_and_date(self, supplier: str, list_date: date) -> int:
        """Elimina productos de un proveedor con una fecha de lista especifica."""
        ...


class ISaleRepository(ABC):
    """Contrato para el repositorio de ventas."""

    @abstractmethod
    def add(self, sale: Sale) -> Sale:
        """Registra una venta con todos sus items (transaccional)."""
        ...

    @abstractmethod
    def get_by_id(self, sale_id: int) -> Optional[Sale]:
        """Obtiene venta con todos sus items."""
        ...

    @abstractmethod
    def get_all(self) -> List[Sale]:
        """Todas las ventas (orden descendente por fecha)."""
        ...

    @abstractmethod
    def get_by_date_range(self, start: datetime, end: datetime) -> List[Sale]:
        """Ventas dentro de un rango de fechas [start, end)."""
        ...

    @abstractmethod
    def delete(self, sale_id: int) -> None:
        """Elimina una venta y sus items."""
        ...


class IExpenseRepository(ABC):
    """Contrato para el repositorio de gastos."""

    @abstractmethod
    def add(self, expense: Expense) -> Expense: ...

    @abstractmethod
    def get_by_id(self, expense_id: int) -> Optional[Expense]: ...

    @abstractmethod
    def get_all(self) -> List[Expense]: ...

    @abstractmethod
    def get_by_date_range(self, start: datetime, end: datetime) -> List[Expense]: ...


class IMissingItemRepository(ABC):
    @abstractmethod
    def add(self, item: MissingItem) -> MissingItem:
        ...

    @abstractmethod
    def get_all(self) -> List[MissingItem]:
        ...

    @abstractmethod
    def delete(self, item_id: int) -> None:
        ...


class ISettingsRepository(ABC):
    """Contrato para almacenar configuraciones clave-valor."""

    @abstractmethod
    def get(self, key: str, default: str = "") -> str:
        """Obtiene el valor de una configuracion. Retorna default si no existe."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Guarda o actualiza una configuracion."""
        ...


class IUploadedListRepository(ABC):
    """Repositorio de listas de precios subidas."""

    @abstractmethod
    def add(self, uploaded_list: UploadedList) -> UploadedList:
        ...

    @abstractmethod
    def get_all(self) -> List[UploadedList]:
        ...

    @abstractmethod
    def get_by_supplier_and_date(self, supplier: str, list_date: date) -> UploadedList:
        ...

    @abstractmethod
    def delete(self, list_id: int) -> None:
        ...
