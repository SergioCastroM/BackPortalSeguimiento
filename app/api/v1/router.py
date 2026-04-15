from fastapi import APIRouter
from app.api.v1 import auth, metas, seguimiento, dashboard, admin, excel, reportes, sisben

api_router = APIRouter()


@api_router.get("", include_in_schema=False)
def api_v1_root():
    """GET permitido en /api/v1 para comprobar que el servicio responde (evita confusión con 404/405)."""
    return {
        "message": "Plan de Acción 2026 — API v1",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
    }


api_router.include_router(auth.router)
api_router.include_router(metas.router)
api_router.include_router(seguimiento.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(excel.router)
api_router.include_router(reportes.router)
api_router.include_router(sisben.router)
