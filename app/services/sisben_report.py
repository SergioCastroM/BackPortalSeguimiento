"""
Informe Sisben: Excel con columnas ID, Número, Fecha, Nombre Solicitante, ...
Tipo de ficha = parte izquierda de "Nombre Solicitante" antes del separador " - " (guión con espacios),
p. ej. "MODIFICACIÓN DE FICHA - LUZ DARI..." → "MODIFICACIÓN DE FICHA".
Las agrupaciones por año y por mes se hacen siempre por tipo de ficha + período (no hay totales globales por mes/año).
"""
from __future__ import annotations

import io
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from app.services.excel_importer import normalize_secretaria_key


def _norm_col(name: Any) -> str:
    return normalize_secretaria_key(name) if name is not None else ""


def _tipo_ficha_desde_nombre_solicitante(text: str) -> str:
    """
    Tipo de ficha = primera parte del nombre antes de " - " (como en Excel Sisben).
    Ej.: "MODIFICACIÓN DE FICHA - LUZ DARI BEDOYA AGUDELO" → "MODIFICACIÓN DE FICHA"
    Si no hay guión, se intenta coma/punto y coma; si no, el texto completo (recortado).
    """
    s = (text or "").strip()
    if not s:
        return "(Sin tipo)"
    s = re.sub(r"\s+", " ", s)
    # Regla principal: separador espacio-guión-espacio (o variantes de espacios)
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    if len(parts) >= 2 and parts[0].strip():
        return parts[0].strip()[:300]
    for sep in [",", ";", "\n", "\r"]:
        if sep in s:
            part = s.split(sep)[0].strip()
            if part:
                return part[:300]
    out = s[:300].strip()
    return out if out else "(Sin tipo)"


def _parse_fecha_string(s: str) -> tuple[int | None, int | None]:
    """
    Texto típico de Excel en español/Windows: mes/día/año con AM/PM (locale en-US).
    Con dayfirst=True, "1/5/2026" se lee como 1-may en vez de 5-ene y reparte mal los meses.

    Heurística para a/b/aaaa:
    - Si a > 12 → día/mes (ej. 25/1/2026).
    - Si b > 12 → mes/día (ej. 1/25/2026 o 2/27/2026).
    - Si ambos ≤ 12 → mes/día (comportamiento habitual de Excel exportado en inglés).
    """
    s = s.strip()
    if not s:
        return None, None
    m = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            dayfirst = True
        elif b > 12:
            dayfirst = False
        else:
            dayfirst = False  # M/D/Y (evita inflar meses 3–12 con datos solo de ene/feb)
        dt = pd.to_datetime(s, dayfirst=dayfirst, errors="coerce")
    else:
        dt = pd.to_datetime(s, dayfirst=False, errors="coerce")
    if pd.isna(dt):
        return None, None
    return int(dt.year), int(dt.month)


def _parse_fecha(val: Any) -> tuple[int | None, int | None]:
    """
    Devuelve (año, mes) para agrupar por tipo+año y tipo+mes.

    - Celdas de fecha reales en Excel: Timestamp/datetime → año/mes del calendario.
    - Serial numérico Excel (días desde 1899-12-30) en rango típico.
    - Cadenas: ver `_parse_fecha_string` (M/D/Y por defecto si es ambiguo).
    """
    if val is None:
        return None, None
    if isinstance(val, float) and pd.isna(val):
        return None, None

    try:
        if isinstance(val, pd.Timestamp):
            if pd.isna(val):
                return None, None
            return int(val.year), int(val.month)

        if isinstance(val, datetime):
            return int(val.year), int(val.month)

        if isinstance(val, date):
            return int(val.year), int(val.month)

        if isinstance(val, np.datetime64):
            ts = pd.Timestamp(val)
            if pd.isna(ts):
                return None, None
            return int(ts.year), int(ts.month)

        # Serial numérico de Excel (p. ej. columna numérica con formato fecha)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            fv = float(val)
            if 35_000 <= fv <= 120_000:
                ts = pd.to_datetime(fv, unit="D", origin="1899-12-30", errors="coerce")
                if not pd.isna(ts):
                    return int(ts.year), int(ts.month)

        if isinstance(val, str):
            return _parse_fecha_string(val)

        dt = pd.to_datetime(val, errors="coerce")
        if pd.isna(dt):
            return None, None
        return int(dt.year), int(dt.month)
    except Exception:
        return None, None


def _detect_columns(df: pd.DataFrame) -> tuple[int, int, int | None, list[str]]:
    """Índices de Fecha, Nombre Solicitante y Dirección (columna E si existe)."""
    warnings: list[str] = []
    n = len(df.columns)
    norms = [_norm_col(str(df.columns[i]).strip()) for i in range(n)]
    idx_fecha = min(2, max(0, n - 1))
    idx_nombre = min(3, max(0, n - 1))
    idx_direccion: int | None = min(4, max(0, n - 1)) if n > 4 else None
    for i, nk in enumerate(norms):
        if nk == "fecha" or (nk.startswith("fecha") and "solicitante" not in nk):
            idx_fecha = i
        if "nombre" in nk and "solicitante" in nk:
            idx_nombre = i
        if nk == "nombre solicitante":
            idx_nombre = i
        if nk == "direccion" or nk.startswith("direccion"):
            idx_direccion = i
    if n < 4:
        warnings.append("Se esperan al menos 4 columnas (hasta Nombre Solicitante).")
    if n < 5 and idx_direccion is None:
        warnings.append("No hay columna Dirección (columna E); las anomalías por dirección no estarán disponibles.")
    return idx_fecha, idx_nombre, idx_direccion, warnings


