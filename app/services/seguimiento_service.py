from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import Meta, SeguimientoMeta, Usuario, PeriodoSeguimiento, EstadoPeriodo


def calcular_porcentaje(valor_ejecutado: float, valor_esperado_2026: float) -> float:
    if valor_esperado_2026 == 0:
        return 0.0
    return round((float(valor_ejecutado) / float(valor_esperado_2026)) * 100, 2)


def trimestre_abierto(db: Session, trimestre: int, anio: int) -> bool:
    p = db.query(PeriodoSeguimiento).filter(
        PeriodoSeguimiento.anio == anio,
        PeriodoSeguimiento.trimestre == trimestre,
    ).first()
    return p is not None and p.estado == EstadoPeriodo.abierto


def puede_crear_editar_seguimiento(db: Session, usuario: Usuario, trimestre: int, anio: int) -> bool:
    if usuario.rol.value == "admin":
        return True
    return trimestre_abierto(db, trimestre, anio)
