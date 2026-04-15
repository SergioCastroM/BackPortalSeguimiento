from sqlalchemy import Column, Integer, String
from app.db.session import Base


class PlanDesarrollo(Base):
    __tablename__ = "plan_desarrollo"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    periodo = Column(String(50), nullable=True)
