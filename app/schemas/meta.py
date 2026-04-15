from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal


class MetaBase(BaseModel):
    descripcion: str
    linea_estrategica_id: Optional[int] = None
    secretaria_id: int
    indicador_producto_id: Optional[int] = None
    meta_cuatrienio: Optional[Decimal] = 0
    valor_esperado_2024: Optional[Decimal] = 0
    valor_esperado_2025: Optional[Decimal] = 0
    valor_esperado_2026: Optional[Decimal] = 0
    valor_esperado_2027: Optional[Decimal] = 0
    activo: bool = True


class MetaList(MetaBase):
    id: int
    linea_estrategica: Optional[dict] = None
    secretaria: Optional[dict] = None
    indicador_producto: Optional[dict] = None
    seguimientos: Optional[List[dict]] = None

    class Config:
        from_attributes = True


class MetaDetail(MetaList):
    proyectos_mga: Optional[List[dict]] = None

    class Config:
        from_attributes = True


class PaginatedMetas(BaseModel):
    items: List[MetaDetail]
    total: int
    page: int
    size: int
    pages: int
