from app.db.session import Base
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin con created_at/updated_at si se necesita en el futuro."""
