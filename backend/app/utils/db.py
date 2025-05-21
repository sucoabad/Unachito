# app/utils/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.settings import get_settings

settings = get_settings()

# -----------------------------------
# Motor y sesión principal (FAQ/OTP)
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -----------------------------------
# Sesión para RADIUS Estudiantes (MySQL)
engine_est = create_engine(
    str(settings.DATABASE_URL_ESTUDIANTES),
    pool_pre_ping=True,
    connect_args={"charset": "utf8"}            # <— fuerza utf8
)
SessionLocalEstudiantes = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_est
)

# -----------------------------------
# Sesión para RADIUS Docentes (MySQL)
engine_doc = create_engine(
    str(settings.DATABASE_URL_DOCENTES),
    pool_pre_ping=True,
    connect_args={"charset": "utf8"}            # <— fuerza utf8
)
SessionLocalDocentes = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_doc
)
