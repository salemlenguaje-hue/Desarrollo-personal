/* =====================================================
   REPORTES.JS — Buscador y generador de reportes
   ===================================================== */

let entradasEncontradas = [];

async function buscar() {
  const texto = document.getElementById('campo-busqueda').value.trim();
  const contenedor = document.getElementById('resultados-busqueda');
  
  if (!texto) {
    contenedor.innerHTML = '<p class="ayuda">Escribí un término para buscar.</p>';
    document.getElementById('acciones-reportes').hidden = true;
    return;
  }

  contenedor.innerHTML = '<p class="ayuda">Buscando...</p>';
  
  try {
    const resp = await fetch(`/api/entradas/buscar?q=${encodeURIComponent(texto)}`);
    entradasEncontradas = await resp.json();
    
    if (entradasEncontradas.length === 0) {
      contenedor.innerHTML = '<p class="ayuda">No se encontraron entradas con ese término.</p>';
      document.getElementById('acciones-reportes').hidden = true;
      return;
    }

    contenedor.innerHTML = '';
    entradasEncontradas.forEach((e, index) => {
      const div = document.createElement('div');
      div.className = 'item-entrada';
      div.innerHTML = `
        <input type="checkbox" id="chk-${index}" class="chk-entrada" onchange="actualizarContador()">
        <div class="contenido-entrada">
          <div class="entrada-header">
            <strong>${e.fecha}</strong> · ${e.tematica_nombre}
          </div>
          <div class="entrada-resumen">${e.resumen || e.descripcion || 'Sin resumen'}</div>
        </div>
      `;
      contenedor.appendChild(div);
    });
    
    document.getElementById('acciones-reportes').hidden = false;
    actualizarContador();
  } catch (error) {
    contenedor.innerHTML = '<p class="error">Error al buscar.</p>';
  }
}

function actualizarContador() {
  const seleccionadas = document.querySelectorAll('.chk-entrada:checked').length;
  document.getElementById('contador-seleccion').textContent = `${seleccionadas} seleccionadas`;
}

function generarReporte() {
  const seleccionadas = document.querySelectorAll('.chk-entrada:checked');
  if (seleccionadas.length === 0) {
    alert('Seleccioná al menos una entrada para el reporte.');
    return;
  }

  // Abrimos una ventana nueva para imprimir
  const ventana = window.open('', '_blank');
  let html = `
    <html>
    <head>
      <title>Reporte de Estudio</title>
      <style>
        body { font-family: system-ui, sans-serif; padding: 20px; color: #333; }
        h1 { color: #1F4E79; border-bottom: 2px solid #1F4E79; padding-bottom: 10px; }
        .entrada { margin-bottom: 30px; page-break-inside: avoid; border: 1px solid #ddd; padding: 15px; border-radius: 8px; }
        .entrada-header { font-weight: bold; color: #6C4AB6; margin-bottom: 10px; font-size: 1.1em; }
        .tematica { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
        .seccion { margin-top: 10px; }
        .seccion-titulo { font-weight: bold; color: #555; margin-bottom: 5px; }
        @media print { body { padding: 0; } .entrada { border: none; } }
      </style>
    </head>
    <body>
      <h1>Reporte de Estudio Personal</h1>
      <p>Generado el ${new Date().toLocaleDateString()} · ${seleccionadas.length} entradas seleccionadas</p>
      <hr>
  `;

  seleccionadas.forEach(chk => {
    const index = chk.id.split('-')[1];
    const e = entradasEncontradas[index];
    html += `
      <div class="entrada">
        <div class="entrada-header">
          📅 ${e.fecha} <span class="tematica">${e.tematica_nombre}</span>
        </div>
        ${e.descripcion ? `<div class="seccion"><div class="seccion-titulo">Descripción:</div><p>${e.descripcion}</p></div>` : ''}
        ${e.resumen ? `<div class="seccion"><div class="seccion-titulo">Resumen:</div><p>${e.resumen}</p></div>` : ''}
        ${e.observaciones ? `<div class="seccion"><div class="seccion-titulo">Observaciones:</div><p>${e.observaciones}</p></div>` : ''}
      </div>
    `;
  });

  html += `</body></html>`;
  
  ventana.document.write(html);
  ventana.document.close();
  ventana.focus();
  setTimeout(() => ventana.print(), 500);
}

// Permitir buscar con Enter
document.getElementById('campo-busqueda').addEventListener('keypress', function (e) {
  if (e.key === 'Enter') buscar();
});
