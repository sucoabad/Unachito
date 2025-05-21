# app/routes/zoom_routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.routes.unach_client import UnachApi
from app.services.ldap_service import reset_ldap_password
from app.utils.otp_manager import generar_otp, verificar_otp
from app.config.settings import get_settings
from app.utils.email import enviar_correo
import logging

router = APIRouter(prefix="/api/chatbot", tags=["Zoom-LDAP"])
logger = logging.getLogger("uvicorn.error")
settings = get_settings()

# Cache temporal OTP
otp_cache = {}

class CedulaRequest(BaseModel):
    cedula: str

class VerificarOtpRequest(BaseModel):
    cedula: str
    otp: str

class ResetZoomRequest(BaseModel):
    username: str
    confirm_data: str  # OTP
    new_password: str

@router.post("/enviar_otp_zoom")
async def enviar_otp_zoom(payload: CedulaRequest):
    cedula = payload.cedula
    api = UnachApi()
    correo = api.obtener_correo_por_cedula(cedula)

    if not correo:
        raise HTTPException(status_code=404, detail="No se encontró un correo para esa cédula.")

    otp = generar_otp()
    otp_cache[cedula] = otp

    contenido = f"Tu código OTP para cambiar la contraseña de Zoom es: {otp}"
    enviado = await enviar_correo(destinatario=correo, asunto="Código OTP - Zoom UNACH", cuerpo=contenido)

    if not enviado:
        raise HTTPException(status_code=500, detail="No se pudo enviar el OTP.")

    return {"status": "success", "message": "OTP enviado al correo registrado."}

@router.post("/verificar_otp_zoom")
async def verificar_otp_zoom(payload: VerificarOtpRequest):
    if otp_cache.get(payload.cedula) != payload.otp:
        raise HTTPException(status_code=400, detail="OTP incorrecto o expirado.")

    return {"status": "success", "message": "OTP verificado."}

@router.post("/reset_zoom")
async def reset_zoom(payload: ResetZoomRequest):
    if otp_cache.get(payload.username) != payload.confirm_data:
        raise HTTPException(status_code=400, detail="OTP inválido o expirado.")

    cambiado = reset_ldap_password(payload.username, payload.new_password)

    if not cambiado:
        raise HTTPException(status_code=500, detail="No se pudo actualizar la contraseña.")

    otp_cache.pop(payload.username, None)

    return {"status": "success", "message": "Contraseña de Zoom actualizada correctamente."}

