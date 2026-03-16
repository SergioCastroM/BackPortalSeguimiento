"""
Importador mínimo de Excel para metas.
Lee .xlsx: columna 1 = Oficina/Secretaría, columna 3 = Descripción meta (por posición).
Si el Excel tiene encabezado en fila 0, los datos desde fila 1.
"""
from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models import Meta, Secretaria, LineaEstrategica, IndicadorProducto, Sector, Programa, Producto


# Mapeo por posición: 0=Plan, 1=Oficina/Secretaría, 2=Línea, 3=Meta/Descripción
COL_SECRETARIA = 1
COL_DESCRIPCION = 3
COL_META_2026 = 14  # valor esperado 2026 si existe
MAX_PREVIEW_ROWS = 10
MAX_FILE_SIZE_MB = 500


def _normalize_name(name: Any) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return str(name).strip()


def _get_or_create_indicador(db: Session) -> IndicadorProducto:
    ind = db.query(IndicadorProducto).first()
    if ind:
        return ind
    sector = db.query(Sector).first()
    if not sector:
        sector = Sector(codigo="GEN", nombre="General")
        db.add(sector)
        db.flush()
    programa = db.query(Programa).filter(Programa.sector_id == sector.id).first()
    if not programa:
        programa = Programa(codigo="P00", nombre="Programa general", sector_id=sector.id)
        db.add(programa)
        db.flush()
    producto = db.query(Producto).filter(Producto.programa_id == programa.id).first()
    if not producto:
        producto = Producto(codigo="PR0", nombre="Producto general", programa_id=programa.id)
        db.add(producto)
        db.flush()
    ind = IndicadorProducto(codigo="IND001", nombre="Indicador importado", producto_id=producto.id)
    db.add(ind)
    db.flush()
    return ind


def _secretaria_by_name(db: Session, name: str) -> int | None:
    if not name:
        return None
    name = name.strip()
    s = db.query(Secretaria).filter(Secretaria.nombre.ilike(f"%{name}%")).first()
    return s.id if s else None


def parse_excel(content: bytes) -> tuple[list[dict], list[dict], list[str]]:
    """
    Parsea el Excel y devuelve (preview_rows, filas_para_importar, warnings).
    """
    df = pd.read_excel(io.BytesIO(content), header=0, engine="openpyxl")
    if df.empty or len(df.columns) < 4:
        return [], [], ["El archivo tiene pocas columnas. Se esperan al menos: Oficina (col 2), Meta/Descripción (col 4)."]

    preview = []
    filas = []
    warnings = []

    for idx, row in df.iterrows():
        oficina = _normalize_name(row.iloc[COL_SECRETARIA] if len(row) > COL_SECRETARIA else "")
        desc = _normalize_name(row.iloc[COL_DESCRIPCION] if len(row) > COL_DESCRIPCION else "")
        valor_2026 = 0
        if len(row) > COL_META_2026:
            try:
                v = row.iloc[COL_META_2026]
                if v is not None and not (isinstance(v, float) and pd.isna(v)):
                    valor_2026 = float(v)
            except (TypeError, ValueError):
                pass

        if not desc:
            continue
        filas.append({"oficina": oficina, "descripcion": desc[:2000], "valor_esperado_2026": valor_2026})
        if len(preview) < MAX_PREVIEW_ROWS:
            preview.append({"Secretaría": oficina, "Meta": desc[:80] + ("..." if len(desc) > 80 else ""), "Valor 2026": valor_2026})

    if not filas:
        warnings.append("No se encontraron filas con descripción de meta.")
    return preview, filas, warnings


def run_import(db: Session, filas: list[dict], linea_id: int | None = None) -> tuple[int, int, int]:
    """
    Inserta o actualiza metas. Retorna (inserted, updated, errors).
    """
    inserted = 0
    updated = 0
    errors = 0
    indicador = _get_or_create_indicador(db)
    lineas = db.query(LineaEstrategica).all()
    linea_id = linea_id or (lineas[0].id if lineas else None)
    secretarias_by_name = {s.nombre.strip().upper(): s.id for s in db.query(Secretaria).all()}

    for f in filas:
        try:
            oficina = (f.get("oficina") or "").strip()
            desc = (f.get("descripcion") or "").strip()
            if not desc:
                errors += 1
                continue
            sec_id = None
            if oficina:
                for nom, sid in secretarias_by_name.items():
                    if oficina.upper() in nom or nom in oficina.upper():
                        sec_id = sid
                        break
            if not sec_id:
                sec_id = list(secretarias_by_name.values())[0] if secretarias_by_name else None
            if not sec_id:
                errors += 1
                continue

            valor_2026 = float(f.get("valor_esperado_2026") or 0)
            existing = db.query(Meta).filter(
                Meta.secretaria_id == sec_id,
                Meta.descripcion == desc[:500],
            ).first()
            if existing:
                existing.valor_esperado_2026 = Decimal(str(valor_2026))
                existing.meta_cuatrienio = Decimal(str(valor_2026 * 4))
                db.flush()
                updated += 1
            else:
                meta = Meta(
                    descripcion=desc,
                    linea_estrategica_id=linea_id,
                    secretaria_id=sec_id,
                    indicador_producto_id=indicador.id,
                    meta_cuatrienio=Decimal(str(valor_2026 * 4)),
                    valor_esperado_2026=Decimal(str(valor_2026)),
                    activo=True,
                )
                db.add(meta)
                inserted += 1
        except Exception:
            errors += 1
    db.commit()
    return inserted, updated, errors
