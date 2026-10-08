/* =====================================================
   SCRIPT.JS — la electricidad de la página principal
   Acá vive todo lo que pasa cuando tocás botones.
   ===================================================== */

// ---------- ESCALA DE NIVELES (igualita a la de logica.py) ----------
const METAS   = [7, 14, 21, 30, 60, 90, 180, 365];
const NOMBRES = ['Aprendiz', 'Constante', 'Disciplinado', 'Maestro',
                 'Experto', 'Sabio', 'Leyenda en camino', 'Infinito SALEM'];
const EMOJIS  = ['🌱', '', '', '', '🛡️', '🔮', '👑', '♾️'];

// ---------- DATOS QUE EL SERVIDOR DEJÓ ESCRITOS EN EL <body> ----------
const racha = parseInt(document.body.dataset.racha || '0', 10);
const mejor = parseInt(document.body.dataset.mejor || '0', 10);

// ---------- MENSAJITO FLOTANTE (toast) ----------
function avisar(mensaje) {
  const toast = document.getElementById('toast');
  toast.textContent = mensaje;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 3500);
}

// ---------- PINTAR LA ZONA DE RACHA ----------
function pintarRacha() {
  document.getElementById('numero-racha').textContent = racha;
  document.getElementById('mejor-racha').textContent = mejor;

  // Cuántas metas completaste y en qué nivel estás parado
  const completadas = METAS.filter(m => racha >= m).length;
  const nivel = Math.min(completadas + 1, 8);

  document.getElementById('insignia-nivel').textContent =
    'Nivel ' + nivel + ' · ' + NOMBRES[nivel - 1] + ' ' + EMOJIS[nivel - 1];

  const barra = document.getElementById('relleno-progreso');
  const texto = document.getElementById('texto-progreso');

  if (racha >= 365) {
    // Tope máximo: corona y barra llena
    barra.style.width = '100%';
    texto.textContent = '🏆 ¡Meta máxima alcanzada! Sos leyenda viva.';
  } else {
    const meta = METAS[nivel - 1];                 // meta del nivel actual
    const previa = nivel >= 2 ? METAS[nivel - 2] : 0;  // meta del nivel anterior
    const progreso = ((racha - previa) / (meta - previa)) * 100;
    barra.style.width = progreso + '%';
    const faltan = meta - racha;
    texto.textContent =
      'Meta del nivel ' + nivel + ': ' + meta +
      ' días · te faltan ' + faltan + ' 🔥';
  }
}

// ---------- AGREGAR TEMÁTICA ----------
document.getElementById('form-tematica').addEventListener('submit', async (evento) => {
  evento.preventDefault();  // que el formulario no recargue la página a su modo
  const nombre = document.getElementById('nueva-tematica').value.trim();
  const respuesta = await fetch('/api/tematicas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre })
  });
  const datos = await respuesta.json();
  avisar(datos.mensaje);
  if (datos.ok) setTimeout(() => location.reload(), 700);
});

// ---------- DESACTIVAR TEMÁTICA (botones ✖) ----------
document.querySelectorAll('.boton-borrar').forEach(boton => {
  boton.addEventListener('click', async () => {
    if (!confirm('¿Desactivar esta temática? Su historial se conserva.')) return;
    const respuesta = await fetch('/api/tematicas/' + boton.dataset.id, { method: 'DELETE' });
    const datos = await respuesta.json();
    avisar(datos.mensaje);
    setTimeout(() => location.reload(), 700);
  });
});

// ---------- GUARDAR NUEVA ENTRADA ----------
document.getElementById('form-entrada').addEventListener('submit', async (evento) => {
  evento.preventDefault();

  // Juntamos los tipos de estudio tildados
  const tipos = [...document.querySelectorAll('#caja-tipos input:checked')]
    .map(caja => parseInt(caja.value, 10));

  if (tipos.length === 0) {
    avisar('Elegí al menos un tipo de estudio 😉');
    return;
  }

  const carga = {
    tematica_id: parseInt(document.getElementById('entrada-tematica').value, 10),
    descripcion: document.getElementById('entrada-descripcion').value.trim(),
    tipos: tipos,
    resumen: document.getElementById('entrada-resumen').value.trim(),
    observaciones: document.getElementById('entrada-observaciones').value.trim(),
    minutos: parseInt(document.getElementById('entrada-minutos').value) || 0
  };

  const respuesta = await fetch('/api/entradas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(carga)
  });
  const datos = await respuesta.json();
  avisar(datos.mensaje);
  // Recargamos para ver la racha y las entradas de hoy frescas
  setTimeout(() => location.reload(), 900);
});

// ---------- TRAER EL COMPILADO DEL DÍA ----------
async function traerCompilado() {
  const respuesta = await fetch('/api/compilado');
  const datos = await respuesta.json();
  return datos.texto;
}

// Ver / ocultar el compilado en pantalla
document.getElementById('btn-ver-compilado').addEventListener('click', async () => {
  const vista = document.getElementById('vista-compilado');
  if (!vista.hidden) { vista.hidden = true; return; }
  vista.textContent = await traerCompilado();
  vista.hidden = false;
});

// WhatsApp: abre la app con el texto ya escrito (vos elegís el chat)
document.getElementById('btn-whatsapp').addEventListener('click', async () => {
  const texto = await traerCompilado();
  window.open('https://wa.me/?text=' + encodeURIComponent(texto), '_blank');
});

