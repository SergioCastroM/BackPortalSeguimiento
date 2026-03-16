from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.session import Base


class Sector(Base):
    __tablename__ = "sector"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=True)
    nombre = Column(String(255), nullable=False)
    programas = relationship("Programa", back_populates="sector")
