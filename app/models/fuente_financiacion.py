from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.session import Base


class FuenteFinanciacion(Base):
    __tablename__ = "fuente_financiacion"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=True, index=True)
    nombre = Column(String(255), nullable=True)
    presupuestos = relationship("PresupuestoFuente", back_populates="fuente")
