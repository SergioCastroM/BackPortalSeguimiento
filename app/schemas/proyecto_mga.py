from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ProyectoMgaMovimientoCreate(BaseModel):
    tipo: Literal["adicion", "reduccion"]
    monto: Decimal = Field(..., gt=0, description="Monto en pesos a sumar a adiciones o a disminuciones")
