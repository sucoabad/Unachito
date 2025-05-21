# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.routes.chatbot_routes import router as chatbot_router, load_faq_cache, get_db

settings = get_settings()
app = FastAPI(title="Asistente Virtual UNACH")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # aquí ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Evento de arranque: precargar FAQs en memoria
@app.on_event("startup")
async def on_startup():
    db = next(get_db())
    load_faq_cache(db)

# Montar router del chatbot
app.include_router(chatbot_router)
