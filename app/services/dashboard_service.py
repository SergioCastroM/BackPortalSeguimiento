from decimal import Decimal
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_

from app.models import (
    Meta,
    SeguimientoMeta,
    Secretaria,
    Sector,
    Programa,
    Producto,
    IndicadorProducto,
)


def dashboard_global(db: Session, anio: int, trimestre: int) -> dict:
    """
    KPIs y gráficos en pocas consultas agregadas (evita N+1 por secretaría/trimestre).
    """
    total_metas = db.query(func.count(Meta.id)).filter(Meta.activo == True).scalar() or 0

    con_seg = (
        db.query(func.count(func.distinct(SeguimientoMeta.meta_id)))
        .filter(
            SeguimientoMeta.anio == anio,
            SeguimientoMeta.trimestre == trimestre,
        )
        .scalar()
    ) or 0

    pendientes = max(0, int(total_metas) - int(con_seg))

    prom = (
        db.query(func.coalesce(func.avg(SeguimientoMeta.porcentaje_cumplimiento), 0))
        .filter(SeguimientoMeta.anio == anio, SeguimientoMeta.trimestre == trimestre)
        .scalar()
    )
    porcentaje_prom = float(prom or 0)

    # Una consulta por secretaría: total metas activas + promedio % en el trimestre seleccionado
    sec_rows = (
        db.query(
            Secretaria.id,
            Secretaria.nombre,
            func.count(Meta.id),
            func.avg(SeguimientoMeta.porcentaje_cumplimiento),
        )
        .outerjoin(Meta, and_(Meta.secretaria_id == Secretaria.id, Meta.activo == True))
        .outerjoin(
            SeguimientoMeta,
            and_(
                SeguimientoMeta.meta_id == Meta.id,
                SeguimientoMeta.anio == anio,
                SeguimientoMeta.trimestre == trimestre,
            ),
        )
        .group_by(Secretaria.id, Secretaria.nombre)
        .order_by(Secretaria.id)
        .all()
    )
    por_secretaria = [
        {
            "secretaria_id": r[0],
            "secretaria_nombre": r[1],
            "porcentaje": float(r[3] or 0) if r[2] else 0.0,
            "total_metas": int(r[2] or 0),
        }
        for r in sec_rows
    ]

    sector_count_rows = (
        db.query(Programa.sector_id, func.count(Meta.id))
        .select_from(Meta)
        .join(IndicadorProducto, Meta.indicador_producto_id == IndicadorProducto.id)
        .join(Producto, IndicadorProducto.producto_id == Producto.id)
        .join(Programa, Producto.programa_id == Programa.id)
        .filter(Meta.activo == True, Programa.sector_id.isnot(None))
        .group_by(Programa.sector_id)
        .all()
    )
    count_by_sector = {int(sid): int(c) for sid, c in sector_count_rows if sid is not None}
    total_s = sum(count_by_sector.values())

    sectores = db.query(Sector).order_by(Sector.id).all()
    por_sector = []
    for sec in sectores:
        cnt = count_by_sector.get(sec.id, 0)
        pct = (cnt / total_s * 100) if total_s else 0.0
        por_sector.append(
            {"sector_id": sec.id, "sector_nombre": sec.nombre, "cantidad": cnt, "porcentaje": round(pct, 1)}
        )

    # Evolución: mismas 5 primeras secretarías (por id) × T1–T4
    top5 = db.query(Secretaria).order_by(Secretaria.id).limit(5).all()
    ids5 = [s.id for s in top5]
    evolucion: list[dict] = []
    if ids5:
        ev_agg = (
            db.query(
                Secretaria.id,
                Secretaria.nombre,
                SeguimientoMeta.trimestre,
                func.avg(SeguimientoMeta.porcentaje_cumplimiento),
            )
            .join(Meta, and_(Meta.secretaria_id == Secretaria.id, Meta.activo == True))
            .join(
                SeguimientoMeta,
                and_(
                    SeguimientoMeta.meta_id == Meta.id,
                    SeguimientoMeta.anio == anio,
                ),
            )
            .filter(Secretaria.id.in_(ids5))
            .group_by(Secretaria.id, Secretaria.nombre, SeguimientoMeta.trimestre)
            .all()
        )
        ev_map = {(r[0], r[2]): float(r[3] or 0) for r in ev_agg}
        for s in top5:
            for t in (1, 2, 3, 4):
                evolucion.append(
                    {
                        "trimestre": t,
                        "anio": anio,
                        "secretaria_id": s.id,
                        "secretaria_nombre": s.nombre,
                        "porcentaje": ev_map.get((s.id, t), 0.0),
                    }
                )

    # Heatmap: todas las secretarías × 4 trimestres (una consulta agregada + relleno)
    all_sec = db.query(Secretaria).order_by(Secretaria.id).all()
    hm_agg = (
        db.query(
            Secretaria.id,
            Secretaria.nombre,
            SeguimientoMeta.trimestre,
            func.avg(SeguimientoMeta.porcentaje_cumplimiento),
        )
        .join(Meta, and_(Meta.secretaria_id == Secretaria.id, Meta.activo == True))
        .join(
            SeguimientoMeta,
            and_(SeguimientoMeta.meta_id == Meta.id, SeguimientoMeta.anio == anio),
        )
        .group_by(Secretaria.id, Secretaria.nombre, SeguimientoMeta.trimestre)
        .all()
    )
    hm_map: dict[tuple[int, int], float | None] = {}
    for r in hm_agg:
        v = r[3]
        hm_map[(r[0], r[2])] = float(v) if v is not None else None

    heatmap = []
    for s in all_sec:
        for t in (1, 2, 3, 4):
            prom_t = hm_map.get((s.id, t))
            heatmap.append(
                {
                    "secretaria_id": s.id,
                    "secretaria_nombre": s.nombre,
                    "trimestre": t,
                    "anio": anio,
                    "porcentaje": prom_t,
                }
            )

    return {
        "kpis": {
            "total_metas": int(total_metas),
            "con_seguimiento": int(con_seg),
            "pendientes": pendientes,
            "porcentaje_cumplimiento_prom": round(porcentaje_prom, 1),
        },
        "por_secretaria": por_secretaria,
        "por_sector": por_sector[:6],
        "evolucion": evolucion,
        "heatmap": heatmap,
    }


