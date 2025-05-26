import ldap3
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config.settings import Settings

logger = logging.getLogger(__name__)

def change_ldap_zoom_password(
    username: str,
    new_password: str,
    settings: Settings,
    db: Session,
    client_ip: str = "N/A"
) -> None:
    """
    Cambia la contraseña del usuario Zoom en LDAP y registra el evento.
    """

    # 1) Extraigo la contraseña real del SecretStr
    ldap_password = settings.LDAP_ZOOM_PASSWORD.get_secret_value()

    # 2) Conexión al servidor LDAP
    server = ldap3.Server(settings.LDAP_ZOOM_HOST, port=settings.LDAP_ZOOM_PORT, get_info=ldap3.ALL)
    conn = ldap3.Connection(
        server,
        user=settings.LDAP_ZOOM_USER,
        password=ldap_password,    # <-- ya es un str
        auto_bind=True
    )

    # 3) Busco al usuario por su cn/uid
    search_filter = f"(cn={username})"
    conn.search(
        search_base=settings.LDAP_ZOOM_BASE_DN,
        search_filter=search_filter,
        attributes=["uid"]
    )
    if not conn.entries:
        conn.unbind()
        logger.warning(f"[LDAP-ZOOM] Usuario '{username}' no encontrado.")
        raise Exception(f"Usuario '{username}' no encontrado en LDAP.")

    user_dn = conn.entries[0].entry_dn

    # 4) Modifico la contraseña
    success = conn.modify(
        user_dn,
        {"userPassword": [(ldap3.MODIFY_REPLACE, [new_password])]}
    )
    if not success:
        error_msg = conn.result.get("message", "")
        conn.unbind()
        logger.error(f"[LDAP-ZOOM] Error modificando contraseña de {username}: {error_msg}")
        raise Exception(f"Error al actualizar la contraseña: {error_msg}")

    conn.unbind()

    # 5) Registrar el cambio en la base de datos
    try:
        db.execute(text("""
            INSERT INTO logs_password_changes
              (usuario, sistema, ip_origen, fecha_hora, observacion)
            VALUES
              (:u, 'zoom', :ip, :dt, 'Cambio de contraseña exitoso')
        """), {
            "u": username,
            "ip": client_ip,
            "dt": datetime.utcnow()
        })
        db.commit()
        logger.info(f"[LDAP-ZOOM] Contraseña cambiada para {username} desde {client_ip}")
    except Exception as db_err:
        db.rollback()
        logger.warning(f"[LDAP-ZOOM] Cambio realizado, pero no se pudo registrar en logs: {db_err}")
