"""
Corrige 3 detalles que dejó el cronómetro:
1. El auditor validaba hashes con la fórmula vieja (sin minutos).
2. Dos consultas de estadísticas quedaron ordenando por la columna vieja.
3. A la consulta de tipos le faltaba conectarse con la tabla entradas.
4. La tarjeta 'Total entradas' mostraba minutos en vez de entradas.
Tus datos NUNCA fueron modificados: era falsa alarma.
"""

# ---------- 1) logica.py ----------
with open('logica.py', encoding='utf-8') as f:
    code = f.read()

# 1a. El auditor ahora pasa los minutos al recalcular el hash
old_call = "entrada['observaciones'] or ''\n        )"
new_call = "entrada['observaciones'] or '', entrada['minutos'] or 0\n        )"
if old_call in code:
    code = code.replace(old_call, new_call)
    print("✅ 1. Auditor actualizado: valida con la fórmula nueva (con minutos)")
else:
    print("⚠️ No encontré la llamada del auditor")

# 1b. Ordenar por la columna nueva (minutos), no por la vieja (cantidad)
if 'ORDER BY cantidad DESC' in code:
    code = code.replace('ORDER BY cantidad DESC', 'ORDER BY minutos DESC')
    print("✅ 2. Orden de las estadísticas corregido")

# 1c. A la consulta de tipos le falta conectarse con la tabla entradas
old_from = """        FROM entrada_tipos et
        JOIN tipos_estudio te ON et.tipo_id = te.id"""
new_from = """        FROM entrada_tipos et
        JOIN tipos_estudio te ON et.tipo_id = te.id
        JOIN entradas e ON et.entrada_id = e.id"""
if old_from in code:
    code = code.replace(old_from, new_from)
    print("✅ 3. Consulta de tipos conectada con entradas")
else:
    print("⚠️ No encontré la consulta de tipos")

with open('logica.py', 'w', encoding='utf-8') as f:
    f.write(code)

# ---------- 2) analytics.js ----------
with open('static/analytics.js', encoding='utf-8') as f:
    js = f.read()

# La tarjeta 'Total entradas' debe contar entradas, no minutos.
# Sacamos la línea equivocada...
js = js.replace("document.getElementById('stat-total').textContent = totalEntradas;\n", "")
# ...y la calculamos en el calendario, que sí conoce las cantidades por día
old_cal = "const dias = await resp.json();\n  const contenedor"
new_cal = ("const dias = await resp.json();\n"
           "  const totalReal = dias.reduce((sum, d) => sum + d.cantidad, 0);\n"
           "  document.getElementById('stat-total').textContent = totalReal;\n"
           "  const contenedor")
if old_cal in js:
    js = js.replace(old_cal, new_cal)
    print("✅ 4. Tarjeta 'Total entradas' corregida")
else:
    print("⚠️ No encontré el calendario en analytics.js")

with open('static/analytics.js', 'w', encoding='utf-8') as f:
    f.write(js)

print("🎉 Parche aplicado. Reiniciá el servidor y volvé a auditar.")
