"""
Seed de datos iniciales para Plan de Acción 2026.
Ejecutar: python seed.py (desde la carpeta backend, con venv activo y DB corriendo)
"""
import os
import sys
from datetime import date
from pathlib import Path

# Cargar .env del backend para usar SQLite (o la DB configurada)
_backend_dir = Path(__file__).resolve().parent
_env = _backend_dir / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env, override=True)

sys.path.insert(0, str(_backend_dir))

from app.db.session import SessionLocal, engine
from app.models import (
    PlanDesarrollo,
    LineaEstrategica,
    Secretaria,
    TipoSecretaria,
    Usuario,
    RolUsuario,
    Sector,
    Programa,
    Producto,
    IndicadorProducto,
    Meta,
    PeriodoSeguimiento,
    EstadoPeriodo,
)
from app.core.security import get_password_hash
from sqlalchemy import text

# Crear tablas si no existen (usar migraciones en producción)
# from app.db.session import Base
# Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    try:
        # Plan desarrollo
        plan = db.query(PlanDesarrollo).first()
        if not plan:
            plan = PlanDesarrollo(nombre="Plan de Acción 2026", periodo="2024-2027")
            db.add(plan)
            db.commit()
            db.refresh(plan)
        print("Plan de desarrollo OK")

        # Línea estratégica ejemplo
        linea = db.query(LineaEstrategica).first()
        if not linea:
            linea = LineaEstrategica(nombre="Línea estratégica principal", plan_desarrollo_id=plan.id)
            db.add(linea)
            db.commit()
            db.refresh(linea)
        print("Línea estratégica OK")

        # Secretarías
        secretarias_data = [
            "Secretaría de Desarrollo Social",
            "Secretaría de Gobierno",
            "EMAO",
            "Oficina de Planeación e Infraestructura",
            "Secretaría Administrativa y Financiera",
            "Oficina de Talento Humano",
            "Oficina de Estadística",
            "TIC'S",
            "Desarrollo Económico",
            "Oficina de Tránsito",
        ]
        secretarias = {}
        for nombre in secretarias_data:
            existing = db.query(Secretaria).filter(Secretaria.nombre == nombre).first()
            if not existing:
                s = Secretaria(nombre=nombre, tipo=TipoSecretaria.secretaria)
                db.add(s)
                db.flush()
                secretarias[nombre] = s.id
            else:
                secretarias[nombre] = existing.id
        db.commit()
        print("Secretarías OK")

        # Usuarios de prueba
        users_data = [
            ("admin@chinchina.gov.co", "admin123", "Juan Admin", RolUsuario.admin, None),
            ("desarrollo.social@chinchina.gov.co", "sec123", "María Desarrollo Social", RolUsuario.secretaria, "Secretaría de Desarrollo Social"),
            ("gobierno@chinchina.gov.co", "sec123", "Pedro Gobierno", RolUsuario.secretaria, "Secretaría de Gobierno"),
            ("emao@chinchina.gov.co", "sec123", "Ana EMAO", RolUsuario.secretaria, "EMAO"),
        ]
        for email, password, nombre, rol, sec_name in users_data:
            if db.query(Usuario).filter(Usuario.email == email).first():
                continue
            sec_id = secretarias.get(sec_name) if sec_name else None
            u = Usuario(
                nombre=nombre,
                email=email,
                password_hash=get_password_hash(password),
                rol=rol,
                secretaria_id=sec_id,
                activo=True,
                requiere_cambio_password=False,
            )
            db.add(u)
        db.commit()
        print("Usuarios OK")

        # Período activo: T1 2026 abierto
        periodo = db.query(PeriodoSeguimiento).filter(
            PeriodoSeguimiento.anio == 2026,
            PeriodoSeguimiento.trimestre == 1,
        ).first()
        if not periodo:
            periodo = PeriodoSeguimiento(
                anio=2026,
                trimestre=1,
                estado=EstadoPeriodo.abierto,
                fecha_limite=date(2026, 3, 31),
            )
            db.add(periodo)
            db.commit()
        print("Período T1 2026 OK")

        # Sectores, programas, productos e indicadores (para que haya metas con estructura)
        sector = db.query(Sector).first()
        if not sector:
            sector = Sector(codigo="EDU", nombre="Educación")
            db.add(sector)
            db.flush()
            sector2 = Sector(codigo="SAL", nombre="Salud")
            db.add(sector2)
            db.flush()
            sector3 = Sector(codigo="GOB", nombre="Gobierno")
            db.add(sector3)
            db.flush()
        db.commit()
        sectores = {s.nombre: s.id for s in db.query(Sector).all()}

        programa = db.query(Programa).first()
        if not programa:
            for nom, cod, sec_nom in [("Programa Educación", "P001", "Educación"), ("Programa Salud", "P002", "Salud"), ("Programa Gobierno", "P003", "Gobierno")]:
                sid = sectores.get(sec_nom)
                if sid:
                    p = Programa(codigo=cod, nombre=nom, sector_id=sid)
                    db.add(p)
            db.commit()
        programas = list(db.query(Programa).limit(3).all())

        producto = db.query(Producto).first()
        if not producto and programas:
            for i, p in enumerate(programas):
                prod = Producto(codigo=f"PR{i+1}", nombre=f"Producto {p.nombre[:20]}", programa_id=p.id)
                db.add(prod)
            db.commit()
        productos = list(db.query(Producto).limit(5).all())

        indicador = db.query(IndicadorProducto).first()
        if not indicador and productos:
            for i, prod in enumerate(productos[:5]):
                ind = IndicadorProducto(codigo=f"33010{i+1}00", nombre=f"Indicador producto {prod.nombre[:15]}", producto_id=prod.id)
                db.add(ind)
            db.commit()
        indicadores = list(db.query(IndicadorProducto).limit(10).all())

        # Metas de ejemplo (repartidas en secretarías)
        if db.query(Meta).count() == 0 and indicadores and secretarias:
            secretaria_ids = list(secretarias.values())
            lineas = db.query(LineaEstrategica).all()
            linea_id = lineas[0].id if lineas else None
            descripciones = [
                "Fortalecer la entrega de kits escolares al 100% de estudiantes focalizados.",
                "Garantizar la cobertura en salud para la población vulnerable.",
                "Implementar estrategias de convivencia ciudadana.",
                "Gestionar el talento humano y bienestar laboral.",
                "Actualizar el plan de ordenamiento territorial.",
                "Fortalecer la gestión administrativa y financiera.",
                "Producir y divulgar estadísticas oficiales.",
                "Implementar soluciones TIC en la administración.",
                "Apoyar el emprendimiento y desarrollo económico.",
                "Mejorar la movilidad y seguridad vial.",
                "Ampliar cobertura de educación inicial.",
                "Reducir la deserción escolar.",
                "Promover la participación ciudadana.",
                "Modernizar la infraestructura institucional.",
                "Fomentar la cultura y el deporte.",
            ]
            for i, desc in enumerate(descripciones):
                sec_id = secretaria_ids[i % len(secretaria_ids)]
                ind = indicadores[i % len(indicadores)]
                valor = (i + 1) * 1000
                m = Meta(
                    descripcion=desc,
                    linea_estrategica_id=linea_id,
                    secretaria_id=sec_id,
                    indicador_producto_id=ind.id,
                    meta_cuatrienio=valor * 4,
                    valor_esperado_2026=valor,
                    activo=True,
                )
                db.add(m)
            db.commit()
            print("Metas de ejemplo OK")

        print("\nSeed completado. Usuarios:")
        print("  admin@chinchina.gov.co / admin123 (admin)")
        print("  desarrollo.social@chinchina.gov.co / sec123 (secretaría)")
        print("  gobierno@chinchina.gov.co / sec123 (secretaría)")
        print("  emao@chinchina.gov.co / sec123 (secretaría)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
