from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Programa(Base):
    __tablename__ = "programa"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=True)
    nombre = Column(String(255), nullable=False)
    sector_id = Column(Integer, ForeignKey("sector.id"), nullable=True)
    sector = relationship("Sector", back_populates="programas")
    productos = relationship("Producto", back_populates="programa")
