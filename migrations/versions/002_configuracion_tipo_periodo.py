"""Tabla configuracion (tipo de período). Solo añade; no toca datos existentes.

Revision ID: 002
Revises: 001
Create Date: 2026-08-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "configuracion",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("clave", sa.String(64), nullable=False),
        sa.Column("valor", sa.String(64), nullable=False),
    )
    op.create_index("ix_configuracion_clave", "configuracion", ["clave"], unique=True)
    op.execute(
        sa.text(
            "INSERT INTO configuracion (clave, valor) VALUES ('tipo_periodo', 'cuatrimestre')"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_configuracion_clave", table_name="configuracion")
    op.drop_table("configuracion")
