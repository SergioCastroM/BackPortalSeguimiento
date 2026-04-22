from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Numeric, and_, asc, case, cast, desc, distinct, func, literal
from sqlalchemy.orm import Session, aliased, joinedload, selectinload

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import (
    IndicadorProducto,
    Meta,
    Producto,
    Programa,
    ProyectoMga,
    RolUsuario,
    Secretaria,
    Sector,
    SeguimientoMeta,
    Usuario,
)
from app.schemas.meta import MetaDetail, PaginatedMetas
from app.schemas.proyecto_mga import ProyectoMgaMovimientoCreate
from app.services.proyecto_mga_service import registrar_adicion_o_reduccion

router = APIRouter(prefix="/metas", tags=["metas"])


def _meta_to_detail(meta: Meta) -> dict:
    """Construye un dict serializable para listado y detalle (evita referencias circulares)."""
    ip = meta.indicador_producto
    producto = ip.producto if ip else None
    programa = producto.programa if producto else None
    sector = programa.sector if programa else None
    indicador_producto = None
    if ip:
        indicador_producto = {
            "id": ip.id,
            "codigo": ip.codigo,
            "nombre": ip.nombre,
            "producto": {
                "id": producto.id,
                "nombre": getattr(producto, "nombre", None),
                "programa": {
                    "id": programa.id,
                    "nombre": getattr(programa, "nombre", None),
                    "sector": {"id": sector.id, "nombre": sector.nombre} if sector else None,
                } if programa else None,
            } if producto else None,
        }
    return {
        "id": meta.id,
        "descripcion": meta.descripcion,
        "linea_estrategica_id": meta.linea_estrategica_id,
        "secretaria_id": meta.secretaria_id,
        "indicador_producto_id": meta.indicador_producto_id,
        "meta_cuatrienio": float(meta.meta_cuatrienio or 0),
        "valor_esperado_2024": float(meta.valor_esperado_2024 or 0),
        "valor_esperado_2025": float(meta.valor_esperado_2025 or 0),
        "valor_esperado_2026": float(meta.valor_esperado_2026 or 0),
        "valor_esperado_2027": float(meta.valor_esperado_2027 or 0),
        "activo": meta.activo,
        "linea_estrategica": {"id": meta.linea_estrategica.id, "nombre": meta.linea_estrategica.nombre} if meta.linea_estrategica and getattr(meta.linea_estrategica, "id", None) is not None else None,
        "secretaria": {"id": meta.secretaria.id, "nombre": meta.secretaria.nombre} if meta.secretaria and getattr(meta.secretaria, "id", None) is not None else None,
        "indicador_producto": indicador_producto,
        "proyectos_mga": [
            {
                "id": p.id,
                "codigo_bpin": p.codigo_bpin,
                "nombre": p.nombre,
                "valor_inicial": float(p.valor_inicial or 0),
                "adicion": float(p.adicion or 0),
                "reduccion": float(p.reduccion or 0),
                "valor_final": float(p.valor_final or 0),
                "meta_id": p.meta_id,
            }
            for p in sorted(meta.proyectos_mga or [], key=lambda x: x.id)
        ],
        "seguimientos": [
            {"id": s.id, "meta_id": s.meta_id, "usuario_id": s.usuario_id, "trimestre": s.trimestre, "anio": s.anio, "valor_ejecutado": float(s.valor_ejecutado or 0), "recursos_ejecutados": float(s.recursos_ejecutados or 0), "evidencia": s.evidencia, "porcentaje_cumplimiento": float(s.porcentaje_cumplimiento or 0), "observaciones": s.observaciones, "fecha_registro": s.fecha_registro.isoformat() if s.fecha_registro else None}
            for s in (meta.seguimientos or [])
        ],
    }


def _meta_base_query(db: Session, user: Usuario):
    """Consulta filtrada sin eager load: segura para .count()."""
    q = db.query(Meta).filter(Meta.activo == True)
    if user.rol == RolUsuario.secretaria:
        q = q.filter(Meta.secretaria_id == user.secretaria_id)
    return q


def _apply_meta_list_filters(q, sector_id: Optional[int], search: Optional[str]):
    if sector_id:
        q = (
            q.join(Meta.indicador_producto)
            .join(IndicadorProducto.producto)
            .join(Producto.programa)
            .filter(Programa.sector_id == sector_id)
        )
    if search:
        q = q.filter(Meta.descripcion.ilike(f"%{search}%"))
    return q


