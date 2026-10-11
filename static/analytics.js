/* =====================================================
   ANALYTICS.JS — gráficos con filtro por período
   y tarjeta de tiempo en racha siempre visible.
   ===================================================== */

const COLORES = [
  '#0B2E59', '#1663A8', '#4D8FD1', '#6C4AB6',
  '#F5B301', '#2FA36B', '#E5484D'
];
const COLORES_CALENDARIO = ['#EBEDF0', '#E3D7F5', '#B89DF0', '#6C4AB6', '#F5B301'];

// Guardamos los gráficos para poder redibujarlos al cambiar el período
let chartLinea = null, chartTorta = null, chartBarras = null;
let ultimosDatos = null;

// Escribe un valor solo si el elemento existe (evita errores silenciosos)
function poner(id, valor) {
  const el = document.getElementById(id);
  if (el) el.textContent = valor;
}  // conoce racha_inicio sin recargar nada

function avisar(mensaje) {
  const toast = document.getElementById('toast');
  toast.textContent = mensaje;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 3500);
}

// "135" minutos -> "2h 15m"
function fmtHoras(min) {
  min = min || 0;
  return Math.floor(min / 60) + 'h ' + (min % 60) + 'm';
}

// Fecha local en formato YYYY-MM-DD (sin sorpresas de zona horaria)
function fechaLocal(d) {
  return d.getFullYear() + '-' +
         String(d.getMonth() + 1).padStart(2, '0') + '-' +
         String(d.getDate()).padStart(2, '0');
}

