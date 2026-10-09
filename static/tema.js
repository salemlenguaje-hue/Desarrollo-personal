/* =====================================================
   TEMA CLARO / OSCURO ("Noche SALEM")
   Se guarda en localStorage y se aplica apenas abre la página.
   ===================================================== */
function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  localStorage.setItem('tema', tema);
  const btn = document.getElementById('btn-tema');
  if (btn) btn.textContent = tema === 'oscuro' ? '☀️' : '🌙';
}

function alternarTema() {
  const actual = document.documentElement.dataset.tema || 'claro';
  aplicarTema(actual === 'oscuro' ? 'claro' : 'oscuro');
  // Recargamos para que gráficos y calendario se repinten con la paleta correcta
  location.reload();
}

// Al abrir cualquier página, respetamos tu última elección
aplicarTema(localStorage.getItem('tema') || 'claro');
