import ldap3
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config.settings import Settings

logger = logging.getLogger(__name__)


def change_ldap_zoom_password(username: str, new_password: str, settings: Settings, db: Session, ip: str = "N/A") -> None:
    """
    Cambia la contraseña del usuario Zoom en LDAP y registra el evento.

    :param username: Nombre de usuario (uid).
    :param new_password: Nueva contraseña.
    :param settings: Configuración con parámetros LDAP.
    :param db: Sesión de base de datos SQLAlchemy.
    :param ip: Dirección IP de origen del cambio.
    :raises Exception: Si no se puede realizar el cambio.
    """

    # Conexión al servidor LDAP
    server = ldap3.Server(settings.LDAP_ZOOM_HOST, port=settings.LDAP_ZOOM_PORT, use_ssl=False)
    conn = ldap3.Connection(
        server,
        user=settings.LDAP_ZOOM_USER,
        password=settings.LDAP_ZOOM_PASSWORD,
        auto_bind=True
    )

    # Buscar al usuario
    search_filter = f"(cn={username})"
    conn.search(
        search_base=settings.LDAP_ZOOM_BASE_DN,
        search_filter=search_filter,
        attributes=["uid"]
    )

    if not conn.entries:
        logger.warning(f"[LDAP-ZOOM] Usuario '{username}' no encontrado.")
        raise Exception(f"Usuario '{username}' no encontrado en LDAP.")

    user_dn = conn.entries[0].entry_dn

    # Modificar contraseña
    success = conn.modify(user_dn, {
        'userPassword': [(ldap3.MODIFY_REPLACE, [new_password])]
    })

    if not success:
        error_msg = conn.result['message']
        logger.error(f"[LDAP-ZOOM] Error modificando contraseña de {username}: {error_msg}")
        raise Exception(f"Error modificando contraseña: {error_msg}")

    # Registrar en base de datos
    try:
        db.execute(text("""
            INSERT INTO logs_password_changes (usuario, sistema, ip_origen, fecha_hora, observacion)
            VALUES (:u, :s, :ip, :dt, :obs)
        """), {
            "u": username,
            "s": "zoom",
            "ip": ip,
            "dt": datetime.utcnow(),
            "obs": "Cambio de contraseña exitoso"
        })
        db.commit()
        logger.info(f"[LDAP-ZOOM] Contraseña cambiada para {username} desde {ip}")
    except Exception as db_error:
        db.rollback()
        logger.warning(f"[LDAP-ZOOM] Cambio realizado, pero error registrando en DB: {db_error}")

