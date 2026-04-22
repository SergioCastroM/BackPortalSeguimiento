"""Sincronización de presupuesto MGA desde Excel (preview + confirmación)."""
from __future__ import annotations

import io
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import IndicadorProducto, Meta, ProyectoMga
from app.services.proyecto_mga_service import crear_proyecto_mga_minimo_si_falta, primer_proyecto_mga


def _norm_header(s: str) -> str:
    """
    Normaliza encabezados: quita acentos (NFD) y deja solo [a-z0-9].
    Así 'Código meta' y plantillas exportadas desde Excel coinciden con la detección.
    """
    t = unicodedata.normalize("NFD", str(s).lower().strip())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t)


def _detect_columns(columns: list[str]) -> dict[str, str | None]:
    """Asigna nombre semántico -> nombre de columna original en el DataFrame."""
    by_norm = {_norm_header(c): c for c in columns}

    def pick(*candidates: str) -> str | None:
        for cand in candidates:
            if cand in by_norm:
                return by_norm[cand]
        return None

    # Plantilla exportada por el sistema: Meta ID, Código meta, Valor inicial, …
    meta_id_col = pick("metaid", "meta_id", "idmeta", "id_meta")
    codigo = (
        pick("codigometa", "codigodelameta", "codigoindicador", "codigo")
        or next((by_norm[k] for k in by_norm if "codigo" in k and "meta" in k and "descripcion" not in k), None)
        or next((by_norm[k] for k in by_norm if k == "codigo" or (k.startswith("codigo") and "sector" not in k)), None)
    )
    if codigo and any(x in _norm_header(str(codigo)) for x in ("sector", "bpin")):
        codigo = None

    vi = (
        pick("valorinicial", "valinicial", "presupuestoinicial")
        or next((by_norm[k] for k in by_norm if "inicial" in k and "valor" in k), None)
        or next((by_norm[k] for k in by_norm if k.startswith("valor") and "inicial" in k), None)
    )
    ad = (
        pick("adiciones", "adicion", "adicciones")
        or next((by_norm[k] for k in by_norm if "adicion" in k and "meta" not in k), None)
        or next((by_norm[k] for k in by_norm if "adicion" in k), None)
    )
    ded = (
        pick("deducciones", "deduccion", "disminuciones", "reducciones", "reduccion")
        or next((by_norm[k] for k in by_norm if "deducc" in k or "reducc" in k or "disminuc" in k), None)
    )
    vf = (
        pick("valorfinal", "valfinal")
        or next((by_norm[k] for k in by_norm if "final" in k and "valor" in k), None)
    )
    return {
        "meta_id": meta_id_col,
        "codigo": codigo,
        "valor_inicial": vi,
        "adiciones": ad,
        "deducciones": ded,
        "valor_final": vf,
    }


