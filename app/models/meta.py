from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship
from app.db.session import Base


class Meta(Base):
    __tablename__ = "meta"
    __table_args__ = (
        Index("idx_meta_secretaria", "secretaria_id"),
        Index("idx_meta_linea", "linea_estrategica_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(2000), nullable=False)
    linea_estrategica_id = Column(Integer, ForeignKey("linea_estrategica.id"), nullable=True)
    secretaria_id = Column(Integer, ForeignKey("secretaria.id"), nullable=False)
    indicador_producto_id = Column(Integer, ForeignKey("indicador_producto.id"), nullable=True)
    meta_cuatrienio = Column(Numeric(20, 4), default=0, nullable=True)
    valor_esperado_2024 = Column(Numeric(20, 4), default=0, nullable=True)
    valor_esperado_2025 = Column(Numeric(20, 4), default=0, nullable=True)
    valor_esperado_2026 = Column(Numeric(20, 4), default=0, nullable=True)
    valor_esperado_2027 = Column(Numeric(20, 4), default=0, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)

    linea_estrategica = relationship("LineaEstrategica", backref="metas")
    secretaria = relationship("Secretaria", back_populates="metas")
    indicador_producto = relationship("IndicadorProducto", back_populates="metas")
    proyectos_mga = relationship("ProyectoMga", back_populates="meta", cascade="all, delete-orphan")
    seguimientos = relationship("SeguimientoMeta", back_populates="meta", cascade="all, delete-orphan")
