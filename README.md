# Unachito Chatbot

![Unachito Logo](https://chatbot.unach.edu.ec/widget/img/logo.png)

**Unachito** es un agente de IA conversacional diseñado para descentralizar y automatizar el soporte técnico de contraseñas y FAQs en la UNACH.  
Implementado en Python & FastAPI sobre MySQL, se integra como widget en WordPress y C# y ofrece:

- 🔐 Restablecimiento remoto de contraseñas Wi-Fi (RADIUS) y Zoom (LDAP) vía OTP  
- 🤖 Clasificación de intenciones + búsqueda semántica en FAQs  
- ⭐ Feedback activo (👍/👎) y escalado automático de casos complejos  
- 📈 Detección de tendencias y alertas automáticas al equipo de DTIC  
- ⏰ Scheduler para retraining mensual y clustering semanal (pendiente de habilitar)

---

## 📂 Estructura del repositorio

unachito_chatbot/
├── app/
│ ├── main.py # Inicializa FastAPI, Prometheus y Scheduler
│ ├── chatbot_routes.py # Endpoints de OTP, query, rating y escalado
│ ├── scheduler.py # Tareas con APScheduler
│ ├── services/ # Lógica de negocio y conectores
│ │ ├── ml.py # Fine-tuning y clasificación de intenciones
│ │ ├── trending.py # Detección de tendencias y alertas
│ │ ├── radius_service.py # Cambio de password en RADIUS
│ │ ├── ldap_service.py # Cambio de password en LDAP (Zoom)
│ │ ├── office365.py # (Futuro) reset via Graph API
│ │ ├── moodle.py # (Futuro) integración con REST API Moodle
│ │ ├── voice.py # (Opcional) STT wrapper
│ │ └── ocr.py # (Opcional) OCR de capturas de pantalla
│ └── utils/
│ └── db.py # Conexión y sesión con MySQL
├── update_scraped_data.py # Script para refrescar datos y embeddings
├── requirements.txt # Dependencias
└── README.md # Este archivo


---

## 🚀 Instalación

1. **Clona el repositorio**  
   ```bash
   git clone https://github.com/UNACH-DTIC/unachito_chatbot.git
   cd unachito_chatbot

Prepara el entorno

bash
Copiar
Editar
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
Configura la base de datos

Crea una instancia MySQL 8.0 y un usuario con permisos.

Ajusta app/utils/db.py con tu cadena de conexión.

Define variables de entorno

ini
Copiar
Editar
DATABASE_URL=mysql://user:pass@host:3306/unachito
UNACH_API_BASE=https://api.unach.edu.ec
EMAIL_SMTP_HOST=smtp.unach.edu.ec
EMAIL_SMTP_USER=bot@unach.edu.ec
EMAIL_SMTP_PASS=…
Configura Nginx & systemd

Copia deploy/unachito.service a /etc/systemd/system/.

Copia deploy/unachito.conf a /etc/nginx/conf.d/.

Recarga y arranca servicios:

bash
Copiar
Editar
systemctl daemon-reload
systemctl enable --now unachito
nginx -s reload
💬 Integración en WordPress / C#
En tu tema o plugin de WordPress (dtic.unach.edu.ec) añade al <head>:

html
Copiar
Editar
<link rel="stylesheet" href="https://chatbot.unach.edu.ec/widget/css/style.css?v=2" />
<script src="https://chatbot.unach.edu.ec/widget/js/chatbot-widget.js" defer></script>
<div id="chatbot-button">💬</div>
En tu proyecto C# (uvirtual.unach.edu.ec) inserta el mismo bloque en la master page o layout.

🛠 Uso
Iniciar servidor

bash
Copiar
Editar
uvicorn app.main:app --host 0.0.0.0 --port 8000
Documentación interactiva
Visita https://chatbot.unach.edu.ec/docs para probar todos los endpoints.

Métricas
Expuestas en https://chatbot.unach.edu.ec/metrics (Prometheus).

📋 Endpoints clave
Ruta	Método	Descripción
/api/chatbot/enviar_otp	POST	Envía OTP al correo asociado a una cédula
/api/chatbot/verificar_otp	POST	Verifica OTP y ejecuta cambio en RADIUS/LDAP
/api/chatbot/query	POST	Clasifica consulta y responde o escala a humano
/api/chatbot/rate_response	POST	Recibe valoración 👍/👎 para feedback del modelo

🤝 Contribuciones
Unachito está licenciado bajo GNU AFFERO GPL v3.
Todos los cambios que despliegues como servicio web deben ponerse a disposición de los usuarios y publicarse en este repositorio.
Para contribuir:

Haz tu fork y crea una rama nueva: feature/mi-mejora.

Abre un pull request describiendo tu aporte.

Asegúrate de incluir tests y actualizar documentación.

⚖️ Licencia
© 2025 UNACH, Hernán Xavier Abad Hidalgo
Este proyecto está bajo la GNU Affero GPL v3.




# 🤖 Unachito – Chatbot Institucional de la UNACH

**Unachito** es un chatbot institucional desarrollado para la Universidad Nacional de Chimborazo (UNACH), diseñado para brindar asistencia automatizada a estudiantes, docentes, administrativos y usuarios externos.

<p align="center">
  <img src="frontend/widget/img/unach-sphere.png" alt="Unachito Logo" width="120"/>
</p>

---

## ✅ Funcionalidades implementadas

- 💬 Responde preguntas frecuentes (FAQs) usando búsqueda semántica.
- 🔐 Verificación de identidad por cédula y tipo de usuario (estudiante, servidor o externo).
- 📧 Envío de código OTP al correo institucional para validar identidad.
- 🔄 Cambio de contraseñas para servicios WiFi y Zoom.
- 📚 Flujo completo de conversación con validación paso a paso.
- 📜 Consentimiento de Política de Protección de Datos Personales.
- 💡 Registro de preguntas no respondidas para análisis posterior.
- 🖼️ Widget web adaptable, visualmente moderno y responsivo.

## 🧪 Tecnologías utilizadas

| Componente        | Tecnología                          |
|-------------------|--------------------------------------|
| API REST          | FastAPI (Python 3.10+)               |
| IA/PLN            | SentenceTransformers (MiniLM)        |
| Base de datos     | PostgreSQL                           |
| Frontend          | HTML, CSS, JavaScript (widget)       |
| Correo OTP        | aiosmtplib                           |
| Backend adicional | Verificación por LDAP, RADIUS        |
| Autenticación     | Validación por cédula + OTP          |

## 🗃️ Estructura del repositorio

```
📦 unachito-chatbot
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   └── chatbot_routes.py
│   │   ├── services/
│   │   │   ├── radius_service.py
│   │   │   ├── ldap_service.py
│   │   │   ├── scraping_service.py
│   │   │   └── unach_client.py
│   │   ├── models/
│   │   │   ├── faq_model.py
│   │   │   └── unanswered_model.py
│   │   └── knowledge_search.py
│   └── main.py
├── frontend/
│   ├── widget/
│   │   ├── js/
│   │   │   └── chatbot-widget.js
│   │   ├── css/
│   │   │   └── style.css
│   │   └── img/
│   │       └── unach-sphere.png
│   └── index.html
└── README.md
```

## 🚀 Instalación rápida (modo desarrollo)

### Requisitos previos

- Python 3.10+
- PostgreSQL
- Navegador moderno

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

Abrir el archivo `frontend/index.html` directamente en el navegador.

## 🔐 Seguridad y ética

- Solicita consentimiento explícito para el tratamiento de datos personales.
- Los códigos OTP se envían únicamente a correos registrados.
- Las preguntas no resueltas se registran para futura mejora del sistema.

## 🏷️ Créditos

Desarrollado por **HXAH**  
Maestría en Inteligencia Artificial Aplicada – Universidad de los Hemisferios 