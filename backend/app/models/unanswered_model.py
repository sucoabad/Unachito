from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Unanswered(Base):
    __tablename__ = 'unanswered'

    id = Column(Integer, primary_key=True, index=True)
    pregunta = Column(Text, nullable=False)
    fecha = Column(DateTime, default=func.now())
    usuario_ip = Column(String(50))
    origen = Column(String(100))
    url_origen = Column(Text)
    estado = Column(String(20), default='pendiente')
