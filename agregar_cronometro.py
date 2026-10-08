import sqlite3, os, hashlib, hmac

print("⏳ Aplicando Cronómetro al Backend...")

# 1. Base de Datos
conn = sqlite3.connect('database.db')
try:
    conn.execute('ALTER TABLE entradas ADD COLUMN minutos INTEGER DEFAULT 0')
    print("✅ DB: Columna 'minutos' agregada")
except sqlite3.OperationalError:
    print("ℹ️ DB: Columna 'minutos' ya existía")
conn.commit()
conn.close()

# 2. Lógica (logica.py)
with open('logica.py', 'r', encoding='utf-8') as f: code = f.read()

replacements = [
    # Hash function (ahora incluye minutos)
    ("def calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones):",
     "def calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones, minutos=0):"),
    ('contenido = f"{fecha}|{tematica_id}|{descripcion}|{resumen}|{observaciones}"',
     'contenido = f"{fecha}|{tematica_id}|{descripcion}|{resumen}|{observaciones}|{minutos}"'),
    
    # Guardar entrada
    ("def guardar_entrada(fecha, tematica_id, descripcion, tipos, resumen, observaciones):",
     "def guardar_entrada(fecha, tematica_id, descripcion, tipos, resumen, observaciones, minutos=0):"),
    ("hash_entrada = calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones)",
     "hash_entrada = calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones, minutos)"),
    ("INSERT INTO entradas (fecha, tematica_id, descripcion, resumen, observaciones,\n                              hash, hash_previo, firma)\n        VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
     "INSERT INTO entradas (fecha, tematica_id, descripcion, resumen, observaciones, minutos,\n                              hash, hash_previo, firma)\n        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"),
    ("(fecha, tematica_id, descripcion, resumen, observaciones,\n          hash_entrada, hash_previo, firma)",
     "(fecha, tematica_id, descripcion, resumen, observaciones, minutos,\n          hash_entrada, hash_previo, firma)"),
     
    # Estadísticas (Cambiamos COUNT por SUM de minutos)
    ("SELECT fecha, COUNT(*) as cantidad\n        FROM entradas\n        WHERE fecha >= date('now', '-30 days')",
     "SELECT fecha, COALESCE(SUM(minutos), 0) as minutos\n        FROM entradas\n        WHERE fecha >= date('now', '-30 days')"),
    ("SELECT t.nombre, COUNT(e.id) as cantidad\n        FROM entradas e",
     "SELECT t.nombre, COALESCE(SUM(e.minutos), 0) as minutos\n        FROM entradas e"),
    ("SELECT te.nombre, COUNT(et.entrada_id) as cantidad",
     "SELECT te.nombre, COALESCE(SUM(e.minutos), 0) as minutos"),
]

for old, new in replacements:
    if old in code: code = code.replace(old, new)

with open('logica.py', 'w', encoding='utf-8') as f: f.write(code)
print("✅ logica.py actualizado")

# 3. Servidor (server.py)
with open('server.py', 'r', encoding='utf-8') as f: srv = f.read()
srv = srv.replace(
    "observaciones=datos.get('observaciones', '')\n    )",
    "observaciones=datos.get('observaciones', ''),\n        minutos=int(datos.get('minutos', 0) or 0)\n    )"
)
with open('server.py', 'w', encoding='utf-8') as f: f.write(srv)
print("✅ server.py actualizado")

# 4. Recalcular Blockchain (¡Crítico para que no se rompa la cadena!)
with open('.secreto', 'r') as f: clave = f.read().strip()

def calc_hash(fecha, t_id, desc, res, obs, mins=0):
    return hashlib.sha256(f"{fecha}|{t_id}|{desc}|{res}|{obs}|{mins}".encode()).hexdigest()
def calc_firma(h, k):
    return hmac.new(k.encode(), h.encode(), hashlib.sha256).hexdigest()

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT * FROM entradas ORDER BY id ASC')
entradas = cur.fetchall()
hash_prev = None
for e in entradas:
    # Las entradas viejas tendrán minutos=0 o None, lo manejamos con 'or 0'
    h = calc_hash(e['fecha'], e['tematica_id'], e['descripcion'] or '', e['resumen'] or '', e['observaciones'] or '', e['minutos'] or 0)
    f = calc_firma(h, clave)
    cur.execute('UPDATE entradas SET hash=?, hash_previo=?, firma=? WHERE id=?', (h, hash_prev, f, e['id']))
    hash_prev = h
conn.commit()
conn.close()
print(f"✅ Blockchain recalculada para {len(entradas)} entradas (ahora el hash incluye los minutos)")
