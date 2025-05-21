# app/services/radius_service.py

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.utils.db import SessionLocalEstudiantes, SessionLocalDocentes, SessionLocal
from fastapi import HTTPException
from datetime import datetime
import logging

logger = logging.getLogger("uvicorn.error")


def change_radius_password(username: str, new_password: str, group: str, ip_origen: str = "desconocido") -> None:
    """
    Actualiza la contraseña Cleartext-Password de un usuario en la base RADIUS.
    También registra el cambio en logs_password_changes.
    """
    try:
        if group.lower() == "estudiantes":
            db_radius: Session = SessionLocalEstudiantes()
        elif group.lower() == "docentes":
            db_radius: Session = SessionLocalDocentes()
        else:
            raise HTTPException(status_code=400, detail="Grupo inválido")
    except Exception as e:
        logger.error(f"[RADIUS] Error conectando a RADIUS: {e}")
        raise HTTPException(status_code=500, detail="Error interno de conexión RADIUS")

    try:
        stmt = text("""
            UPDATE radcheck
            SET value = :pwd
            WHERE username = :user AND attribute = 'Cleartext-Password'
        """)
        result = db_radius.execute(stmt, {"pwd": new_password, "user": username})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado en RADIUS.")

        db_radius.commit()
        logger.info(f"[RADIUS] Contraseña actualizada para usuario: {username}")

        # Registrar en logs con IP
        registrar_log_password_change(username, "radius", ip_origen, "Cambio de contraseña exitoso")

    except HTTPException:
        db_radius.rollback()
        raise
    except Exception as e:
        db_radius.rollback()
        logger.error(f"[RADIUS] Error ejecutando UPDATE radcheck: {e}")
        raise HTTPException(status_code=500, detail="Error interno actualizando RADIUS")
    finally:
        db_radius.close()


def registrar_log_password_change(usuario: str, sistema: str, ip: str, observacion: str):
    """
    Registra un cambio de contraseña en la tabla logs_password_changes.
    """
    try:
        db = SessionLocal()
        stmt = text("""
            INSERT INTO logs_password_changes (usuario, sistema, ip_origen, fecha_hora, observacion)
            VALUES (:u, :s, :ip, :dt, :obs)
        """)
        db.execute(stmt, {
            "u": usuario,
            "s": sistema,
            "ip": ip,
            "dt": datetime.utcnow(),
            "obs": observacion
        })
        db.commit()
    except Exception as e:
        logger.warning(f"[RADIUS] Cambio realizado, pero error registrando en DB: {e}")
    finally:
        db.close()

