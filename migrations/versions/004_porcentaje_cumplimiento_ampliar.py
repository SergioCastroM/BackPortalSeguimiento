"""Amplía porcentaje_cumplimiento para no fallar con sobrecumplimientos altos.

Revision ID: 004
Revises: 003
Create Date: 2026-11-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "seguimiento_meta",
        "porcentaje_cumplimiento",
        existing_type=sa.Numeric(5, 2),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "seguimiento_meta",
        "porcentaje_cumplimiento",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(5, 2),
        existing_nullable=True,
    )
