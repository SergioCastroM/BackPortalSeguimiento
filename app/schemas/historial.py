from typing import List, Optional

from pydantic import BaseModel


class HistorialUsuarioInfo(BaseModel):
    id: int
    nombre: str
    email: str
    cargo: Optional[str] = None


class HistorialMetaResumen(BaseModel):
    id: int
    descripcion: str
    indicador_codigo: Optional[str] = None


class HistorialSecretariaResumen(BaseModel):
    id: int
    nombre: str


class HistorialEventoResponse(BaseModel):
    id: int
    meta_id: int
    seguimiento_id: Optional[int] = None
    tipo_evento: str
    trimestre: Optional[int] = None
    anio: Optional[int] = None
    valor_anterior: Optional[float] = None
    valor_nuevo: Optional[float] = None
    monto_movimiento: Optional[float] = None
    porcentaje_cumplimiento: Optional[float] = None
    observaciones: Optional[str] = None
    observaciones_anterior: Optional[str] = None
    evidencia: Optional[str] = None
    evidencia_anterior: Optional[str] = None
    fecha_registro: Optional[str] = None
    usuario: Optional[HistorialUsuarioInfo] = None


class HistorialAdminItemResponse(HistorialEventoResponse):
    meta: Optional[HistorialMetaResumen] = None
    secretaria: Optional[HistorialSecretariaResumen] = None


class PaginatedHistorialResponse(BaseModel):
    items: List[HistorialAdminItemResponse]
    total: int
    page: int
    size: int
    pages: int
