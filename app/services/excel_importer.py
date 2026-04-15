"""
Importador mínimo de Excel para metas.
Encabezado en fila 0, datos desde fila 1.

Formato habitual municipal:
  - A: Plan de desarrollo (no es sector).
  - B: Secretaría / oficina
  - C: Línea estratégica
  - D: Descripción de la meta
  - E: (otros campos según plantilla)
  - F: Código del sector
  - G: Nombre del sector

Columnas MGA/BPIN (si existen en el archivo, por encabezado):
  - Código BPIN - Nacional / BPIN Nacional / código BPIN, etc.
  - Valor inicial, Adición(es), Deducción(es) / Reducción(es), Valor final
  - Nombre proyecto / proyecto MGA (opcional)

Las columnas se resuelven por encabezado; si no hay encabezados claros y hay suficientes
columnas, por defecto F=índice 5 (código) y G=índice 6 (nombre).
"""
from __future__ import annotations

import io
import re
import unicodedata
from decimal import Decimal
from typing import Any

import pandas as pd
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import (
    Meta,
    Secretaria,
    LineaEstrategica,
    IndicadorProducto,
    Sector,
    Programa,
    Producto,
    SeguimientoMeta,
    ProyectoMga,
    ActividadMga,
    PresupuestoFuente,
)
from app.services.proyecto_mga_service import recalcular_valor_final


# Valores por defecto si no hay encabezado reconocible (índices 0-based)
DEFAULT_COL_SECRETARIA = 1
DEFAULT_COL_DESCRIPCION = 3
DEFAULT_COL_META_2026 = 14
# Sector: F=código (índice 5), G=nombre (índice 6); legado E (índice 4) solo si hay pocas columnas
DEFAULT_COL_SECTOR_CODIGO = 5
DEFAULT_COL_SECTOR_NOMBRE = 6
DEFAULT_COL_SECTOR_NOMBRE_LEGACY = 4

MAX_PREVIEW_ROWS = 10
MAX_FILE_SIZE_MB = 500


@dataclass
class ExcelColumnMap:
    """idx_sector = nombre (columna G); idx_sector_codigo = código (columna F)."""
    idx_sector: int | None
    idx_sector_codigo: int | None
    idx_secretaria: int
    idx_descripcion: int
    idx_valor_2026: int | None
    idx_codigo_bpin: int | None
    idx_valor_inicial: int | None
    idx_adicion: int | None
    idx_reduccion: int | None
    idx_valor_final: int | None
    idx_nombre_proyecto: int | None


# Artículos/preposiciones comunes en nombres de secretarías (título legible)
_SMALL_WORDS_ES = frozenset(
    {"de", "del", "la", "las", "los", "y", "e", "en", "al", "a", "por", "con", "sin", "sobre"}
)


