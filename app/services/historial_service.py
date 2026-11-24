"""Servicio de registro y consulta de bitácora de actividad sobre metas."""
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, cast, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models import IndicadorProducto, Meta, SeguimientoMeta
from app.models.historial_actividad_meta import HistorialActividadMeta

TIPO_SEGUIMIENTO_CREADO = "seguimiento_creado"
TIPO_SEGUIMIENTO_ACTUALIZADO = "seguimiento_actualizado"
TIPO_ADICION_PRESUPUESTO = "adicion_presupuesto"
TIPO_REDUCCION_PRESUPUESTO = "reduccion_presupuesto"


def _to_decimal_or_none(val: Decimal | float | int | None) -> Optional[Decimal]:
    if val is None:
        return None
    return Decimal(str(val))


def _to_float_or_none(val: Decimal | float | int | None) -> Optional[float]:
    if val is None:
        return None
    return float(val)


def registrar_evento_seguimiento_creado(
    db: Session,
    seg: SeguimientoMeta,
    usuario_id: int,
) -> HistorialActividadMeta:
    valor_actual = seg.recursos_ejecutados if seg.recursos_ejecutados is not None else seg.valor_ejecutado
    evento = HistorialActividadMeta(
        meta_id=seg.meta_id,
        seguimiento_id=seg.id,
        usuario_id=usuario_id,
        tipo_evento=TIPO_SEGUIMIENTO_CREADO,
        trimestre=seg.trimestre,
        anio=seg.anio,
        valor_nuevo=_to_decimal_or_none(valor_actual),
        porcentaje_cumplimiento=_to_decimal_or_none(seg.porcentaje_cumplimiento),
        observaciones=seg.observaciones,
        evidencia=seg.evidencia,
    )
    db.add(evento)
    return evento


def registrar_evento_seguimiento_actualizado(
    db: Session,
    seg: SeguimientoMeta,
    usuario_id: int,
    valor_anterior: Decimal | float | int | None = None,
    observaciones_anterior: Optional[str] = None,
    evidencia_anterior: Optional[str] = None,
) -> HistorialActividadMeta:
    valor_actual = seg.recursos_ejecutados if seg.recursos_ejecutados is not None else seg.valor_ejecutado
    evento = HistorialActividadMeta(
        meta_id=seg.meta_id,
        seguimiento_id=seg.id,
        usuario_id=usuario_id,
        tipo_evento=TIPO_SEGUIMIENTO_ACTUALIZADO,
        trimestre=seg.trimestre,
        anio=seg.anio,
        valor_anterior=_to_decimal_or_none(valor_anterior),
        valor_nuevo=_to_decimal_or_none(valor_actual),
        porcentaje_cumplimiento=_to_decimal_or_none(seg.porcentaje_cumplimiento),
        observaciones=seg.observaciones,
        observaciones_anterior=observaciones_anterior,
        evidencia=seg.evidencia,
        evidencia_anterior=evidencia_anterior,
    )
    db.add(evento)
    return evento


def registrar_evento_movimiento_presupuesto(
    db: Session,
    meta_id: int,
    usuario_id: int,
    tipo: str,
    monto: Decimal,
    valor_final_anterior: Decimal | float | int,
    valor_final_nuevo: Decimal | float | int,
) -> HistorialActividadMeta:
    tipo_evento = (
        TIPO_ADICION_PRESUPUESTO if tipo == "adicion" else TIPO_REDUCCION_PRESUPUESTO
    )
    evento = HistorialActividadMeta(
        meta_id=meta_id,
        usuario_id=usuario_id,
        tipo_evento=tipo_evento,
        valor_anterior=_to_decimal_or_none(valor_final_anterior),
        valor_nuevo=_to_decimal_or_none(valor_final_nuevo),
        monto_movimiento=_to_decimal_or_none(monto),
    )
    db.add(evento)
    return evento


