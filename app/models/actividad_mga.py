from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.session import Base


class ActividadMga(Base):
    __tablename__ = "actividad_mga"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(500), nullable=True)
    valor_inicial = Column(Numeric(20, 4), default=0, nullable=True)
    valor_final = Column(Numeric(20, 4), default=0, nullable=True)
    proyecto_mga_id = Column(Integer, ForeignKey("proyecto_mga.id"), nullable=False)
    proyecto_mga = relationship("ProyectoMga", back_populates="actividades")
