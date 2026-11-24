from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import Meta, SeguimientoMeta, Usuario, RolUsuario
from app.schemas.seguimiento import SeguimientoCreate, SeguimientoUpdate, SeguimientoResponse
from app.services.historial_service import (
    registrar_evento_seguimiento_actualizado,
    registrar_evento_seguimiento_creado,
)
from app.services.seguimiento_service import (
    calcular_porcentaje,
    denominador_cumplimiento_seguimiento,
    puede_crear_editar_seguimiento,
)

router = APIRouter(prefix="/seguimiento", tags=["seguimiento"])


@router.post("", response_model=SeguimientoResponse)
def create_seguimiento(
    body: SeguimientoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol == RolUsuario.secretaria and not puede_crear_editar_seguimiento(db, current_user, body.trimestre, body.anio):
        raise HTTPException(status_code=400, detail="El período no está abierto para registro.")
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
    referencia = denominador_cumplimiento_seguimiento(db, meta.id)
    valor_pesos = Decimal(body.recursos_ejecutados)
    # Siempre se calcula en servidor. Sin valor final MGA el % queda 0 y se
    # recalcula al sincronizar o mover el presupuesto.
    pct = calcular_porcentaje(float(valor_pesos), referencia)
    if existing:
        valor_prev = (
            existing.recursos_ejecutados
            if existing.recursos_ejecutados is not None
            else existing.valor_ejecutado
        )
        obs_prev = existing.observaciones
        ev_prev = existing.evidencia
        existing.usuario_id = current_user.id
        existing.fecha_registro = func.now()
        existing.valor_ejecutado = valor_pesos
        existing.recursos_ejecutados = valor_pesos
        existing.evidencia = body.evidencia
        existing.porcentaje_cumplimiento = pct
        existing.observaciones = body.observaciones
        registrar_evento_seguimiento_actualizado(
            db,
            existing,
            current_user.id,
            valor_anterior=valor_prev,
            observaciones_anterior=obs_prev,
            evidencia_anterior=ev_prev,
        )
        db.commit()
        db.refresh(existing)
        return existing
    seg = SeguimientoMeta(
        meta_id=body.meta_id,
        usuario_id=current_user.id,
        trimestre=body.trimestre,
        anio=body.anio,
        valor_ejecutado=valor_pesos,
        recursos_ejecutados=valor_pesos,
        evidencia=body.evidencia,
        porcentaje_cumplimiento=pct,
        observaciones=body.observaciones,
    )
    db.add(seg)
    db.flush()
    registrar_evento_seguimiento_creado(db, seg, current_user.id)
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
        raise HTTPException(status_code=400, detail="El período está cerrado.")
    valor_prev = (
        seg.recursos_ejecutados
        if seg.recursos_ejecutados is not None
        else seg.valor_ejecutado
    )
    obs_prev = seg.observaciones
    ev_prev = seg.evidencia
    changed_monto = False
    if body.recursos_ejecutados is not None:
        seg.recursos_ejecutados = body.recursos_ejecutados
        seg.valor_ejecutado = body.recursos_ejecutados
        changed_monto = True
    elif body.valor_ejecutado is not None:
        seg.valor_ejecutado = body.valor_ejecutado
        seg.recursos_ejecutados = body.valor_ejecutado
        changed_monto = True
    if body.evidencia is not None:
        ev = body.evidencia.strip()
        if len(ev) < 2:
            raise HTTPException(status_code=400, detail="Indique los números de CDP (mínimo 2 caracteres).")
        seg.evidencia = ev
    if body.observaciones is not None:
        ob = body.observaciones.strip()
        if len(ob) < 5:
            raise HTTPException(status_code=400, detail="Describa lo realizado (mínimo 5 caracteres).")
        seg.observaciones = ob
    if changed_monto or body.porcentaje_cumplimiento is not None:
        referencia = denominador_cumplimiento_seguimiento(db, meta.id)
        seg.porcentaje_cumplimiento = calcular_porcentaje(
            float(seg.valor_ejecutado or 0), referencia
        )
    seg.usuario_id = current_user.id
    seg.fecha_registro = func.now()
    registrar_evento_seguimiento_actualizado(
        db,
        seg,
        current_user.id,
        valor_anterior=valor_prev,
        observaciones_anterior=obs_prev,
        evidencia_anterior=ev_prev,
    )
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
