/* =====================================================
   TUTOR.JS — versión mobile-first
   Botones siempre visibles, copiar con plan B para HTTP,
   reutilizar tus inputs, reintentar errores y borrador
   que sobrevive recargas de página.
   ===================================================== */

const lienzo = document.getElementById('lienzo-chat');
const campoChat = document.getElementById('campo-chat');
const usuario = document.body.dataset.usuario || 'Martín';
const CLAVE_BORRADOR = 'tutor_borrador';

// ==================== TOAST ====================
function mostrarToast(mensaje) {
  const toast = document.getElementById('toast');
  toast.textContent = mensaje;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 3000);
}

// ==================== BORRADOR (sobrevive recargas) ====================
// Cada vez que escribís, guardamos el texto en el celular.
// Si recargás la página sin enviar, lo recuperamos solito.
campoChat.addEventListener('input', () => {
  localStorage.setItem(CLAVE_BORRADOR, campoChat.value);
});

function restaurarBorrador() {
  const borrador = localStorage.getItem(CLAVE_BORRADOR) || '';
  if (borrador.trim()) {
    campoChat.value = borrador;
    mostrarToast('✏️ Recuperamos lo que tenías escrito');
  }
}

// ==================== COPIAR (con plan B para HTTP) ====================
// El clipboard moderno solo funciona en HTTPS o localhost.
// Como vos entrás por la WiFi con HTTP, usamos el truco viejo.
function copiarTexto(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(texto)
      .then(() => mostrarToast('📋 Copiado'))
      .catch(() => copiarAlModoViejo(texto));
  } else {
    copiarAlModoViejo(texto);
  }
}

function copiarAlModoViejo(texto) {
  const area = document.createElement('textarea');
  area.value = texto;
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.appendChild(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  area.remove();
  mostrarToast(ok ? '📋 Copiado' : '❌ Tu navegador no dejó copiar');
}

// ==================== BURBUJAS ====================
function botonAccion(icono, titulo, alTocar) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.textContent = icono;
  btn.title = titulo;
  btn.setAttribute('aria-label', titulo);
  btn.onclick = () => alTocar(btn);
  return btn;
}

function burbuja(rol, texto, opciones = {}) {
  const { id = null, favorito = false, pregunta = null } = opciones;
  const div = document.createElement('div');
  div.className = 'burbuja ' + (rol === 'usuario' ? 'burbuja-usuario' : 'burbuja-tutor');
  if (id) div.dataset.id = id;
  if (pregunta) div.dataset.pregunta = pregunta;

  const contenido = document.createElement('div');
  contenido.className = 'burbuja-contenido';
  contenido.textContent = texto;
  div.appendChild(contenido);

  // Botoncitos de acción: SIEMPRE visibles (en el celu no existe el hover)
  const acciones = document.createElement('div');
  acciones.className = 'burbuja-acciones';

  // Copiar este mensaje (usuario y tutor)
  acciones.appendChild(botonAccion('📋', 'Copiar mensaje', () => copiarTexto(texto)));

  if (rol === 'usuario') {
    // ✏️ Devuelve tu mensaje a la cajita: adiós copiar a mano
    acciones.appendChild(botonAccion('✏️', 'Editar o reenviar', () => {
      campoChat.value = texto;
      campoChat.focus();
      mostrarToast('✏️ Mensaje cargado en la cajita');
    }));
  }

  if (rol === 'tutor' && id) {
    // 📄 Copiar el diálogo completo (tu pregunta + su respuesta)
    acciones.appendChild(botonAccion('📄', 'Copiar diálogo', () => {
      const preg = div.dataset.pregunta || '(pregunta no registrada)';
      copiarTexto('👤 ' + usuario + ': ' + preg + '\n\n✨ Sibeli:\n' + texto);
    }));
    // ⭐ Favorito
    const btnFav = botonAccion(favorito ? '⭐' : '☆', 'Favorito',
      (btn) => toggleFavorito(id, btn));
    if (favorito) btnFav.classList.add('activo');
    acciones.appendChild(btnFav);
  }

  div.appendChild(acciones);
  lienzo.appendChild(div);
  lienzo.scrollTop = lienzo.scrollHeight;
  return div;
}

function burbujaPensando() {
  const div = burbuja('tutor', 'escribiendo…');
  div.classList.add('pensando');
  return div;
}

// Burbuja de error con botón 🔄 Reintentar (reenvía tu último mensaje)
function burbujaError(texto, reintentarCon) {
  const div = burbuja('tutor', '😵 ' + texto);
  if (reintentarCon) {
    const acciones = div.querySelector('.burbuja-acciones');
    acciones.appendChild(botonAccion('🔄', 'Reintentar', () => {
      div.remove();
      enviar(reintentarCon);
    }));
  }
  return div;
}

