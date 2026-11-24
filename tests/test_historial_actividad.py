"""Tests de bitácora de actividad de secretarios (seguimientos y presupuesto MGA)."""
import os
import unittest
from decimal import Decimal

os.environ.setdefault(
    "DATABASE_URL",
    "mssql+pyodbc://u:p@localhost:1433/db?driver=ODBC+Driver+17+for+SQL+Server",
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import (
    IndicadorProducto,
    Meta,
    PeriodoSeguimiento,
    EstadoPeriodo,
    ProyectoMga,
    RolUsuario,
    Secretaria,
    SeguimientoMeta,
    TipoSecretaria,
    Usuario,
)
from app.models.historial_actividad_meta import HistorialActividadMeta
from app.services.historial_service import (
    TIPO_ADICION_PRESUPUESTO,
    TIPO_REDUCCION_PRESUPUESTO,
    TIPO_SEGUIMIENTO_ACTUALIZADO,
    TIPO_SEGUIMIENTO_CREADO,
    listar_historial_admin,
    listar_historial_meta,
    registrar_evento_movimiento_presupuesto,
    registrar_evento_seguimiento_actualizado,
    registrar_evento_seguimiento_creado,
)


class HistorialServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        SessionTesting = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionTesting()

        self.sec_salud = Secretaria(nombre="Secretaría de Salud", tipo=TipoSecretaria.secretaria)
        self.sec_educ = Secretaria(nombre="Secretaría de Educación", tipo=TipoSecretaria.secretaria)
        self.db.add_all([self.sec_salud, self.sec_educ])
        self.db.flush()

        self.user_salud = Usuario(
            nombre="Ana Gómez",
            email="ana@salud.gov.co",
            password_hash="x",
            cargo="Secretaria de Salud",
            secretaria_id=self.sec_salud.id,
            rol=RolUsuario.secretaria,
            activo=True,
        )
        self.user_educ = Usuario(
            nombre="Carlos Ruiz",
            email="carlos@educ.gov.co",
            password_hash="x",
            cargo="Secretario de Educación",
            secretaria_id=self.sec_educ.id,
            rol=RolUsuario.secretaria,
            activo=True,
        )
        self.db.add_all([self.user_salud, self.user_educ])
        self.db.flush()

        self.ind = IndicadorProducto(codigo="IND-101", nombre="Cobertura vacunación")
        self.db.add(self.ind)
        self.db.flush()

        self.meta_salud = Meta(
            descripcion="Vacunar población infantil rural",
            secretaria_id=self.sec_salud.id,
            indicador_producto_id=self.ind.id,
            valor_esperado_2026=Decimal("1000"),
            activo=True,
        )
        self.meta_educ = Meta(
            descripcion="Dotación de aulas escolares",
            secretaria_id=self.sec_educ.id,
            valor_esperado_2026=Decimal("50"),
            activo=True,
        )
        self.db.add_all([self.meta_salud, self.meta_educ])
        self.db.flush()

        self.pm_salud = ProyectoMga(
            meta_id=self.meta_salud.id,
            codigo_bpin="20260001",
            nombre="Proyecto Salud Rural",
            valor_inicial=Decimal("100000000"),
            adicion=Decimal("0"),
            reduccion=Decimal("0"),
            valor_final=Decimal("100000000"),
        )
        self.db.add(self.pm_salud)
        self.db.add(
            PeriodoSeguimiento(anio=2026, trimestre=1, estado=EstadoPeriodo.abierto)
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_registra_creacion_edicion_y_movimientos_en_orden(self):
        seg = SeguimientoMeta(
            meta_id=self.meta_salud.id,
            usuario_id=self.user_salud.id,
            trimestre=1,
            anio=2026,
            valor_ejecutado=Decimal("25000000"),
            recursos_ejecutados=Decimal("25000000"),
            evidencia="CDP 1001",
            porcentaje_cumplimiento=Decimal("25.00"),
            observaciones="Primera jornada ejecutada",
        )
        self.db.add(seg)
        self.db.flush()
        registrar_evento_seguimiento_creado(self.db, seg, self.user_salud.id)
        self.db.commit()

        # Edición posterior del mismo período
        valor_prev = seg.recursos_ejecutados
        obs_prev = seg.observaciones
        ev_prev = seg.evidencia
        seg.valor_ejecutado = Decimal("40000000")
        seg.recursos_ejecutados = Decimal("40000000")
        seg.porcentaje_cumplimiento = Decimal("40.00")
        seg.observaciones = "Primera y segunda jornada ejecutadas"
        seg.evidencia = "CDP 1001, CDP 1002"
        registrar_evento_seguimiento_actualizado(
            self.db,
            seg,
            self.user_salud.id,
            valor_anterior=valor_prev,
            observaciones_anterior=obs_prev,
            evidencia_anterior=ev_prev,
        )
        self.db.commit()

        # Movimiento presupuestal de adición
        registrar_evento_movimiento_presupuesto(
            self.db,
            meta_id=self.meta_salud.id,
            usuario_id=self.user_salud.id,
            tipo="adicion",
            monto=Decimal("10000000"),
            valor_final_anterior=Decimal("100000000"),
            valor_final_nuevo=Decimal("110000000"),
        )
        self.db.commit()

        historial = listar_historial_meta(self.db, self.meta_salud.id)
        self.assertEqual(len(historial), 3)
        # Orden descendente por id / fecha_registro
        self.assertEqual(historial[0]["tipo_evento"], TIPO_ADICION_PRESUPUESTO)
        self.assertEqual(historial[0]["monto_movimiento"], 10000000.0)
        self.assertEqual(historial[0]["valor_anterior"], 100000000.0)
        self.assertEqual(historial[0]["valor_nuevo"], 110000000.0)
        self.assertEqual(historial[0]["usuario"]["nombre"], "Ana Gómez")

        self.assertEqual(historial[1]["tipo_evento"], TIPO_SEGUIMIENTO_ACTUALIZADO)
        self.assertEqual(historial[1]["valor_anterior"], 25000000.0)
        self.assertEqual(historial[1]["valor_nuevo"], 40000000.0)
        self.assertEqual(historial[1]["observaciones_anterior"], "Primera jornada ejecutada")
        self.assertEqual(historial[1]["evidencia_anterior"], "CDP 1001")

        self.assertEqual(historial[2]["tipo_evento"], TIPO_SEGUIMIENTO_CREADO)
        self.assertEqual(historial[2]["valor_nuevo"], 25000000.0)
        self.assertEqual(historial[2]["evidencia"], "CDP 1001")

    def test_filtros_bandeja_admin(self):
        seg_salud = SeguimientoMeta(
            meta_id=self.meta_salud.id,
            usuario_id=self.user_salud.id,
            trimestre=1,
            anio=2026,
            valor_ejecutado=Decimal("15000000"),
            recursos_ejecutados=Decimal("15000000"),
            evidencia="CDP-SALUD-99",
            porcentaje_cumplimiento=Decimal("15.00"),
            observaciones="Brigada rural",
        )
        seg_educ = SeguimientoMeta(
            meta_id=self.meta_educ.id,
            usuario_id=self.user_educ.id,
            trimestre=1,
            anio=2026,
            valor_ejecutado=Decimal("8000000"),
            recursos_ejecutados=Decimal("8000000"),
            evidencia="CDP-EDU-77",
            porcentaje_cumplimiento=Decimal("0"),
            observaciones="Compra pupitres",
        )
        self.db.add_all([seg_salud, seg_educ])
        self.db.flush()
        registrar_evento_seguimiento_creado(self.db, seg_salud, self.user_salud.id)
        registrar_evento_seguimiento_creado(self.db, seg_educ, self.user_educ.id)
        registrar_evento_movimiento_presupuesto(
            self.db,
            meta_id=self.meta_salud.id,
            usuario_id=self.user_salud.id,
            tipo="reduccion",
            monto=Decimal("5000000"),
            valor_final_anterior=Decimal("100000000"),
            valor_final_nuevo=Decimal("95000000"),
        )
        self.db.commit()

        todos = listar_historial_admin(self.db, page=1, size=25)
        self.assertEqual(todos["total"], 3)

        por_sec = listar_historial_admin(self.db, page=1, size=25, secretaria_id=self.sec_educ.id)
        self.assertEqual(por_sec["total"], 1)
        self.assertEqual(por_sec["items"][0]["secretaria"]["nombre"], "Secretaría de Educación")

        por_tipo = listar_historial_admin(self.db, page=1, size=25, tipo_evento=TIPO_REDUCCION_PRESUPUESTO)
        self.assertEqual(por_tipo["total"], 1)
        self.assertEqual(por_tipo["items"][0]["monto_movimiento"], 5000000.0)

        por_busqueda_cdp = listar_historial_admin(self.db, page=1, size=25, search="CDP-SALUD-99")
        self.assertEqual(por_busqueda_cdp["total"], 1)
        self.assertEqual(por_busqueda_cdp["items"][0]["meta"]["indicador_codigo"], "IND-101")

    def test_endpoints_registran_bitacora_y_enriquecen_usuario(self):
        from fastapi import HTTPException
        from app.api.v1.seguimiento import create_seguimiento, update_seguimiento
        from app.api.v1.metas import (
            get_meta,
            get_meta_historial,
            registrar_movimiento_presupuesto_mga,
        )
        from app.api.v1.admin import (
            delete_all_metas_y_seguimientos,
            list_admin_historial,
        )
        from app.schemas.seguimiento import SeguimientoCreate, SeguimientoUpdate
        from app.schemas.proyecto_mga import ProyectoMgaMovimientoCreate

        user_admin = Usuario(
            nombre="Admin General",
            email="admin@portal.gov.co",
            password_hash="x",
            rol=RolUsuario.admin,
            activo=True,
        )
        user_salud_2 = Usuario(
            nombre="Luis Pérez",
            email="luis@salud.gov.co",
            password_hash="x",
            cargo="Profesional Apoyo",
            secretaria_id=self.sec_salud.id,
            rol=RolUsuario.secretaria,
            activo=True,
        )
        self.db.add_all([user_admin, user_salud_2])
        self.db.commit()

        # 1. Crear seguimiento por POST
        seg = create_seguimiento(
            body=SeguimientoCreate(
                meta_id=self.meta_salud.id,
                trimestre=1,
                anio=2026,
                valor_ejecutado=Decimal("20000000"),
                recursos_ejecutados=Decimal("20000000"),
                evidencia="CDP 501",
                porcentaje_cumplimiento=Decimal("0"),
                observaciones="Avance inicial reportado",
            ),
            db=self.db,
            current_user=self.user_salud,
        )

        # 2. Actualizar seguimiento por PUT con otro usuario de la misma secretaría
        update_seguimiento(
            seguimiento_id=seg.id,
            body=SeguimientoUpdate(
                recursos_ejecutados=Decimal("35000000"),
                evidencia="CDP 501, CDP 502",
                observaciones="Avance ajustado con segundo CDP",
            ),
            db=self.db,
            current_user=user_salud_2,
        )

        # 3. Registrar adición presupuestal MGA
        registrar_movimiento_presupuesto_mga(
            meta_id=self.meta_salud.id,
            body=ProyectoMgaMovimientoCreate(tipo="adicion", monto=Decimal("25000000")),
            db=self.db,
            current_user=self.user_salud,
        )

        # 4. get_meta incluye usuario_nombre y usuario_email del último secretario que editó
        detalle = get_meta(meta_id=self.meta_salud.id, db=self.db, current_user=user_admin)
        self.assertEqual(len(detalle["seguimientos"]), 1)
        self.assertEqual(detalle["seguimientos"][0]["usuario_nombre"], "Luis Pérez")
        self.assertEqual(detalle["seguimientos"][0]["usuario_email"], "luis@salud.gov.co")

        # 5. get_meta_historial devuelve los 3 eventos en orden descendente
        hist_meta = get_meta_historial(
            meta_id=self.meta_salud.id, db=self.db, current_user=user_admin
        )
        self.assertEqual(len(hist_meta), 3)
        self.assertEqual(hist_meta[0]["tipo_evento"], TIPO_ADICION_PRESUPUESTO)
        self.assertEqual(hist_meta[0]["valor_anterior"], 100000000.0)
        self.assertEqual(hist_meta[0]["valor_nuevo"], 125000000.0)
        self.assertEqual(hist_meta[1]["tipo_evento"], TIPO_SEGUIMIENTO_ACTUALIZADO)
        self.assertEqual(hist_meta[1]["usuario"]["nombre"], "Luis Pérez")
        self.assertEqual(hist_meta[1]["valor_anterior"], 20000000.0)
        self.assertEqual(hist_meta[1]["valor_nuevo"], 35000000.0)
        self.assertEqual(hist_meta[2]["tipo_evento"], TIPO_SEGUIMIENTO_CREADO)
        self.assertEqual(hist_meta[2]["usuario"]["nombre"], "Ana Gómez")

        # Otra secretaría no puede ver el historial de esta meta
        with self.assertRaises(HTTPException) as ctx:
            get_meta_historial(
                meta_id=self.meta_salud.id, db=self.db, current_user=self.user_educ
            )
        self.assertEqual(ctx.exception.status_code, 404)

        # 6. Bandeja admin global
        bandeja = list_admin_historial(
            db=self.db,
            current_user=user_admin,
            page=1,
            size=25,
            secretaria_id=self.sec_salud.id,
            usuario_id=None,
            tipo_evento=None,
            trimestre=None,
            anio=None,
            search=None,
        )
        self.assertEqual(bandeja["total"], 3)

        # 7. Purga total limpia historial sin fallar por FK
        purge_res = delete_all_metas_y_seguimientos(db=self.db, current_user=user_admin)
        self.assertEqual(purge_res.eliminados_historial, 3)
        self.assertEqual(self.db.query(HistorialActividadMeta).count(), 0)


if __name__ == "__main__":
    unittest.main()
