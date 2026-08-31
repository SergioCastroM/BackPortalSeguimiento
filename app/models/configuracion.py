from sqlalchemy import Column, Integer, String
from app.db.session import Base


class Configuracion(Base):
    """Clave/valor de sistema. No guarda datos de metas ni seguimientos."""

    __tablename__ = "configuracion"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(64), unique=True, nullable=False, index=True)
    valor = Column(String(64), nullable=False)
