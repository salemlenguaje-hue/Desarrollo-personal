/* =====================================================
   CONFIG.JS — La electricidad del panel de administración
   ===================================================== */

function avisar(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('visible');
  setTimeout(() => t.classList.remove('visible'), 3000);
}

// ---------- CARGAR Y PINTAR TEMÁTICAS ----------
async function cargarTematicas() {
  const resp = await fetch('/api/tematicas');
  const datos = await resp.json();
  const lista = document.getElementById('lista-tematicas');
  lista.innerHTML = '';
  
  datos.forEach(t => {
    const li = document.createElement('li');
    li.innerHTML = `
      <input type="text" value="${t.nombre}" class="input-edit" data-id="${t.id}" data-tipo="tematica">
      <button class="boton-chico boton-guardar" onclick="guardarCambio(this, 'tematica')">💾</button>
    `;
    lista.appendChild(li);
  });
}

// ---------- CARGAR Y PINTAR TIPOS ----------
async function cargarTipos() {
  const resp = await fetch('/api/config/tipos');
  const datos = await resp.json();
  const lista = document.getElementById('lista-tipos');
  lista.innerHTML = '';
  
  datos.forEach(t => {
    const li = document.createElement('li');
    li.innerHTML = `
      <input type="text" value="${t.nombre}" class="input-edit" data-id="${t.id}" data-tipo="tipo">
      <button class="boton-chico boton-guardar" onclick="guardarCambio(this, 'tipo')">💾</button>
      <button class="boton-chico boton-borrar" onclick="borrarTipo(${t.id})">🗑️</button>
    `;
    lista.appendChild(li);
  });
}

// ---------- GUARDAR CAMBIOS DE NOMBRE ----------
async function guardarCambio(boton, tipo) {
  const input = boton.previousElementSibling;
  const id = input.dataset.id;
  const nuevoNombre = input.value.trim();
  
  if (!nuevoNombre) return avisar('El nombre no puede estar vacío');

  const url = tipo === 'tematica' 
    ? `/api/config/tematicas/${id}` 
    : `/api/config/tipos/${id}`;

  const resp = await fetch(url, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({nombre: nuevoNombre})
  });
  const datos = await resp.json();
  avisar(datos.mensaje);
}

// ---------- AGREGAR TIPO NUEVO ----------
document.getElementById('form-nuevo-tipo').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('nuevo-tipo-nombre');
  const resp = await fetch('/api/config/tipos', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({nombre: input.value})
  });
  const datos = await resp.json();
  avisar(datos.mensaje);
  if (datos.ok) {
    input.value = '';
    cargarTipos();
  }
});

// ---------- BORRAR TIPO ----------
async function borrarTipo(id) {
  if (!confirm('¿Borrar este tipo? Se desvinculará de las entradas pasadas (la entrada no se borra, solo pierde esta etiqueta).')) return;
  const resp = await fetch(`/api/config/tipos/${id}`, {method: 'DELETE'});
  const datos = await resp.json();
  avisar(datos.mensaje);
  cargarTipos();
}

