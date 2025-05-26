// chatbot-widget.js
// const API_BASE = 'https://chatbot.unach.edu.ec/api/chatbot';
(function () {
  'use strict';

  const API_BASE = 'http://localhost:8000/api/chatbot';

  // ─────────────────────────────────────────────────────────────────────────────
  // 🌟 Estado global
  const state = {
    consent: false, //consent: localStorage.getItem('chatbotConsent') === 'true',
    flujo: null,         // 'tipo' | 'cedula' | 'nombreExt' | 'servicio' | 'otp' | 'pass'
    tipoUsuario: null,   // 'estudiante' | 'servidor' | 'externo'
    servicio: null,      // 'wifi' | 'zoom'
    datos: {},            // { cedula, nombre, otp, grupo }
    intentosCedula: 0,   // ← contador de intentos para la cédula
    intentosOtp: 0,
    otpExpiry: null
  };

  // 1) Crear/reusar popup *sin* hidden
  let popup = document.getElementById('chatbot-popup');
  if (!popup) {
    popup = document.createElement('div');
    popup.id = 'chatbot-popup';
    popup.classList.add('hidden');  
    document.body.appendChild(popup);
  }

  console.log('state.consent:', state.consent);

  // 2) Inyectar siempre mismo HTML (consent + chat)
  popup.innerHTML = `
    <!-- Consentimiento -->
    <div id="chatbot-consent" class="${state.consent ? 'hidden':''}">
      <h3>Política de Protección de Datos Personales</h3>
      <p>
        En cumplimiento de lo dispuesto en el Acuerdo No. 012-2019, emitido por el Ministerio de Telecomunicaciones y de la Sociedad de la información, comunicamos nuestra política para el tratamiento de datos personales. Para continuar navegando en este sitio debe aceptar los términos de la misma.
        Consulta la  
        <a href="https://www.unach.edu.ec/politica-de-proteccion-de-datos-personales/" target="_blank">
          Política de Protección de Datos Personales
        </a>.
      </p>
      <label><input type="checkbox" id="consent-checkbox"/> Acepto la política</label>
      <button id="consent-button" disabled>Aceptar y continuar</button>
    </div>
    <!-- Chat (oculto hasta aceptar) -->
    <div id="chatbot-chat" class="${state.consent ? '':'hidden'}">
      <div id="chatbot-header">
        <img id="chatbot-logo" src="https://dtic.unach.edu.ec/wp-content/uploads/2025/05/unach.png" alt="Logo UNACH">
        <strong>Unachito</strong>
      </div>
      <div id="chatbot-messages"></div>
        <div id="chatbot-input">
          <input type="text" id="user-input" placeholder="Escribe aquí…" autocomplete="off"/>
          <button id="send-button">▶</button>
        </div>

        <!-- NUEVO PIE DE PÁGINA -->
        <div id="chatbot-footer">
          Desarrollado por HXAH
        </div>
    </div>
  `;

  // 3) Crear / reusar botón flotante
  let btnToggle = document.getElementById('chatbot-button');
  if (!btnToggle) {
    btnToggle = document.createElement('button');
    btnToggle.id = 'chatbot-button';
    btnToggle.textContent = '💬';
    document.body.appendChild(btnToggle);
  }

  // 4) Capturar **todas** las referencias que vas a usar:
  const consentBox  = popup.querySelector('#chatbot-consent');
  const consentBtn  = popup.querySelector('#consent-button');
  const chatBox     = popup.querySelector('#chatbot-chat');
  const chkBox      = popup.querySelector('#consent-checkbox');
  const btnSend     = popup.querySelector('#send-button');
  const inputField  = popup.querySelector('#user-input');
  const messageBox  = popup.querySelector('#chatbot-messages');

  if (![btnToggle, consentBox, consentBtn, chatBox, chkBox, btnSend, inputField, messageBox]
      .every(el => el)) {
    console.error('Chatbot: faltan elementos del DOM');
    return;
  }

  // 5) Bloquear inputs hasta consentimiento
  function toggleChatElements(on) {
    popup.querySelectorAll(
      '#chatbot-input input, #chatbot-input button, .option-btn'
    ).forEach(el => {
      el.disabled = !on;
      el.style.pointerEvents = on ? 'auto' : 'none';
      el.style.opacity       = on ? '1' : '0.5';
    });
  }
  toggleChatElements(state.consent);

  // 6) Checkbox → habilita “Aceptar”
  chkBox.addEventListener('change', () => {
    consentBtn.disabled = !chkBox.checked;
  });

  // 7) Al aceptar la política
  consentBtn.addEventListener('click', () => {
    state.consent = true;
    //localStorage.setItem('chatbotConsent','true');
    consentBox.classList.add('hidden');
    chatBox.classList.remove('hidden');
    toggleChatElements(true);
    iniciarChat();    // saludo inicial
  });

  // 8) Toggle popup
  btnToggle.addEventListener('click', () => {
    // antes, restablezco qué bloque debe verse
    if (!state.consent) {
      consentBox.classList.remove('hidden');
      chatBox.classList.add('hidden');
    } else {
      consentBox.classList.add('hidden');
      chatBox.classList.remove('hidden');
    }
    popup.classList.toggle('hidden');
    animateLogo();
  });

  // 9) Eventos de envío de mensajes
  btnSend.addEventListener('click', handleInput);
  inputField.addEventListener('keypress', e => {
    if (e.key === 'Enter') handleInput();
  });

  // — Función inicial de saludo —
  function iniciarChat() {
    state.flujo = 'tipo';
    appendBot(
      '👋 <strong>¡Hola! Soy Unachito</strong>.<br>😊 ¿Eres Estudiante, Servidor o Externo?',
      ['Estudiante','Servidor','Externo']
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ✉️ Eventos de entrada
  btnSend.addEventListener('click', handleInput);
  inputField.addEventListener('keypress', e => {
    if (e.key === 'Enter') handleInput();
  });

  // ─────────────────────────────────────────────────────────────────────────────
  // 💬 Handler general
  function handleInput() {
    const texto = inputField.value.trim();
    if (!texto) return;
    appendUser(texto);
    inputField.value = '';

    switch (state.flujo) {
      case 'tipo':       return seleccionarTipo(texto);
      case 'cedula':     return ingresarCedula(texto);
      case 'nombreExt':  return ingresarNombreExterno(texto);
      case 'servicio':   return seleccionarServicio(texto);
      case 'otp':        return ingresarOtp(texto);
      case 'pass':       return ingresarNuevaPass(texto);
      default:           return buscarRespuesta(texto);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 1️⃣ Seleccionar tipo de usuario
  function seleccionarTipo(text) {
    const t = text.toLowerCase();
    if (!['estudiante','servidor','externo'].includes(t)) {
      return appendBot(
        '❓ Selecciona una opción válida:',
        ['Estudiante', 'Servidor', 'Externo']
      );
    }
    state.tipoUsuario = t;
    if (t === 'externo') {
      state.flujo = 'nombreExt';
      appendBot('👍 ¡Genial! ¿Cómo te llamas?');
    } else {
      state.flujo = 'cedula';
      appendBot('🪪 Por favor ingresa tu cédula (8–10 dígitos):');
    }
  }

  // 2️⃣ Ingresar cédula y obtener nombre

  function ingresarCedula(text) {
    const ced = text.trim();

    // 1️⃣ Validación de formato
    if (!/^[0-9]{8,10}$/.test(ced)) {
      state.intentosCedula = (state.intentosCedula || 0) + 1;
      const restantes = 3 - state.intentosCedula;
      if (restantes > 0) {
        return appendBot(
          `❗ Formato incorrecto. Usa 8–10 dígitos numéricos.` +
          `\nIntentos restantes: ${restantes}.`
        );
      }
      // agotó intentos → reset y volver al inicio
      state.intentosCedula = 0;
      state.flujo = 'tipo';
      return appendBot(
        '❗ Demasiados intentos inválidos de cédula. Volvamos al inicio.<br>' +
        '¿Eres Estudiante, Servidor o Externo?',
        ['Estudiante','Servidor','Externo']
      );
    }

    // 2️⃣ Formato OK: reset contador y petición al backend
    state.intentosCedula = 0;
    state.datos.cedula = ced;
    appendBot('🔎 Consultando tus datos…');

    post('/get_user_info', { cedula: ced, user_type: state.tipoUsuario })
      .then(res => {
        if (res.error) {
          // usuario no existe → reintentar
          state.intentosCedula++;
          const restantes = 3 - state.intentosCedula;
          if (restantes > 0) {
            state.flujo = 'cedula';
            return appendBot(
              `❗ ${res.error}. Por favor, inténtalo de nuevo.` +
              `\nIntentos restantes: ${restantes}.`
            );
          }
          // agotó intentos → reset y volver al inicio
          state.intentosCedula = 0;
          state.flujo = 'tipo';
          return appendBot(
            `❗ Usuario no encontrado tras varios intentos. Volvamos al inicio.<br>` +
            `¿Eres Estudiante, Servidor o Externo?`,
            ['Estudiante','Servidor','Externo']
          );
        }
        // encontrado → saludo y menú de servicios
        state.intentosCedula = 0;
        state.datos.nombre = res.nombre;
        state.flujo = 'servicio';
        appendBot(
          `👋 ¡Hola, <strong>${res.nombre}</strong>! ¿Qué necesitas hoy?`,
          ['WiFi','Zoom','FAQs']
        );
      })
      .catch(() => {
        // error de red → permitimos reintento
        state.flujo = 'cedula';
        appendBot(
          '❗ Hubo un error al contactar al servidor. ' +
          'Por favor, ingresa tu cédula de nuevo.'
        );
      });
  }


  // 3️⃣ Ingresar nombre para usuario externo
  function ingresarNombreExterno(text) {
    state.datos.nombre = text;
    state.flujo = null;
    appendBot(
      `🙂 ¡Un placer, <strong>${text}</strong>! Puedes preguntarme cualquier FAQ.`,
      []
    );
  }

  // 4️⃣ Seleccionar servicio o FAQs
  function seleccionarServicio(text) {
    const svc = text.toLowerCase();

    // 1️⃣ Validación de opción
    if (!['wifi','zoom','faqs'].includes(svc)) {
      return appendBot(
        '❓ Por favor, elige una opción válida:',
        ['WiFi','Zoom','FAQs']
      );
    }

    // 2️⃣ Opción FAQs pura
    if (svc === 'faqs') {
      state.flujo = null;
      return appendBot('📚 ¡Claro! Pregúntame cualquier cosa sobre nuestras FAQs.');
    }

    // 3️⃣ Preparamos datos para el OTP
    state.servicio = svc;
    state.datos.grupo = state.tipoUsuario === 'estudiante' ? 'estudiantes' : 'servidores';
    state.flujo = 'otp';

    // 4️⃣ Verificamos la cuenta
    appendBot(`⏳ Verificando tu cuenta para <strong>${svc.toUpperCase()}</strong>…`);
    post('/check_account', {
      cedula:     state.datos.cedula,
      user_type:  state.tipoUsuario,
      servicio:   svc
    })
    .then(res => {
      if (!res.exists) {
        // si no existe, salimos del flujo de OTP
        state.flujo = null;
        return appendBot(`❗ No encontramos tu cuenta de <strong>${svc.toUpperCase()}</strong>.`);
      }
      // si existe, solicitamos envío de OTP y devolvemos esa promesa
      return post('/enviar_otp', {
        cedula:     state.datos.cedula,
        user_type:  state.tipoUsuario,
        servicio:   svc
      });
    })
    .then(res2 => {
      // si viene undefined (por no existir cuenta), terminamos
      if (!res2) return;

      // Aquí guardamos el timestamp de expiración (ahora + 10 minutos)
      state.otpExpiry = Date.now() + 10 * 60 * 1000;

      // Mostrar al usuario a qué correo llegó el OTP
      appendBot(`✅ ${res2.message}`);
      appendBot('✉️ Por favor, pega o ingresa aquí tu código OTP:');
    })
    .catch(() => {
      state.flujo = null;
      appendBot('❗ Ocurrió un problema. Por favor, inténtalo de nuevo más tarde.');
    });
  }


  // 5️⃣ Ingresar y verificar OTP
  function ingresarOtp(text) {
    const now = Date.now();
    const diffMs = (state.otpExpiry || 0) - now;

    // 1) Si ya expiró, abortamos
    if (diffMs <= 0) {
      state.flujo = 'servicio';
      appendBot(
        '⌛ Lo siento, tu código OTP ha expirado. ' +
        'Por favor, vuelve a solicitar uno nuevo.',
        ['WiFi','Zoom','FAQs']
      );
      return;
    }

    // 2) Si sigue válido, mostramos el tiempo restante
    const minutos = Math.floor(diffMs / 60000);
    const segundos = Math.floor((diffMs % 60000) / 1000);
    appendBot(
      `⏳ Te quedan ${minutos} min ${segundos} seg para ingresar el OTP…`
    );

    // 3) Procedemos a verificar
    state.datos.otp = text.trim();
    state.intentosOtp = (state.intentosOtp || 0) + 1;

    post('/verificar_otp', {
      cedula: state.datos.cedula,
      otp:    state.datos.otp
    })
    .then(res => {
      if (res.status === 'success') {
        state.intentosOtp = 0;
        state.flujo = 'pass';
        appendBot('✅ OTP correcto. Ahora ingresa tu nueva contraseña:');
      } else {
        const restantes = 3 - state.intentosOtp;
        if (restantes > 0) {
          state.flujo = 'otp';
          appendBot(
            `❗ OTP inválido. Te quedan ${restantes} intento${restantes > 1 ? 's' : ''}.`
          );
        } else {
          state.flujo = 'servicio';
          state.intentosOtp = 0;
          appendBot(
            '❗ Has agotado los intentos. Volvemos al menú de servicios:',
            ['WiFi','Zoom','FAQs']
          );
        }
      }
    })
    .catch(() => {
      appendBot('❗ Error al verificar OTP. Intenta de nuevo.');
      state.flujo = 'otp';
    });
  }


  // 6️⃣ Ingresar nueva contraseña
  function ingresarNuevaPass(text) {
    appendBot('🔄 Actualizando tu contraseña…');
    const endpoint = state.servicio === 'zoom'
      ? '/reset_zoom_password'
      : '/reset_radius_password';

    post(endpoint, {
      username: state.datos.cedula,
      confirm_data: state.datos.otp,
      new_password: text,
      grupo: state.datos.grupo
    })
    .then(res => {
      appendBot(
        `🎉 ¡Listo! Tu contraseña de <strong>${state.servicio.toUpperCase()}</strong> ha sido actualizada.`,
        ['WiFi','Zoom','FAQs','No, gracias']
      );
      state.flujo = 'servicio';
    })
    .catch(() => {
      state.flujo = null;
      appendBot('❗ No pude actualizar la contraseña. Intenta de nuevo.');
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 🌐 Flujo FAQ / búsqueda semántica
  async function buscarRespuesta(text) {
    appendBot('⌛ Buscando la mejor respuesta…');
    try {
      const { fuente, respuesta, acciones=[] } = await post('/query', { pregunta: text });
      removeLoading();
      appendBot(respuesta, acciones);
      if (fuente === 'Saludo')       state.flujo = 'tipo';
      else if (fuente === 'Manejo especial') state.flujo = 'servicio';
      else                              state.flujo = null;
    } catch {
      removeLoading();
      appendBot('❗ Error de conexión con el servidor.');
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 🎨 Utilidades de UI
  function appendBot(html, opciones = []) {
    const msg = document.createElement('div');
    msg.className = 'message bot';
    msg.innerHTML = `<strong>Chatbot:</strong> ${html}${renderButtons(opciones)}`;
    messageBox.appendChild(msg);
    // scroll sólo dentro de #chatbot-messages
    messageBox.scrollTop = messageBox.scrollHeight;
  }

  function appendUser(text) {
    const msg = document.createElement('div');
    msg.className = 'message user';
    msg.innerHTML = `<strong>Tú:</strong> ${text}`;
    messageBox.appendChild(msg);
    // scroll sólo dentro de #chatbot-messages
    messageBox.scrollTop = messageBox.scrollHeight;
  }


  function renderButtons(list) {
    if (!list.length) return '';
    return `<div class="bot-options">` +
      list.map(opt =>
        `<button class="option-btn" data-opt="${opt}">${opt}</button>`
      ).join('') +
      `</div>`;
  }

  function removeLoading() {
    const last = messageBox.querySelector('.message.bot:last-child');
    if (last && /⌛/.test(last.textContent)) last.remove();
  }

  function animateLogo() {
    const logo = document.getElementById('chatbot-logo');
    logo?.classList.add('pop');
    setTimeout(() => logo?.classList.remove('pop'), 300);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // 🔘 Delegación de clicks en botones de acción
  document.addEventListener('click', e => {
    const btn = e.target.closest('.option-btn');
    if (!btn) return;
    const opt = btn.dataset.opt;
    switch (state.flujo) {
      case 'tipo':       return seleccionarTipo(opt);
      case 'servicio':   return seleccionarServicio(opt);
      case 'otp':        return ingresarOtp(opt);
      case 'pass':       return ingresarNuevaPass(opt);
      default:
        if (opt === 'No, gracias') {
          appendBot('👍 ¡Perfecto! Si necesitas algo más, aquí estaré.');
          state.flujo = null;
        }
        if (opt === 'Mostrar FAQs') {
          appendBot('📚 Adelante, haz tu consulta sobre FAQs.');
          state.flujo = null;
        }
    }
  });

  // ─────────────────────────────────────────────────────────────────────────────
  // 📡 Helper para POST
  async function post(path, body) {
    const res = await fetch(API_BASE + path, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body)
    });
    return res.json();
  }

})();
