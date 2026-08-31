from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.periodo_config import get_periodo_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/periodos")
def get_config_periodos(db: Session = Depends(get_db)):
    """Público: tipo de período activo (textos y cantidad). No expone secretos."""
    return get_periodo_config(db)
