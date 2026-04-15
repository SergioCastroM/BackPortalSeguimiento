from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db.session import get_db
from app.core.deps import require_admin
from app.models import Usuario
from app.services.reportes_excel import (
    build_reporte_pendientes_excel,
    build_reporte_secretaria_excel,
    build_reporte_sector_excel,
    build_reporte_total_excel,
)

router = APIRouter(prefix="/reportes", tags=["reportes"])


def _xlsx_response(data: bytes, filename: str) -> StreamingResponse:
    buf = io.BytesIO(data)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/secretaria/{secretaria_id}")
def reporte_secretaria(
    secretaria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    trimestre: int = Query(1),
    formato: str = Query("xlsx"),
):
    body = build_reporte_secretaria_excel(db, secretaria_id, anio, trimestre)
    return _xlsx_response(body, f"reporte-secretaria-{anio}-T{trimestre}.xlsx")


@router.get("/total")
def reporte_total(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    trimestre: int = Query(1),
    formato: str = Query("xlsx"),
):
    body = build_reporte_total_excel(db, anio, trimestre)
    return _xlsx_response(body, f"reporte-total-{anio}-T{trimestre}.xlsx")


@router.get("/sector/{sector_id}")
def reporte_sector(
    sector_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    trimestre: int = Query(1),
    formato: str = Query("xlsx"),
):
    body = build_reporte_sector_excel(db, sector_id, anio, trimestre)
    return _xlsx_response(body, f"reporte-sector-{sector_id}-{anio}-T{trimestre}.xlsx")


@router.get("/pendientes")
def reporte_pendientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    anio: int = Query(2026),
    trimestre: int = Query(1),
    formato: str = Query("xlsx"),
):
    body = build_reporte_pendientes_excel(db, anio, trimestre)
    return _xlsx_response(body, f"pendientes-{anio}-T{trimestre}.xlsx")
