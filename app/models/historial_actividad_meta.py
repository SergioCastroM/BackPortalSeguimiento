from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class HistorialActividadMeta(Base):
    """Bitácora de registros y modificaciones realizadas sobre seguimientos y presupuesto MGA."""

    __tablename__ = "historial_actividad_meta"
    __table_args__ = (
        Index("idx_historial_meta_id", "meta_id"),
        Index("idx_historial_usuario_id", "usuario_id"),
        Index("idx_historial_fecha", "fecha_registro"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meta_id = Column(Integer, ForeignKey("meta.id"), nullable=False)
    seguimiento_id = Column(Integer, ForeignKey("seguimiento_meta.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    tipo_evento = Column(String(40), nullable=False)
    trimestre = Column(Integer, nullable=True)
    anio = Column(Integer, nullable=True)
    valor_anterior = Column(Numeric(20, 4), nullable=True)
    valor_nuevo = Column(Numeric(20, 4), nullable=True)
    monto_movimiento = Column(Numeric(20, 4), nullable=True)
    porcentaje_cumplimiento = Column(Numeric(12, 2), nullable=True)
    observaciones = Column(Text, nullable=True)
    observaciones_anterior = Column(Text, nullable=True)
    evidencia = Column(Text, nullable=True)
    evidencia_anterior = Column(Text, nullable=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    meta = relationship("Meta", back_populates="historial_actividades")
    usuario = relationship("Usuario")
