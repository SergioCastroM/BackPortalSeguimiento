import uuid
from collections import defaultdict
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import require_admin
from app.models import Usuario
from app.services.excel_importer import (
    parse_excel,
    run_import,
    replace_sectors_catalog,
    normalize_secretaria_key,
    normalize_secretaria_title_for_display,
)

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
    # Agrupar por clave normalizada para no duplicar filas por mayúsculas/minúsculas distintas
    grupos: dict[str, dict] = defaultdict(lambda: {"cantidad": 0, "label": ""})
    for f in filas:
        raw = (f.get("oficina") or "").strip()
        k = normalize_secretaria_key(raw)
        label = normalize_secretaria_title_for_display(raw) if raw else "(Sin oficina)"
        if not grupos[k]["label"]:
            grupos[k]["label"] = label
        grupos[k]["cantidad"] += 1
    metas_por_secretaria = [
        {"oficina": grupos[k]["label"], "cantidad": grupos[k]["cantidad"]}
        for k in sorted(grupos, key=lambda x: -grupos[x]["cantidad"])
    ]
    grupos_sec: dict[str, dict] = defaultdict(lambda: {"cantidad": 0, "label": "", "codigo": ""})
    for f in filas:
        raw_s = (f.get("sector") or "").strip()
        raw_c = (f.get("sector_codigo") or "").strip()
        if not raw_s and not raw_c:
            continue
        kn = normalize_secretaria_key(raw_s)
        kc = normalize_secretaria_key(raw_c)
        group_key = f"{kc}|{kn}"
        label_n = normalize_secretaria_title_for_display(raw_s) if raw_s else "(Sin nombre)"
        codigo_disp = raw_c if raw_c else "—"
        if not grupos_sec[group_key]["label"]:
            grupos_sec[group_key]["label"] = label_n
        if not grupos_sec[group_key]["codigo"]:
            grupos_sec[group_key]["codigo"] = codigo_disp
        grupos_sec[group_key]["cantidad"] += 1
    metas_por_sector = [
        {
            "sector": grupos_sec[k]["label"],
            "codigo": grupos_sec[k]["codigo"],
            "cantidad": grupos_sec[k]["cantidad"],
        }
        for k in sorted(grupos_sec, key=lambda x: -grupos_sec[x]["cantidad"])
    ]
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
        "metas_por_sector": metas_por_sector,
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


@router.post("/replace-sectors/{job_id}")
def replace_sectors_from_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    """
    Sustituye el catálogo de sectores por los únicos del Excel del job.
    Elimina metas, seguimientos, proyectos MGA y la cadena programa/producto/indicador previa.
    """
    if job_id not in _upload_preview:
        raise HTTPException(status_code=404, detail="Job no encontrado o expirado")
    data = _upload_preview[job_id]
    filas = data.get("filas") or []
    result = replace_sectors_catalog(db, filas)
    return result


@router.get("/logs")
def list_logs(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return {"items": [], "total": 0}
