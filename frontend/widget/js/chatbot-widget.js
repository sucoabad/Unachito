(function () {
  'use strict';

  const API_BASE = 'https://chatbot.unach.edu.ec/api/chatbot';

  let estadoFlujo = null;
  let datosReset = {};
  let userName = null;

  // Crear dinámicamente el popup si no existe (modo auto)
  if (!document.getElementById('chatbot-popup')) {
    const popup = document.createElement('div');
    popup.id = 'chatbot-popup';
    popup.className = 'hidden';
    popup.innerHTML = `
      <div id="chatbot-header" title="Asistente virtual de la Universidad Nacional de Chimborazo">
        <img id="chatbot-logo" src="https://dtic.unach.edu.ec/wp-content/uploads/2025/05/unach.png" alt="Logo UNACH" style="width: 30px; height: 30px; margin-right: 10px;">
        <strong>Unachito – UNACH</strong>
      </div>
      <div id="chatbot-messages"></div>
      <div id="chatbot-input">
        <input type="text" id="user-input" placeholder="Escribe tu pregunta aquí…" />
        <button id="send-button">▶</button>
      </div>
    `;
    document.body.appendChild(popup);
  }

  const chatbotButton = document.getElementById('chatbot-button');
  const chatbotPopup = document.getElementById('chatbot-popup');
  const sendButton = document.getElementById('send-button');
  const userInput = document.getElementById('user-input');
  const messagesContainer = document.getElementById('chatbot-messages');

  if (!chatbotButton || !chatbotPopup || !sendButton || !userInput || !messagesContainer) {
    console.error('⚠️ No se encontraron los elementos del chatbot.');
    return;
  }

//  chatbotButton.addEventListener('click', () => chatbotPopup.classList.toggle('hidden'));
  
  chatbotButton.addEventListener('click', () => {
    chatbotPopup.classList.toggle('hidden');
  
    // Animación en el ícono al abrir el chatbot
    const logo = document.getElementById('chatbot-logo');
    if (logo) {
      logo.style.transition = 'transform 0.3s ease';
      logo.style.transform = 'scale(1.2)';
      setTimeout(() => {
        logo.style.transform = 'scale(1)';
      }, 300);
    }
  });
	
	
  sendButton.addEventListener('click', handleUserInput);
  userInput.addEventListener('keypress', e => { if (e.key === 'Enter') handleUserInput(); });

  // 👂 Entrada principal del usuario
  async function handleUserInput() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage('Tú', text);
    userInput.value = '';

    const lower = text.toLowerCase();

    // 🪪 Flujo de cambio de contraseña
    if (estadoFlujo === 'esperando_cedula') return handleCedula(text);
    if (estadoFlujo === 'esperando_cedula_zoom') return handleCedulaZoom(text);
    if (estadoFlujo === 'esperando_otp_zoom') return handleOtpZoom(text);
    if (estadoFlujo === 'esperando_nueva_contrasena_zoom') return handleNuevaContrasenaZoom(text);
    if (estadoFlujo === 'esperando_otp') return handleOtp(text);
    if (estadoFlujo === 'esperando_nueva_contrasena') return handleNuevaContrasena(text);

    // 💬 Si estamos esperando nombre (después de saludo del backend)
    if (estadoFlujo === 'esperando_nombre') {
      const name = extractName(text);
      if (name) {
        userName = name;
        estadoFlujo = null;
        appendMessage('Chatbot', `¡Mucho gusto, ${userName}! 😊 ¿En qué puedo ayudarte hoy?`);
        return;
      }
    }

    // 🔁 Envío normal al backend
    await fetchChatbotResponse(text);
  }

  // 🌐 Consulta al backend
async function fetchChatbotResponse(question) {
  try {
    // Primero hacemos el fetch al backend
    const res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pregunta: question })
    });

    const data = await res.json();
    const respuesta = data.respuesta || 'Lo siento, hubo un problema.';
    const fuente = data.fuente ? `<br><small>🔎 Fuente: ${data.fuente}</small>` : '';
    const botonesHTML = generateActions(data.acciones);

    // Si es saludo, NO mostrar cargando y activar captura de nombre
    if (data.fuente === 'Saludo') {
      estadoFlujo = 'esperando_nombre';
      appendMessage("Chatbot", `${respuesta}${fuente}`, botonesHTML);
      return;
    }

    // Si es manejo especial, tampoco mostrar cargando
    if (data.fuente === 'Manejo especial') {
      appendMessage("Chatbot", `${respuesta}${fuente}`, botonesHTML);
      return;
    }

    // Solo aquí mostrar mensaje "⌛ Estoy buscando..."
    const msgId = `loading-msg-${Date.now()}`;
    const loadingDiv = document.createElement('div');
    loadingDiv.id = msgId;
    loadingDiv.className = 'message bot loading';
    loadingDiv.innerHTML = '<strong>Chatbot:</strong> ⌛ Estoy buscando en los sitios de la UNACH. Un momento por favor...';
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Simula una pequeña espera (puedes quitar si no deseas)
    await new Promise(resolve => setTimeout(resolve, 200));

    // Elimina mensaje de espera y muestra respuesta final
    const loading = document.getElementById(msgId);
    if (loading) loading.remove();

    appendMessage("Chatbot", `${respuesta}${fuente}`, botonesHTML);

  } catch (err) {
    console.error('[ERROR] Fetch chatbot:', err);

    // Quitar mensaje loading si hubo error
    const loading = document.querySelector('.message.bot.loading');
    if (loading) loading.remove();

    appendMessage("Chatbot", "❗ Error de conexión con el servidor.");
  }
}


  // 🧩 Botones adicionales (wifi, moodle, etc.)
  function generateActions(actions = []) {
    if (!actions.length) return '';
    let html = '<div class="bot-options" style="margin-top:10px;">';
    actions.forEach(act => {
      html += `<button class="option-btn ${act}" data-option="${act}">${act}</button>`;
    });
    return html + '</div>';
  }

  document.addEventListener('click', event => {
    const button = event.target.closest('.option-btn');
    if (!button) return;

    const option = button.getAttribute('data-option');
    switch (option) {
      case 'wifi':
        appendMessage('Chatbot', '¿Eres estudiante?', `
          <div class="bot-options" style="margin-top:10px;">
            <button class="option-btn grupo-estudiante" data-option="grupo-estudiante">✅ Estudiante</button>
            <button class="option-btn grupo-docente" data-option="grupo-docente">❌ Docente/Administrativo</button>
          </div>`);
        break;
      case 'grupo-estudiante':
      case 'grupo-docente':
        datosReset.grupo = option === 'grupo-estudiante' ? 'estudiantes' : 'docentes';
        appendMessage('Chatbot', `✅ Seleccionado: ${option === 'grupo-estudiante' ? 'Estudiante' : 'Docente/Administrativo'}. Ingresa tu cédula.`);
        estadoFlujo = 'esperando_cedula';
        break;
      case 'office365':
        appendMessage('Chatbot', `Puedes restablecer tu contraseña de Office 365 accediendo a <a href="https://passwordreset.microsoftonline.com/" target="_blank" style="color: #005baa; font-weight: bold;">este enlace</a>. 
    Si necesitas ayuda adicional, también puedes ingresar a <a href="https://portal.office.com" target="_blank" style="color: #005baa; font-weight: bold;">portal.office.com</a> y seguir las instrucciones de recuperación.`
  );
	break;
      case 'moodle':
	appendMessage('Chatbot',  "Para cambiar tu contraseña de Moodle, accede al portal y usa <a href='https://moodle.unach.edu.ec/login/forgot_password.php' target='_blank' style='color: #005baa; font-weight: bold;'>¿Olvidaste tu contraseña?</a>.");
        break;
      case 'zoom':
	appendMessage('Chatbot', 'Por favor, ingresa tu cédula para iniciar el proceso de cambio de contraseña de Zoom.');
	estadoFlujo = 'esperando_cedula_zoom';
	break;
    }
  }) ;

