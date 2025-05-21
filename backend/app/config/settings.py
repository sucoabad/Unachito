import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, AnyUrl, ConfigDict

# Carga variables de entorno desde archivo .env (raíz del backend)
dotenv_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '.env')
)
load_dotenv(dotenv_path, override=True)

class Settings(BaseSettings):
    model_config = ConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    # Bases de datos
    DATABASE_URL: AnyUrl = Field(..., env="DATABASE_URL")
    DATABASE_URL_ESTUDIANTES: AnyUrl = Field(..., env="DATABASE_URL_ESTUDIANTES")
    DATABASE_URL_DOCENTES: AnyUrl = Field(..., env="DATABASE_URL_DOCENTES")

    # SMTP
    SMTP_HOST: str = Field(..., env="SMTP_HOST")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USER: str = Field(..., env="SMTP_USER")
    SMTP_PASSWORD: str = Field(..., env="SMTP_PASSWORD")

    # 🔐 Config LDAP para Zoom
    LDAP_ZOOM_HOST: str = Field(..., env="LDAP_ZOOM_HOST")
    LDAP_ZOOM_PORT: int = Field(389, env="LDAP_ZOOM_PORT")
    LDAP_ZOOM_USER: str = Field(..., env="LDAP_ZOOM_USER")
    LDAP_ZOOM_PASSWORD: str = Field(..., env="LDAP_ZOOM_PASSWORD")
    LDAP_ZOOM_BASE_DN: str = Field(..., env="LDAP_ZOOM_BASE_DN")

    # Umbrales
    THRESHOLD_FAQ: float = Field(0.65, env="THRESHOLD_FAQ")
    THRESHOLD_SCRAPING: float = Field(0.50, env="THRESHOLD_SCRAPING")

    # CORS
    CORS_ORIGINS: list[str] = Field(["https://tu-dominio.com"], env="CORS_ORIGINS")

    # 🔧 NUEVO: Control de scraping
    ENABLE_SCRAPING: bool = Field(True, env="ENABLE_SCRAPING")

# Singleton de configuración
#env_settings: Settings | None = None
env_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global env_settings
    if env_settings is None:
        env_settings = Settings()
        print(f"[DEBUG] ENABLE_SCRAPING cargado como: {env_settings.ENABLE_SCRAPING} (tipo: {type(env_settings.ENABLE_SCRAPING)})")
    return env_settings


