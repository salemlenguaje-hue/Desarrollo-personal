"""
Lógica de negocio del Diario de Capacitación.
Acá están todas las funciones que manejan rachas, niveles, compilados, etc.
AHORA CON BLOCKCHAIN: cada entrada tiene hash, hash previo y firma.
"""

import sqlite3
import hashlib
import hmac
import os
from datetime import datetime, timedelta

ARCHIVO_SECRETO = '.secreto'

def obtener_conexion():
    """
    Nos conectamos a la base de datos.
    Usamos row_factory para poder acceder a las columnas por nombre.
    """
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== BLOCKCHAIN: HASHES Y FIRMAS ====================

def cargar_clave_secreta():
    """
    Lee la clave maestra desde el archivo .secreto
    """
    if not os.path.exists(ARCHIVO_SECRETO):
        raise FileNotFoundError(
            f"No existe {ARCHIVO_SECRETO}. Corré primero: python generar_secreto.py"
        )
    with open(ARCHIVO_SECRETO, 'r') as f:
        return f.read().strip()

def calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones, minutos=0):
    """
    Calcula el hash SHA-256 de una entrada.
    Es la "huella digital" única de este contenido.
    """
    # Concatenamos todos los campos en un string
    contenido = f"{fecha}|{tematica_id}|{descripcion}|{resumen}|{observaciones}|{minutos}"
    # Calculamos el hash SHA-256
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()

def obtener_hash_ultima_entrada():
    """
    Devuelve el hash de la última entrada registrada.
    Si no hay entradas, devuelve None.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT hash FROM entradas 
        WHERE hash IS NOT NULL 
        ORDER BY id DESC 
        LIMIT 1
    ''')
    resultado = cursor.fetchone()
    conn.close()
    return resultado['hash'] if resultado else None

def calcular_firma(hash_entrada, clave_secreta):
    """
    Calcula la firma HMAC-SHA256 de un hash usando la clave secreta.
    Es tu "rúbrica digital" que solo vos podés generar.
    """
    return hmac.new(
        clave_secreta.encode('utf-8'),
        hash_entrada.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# ==================== GESTIÓN DE TEMÁTICAS ====================

def obtener_tematicas():
    """
    Devuelve todas las temáticas activas.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tematicas WHERE activa = 1 ORDER BY nombre')
    tematicas = cursor.fetchall()
    conn.close()
    return [dict(t) for t in tematicas]

def agregar_tematica(nombre):
    """
    Agrega una nueva temática si no existe.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO tematicas (nombre) VALUES (?)', (nombre,))
        conn.commit()
        conn.close()
        return True, "Temática agregada exitosamente"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Esa temática ya existe"

def eliminar_tematica(id_tematica):
    """
    Marca una temática como inactiva (no la borra para no perder historial).
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('UPDATE tematicas SET activa = 0 WHERE id = ?', (id_tematica,))
    conn.commit()
    conn.close()
    return True

# ==================== GESTIÓN DE TIPOS DE ESTUDIO ====================

