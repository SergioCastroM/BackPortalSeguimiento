from sqlalchemy import Column, Integer, ForeignKey, Numeric, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class SeguimientoMeta(Base):
    __tablename__ = "seguimiento_meta"
    __table_args__ = (
        UniqueConstraint("meta_id", "trimestre", "anio", name="uq_seguimiento_meta_trimestre_anio"),
        Index("idx_seguimiento_meta", "meta_id"),
        Index("idx_seguimiento_anio", "anio", "trimestre"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meta_id = Column(Integer, ForeignKey("meta.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    trimestre = Column(Integer, nullable=False)  # 1-4
    anio = Column(Integer, nullable=False)
    valor_ejecutado = Column(Numeric(20, 4), default=0, nullable=True)
    recursos_ejecutados = Column(Numeric(20, 4), default=0, nullable=True)
    evidencia = Column(Text, nullable=True)
    porcentaje_cumplimiento = Column(Numeric(5, 2), default=0, nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    meta = relationship("Meta", back_populates="seguimientos")
    usuario = relationship("Usuario", back_populates="seguimientos")
