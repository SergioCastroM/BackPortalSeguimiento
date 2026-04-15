from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class IndicadorProducto(Base):
    __tablename__ = "indicador_producto"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=True, index=True)
    nombre = Column(String(500), nullable=True)
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=True)
    producto = relationship("Producto", back_populates="indicadores")
    metas = relationship("Meta", back_populates="indicador_producto")
