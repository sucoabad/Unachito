# unach_client.py
import requests
from requests.adapters import HTTPAdapter, Retry
from typing import Optional
import logging

logger = logging.getLogger("uvicorn.error")

# Coloca tu token aquí, al principio del módulo
MI_TOKEN = "xyz"

class UnachApi:
    def __init__(self,
                 base_url: str = "https://pruebas.unach.edu.ec:4432",
                 token: str = MI_TOKEN,
                 verify_ssl: bool = False):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Authorization": f"Bearer {token}"})

        # 🔁 Configurar reintentos automáticos (3 veces, solo en errores temporales)
        retries = Retry(
            total=3,
            backoff_factor=1,  # Espera 1s, luego 2s, luego 4s
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_usuario_por_cedula(self, cedula: str) -> Optional[dict]:
        url = f"{self.base_url}/api/Servidores/Buscar/{cedula}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data[0] if isinstance(data, list) and len(data) > 0 else None

        except requests.exceptions.ReadTimeout:
            logger.warning(f"⚠️ Timeout al consultar la API de UNACH para la cédula {cedula}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"❗ Error de conexión al consultar {url}")
            return None
        except requests.RequestException as e:
            logger.error(f"[ERROR] al consultar {url}: {e}")
            return None

    def get_correo_por_cedula(self, cedula: str) -> Optional[str]:
        usuario = self.get_usuario_por_cedula(cedula)
        if not usuario:
            logger.info(f"[INFO] No se encontró usuario para la cédula {cedula}.")
            return None

        correo = usuario.get("correoElectronico")
        if correo and correo.strip():
            return correo.strip()

        correo_tmp = usuario.get("correoElectronicoTmp")
        if correo_tmp and correo_tmp.strip():
            return correo_tmp.strip()

        logger.info(f"[INFO] Usuario {cedula} encontrado pero sin correos disponibles.")
        return None
