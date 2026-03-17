from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.core.config import get_settings
from app.api.v1.router import api_router

settings = get_settings()

OPENAPI_TAGS = [
    {"name": "auth", "description": "Login, tokens y perfil de usuario."},
    {"name": "metas", "description": "Listado y detalle de metas por secretaría."},
    {"name": "seguimiento", "description": "Registro y actualización de seguimiento trimestral por meta."},
    {"name": "dashboard", "description": "KPIs y datos para dashboards (global y por secretaría)."},
    {"name": "admin", "description": "Secretarías, usuarios, trimestres (solo admin)."},
    {"name": "excel", "description": "Carga y confirmación de importación desde Excel."},
    {"name": "reportes", "description": "Descarga de reportes Excel/PDF por secretaría, total, pendientes."},
]

app = FastAPI(
    title="Plan de Acción 2026 - Seguimiento de Metas",
    description="API para el sistema de seguimiento trimestral de metas.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    servers=[{"url": "http://localhost:8001", "description": "Backend local"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return RedirectResponse(url="/docs")


@app.get("/swagger", include_in_schema=False)
def swagger_redirect():
    """Redirige a la documentación Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}
