from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class LineaEstrategica(Base):
    __tablename__ = "linea_estrategica"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    plan_desarrollo_id = Column(Integer, ForeignKey("plan_desarrollo.id"), nullable=True)
    plan_desarrollo = relationship("PlanDesarrollo", backref="lineas_estrategicas")
