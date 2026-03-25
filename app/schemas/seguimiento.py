from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SeguimientoCreate(BaseModel):
    meta_id: int
    trimestre: int
    anio: int
    valor_ejecutado: Decimal = 0
    recursos_ejecutados: Decimal = Field(..., ge=0, description="Valor ejecutado en pesos (COP)")
    evidencia: str = Field(..., min_length=1, description="Números de CDP que respaldan la ejecución")
    porcentaje_cumplimiento: Decimal = 0
    observaciones: str = Field(..., min_length=1, description="Descripción de lo realizado en el periodo")

    @field_validator("evidencia", "observaciones", mode="before")
    @classmethod
    def _strip_text(cls, v):
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("evidencia")
    @classmethod
    def _evidencia_cdps(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("Indique los números de CDP (evidencia presupuestal).")
        return v

    @field_validator("observaciones")
    @classmethod
    def _obs_descripcion(cls, v: str) -> str:
        if len(v) < 5:
            raise ValueError("Describa lo realizado (mínimo 5 caracteres).")
        return v


class SeguimientoUpdate(BaseModel):
    valor_ejecutado: Optional[Decimal] = None
    recursos_ejecutados: Optional[Decimal] = None
    evidencia: Optional[str] = None
    porcentaje_cumplimiento: Optional[Decimal] = None
    observaciones: Optional[str] = None


class SeguimientoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    @field_validator("fecha_registro", mode="before")
    @classmethod
    def _fecha_registro_iso(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return v
