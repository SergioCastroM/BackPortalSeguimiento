import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from app.db.session import Base


class RolUsuario(str, enum.Enum):
    admin = "admin"
    secretaria = "secretaria"


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (Index("idx_usuario_secretaria", "secretaria_id"),)

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    cargo = Column(String(255), nullable=True)
    secretaria_id = Column(Integer, ForeignKey("secretaria.id"), nullable=True)
    rol = Column(Enum(RolUsuario), default=RolUsuario.secretaria, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    requiere_cambio_password = Column(Boolean, default=False, nullable=False)

    secretaria = relationship("Secretaria", back_populates="usuarios")
    seguimientos = relationship("SeguimientoMeta", back_populates="usuario")
