"""
Asigna minutos a las entradas creadas antes del cronómetro
y refirma la blockchain para que la cadena no se rompa.
"""
import sqlite3, hashlib, hmac

MINUTOS_POR_DEFECTO = 45   # <-- cambiá este número si querés otro

with open('.secreto') as f:
    clave = f.read().strip()

def calc_hash(fecha, t_id, desc, res, obs, mins=0):
    return hashlib.sha256(f"{fecha}|{t_id}|{desc}|{res}|{obs}|{mins}".encode()).hexdigest()

def calc_firma(h, k):
    return hmac.new(k.encode(), h.encode(), hashlib.sha256).hexdigest()

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Solo toca las entradas que no tienen minutos declarados (NULL o 0)
cur.execute('UPDATE entradas SET minutos = ? WHERE minutos IS NULL OR minutos = 0',
            (MINUTOS_POR_DEFECTO,))
afectadas = cur.rowcount
conn.commit()

# Refirmamos toda la cadena (el hash ahora incluye los minutos)
cur.execute('SELECT * FROM entradas ORDER BY id ASC')
hash_prev = None
for e in cur.fetchall():
    h = calc_hash(e['fecha'], e['tematica_id'], e['descripcion'] or '',
                  e['resumen'] or '', e['observaciones'] or '', e['minutos'] or 0)
    f = calc_firma(h, clave)
    cur.execute('UPDATE entradas SET hash=?, hash_previo=?, firma=? WHERE id=?',
                (h, hash_prev, f, e['id']))
    hash_prev = h
conn.commit()
conn.close()

print(f"✅ {afectadas} entrada(s) viejas ahora tienen {MINUTOS_POR_DEFECTO} min cada una")
print("🔐 Blockchain refirmada: cadena intacta")
