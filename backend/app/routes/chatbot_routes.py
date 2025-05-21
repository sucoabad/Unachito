from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.db import SessionLocal
from app.models.faq_model import FAQ
from app.models.unanswered_model import Unanswered
from app.services.radius_service import change_radius_password
from sentence_transformers import SentenceTransformer, util
from app.config.settings import Settings, get_settings
from datetime import datetime, timedelta
from email.message import EmailMessage
from app.routes.unach_client import UnachApi
from app.services.scraping_service import search_in_scraped_data

from app.services.knowledge_search import search_in_scraped_data

import aiosmtplib
import re, random, logging, time
import numpy as np

# ------------------------ CONFIGURACIÓN ------------------------
logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])

model = SentenceTransformer(
    'distiluse-base-multilingual-cased-v1',
    cache_folder="/srv/chatbot/.model_cache"
)
_cached_faqs = []
_cached_embeddings = []


# ------------------------ NLP: detección semántica ------------------------
contraseña_keywords = [
    "cambiar mi contraseña", "olvidé mi contraseña", "recuperar mi clave", "resetear password",
    "actualizar contraseña", "no puedo acceder", "problema con la clave", "restablecer contraseña", 
    "quiero cambiar el pass de la wifi",
    "quiero cambiar la clave de la red",
    "necesito cambiar mi clave wifi",
    "cambiar la contraseña de la red",
    "resetear clave del wifi",
    "cambiar clave del internet",
    "olvide la contraseña de la red",
    "clave de wifi",
    "pass del wifi",
    "no funciona mi wifi",
    "restablecer clave wifi"
]

saludo_keywords = [
    "hola", "buenos días", "buenas tardes", "buenas noches", "saludos", "hello", "hi", "qué tal",
    "buenas",
    "hey",
    "holi",
    "buen día",
    "buenas noches unachito",
    "unachito estás ahí",
    "unachito hola",
    "cómo estás",
    "qué onda",
    "qué hubo"
]

contraseña_embeddings = [model.encode(k, convert_to_tensor=True) for k in contraseña_keywords]
saludo_embeddings = [model.encode(k, convert_to_tensor=True) for k in saludo_keywords]

def es_pregunta_de_contrasena(texto: str) -> bool:
    emb = model.encode(texto, convert_to_tensor=True)
    sims = [util.pytorch_cos_sim(emb, ref)[0][0].item() for ref in contraseña_embeddings]
    max_sim = max(sims)
    logger.info(f"🔑 Similitud máxima con frases de contraseña: {max_sim:.4f}")
    return max_sim >= 0.60

def es_saludo(texto: str) -> bool:
    emb = model.encode(texto, convert_to_tensor=True)
    sims = [util.pytorch_cos_sim(emb, ref)[0][0].item() for ref in saludo_embeddings]
    max_sim = max(sims)
    logger.info(f"🙋 Similitud máxima con saludos: {max_sim:.4f}")
    return max_sim >= 0.65

# ------------------------ ESQUEMAS ------------------------
class QuestionRequest(BaseModel):
    pregunta: str

class EnviarOtpRequest(BaseModel):
    cedula: str

class VerificarOtpRequest(BaseModel):
    cedula: str
    otp: str

class ResetRadiusRequest(BaseModel):
    username: str
    confirm_data: str
    new_password: str
    grupo: str

class ResetZoomRequest(BaseModel):
    username: str
    confirm_data: str
    new_password: str


# ------------------------ DEPENDENCIA DB ------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------ CACHE FAQs ------------------------
def load_faq_cache(db: Session):
    global _cached_faqs, _cached_embeddings
    faqs = db.query(FAQ).all()
    _cached_faqs = faqs
    _cached_embeddings = [model.encode(f.pregunta.lower(), convert_to_tensor=True) for f in faqs]
    logger.info(f"✅ Cargadas {len(_cached_faqs)} FAQs en caché.")

@router.on_event("startup")
async def startup_event():
    db = next(get_db())
    load_faq_cache(db)

