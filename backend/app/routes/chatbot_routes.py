from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks, status
from pydantic import BaseModel
from typing import Literal, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from email.message import EmailMessage
import aiosmtplib, logging, random

from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer, util
import torch

from app.utils.db import SessionLocal, SessionLocalEstudiantes, SessionLocalServidores
from app.models.faq_model import FAQ
from app.models.unanswered_model import Unanswered
from app.routes.unach_client import UnachApi
from app.services.scraping_service import search_in_scraped_data
from app.services.radius_service import change_radius_password
from app.services.ldap_service import change_ldap_zoom_password
from app.config.settings import Settings, get_settings

import ldap3
settings = get_settings()


# ------------------------ CONFIGURACIÓN ------------------------
logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])

# Carga de modelo y cache de FAQs en memoria
model = SentenceTransformer('distiluse-base-multilingual-cased-v1')
_cached_faqs: list[FAQ] = []
_cached_embeddings: list[torch.Tensor] = []

# Palabras clave para flujos especiales
PASSWD_KW    = ["cambiar mi contraseña", "olvidé mi contraseña", "resetear password", "restablecer contraseña"]
SALUDO_KW    = ["hola", "buenos días", "buenas tardes", "saludos", "hello"]
PASSWD_EMB   = [model.encode(k, convert_to_tensor=True) for k in PASSWD_KW]
SALUDO_EMB   = [model.encode(k, convert_to_tensor=True) for k in SALUDO_KW]
THRESHOLD_PW = 0.60
THRESHOLD_HELLO = 0.65

# ------------------------ DEPENDENCIA DB ------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------ ESQUEMAS ------------------------
class QuestionRequest(BaseModel):
    pregunta: str

class GetUserInfoRequest(BaseModel):
    cedula: str
    user_type: Literal['estudiante','servidor']

class CheckAccountRequest(BaseModel):
    cedula: str
    user_type: Literal['estudiante','servidor']
    servicio: Literal['wifi','zoom']

class EnviarOtpRequest(BaseModel):
    cedula: str
    user_type: Literal['estudiante','servidor']
    servicio: Literal['wifi','zoom']

class VerificarOtpRequest(BaseModel):
    cedula: str
    otp: str

class ResetRadiusRequest(BaseModel):
    username: str
    confirm_data: str
    new_password: str
    grupo: str

# ------------------------ UTILIDADES NLP ------------------------
def es_saludo(texto: str) -> bool:
    emb = model.encode(texto, convert_to_tensor=True)
    sims = [util.pytorch_cos_sim(emb, ref)[0][0].item() for ref in SALUDO_EMB]
    return max(sims) >= THRESHOLD_HELLO

def es_pregunta_de_contrasena(texto: str) -> bool:
    emb = model.encode(texto, convert_to_tensor=True)
    sims = [util.pytorch_cos_sim(emb, ref)[0][0].item() for ref in PASSWD_EMB]
    return max(sims) >= THRESHOLD_PW

# ------------------------ CACHE FAQs ------------------------
def load_faq_cache(db: Session):
    global _cached_faqs, _cached_embeddings
    faqs = db.query(FAQ).all()
    _cached_faqs = faqs
    _cached_embeddings = [
        model.encode(f.pregunta.lower(), convert_to_tensor=True)
        for f in faqs
    ]

@router.on_event("startup")
async def startup_event():
    db = next(get_db())
    load_faq_cache(db)

# ------------------------ ENVÍO DE CORREO OTP ------------------------

