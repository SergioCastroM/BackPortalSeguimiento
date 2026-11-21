from sqlalchemy.orm import Session

from app.models import Usuario, PeriodoSeguimiento, EstadoPeriodo, SeguimientoMeta


def calcular_porcentaje(valor_ejecutado: float, referencia: float) -> float:
    """(ejecutado / referencia) * 100. Si referencia es 0, devuelve 0."""
    if referencia == 0:
        return 0.0
    return round((float(valor_ejecutado) / float(referencia)) * 100, 2)


def denominador_cumplimiento_seguimiento(
    db: Session, meta_id: int, valor_esperado_meta: float = 0
) -> float:
    """
    Denominador del % de seguimiento: valor final MGA del primer proyecto.
    Si aún no hay valor final (> 0), devuelve 0: se puede registrar la ejecución
    y el % se recalcula cuando se cargue el presupuesto.
    No usa valor_esperado_2026 (suele ser unidades, no pesos).
    """
    from app.services.proyecto_mga_service import primer_proyecto_mga

    _ = valor_esperado_meta  # compat firma; no se usa como pesos
    p = primer_proyecto_mga(db, meta_id)
    if p is not None:
        vf = float(p.valor_final or 0)
        if vf > 0:
            return vf
    return 0.0


def recalcular_porcentajes_meta(db: Session, meta_id: int) -> int:
    """Recalcula porcentaje_cumplimiento de todos los seguimientos de la meta."""
    referencia = denominador_cumplimiento_seguimiento(db, meta_id)
    n = 0
    for seg in db.query(SeguimientoMeta).filter(SeguimientoMeta.meta_id == meta_id).all():
        seg.porcentaje_cumplimiento = calcular_porcentaje(
            float(seg.valor_ejecutado or 0), referencia
        )
        n += 1
    return n


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