// ---------- CARGAR TABLA CRUDA (AUDITORÍA) ----------
async function cargarEntradasCrudas() {
  const resp = await fetch('/api/config/entradas_crudas');
  const datos = await resp.json();
  const tbody = document.querySelector('#tabla-entradas tbody');
  tbody.innerHTML = '';
  
  datos.forEach(e => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${e.id}</td>
      <td>${e.fecha}</td>
      <td>${e.tematica}</td>
      <td>${e.minutos || 0}</td>
      <td class="hash-cell" title="Hash completo: ${e.hash}">${e.hash ? e.hash.substring(0, 8) + '...' : 'N/A'}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ¡Arrancamos!
cargarTematicas();
cargarTipos();
cargarEntradasCrudas();

/* =====================================================
   GESTIÓN DE CHARLAS CON SIBELI
   ===================================================== */
let chatsCache = [];

async function cargarChats() {
  const resp = await fetch('/api/config/chats');
  chatsCache = await resp.json();
  pintarChats(chatsCache);
}

function pintarChats(lista) {
  const ul = document.getElementById('lista-chats');
  ul.innerHTML = '';
  if (!lista.length) {
    ul.innerHTML = '<li class="ayuda">No hay charlas guardadas todavía.</li>';
    return;
  }
  // Las más recientes primero
  lista.slice().reverse().forEach(m => {
    const li = document.createElement('li');
    li.className = 'item-chat';
    const icono = m.rol === 'usuario' ? '👤' : '✨';
    const texto = document.createElement('span');
    texto.className = 'chat-resumen';
    texto.textContent = icono + ' ' + (m.mensaje.length > 90 ? m.mensaje.substring(0, 90) + '…' : m.mensaje);
    texto.title = m.mensaje;
    const btn = document.createElement('button');
    btn.className = 'boton-chico boton-borrar';
    btn.textContent = '🗑️';
    btn.onclick = () => borrarMensajeChat(m.id);
    li.appendChild(texto);
    li.appendChild(btn);
    ul.appendChild(li);
  });
}

function filtrarChats(texto) {
  const t = texto.toLowerCase().trim();
  if (!t) { pintarChats(chatsCache); return; }
  pintarChats(chatsCache.filter(m => m.mensaje.toLowerCase().includes(t)));
}

async function borrarMensajeChat(id) {
  if (!confirm('¿Borrar este mensaje de la charla?')) return;
  const resp = await fetch('/api/config/chats/' + id, { method: 'DELETE' });
  const datos = await resp.json();
  avisar(datos.mensaje);
  cargarChats();
}

async function borrarTodoChat() {
  if (!confirm('¿Borrar TODA la charla con Sibeli? No se puede deshacer.')) return;
  const resp = await fetch('/api/config/chats/borrar_todo', { method: 'POST' });
  const datos = await resp.json();
  avisar(datos.mensaje);
  cargarChats();
}

cargarChats();

/* =====================================================
   CARPETA DE SIBELI: preferencias y manager de documentos
   ===================================================== */
async function cargarPreferenciasSibeli() {
  const resp = await fetch('/api/config/sibeli');
  const datos = await resp.json();
  document.getElementById('carpeta-sibeli-ruta').textContent = '📁 ' + datos.carpeta;
  document.getElementById('toggle-biblioteca').checked = datos.biblioteca;
  document.getElementById('toggle-escritura').checked = datos.escritura;
  cargarDocs();
}

async function guardarPreferenciasSibeli() {
  const resp = await fetch('/api/config/sibeli', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      biblioteca: document.getElementById('toggle-biblioteca').checked,
      escritura: document.getElementById('toggle-escritura').checked
    })
  });
  const datos = await resp.json();
  avisar(datos.mensaje);
}

async function cargarDocs() {
  const resp = await fetch('/api/documentos');
  const docs = await resp.json();
  const ul = document.getElementById('lista-docs');
  ul.innerHTML = '';
  if (!docs.length) {
    ul.innerHTML = '<li class="ayuda">Carpeta vacía. Guardá .txt, .md o .pdf en Download/Sibeli desde Android.</li>';
    return;
  }
  docs.forEach(d => {
    const li = document.createElement('li');
    li.className = 'item-chat';
    const span = document.createElement('span');
    span.className = 'chat-resumen';
    span.textContent = '📄 ' + d.nombre + ' (' + d.tam_kb + ' KB)';
    li.appendChild(span);
    const ver = document.createElement('button');
    ver.className = 'boton-chico';
    ver.textContent = '👁';
    ver.title = 'Ver contenido';
    ver.onclick = () => verDoc(d.nombre);
    const bor = document.createElement('button');
    bor.className = 'boton-chico boton-borrar';
    bor.textContent = '🗑️';
    bor.onclick = () => borrarDoc(d.nombre);
    li.appendChild(ver);
    li.appendChild(bor);
    ul.appendChild(li);
  });
}

async function verDoc(nombre) {
  const resp = await fetch('/api/documentos/ver?nombre=' + encodeURIComponent(nombre));
  const datos = await resp.json();
  document.getElementById('modal-doc-titulo').textContent = nombre;
  document.getElementById('modal-doc-texto').textContent =
    datos.ok ? (datos.aviso ? datos.aviso + '\n\n' : '') + datos.texto : datos.aviso;
  document.getElementById('modal-doc').hidden = false;
}

function cerrarModalDoc() {
  document.getElementById('modal-doc').hidden = true;
}

async function borrarDoc(nombre) {
  if (!confirm('¿Borrar ' + nombre + ' de la carpeta de Sibeli?')) return;
  const resp = await fetch('/api/documentos/borrar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre: nombre })
  });
  const datos = await resp.json();
  avisar(datos.mensaje);
  cargarDocs();
}

cargarPreferenciasSibeli();

/* =====================================================
   AUTO-PUSH GITHUB
   ===================================================== */
async function cargarConfigAutoPush() {
  // Asumimos que ya tenemos la config cargada o la pedimos
  // Para simplificar, leemos el valor inicial del checkbox si existe
  const checkbox = document.getElementById('toggle-auto-push');
  if (checkbox) {
    // Por defecto activado si no existe la clave
    checkbox.checked = true; 
    // Guardamos el estado inicial
    fetch('/api/config/auto_push', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({valor: '1'}) });
  }
}

function guardarAutoPush() {
  const valor = document.getElementById('toggle-auto-push').checked ? '1' : '0';
  fetch('/api/config/auto_push', { 
    method: 'POST', 
    headers: {'Content-Type': 'application/json'}, 
    body: JSON.stringify({valor: valor}) 
  }).then(() => avisar('Configuración de auto-push actualizada'));
}

// Necesitamos la ruta para guardar esta config específica