async def enviar_correo_otp(dest: str, otp: str, settings: Settings) -> None:
    # Construir el mensaje
    msg = EmailMessage()
    msg["From"] = settings.SMTP_USER
    msg["To"] = dest
    msg["Subject"] = "Código de verificación – Asistente Virtual UNACH"

    # Texto plano de respaldo
    texto_plano = f"""
Estimado/a usuario/a,

Hemos recibido una solicitud para verificación de identidad mediante un código OTP.

Su código de verificación es: {otp}

Este código expira en 10 minutos. Por favor, no comparta este código con nadie.

Atentamente,
Asistente Virtual UNACH
Dirección de Tecnologías de la Información y Comunicación
Universidad Nacional de Chimborazo
"""

    # HTML enriquecido
    html = f"""
<html>
  <body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;border:1px solid #ddd;padding:20px;border-radius:8px;">
      <div style="text-align:center;margin-bottom:20px;">
        <img src="https://dtic.unach.edu.ec/wp-content/uploads/2025/05/unach.png"
             alt="Logotipo UNACH" width="80" style="display:block;margin:auto;"/>
        <h2 style="color:#00539C;">Asistente Virtual UNACH</h2>
      </div>
      <p>Estimado/a usuario/a,</p>
      <p>Hemos recibido una solicitud para verificación de identidad mediante un código OTP.</p>
      <p style="font-size:1.1em;">
        <strong>🔒 Su código de verificación es:</strong><br/>
        <span style="
          display:inline-block;
          background:#f5f5f5;
          padding:10px 20px;
          border-radius:4px;
          font-size:1.5em;
          letter-spacing:3px;
        ">
          {otp}
        </span>
      </p>
      <p style="font-size:0.9em;color:#666;">
        Este código es válido por <strong>10 minutos</strong>.<br/>
        Por razones de seguridad, <strong>no comparta este código con nadie</strong>.<br/>
        Si usted no solicitó este código, puede ignorar este mensaje.
      </p>
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0;"/>
      <p>Atentamente,</p>
      <p>
        <strong>Asistente Virtual UNACH</strong><br/>
        Dirección de Tecnologías de la Información y Comunicación<br/>
        Universidad Nacional de Chimborazo
      </p>
    </div>
  </body>
</html>
"""

    # Asignar contenidos al mensaje
    msg.set_content(texto_plano)
    msg.add_alternative(html, subtype="html")

    # Credenciales
    usuario = settings.SMTP_USER
    contraseña = settings.SMTP_PASSWORD.get_secret_value()

    try:
        # Envío
        client = aiosmtplib.SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            timeout=10.0,
        )
        await client.connect()
        await client.login(usuario, contraseña)
        await client.send_message(msg)
        await client.quit()
        logger.info(f"✅ OTP enviado correctamente a {dest}")
    except Exception as e:
        logger.error(f"❗ Error enviando OTP a {dest}: {e}", exc_info=True)


# ------------------------ ENDPOINTS ------------------------

