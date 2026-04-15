# BackPortalSeguimiento

API REST del **Plan de acción – Seguimiento de metas** (Municipio de Chinchiná). FastAPI, SQLAlchemy, Alembic y despliegue orientado a Azure App Service.

## Repos relacionado

- Frontend: [FrontPortalSeguimiento](https://github.com/SergioCastroM/FrontPortalSeguimiento)

## Requisitos

- Python 3.11+
- PostgreSQL (local o Azure)
- Opcional: Docker (ver `Dockerfile`)

## Configuración

1. Copia el entorno de ejemplo:

   ```bash
   copy .env.example .env
   ```

2. Ajusta en `.env` la cadena de conexión a la base de datos y el secreto JWT (`SECRET_KEY`).

3. Crea el entorno virtual e instala dependencias:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Migraciones:

   ```bash
   alembic upgrade head
   ```

5. (Opcional) Datos de prueba:

   ```bash
   python seed.py
   ```

## Desarrollo local

Desde la carpeta `backend` (Windows PowerShell):

```powershell
.\run.ps1
```

O manualmente:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

- API: `http://localhost:8001`
- Documentación OpenAPI: `http://localhost:8001/docs`

## Estructura principal

| Ruta | Descripción |
|------|-------------|
| `app/main.py` | Aplicación FastAPI y CORS |
| `app/api/v1/` | Rutas: auth, metas, seguimiento, dashboard, excel, reportes, admin |
| `app/services/` | Lógica de negocio e importación Excel |
| `migrations/` | Alembic |

## CI/CD

Flujos en `.github/workflows/` para build y despliegue en Azure (variables y secretos en el repositorio o en Azure).
