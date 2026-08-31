"""Tipo de período (trimestre / cuatrimestre). No modifica ni borra seguimientos existentes."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

TIPO_TRIMESTRE = "trimestre"
TIPO_CUATRIMESTRE = "cuatrimestre"
TIPOS_VALIDOS = (TIPO_TRIMESTRE, TIPO_CUATRIMESTRE)
CLAVE_TIPO_PERIODO = "tipo_periodo"
TIPO_DEFAULT = TIPO_CUATRIMESTRE

_FECHAS = {
    TIPO_TRIMESTRE: {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)},
    TIPO_CUATRIMESTRE: {1: (4, 30), 2: (8, 31), 3: (12, 31)},
}


def normalizar_tipo(valor: str | None) -> str:
    v = (valor or "").strip().lower()
    return v if v in TIPOS_VALIDOS else TIPO_DEFAULT


def cantidad_periodos(tipo: str) -> int:
    return 4 if normalizar_tipo(tipo) == TIPO_TRIMESTRE else 3


def numeros_periodo(tipo: str) -> list[int]:
    return list(range(1, cantidad_periodos(tipo) + 1))


def prefijo_periodo(tipo: str) -> str:
    return "T" if normalizar_tipo(tipo) == TIPO_TRIMESTRE else "C"


def etiqueta_periodo(tipo: str, numero: int) -> str:
    return f"{prefijo_periodo(tipo)}{numero}"


def nombre_periodo(tipo: str, plural: bool = False) -> str:
    if normalizar_tipo(tipo) == TIPO_TRIMESTRE:
        return "Trimestres" if plural else "Trimestre"
    return "Cuatrimestres" if plural else "Cuatrimestre"


def fechas_limite_tipo(tipo: str) -> dict[int, tuple[int, int]]:
    return dict(_FECHAS[normalizar_tipo(tipo)])


def fecha_limite_default(tipo: str, anio: int, numero: int) -> date | None:
    fechas = fechas_limite_tipo(tipo)
    if numero not in fechas:
        return None
    mes, dia = fechas[numero]
    return date(anio, mes, dia)


def es_periodo_visible(tipo: str, numero: int) -> bool:
    return 1 <= int(numero) <= cantidad_periodos(tipo)


def descripcion_config(tipo: str) -> dict[str, Any]:
    t = normalizar_tipo(tipo)
    nums = numeros_periodo(t)
    return {
        "tipo": t,
        "cantidad": cantidad_periodos(t),
        "numeros": nums,
        "prefijo": prefijo_periodo(t),
        "nombre": nombre_periodo(t, plural=False),
        "nombre_plural": nombre_periodo(t, plural=True),
        "etiquetas": {n: etiqueta_periodo(t, n) for n in nums},
    }


def _ensure_tabla(db: Session) -> None:
    """Crea solo la tabla configuracion si no existe. No toca el resto del esquema."""
    from sqlalchemy import inspect
    from sqlalchemy.exc import ProgrammingError
    from app.models.configuracion import Configuracion

    bind = db.get_bind()
    try:
        if inspect(bind).has_table("configuracion"):
            return
        Configuracion.__table__.create(bind=bind, checkfirst=True)
    except ProgrammingError:
        db.rollback()
        # En Azure SQL, checkfirst a veces no ve la tabla y el CREATE choca. Seguir con SELECT.


def get_tipo_periodo(db: Session) -> str:
    from app.models.configuracion import Configuracion

    _ensure_tabla(db)
    row = db.query(Configuracion).filter(Configuracion.clave == CLAVE_TIPO_PERIODO).first()
    if not row:
        row = Configuracion(clave=CLAVE_TIPO_PERIODO, valor=TIPO_DEFAULT)
        db.add(row)
        db.commit()
        db.refresh(row)
    return normalizar_tipo(row.valor)


def set_tipo_periodo(db: Session, tipo: str) -> str:
    from app.models.configuracion import Configuracion

    _ensure_tabla(db)
    tipo = normalizar_tipo(tipo)
    row = db.query(Configuracion).filter(Configuracion.clave == CLAVE_TIPO_PERIODO).first()
    if not row:
        row = Configuracion(clave=CLAVE_TIPO_PERIODO, valor=tipo)
        db.add(row)
    else:
        row.valor = tipo
    db.commit()
    db.refresh(row)
    return normalizar_tipo(row.valor)


def get_periodo_config(db: Session) -> dict[str, Any]:
    return descripcion_config(get_tipo_periodo(db))