@router.post("/query")
async def chatbot_query(
    payload: QuestionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> Dict:
    pregunta = payload.pregunta.strip().lower()
    if not pregunta:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pregunta vacía.")

    # 1) Saludo inicial
    if es_saludo(pregunta):
        return {
            "respuesta": (
                "👋 <strong>¡Hola! Soy Unachito</strong>.<br>"
                "😊 ¿Eres Estudiante, Servidor o Externo?"
            ),
            "fuente": "Saludo",
            "acciones": ["Estudiante","Servidor","Externo"]
        }

    # 2) Intento FAQ en caché
    if _cached_embeddings:
        emb_user   = model.encode(pregunta, convert_to_tensor=True)
        emb_tensor = torch.stack(_cached_embeddings)
        sims       = util.pytorch_cos_sim(emb_user, emb_tensor)[0]
        best_idx   = sims.argmax().item()
        if sims[best_idx].item() >= settings.THRESHOLD_FAQ:
            return {
                "respuesta": _cached_faqs[best_idx].respuesta,
                "fuente": "FAQ BD",
                "acciones": []
            }

    # 3) Cambio de contraseña
    if es_pregunta_de_contrasena(pregunta):
        return {
            "respuesta": "🔑 Para cambiar tu contraseña, selecciona un servicio:",
            "fuente": "Manejo especial",
            "acciones": ["WiFi","Zoom"]
        }

    # 4) Registrar unanswered
    db.add(Unanswered(
        pregunta   = payload.pregunta.strip(),
        usuario_ip = request.client.host,
        origen     = "API Chatbot",
        url_origen = request.headers.get('referer','')
    ))
    db.commit()

    # 5) Scraping fallback
    if settings.ENABLE_SCRAPING:
        resp = search_in_scraped_data(
            pregunta,
            umbral_similitud=settings.THRESHOLD_SCRAPING
        )
        if resp:
            return {"respuesta": resp, "fuente": "Scraping", "acciones": []}

    # 6) Respuesta por defecto
    return {
        "respuesta": (
            "❓ Lo siento, no encontré respuesta.<br>"
            "¿Quieres consultar nuestras preguntas frecuentes?"
        ),
        "fuente": "Sin respuesta",
        "acciones": ["Mostrar FAQs"]
    }

@router.post("/get_user_info")
async def get_user_info(
    payload: GetUserInfoRequest
) -> Dict:
    api = UnachApi(verify_ssl=False)
    nombre = api.get_nombre_por_cedula(payload.cedula, payload.user_type)
    if not nombre:
        return {"error": "Usuario no encontrado"}
    return {"nombre": nombre}





@router.post(
    "/check_account",
    response_model=Dict[str, bool],
    summary="Verifica si existe cuenta de WiFi o Zoom para la cédula dada"
)
async def check_account(payload: CheckAccountRequest) -> Dict[str, bool]:
    """
    Verifica existencia de cuenta de WiFi (RADIUS) o Zoom (LDAP)
    según payload.servicio. Siempre devuelve {"exists": bool}
    para que el frontend pueda decidir no esperar OTP si es False.
    """
    cedula = payload.cedula
    servicio = payload.servicio.lower()
    exists = False

    try:
        if servicio == "wifi":
            # 1) Conexión a la base RADIUS según tipo de usuario
            session: Session = (
                SessionLocalEstudiantes() if payload.user_type == "estudiante"
                else SessionLocalServidores()
            )
            try:
                row = session.execute(
                    text("SELECT 1 FROM radcheck WHERE username = :u LIMIT 1"),
                    {"u": cedula}
                ).first()
                exists = row is not None
            finally:
                session.close()

        elif servicio == "zoom":
            # 2) Búsqueda en LDAP Zoom
            ldap_pass = settings.LDAP_ZOOM_PASSWORD.get_secret_value()
            server = ldap3.Server(
                settings.LDAP_ZOOM_HOST,
                port=settings.LDAP_ZOOM_PORT,
                get_info=ldap3.ALL
            )
            conn = ldap3.Connection(
                server,
                user=settings.LDAP_ZOOM_USER,
                password=ldap_pass,
                auto_bind=True
            )
            conn.search(
                search_base=settings.LDAP_ZOOM_BASE_DN,
                search_filter=f"(cn={cedula})",
                attributes=["cn"]
            )
            exists = bool(conn.entries)
            conn.unbind()

        else:
            # servicio no soportado
            exists = False

    except Exception as e:
        # Cualquier error, lo registramos y devolvemos exists=False
        logger.error("Error al verificar cuenta %s para %s: %s", servicio, cedula, e)

    return {"exists": exists}




@router.post("/enviar_otp")
async def enviar_otp(
    payload: EnviarOtpRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> Dict:
    if not payload.cedula.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cédula inválida.")
    api    = UnachApi(verify_ssl=False)
    correo = api.get_correo_por_cedula(payload.cedula, payload.user_type)
    if not correo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Correo institucional no encontrado.")

    otp = f"{random.randint(0,999999):06d}"
    exp = datetime.utcnow() + timedelta(minutes=10)
    db.execute(text(
        "INSERT INTO otp_tokens(cedula,correo,codigo_otp,expiracion,ip_origen,comentario) "
        "VALUES(:c,:e,:o,:x,:ip,'OTP enviado')"
    ), {"c":payload.cedula, "e":correo, "o":otp, "x":exp, "ip":request.client.host})
    db.commit()

    background_tasks.add_task(enviar_correo_otp, correo, otp, settings)
    return {"status":"success", "message":f"✅ OTP enviado a {correo}."}

@router.post("/verificar_otp")
async def verificar_otp(
    payload: VerificarOtpRequest,
    db: Session = Depends(get_db)
) -> Dict:
    rec = db.execute(text(
        "SELECT * FROM otp_tokens WHERE cedula=:c AND codigo_otp=:o "
        "ORDER BY id DESC LIMIT 1"
    ), {"c":payload.cedula, "o":payload.otp}).mappings().first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OTP no encontrado.")
    if rec['expiracion'] < datetime.utcnow() or rec['usado']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP inválido o expirado.")

    db.execute(text("UPDATE otp_tokens SET usado=TRUE WHERE id=:id"), {"id":rec['id']})
    db.commit()
    return {"status":"success", "message":"✅ OTP verificado."}

@router.post("/reset_radius_password")
async def reset_radius_password(
    payload: ResetRadiusRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    db_otp: Session = Depends(get_db)
) -> Dict:
    rec = db_otp.execute(text(
        "SELECT * FROM otp_tokens WHERE cedula=:c AND codigo_otp=:o "
        "ORDER BY id DESC LIMIT 1"
    ), {"c":payload.username, "o":payload.confirm_data}).mappings().first()
    if not rec or rec['expiracion'] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP inválido o expirado.")

    change_radius_password(
        payload.username,
        payload.new_password,
        payload.grupo,
        request.client.host
    )
    db_otp.execute(text("UPDATE otp_tokens SET usado=TRUE WHERE id=:id"), {"id":rec['id']})
    db_otp.commit()
    return {"status":"success", "message":"🎉 Contraseña WiFi actualizada correctamente."}

@router.post("/reset_zoom_password")
async def reset_zoom_password(
    payload: ResetRadiusRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    db_otp: Session = Depends(get_db)
) -> Dict:
    # 1) Validar OTP
    rec = db_otp.execute(text(
        "SELECT * FROM otp_tokens WHERE cedula=:c AND codigo_otp=:o "
        "ORDER BY id DESC LIMIT 1"
    ), {"c": payload.username, "o": payload.confirm_data}).mappings().first()
    if not rec or rec["expiracion"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP inválido o expirado.")

    # 2) Cambiar contraseña en LDAP
    change_ldap_zoom_password(
        username=payload.username,
        new_password=payload.new_password,
        settings=settings,        # le pasamos todo Settings
        db=db_otp,
        client_ip=request.client.host
    )

    # 3) Marcar OTP como usado
    db_otp.execute(
        text("UPDATE otp_tokens SET usado=TRUE WHERE id=:id"),
        {"id": rec["id"]}
    )
    db_otp.commit()

    return {"status": "success", "message": "🎉 Contraseña Zoom actualizada correctamente."}