def _meta_query(db: Session, user: Usuario):
    """Listados y detalle con relaciones cargadas."""
    return _meta_base_query(db, user).options(
        joinedload(Meta.linea_estrategica),
        joinedload(Meta.secretaria),
        joinedload(Meta.indicador_producto).joinedload(IndicadorProducto.producto).joinedload(Producto.programa).joinedload(Programa.sector),
        # Colecciones: selectinload evita JOIN+cartesiano con LIMIT (SQLAlchemy 2 / Postgres en Azure).
        selectinload(Meta.proyectos_mga),
        selectinload(Meta.seguimientos),
    )


LIST_ANIO_METAS = 2026
_SORT_KEYS = frozenset(
    {"id", "secretaria", "sector", "meta_2026", "valor_final", "valor_ejecutado", "pct_ejecucion"}
)


def _first_pm_subq(db: Session):
    return (
        db.query(
            ProyectoMga.meta_id.label("meta_id"),
            func.min(ProyectoMga.id).label("min_pm_id"),
        )
        .group_by(ProyectoMga.meta_id)
        .subquery()
    )


def _ejecutado_anio_subq(db: Session):
    return (
        db.query(
            SeguimientoMeta.meta_id.label("meta_id"),
            func.coalesce(func.sum(SeguimientoMeta.valor_ejecutado), 0).label("total_ej"),
        )
        .filter(SeguimientoMeta.anio == LIST_ANIO_METAS)
        .group_by(SeguimientoMeta.meta_id)
        .subquery()
    )


def _sector_nombre_subq(db: Session):
    return (
        db.query(Meta.id.label("meta_row_id"), Sector.nombre.label("sector_order_nombre"))
        .select_from(Meta)
        .outerjoin(IndicadorProducto, Meta.indicador_producto_id == IndicadorProducto.id)
        .outerjoin(Producto, IndicadorProducto.producto_id == Producto.id)
        .outerjoin(Programa, Producto.programa_id == Programa.id)
        .outerjoin(Sector, Programa.sector_id == Sector.id)
        .subquery()
    )


@router.get("", response_model=PaginatedMetas)
def list_metas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    sector_id: Optional[int] = None,
    estado: Optional[str] = None,
    search: Optional[str] = None,
    secretaria_id: Optional[int] = Query(None, description="Filtrar por secretaría (solo admin)."),
    desbalance: Optional[bool] = Query(
        None,
        description="Solo metas con ejecución acumulada 2026 mayor al presupuesto de referencia (valor final MGA o valor esperado 2026).",
    ),
    sort_by: str = Query("id", description="id, secretaria, sector, meta_2026, valor_final, valor_ejecutado, pct_ejecucion"),
    sort_dir: str = Query("asc", description="asc o desc"),
):
    if secretaria_id is not None and current_user.rol != RolUsuario.admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden filtrar por secretaría.")

    def base_filtered():
        q = _apply_meta_list_filters(_meta_base_query(db, current_user), sector_id, search)
        if secretaria_id is not None:
            q = q.filter(Meta.secretaria_id == secretaria_id)
        return q

    sort_key = (sort_by or "id").lower()
    if sort_key not in _SORT_KEYS:
        sort_key = "id"
    sd = (sort_dir or "asc").lower()
    if sd not in ("asc", "desc"):
        sd = "asc"
    ascending = sd == "asc"

    pm_sq = _first_pm_subq(db)
    ej_sq = _ejecutado_anio_subq(db)
    PMp = aliased(ProyectoMga)

    need_metrics = bool(desbalance) or sort_key in ("valor_final", "valor_ejecutado", "pct_ejecucion")

    def attach_pm_ej(q):
        q2 = (
            q.outerjoin(pm_sq, pm_sq.c.meta_id == Meta.id)
            .outerjoin(PMp, PMp.id == pm_sq.c.min_pm_id)
            .outerjoin(ej_sq, ej_sq.c.meta_id == Meta.id)
        )
        vf_num = func.coalesce(cast(PMp.valor_final, Numeric), 0)
        ve_num = func.coalesce(cast(ej_sq.c.total_ej, Numeric), 0)
        vesp = func.coalesce(cast(Meta.valor_esperado_2026, Numeric), 0)
        ref_num = case((vf_num > 0, vf_num), else_=vesp)
        return q2, vf_num, ve_num, ref_num

    q_count = base_filtered()
    vf_num = ve_num = ref_num = None
    if need_metrics:
        q_count, vf_num, ve_num, ref_num = attach_pm_ej(q_count)
        if desbalance:
            q_count = q_count.filter(and_(ref_num > 0, ve_num > ref_num))
    total = q_count.with_entities(func.count(distinct(Meta.id))).scalar() or 0

    q_items = base_filtered().options(
        joinedload(Meta.linea_estrategica),
        joinedload(Meta.secretaria),
        joinedload(Meta.indicador_producto).joinedload(IndicadorProducto.producto).joinedload(Producto.programa).joinedload(Programa.sector),
        selectinload(Meta.proyectos_mga),
        selectinload(Meta.seguimientos),
    )
    order_cols: list = []
    if need_metrics:
        q_items, vf_num, ve_num, ref_num = attach_pm_ej(q_items)
        if desbalance:
            q_items = q_items.filter(and_(ref_num > 0, ve_num > ref_num))
        pct_col = case(
            (ref_num > 0, cast(ve_num / ref_num * literal(100), Numeric)),
            else_=literal(0),
        )
        if sort_key == "valor_final":
            order_cols = [vf_num]
        elif sort_key == "valor_ejecutado":
            order_cols = [ve_num]
        elif sort_key == "pct_ejecucion":
            order_cols = [pct_col]
    if sort_key == "secretaria":
        q_items = q_items.join(Secretaria, Meta.secretaria_id == Secretaria.id)
        order_cols = [Secretaria.nombre]
    elif sort_key == "sector":
        sec_sq = _sector_nombre_subq(db)
        q_items = q_items.outerjoin(sec_sq, sec_sq.c.meta_row_id == Meta.id)
        order_cols = [sec_sq.c.sector_order_nombre]
    elif sort_key == "meta_2026":
        order_cols = [Meta.valor_esperado_2026]
    elif sort_key == "id" or not order_cols:
        order_cols = [Meta.id]

    if ascending:
        q_items = q_items.order_by(*(asc(c) for c in order_cols), asc(Meta.id))
    else:
        q_items = q_items.order_by(*(desc(c) for c in order_cols), asc(Meta.id))

    items = q_items.offset((page - 1) * size).limit(size).all()
    if estado == "registrada":
        anio, trimestre = 2026, 1
        items = [m for m in items if any(s.anio == anio and s.trimestre == trimestre for s in m.seguimientos)]
    elif estado == "pendiente":
        anio, trimestre = 2026, 1
        items = [m for m in items if not any(s.anio == anio and s.trimestre == trimestre for s in m.seguimientos)]
    pages = (total + size - 1) // size if total else 0
    # Los ítems ORM no encajan en MetaDetail (anidados dict vs modelos SQLAlchemy) → 500 al serializar.
    serialized = [MetaDetail.model_validate(_meta_to_detail(m)) for m in items]
    return PaginatedMetas(items=serialized, total=total, page=page, size=size, pages=pages)


