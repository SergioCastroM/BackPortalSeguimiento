from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Producto(Base):
    __tablename__ = "producto"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=True)
    nombre = Column(String(255), nullable=False)
    programa_id = Column(Integer, ForeignKey("programa.id"), nullable=True)
    programa = relationship("Programa", back_populates="productos")
    indicadores = relationship("IndicadorProducto", back_populates="producto")
