from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.session import Base


class ProyectoMga(Base):
    __tablename__ = "proyecto_mga"

    id = Column(Integer, primary_key=True, index=True)
    codigo_bpin = Column(String(50), nullable=True)
    nombre = Column(String(500), nullable=True)
    valor_inicial = Column(Numeric(20, 4), default=0, nullable=True)
    adicion = Column(Numeric(20, 4), default=0, nullable=True)
    reduccion = Column(Numeric(20, 4), default=0, nullable=True)
    valor_final = Column(Numeric(20, 4), default=0, nullable=True)
    meta_id = Column(Integer, ForeignKey("meta.id"), nullable=False)
    meta = relationship("Meta", back_populates="proyectos_mga")
    actividades = relationship("ActividadMga", back_populates="proyecto_mga", cascade="all, delete-orphan")
    presupuestos_fuente = relationship("PresupuestoFuente", back_populates="proyecto_mga", cascade="all, delete-orphan")