# Ruta más específica antes que /{meta_id} para evitar ambigüedad en el enrutado.
@router.get("/{meta_id}/seguimiento")
def get_meta_seguimiento(
    meta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = _meta_query(db, current_user).filter(Meta.id == meta_id)
    meta = q.first()
    if not meta:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    return [{"id": s.id, "trimestre": s.trimestre, "anio": s.anio, "porcentaje_cumplimiento": float(s.porcentaje_cumplimiento or 0), "valor_ejecutado": float(s.valor_ejecutado or 0), "evidencia": s.evidencia, "fecha_registro": s.fecha_registro.isoformat() if s.fecha_registro else None} for s in meta.seguimientos]


@router.post("/{meta_id}/proyecto-mga/movimiento")
def registrar_movimiento_presupuesto_mga(
    meta_id: int,
    body: ProyectoMgaMovimientoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Registra una adición o disminución (reducción) en el primer proyecto MGA de la meta.
    valor_final se recalcula: valor_inicial + adiciones − disminuciones.
    """
    q = _meta_base_query(db, current_user).filter(Meta.id == meta_id)
    meta = q.first()
    if not meta:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    try:
        p = registrar_adicion_o_reduccion(db, meta_id, body.tipo, body.monto)
        db.commit()
        db.refresh(p)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "mensaje": "Movimiento registrado. Valor final = valor inicial + adiciones − disminuciones.",
        "proyecto": {
            "id": p.id,
            "codigo_bpin": p.codigo_bpin,
            "nombre": p.nombre,
            "valor_inicial": float(p.valor_inicial or 0),
            "adicion": float(p.adicion or 0),
            "reduccion": float(p.reduccion or 0),
            "valor_final": float(p.valor_final or 0),
            "meta_id": p.meta_id,
        },
    }


@router.get("/{meta_id}")
def get_meta(
    meta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = _meta_query(db, current_user).filter(Meta.id == meta_id)
    meta = q.first()
    if not meta:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    return _meta_to_detail(meta)