// ==================== CARGA CON PERÍODO ====================
async function cargarEstadisticas(desde, hasta) {
  try {
    let url = '/api/estadisticas';
    const params = new URLSearchParams();
    if (desde) params.set('desde', desde);
    if (hasta) params.set('hasta', hasta);
    if ([...params].length) url += '?' + params.toString();

    const resp = await fetch(url);
    if (!resp.ok) {
      const detalle = await resp.text();
      console.error('Detalle del error del servidor:', detalle);
      throw new Error('HTTP ' + resp.status);
    }
    const stats = await resp.json();
    ultimosDatos = stats;

    // Tinta de los gráficos según el tema activo
    if (document.documentElement.dataset.tema === 'oscuro' && window.Chart) {
      Chart.defaults.color = '#B9C7DC';
      Chart.defaults.borderColor = 'rgba(185, 199, 220, .15)';
    }

    // Tarjetas fijas + tarjetas del período
    poner('stat-racha', stats.racha_actual);
    poner('stat-mejor', stats.mejor_racha);
    poner('stat-nivel', stats.nivel_actual);
    poner('stat-total', stats.total_entradas);
    poner('stat-tiempo', fmtHoras(stats.minutos_totales));
    poner('stat-tiempo-racha', fmtHoras(stats.minutos_racha));
    poner('etiqueta-periodo',
      '📆 Período del reporte: ' + (stats.desde || '?') + '  →  ' + (stats.hasta || '?') +
      (stats.racha_inicio ? '   ·   🔥 Racha vigente desde ' + stats.racha_inicio : ''));

    // Gráfico de línea (evolución del período)
    if (chartLinea) chartLinea.destroy();
    chartLinea = new Chart(document.getElementById('grafico-linea'), {
      type: 'line',
      data: {
        labels: stats.entradas_por_dia.map(d => d.fecha.substring(5)),
        datasets: [{
          label: 'Minutos por día',
          data: stats.entradas_por_dia.map(d => d.minutos),
          borderColor: '#1663A8',
          backgroundColor: 'rgba(22, 99, 168, 0.1)',
          fill: true,
          tension: 0.3
        }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });

    // Torta de temáticas del período
    if (chartTorta) chartTorta.destroy();
    chartTorta = new Chart(document.getElementById('grafico-torta'), {
      type: 'doughnut',
      data: {
        labels: stats.por_tematica.map(t => t.nombre),
        datasets: [{ data: stats.por_tematica.map(t => t.minutos), backgroundColor: COLORES }]
      },
      options: { responsive: true }
    });

    // Barras de tipos de estudio del período
    if (chartBarras) chartBarras.destroy();
    chartBarras = new Chart(document.getElementById('grafico-barras'), {
      type: 'bar',
      data: {
        labels: stats.por_tipo.map(t => t.nombre),
        datasets: [{
          label: 'Minutos',
          data: stats.por_tipo.map(t => t.minutos),
          backgroundColor: COLORES,
          borderRadius: 8
        }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } catch (error) {
    console.error('Error cargando estadísticas:', error);
    avisar('Error al cargar los gráficos 😢 ' + error.message);
  }
}

// ==================== CALENDARIO (mapa general, 365 días) ====================
async function dibujarCalendario() {
  const resp = await fetch('/api/calendario');
  const dias = await resp.json();
  const contenedor = document.getElementById('calendario');
  const paleta = document.documentElement.dataset.tema === 'oscuro'
    ? ['#22304A', '#3A2E57', '#5B4494', '#8A63D2', '#F5B301']
    : COLORES_CALENDARIO;
  contenedor.innerHTML = '';
  dias.forEach(dia => {
    const celda = document.createElement('div');
    celda.className = 'dia-cuadrito';
    celda.style.backgroundColor = paleta[dia.nivel];
    celda.title = dia.fecha + ': ' + dia.cantidad + ' entrada(s)';
    contenedor.appendChild(celda);
  });
}

// ==================== CHIPS DE PERÍODO ====================
document.querySelectorAll('#chips-periodo .boton-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('#chips-periodo .boton-chip')
      .forEach(c => c.classList.remove('chip-activo'));
    chip.classList.add('chip-activo');

    const hoy = new Date();
    const modo = chip.dataset.modo;

    if (modo === 'racha') {
      cargarEstadisticas(ultimosDatos ? ultimosDatos.racha_inicio : null, fechaLocal(hoy));
    } else if (modo === '7') {
      const d = new Date(); d.setDate(d.getDate() - 6);
      cargarEstadisticas(fechaLocal(d), fechaLocal(hoy));
    } else if (modo === '30') {
      const d = new Date(); d.setDate(d.getDate() - 29);
      cargarEstadisticas(fechaLocal(d), fechaLocal(hoy));
    } else if (modo === 'mes') {
      const d = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
      cargarEstadisticas(fechaLocal(d), fechaLocal(hoy));
    } else if (modo === 'todo') {
      cargarEstadisticas('2000-01-01', fechaLocal(hoy));
    } else if (modo === 'custom') {
      document.getElementById('fila-fechas').hidden = false;
    }
  });
});

// Período a medida con los dos calendarios
function aplicarPeriodoCustom() {
  const desde = document.getElementById('fecha-desde').value;
  const hasta = document.getElementById('fecha-hasta').value;
  if (!desde || !hasta) { avisar('Elegí ambas fechas 📅'); return; }
  if (desde > hasta) { avisar('El "desde" no puede ser posterior al "hasta"'); return; }
  cargarEstadisticas(desde, hasta);
}

// ==================== AUDITORÍA DE BLOCKCHAIN ====================
document.getElementById('btn-validar').addEventListener('click', async () => {
  const boton = document.getElementById('btn-validar');
  const resultado = document.getElementById('resultado-auditoria');
  boton.disabled = true;
  boton.textContent = '🔍 Auditando...';
  resultado.hidden = true;
  try {
    const resp = await fetch('/api/validar_blockchain');
    const data = await resp.json();
    let texto = data.mensaje + '\n\n';
    if (data.errores && data.errores.length > 0) {
      texto += 'Detalles de los errores:\n';
      data.errores.forEach(err => texto += '❌ ' + err + '\n');
    } else {
      texto += '🔒 Hashes verificados.\n🔗 Eslabones de la cadena intactos.\n✍️ Firmas criptográficas válidas.';
    }
    resultado.textContent = texto;
    resultado.hidden = false;
  } catch (error) {
    avisar('Error al conectar con el validador.');
  } finally {
    boton.disabled = false;
    boton.textContent = '🕵️‍♂️ Auditar Cadena';
  }
});

// ==================== ARRANQUE ====================
cargarEstadisticas();   // sin fechas = últimos 30 días, como siempre
dibujarCalendario();
