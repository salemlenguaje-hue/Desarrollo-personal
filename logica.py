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

def calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones):
    """
    Calcula el hash SHA-256 de una entrada.
    Es la "huella digital" única de este contenido.
    """
    # Concatenamos todos los campos en un string
    contenido = f"{fecha}|{tematica_id}|{descripcion}|{resumen}|{observaciones}"
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

def guardar_entrada(fecha, tematica_id, descripcion, tipos, resumen, observaciones):
    """
    Guarda una nueva entrada de estudio CON BLOCKCHAIN.
    Calcula hash, hash previo y firma automáticamente.
    """
    # Calculamos el hash de esta entrada
    hash_entrada = calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones)
    
    # Obtenemos el hash de la entrada anterior (para encadenar)
    hash_previo = obtener_hash_ultima_entrada()
    
    # Calculamos la firma con la clave secreta
    clave_secreta = cargar_clave_secreta()
    firma = calcular_firma(hash_entrada, clave_secreta)
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Insertamos la entrada con los campos de blockchain
    cursor.execute('''
        INSERT INTO entradas (fecha, tematica_id, descripcion, resumen, observaciones,
                              hash, hash_previo, firma)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, tematica_id, descripcion, resumen, observaciones,
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
        SELECT fecha, COUNT(*) as cantidad
        FROM entradas
        WHERE fecha >= date('now', '-30 days')
        GROUP BY fecha
        ORDER BY fecha
    ''')
    entradas_por_dia = cursor.fetchall()
    
    # Distribución por temática
    cursor.execute('''
        SELECT t.nombre, COUNT(e.id) as cantidad
        FROM entradas e
        JOIN tematicas t ON e.tematica_id = t.id
        GROUP BY t.id
        ORDER BY cantidad DESC
    ''')
    por_tematica = cursor.fetchall()
    
    # Distribución por tipo de estudio
    cursor.execute('''
        SELECT te.nombre, COUNT(et.entrada_id) as cantidad
        FROM entrada_tipos et
        JOIN tipos_estudio te ON et.tipo_id = te.id
        GROUP BY te.id
        ORDER BY cantidad DESC
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
        SELECT id, fecha, tematica_id, descripcion, resumen, observaciones, 
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
            entrada['observaciones'] or ''
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
