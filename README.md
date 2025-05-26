
# 🤖 Unachito Chatbot

![Logo Unachito](https://chatbot.unach.edu.ec/widget/img/logo.png)

**Unachito** es un agente conversacional de la Universidad Nacional de Chimborazo (UNACH), desarrollado para automatizar la asistencia técnica relacionada con contraseñas institucionales (Wi-Fi, Zoom) y responder preguntas frecuentes (FAQs). Está diseñado para integrarse fácilmente con sistemas WordPress y C#.

---

## 🚀 Funcionalidades principales

- 🔐 **Restablecimiento de contraseñas**:
  - Wi-Fi (RADIUS)
  - Zoom (LDAP)
- 🔑 Verificación mediante OTP enviado al correo institucional
- 📚 Respuestas semánticas a preguntas frecuentes usando embeddings
- ✅ Clasificación automática de intenciones (saludo, pregunta, etc.)
- 🧠 Evaluación continua con botones de 👍 / 👎
- 🌐 Integración como widget flotante en cualquier sitio web (HTML/JS)

---

## 🛠️ Tecnologías utilizadas

- **Backend:** Python 3.11, FastAPI, Uvicorn
- **Frontend:** HTML + CSS + JS (sin frameworks externos)
- **Base de datos:** MySQL 8.0
- **Autenticación:** RADIUS y LDAP
- **Embeddings:** `sentence-transformers` (distiluse-base-multilingual-cased)
- **Scraping:** `BeautifulSoup`, `requests`
- **Infraestructura:** Nginx, systemd

---

## 📂 Estructura del proyecto

```
unachito_chatbot/
├── app/
│   ├── main.py
│   ├── chatbot_routes.py
│   ├── services/
│   │   ├── faq_model.py
│   │   ├── knowledge_search.py
│   │   ├── ldap_service.py
│   │   ├── radius_service.py
│   │   ├── scraping_service.py
│   │   └── unach_client.py
│   └── models/
│       └── unanswered_model.py
├── widget/
│   ├── css/style.css
│   ├── js/chatbot-widget.js
│   └── img/unach-sphere.png
└── README.md
```

---

## ⚙️ Instalación

### 1. Clona el repositorio

```bash
git clone https://github.com/UNACH-DTIC/unachito_chatbot.git
cd unachito_chatbot
```

### 2. Crea entorno virtual e instala dependencias

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configura base de datos

Edita tu archivo `.env` o ajusta directamente en `app/main.py`:

```
DATABASE_URL=mysql://usuario:clave@host:3306/unachito
UNACH_API_BASE=https://api.unach.edu.ec
EMAIL_SMTP_HOST=smtp.unach.edu.ec
EMAIL_SMTP_USER=bot@unach.edu.ec
EMAIL_SMTP_PASS=********
```

### 4. Configura NGINX y systemd

- Copia `unachito.service` a `/etc/systemd/system/`
- Copia `unachito.conf` a `/etc/nginx/conf.d/`
- Reinicia servicios:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now unachito
sudo nginx -s reload
```

### 5. Inicia manualmente en desarrollo

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 Integración como widget

Agrega lo siguiente a tu HTML (WordPress, C#, etc.)

```html
<link rel="stylesheet" href="https://chatbot.unach.edu.ec/widget/css/style.css" />
<script defer src="https://chatbot.unach.edu.ec/widget/js/chatbot-widget.js"></script>
```

---

## 📬 Endpoints principales

| Ruta                        | Método | Función                                  |
|----------------------------|--------|-------------------------------------------|
| `/api/chatbot/enviar_otp` | POST   | Enviar OTP al correo del usuario          |
| `/api/chatbot/verificar_otp` | POST   | Verificar OTP y cambiar contraseña       |
| `/api/chatbot/query`      | POST   | Clasificar y responder preguntas          |
| `/api/chatbot/rate_response` | POST   | Recibir valoración de respuestas         |

---

## 👥 Créditos

Desarrollado por: **Hernán Xavier Abad Hidalgo**  
Maestría en Inteligencia Artificial Aplicada – Universidad de los Hemisferios 

---

## ⚖️ Licencia

Este proyecto está licenciado bajo **GNU AGPL v3**.  
Cualquier modificación que sea desplegada como servicio web debe ser publicada también.

---

📩 Contacto: [habad@unach.edu.ec](mailto:habad@unach.edu.ec)