def _cell_str(row: Any, idx: int | None) -> str:
    if idx is None or len(row) <= idx:
        return ""
    val = row.iloc[idx]
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def parse_sisben_excel(content: bytes) -> dict[str, Any]:
    """
    Lee el Excel y devuelve filas normalizadas + agregaciones.
    """
    df = pd.read_excel(io.BytesIO(content), header=0, engine="openpyxl")
    warnings: list[str] = []
    if df.empty:
        return {
            "total_filas": 0,
            "filas_muestra": [],
            "por_tipo_ficha": [],
            "por_tipo_anio": [],
            "por_tipo_mes_anio": [],
            "nombres_repetidos": [],
            "direcciones_repetidas": [],
            "warnings": ["El archivo no tiene filas de datos."],
        }

    idx_fecha, idx_nombre, idx_direccion, det_warnings = _detect_columns(df)
    warnings.extend(det_warnings)

    filas: list[dict[str, Any]] = []
    por_tipo: dict[str, int] = defaultdict(int)
    por_tipo_anio: dict[tuple[str, int], int] = defaultdict(int)
    por_tipo_mes: dict[tuple[str, int, int], int] = defaultdict(int)
    cnt_nombre_completo: dict[str, int] = defaultdict(int)
    cnt_direccion: dict[str, int] = defaultdict(int)

    for _, row in df.iterrows():
        raw_nombre = row.iloc[idx_nombre] if len(row) > idx_nombre else None
        raw_fecha = row.iloc[idx_fecha] if len(row) > idx_fecha else None
        nombre_txt = "" if raw_nombre is None or (isinstance(raw_nombre, float) and pd.isna(raw_nombre)) else str(raw_nombre).strip()
        dir_txt = _cell_str(row, idx_direccion)
        if nombre_txt:
            cnt_nombre_completo[nombre_txt] += 1
        if dir_txt:
            cnt_direccion[dir_txt] += 1
        tipo_ficha = _tipo_ficha_desde_nombre_solicitante(nombre_txt)
        anio, mes = _parse_fecha(raw_fecha)

        filas.append(
            {
                "tipo_ficha": tipo_ficha,
                "nombre_solicitante": nombre_txt[:500],
                "anio": anio,
                "mes": mes,
                "mes_label": f"{anio}-{mes:02d}" if anio and mes else None,
            }
        )
        por_tipo[tipo_ficha] += 1
        if anio is not None:
            por_tipo_anio[(tipo_ficha, anio)] += 1
        if anio is not None and mes is not None:
            por_tipo_mes[(tipo_ficha, anio, mes)] += 1

    sin_fecha = sum(1 for f in filas if f["anio"] is None)
    if sin_fecha:
        warnings.append(
            f"{sin_fecha} fila(s) sin fecha válida en la columna Fecha "
            "(no entran en agregados por tipo+año ni por tipo+mes)."
        )

    por_tipo_list = [{"tipo_ficha": k, "cantidad": v} for k, v in sorted(por_tipo.items(), key=lambda x: -x[1])]
    por_tipo_anio_list = [
        {"tipo_ficha": tf, "anio": a, "cantidad": c}
        for (tf, a), c in sorted(por_tipo_anio.items(), key=lambda kv: (kv[0][1], kv[0][0]))
    ]
    por_tipo_mes_list = [
        {"tipo_ficha": tf, "anio": a, "mes": m, "mes_label": f"{a}-{m:02d}", "cantidad": c}
        for (tf, a, m), c in sorted(
            por_tipo_mes.items(),
            key=lambda kv: (kv[0][1], kv[0][2], kv[0][0]),
        )
    ]

    muestra = filas[:50]

    # Anomalías: solo valores que aparecen 2+ veces, ordenados por frecuencia descendente
    nombres_rep = [
        {"nombre_solicitante": k, "veces": v}
        for k, v in sorted(cnt_nombre_completo.items(), key=lambda x: (-x[1], x[0]))
        if v >= 2
    ]
    dirs_rep = [
        {"direccion": k, "veces": v}
        for k, v in sorted(cnt_direccion.items(), key=lambda x: (-x[1], x[0]))
        if v >= 2
    ]

    return {
        "total_filas": len(filas),
        "filas_muestra": muestra,
        "por_tipo_ficha": por_tipo_list,
        "por_tipo_anio": por_tipo_anio_list,
        "por_tipo_mes_anio": por_tipo_mes_list,
        "nombres_repetidos": nombres_rep,
        "direcciones_repetidas": dirs_rep,
        "warnings": warnings,
    }
