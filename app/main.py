import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("app.main")

# SWA de producción (Azure); también configurable con FRONTEND_URL / CORS_ORIGINS_EXTRA.
_AZURE_SWA_PRODUCTION = "https://lively-meadow-086bce210.1.azurestaticapps.net"


def _cors_allow_origins() -> list[str]:
    """Lista de orígenes permitidos (CORS). Sin duplicados."""
    raw = [
        _AZURE_SWA_PRODUCTION,
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if settings.CORS_ORIGINS_EXTRA:
        raw.extend([o.strip() for o in settings.CORS_ORIGINS_EXTRA.split(",") if o.strip()])
    seen: set[str] = set()
    out: list[str] = []
    for o in raw:
        o = (o or "").strip()
        if not o or o in seen:
            continue
        seen.add(o)
        out.append(o)
    return out


# Regex: localhost + cualquier subdominio de Azure Static Web Apps (*.azurestaticapps.net).
# Si el preflight OPTIONS no coincide, el navegador no recibe 200 CORS y la ruta POST responde 405.
_CORS_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$|https://.+\.azurestaticapps\.net$"

OPENAPI_TAGS = [
    {"name": "auth", "description": "Login, tokens y perfil de usuario."},
    {"name": "metas", "description": "Listado y detalle de metas por secretaría."},
    {"name": "seguimiento", "description": "Registro y actualización de seguimiento trimestral por meta."},
    {"name": "dashboard", "description": "KPIs y datos para dashboards (global y por secretaría)."},
    {"name": "admin", "description": "Secretarías, usuarios, períodos (solo admin)."},
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

# CORSMiddleware debe ser la capa exterior: en Starlette el último add_middleware se ejecuta
# primero en la petición. Si añades más middleware (TrustedHost, GZip, etc.), decláralos
# *antes* de este bloque para que sigan atendiendo OPTIONS/preflight con cabeceras CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_origin_regex=_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Evita la respuesta plana 'Internal Server Error' de Starlette: devuelve JSON con tipo y,
    si EXPOSE_INTERNAL_ERRORS=true, el mensaje del error (útil en Postman/Azure). Trace completo en logs.
    """
    from starlette.exceptions import HTTPException as StarletteHTTPException

    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    req_id = str(uuid.uuid4())[:12]
    logger.exception("Error no controlado [%s] %s %s", req_id, request.method, request.url.path)
    detail = "Error interno del servidor."
    if settings.EXPOSE_INTERNAL_ERRORS:
        msg = str(exc).strip() or repr(exc)
        detail = msg[:4000]
    elif isinstance(exc, (ProgrammingError, OperationalError)):
        parts = [str(exc).strip()]
        orig = getattr(exc, "orig", None)
        if orig is not None:
            parts.append(str(orig).strip())
        merged = " | ".join(p for p in parts if p)
        if merged:
            detail = merged[:2000]
    content: dict = {
        "detail": detail,
        "error_type": type(exc).__name__,
        "request_id": req_id,
        "path": str(request.url.path),
    }
    if not settings.EXPOSE_INTERNAL_ERRORS and not isinstance(exc, (ProgrammingError, OperationalError)):
        content["hint"] = (
            "Defina EXPOSE_INTERNAL_ERRORS=true en variables de entorno (App Service) o en backend/.env "
            "para incluir el mensaje detallado del error en esta respuesta."
        )
    return JSONResponse(status_code=500, content=content)


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