def obtener_tipos_estudio():
    """
    Devuelve todos los tipos de estudio disponibles.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_estudio ORDER BY nombre')
    tipos = cursor.fetchall()
    conn.close()
    return [dict(t) for t in tipos]

# ==================== GESTIÓN DE ENTRADAS (CON BLOCKCHAIN) ====================

def guardar_entrada(fecha, tematica_id, descripcion, tipos, resumen, observaciones, minutos=0):
    """
    Guarda una nueva entrada de estudio CON BLOCKCHAIN.
    Calcula hash, hash previo y firma automáticamente.
    """
    # Calculamos el hash de esta entrada
    hash_entrada = calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones, minutos)
    
    # Obtenemos el hash de la entrada anterior (para encadenar)
    hash_previo = obtener_hash_ultima_entrada()
    
    # Calculamos la firma con la clave secreta
    clave_secreta = cargar_clave_secreta()
    firma = calcular_firma(hash_entrada, clave_secreta)
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Insertamos la entrada con los campos de blockchain
    cursor.execute('''
        INSERT INTO entradas (fecha, tematica_id, descripcion, resumen, observaciones, minutos,
                              hash, hash_previo, firma)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, tematica_id, descripcion, resumen, observaciones, minutos,
          hash_entrada, hash_previo, firma))
    
    entrada_id = cursor.lastrowid
    
    # Relacionamos la entrada con sus tipos de estudio
    for tipo_id in tipos:
        cursor.execute('''
            INSERT INTO entrada_tipos (entrada_id, tipo_id)
            VALUES (?, ?)
        ''', (entrada_id, tipo_id))
    
    conn.commit()
    conn.close()
    
    # Actualizamos la racha
    actualizar_racha()
    
    return entrada_id

def obtener_entradas_hoy():
    """
    Devuelve todas las entradas del día de hoy.
    """
    hoy = datetime.now().strftime('%Y-%m-%d')
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.*, t.nombre as tematica_nombre,
               GROUP_CONCAT(te.nombre, ', ') as tipos_nombres
        FROM entradas e
        JOIN tematicas t ON e.tematica_id = t.id
        LEFT JOIN entrada_tipos et ON e.id = et.entrada_id
        LEFT JOIN tipos_estudio te ON et.tipo_id = te.id
        WHERE e.fecha = ?
        GROUP BY e.id
        ORDER BY e.fecha_creacion DESC
    ''', (hoy,))
    
    entradas = cursor.fetchall()
    conn.close()
    return [dict(e) for e in entradas]

def obtener_entradas_por_rango(fecha_inicio, fecha_fin):
    """
    Devuelve todas las entradas entre dos fechas.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.*, t.nombre as tematica_nombre,
               GROUP_CONCAT(te.nombre, ', ') as tipos_nombres
        FROM entradas e
        JOIN tematicas t ON e.tematica_id = t.id
        LEFT JOIN entrada_tipos et ON e.id = et.entrada_id
        LEFT JOIN tipos_estudio te ON et.tipo_id = te.id
        WHERE e.fecha BETWEEN ? AND ?
        GROUP BY e.id
        ORDER BY e.fecha DESC, e.fecha_creacion DESC
    ''', (fecha_inicio, fecha_fin))
    
    entradas = cursor.fetchall()
    conn.close()
    return [dict(e) for e in entradas]

# ==================== SISTEMA DE RACHAS Y NIVELES ====================

def obtener_configuracion():
    """
    Devuelve toda la configuración como un diccionario.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('SELECT clave, valor FROM configuracion')
    config = {row['clave']: row['valor'] for row in cursor.fetchall()}
    conn.close()
    return config

def actualizar_configuracion(clave, valor):
    """
    Actualiza un valor de configuración.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE configuracion SET valor = ? WHERE clave = ?
    ''', (valor, clave))
    conn.commit()
    conn.close()

def calcular_nivel(racha):
    """
    Devuelve el nivel actual (1 a 8) según la racha.
    La idea: cada nivel tiene una META de días que alcanzar.
    Cuando llegás a la meta, subís al siguiente nivel.
    Nivel 1: meta 7   | Nivel 2: meta 14  | Nivel 3: meta 21
    Nivel 4: meta 30  | Nivel 5: meta 60  | Nivel 6: meta 90
    Nivel 7: meta 180 | Nivel 8: meta 365
    """
    metas = [7, 14, 21, 30, 60, 90, 180, 365]
    completadas = sum(1 for meta in metas if racha >= meta)
    # Si completaste las 8 metas, quedás en el nivel 8 (tope)
    return min(completadas + 1, 8)