def dashboard_secretaria(db: Session, secretaria_id: int, anio: int, trimestre: int) -> dict:
    metas = (
        db.query(Meta)
        .filter(Meta.secretaria_id == secretaria_id, Meta.activo == True)
        .options(
            selectinload(Meta.seguimientos),
            selectinload(Meta.indicador_producto)
            .selectinload(IndicadorProducto.producto)
            .selectinload(Producto.programa)
            .selectinload(Programa.sector),
        )
        .all()
    )
    total_metas = len(metas)
    registradas = 0
    suma_pct = Decimal("0")
    metas_ev = []

    for m in metas:
        seg = next(
            (s for s in m.seguimientos if s.anio == anio and s.trimestre == trimestre),
            None,
        )
        if seg:
            registradas += 1
            suma_pct += seg.porcentaje_cumplimiento or 0
        valor_esp = m.valor_esperado_2026 or 0
        valor_ej = float(seg.valor_ejecutado or 0) if seg else 0
        metas_ev.append(
            {
                "meta_id": m.id,
                "meta_descripcion": (m.descripcion or "")[:80],
                "esperado": float(valor_esp) if valor_esp is not None else 0,
                "ejecutado": valor_ej,
            }
        )

    pendientes = total_metas - registradas
    porcentaje_cumplimiento = (suma_pct / registradas) if registradas else Decimal("0")

    ev_rows = (
        db.query(SeguimientoMeta.trimestre, func.avg(SeguimientoMeta.porcentaje_cumplimiento))
        .join(Meta, SeguimientoMeta.meta_id == Meta.id)
        .filter(
            Meta.secretaria_id == secretaria_id,
            SeguimientoMeta.anio == anio,
            SeguimientoMeta.trimestre.in_((1, 2, 3, 4)),
        )
        .group_by(SeguimientoMeta.trimestre)
        .all()
    )
    ev_map = {int(t): float(p or 0) for t, p in ev_rows}
    evolucion = [{"trimestre": t, "anio": anio, "porcentaje": ev_map.get(t, 0.0)} for t in (1, 2, 3, 4)]

    metas_list = []
    for m in metas:
        segs = m.seguimientos
        meta_dict = {
            "id": m.id,
            "descripcion": m.descripcion,
            "valor_esperado_2026": float(m.valor_esperado_2026 or 0),
            "indicador_producto": None,
            "seguimientos": [
                {
                    "trimestre": s.trimestre,
                    "anio": s.anio,
                    "porcentaje_cumplimiento": float(s.porcentaje_cumplimiento or 0),
                }
                for s in segs
            ],
        }
        if m.indicador_producto:
            meta_dict["indicador_producto"] = {
                "codigo": m.indicador_producto.codigo,
                "nombre": m.indicador_producto.nombre,
                "producto": None,
            }
            ip = m.indicador_producto
            if ip.producto and ip.producto.programa and ip.producto.programa.sector:
                meta_dict["indicador_producto"]["producto"] = {
                    "programa": {"sector": {"nombre": ip.producto.programa.sector.nombre}},
                }
        metas_list.append(meta_dict)

    sec = db.get(Secretaria, secretaria_id)
    sec_nombre = sec.nombre if sec else ""

    return {
        "secretaria": {"id": secretaria_id, "nombre": sec_nombre},
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
