/* =====================================================
   ANALYTICS.JS — El pintor de los gráficos
   ===================================================== */

// Paleta de colores SALEM para los gráficos
const COLORES = [
  '#0B2E59', // Azul profundo
  '#1663A8', // Azul medio
  '#4D8FD1', // Azul claro
  '#6C4AB6', // Violeta
  '#F5B301', // Dorado
  '#2FA36B', // Verde
  '#E5484D'  // Rojo suave
];

// Colores para el calendario (de menos a más intensidad)
const COLORES_CALENDARIO = ['#EBEDF0', '#E3D7F5', '#B89DF0', '#6C4AB6', '#F5B301'];

function avisar(mensaje) {
  const toast = document.getElementById('toast');
  toast.textContent = mensaje;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 3500);
}

// ---------- CARGAR DATOS Y DIBUJAR TODO ----------
async function inicializar() {
  try {
    const resp = await fetch('/api/estadisticas');
    const stats = await resp.json();

    // 1. Llenar tarjetas de resumen
    document.getElementById('stat-racha').textContent = stats.racha_actual;
    document.getElementById('stat-mejor').textContent = stats.mejor_racha;
    document.getElementById('stat-nivel').textContent = stats.nivel_actual;
    
    // Calcular total de entradas sumando las de los últimos 30 días
    const totalEntradas = stats.entradas_por_dia.reduce((sum, dia) => sum + (dia.minutos || 0), 0);
        const horas = Math.floor(totalEntradas / 60);
    const mins = totalEntradas % 60;
    document.getElementById('stat-tiempo').textContent = horas + 'h ' + mins + 'm';

    // 2. Dibujar Gráfico de Línea (Evolución)
    new Chart(document.getElementById('grafico-linea'), {
      type: 'line',
      data: {
        labels: stats.entradas_por_dia.map(d => d.fecha.substring(5)), // Mostrar solo MM-DD
        datasets: [{
          label: 'Minutos por día',
          data: stats.entradas_por_dia.map(d => d.minutos),
          borderColor: '#1663A8',
          backgroundColor: 'rgba(22, 99, 168, 0.1)',
          fill: true,
          tension: 0.3 // Línea suavecita
        }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });

    // 3. Dibujar Gráfico de Torta (Temáticas)
    new Chart(document.getElementById('grafico-torta'), {
      type: 'doughnut', // Tipo dona, queda más moderno
      data: {
        labels: stats.por_tematica.map(t => t.nombre),
        datasets: [{
          data: stats.por_tematica.map(t => t.minutos),
          backgroundColor: COLORES
        }]
      },
      options: { responsive: true }
    });

    // 4. Dibujar Gráfico de Barras (Tipos de estudio)
    new Chart(document.getElementById('grafico-barras'), {
      type: 'bar',
      data: {
        labels: stats.por_tipo.map(t => t.nombre),
        datasets: [{
          label: 'Minutos',
          data: stats.por_tipo.map(t => t.minutos),
          backgroundColor: COLORES,
          borderRadius: 8 // Bordes redondeados estilo Duolingo
        }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });

    // 5. Dibujar Calendario
    dibujarCalendario();

  } catch (error) {
    console.error("Error cargando estadísticas:", error);
    avisar("Error al cargar los gráficos 😢");
  }
}

// ---------- CALENDARIO TIPO GITHUB ----------
async function dibujarCalendario() {
  const resp = await fetch('/api/calendario');
  const dias = await resp.json();
  const totalReal = dias.reduce((sum, d) => sum + d.cantidad, 0);
  document.getElementById('stat-total').textContent = totalReal;
  const contenedor = document.getElementById('calendario');
  contenedor.innerHTML = '';
  
  // Iteramos los 365 días y creamos un cuadradito para cada uno
  dias.forEach(dia => {
    const celda = document.createElement('div');
    celda.className = 'dia-cuadrito';
    // El nivel va de 0 a 4, lo usamos para elegir el color
    celda.style.backgroundColor = COLORES_CALENDARIO[dia.nivel];
    celda.title = `${dia.fecha}: ${dia.cantidad} entrada(s)`;
    contenedor.appendChild(celda);
  });
}

// ---------- AUDITORÍA DE BLOCKCHAIN ----------
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
    avisar("Error al conectar con el validador.");
  } finally {
    boton.disabled = false;
    boton.textContent = '🕵️‍♂️ Auditar Cadena';
  }
});

// ¡Arrancamos!
inicializar();
