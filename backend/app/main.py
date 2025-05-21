# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.routes.chatbot_routes import router as chatbot_router, load_faq_cache, get_db

import logging

settings = get_settings()
app = FastAPI(title="Asistente Virtual UNACH")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logger = logging.getLogger("uvicorn.error")

# Precargar FAQs al iniciar el servidor
@app.on_event("startup")
async def on_startup():
    try:
        db = next(get_db())
        load_faq_cache(db)
        logger.info("✅ FAQ cache cargado en startup.")
    except Exception as e:
        logger.error(f"❌ Error cargando caché de FAQ en startup: {e}")

# Montar router del chatbot
app.include_router(chatbot_router)