def _to_decimal(val: Any) -> Decimal | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, Decimal):
        return val
    s = str(val).strip().replace(",", "")
    if s == "" or s.lower() in ("nan", "none"):
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def parse_presupuesto_excel(content: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Lee el Excel y devuelve filas con claves: codigo, valor_inicial, adiciones, deducciones, valor_final.
    Errores de cabecera en la lista de warnings (y lista vacía si falla grave).
    """
    warnings: list[str] = []
    df = pd.read_excel(io.BytesIO(content), header=0, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    mapping = _detect_columns(list(df.columns))
    need_codigo = not mapping.get("meta_id")
    need_val = ["valor_inicial", "adiciones", "deducciones", "valor_final"]
    missing = [k for k in need_val if not mapping.get(k)]
    if need_codigo and not mapping.get("codigo"):
        missing.insert(0, "codigo (o columna Meta ID)")
    if missing:
        raise ValueError(
            "No se pudieron detectar columnas obligatorias: "
            + ", ".join(missing)
            + f". Columnas encontradas: {list(df.columns)}. "
            "Use la plantilla exportada desde el sistema o encabezados como: "
            "Meta ID (opcional), Código meta, Valor inicial, Adiciones, Deducciones, Valor final."
        )

    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        meta_id_val: int | None = None
        if mapping.get("meta_id"):
            raw_mid = row.get(mapping["meta_id"])
            if raw_mid is not None and not (isinstance(raw_mid, float) and pd.isna(raw_mid)):
                try:
                    meta_id_val = int(float(str(raw_mid).strip()))
                except (ValueError, TypeError):
                    meta_id_val = None

        cod_s = ""
        if mapping.get("codigo"):
            cod = row.get(mapping["codigo"])
            if cod is not None and not (isinstance(cod, float) and pd.isna(cod)):
                cod_s = str(cod).strip()

        if meta_id_val is None and not cod_s:
            continue
        vi = _to_decimal(row.get(mapping["valor_inicial"])) or Decimal("0")
        ad = _to_decimal(row.get(mapping["adiciones"])) or Decimal("0")
        ded = _to_decimal(row.get(mapping["deducciones"])) or Decimal("0")
        vf = _to_decimal(row.get(mapping["valor_final"]))
        if vf is None:
            vf = vi + ad - ded
            warnings.append(f"Fila {int(idx) + 2}: sin valor final; se asume inicial + adiciones − deducciones.")
        rows.append(
            {
                "fila_excel": int(idx) + 2,
                "meta_id": meta_id_val,
                "codigo": cod_s,
                "valor_inicial": float(vi),
                "adiciones": float(ad),
                "deducciones": float(ded),
                "valor_final": float(vf),
            }
        )
    if not rows:
        raise ValueError("No hay filas de datos con Meta ID o código de meta.")
    return rows, warnings


def _metas_por_codigo_indicador(db: Session, codigo: str) -> list[Meta]:
    c = (codigo or "").strip()
    if not c:
        return []
    cl = c.strip().lower()
    return (
        db.query(Meta)
        .options(joinedload(Meta.secretaria))
        .join(IndicadorProducto, Meta.indicador_producto_id == IndicadorProducto.id)
        .filter(
            Meta.activo == True,
            IndicadorProducto.codigo.isnot(None),
            func.lower(func.trim(IndicadorProducto.codigo)) == cl,
        )
        .all()
    )


def build_preview(db: Session, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enriquece cada fila con estado, valores actuales en BD y mensajes de error."""
    out: list[dict[str, Any]] = []
    for r in rows:
        codigo = r.get("codigo") or ""
        meta_id_excel = r.get("meta_id")
        meta: Meta | None = None
        if meta_id_excel is not None:
            meta = (
                db.query(Meta)
                .options(joinedload(Meta.secretaria))
                .filter(Meta.id == int(meta_id_excel), Meta.activo == True)
                .first()
            )
        if meta is None and codigo:
            metas = _metas_por_codigo_indicador(db, codigo)
            if len(metas) == 1:
                meta = metas[0]
        base = {
            "fila_excel": r.get("fila_excel"),
            "codigo": codigo,
            "valor_inicial_nuevo": r["valor_inicial"],
            "adiciones_nuevo": r["adiciones"],
            "deducciones_nuevo": r["deducciones"],
            "valor_final_nuevo": r["valor_final"],
            "meta_id": None,
            "descripcion": None,
            "secretaria": None,
            "valor_inicial_actual": None,
            "adiciones_actual": None,
            "deducciones_actual": None,
            "valor_final_actual": None,
            "error": None,
            "aviso_formula": None,
            "aviso_sin_proyecto": None,
        }
        if meta is None:
            if meta_id_excel is not None:
                base["error"] = f"No existe meta activa con Meta ID {meta_id_excel}."
            elif codigo:
                metas = _metas_por_codigo_indicador(db, codigo)
                if len(metas) == 0:
                    base["error"] = "No hay meta activa con ese código de indicador."
                else:
                    base["error"] = f"Hay {len(metas)} metas con el mismo código; debe ser único o use Meta ID."
            else:
                base["error"] = "Indique Meta ID o código de indicador."
            out.append(base)
            continue

        p = primer_proyecto_mga(db, meta.id)
        sin_proyecto = p is None

        vi_n, ad_n, ded_n, vf_n = map(
            Decimal,
            (r["valor_inicial"], r["adiciones"], r["deducciones"], r["valor_final"]),
        )
        esperado = vi_n + ad_n - ded_n
        if abs(esperado - vf_n) > Decimal("0.02"):
            base["aviso_formula"] = (
                f"Valor final ({vf_n}) difiere de inicial+adiciones−deducciones ({esperado}). "
                "Se guardarán los valores del Excel tal cual."
            )

        base["meta_id"] = meta.id
        base["descripcion"] = (meta.descripcion or "")[:120]
        base["secretaria"] = meta.secretaria.nombre if meta.secretaria else ""
        if sin_proyecto:
            base["valor_inicial_actual"] = 0.0
            base["adiciones_actual"] = 0.0
            base["deducciones_actual"] = 0.0
            base["valor_final_actual"] = 0.0
            base["proyecto_mga_id"] = None
            base["aviso_sin_proyecto"] = (
                "La meta no tenía proyecto MGA; se creará uno al confirmar la sincronización."
            )
        else:
            base["valor_inicial_actual"] = float(p.valor_inicial or 0)
            base["adiciones_actual"] = float(p.adicion or 0)
            base["deducciones_actual"] = float(p.reduccion or 0)
            base["valor_final_actual"] = float(p.valor_final or 0)
            base["proyecto_mga_id"] = p.id
        out.append(base)
    return out


def apply_presupuesto_sync(db: Session, preview: list[dict[str, Any]]) -> tuple[int, list[str]]:
    """
    Aplica filas del preview sin error y con proyecto MGA válido.
    Las filas con error en preview se omiten. Si no había proyecto MGA, se crea al aplicar.
    Transacción única.
    """
    to_apply: list[tuple[ProyectoMga, dict[str, Any]]] = []
    for row in preview:
        if row.get("error"):
            continue
        mid = row.get("meta_id")
        if not mid:
            continue
        pid = row.get("proyecto_mga_id")
        if pid:
            p = db.query(ProyectoMga).filter(ProyectoMga.id == pid).first()
        else:
            meta = db.query(Meta).filter(Meta.id == int(mid), Meta.activo == True).first()
            if not meta:
                continue
            p = crear_proyecto_mga_minimo_si_falta(db, meta)
        if not p:
            continue
        to_apply.append((p, row))

    if not to_apply:
        return 0, ["No hay filas válidas para aplicar. Corrija los errores del preview o suba otro archivo."]

    try:
        for p, row in to_apply:
            p.valor_inicial = Decimal(str(row["valor_inicial_nuevo"]))
            p.adicion = Decimal(str(row["adiciones_nuevo"]))
            p.reduccion = Decimal(str(row["deducciones_nuevo"]))
            p.valor_final = Decimal(str(row["valor_final_nuevo"]))
        db.commit()
    except Exception as e:
        db.rollback()
        return 0, [str(e)]
    return len(to_apply), []
