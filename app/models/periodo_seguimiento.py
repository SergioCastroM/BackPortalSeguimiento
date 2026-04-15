import enum
from sqlalchemy import Column, Integer, DateTime, Enum, Date
from app.db.session import Base


class EstadoPeriodo(str, enum.Enum):
    abierto = "abierto"
    cerrado = "cerrado"
    proximo = "proximo"


class PeriodoSeguimiento(Base):
    __tablename__ = "periodos_seguimiento"

    id = Column(Integer, primary_key=True, index=True)
    anio = Column(Integer, nullable=False)
    trimestre = Column(Integer, nullable=False)  # 1-4
    estado = Column(Enum(EstadoPeriodo), default=EstadoPeriodo.proximo, nullable=False)
    fecha_limite = Column(Date, nullable=True)
