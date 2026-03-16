from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import Meta, SeguimientoMeta, Usuario, RolUsuario
from app.schemas.seguimiento import SeguimientoCreate, SeguimientoUpdate, SeguimientoResponse
from app.services.seguimiento_service import calcular_porcentaje, puede_crear_editar_seguimiento

router = APIRouter(prefix="/seguimiento", tags=["seguimiento"])


@router.post("", response_model=SeguimientoResponse)
def create_seguimiento(
    body: SeguimientoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol == RolUsuario.secretaria and not puede_crear_editar_seguimiento(db, current_user, body.trimestre, body.anio):
        raise HTTPException(status_code=400, detail="El trimestre no está abierto para registro.")
    meta = db.query(Meta).filter(Meta.id == body.meta_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    if current_user.rol == RolUsuario.secretaria and meta.secretaria_id != current_user.secretaria_id:
        raise HTTPException(status_code=403, detail="No puede registrar seguimiento de esta meta.")
    existing = db.query(SeguimientoMeta).filter(
        SeguimientoMeta.meta_id == body.meta_id,
        SeguimientoMeta.trimestre == body.trimestre,
        SeguimientoMeta.anio == body.anio,
    ).first()
    valor_esp = float(meta.valor_esperado_2026 or 0)
    pct = body.porcentaje_cumplimiento if body.porcentaje_cumplimiento is not None else calcular_porcentaje(float(body.valor_ejecutado), valor_esp)
    if existing:
        existing.valor_ejecutado = body.valor_ejecutado
        existing.recursos_ejecutados = body.recursos_ejecutados
        existing.evidencia = body.evidencia or ""
        existing.porcentaje_cumplimiento = pct
        existing.observaciones = body.observaciones
        db.commit()
        db.refresh(existing)
        return existing
    seg = SeguimientoMeta(
        meta_id=body.meta_id,
        usuario_id=current_user.id,
        trimestre=body.trimestre,
        anio=body.anio,
        valor_ejecutado=body.valor_ejecutado,
        recursos_ejecutados=body.recursos_ejecutados,
        evidencia=body.evidencia or "",
        porcentaje_cumplimiento=pct,
        observaciones=body.observaciones,
    )
    db.add(seg)
    db.commit()
    db.refresh(seg)
    return seg


@router.put("/{seguimiento_id}", response_model=SeguimientoResponse)
def update_seguimiento(
    seguimiento_id: int,
    body: SeguimientoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    seg = db.query(SeguimientoMeta).filter(SeguimientoMeta.id == seguimiento_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    meta = seg.meta
    if current_user.rol == RolUsuario.secretaria and meta.secretaria_id != current_user.secretaria_id:
        raise HTTPException(status_code=403, detail="No puede editar este seguimiento.")
    if current_user.rol == RolUsuario.secretaria and not puede_crear_editar_seguimiento(db, current_user, seg.trimestre, seg.anio):
        raise HTTPException(status_code=400, detail="El trimestre está cerrado.")
    if body.valor_ejecutado is not None:
        seg.valor_ejecutado = body.valor_ejecutado
    if body.recursos_ejecutados is not None:
        seg.recursos_ejecutados = body.recursos_ejecutados
    if body.evidencia is not None:
        seg.evidencia = body.evidencia
    if body.porcentaje_cumplimiento is not None:
        seg.porcentaje_cumplimiento = body.porcentaje_cumplimiento
    if body.observaciones is not None:
        seg.observaciones = body.observaciones
    db.commit()
    db.refresh(seg)
    return seg


@router.get("/{seguimiento_id}", response_model=SeguimientoResponse)
def get_seguimiento(
    seguimiento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    seg = db.query(SeguimientoMeta).filter(SeguimientoMeta.id == seguimiento_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    if current_user.rol == RolUsuario.secretaria and seg.meta.secretaria_id != current_user.secretaria_id:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return seg
