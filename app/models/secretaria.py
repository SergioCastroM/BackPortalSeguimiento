import enum
from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from app.db.session import Base


class TipoSecretaria(str, enum.Enum):
    secretaria = "secretaria"
    oficina = "oficina"
    entidad = "entidad"


class Secretaria(Base):
    __tablename__ = "secretaria"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    tipo = Column(Enum(TipoSecretaria), default=TipoSecretaria.secretaria, nullable=False)
    usuarios = relationship("Usuario", back_populates="secretaria")
    metas = relationship("Meta", back_populates="secretaria")
