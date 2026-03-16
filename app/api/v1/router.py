from fastapi import APIRouter
from app.api.v1 import auth, metas, seguimiento, dashboard, admin, excel, reportes

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(metas.router)
api_router.include_router(seguimiento.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(excel.router)
api_router.include_router(reportes.router)
