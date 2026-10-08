print("⏳ Aplicando Cronómetro al Frontend...")

# 1. index.html (Formulario y lista de hoy)
with open('templates/index.html', 'r', encoding='utf-8') as f: html = f.read()
html = html.replace(
    '<button class="boton boton-dorado" type="submit">Guardar entrada ✅</button>',
    '<label>Minutos dedicados ⏱️</label>\n        <input type="number" id="entrada-minutos" min="1" placeholder="Ej: 45" required>\n\n        <button class="boton boton-dorado" type="submit">Guardar entrada ✅</button>'
)
html = html.replace(
    '<div class="entrada-dato"><strong>Tipos:</strong>',
    '<div class="entrada-dato"><strong>⏱️ Tiempo:</strong> {{ e.minutos }} minutos</div>\n          <div class="entrada-dato"><strong>Tipos:</strong>'
)
with open('templates/index.html', 'w', encoding='utf-8') as f: f.write(html)

# 2. script.js (Enviar minutos al guardar)
with open('static/script.js', 'r', encoding='utf-8') as f: js = f.read()
js = js.replace(
    "observaciones: document.getElementById('entrada-observaciones').value.trim()",
    "observaciones: document.getElementById('entrada-observaciones').value.trim(),\n    minutos: parseInt(document.getElementById('entrada-minutos').value) || 0"
)
with open('static/script.js', 'w', encoding='utf-8') as f: f.write(js)

# 3. analytics.html (Nueva tarjeta de Tiempo Total)
with open('templates/analytics.html', 'r', encoding='utf-8') as f: ahtml = f.read()
ahtml = ahtml.replace(
    '<div class="mini-titulo">📚 TOTAL ENTRADAS</div>\n        <div class="mini-numero" id="stat-total">0</div>',
    '<div class="mini-titulo">📚 TOTAL ENTRADAS</div>\n        <div class="mini-numero" id="stat-total">0</div>\n      </div>\n      <div class="tarjeta tarjeta-mini">\n        <div class="mini-titulo">⏱️ TIEMPO TOTAL</div>\n        <div class="mini-numero" id="stat-tiempo">0h</div>'
)
with open('templates/analytics.html', 'w', encoding='utf-8') as f: f.write(ahtml)

# 4. analytics.js (Gráficos usan minutos y los formatean a horas)
with open('static/analytics.js', 'r', encoding='utf-8') as f: ajs = f.read()
ajs = ajs.replace(
    "const totalEntradas = stats.entradas_por_dia.reduce((sum, dia) => sum + dia.cantidad, 0);\n    document.getElementById('stat-total').textContent = totalEntradas;",
    "const totalEntradas = stats.entradas_por_dia.reduce((sum, dia) => sum + (dia.minutos || 0), 0);\n    document.getElementById('stat-total').textContent = totalEntradas;\n    const horas = Math.floor(totalEntradas / 60);\n    const mins = totalEntradas % 60;\n    document.getElementById('stat-tiempo').textContent = horas + 'h ' + mins + 'm';"
)
ajs = ajs.replace("data: stats.entradas_por_dia.map(d => d.cantidad),", "data: stats.entradas_por_dia.map(d => d.minutos),")
ajs = ajs.replace("data: stats.por_tematica.map(t => t.cantidad),", "data: stats.por_tematica.map(t => t.minutos),")
ajs = ajs.replace("data: stats.por_tipo.map(t => t.cantidad),", "data: stats.por_tipo.map(t => t.minutos),")
ajs = ajs.replace("label: 'Entradas por día',", "label: 'Minutos por día',")
ajs = ajs.replace("label: 'Usos',", "label: 'Minutos',")

with open('static/analytics.js', 'w', encoding='utf-8') as f: f.write(ajs)

print("✅ Frontend actualizado. ¡Todo listo!")