def _serialize_evento(ev: HistorialActividadMeta, incluir_meta: bool = False) -> dict:
    usuario = ev.usuario
    data = {
        "id": ev.id,
        "meta_id": ev.meta_id,
        "seguimiento_id": ev.seguimiento_id,
        "tipo_evento": ev.tipo_evento,
        "trimestre": ev.trimestre,
        "anio": ev.anio,
        "valor_anterior": _to_float_or_none(ev.valor_anterior),
        "valor_nuevo": _to_float_or_none(ev.valor_nuevo),
        "monto_movimiento": _to_float_or_none(ev.monto_movimiento),
        "porcentaje_cumplimiento": _to_float_or_none(ev.porcentaje_cumplimiento),
        "observaciones": ev.observaciones,
        "observaciones_anterior": ev.observaciones_anterior,
        "evidencia": ev.evidencia,
        "evidencia_anterior": ev.evidencia_anterior,
        "fecha_registro": ev.fecha_registro.isoformat() if ev.fecha_registro else None,
        "usuario": (
            {
                "id": usuario.id,
                "nombre": usuario.nombre,
                "email": usuario.email,
                "cargo": usuario.cargo,
            }
            if usuario
            else None
        ),
    }
    if incluir_meta:
        meta = ev.meta
        sec = meta.secretaria if meta else None
        ind = meta.indicador_producto if meta else None
        data["meta"] = (
            {
                "id": meta.id,
                "descripcion": meta.descripcion,
                "indicador_codigo": ind.codigo if ind else None,
            }
            if meta
            else None
        )
        data["secretaria"] = (
            {"id": sec.id, "nombre": sec.nombre}
            if sec
            else None
        )
    return data


def listar_historial_meta(db: Session, meta_id: int) -> list[dict]:
    rows = (
        db.query(HistorialActividadMeta)
        .options(joinedload(HistorialActividadMeta.usuario))
        .filter(HistorialActividadMeta.meta_id == meta_id)
        .order_by(desc(HistorialActividadMeta.fecha_registro), desc(HistorialActividadMeta.id))
        .all()
    )
    return [_serialize_evento(r, incluir_meta=False) for r in rows]


def listar_historial_admin(
    db: Session,
    page: int = 1,
    size: int = 25,
    secretaria_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
    tipo_evento: Optional[str] = None,
    trimestre: Optional[int] = None,
    anio: Optional[int] = None,
    search: Optional[str] = None,
) -> dict:
    q_base = (
        db.query(HistorialActividadMeta)
        .join(Meta, HistorialActividadMeta.meta_id == Meta.id)
        .outerjoin(IndicadorProducto, Meta.indicador_producto_id == IndicadorProducto.id)
        .filter(Meta.activo == True)
    )
    if secretaria_id is not None:
        q_base = q_base.filter(Meta.secretaria_id == secretaria_id)
    if usuario_id is not None:
        q_base = q_base.filter(HistorialActividadMeta.usuario_id == usuario_id)
    if tipo_evento:
        q_base = q_base.filter(HistorialActividadMeta.tipo_evento == tipo_evento)
    if trimestre is not None:
        q_base = q_base.filter(HistorialActividadMeta.trimestre == trimestre)
    if anio is not None:
        q_base = q_base.filter(HistorialActividadMeta.anio == anio)
    if search and search.strip():
        pat = f"%{search.strip().lower()}%"
        q_base = q_base.filter(
            or_(
                func.lower(Meta.descripcion).like(pat),
                func.lower(func.coalesce(IndicadorProducto.codigo, "")).like(pat),
                func.lower(func.coalesce(cast(HistorialActividadMeta.evidencia, String(4000)), "")).like(pat),
                func.lower(func.coalesce(cast(HistorialActividadMeta.observaciones, String(4000)), "")).like(pat),
            )
        )

    total = q_base.with_entities(func.count(HistorialActividadMeta.id)).scalar() or 0
    rows = (
        q_base.options(
            joinedload(HistorialActividadMeta.usuario),
            joinedload(HistorialActividadMeta.meta).joinedload(Meta.secretaria),
            joinedload(HistorialActividadMeta.meta).joinedload(Meta.indicador_producto),
        )
        .order_by(desc(HistorialActividadMeta.fecha_registro), desc(HistorialActividadMeta.id))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    pages = (total + size - 1) // size if total else 0
    return {
        "items": [_serialize_evento(r, incluir_meta=True) for r in rows],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }
