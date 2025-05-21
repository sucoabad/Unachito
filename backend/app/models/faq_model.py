from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FAQ(Base):
    __tablename__ = 'faq'

    id = Column(Integer, primary_key=True, index=True)
    pregunta = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    categoria = Column(String(50))
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_update = Column(DateTime, onupdate=func.now())
