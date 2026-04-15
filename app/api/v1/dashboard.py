from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import Usuario, RolUsuario
from app.services.dashboard_service import dashboard_global, dashboard_secretaria

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/global")
def get_global(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    anio: int = Query(2026),
    trimestre: int = Query(1, ge=1, le=4),
):
    if current_user.rol != RolUsuario.admin:
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return dashboard_global(db, anio, trimestre)


@router.get("/secretaria/{secretaria_id}")
def get_secretaria_dashboard(
    secretaria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    anio: int = Query(2026),
    trimestre: int = Query(1, ge=1, le=4),
):
    if current_user.rol == RolUsuario.secretaria and current_user.secretaria_id != secretaria_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return dashboard_secretaria(db, secretaria_id, anio, trimestre)


@router.get("/heatmap")
def get_heatmap(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    anio: int = Query(2026),
):
    if current_user.rol != RolUsuario.admin:
        return {"detail": "Se requieren permisos de administrador"}
    data = dashboard_global(db, anio, 1)
    return {"heatmap": data["heatmap"]}
