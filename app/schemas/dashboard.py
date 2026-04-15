from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal


class KPIsGlobal(BaseModel):
    total_metas: int
    con_seguimiento: int
    pendientes: int
    porcentaje_cumplimiento_prom: Decimal


class PorSecretaria(BaseModel):
    secretaria_id: int
    secretaria_nombre: str
    porcentaje: Decimal
    total_metas: int


class PorSector(BaseModel):
    sector_id: int
    sector_nombre: str
    cantidad: int
    porcentaje: Decimal


class EvolucionItem(BaseModel):
    trimestre: int
    anio: int
    secretaria_id: int
    secretaria_nombre: str
    porcentaje: Decimal


class HeatmapItem(BaseModel):
    secretaria_id: int
    secretaria_nombre: str
    trimestre: int
    anio: int
    porcentaje: Optional[Decimal] = None


class DashboardGlobalResponse(BaseModel):
    kpis: KPIsGlobal
    por_secretaria: List[PorSecretaria]
    por_sector: List[PorSector]
    evolucion: List[EvolucionItem]
    heatmap: List[HeatmapItem]


class KPIsSecretaria(BaseModel):
    total_metas: int
    registradas: int
    pendientes: int
    porcentaje_cumplimiento: Decimal


class EsperadoVsEjecutado(BaseModel):
    meta_id: int
    meta_descripcion: str
    esperado: Decimal
    ejecutado: Decimal


class EvolucionSecretaria(BaseModel):
    trimestre: int
    anio: int
    porcentaje: Decimal


class DashboardSecretariaResponse(BaseModel):
    kpis: KPIsSecretaria
    metas_esperado_vs_ejecutado: List[EsperadoVsEjecutado]
    evolucion: List[EvolucionSecretaria]
    metas: List[dict]
