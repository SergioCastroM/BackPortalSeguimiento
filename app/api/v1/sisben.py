from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.core.deps import require_admin
from app.models import Usuario
from app.services.sisben_report import parse_sisben_excel

router = APIRouter(prefix="/sisben", tags=["sisben"])

MAX_FILE_BYTES = 50 * 1024 * 1024


@router.post("/informe")
async def upload_informe_sisben(
    file: UploadFile = File(...),
    current_user: Usuario = Depends(require_admin),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx")
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande (máx. 50 MB)")
    try:
        return parse_sisben_excel(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el Excel: {e!s}")
