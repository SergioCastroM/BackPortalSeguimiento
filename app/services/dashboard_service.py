from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import (
    Meta,
    SeguimientoMeta,
    Secretaria,
    Sector,
    Programa,
    Producto,
    IndicadorProducto,
    Usuario,
)


def dashboard_global(db: Session, anio: int, trimestre: int) -> dict:
    total_metas = db.query(Meta).filter(Meta.activo == True).count()
    sub = (
        db.query(SeguimientoMeta.meta_id)
        .filter(SeguimientoMeta.anio == anio, SeguimientoMeta.trimestre == trimestre)
        .distinct()
        .subquery()
    )
    con_seg = db.query(Meta.id).filter(Meta.id.in_(db.query(sub))).count()
    pendientes = max(0, total_metas - con_seg)
    prom = (
        db.query(func.coalesce(func.avg(SeguimientoMeta.porcentaje_cumplimiento), 0))
        .filter(SeguimientoMeta.anio == anio, SeguimientoMeta.trimestre == trimestre)
        .scalar()
    )
    porcentaje_prom = float(prom or 0)

    por_secretaria = []
    for s in db.query(Secretaria).all():
        metas_s = db.query(Meta).filter(Meta.secretaria_id == s.id, Meta.activo == True).count()
        if metas_s == 0:
            por_secretaria.append({"secretaria_id": s.id, "secretaria_nombre": s.nombre, "porcentaje": 0, "total_metas": 0})
            continue
        prom_s = (
            db.query(func.avg(SeguimientoMeta.porcentaje_cumplimiento))
            .join(Meta)
            .filter(
                Meta.secretaria_id == s.id,
                SeguimientoMeta.anio == anio,
                SeguimientoMeta.trimestre == trimestre,
            )
            .scalar()
        )
        por_secretaria.append({
            "secretaria_id": s.id,
            "secretaria_nombre": s.nombre,
            "porcentaje": float(prom_s or 0),
            "total_metas": metas_s,
        })

    sectores = db.query(Sector).all()
    total_s = sum(
        db.query(Meta).join(IndicadorProducto).join(Producto).join(Programa).filter(Programa.sector_id == sec.id, Meta.activo == True).count()
        for sec in sectores
    )
    por_sector = []
    for sec in sectores:
        cnt = db.query(Meta).join(IndicadorProducto).join(Producto).join(Programa).filter(Programa.sector_id == sec.id, Meta.activo == True).count()
        pct = (cnt / total_s * 100) if total_s else 0
        por_sector.append({"sector_id": sec.id, "sector_nombre": sec.nombre, "cantidad": cnt, "porcentaje": round(pct, 1)})

    evolucion = []
    for s in db.query(Secretaria).all()[:5]:
        for t in [1, 2, 3, 4]:
            prom_t = (
                db.query(func.avg(SeguimientoMeta.porcentaje_cumplimiento))
                .join(Meta)
                .filter(Meta.secretaria_id == s.id, SeguimientoMeta.anio == anio, SeguimientoMeta.trimestre == t)
                .scalar()
            )
            evolucion.append({
                "trimestre": t,
                "anio": anio,
                "secretaria_id": s.id,
                "secretaria_nombre": s.nombre,
                "porcentaje": float(prom_t or 0),
            })

    heatmap = []
    for s in db.query(Secretaria).all():
        for t in [1, 2, 3, 4]:
            prom_t = (
                db.query(func.avg(SeguimientoMeta.porcentaje_cumplimiento))
                .join(Meta)
                .filter(Meta.secretaria_id == s.id, SeguimientoMeta.anio == anio, SeguimientoMeta.trimestre == t)
                .scalar()
            )
            heatmap.append({
                "secretaria_id": s.id,
                "secretaria_nombre": s.nombre,
                "trimestre": t,
                "anio": anio,
                "porcentaje": float(prom_t) if prom_t is not None else None,
            })

    return {
        "kpis": {
            "total_metas": total_metas,
            "con_seguimiento": con_seg,
            "pendientes": pendientes,
            "porcentaje_cumplimiento_prom": round(porcentaje_prom, 1),
        },
        "por_secretaria": por_secretaria,
        "por_sector": por_sector[:6],
        "evolucion": evolucion,
        "heatmap": heatmap,
    }


def dashboard_secretaria(db: Session, secretaria_id: int, anio: int, trimestre: int) -> dict:
    metas = db.query(Meta).filter(Meta.secretaria_id == secretaria_id, Meta.activo == True).all()
    total_metas = len(metas)
    registradas = 0
    suma_pct = Decimal("0")
    metas_ev = []
    for m in metas:
        seg = db.query(SeguimientoMeta).filter(
            SeguimientoMeta.meta_id == m.id,
            SeguimientoMeta.anio == anio,
            SeguimientoMeta.trimestre == trimestre,
        ).first()
        if seg:
            registradas += 1
            suma_pct += seg.porcentaje_cumplimiento or 0
        valor_esp = m.valor_esperado_2026 or 0
        valor_ej = float(seg.valor_ejecutado or 0) if seg else 0
        metas_ev.append({
            "meta_id": m.id,
            "meta_descripcion": (m.descripcion or "")[:80],
            "esperado": valor_esp,
            "ejecutado": valor_ej,
        })
    pendientes = total_metas - registradas
    porcentaje_cumplimiento = (suma_pct / registradas) if registradas else Decimal("0")

    evolucion = []
    for t in [1, 2, 3, 4]:
        prom = (
            db.query(func.avg(SeguimientoMeta.porcentaje_cumplimiento))
            .join(Meta)
            .filter(Meta.secretaria_id == secretaria_id, SeguimientoMeta.anio == anio, SeguimientoMeta.trimestre == t)
            .scalar()
        )
        evolucion.append({"trimestre": t, "anio": anio, "porcentaje": float(prom or 0)})

    metas_list = []
    for m in metas:
        segs = db.query(SeguimientoMeta).filter(SeguimientoMeta.meta_id == m.id).all()
        meta_dict = {
            "id": m.id,
            "descripcion": m.descripcion,
            "valor_esperado_2026": float(m.valor_esperado_2026 or 0),
            "indicador_producto": None,
            "seguimientos": [
                {"trimestre": s.trimestre, "anio": s.anio, "porcentaje_cumplimiento": float(s.porcentaje_cumplimiento or 0)}
                for s in segs
            ],
        }
        if m.indicador_producto:
            meta_dict["indicador_producto"] = {
                "codigo": m.indicador_producto.codigo,
                "nombre": m.indicador_producto.nombre,
                "producto": None,
            }
            if m.indicador_producto.producto and m.indicador_producto.producto.programa and m.indicador_producto.producto.programa.sector:
                meta_dict["indicador_producto"]["producto"] = {
                    "programa": {"sector": {"nombre": m.indicador_producto.producto.programa.sector.nombre}},
                }
        metas_list.append(meta_dict)

    return {
        "secretaria": {"id": secretaria_id, "nombre": db.query(Secretaria).get(secretaria_id).nombre},
        "kpis": {
            "total_metas": total_metas,
            "registradas": registradas,
            "pendientes": pendientes,
            "porcentaje_cumplimiento": round(float(porcentaje_cumplimiento), 1),
        },
        "metas_esperado_vs_ejecutado": metas_ev,
        "evolucion": evolucion,
        "metas": metas_list,
    }
