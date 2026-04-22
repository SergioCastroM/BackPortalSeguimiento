"""Lógica de presupuesto MGA: valor_final = valor_inicial + adiciones - disminuciones (reducción)."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Meta, ProyectoMga


def primer_proyecto_mga(db: Session, meta_id: int) -> ProyectoMga | None:
    return (
        db.query(ProyectoMga)
        .filter(ProyectoMga.meta_id == meta_id)
        .order_by(ProyectoMga.id.asc())
        .first()
    )


def crear_proyecto_mga_minimo_si_falta(db: Session, meta: Meta) -> ProyectoMga:
    """
    Garantiza un ProyectoMga para la meta (p. ej. sincronización de presupuesto sin import previo).
    Si ya existe, devuelve el primero por id.
    """
    p = primer_proyecto_mga(db, meta.id)
    if p:
        return p
    nombre = ((meta.descripcion or "").strip()[:500]) or f"Proyecto MGA meta #{meta.id}"
    np = ProyectoMga(
        meta_id=meta.id,
        codigo_bpin=None,
        nombre=nombre,
        valor_inicial=Decimal("0"),
        adicion=Decimal("0"),
        reduccion=Decimal("0"),
        valor_final=Decimal("0"),
    )
    db.add(np)
    db.flush()
    recalcular_valor_final(np)
    return np


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
