# Backend Plan de Acción 2026 - Puerto 8001 (para no chocar con otro servicio en 8000)
Set-Location $PSScriptRoot
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
