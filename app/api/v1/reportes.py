from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db.session import get_db
from app.core.deps import require_admin
from app.models import Usuario

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/secretaria/{secretaria_id}")
def reporte_secretaria(
    secretaria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    trimestre: int = Query(1),
    formato: str = Query("xlsx"),
):
    # Placeholder: generate Excel with openpyxl
    buf = io.BytesIO()
    buf.write(b"placeholder")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=reporte-secretaria.xlsx"})


@router.get("/total")
def reporte_total(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    trimestre: int = Query(1),
    formato: str = Query("xlsx"),
):
    buf = io.BytesIO()
    buf.write(b"placeholder")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=reporte-total.xlsx"})


@router.get("/sector/{sector_id}")
def reporte_sector(
    sector_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    formato: str = Query("xlsx"),
):
    buf = io.BytesIO()
    buf.write(b"placeholder")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=reporte-sector.xlsx"})


@router.get("/pendientes")
def reporte_pendientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    trimestre: int = Query(1),
    formato: str = Query("xlsx"),
):
    buf = io.BytesIO()
    buf.write(b"placeholder")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=pendientes.xlsx"})
