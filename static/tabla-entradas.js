/* =====================================================
   TABLA INTERACTIVA DE ENTRADAS — con diagnóstico
   ===================================================== */

let todasLasEntradas = [];
let tematicasDisponibles = [];

async function cargarTablaEntradas() {
  const contenedor = document.getElementById('tabla-entradas-container');
  if (!contenedor) {
    console.log('⚠️ No se encontró #tabla-entradas-container');
    return;
  }

  console.log('🔄 Cargando tabla de entradas...');

  try {
    // Cargar temáticas para el filtro
    const respTem = await fetch('/api/tematicas');
    if (!respTem.ok) throw new Error(`Error temáticas: ${respTem.status}`);
    tematicasDisponibles = await respTem.json();
    console.log(`✅ Temáticas cargadas: ${tematicasDisponibles.length}`);
    
    // Cargar todas las entradas
    const resp = await fetch('/api/entradas/historial');
    console.log(`📡 Respuesta del servidor: ${resp.status} ${resp.statusText}`);
    
    if (!resp.ok) {
      const errorText = await resp.text();
      console.error('❌ Error del servidor:', errorText);
      document.getElementById('tabla-entradas-body').innerHTML = 
        `<tr><td colspan="3" class="error">Error ${resp.status}: ${errorText}</td></tr>`;
      return;
    }
    
    todasLasEntradas = await resp.json();
    console.log(`✅ Entradas cargadas: ${todasLasEntradas.length}`);

    renderizarFiltros();
    renderizarTabla(todasLasEntradas);
  } catch (error) {
    console.error('❌ Error al cargar tabla:', error);
    document.getElementById('tabla-entradas-body').innerHTML = 
      `<tr><td colspan="3" class="error">Error: ${error.message}</td></tr>`;
  }
}

function renderizarFiltros() {
  const contenedor = document.getElementById('filtros-entradas');
  if (!contenedor) return;

  contenedor.innerHTML = `
    <div class="filtros-row">
      <div class="filtro-grupo">
        <label for="filtro-fecha-desde">Desde:</label>
        <input type="date" id="filtro-fecha-desde" onchange="aplicarFiltros()">
      </div>
      <div class="filtro-grupo">
        <label for="filtro-fecha-hasta">Hasta:</label>
        <input type="date" id="filtro-fecha-hasta" onchange="aplicarFiltros()">
      </div>
      <div class="filtro-grupo">
        <label for="filtro-tematica">Temática:</label>
        <select id="filtro-tematica" onchange="aplicarFiltros()">
          <option value="">Todas</option>
          ${tematicasDisponibles.map(t => `<option value="${t.id}">${t.nombre}</option>`).join('')}
        </select>
      </div>
      <button class="boton boton-suave" onclick="limpiarFiltros()">Limpiar filtros</button>
    </div>
  `;
}

function aplicarFiltros() {
  const desde = document.getElementById('filtro-fecha-desde').value;
  const hasta = document.getElementById('filtro-fecha-hasta').value;
  const tematica = document.getElementById('filtro-tematica').value;

  let filtradas = todasLasEntradas;

  if (desde) filtradas = filtradas.filter(e => e.fecha >= desde);
  if (hasta) filtradas = filtradas.filter(e => e.fecha <= hasta);
  if (tematica) filtradas = filtradas.filter(e => e.tematica_id == tematica);

  renderizarTabla(filtradas);
}

function limpiarFiltros() {
  document.getElementById('filtro-fecha-desde').value = '';
  document.getElementById('filtro-fecha-hasta').value = '';
  document.getElementById('filtro-tematica').value = '';
  renderizarTabla(todasLasEntradas);
}

function renderizarTabla(entradas) {
  const tbody = document.getElementById('tabla-entradas-body');
  if (!tbody) return;

  if (entradas.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" class="sin-resultados">No hay entradas que coincidan con los filtros.</td></tr>';
    return;
  }

  tbody.innerHTML = entradas.map(e => `
    <tr class="fila-clickeable" onclick="verDetalleEntrada(${e.id})">
      <td>${e.id}</td>
      <td>${e.fecha}</td>
      <td>${e.tematica_nombre}</td>
    </tr>
  `).join('');
}

async function verDetalleEntrada(id) {
  const modal = document.getElementById('modal-detalle-entrada');
  const contenido = document.getElementById('detalle-entrada-contenido');
  
  if (!modal || !contenido) return;

  contenido.innerHTML = '<p class="cargando">Cargando...</p>';
  modal.hidden = false;

  try {
    const resp = await fetch(`/api/entradas/${id}`);
    const entrada = await resp.json();

    if (entrada.error) {
      contenido.innerHTML = `<p class="error">${entrada.error}</p>`;
      return;
    }

    contenido.innerHTML = `
      <div class="detalle-header">
        <h3>Entrada #${entrada.id}</h3>
        <span class="detalle-fecha">${entrada.fecha}</span>
      </div>
      <div class="detalle-tematica"><strong>Temática:</strong> ${entrada.tematica_nombre}</div>
      <div class="detalle-tipos"><strong>Tipos:</strong> ${entrada.tipos_nombres || 'No especificado'}</div>
      ${entrada.minutos ? `<div class="detalle-minutos"><strong>Minutos:</strong> ${entrada.minutos}</div>` : ''}
      ${entrada.descripcion ? `<div class="detalle-seccion"><strong>Descripción:</strong><p>${entrada.descripcion}</p></div>` : ''}
      ${entrada.resumen ? `<div class="detalle-seccion"><strong>Resumen:</strong><p>${entrada.resumen}</p></div>` : ''}
      ${entrada.observaciones ? `<div class="detalle-seccion"><strong>Observaciones:</strong><p>${entrada.observaciones}</p></div>` : ''}
      <div class="detalle-blockchain">
        <strong>Blockchain:</strong>
        <div class="hash-info">
          <div><strong>Hash:</strong> ${entrada.hash ? entrada.hash.substring(0, 32) + '...' : 'N/A'}</div>
          <div><strong>Hash previo:</strong> ${entrada.hash_previo ? entrada.hash_previo.substring(0, 32) + '...' : 'N/A'}</div>
          <div><strong>Firma:</strong> ${entrada.firma ? entrada.firma.substring(0, 32) + '...' : 'N/A'}</div>
        </div>
      </div>
    `;
  } catch (error) {
    contenido.innerHTML = '<p class="error">Error al cargar el detalle.</p>';
  }
}

function cerrarModalDetalle() {
  const modal = document.getElementById('modal-detalle-entrada');
  if (modal) modal.hidden = true;
}

// Inicializar cuando el DOM esté listo
if (document.getElementById('tabla-entradas-container')) {
  cargarTablaEntradas();
}