// Email: abre tu app de correo con asunto y cuerpo ya listos
document.getElementById('btn-email').addEventListener('click', async () => {
  const texto = await traerCompilado();
  const hoy = new Date().toLocaleDateString('es-AR');
  location.href = 'mailto:?subject=' +
    encodeURIComponent('Diario de Capacitación — ' + hoy) +
    '&body=' + encodeURIComponent(texto);
});

// GitHub: guarda el compilado del día y sube todo al repositorio
document.getElementById('btn-github').addEventListener('click', async () => {
  const boton = document.getElementById('btn-github');
  boton.disabled = true;
  boton.textContent = '⏳ Subiendo…';
  const respuesta = await fetch('/api/github', { method: 'POST' });
  const datos = await respuesta.json();
  avisar(datos.mensaje);
  boton.disabled = false;
  boton.textContent = '🐙 GitHub';
});

// ---------- ARRANQUE ----------
pintarRacha();

/* =====================================================
   EDITOR INTUITIVO DE RESUMEN
   Los botones no "pintan" el texto: escriben los símbolos
   de Markdown alrededor de lo que tengas seleccionado.
   Así tu resumen queda en Markdown puro y portable.
   ===================================================== */

// Atajo para tomar el campo de resumen
function campoResumen() {
  return document.getElementById('entrada-resumen');
}

// Envuelve la selección con los símbolos que le pases.
// Ejemplo: envolver('**', '**') convierte "hola" en "**hola**"
function envolver(antes, despues) {
  const campo = campoResumen();
  const inicio = campo.selectionStart;
  const fin = campo.selectionEnd;
  const seleccionado = campo.value.slice(inicio, fin) || 'texto';

  campo.value = campo.value.slice(0, inicio) +
                antes + seleccionado + despues +
                campo.value.slice(fin);

  // Dejamos seleccionado lo que acabamos de formatear,
  // para que puedas encadenar botones (negrita + color, etc.)
  campo.focus();
  campo.selectionStart = inicio + antes.length;
  campo.selectionEnd = inicio + antes.length + seleccionado.length;
}

// Tamaños: un span con tamaño de letra (HTML válido dentro de Markdown)
function aplicarTamano(valor) {
  if (!valor) return;
  envolver('<span style="font-size:' + valor + 'em">', '</span>');
}

// Colores: un span con color
function aplicarColor(color) {
  if (!color) return;
  envolver('<span style="color:' + color + '">', '</span>');
}

// Pone un prefijo al inicio de cada línea seleccionada (para listas)
function prefijarLineas(prefijo) {
  const campo = campoResumen();
  const inicio = campo.selectionStart;
  const fin = campo.selectionEnd;
  const seleccionado = campo.value.slice(inicio, fin) || 'ítem';
  const conPrefijo = seleccionado.split('\n')
    .map(linea => prefijo + linea).join('\n');
  campo.value = campo.value.slice(0, inicio) + conPrefijo + campo.value.slice(fin);
  campo.focus();
}

// Lista numerada: 1. , 2. , 3. …
function prefijarLineasNumeradas() {
  const campo = campoResumen();
  const inicio = campo.selectionStart;
  const fin = campo.selectionEnd;
  const seleccionado = campo.value.slice(inicio, fin) || 'ítem';
  const conNumeros = seleccionado.split('\n')
    .map((linea, i) => (i + 1) + '. ' + linea).join('\n');
  campo.value = campo.value.slice(0, inicio) + conNumeros + campo.value.slice(fin);
  campo.focus();
}

// ---------- MINI TRADUCTOR DE MARKDOWN A HTML (vista previa) ----------
function markdownAHtml(md) {
  // 1) Guardamos en un "bolsillo" las etiquetas que SÍ permitimos
  const bolsillo = [];
  let texto = md.replace(
    /<span style="(font-size:[0-9.]+em|color:#[0-9A-Fa-f]{3,6})">|<\/span>|<u>|<\/u>/gi,
    etiqueta => { bolsillo.push(etiqueta); return '\u0000' + (bolsillo.length - 1) + '\u0000'; }
  );

  // 2) Escapamos todo lo demás (seguridad: nada de código ejecutable)
  texto = texto.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // 3) Negrita e itálica
  texto = texto.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  texto = texto.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // 4) Línea por línea: títulos y listas
  const lineas = texto.split('\n');
  let html = '';
  let enLista = '';  // '' | 'ul' | 'ol'

  const cerrarLista = () => { if (enLista) { html += '</' + enLista + '>'; enLista = ''; } };

  for (const linea of lineas) {
    if (/^- /.test(linea)) {
      if (enLista !== 'ul') { cerrarLista(); html += '<ul>'; enLista = 'ul'; }
      html += '<li>' + linea.slice(2) + '</li>';
    } else if (/^\d+\. /.test(linea)) {
      if (enLista !== 'ol') { cerrarLista(); html += '<ol>'; enLista = 'ol'; }
      html += '<li>' + linea.replace(/^\d+\. /, '') + '</li>';
    } else if (/^# /.test(linea)) {
      cerrarLista();
      html += '<h4>' + linea.slice(2) + '</h4>';
    } else {
      cerrarLista();
      html += linea + '<br>';
    }
  }
  cerrarLista();

  // 5) Devolvemos las etiquetas permitidas desde el bolsillo
  html = html.replace(/\u0000(\d+)\u0000/g, (_, i) => bolsillo[parseInt(i, 10)]);
  return html;
}

// Muestra / oculta la vista previa del resumen
function alternarVistaPrevia() {
  const vista = document.getElementById('vista-previa-resumen');
  if (!vista.hidden) { vista.hidden = true; return; }
  vista.innerHTML = markdownAHtml(campoResumen().value);
  vista.hidden = false;
}
