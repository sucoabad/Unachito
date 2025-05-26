from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, AnyUrl, SecretStr

class Settings(BaseSettings):
    # ------------------------ ENV_FILE CONFIG ------------------------
    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

    # ------------------------ TOKENS API ------------------------
    UNACH_TOKEN_SERVIDOR: SecretStr = Field(..., env="UNACH_TOKEN_SERVIDOR")
    UNACH_TOKEN_ESTUDIANTE: SecretStr = Field(..., env="UNACH_TOKEN_ESTUDIANTE")

    # ------------------------ URL API ------------------------
    UNACH_API_SERVIDOR: str = Field(..., env="UNACH_API_SERVIDOR")
    UNACH_API_ESTUDIANTE: str = Field(..., env="UNACH_API_ESTUDIANTE")

    # ------------------------ Base de datos ------------------------
    DATABASE_URL: AnyUrl = Field(..., env="DATABASE_URL")
    DATABASE_URL_ESTUDIANTES: AnyUrl = Field(..., env="DATABASE_URL_ESTUDIANTES")
    DATABASE_URL_SERVIDORES: AnyUrl = Field(..., env="DATABASE_URL_SERVIDORES")

    # ------------------------ SMTP ------------------------
    SMTP_HOST: str = Field(..., env="SMTP_HOST")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USER: str = Field(..., env="SMTP_USER")
    SMTP_PASSWORD: SecretStr = Field(..., env="SMTP_PASSWORD")

    # ------------------------ LDAP ZOOM ------------------------
    LDAP_ZOOM_HOST: str = Field(..., env="LDAP_ZOOM_HOST")
    LDAP_ZOOM_PORT: int = Field(389, env="LDAP_ZOOM_PORT")
    LDAP_ZOOM_USER: str = Field(..., env="LDAP_ZOOM_USER")
    LDAP_ZOOM_PASSWORD: SecretStr = Field(..., env="LDAP_ZOOM_PASSWORD")
    LDAP_ZOOM_BASE_DN: str = Field(..., env="LDAP_ZOOM_BASE_DN")

    # ------------------------ Umbrales y flags ------------------------
    THRESHOLD_FAQ: float = Field(0.65, env="THRESHOLD_FAQ")
    THRESHOLD_SCRAPING: float = Field(0.50, env="THRESHOLD_SCRAPING")
    ENABLE_SCRAPING: bool = Field(True, env="ENABLE_SCRAPING")

    # ------------------------ CORS ------------------------
    CORS_ORIGINS: List[str] = Field(default_factory=list, env="CORS_ORIGINS")


# ------------------------ SINGLETON Y FUNCIÓN DE ACCESO ------------------------
env_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Devuelve la instancia singleton de Settings.
    """
    global env_settings
    if env_settings is None:
        env_settings = Settings()
    return env_settings