// SECCION ZOOM - LDAP
	

async function handleCedulaZoom(cedula) {
  datosReset.cedula = cedula;
  datosReset.servicio = 'zoom'; // 👈 IMPORTANTE para distinguir el tipo

  appendMessage('Chatbot', 'Enviando OTP para restablecer contraseña de Zoom...');

  try {
    const response = await post(`${API_BASE}/enviar_otp`, { cedula });

    if (response.status === 'success') {
      appendMessage('Chatbot', `✅ ${response.message} Ingresa el código OTP que llegó a tu correo institucional.`);
      estadoFlujo = 'esperando_otp';
    } else {
      appendMessage('Chatbot', `❗ Error: ${response.detail || 'No se pudo enviar OTP.'}`);
      estadoFlujo = null;
    }
  } catch (err) {
    appendMessage('Chatbot', '❗ Error de conexión al enviar OTP.');
    estadoFlujo = null;
  }
}


//SECCION WIFI - RADIUS
  // 🔐 Flujo OTP
  async function handleCedula(cedula) {
    datosReset.cedula = cedula;
    appendMessage('Chatbot', `${userName ? `${userName}, ` : ''}enviando OTP...`);

    try {
      const response = await post(`${API_BASE}/enviar_otp`, { cedula });
      if (response.status === 'success') {
        appendMessage('Chatbot', `✅ ${response.message} Ingresa el código OTP.`);
        estadoFlujo = 'esperando_otp';
      } else {
        appendMessage('Chatbot', `❗ Error: ${response.detail || 'No se pudo enviar OTP.'}`);
        estadoFlujo = null;
      }
    } catch (err) {
      appendMessage('Chatbot', '❗ Error de conexión al enviar OTP.');
      estadoFlujo = null;
    }
  }

  async function handleOtp(otp) {
    datosReset.otp = otp;
    appendMessage('Chatbot', 'Verificando OTP...');

    try {
      const response = await post(`${API_BASE}/verificar_otp`, {
        cedula: datosReset.cedula,
        otp
      });

      if (response.status === 'success') {
        appendMessage('Chatbot', `✅ OTP verificado. Ingresa tu nueva contraseña.`);
        estadoFlujo = 'esperando_nueva_contrasena';
      } else {
        appendMessage('Chatbot', `❗ Error: ${response.detail}`);
        estadoFlujo = null;
      }
    } catch (err) {
      appendMessage('Chatbot', '❗ Error verificando OTP.');
      estadoFlujo = null;
    }
  }


  async function handleNuevaContrasena(password) {
    datosReset.new_password = password;
    appendMessage('Chatbot', 'Actualizando contraseña...');
  
    const endpoint = datosReset.servicio === 'zoom'
      ? `${API_BASE}/reset_zoom_password`
      : `${API_BASE}/reset_radius_password`;
  
    try {
      const response = await post(endpoint, {
        username: datosReset.cedula,
        confirm_data: datosReset.otp,
        new_password: password,
        grupo: datosReset.grupo || 'estudiantes'
      });
  
      if (response.status === 'success') {
        appendMessage('Chatbot', `✅ ¡Listo${userName ? `, ${userName}` : ''}! ${response.message}`);
      } else {
        appendMessage('Chatbot', `❗ Error: ${response.detail}`);
      }
    } catch (err) {
      appendMessage('Chatbot', '❗ Error al cambiar la contraseña.');
    } finally {
      estadoFlujo = null;
      datosReset = {};
    }
  }



  // 🧠 Detección y capitalización de nombre
  function extractName(text) {
    const blacklist = ['hola', 'buenos', 'días', 'dias', 'tardes', 'noches', 'saludos', 'hello', 'hi'];
    const patterns = [
      /me llamo\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)/i,
      /soy\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)/i,
      /mi nombre es\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)/i
    ];
    for (const regex of patterns) {
      const match = text.match(regex);
      if (match && !blacklist.includes(match[1].toLowerCase())) {
        return capitalize(match[1]);
      }
    }
    const words = text.split(/\s+/);
    if (
      words.length === 1 &&
      /^[A-Za-zÁÉÍÓÚáéíóúñÑ]+$/.test(words[0]) &&
      !blacklist.includes(words[0].toLowerCase())
    ) {
      return capitalize(words[0]);
    }
    return null;
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }

  // 🧾 Función POST genérica
  async function post(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return res.json();
  }

  // 📥 Mostrar mensaje en el DOM
  function appendMessage(sender, text, extraHTML = '') {
    const msg = document.createElement('div');
    msg.classList.add('message', sender === 'Tú' ? 'user' : 'bot');
    msg.innerHTML = `<div><strong>${sender}:</strong> ${text}</div>${extraHTML}`;
    messagesContainer.appendChild(msg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
})();

