import uuid
from collections import Counter
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import require_admin
from app.models import Usuario
from app.services.excel_importer import parse_excel, run_import

router = APIRouter(prefix="/excel", tags=["excel"])

# In-memory store: job_id -> { "filas": [...], "preview": [...], "warnings": [...] }
_upload_preview: dict = {}
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx")
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (máx. 50 MB)")
    try:
        preview, filas, warnings = parse_excel(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el Excel: {e!s}")
    # Contar metas por secretaría/oficina (nombre normalizado)
    oficinas = [f.get("oficina") or "(Sin oficina)" for f in filas]
    metas_por_secretaria = [{"oficina": nombre, "cantidad": count} for nombre, count in sorted(Counter(oficinas).items(), key=lambda x: -x[1])]
    job_id = str(uuid.uuid4())
    new_count = len(filas)
    resumen = {"new": new_count, "update": 0, "errors": 0}
    _upload_preview[job_id] = {"filas": filas, "preview": preview, "warnings": warnings}
    return {
        "job_id": job_id,
        "preview": preview,
        "resumen": resumen,
        "warnings": warnings,
        "metas_por_secretaria": metas_por_secretaria,
    }


@router.post("/confirm/{job_id}")
def confirm_import(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    if job_id not in _upload_preview:
        raise HTTPException(status_code=404, detail="Job no encontrado o expirado")
    data = _upload_preview.pop(job_id)
    filas = data.get("filas") or []
    inserted, updated, errors = run_import(db, filas)
    return {"message": "Importación completada", "inserted": inserted, "updated": updated, "errors": errors}


@router.get("/logs")
def list_logs(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return {"items": [], "total": 0}
