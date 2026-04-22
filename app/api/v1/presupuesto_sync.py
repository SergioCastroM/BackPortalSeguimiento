"""Admin: sincronización de presupuesto MGA desde Excel (vista previa + confirmación)."""
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.core.deps import require_admin
from app.models import Meta, Usuario
from app.services.presupuesto_sync_service import (
    apply_presupuesto_sync,
    build_preview,
    parse_presupuesto_excel,
)

router = APIRouter(prefix="/admin/presupuesto-sync", tags=["admin"])

_jobs: dict[str, dict] = {}
MAX_FILE_BYTES = 10 * 1024 * 1024


@router.get("/template")
def presupuesto_sync_template(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    metas = (
        db.query(Meta)
        .filter(Meta.activo == True)
        .options(joinedload(Meta.secretaria), joinedload(Meta.indicador_producto))
        .order_by(Meta.secretaria_id, Meta.id)
        .all()
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Plantilla presupuesto"
    headers = [
        "Meta ID",
        "Indicador ID",
        "Código meta",
        "Meta descripción",
        "Secretaría",
        "Valor inicial",
        "Adiciones",
        "Deducciones",
        "Valor final",
    ]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    for m in metas:
        ind = m.indicador_producto
        ws.append(
            [
                m.id,
                ind.id if ind else "",
                (ind.codigo if ind else "") or "",
                (m.descripcion or "")[:350],
                m.secretaria.nombre if m.secretaria else "",
                "",
                "",
                "",
                "",
            ]
        )

    widths = [10, 12, 18, 52, 28, 16, 14, 14, 16]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plantilla-presupuesto-sync.xlsx"'},
    )


@router.post("/upload")
async def presupuesto_sync_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx")
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (máx. 10 MB)")
    try:
        rows, parse_warnings = parse_presupuesto_excel(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    preview = build_preview(db, rows)
    err_count = sum(1 for r in preview if r.get("error"))
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"rows": rows}
    return {
        "job_id": job_id,
        "preview": preview,
        "resumen": {
            "filas": len(preview),
            "validas": len(preview) - err_count,
            "con_error": err_count,
        },
        "warnings": parse_warnings,
    }


@router.post("/confirm/{job_id}")
def presupuesto_sync_confirm(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Sesión de sincronización no encontrada o expirada. Vuelva a subir el archivo.")
    data = _jobs[job_id]
    rows = data.get("rows") or []
    preview = build_preview(db, rows)
    n, errs = apply_presupuesto_sync(db, preview)
    if n == 0 and errs:
        raise HTTPException(status_code=400, detail="; ".join(errs))
    _jobs.pop(job_id, None)
    return {
        "actualizados": n,
        "mensaje": f"Se actualizaron {n} proyecto(s) MGA con los valores del Excel.",
        "advertencias": errs,
    }
