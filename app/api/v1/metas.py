from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import Meta, Usuario, RolUsuario, IndicadorProducto, Producto, Programa, Sector
from app.schemas.meta import PaginatedMetas

router = APIRouter(prefix="/metas", tags=["metas"])


def _meta_query(db: Session, user: Usuario):
    q = db.query(Meta).filter(Meta.activo == True).options(
        joinedload(Meta.linea_estrategica),
        joinedload(Meta.secretaria),
        joinedload(Meta.indicador_producto).joinedload(IndicadorProducto.producto).joinedload(Producto.programa).joinedload(Programa.sector),
        joinedload(Meta.proyectos_mga),
        joinedload(Meta.seguimientos),
    )
    if user.rol == RolUsuario.secretaria:
        q = q.filter(Meta.secretaria_id == user.secretaria_id)
    return q


@router.get("", response_model=PaginatedMetas)
def list_metas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    sector_id: Optional[int] = None,
    estado: Optional[str] = None,
    search: Optional[str] = None,
):
    q = _meta_query(db, current_user)
    if sector_id:
        q = q.join(Meta.indicador_producto).join(IndicadorProducto.producto).join(Producto.programa).filter(Programa.sector_id == sector_id)
    if search:
        q = q.filter(Meta.descripcion.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    if estado == "registrada":
        anio, trimestre = 2026, 1
        items = [m for m in items if any(s.anio == anio and s.trimestre == trimestre for s in m.seguimientos)]
    elif estado == "pendiente":
        anio, trimestre = 2026, 1
        items = [m for m in items if not any(s.anio == anio and s.trimestre == trimestre for s in m.seguimientos)]
    pages = (total + size - 1) // size if total else 0
    return PaginatedMetas(items=items, total=total, page=page, size=size, pages=pages)


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


def _meta_to_detail(meta: Meta) -> dict:
    """Construye un dict serializable para el detalle (evita referencias circulares)."""
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
            {"id": p.id, "codigo_bpin": p.codigo_bpin, "nombre": p.nombre, "valor_inicial": float(p.valor_inicial or 0), "valor_final": float(p.valor_final or 0), "meta_id": p.meta_id}
            for p in (meta.proyectos_mga or [])
        ],
        "seguimientos": [
            {"id": s.id, "meta_id": s.meta_id, "usuario_id": s.usuario_id, "trimestre": s.trimestre, "anio": s.anio, "valor_ejecutado": float(s.valor_ejecutado or 0), "recursos_ejecutados": float(s.recursos_ejecutados or 0), "evidencia": s.evidencia, "porcentaje_cumplimiento": float(s.porcentaje_cumplimiento or 0), "observaciones": s.observaciones, "fecha_registro": s.fecha_registro.isoformat() if s.fecha_registro else None}
            for s in (meta.seguimientos or [])
        ],
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