def normalize_secretaria_key(name: Any) -> str:
    """
    Clave estable para comparar secretarías/oficinas con el catálogo en BD:
    - mayúsculas/minúsculas
    - espacios repetidos
    - tildes y diacríticos (Excel a menudo sin tilde; BD con tilde → misma clave)
    - apóstrofos tipográficos (TIC'S vs TIC'S)
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = str(name).strip()
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    # Unificar apóstrofos
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    s = re.sub(r"\s+", " ", s)
    s = s.casefold()
    # NFD + quitar marcas combinantes → "Secretaría" y "Secretaria" alinean; "Planeación"/"Planeacion" idem
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_secretaria_title_for_display(name: Any) -> str:
    """Nombre legible para previsualización (título en español aproximado)."""
    key = normalize_secretaria_key(name)
    if not key:
        return ""
    words = key.split()
    out: list[str] = []
    for i, w in enumerate(words):
        if i > 0 and w in _SMALL_WORDS_ES:
            out.append(w)
        else:
            out.append(w.capitalize() if w else "")
    return " ".join(out)


def _norm_header(col: Any) -> str:
    return normalize_secretaria_key(col) if col is not None else ""


def _header_es_codigo_sector(nk: str) -> bool:
    if not nk:
        return False
    if "codigo" in nk and "sector" in nk:
        return True
    if nk.startswith("codigo") and "sector" in nk:
        return True
    if nk in ("cod sector", "cod. sector", "id sector"):
        return True
    if nk.startswith("cod ") and "sector" in nk:
        return True
    return False


def _header_es_nombre_sector(nk: str) -> bool:
    if not nk or _header_es_codigo_sector(nk):
        return False
    if nk in ("sector", "sectores", "nombre sector", "nombre del sector", "sector nombre"):
        return True
    if nk.startswith("sector") and "secretaria" not in nk and "codigo" not in nk:
        return True
    return False


def _header_es_bpin(nk: str) -> bool:
    """Encabezados tipo «Código BPIN - Nacional», «BPIN Nacional», etc."""
    if not nk or _header_es_codigo_sector(nk):
        return False
    if "bpin" not in nk:
        return False
    if "nacional" in nk:
        return True
    if "codigo" in nk or nk.startswith("codigo"):
        return True
    if nk == "bpin" or nk.startswith("bpin "):
        return True
    return False


def _header_es_valor_inicial(nk: str) -> bool:
    return bool(nk) and "valor" in nk and "inicial" in nk


def _header_es_valor_final_mga(nk: str) -> bool:
    """Valor final presupuestal MGA (no confundir con «valor ejecutado»)."""
    if not nk or "valor" not in nk or "final" not in nk:
        return False
    if "ejecut" in nk:
        return False
    return True


def _header_es_adicion(nk: str) -> bool:
    return bool(nk) and ("adicion" in nk or "adiciones" in nk)


def _header_es_reduccion(nk: str) -> bool:
    return bool(nk) and (
        "deduccion" in nk
        or "deducciones" in nk
        or "reduccion" in nk
        or "reducciones" in nk
    )


def _header_es_nombre_proyecto(nk: str) -> bool:
    if not nk:
        return False
    if "proyecto" in nk and "nombre" in nk:
        return True
    if nk in ("proyecto mga", "proyecto", "nombre proyecto"):
        return True
    if nk.startswith("proyecto ") and "bpin" not in nk:
        return True
    return False


def _detect_excel_columns(df: pd.DataFrame) -> tuple[ExcelColumnMap, list[str]]:
    """
    Resuelve columnas por encabezado. La columna A suele ser Plan de desarrollo, no sector.
    """
    n = len(df.columns)
    norms = [_norm_header(str(df.columns[i]).strip()) for i in range(n)]
    extra: list[str] = []

    def pick_secretaria() -> int:
        for i, nk in enumerate(norms):
            if nk in ("secretaria", "secretarias", "oficina", "oficinas", "dependencia"):
                return i
            if ("secretaria" in nk or "oficina" in nk) and "sector" not in nk:
                return i
        return min(DEFAULT_COL_SECRETARIA, n - 1)

    def pick_descripcion() -> int:
        for i, nk in enumerate(norms):
            if nk in ("meta", "metas", "descripcion", "descripcion meta", "indicador"):
                return i
            if ("meta" in nk or "descripcion" in nk) and "secretaria" not in nk:
                return i
        return min(DEFAULT_COL_DESCRIPCION, n - 1)

    def pick_valor_2026() -> int | None:
        for i, nk in enumerate(norms):
            if "2026" in nk and "trimestre" not in nk:
                return i
            if "valor" in nk and "2026" in nk:
                return i
            if nk in ("valor esperado 2026", "valor meta 2026"):
                return i
        if n > DEFAULT_COL_META_2026:
            return DEFAULT_COL_META_2026
        return None

    def pick_optional(match_fn) -> int | None:
        for i, nk in enumerate(norms):
            if match_fn(nk):
                return i
        return None

    idx_sec_cod: int | None = None
    for i, nk in enumerate(norms):
        if _header_es_codigo_sector(nk):
            idx_sec_cod = i
            break

    idx_sec: int | None = None
    for i, nk in enumerate(norms):
        if _header_es_nombre_sector(nk):
            idx_sec = i
            break
    if idx_sec is None:
        for i, nk in enumerate(norms):
            if i == 0:
                continue
            if not nk:
                continue
            if nk in ("sector", "sectores"):
                idx_sec = i
                break

    if idx_sec is None and n > DEFAULT_COL_SECTOR_NOMBRE:
        idx_sec = DEFAULT_COL_SECTOR_NOMBRE
        extra.append(
            "No se encontró el encabezado de nombre de sector; se asume la columna G (índice 6). "
            "Código en F (índice 5), nombre en G (índice 6)."
        )
    elif idx_sec is None and n == DEFAULT_COL_SECTOR_NOMBRE:
        extra.append(
            "Hay 6 columnas (A–F): falta la columna G con el nombre del sector. "
            "Se esperan al menos 7 columnas (A–G) con código en F y nombre en G."
        )
    elif idx_sec is None and n > DEFAULT_COL_SECTOR_NOMBRE_LEGACY and n < DEFAULT_COL_SECTOR_NOMBRE:
        idx_sec = DEFAULT_COL_SECTOR_NOMBRE_LEGACY
        extra.append(
            "No se encontró encabezado de sector; se asume la columna E (índice 4), formato antiguo."
        )
    elif idx_sec is None:
        extra.append("No hay columna para nombre de sector; en importación se usará el indicador genérico.")

    if idx_sec_cod is None and n > DEFAULT_COL_SECTOR_CODIGO:
        idx_sec_cod = DEFAULT_COL_SECTOR_CODIGO
        extra.append(
            "No se encontró encabezado de código de sector; se asume la columna F (índice 5)."
        )

    mga_cols = (
        pick_optional(_header_es_bpin),
        pick_optional(_header_es_valor_inicial),
        pick_optional(_header_es_adicion),
        pick_optional(_header_es_reduccion),
        pick_optional(_header_es_valor_final_mga),
        pick_optional(_header_es_nombre_proyecto),
    )
    if any(c is not None for c in mga_cols):
        extra.append(
            "Se detectaron columnas MGA/BPIN (valor inicial, final, adiciones, deducciones y/o código BPIN nacional). "
            "Se vincularán al proyecto MGA de cada meta al confirmar la importación."
        )

    return (
        ExcelColumnMap(
            idx_sector=idx_sec,
            idx_sector_codigo=idx_sec_cod,
            idx_secretaria=pick_secretaria(),
            idx_descripcion=pick_descripcion(),
            idx_valor_2026=pick_valor_2026(),
            idx_codigo_bpin=mga_cols[0],
            idx_valor_inicial=mga_cols[1],
            idx_adicion=mga_cols[2],
            idx_reduccion=mga_cols[3],
            idx_valor_final=mga_cols[4],
            idx_nombre_proyecto=mga_cols[5],
        ),
        extra,
    )


def _normalize_name(name: Any) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return str(name).strip()


def _cell_float(row: pd.Series, idx: int | None) -> float:
    if idx is None or len(row) <= idx:
        return 0.0
    v = row.iloc[idx]
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _sync_proyecto_mga_for_meta(db: Session, meta: Meta, f: dict) -> None:
    """
    Crea o actualiza un ProyectoMga por meta a partir de filas del Excel (BPIN, valores MGA).
    """
    bpin = (f.get("codigo_bpin") or "").strip()[:50]
    nombre_proy = (f.get("nombre_proyecto") or "").strip()[:500]
    vi = float(f.get("valor_inicial") or 0)
    ad = float(f.get("adicion") or 0)
    red = float(f.get("reduccion") or 0)
    has = bool(bpin) or vi != 0 or ad != 0 or red != 0 or bool(nombre_proy)
    if not has:
        return
    p = db.query(ProyectoMga).filter(ProyectoMga.meta_id == meta.id).first()
    default_nombre = nombre_proy or (
        f"BPIN {bpin}" if bpin else ((meta.descripcion or "")[:200] or "Proyecto MGA")
    )
    if p:
        if bpin:
            p.codigo_bpin = bpin
        p.valor_inicial = Decimal(str(vi))
        p.adicion = Decimal(str(ad))
        p.reduccion = Decimal(str(red))
        recalcular_valor_final(p)
        if nombre_proy:
            p.nombre = nombre_proy
        elif not (p.nombre or "").strip():
            p.nombre = default_nombre
    else:
        np = ProyectoMga(
            meta_id=meta.id,
            codigo_bpin=bpin or None,
            nombre=default_nombre,
            valor_inicial=Decimal(str(vi)),
            adicion=Decimal(str(ad)),
            reduccion=Decimal(str(red)),
            valor_final=Decimal(0),
        )
        db.add(np)
        db.flush()
        recalcular_valor_final(np)
    db.flush()


def _indicador_por_sector_key(db: Session) -> dict[str, int]:
    """
    Nombre de sector (normalizado) -> primer indicador_producto ligado a ese sector
    (producto -> programa -> sector).
    """
    out: dict[str, int] = {}
    for s in db.query(Sector).order_by(Sector.id):
        k = normalize_secretaria_key(s.nombre)
        ck = normalize_secretaria_key(s.codigo) if s.codigo else ""
        ind = (
            db.query(IndicadorProducto)
            .join(Producto, IndicadorProducto.producto_id == Producto.id)
            .join(Programa, Producto.programa_id == Programa.id)
            .filter(Programa.sector_id == s.id)
            .order_by(IndicadorProducto.id)
            .first()
        )
        if not ind:
            continue
        if k and k not in out:
            out[k] = ind.id
        if ck and ck not in out:
            out[ck] = ind.id
    return out


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


def _secretarias_por_clave_normalizada(db: Session) -> dict[str, int]:
    """Mapa clave normalizada -> id (si hay duplicados en BD con distinto casing, se usa el id menor)."""
    by_key: dict[str, int] = {}
    for s in db.query(Secretaria).order_by(Secretaria.id):
        k = normalize_secretaria_key(s.nombre)
        if not k:
            continue
        if k not in by_key:
            by_key[k] = s.id
    return by_key


def _secretaria_by_name(db: Session, name: str) -> int | None:
    if not name:
        return None
    k = normalize_secretaria_key(name)
    if not k:
        return None
    m = _secretarias_por_clave_normalizada(db)
    return m.get(k)


def parse_excel(content: bytes) -> tuple[list[dict], list[dict], list[str]]:
    """
    Parsea el Excel y devuelve (preview_rows, filas_para_importar, warnings).
    """
    df = pd.read_excel(io.BytesIO(content), header=0, engine="openpyxl")
    if df.empty or len(df.columns) < 4:
        return [], [], ["El archivo tiene pocas columnas. Se esperan al menos: Oficina (col 2), Meta/Descripción (col 4)."]

    cmap, col_warnings = _detect_excel_columns(df)
    preview = []
    filas = []
    warnings = list(col_warnings)

    def _cell(row: pd.Series, idx: int | None) -> str:
        if idx is None or len(row) <= idx:
            return ""
        return _normalize_name(row.iloc[idx])

    for idx, row in df.iterrows():
        sector = _cell(row, cmap.idx_sector)
        sector_codigo = _cell(row, cmap.idx_sector_codigo)
        oficina = _cell(row, cmap.idx_secretaria)
        desc = _cell(row, cmap.idx_descripcion)
        valor_2026 = 0
        if cmap.idx_valor_2026 is not None and len(row) > cmap.idx_valor_2026:
            try:
                v = row.iloc[cmap.idx_valor_2026]
                if v is not None and not (isinstance(v, float) and pd.isna(v)):
                    valor_2026 = float(v)
            except (TypeError, ValueError):
                pass

        codigo_bpin = _cell(row, cmap.idx_codigo_bpin)
        nombre_proyecto = _cell(row, cmap.idx_nombre_proyecto)
        valor_inicial = _cell_float(row, cmap.idx_valor_inicial)
        adicion = _cell_float(row, cmap.idx_adicion)
        reduccion = _cell_float(row, cmap.idx_reduccion)
        valor_final = _cell_float(row, cmap.idx_valor_final)

        if not desc:
            continue
        oficina_key = normalize_secretaria_key(oficina)
        sector_key = normalize_secretaria_key(sector)
        sector_codigo_key = normalize_secretaria_key(sector_codigo)
        filas.append(
            {
                "sector": sector,
                "sector_key": sector_key,
                "sector_codigo": sector_codigo,
                "sector_codigo_key": sector_codigo_key,
                "oficina": oficina,
                "oficina_key": oficina_key,
                "descripcion": desc[:2000],
                "valor_esperado_2026": valor_2026,
                "codigo_bpin": codigo_bpin[:50] if codigo_bpin else "",
                "nombre_proyecto": nombre_proyecto[:500] if nombre_proyecto else "",
                "valor_inicial": valor_inicial,
                "adicion": adicion,
                "reduccion": reduccion,
                "valor_final": valor_final,
            }
        )
        if len(preview) < MAX_PREVIEW_ROWS:
            sec_label = normalize_secretaria_title_for_display(oficina) if oficina else "(Sin oficina)"
            nombre_sec = (
                normalize_secretaria_title_for_display(sector) if sector else "(Sin nombre)"
            )
            cod_sec = sector_codigo if sector_codigo else "—"
            preview.append(
                {
                    "Código sector": cod_sec,
                    "Nombre sector": nombre_sec,
                    "Secretaría": sec_label,
                    "Meta": desc[:80] + ("..." if len(desc) > 80 else ""),
                    "Valor 2026": valor_2026,
                    "BPIN": codigo_bpin or "—",
                    "V. inicial": valor_inicial,
                    "Adición": adicion,
                    "Deducción": reduccion,
                    "V. final": valor_final,
                }
            )

    if not filas:
        warnings.append("No se encontraron filas con descripción de meta.")
    elif any(
        not normalize_secretaria_key(f.get("sector") or "")
        and not normalize_secretaria_key(f.get("sector_codigo") or "")
        for f in filas
    ):
        warnings.append(
            "Hay filas sin código ni nombre de sector (columnas F y G). "
            "En esas filas se usará el indicador genérico al confirmar la importación."
        )
    return preview, filas, warnings


def run_import(db: Session, filas: list[dict], linea_id: int | None = None) -> tuple[int, int, int]:
    """
    Inserta o actualiza metas. Retorna (inserted, updated, errors).
    """
    inserted = 0
    updated = 0
    errors = 0
    indicador_fallback = _get_or_create_indicador(db)
    indicadores_por_sector = _indicador_por_sector_key(db)
    lineas = db.query(LineaEstrategica).all()
    linea_id = linea_id or (lineas[0].id if lineas else None)
    secretarias_map = _secretarias_por_clave_normalizada(db)
    # Recomputar clave en import por si el job guardó filas con criterio antiguo (debe coincidir con BD)
    for f in filas:
        try:
            oficina = (f.get("oficina") or "").strip()
            key = normalize_secretaria_key(oficina)
            desc = (f.get("descripcion") or "").strip()
            if not desc:
                errors += 1
                continue
            if not key:
                errors += 1
                continue
            sec_id = secretarias_map.get(key)
            if not sec_id:
                # No usar "primera secretaría por id": antes min(id) mandaba casi todo a una sola (p. ej. id=1).
                errors += 1
                continue

            sector_txt = (f.get("sector") or "").strip()
            codigo_txt = (f.get("sector_codigo") or "").strip()
            sk = normalize_secretaria_key(sector_txt)
            sk_cod = normalize_secretaria_key(codigo_txt)
            indicador_id = None
            if sk:
                indicador_id = indicadores_por_sector.get(sk)
            if not indicador_id and sk_cod:
                indicador_id = indicadores_por_sector.get(sk_cod)
            if sk or sk_cod:
                if not indicador_id:
                    errors += 1
                    continue
            else:
                indicador_id = indicador_fallback.id

            valor_2026 = float(f.get("valor_esperado_2026") or 0)
            existing = db.query(Meta).filter(
                Meta.secretaria_id == sec_id,
                Meta.descripcion == desc[:500],
            ).first()
            if existing:
                existing.valor_esperado_2026 = Decimal(str(valor_2026))
                existing.meta_cuatrienio = Decimal(str(valor_2026 * 4))
                existing.indicador_producto_id = indicador_id
                db.flush()
                _sync_proyecto_mga_for_meta(db, existing, f)
                updated += 1
            else:
                meta = Meta(
                    descripcion=desc,
                    linea_estrategica_id=linea_id,
                    secretaria_id=sec_id,
                    indicador_producto_id=indicador_id,
                    meta_cuatrienio=Decimal(str(valor_2026 * 4)),
                    valor_esperado_2026=Decimal(str(valor_2026)),
                    activo=True,
                )
                db.add(meta)
                db.flush()
                _sync_proyecto_mga_for_meta(db, meta, f)
                inserted += 1
        except Exception:
            errors += 1
    db.commit()
    return inserted, updated, errors


def unique_sectors_from_filas(filas: list[dict]) -> list[tuple[str, str]]:
    """
    Pares (codigo, nombre) únicos a partir de las filas del Excel.
    codigo y nombre recortados; nombre por defecto si falta.
    """
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for f in filas:
        cod = (f.get("sector_codigo") or "").strip()
        nom = (f.get("sector") or "").strip()
        if not cod and not nom:
            continue
        key = normalize_secretaria_key(cod) if cod else normalize_secretaria_key(nom)
        if not key or key in seen:
            continue
        seen.add(key)
        if not nom:
            nom = cod or "Sin nombre"
        if len(nom) > 255:
            nom = nom[:255]
        if len(cod) > 50:
            cod = cod[:50]
        out.append((cod, nom))
    return out


def replace_sectors_catalog(db: Session, filas: list[dict]) -> dict[str, int | str]:
    """
    Elimina sectores y toda la cadena indicador→meta (y MGA vinculada), luego crea
    sectores desde las filas del Excel con un programa/producto/indicador mínimo cada uno.
    """
    pairs = unique_sectors_from_filas(filas)
    if not pairs:
        return {"creados": 0, "mensaje": "No hay códigos ni nombres de sector en el archivo."}

    # Orden de borrado por FKs
    db.query(SeguimientoMeta).delete(synchronize_session=False)
    db.query(ActividadMga).delete(synchronize_session=False)
    db.query(PresupuestoFuente).delete(synchronize_session=False)
    db.query(ProyectoMga).delete(synchronize_session=False)
    db.query(Meta).delete(synchronize_session=False)
    db.query(IndicadorProducto).delete(synchronize_session=False)
    db.query(Producto).delete(synchronize_session=False)
    db.query(Programa).delete(synchronize_session=False)
    db.query(Sector).delete(synchronize_session=False)
    db.flush()

    created = 0
    for i, (cod, nom) in enumerate(pairs):
        sec = Sector(codigo=cod or None, nombre=nom)
        db.add(sec)
        db.flush()
        sid = sec.id
        prog = Programa(
            codigo=f"P{sid}"[:50],
            nombre=f"Programa {nom[:80]}",
            sector_id=sid,
        )
        db.add(prog)
        db.flush()
        prod = Producto(
            codigo=f"PR{sid}"[:50],
            nombre=f"Producto {nom[:80]}",
            programa_id=prog.id,
        )
        db.add(prod)
        db.flush()
        ind = IndicadorProducto(
            codigo=f"I{sid}"[:50],
            nombre=f"Indicador {nom[:80]}",
            producto_id=prod.id,
        )
        db.add(ind)
        created += 1
    db.commit()
    return {
        "creados": created,
        "mensaje": f"Se crearon {created} sectores con su cadena programa/producto/indicador.",
    }
