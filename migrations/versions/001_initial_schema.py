"""Initial schema - all tables

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plan_desarrollo",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("periodo", sa.String(50), nullable=True),
    )
    op.create_table(
        "linea_estrategica",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("plan_desarrollo_id", sa.Integer(), sa.ForeignKey("plan_desarrollo.id"), nullable=True),
    )
    op.create_table(
        "secretaria",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
    )
    op.create_table(
        "sector",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(50), nullable=True),
        sa.Column("nombre", sa.String(255), nullable=False),
    )
    op.create_table(
        "programa",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(50), nullable=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sector.id"), nullable=True),
    )
    op.create_table(
        "producto",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(50), nullable=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("programa_id", sa.Integer(), sa.ForeignKey("programa.id"), nullable=True),
    )
    op.create_table(
        "indicador_producto",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(50), nullable=True),
        sa.Column("nombre", sa.String(500), nullable=True),
        sa.Column("producto_id", sa.Integer(), sa.ForeignKey("producto.id"), nullable=True),
    )
    op.create_index("ix_indicador_producto_codigo", "indicador_producto", ["codigo"], unique=False)
    op.create_table(
        "fuente_financiacion",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(20), nullable=True),
        sa.Column("nombre", sa.String(255), nullable=True),
    )
    op.create_index("ix_fuente_financiacion_codigo", "fuente_financiacion", ["codigo"], unique=False)
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("cargo", sa.String(255), nullable=True),
        sa.Column("secretaria_id", sa.Integer(), sa.ForeignKey("secretaria.id"), nullable=True),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("requiere_cambio_password", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_usuario_email", "usuario", ["email"], unique=True)
    op.create_index("idx_usuario_secretaria", "usuario", ["secretaria_id"], unique=False)
    op.create_table(
        "meta",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("descripcion", sa.String(2000), nullable=False),
        sa.Column("linea_estrategica_id", sa.Integer(), sa.ForeignKey("linea_estrategica.id"), nullable=True),
        sa.Column("secretaria_id", sa.Integer(), sa.ForeignKey("secretaria.id"), nullable=False),
        sa.Column("indicador_producto_id", sa.Integer(), sa.ForeignKey("indicador_producto.id"), nullable=True),
        sa.Column("meta_cuatrienio", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("valor_esperado_2024", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("valor_esperado_2025", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("valor_esperado_2026", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("valor_esperado_2027", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("idx_meta_secretaria", "meta", ["secretaria_id"], unique=False)
    op.create_index("idx_meta_linea", "meta", ["linea_estrategica_id"], unique=False)
    op.create_table(
        "proyecto_mga",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo_bpin", sa.String(50), nullable=True),
        sa.Column("nombre", sa.String(500), nullable=True),
        sa.Column("valor_inicial", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("adicion", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("reduccion", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("valor_final", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("meta_id", sa.Integer(), sa.ForeignKey("meta.id"), nullable=False),
    )
    op.create_table(
        "actividad_mga",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(500), nullable=True),
        sa.Column("valor_inicial", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("valor_final", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("proyecto_mga_id", sa.Integer(), sa.ForeignKey("proyecto_mga.id"), nullable=False),
    )
    op.create_table(
        "presupuesto_fuente",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("proyecto_mga_id", sa.Integer(), sa.ForeignKey("proyecto_mga.id"), nullable=False),
        sa.Column("fuente_id", sa.Integer(), sa.ForeignKey("fuente_financiacion.id"), nullable=False),
        sa.Column("valor", sa.Numeric(20, 4), nullable=True, server_default="0"),
    )
    op.create_table(
        "periodos_seguimiento",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_limite", sa.Date(), nullable=True),
    )
    op.create_table(
        "seguimiento_meta",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("meta_id", sa.Integer(), sa.ForeignKey("meta.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("valor_ejecutado", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("recursos_ejecutados", sa.Numeric(20, 4), nullable=True, server_default="0"),
        sa.Column("evidencia", sa.Text(), nullable=True),
        sa.Column("porcentaje_cumplimiento", sa.Numeric(5, 2), nullable=True, server_default="0"),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("meta_id", "trimestre", "anio", name="uq_seguimiento_meta_trimestre_anio"),
    )
    op.create_index("idx_seguimiento_meta", "seguimiento_meta", ["meta_id"], unique=False)
    op.create_index("idx_seguimiento_anio", "seguimiento_meta", ["anio", "trimestre"], unique=False)
    op.create_table(
        "import_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("inserted", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("updated", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("import_log")
    op.drop_index("idx_seguimiento_anio", table_name="seguimiento_meta")
    op.drop_index("idx_seguimiento_meta", table_name="seguimiento_meta")
    op.drop_table("seguimiento_meta")
    op.drop_table("periodos_seguimiento")
    op.drop_table("presupuesto_fuente")
    op.drop_table("actividad_mga")
    op.drop_table("proyecto_mga")
    op.drop_index("idx_meta_linea", table_name="meta")
    op.drop_index("idx_meta_secretaria", table_name="meta")
    op.drop_table("meta")
    op.drop_index("idx_usuario_secretaria", table_name="usuario")
    op.drop_index("ix_usuario_email", table_name="usuario")
    op.drop_table("usuario")
    op.drop_index("ix_fuente_financiacion_codigo", table_name="fuente_financiacion")
    op.drop_table("fuente_financiacion")
    op.drop_index("ix_indicador_producto_codigo", table_name="indicador_producto")
    op.drop_table("indicador_producto")
    op.drop_table("producto")
    op.drop_table("programa")
    op.drop_table("sector")
    op.drop_table("secretaria")
    op.drop_table("linea_estrategica")
    op.drop_table("plan_desarrollo")
