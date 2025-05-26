import logging
from typing import Optional, Literal, Dict, Any
import requests
from requests.adapters import HTTPAdapter, Retry
from app.config.settings import get_settings

logger = logging.getLogger("uvicorn.error")
settings = get_settings()

UserType = Literal["servidor", "estudiante"]

class UnachApi:
    """
    Cliente HTTP para las APIs de UNACH (servidores y estudiantes).
    Base URLs y tokens cargados desde las Settings.
    """
    def __init__(
        self,
        verify_ssl: bool = False,
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.timeout = timeout
        # URLs base (sin slash final)
        self.servidor_base_url = settings.UNACH_API_SERVIDOR.rstrip("/")
        self.estudiante_base_url = settings.UNACH_API_ESTUDIANTE.rstrip("/")

        # Tokens de autorización
        tokens: Dict[UserType, str] = {
            "servidor": settings.UNACH_TOKEN_SERVIDOR.get_secret_value(),
            "estudiante": settings.UNACH_TOKEN_ESTUDIANTE.get_secret_value(),
        }

        # Estrategia de reintentos
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        # Creamos una sesión por tipo de usuario
        self.sessions: Dict[UserType, requests.Session] = {}
        for ut, token in tokens.items():
            s = requests.Session()
            s.verify = verify_ssl
            s.headers.update({"Authorization": f"Bearer {token}"})
            s.mount("https://", adapter)
            s.mount("http://", adapter)
            self.sessions[ut] = s

    def _get(self, session: requests.Session, url: str) -> Optional[Any]:
        try:
            r = session.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("Error GET %s: %s", url, e)
        return None

    def _post(self, session: requests.Session, url: str, json_body: Any) -> Optional[Any]:
        try:
            r = session.post(url, json=json_body, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("Error POST %s %s: %s", url, json_body, e)
        return None

    def get_por_cedula(
        self,
        cedula: str,
        user_type: UserType
    ) -> Optional[dict]:
        """
        Devuelve datos crudos de servidor o estudiante según user_type.
        - Servidor: GET /api/Servidores/Buscar/{cedula}
        - Estudiante: POST /api/Estudiante/InformacionBasicaPorCI  body=["cedula"]
        """
        if user_type not in self.sessions:
            logger.error("Tipo de usuario inválido: %s", user_type)
            return None

        session = self.sessions[user_type]

        if user_type == "servidor":
            url = f"{self.servidor_base_url}/api/Servidores/Buscar/{cedula}"
            data = self._get(session, url)
        else:
            url = f"{self.estudiante_base_url}/api/Estudiante/InformacionBasicaPorCI"
            # aquí va un POST con un array de cédula
            data = self._post(session, url, [cedula])

        if not data:
            return None

        # Puede venir lista o dict en ambos casos
        if isinstance(data, list):
            return data[0] if data else None
        if isinstance(data, dict):
            return data

        return None

    def get_correo_por_cedula(
        self,
        cedula: str,
        user_type: UserType
    ) -> Optional[str]:
        """
        Extrae correo principal o temporal del usuario.
        """
        usuario = self.get_por_cedula(cedula, user_type)
        if not usuario:
            logger.info("%s no encontrado: %s", user_type, cedula)
            return None
        for key in ("correoElectronico", "correoElectronicoTmp", "correoInstitucional"):
            c = usuario.get(key)
            if isinstance(c, str) and c.strip():
                return c.strip()
        logger.info("%s %s sin correo disponible", user_type, cedula)
        return None

    def get_nombre_por_cedula(
        self,
        cedula: str,
        user_type: UserType
    ) -> Optional[str]:
        """
        Construye nombre completo (nombres + primer apellido).
        Para estudiantes también intenta 'nombresCompletos'.
        """
        usuario = self.get_por_cedula(cedula, user_type)
        if not usuario:
            return None

        nombres = (
            usuario.get("nombresCompletos")
            or usuario.get("nombres")
            or usuario.get("nombre")
            or ""
        )
        apellido = (
            usuario.get("apellidoPaterno")
            or usuario.get("apellidoMaterno")
            or usuario.get("apellido")
            or ""
        )

        full = f"{nombres} {apellido}".strip()
        return full or None