@router.post("/query")
async def chatbot_query(
    payload: QuestionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    try:
        pregunta = payload.pregunta.strip().lower()
        if not pregunta:
            raise HTTPException(400, "Pregunta vacía.")

        if es_saludo(pregunta):
            return {
                "respuesta": (
                    "👋 <strong>¡Hola! Soy Unachito</strong>, tu compañero digital en la UNACH.<br><br>"
                    "Estoy aquí para ayudarte con:<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;📡 <strong>WiFi</strong><br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;📘 <strong>Moodle</strong><br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;🎥 <strong>Zoom</strong><br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;📧 <strong>Office 365</strong><br><br>"
                    "También puedo responder tus preguntas frecuentes.<br><br>"
                    "😊 <strong>¿Cómo te llamas?</strong>"
                ),
                "fuente": "Saludo",
            }

        if es_pregunta_de_contrasena(pregunta):
            return JSONResponse({
                "respuesta": "Para cambiar tu contraseña, selecciona una opción:",
                "fuente": "Manejo especial",
                "acciones": ["wifi", "office365", "moodle", "zoom"]
            })

        emb_user = model.encode(pregunta, convert_to_tensor=True)

        if not _cached_embeddings:
            raise HTTPException(500, "No hay FAQs cargadas en memoria.")

        import torch
        emb_tensor = torch.stack(_cached_embeddings)
        sims = util.pytorch_cos_sim(emb_user, emb_tensor)[0]
        best_idx = sims.argmax().item()
        best_sim = sims[best_idx].item()
        best_resp = _cached_faqs[best_idx].respuesta

        print(f"🔍 Similitud: {best_sim:.4f} - Pregunta coincidente: {_cached_faqs[best_idx].pregunta}")

        if best_resp and best_sim >= settings.THRESHOLD_FAQ:
            return {
                "respuesta": best_resp,
                "fuente": "FAQ BD"
            }

        # Registrar pregunta sin respuesta
        nueva = Unanswered(
            pregunta=payload.pregunta.strip(),
            usuario_ip=request.client.host,
            origen="API Chatbot",
            url_origen=request.headers.get('referer', 'N/A')
        )
        db.add(nueva)
        db.commit()

        # Intentar scraping si está habilitado
        if str(settings.ENABLE_SCRAPING).lower() == "true":
            try:
                respuesta_scraping = search_in_scraped_data(pregunta, umbral_similitud=settings.THRESHOLD_SCRAPING)
                if respuesta_scraping:
                    return {
                        "respuesta": respuesta_scraping,
                        "fuente": "Scraping"
                    }
            except Exception as e:
                print(f"[SCRAPING] Error al intentar búsqueda semántica: {e}")

        return {
            "respuesta": "Lo siento, no encontré una respuesta adecuada.",
            "fuente": "Sin respuesta"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")



# ------------------------ ENDPOINTS PARA WIFI Y ZOOM COMPARTIDO ------------------------

@router.post("/enviar_otp")
async def enviar_otp(
    payload: EnviarOtpRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    cedula = payload.cedula.strip()
    if not cedula.isdigit() or len(cedula) < 8:
        raise HTTPException(400, "Cédula inválida.")

    cliente = UnachApi(verify_ssl=False)
    correo = cliente.get_correo_por_cedula(cedula)
    print(f"Correo de {cedula} → {correo or 'No encontrado'}")

    if not correo:
        raise HTTPException(404, "No se encontró correo para esta cédula.")

    otp = f"{random.randint(0, 999999):06d}"
    exp = datetime.utcnow() + timedelta(minutes=10)

    db.execute(
        text("""
            INSERT INTO otp_tokens (cedula, correo, codigo_otp, expiracion, ip_origen, comentario)
            VALUES (:c, :e, :o, :x, :ip, :m)
        """),
        {"c": cedula, "e": correo, "o": otp, "x": exp, "ip": request.client.host, "m": "Enviado OTP"}
    )
    db.commit()

    background_tasks.add_task(enviar_correo_otp, correo, otp, settings)
    return {"status": "success", "message": f"OTP enviado a {correo}."}


async def enviar_correo_otp(dest: str, otp: str, settings: Settings) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_USER
    msg["To"] = dest
    msg["Subject"] = "Código de verificación para cambio de contraseña – UNACH"
    msg.set_content(f"""
Estimado/a usuario/a,

Su código OTP es: {otp}

Este código expira en 10 minutos.

Atentamente,
Asistente Virtual UNACH
""")

    msg.add_alternative(f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px;">
      <div style="text-align: center; margin-bottom: 20px;">
        <img src="https://dtic.unach.edu.ec/wp-content/uploads/2025/05/unach.png" alt="Logo UNACH" style="width: 80px; height: auto;">
        <h2 style="color: #004080; margin-top: 10px;">Asistente Virtual UNACH</h2>
      </div>

      <p>Estimado/a usuario/a,</p>
      <p>Hemos recibido una solicitud para verificación de identidad mediante un código OTP.</p>

      <p style="font-size: 18px; font-weight: bold; color: #004080; text-align: center;">
        🔐 Su código de verificación es:<br>
        <span style="display: inline-block; margin-top: 10px; background: #f0f0f0; padding: 10px 20px; border-radius: 5px; font-size: 24px; letter-spacing: 2px;">
          {otp}
        </span>
      </p>

      <p style="text-align: center; color: #888; font-size: 13px;">Este código es válido por 10 minutos.</p>

      <p>Por razones de seguridad, <strong>no comparta este código</strong> con nadie.</p>
      <p>Si usted no solicitó este código, puede ignorar este mensaje.</p>

      <br>
      <p style="font-size: 14px; color: #555;">
        Atentamente,<br>
        <strong>Asistente Virtual UNACH</strong><br>
        Dirección de Tecnologías de la Información y Comunicación<br>
        Universidad Nacional de Chimborazo
      </p>
    </div>
  </body>
</html>
""", subtype='html')

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        start_tls=True,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD
    )


@router.post("/verificar_otp")
async def verificar_otp(
    payload: VerificarOtpRequest,
    db: Session = Depends(get_db)
):
    cedula, otp = payload.cedula.strip(), payload.otp.strip()
    if not (cedula.isdigit() and otp.isdigit() and len(otp) == 6):
        raise HTTPException(400, "Formato inválido.")

    rec = db.execute(
        text("SELECT * FROM otp_tokens WHERE cedula=:c AND codigo_otp=:o ORDER BY id DESC LIMIT 1"),
        {"c": cedula, "o": otp}
    ).mappings().first()

    if not rec:
        raise HTTPException(404, "OTP no encontrado.")
    if rec["intentos"] >= 5:
        raise HTTPException(403, "Máximo intentos superado.")

    db.execute(text("UPDATE otp_tokens SET intentos = intentos + 1 WHERE id = :id"), {"id": rec["id"]})
    db.commit()

    now = datetime.utcnow()
    if now > rec["expiracion"]:
        db.execute(text("UPDATE otp_tokens SET comentario = :m WHERE id = :id"),
                   {"m": "OTP expirado", "id": rec["id"]})
        db.commit()
        raise HTTPException(400, "El OTP ha expirado.")

    if rec["usado"]:
        raise HTTPException(400, "Este OTP ya fue usado.")

    db.execute(
        text("UPDATE otp_tokens SET comentario = :m WHERE id = :id"),
        {"m": f"✅ Verificado en {now.strftime('%Y-%m-%d %H:%M:%S')}", "id": rec["id"]}
    )
    db.commit()
    return {"status": "success", "message": "✅ OTP verificado correctamente."}


# ------------------------ ENDPOINTS PARA WIFI ------------------------

@router.post("/reset_radius_password")
async def reset_radius_password(
    payload: ResetRadiusRequest,
    request: Request,  # ✅ Se agrega aquí
    settings: Settings = Depends(get_settings),
    db_otp: Session = Depends(get_db),
):
    username = payload.username.strip()
    otp = payload.confirm_data.strip()
    new_pw = payload.new_password
    grupo = payload.grupo

    token = db_otp.execute(
        text("SELECT * FROM otp_tokens WHERE cedula=:c AND codigo_otp=:o ORDER BY id DESC LIMIT 1"),
        {"c": username, "o": otp}
    ).mappings().first()

    if not token:
        raise HTTPException(400, "OTP inválido o no encontrado.")
    if token["usado"]:
        raise HTTPException(400, "Este OTP ya fue usado.")
    if token["expiracion"] < datetime.utcnow():
        raise HTTPException(400, "El OTP ha expirado.")

    change_radius_password(username, new_pw, grupo, request.client.host)

    try:
        db_otp.execute(
            text("UPDATE otp_tokens SET usado = TRUE, comentario = :c WHERE id = :id"),
            {"id": token["id"], "c": f"✅ Consumido en reset WIFI {datetime.utcnow().isoformat()}"}
        )
        db_otp.commit()
    except Exception as e:
        db_otp.rollback()
        logger.error(f"Error marcando OTP usado tras reset: {e}")

    return {"status": "success", "message": "Contraseña de la red Inalambrica actualizada correctamente."}



# ------------------------ ENDPOINTS PARA ZOOM ------------------------

from app.services.ldap_service import change_ldap_zoom_password

@router.post("/reset_zoom_password")
async def reset_zoom_password(
    payload: ResetRadiusRequest,  # puede seguir usando este esquema
    request: Request,
    settings: Settings = Depends(get_settings),
    db_otp: Session = Depends(get_db),
):
    username = payload.username.strip()
    otp = payload.confirm_data.strip()
    new_pw = payload.new_password

    token = db_otp.execute(
       text("SELECT * FROM otp_tokens WHERE cedula=:c AND codigo_otp=:o ORDER BY id DESC LIMIT 1"),
        {"c": username, "o": otp}
    ).mappings().first()

    if not token:
        raise HTTPException(400, "OTP inválido o no encontrado.")
    if token["usado"]:
        raise HTTPException(400, "Este OTP ya fue usado.")
    if token["expiracion"] < datetime.utcnow():
        raise HTTPException(400, "El OTP ha expirado.")

    try:
        change_ldap_zoom_password(username, new_pw, settings, db_otp, request.client.host)
    except Exception as e:
        raise HTTPException(500, f"❗ Error al cambiar contraseña en LDAP: {e}")

    try:
        db_otp.execute(
            text("UPDATE otp_tokens SET usado = TRUE, comentario = :c WHERE id = :id"),
            {"id": token["id"], "c": f"✅ Consumido en reset ZOOM {datetime.utcnow().isoformat()}"}
        )
        db_otp.commit()
    except Exception as e:
        db_otp.rollback()
        logger.error(f"Error marcando OTP usado en zoom: {e}")

    return {"status": "success", "message": "Contraseña de Zoom actualizada correctamente."}

