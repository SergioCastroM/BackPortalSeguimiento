"""Lógica de presupuesto MGA: valor_final = valor_inicial + adiciones - disminuciones (reducción)."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import ProyectoMga


def primer_proyecto_mga(db: Session, meta_id: int) -> ProyectoMga | None:
    return (
        db.query(ProyectoMga)
        .filter(ProyectoMga.meta_id == meta_id)
        .order_by(ProyectoMga.id.asc())
        .first()
    )


def recalcular_valor_final(p: ProyectoMga) -> None:
    """valor_final = valor_inicial + adicion - reduccion"""
    vi = Decimal(p.valor_inicial or 0)
    ad = Decimal(p.adicion or 0)
    red = Decimal(p.reduccion or 0)
    p.valor_final = vi + ad - red


def registrar_adicion_o_reduccion(db: Session, meta_id: int, tipo: str, monto: Decimal) -> ProyectoMga:
    """
    tipo: 'adicion' | 'reduccion'
    Suma el monto al acumulado de adiciones o disminuciones y recalcula valor_final.
    """
    p = primer_proyecto_mga(db, meta_id)
    if not p:
        raise ValueError("La meta no tiene proyecto MGA. Cargue los datos desde Excel o cree el vínculo.")
    m = Decimal(monto)
    if m <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    if tipo == "adicion":
        p.adicion = Decimal(p.adicion or 0) + m
    elif tipo == "reduccion":
        p.reduccion = Decimal(p.reduccion or 0) + m
    else:
        raise ValueError("tipo debe ser 'adicion' o 'reduccion'.")
    recalcular_valor_final(p)
    return p
