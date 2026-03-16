from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class SeguimientoCreate(BaseModel):
    meta_id: int
    trimestre: int
    anio: int
    valor_ejecutado: Decimal = 0
    recursos_ejecutados: Decimal = 0
    evidencia: str = ""
    porcentaje_cumplimiento: Decimal = 0
    observaciones: Optional[str] = None


class SeguimientoUpdate(BaseModel):
    valor_ejecutado: Optional[Decimal] = None
    recursos_ejecutados: Optional[Decimal] = None
    evidencia: Optional[str] = None
    porcentaje_cumplimiento: Optional[Decimal] = None
    observaciones: Optional[str] = None


class SeguimientoResponse(BaseModel):
    id: int
    meta_id: int
    usuario_id: int
    trimestre: int
    anio: int
    valor_ejecutado: Optional[Decimal] = None
    recursos_ejecutados: Optional[Decimal] = None
    evidencia: Optional[str] = None
    porcentaje_cumplimiento: Optional[Decimal] = None
    observaciones: Optional[str] = None
    fecha_registro: Optional[str] = None

    class Config:
        from_attributes = True