def actualizar_racha():
    """
    Actualiza la racha de estudio según las reglas:
    - Suma 1 día si hoy no se había estudiado aún
    - Usa día de descanso si es necesario
    - Vuelve a cero si se pasa el límite
    """
    config = obtener_configuracion()
    hoy = datetime.now().strftime('%Y-%m-%d')
    ultimo_dia = config.get('ultimo_dia_estudio', '')
    
    if ultimo_dia == hoy:
        # Ya se actualizó hoy, no hacemos nada
        return
    
    # Calculamos cuántos días pasaron desde el último estudio
    if ultimo_dia:
        dias_paso = (datetime.strptime(hoy, '%Y-%m-%d') - 
                     datetime.strptime(ultimo_dia, '%Y-%m-%d')).days
    else:
        dias_paso = 1
    
    racha_actual = int(config.get('racha_actual', 0))
    mejor_racha = int(config.get('mejor_racha', 0))
    dias_descanso = int(config.get('dias_descanso_usados', 0))
    
    if dias_paso == 1:
        # Día consecutivo normal
        racha_actual += 1
        dias_descanso = 0  # Reseteamos el contador de descanso
    elif dias_paso == 2 and dias_descanso < 1:
        # Usamos el día de descanso semanal
        racha_actual += 1
        dias_descanso += 1
    else:
        # Se cortó la racha, volvemos a cero
        racha_actual = 1
        dias_descanso = 0
    
    # Actualizamos mejor racha si corresponde
    if racha_actual > mejor_racha:
        mejor_racha = racha_actual
    
    # Calculamos el nivel actual
    nivel = calcular_nivel(racha_actual)
    
    # Guardamos todo
    actualizar_configuracion('racha_actual', str(racha_actual))
    actualizar_configuracion('mejor_racha', str(mejor_racha))
    actualizar_configuracion('ultimo_dia_estudio', hoy)
    actualizar_configuracion('dias_descanso_usados', str(dias_descanso))
    actualizar_configuracion('nivel_actual', str(nivel))

def obtener_estadisticas():
    """
    Devuelve estadísticas completas para la página de análisis.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    config = obtener_configuracion()
    
    # Entradas por día (últimos 30 días)
    cursor.execute('''
        SELECT fecha, COALESCE(SUM(minutos), 0) as minutos
        FROM entradas
        WHERE fecha >= date('now', '-30 days')
        GROUP BY fecha
        ORDER BY fecha
    ''')
    entradas_por_dia = cursor.fetchall()
    
    # Distribución por temática
    cursor.execute('''
        SELECT t.nombre, COALESCE(SUM(e.minutos), 0) as minutos
        FROM entradas e
        JOIN tematicas t ON e.tematica_id = t.id
        GROUP BY t.id
        ORDER BY minutos DESC
    ''')
    por_tematica = cursor.fetchall()
    
    # Distribución por tipo de estudio
    cursor.execute('''
        SELECT te.nombre, COALESCE(SUM(e.minutos), 0) as minutos
        FROM entrada_tipos et
        JOIN tipos_estudio te ON et.tipo_id = te.id
        JOIN entradas e ON et.entrada_id = e.id
        GROUP BY te.id
        ORDER BY minutos DESC
    ''')
    por_tipo = cursor.fetchall()
    
    # Calendario de actividad (últimos 365 días)
    cursor.execute('''
        SELECT fecha, COUNT(*) as cantidad
        FROM entradas
        WHERE fecha >= date('now', '-365 days')
        GROUP BY fecha
        ORDER BY fecha
    ''')
    calendario = cursor.fetchall()
    
    conn.close()
    
    return {
        'racha_actual': int(config.get('racha_actual', 0)),
        'mejor_racha': int(config.get('mejor_racha', 0)),
        'nivel_actual': int(config.get('nivel_actual', 1)),
        'entradas_por_dia': [dict(row) for row in entradas_por_dia],
        'por_tematica': [dict(row) for row in por_tematica],
        'por_tipo': [dict(row) for row in por_tipo],
        'calendario': [dict(row) for row in calendario]
    }

# ==================== COMPILADO DEL DÍA (CON BLOCKCHAIN) ====================

def generar_compilado_hoy():
    """
    Genera un texto resumen de todas las entradas del día.
    INCLUYE LA CADENA DE BLOCKCHAIN (hash, previo, firma).
    """
    config = obtener_configuracion()
    entradas = obtener_entradas_hoy()
    hoy = datetime.now().strftime('%d/%m/%Y')
    
    compilado = f"""📚 Diario de Capacitación — {hoy}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 Racha actual: {config.get('racha_actual', 0)} días (Nivel {config.get('nivel_actual', 1)})