// ==================== HISTORIAL ====================
async function cargarHistorial() {
  try {
    const resp = await fetch('/api/historial');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const datos = await resp.json();
    lienzo.innerHTML = '';

    if (!datos.length) {
      burbuja('tutor',
        'Hola ' + usuario + '. Soy Sibeli, tu tutora personal.\n' +
        'Conozco tu diario de estudio: temáticas, resúmenes, racha y tiempo dedicado.\n' +
        '¿En qué puedo asistirte hoy?');
      return;
    }

    // Recorremos emparejando pregunta → respuesta (para el botón 📄)
    let ultimaPregunta = null;
    datos.forEach(m => {
      if (m.rol === 'usuario') {
        burbuja('usuario', m.mensaje, { id: m.id });
        ultimaPregunta = m.mensaje;
      } else {
        burbuja('tutor', m.mensaje,
          { id: m.id, favorito: !!m.favorito, pregunta: ultimaPregunta });
      }
    });
  } catch (error) {
    lienzo.innerHTML = '';
    burbujaError('No pude cargar el historial: ' + error.message, null);
  }
}

// ==================== ENVIAR ====================
async function enviar(texto) {
  texto = (texto || '').trim();
  if (!texto) return;

  const profundidad = document.getElementById('nivel-profundidad').value;
  burbuja('usuario', texto);
  const pensando = burbujaPensando();

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mensaje: texto, profundidad: profundidad })
    });

    // Si el servidor responde feo (500, 502, lo que sea), lo manejamos acá
    if (!resp.ok) {
      pensando.remove();
      burbujaError('El servidor respondió con error ' + resp.status + '.', texto);
      return;
    }

    const datos = await resp.json();
    pensando.remove();

    if (datos.ok) {
      burbuja('tutor', datos.respuesta, { id: datos.id_mensaje, pregunta: texto });
      localStorage.removeItem(CLAVE_BORRADOR);  // ya enviaste: borrador afuera
      mostrarSugerencias();
    } else {
      burbujaError(datos.mensaje, texto);  // con 🔄 para reintentar
    }
  } catch (error) {
    pensando.remove();
    burbujaError('No pude conectar con el servidor. ¿Está andando?', texto);
  }
}

function enviarAtajo(texto) {
  enviar(texto);
}

document.getElementById('form-chat').addEventListener('submit', (evento) => {
  evento.preventDefault();
  const texto = campoChat.value;
  campoChat.value = '';
  localStorage.removeItem(CLAVE_BORRADOR);
  enviar(texto);
});

// ==================== BÚSQUEDA ====================
function buscarEnChat(texto) {
  texto = texto.toLowerCase().trim();
  const burbujas = lienzo.querySelectorAll('.burbuja');
  if (!texto) {
    burbujas.forEach(b => b.style.display = '');
    return;
  }
  burbujas.forEach(b => {
    const contenido = b.querySelector('.burbuja-contenido').textContent.toLowerCase();
    b.style.display = contenido.includes(texto) ? '' : 'none';
  });
}

// ==================== FAVORITOS ====================
async function toggleFavorito(id, boton) {
  const esFavorito = !boton.classList.contains('activo');
  try {
    const resp = await fetch('/api/chat/favorito/' + id, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ favorito: esFavorito })
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    boton.classList.toggle('activo', esFavorito);
    boton.textContent = esFavorito ? '⭐' : '☆';
    mostrarToast(esFavorito ? '⭐ Marcado como favorito' : '☆ Quitado de favoritos');
  } catch (error) {
    mostrarToast('❌ No se pudo marcar el favorito');
  }
}

// ==================== EXPORTAR Y BORRAR ====================
async function exportarChat() {
  try {
    const resp = await fetch('/api/chat/exportar');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const datos = await resp.json();

    const blob = new Blob([datos.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chat_tutor_' + new Date().toISOString().split('T')[0] + '.md';
    a.click();
    URL.revokeObjectURL(url);
    mostrarToast('💾 Chat exportado');
  } catch (error) {
    mostrarToast('❌ Error al exportar: ' + error.message);
  }
}

async function borrarChat() {
  if (!confirm('¿Borrar todo el historial del chat? No se puede deshacer.')) return;
  try {
    const resp = await fetch('/api/chat/borrar', { method: 'POST' });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    lienzo.innerHTML = '';
    cargarHistorial();
    mostrarToast('🗑️ Historial borrado');
  } catch (error) {
    mostrarToast('❌ Error al borrar: ' + error.message);
  }
}

// ==================== SUGERENCIAS ====================
async function mostrarSugerencias() {
  const contenedor = document.getElementById('sugerencias-seguimiento');
  const botones = document.getElementById('sugerencias-botones');
  if (!contenedor || !botones) return;
  try {
    const resp = await fetch('/api/chat/sugerencias');
    if (!resp.ok) return;
    const sugerencias = await resp.json();
    botones.innerHTML = '';
    sugerencias.forEach(s => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'boton-chip';
      btn.textContent = s;
      btn.onclick = () => enviar(s);
      botones.appendChild(btn);
    });
    contenedor.hidden = false;
  } catch (error) {
    console.error('Sugerencias no disponibles:', error);
  }
}

// ==================== ARRANQUE ====================
cargarHistorial();
restaurarBorrador();
