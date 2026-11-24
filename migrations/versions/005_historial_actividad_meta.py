"""Crea tabla historial_actividad_meta y realiza backfill de seguimientos existentes.

Revision ID: 005
Revises: 004
Create Date: 2026-11-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "historial_actividad_meta",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("meta_id", sa.Integer(), sa.ForeignKey("meta.id"), nullable=False),
        sa.Column("seguimiento_id", sa.Integer(), sa.ForeignKey("seguimiento_meta.id"), nullable=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("tipo_evento", sa.String(40), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=True),
        sa.Column("anio", sa.Integer(), nullable=True),
        sa.Column("valor_anterior", sa.Numeric(20, 4), nullable=True),
        sa.Column("valor_nuevo", sa.Numeric(20, 4), nullable=True),
        sa.Column("monto_movimiento", sa.Numeric(20, 4), nullable=True),
        sa.Column("porcentaje_cumplimiento", sa.Numeric(12, 2), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("observaciones_anterior", sa.Text(), nullable=True),
        sa.Column("evidencia", sa.Text(), nullable=True),
        sa.Column("evidencia_anterior", sa.Text(), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("idx_historial_meta_id", "historial_actividad_meta", ["meta_id"], unique=False)
    op.create_index("idx_historial_usuario_id", "historial_actividad_meta", ["usuario_id"], unique=False)
    op.create_index("idx_historial_fecha", "historial_actividad_meta", ["fecha_registro"], unique=False)

    # Poblar el histórico inicial con los seguimientos ya registrados hasta la fecha
    op.execute(
        sa.text(
            """
            INSERT INTO historial_actividad_meta (
                meta_id,
                seguimiento_id,
                usuario_id,
                tipo_evento,
                trimestre,
                anio,
                valor_nuevo,
                porcentaje_cumplimiento,
                observaciones,
                evidencia,
                fecha_registro
            )
            SELECT
                meta_id,
                id,
                usuario_id,
                'seguimiento_creado',
                trimestre,
                anio,
                COALESCE(recursos_ejecutados, valor_ejecutado, 0),
                porcentaje_cumplimiento,
                observaciones,
                evidencia,
                fecha_registro
            FROM seguimiento_meta
            """
        )
    )


def downgrade() -> None:
    op.drop_index("idx_historial_fecha", table_name="historial_actividad_meta")
    op.drop_index("idx_historial_usuario_id", table_name="historial_actividad_meta")
    op.drop_index("idx_historial_meta_id", table_name="historial_actividad_meta")
    op.drop_table("historial_actividad_meta")