🏆 Mejor racha: {config.get('mejor_racha', 0)} días

📝 Sesiones del día:
"""
    
    if not entradas:
        compilado += "\n⚠️ No hay entradas registradas hoy.\n"
        return compilado
    
    # Agrupamos por temática
    tematicas_estudiadas = {}
    for entrada in entradas:
        nombre_tematica = entrada['tematica_nombre']
        if nombre_tematica not in tematicas_estudiadas:
            tematicas_estudiadas[nombre_tematica] = []
        tematicas_estudiadas[nombre_tematica].append(entrada)
    
    for tematica, entradas_tematica in tematicas_estudiadas.items():
        compilado += f"\n🎓 {tematica}\n"
        for entrada in entradas_tematica:
            tipos = entrada.get('tipos_nombres', 'No especificado')
            compilado += f"   • Tipo: {tipos}\n"
            if entrada.get('resumen'):
                compilado += f"   • Resumen: {entrada['resumen']}\n"
            if entrada.get('observaciones'):
                compilado += f"   • Observaciones: {entrada['observaciones']}\n"
            
            # Mostramos la cadena de blockchain
            if entrada.get('hash'):
                compilado += f"   🔒 Hash:      {entrada['hash'][:24]}...\n"
            if entrada.get('hash_previo'):
                compilado += f"   🔗 Previo:    {entrada['hash_previo'][:24]}...\n"
            elif entrada.get('hash'):
                compilado += f"   🔗 Previo:    (primera entrada)\n"
            if entrada.get('firma'):
                compilado += f"   ✍️  Firma:     {entrada['firma'][:24]}...\n"
    
    compilado += f"\nTotal: {len(tematicas_estudiadas)} temáticas estudiadas hoy"
    
    return compilado

# ==================== CALENDARIO DE ACTIVIDAD ====================

def obtener_calendario_actividad():
    """
    Devuelve un calendario tipo GitHub (cuadraditos verdes) de los últimos 365 días.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Obtenemos las fechas con actividad de los últimos 365 días
    cursor.execute('''
        SELECT fecha, COUNT(*) as cantidad
        FROM entradas
        WHERE fecha >= date('now', '-365 days')
        GROUP BY fecha
    ''')
    
    actividad = {row['fecha']: row['cantidad'] for row in cursor.fetchall()}
    conn.close()
    
    # Generamos el calendario completo (365 días)
    calendario = []
    hoy = datetime.now()
    
    for i in range(365):
        fecha = hoy - timedelta(days=i)
        fecha_str = fecha.strftime('%Y-%m-%d')
        cantidad = actividad.get(fecha_str, 0)
        
        # Determinamos el nivel de intensidad (0-4)
        if cantidad == 0:
            nivel = 0
        elif cantidad == 1:
            nivel = 1
        elif cantidad == 2:
            nivel = 2
        elif cantidad <= 4:
            nivel = 3
        else:
            nivel = 4
        
        calendario.append({
            'fecha': fecha_str,
            'cantidad': cantidad,
            'nivel': nivel
        })
    
    # Invertimos para que el día más antiguo vaya primero
    calendario.reverse()
    return calendario

# ==================== VALIDACIÓN DE BLOCKCHAIN ====================

