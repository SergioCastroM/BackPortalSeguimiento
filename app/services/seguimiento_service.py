from sqlalchemy.orm import Session

from app.models import Usuario, PeriodoSeguimiento, EstadoPeriodo


def calcular_porcentaje(valor_ejecutado: float, referencia: float) -> float:
    """(ejecutado / referencia) * 100. Si referencia es 0, devuelve 0."""
    if referencia == 0:
        return 0.0
    return round((float(valor_ejecutado) / float(referencia)) * 100, 2)


def denominador_cumplimiento_seguimiento(db: Session, meta_id: int, valor_esperado_meta: float) -> float:
    """
    Prioriza el valor final MGA (inicial + adiciones − disminuciones) del primer proyecto;
    si no hay proyecto o valor_final es 0, usa valor esperado 2026 de la meta.
    """
    from app.services.proyecto_mga_service import primer_proyecto_mga

    p = primer_proyecto_mga(db, meta_id)
    if p is not None:
        vf = float(p.valor_final or 0)
        if vf > 0:
            return vf
    return float(valor_esperado_meta or 0)


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
