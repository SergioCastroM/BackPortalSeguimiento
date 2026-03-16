from sqlalchemy import Column, Integer, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.session import Base


class PresupuestoFuente(Base):
    __tablename__ = "presupuesto_fuente"

    id = Column(Integer, primary_key=True, index=True)
    proyecto_mga_id = Column(Integer, ForeignKey("proyecto_mga.id"), nullable=False)
    fuente_id = Column(Integer, ForeignKey("fuente_financiacion.id"), nullable=False)
    valor = Column(Numeric(20, 4), default=0, nullable=True)
    proyecto_mga = relationship("ProyectoMga", back_populates="presupuestos_fuente")
    fuente = relationship("FuenteFinanciacion", back_populates="presupuestos")
