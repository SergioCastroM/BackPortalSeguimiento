"""Columna meta.obligado (mínimo de cumplimiento en pesos). Solo añade; no toca datos existentes.

Revision ID: 003
Revises: 002
Create Date: 2026-11-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columnas = {c["name"] for c in sa.inspect(bind).get_columns("meta")}
    if "obligado" not in columnas:
        op.add_column("meta", sa.Column("obligado", sa.Numeric(20, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("meta", "obligado")