def validar_blockchain():
    """
    Revisa toda la cadena de entradas para asegurar que nadie tocó nada.
    Vuelve a calcular hashes y firmas y las compara con las guardadas.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, fecha, tematica_id, descripcion, resumen, observaciones, minutos, 
               hash, hash_previo, firma 
        FROM entradas ORDER BY id ASC
    ''')
    entradas = cursor.fetchall()
    conn.close()

    if not entradas:
        return {'ok': True, 'mensaje': 'No hay entradas para validar todavía.', 'total': 0, 'validadas': 0}

    clave_secreta = cargar_clave_secreta()
    hash_previo_esperado = None
    validadas = 0
    errores = []

    for entrada in entradas:
        # 1. Recalcular el hash del contenido (¿alguien cambió el texto?)
        hash_calc = calcular_hash_entrada(
            entrada['fecha'], entrada['tematica_id'], 
            entrada['descripcion'] or '', entrada['resumen'] or '', 
            entrada['observaciones'] or '', entrada['minutos'] or 0
        )
        
        if hash_calc != entrada['hash']:
            errores.append(f"Entrada ID {entrada['id']}: El contenido fue modificado.")
            continue

        # 2. Verificar el eslabón con la entrada anterior (¿se borró una entrada del medio?)
        if entrada['hash_previo'] != hash_previo_esperado:
            errores.append(f"Entrada ID {entrada['id']}: La cadena se rompió.")
            continue

        # 3. Verificar tu firma digital (¿es realmente tu rúbrica?)
        firma_calc = calcular_firma(hash_calc, clave_secreta)
        if firma_calc != entrada['firma']:
            errores.append(f"Entrada ID {entrada['id']}: La firma digital no es válida.")
            continue

        # Si pasa las 3 pruebas, es válida
        validadas += 1
        hash_previo_esperado = entrada['hash']

    if errores:
        return {
            'ok': False, 
            'mensaje': f'⚠️ Alerta: Se encontraron {len(errores)} anomalías en la cadena.', 
            'errores': errores, 
            'total': len(entradas), 
            'validadas': validadas
        }
    
    return {
        'ok': True, 
        'mensaje': f'✅ Cadena intacta: {validadas} entradas verificadas con éxito. Nadie tocó nada.', 
        'total': len(entradas), 
        'validadas': validadas
    }

# ==================== TUTOR IA: SIBELI ====================

import requests  # la librería que manda pedidos por internet
import time      # pausas de reintento cuando Gemini está saturado

ARCHIVO_CLAVE_GEMINI = '.gemini_key'
# Si algún día un modelo se jubila, agregá el nuevo acá arriba de todo
MODELOS_GEMINI = ['gemini-flash-latest', 'gemini-pro-latest', 'gemini-2.5-flash', 'gemini-2.5-pro']

def cargar_clave_gemini():
    """Lee tu llave secreta de Gemini."""
    if not os.path.exists(ARCHIVO_CLAVE_GEMINI):
        return None
    with open(ARCHIVO_CLAVE_GEMINI, 'r') as f:
        return f.read().strip()

def asegurar_tabla_chats():
    """Crea la tablita de charlas si no existe (separada de la blockchain)."""
    conn = obtener_conexion()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rol TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def guardar_chat(rol, mensaje):
    """Guarda un mensaje de la charla (rol: 'usuario' o 'tutor').
    Devuelve el ID del mensaje recién guardado (para los botones del chat)."""
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute('INSERT INTO chats (rol, mensaje) VALUES (?, ?)', (rol, mensaje))
    nuevo_id = cur.lastrowid
    conn.commit()
    conn.close()
    return nuevo_id

def obtener_historial_chat():
    """Devuelve toda la charla en orden, con ID y favorito, para pintarla."""
    conn = obtener_conexion()
    cur = conn.cursor()
    # Si la columna favorito todavía no existe, la creamos al vuelo
    try:
        cur.execute('ALTER TABLE chats ADD COLUMN favorito INTEGER DEFAULT 0')
        conn.commit()
    except Exception:
        pass  # ya existía, seguimos de largo
    cur.execute('SELECT id, rol, mensaje, favorito FROM chats ORDER BY id ASC')
    filas = cur.fetchall()
    conn.close()
    return [dict(f) for f in filas]

def construir_contexto():
    """
    EL SUPERPODER: arma un resumen de TU diario (racha, temáticas y
    entradas de la última semana) para que el tutor responda con tu material.
    """
    config = obtener_configuracion()
    tematicas = [t['nombre'] for t in obtener_tematicas()]

    desde = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    hasta = datetime.now().strftime('%Y-%m-%d')
    entradas = obtener_entradas_por_rango(desde, hasta)[:15]  # tope para no marear al cerebro

    lineas = []
    for e in entradas:
        lineas.append(
            f"- {e['fecha']} | {e['tematica_nombre']} | Tipos: {e['tipos_nombres']} | "
            f"Resumen: {e['resumen'] or '-'} | Obs: {e['observaciones'] or '-'}"
        )

    return (
        f"Racha actual: {config.get('racha_actual', 0)} días. Nivel: {config.get('nivel_actual', 1)}.\n"
        f"Temáticas activas: {', '.join(tematicas) or 'ninguna'}.\n"
        "Entradas de los últimos 7 días:\n" +
        (chr(10).join(lineas) or '(sin entradas recientes)')
    )

def preguntar_gemini(mensaje_usuario, profundidad='normal'):
    """
    Manda la pregunta al cerebro de Sibeli (servicio Gemini por debajo)
    y devuelve (ok, respuesta).
    Le pasamos los últimos mensajes de la charla para que haya conversación.
    """
    clave = cargar_clave_gemini()
    if not clave:
        return False, 'Falta la clave de Sibeli: guardala en el archivo .gemini_key'

    # Armamos la conversación previa (últimos 10 mensajes)
    historial = obtener_historial_chat()[-10:]
    contents = []
    for h in historial:
        rol = 'user' if h['rol'] == 'usuario' else 'model'
        # Gemini exige turnos alternados: si se repite el rol, juntamos los mensajes
        if contents and contents[-1]['role'] == rol:
            contents[-1]['parts'][0]['text'] += '\n' + h['mensaje']
        else:
            contents.append({'role': rol, 'parts': [{'text': h['mensaje']}]})
    if contents and contents[0]['role'] != 'user':
        contents.pop(0)  # la charla debe empezar con vos

    # Sumamos tu pregunta de ahora
    if contents and contents[-1]['role'] == 'user':
        contents[-1]['parts'][0]['text'] += '\n' + mensaje_usuario
    else:
        contents.append({'role': 'user', 'parts': [{'text': mensaje_usuario}]})

    # Las instrucciones de quién es el tutor (con tu diario adentro)
    # Ajustamos el tono según la profundidad elegida
    # Usamos el parámetro que ya recibimos
    
    tonos = {
        'superficial': 'Ofrecé una síntesis ejecutiva: dos o tres oraciones precisas, sin rodeos. ',
        'normal': 'Exponé los conceptos con claridad y orden, en lenguaje accesible pero preciso. ',
        'profundo': 'Desarrollá el tema en profundidad: fundamentos, causas, ejemplos prácticos y conexiones con otros contenidos del diario. ',
        'ultra': 'Exponé con rigor académico: terminología técnica exacta, formulaciones cuando corresponda y análisis crítico. '
    }

    sistema = (
        'Sos Sibeli, la tutora académica personal de Martín. '
        'Tu registro es profesional, sereno y estimulante: explicás con precisión '
        'universitaria y calidez humana, sin coloquialismos excesivos ni exclamaciones gratuitas. '
        'Usás español rioplatense (voseo) con vocabulario cuidado. '
        'Estructurás las respuestas con títulos y listas cuando aportan claridad. ' +
        tonos.get(profundidad, tonos['normal']) +
        'Personalizás cada respuesta con el contexto de su diario de estudio. '
        'Si te pide que le tomés lección, formulás UNA pregunta por vez y esperás su respuesta. '
        'Contexto del diario de Martín:\n' + construir_contexto()
    )

    datos = {'profundidad': profundidad}
    cuerpo = {
        'systemInstruction': {'parts': [{'text': sistema}]},
        'contents': contents,
    }

    url_base = 'https://generativelanguage.googleapis.com/v1beta/models/'
    ultimo_error = ''
    for modelo in MODELOS_GEMINI:
        # Hasta 2 intentos por modelo: los 503/429 son saturaciones temporarias
        for intento in range(3):
            try:
                r = requests.post(
                    url_base + modelo + ':generateContent',
                    headers={'x-goog-api-key': clave, 'Content-Type': 'application/json'},
                    json=cuerpo,
                    timeout=60
                )
                if r.status_code == 404:   # modelo inexistente: probamos el siguiente
                    ultimo_error = f'modelo {modelo} no disponible'
                    break
                if r.status_code in (429, 503):  # saturado: respiramos y reintentamos
                    ultimo_error = f'{modelo} saturado (HTTP {r.status_code})'
                    time.sleep(2 + intento * 2)  # pausa creciente: 2s, 4s, 6s
                    continue
                if r.status_code != 200:
                    return False, f'Sibeli no pudo responder (error {r.status_code}): {r.text[:200]}'
                datos = r.json()
                texto = datos['candidates'][0]['content']['parts'][0]['text']
                return True, texto
            except Exception as e:
                ultimo_error = str(e)
                time.sleep(2)

    return False, ('Sibeli está con mucha demanda ahora mismo (probé todos sus '
                   'cerebros con reintentos). Último error: {ultimo_error}. '
                   'Esperá un minutito y tocá 🔄 Reintentar.')

# ==================== MEJORAS DEL TUTOR ====================

def buscar_en_chat(texto_busqueda):
    """Busca mensajes que contengan el texto (case insensitive)."""
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, rol, mensaje, fecha_creacion 
        FROM chats 
        WHERE LOWER(mensaje) LIKE LOWER(?)
        ORDER BY id ASC
    ''', (f'%{texto_busqueda}%',))
    resultados = cur.fetchall()
    conn.close()
    return [dict(r) for r in resultados]

def borrar_historial_chat():
    """Borra toda la charla (útil para empezar de nuevo)."""
    conn = obtener_conexion()
    conn.execute('DELETE FROM chats')
    conn.commit()
    conn.close()
    return True

def marcar_favorito(id_mensaje, es_favorito):
    """Marca o desmarca un mensaje como favorito."""
    conn = obtener_conexion()
    # Verificamos que la columna existe, si no la creamos
    try:
        conn.execute('ALTER TABLE chats ADD COLUMN favorito INTEGER DEFAULT 0')
        conn.commit()
    except:
        pass  # ya existía
    
    conn.execute('UPDATE chats SET favorito = ? WHERE id = ?', (1 if es_favorito else 0, id_mensaje))
    conn.commit()
    conn.close()
    return True

def exportar_chat_markdown():
    """Genera un Markdown con toda la charla."""
    historial = obtener_historial_chat()
    if not historial:
        return "# Chat vacío\n\nNo hay mensajes para exportar."
    
    md = "# 💬 Conversación con Sibeli\n\n"
    md += f"**Usuario:** Martín  \n"
    md += f"**Fecha de exportación:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    md += "---\n\n"
    
    for msg in historial:
        if msg['rol'] == 'usuario':
            md += f"## 👤 Martín\n\n{msg['mensaje']}\n\n"
        else:
            md += f"## ✨ Sibeli\n\n{msg['mensaje']}\n\n"
        md += "---\n\n"
    
    return md

def generar_sugerencias_seguimiento(ultimo_mensaje_tutor):
    """
    Genera 3 preguntas de seguimiento basadas en la última respuesta del tutor.
    (Esto es un placeholder: en producción usaríamos otro call a Gemini)
    """
    # Por ahora devolvemos sugerencias genéricas
    return [
        "¿Podés darme un ejemplo práctico?",
        "¿Cómo se relaciona esto con lo que estudié ayer?",
        "¿Qué debería estudiar después de esto?"
    ]

# ==================== TROFEOS Y LOGROS ====================

def asegurar_tabla_trofeos(conn):
    """Crea la tablita de trofeos desbloqueados si no existe."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trofeos (
            id_trofeo TEXT PRIMARY KEY,
            fecha DATE NOT NULL
        )
    ''')

def _dato_total(consulta):
    """Atajo para consultas que devuelven un solo número."""
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute(consulta)
    valor = cur.fetchone()[0]
    conn.close()
    return valor or 0

def obtener_trofeos():
    """
    La vitrina de medallas: cada trofeo se calcula con datos REALES
    del diario (rachas, entradas, minutos, temáticas).
    Los que se desbloquean hoy quedan anotados con fecha y con el
    sello 'nuevo' para que la página los festeje con un toast.
    """
    config = obtener_configuracion()
    mejor_racha = int(config.get('mejor_racha', 0))
    total_entradas = _dato_total('SELECT COUNT(*) FROM entradas')
    total_minutos = _dato_total('SELECT COALESCE(SUM(minutos), 0) FROM entradas')
    total_tematicas = _dato_total('SELECT COUNT(DISTINCT tematica_id) FROM entradas')

    # (id, emoji, nombre, cómo se gana, condición real)
    definiciones = [
        ('primer_paso',  '🌱', 'Primer paso',      'Registraste tu primera sesión de estudio.', total_entradas >= 1),
        ('racha_7',      '🔥', 'Semana ardiente',  'Llegaste a 7 días de racha.',               mejor_racha >= 7),
        ('racha_14',     '⚡', 'Quincena',         'Llegaste a 14 días de racha.',              mejor_racha >= 14),
        ('racha_21',     '🎯', 'Hábito formado',   'Llegaste a 21 días de racha.',              mejor_racha >= 21),
        ('racha_30',     '🛡️', 'Imparable',        'Llegaste a 30 días de racha.',              mejor_racha >= 30),
        ('racha_60',     '🔮', 'Visionario',       'Llegaste a 60 días de racha.',              mejor_racha >= 60),
        ('racha_90',     '👑', 'Realeza',          'Llegaste a 90 días de racha.',              mejor_racha >= 90),
        ('racha_365',    '♾️', 'Infinito SALEM',   'Llegaste a 365 días de racha.',             mejor_racha >= 365),
        ('entradas_10',  '📚', 'Coleccionista',    'Registraste 10 entradas de estudio.',       total_entradas >= 10),
        ('entradas_50',  '🗂️', 'Archivista',       'Registraste 50 entradas de estudio.',       total_entradas >= 50),
        ('entradas_100', '🏛️', 'Biblioteca viva',  'Registraste 100 entradas de estudio.',      total_entradas >= 100),
        ('hora_1',       '⏱️', 'Primera hora',     'Acumulaste 60 minutos de estudio.',         total_minutos >= 60),
        ('horas_10',     '⌛', 'Señor del tiempo', 'Acumulaste 10 horas de estudio.',           total_minutos >= 600),
        ('horas_50',     '🕰️', 'Maratonista',      'Acumulaste 50 horas de estudio.',           total_minutos >= 3000),
        ('multitema',    '🎨', 'Renacentista',     'Estudiaste 3 temáticas distintas.',         total_tematicas >= 3),
    ]

    conn = obtener_conexion()
    cur = conn.cursor()
    asegurar_tabla_trofeos(conn)
    conn.commit()
    cur.execute('SELECT id_trofeo, fecha FROM trofeos')
    ya_desbloqueados = {fila['id_trofeo']: fila['fecha'] for fila in cur.fetchall()}

    hoy = datetime.now().strftime('%Y-%m-%d')
    resultado = []
    for id_trofeo, emoji, nombre, descripcion, logrado in definiciones:
        fecha = ya_desbloqueados.get(id_trofeo)
        nuevo = False
        if logrado and fecha is None:
            # ¡Acaba de desbloquearse! Lo anotamos con fecha de hoy
            fecha = hoy
            nuevo = True
            cur.execute('INSERT INTO trofeos (id_trofeo, fecha) VALUES (?, ?)', (id_trofeo, hoy))
        resultado.append({
            'id': id_trofeo,
            'emoji': emoji,
            'nombre': nombre,
            'descripcion': descripcion,
            'desbloqueado': logrado,
            'fecha': fecha,
            'nuevo': nuevo,
        })
    conn.commit()
    conn.close()
    return resultado
