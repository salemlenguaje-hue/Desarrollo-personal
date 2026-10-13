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
