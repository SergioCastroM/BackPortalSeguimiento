# Guía: Creación y despliegue en Azure App Service

Guía paso a paso para crear un Azure App Service y desplegar tu aplicación (backend FastAPI o frontend estático).

---

## Requisitos previos

- Cuenta de [Azure](https://portal.azure.com) (nivel gratuito sirve para pruebas).
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) instalado (opcional, para comandos desde terminal).
- Código en un repositorio Git (por ejemplo GitHub).

---

## Parte 1: Crear el App Service en Azure Portal

### 1.1 Entrar al portal e iniciar creación

1. Entra en [https://portal.azure.com](https://portal.azure.com).
2. En el buscador superior escribe **App Services** y selecciona el servicio.
3. Pulsa **+ Crear** → **Aplicación web**.

### 1.2 Pestaña «Datos básicos»

| Campo | Qué poner (ejemplo) |
|-------|----------------------|
| **Suscripción** | Tu suscripción de Azure. |
| **Grupo de recursos** | Crear nuevo, p. ej. `rg-portal-seguimiento`. |
| **Nombre** | Nombre único global, p. ej. `plan-accion-2026-api`. Será la URL: `https://<nombre>.azurewebsites.net`. |
| **Publicar** | Código. |
| **Pila en tiempo de ejecución** | **Python 3.11** (backend FastAPI) o **Node 20 LTS** (si solo sirves frontend estático). |
| **Sistema operativo** | Linux (recomendado) o Windows. |
| **Región** | La más cercana, p. ej. East US, Brazil South. |

No es obligatorio crear un Plan de App Service ahora; Azure puede crear uno por defecto. Si quieres elegir:

- **Plan de App Service**: Crear nuevo → nombre p. ej. `plan-portal-seguimiento`.
- **SKU**: **F1** (gratis) o **B1** (básico, de pago).

Pulsa **Revisar y crear** y luego **Crear**.

### 1.3 Esperar al despliegue

Cuando termine, ve a **Ir al recurso** para abrir tu App Service.

---

## Parte 2: Configurar la aplicación

### 2.1 Configuración general (backend Python/FastAPI)

1. En el recurso, menú izquierdo → **Configuración** → **Configuración general**.
2. Ajusta:
   - **Pila**: Python 3.11 (o la que hayas elegido).
   - **Inicio rápido**: Si usas Gunicorn/uvicorn, en **Comando de inicio** puedes poner, por ejemplo:
     ```bash
     gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
     ```
     (En este repo la app está en `app.main:app`.)

### 2.2 Variables de entorno (Configuración de la aplicación)

1. Menú izquierdo → **Configuración** → **Configuración de la aplicación**.
2. **+ Nueva configuración de la aplicación** y añade cada variable que use tu app, por ejemplo:

   | Nombre | Valor (ejemplo) |
   |--------|------------------|
   | `DATABASE_URL` | Cadena de conexión a tu base (Azure SQL, PostgreSQL, etc.). |
   | `SECRET_KEY` | Clave secreta para JWT/sesiones. |
   | `CORS_ORIGINS` | Origen del frontend, p. ej. `https://tu-front.azurestaticapps.net`. |

3. Guarda los cambios (**Guardar** arriba).

### 2.3 Habilitar registro (opcional)

- **Registro de aplicaciones**: Activado; nivel **Información** o **Advertencia**.
- **Registro del servidor web**: Activado si quieres ver logs HTTP.

Así podrás depurar en **Registro de streaming** o descargando logs.

---

## Parte 3: Desplegar el código

Tienes varias opciones. Las más útiles: **GitHub Actions** (automático) y **ZIP deploy** (manual).

---

### Opción A: Despliegue con GitHub Actions (recomendado)

Cada push a `main` (o la rama que elijas) desplegará automáticamente.

#### A.1 Obtener perfil de publicación

1. En tu App Service → **Centro de implementación** (o **Implementación**).
2. Elige **GitHub** como origen y autoriza si hace falta.
3. En **Configuración del proveedor de implementación** no completes aún; solo necesitas el **perfil de publicación**.
4. Alternativa: en el App Service → **Propiedades** → copia **Id. de suscripción**, **Nombre del grupo de recursos** y **Nombre del sitio**.

Para obtener el perfil como archivo:

1. En el App Service, menú superior **Descargar perfil de publicación**.
2. Abre el `.PublishSettings` y localiza: **userName** (o `publishUsername`) y **userPWD** (o `publishPassword`). Los usarás como secretos.

#### A.2 Secretos en GitHub

1. Repositorio en GitHub → **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret** y crea:
   - `AZURE_WEBAPP_PUBLISH_PROFILE`: pega **todo** el contenido del archivo de perfil de publicación descargado.

(Si prefieres no usar el perfil, puedes usar `AZURE_CREDENTIALS` con un service principal; es un paso más.)

#### A.3 Workflow de GitHub Actions

En este repo ya existe el workflow en `.github/workflows/azure-app-service.yml`. Si creas el workflow desde cero, usa:

```yaml
name: Deploy to Azure App Service (API)

on:
  push:
    branches:
      - main

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v3
        with:
          app-name: 'plan-accion-2026-api'   # mismo nombre que en Azure
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

Sustituye `plan-accion-2026-api` por el nombre real de tu App Service.

Después de hacer push a `main`, el workflow desplegará automáticamente.

---

### Opción B: Despliegue con ZIP desde tu PC (manual)

Útil para pruebas rápidas sin GitHub.

1. **Preparar el paquete** (en la carpeta del backend):
   - Crea un ZIP con tu código (incluyendo `requirements.txt`, carpeta `app/`, etc.).
   - No incluyas `venv`, `__pycache__`, `.env` (las variables las pones en la Configuración de la aplicación).

2. **Desplegar con Azure CLI** (con el ZIP ya creado):

   ```bash
   az login
   az webapp deployment source config-zip \
     --resource-group rg-portal-seguimiento \
     --name plan-accion-2026-api \
     --src ruta/al/archivo.zip
   ```

   O desde PowerShell (con `az` instalado):

   ```powershell
   az webapp deployment source config-zip `
     --resource-group rg-portal-seguimiento `
     --name plan-accion-2026-api `
     --src .\deploy.zip
   ```

3. En el portal, **Centro de implementación** mostrará el estado; la primera vez puede tardar 1–2 minutos.

---

### Opción C: Crear el App Service desde Azure CLI y desplegar

Si prefieres todo por línea de comandos:

```bash
# Iniciar sesión
az login

# Crear grupo de recursos
az group create --name rg-portal-seguimiento --location eastus

# Crear Plan de App Service
az appservice plan create \
  --name plan-portal-seguimiento \
  --resource-group rg-portal-seguimiento \
  --is-linux \
  --sku B1

# Crear la Web App (Python 3.11)
az webapp create \
  --name plan-accion-2026-api \
  --resource-group rg-portal-seguimiento \
  --plan plan-portal-seguimiento \
  --runtime "PYTHON:3.11"

# Configurar comando de inicio (Gunicorn + Uvicorn para este backend)
az webapp config set \
  --name plan-accion-2026-api \
  --resource-group rg-portal-seguimiento \
  --startup-file "gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app"

# Desplegar ZIP (después de crear el zip)
az webapp deployment source config-zip \
  --resource-group rg-portal-seguimiento \
  --name plan-accion-2026-api \
  --src deploy.zip
```

Ajusta nombres, región (`eastus`), SKU (`B1`/`F1`) según tu entorno.

---

## Parte 4: Comprobar el despliegue

1. **URL**: `https://<nombre-del-app-service>.azurewebsites.net`.
2. Documentación API: `https://<nombre>.azurewebsites.net/docs` (Swagger) o `/redoc`.
3. Revisa **Registro de streaming** en el App Service si algo falla.
4. **Configuración de la aplicación**: comprueba que `DATABASE_URL` y el resto de variables estén bien (sin espacios, comillas correctas).

---

## Parte 5: Frontend (React) y API

- **Recomendación**: mantener el **frontend** en **Azure Static Web Apps** y el **backend** en **App Service**. El front llama a la URL del App Service (configurar `CORS_ORIGINS` y la variable de API en el front).

---

## Resumen rápido

| Paso | Acción |
|------|--------|
| 1 | Crear App Service en Azure Portal (o con CLI): nombre, región, pila Python 3.11. |
| 2 | Configurar comando de inicio: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app` y variables en **Configuración de la aplicación**. |
| 3 | Añadir en GitHub el secreto `AZURE_WEBAPP_PUBLISH_PROFILE` con el perfil de publicación. |
| 4 | El workflow `.github/workflows/azure-app-service.yml` ya está en el repo; hacer push a `main` para desplegar. |
| 5 | Comprobar la URL `https://<nombre>.azurewebsites.net/docs` y los logs si algo falla. |

---

## Enlaces útiles

- [Documentación App Service](https://learn.microsoft.com/azure/app-service/)
- [Desplegar con perfil de publicación (GitHub Actions)](https://learn.microsoft.com/azure/app-service/deploy-github-actions)
- [Configuración de aplicaciones Python en App Service](https://learn.microsoft.com/azure/app-service/configure-language-python)
