"""
=====================================================
 SERVIDOR WEB — Diario de Capacitación y Desarrollo
=====================================================
Este archivo es el "mozo del restaurante": recibe los pedidos
del navegador (páginas, botones tocados) y los lleva a la
cocina (logica.py y la base de datos).

Para correrlo:   python server.py
Para entrar:     http://localhost:2527
"""

import hashlib     # convierte la contraseña en un código secreto (hash)
import os          # para manejar carpetas y archivos
import socket      # para averiguar la IP de tu celular en la WiFi
import subprocess  # para ejecutar comandos de Git desde acá
from datetime import datetime
from functools import wraps  # nos deja crear nuestro "candado" de login

from flask import (Flask, jsonify, redirect, render_template,
                   request, session, url_for)

import logica  # nuestro archivo con toda la lógica del diario

# ------------------ CONFIGURACIÓN BÁSICA ------------------

app = Flask(__name__)

# Frase secreta para que Flask firme las sesiones (las "cookies").
# Que nadie más la conozca no importa tanto: es uso personal.
app.secret_key = 'salem-diario-clave-super-secreta-2026'

# El puerto que elegiste para ESTE servicio (cada servicio tuyo tiene el suyo)
PUERTO = 2527


def ip_local():
    """
    Averigua la IP de tu celular dentro de tu red WiFi,
    para que puedas entrar desde el celu de tu esposa.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))  # conexión de mentira, solo para saber la IP
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


# ------------------ EL "CANDADO" DE LOGIN ------------------

def login_requerido(funcion):
    """
    Candado: envuelve una ruta para que SOLO se pueda entrar
    si ya te logueaste. Si no, te manda al login.
    """
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return funcion(*args, **kwargs)
    return envoltura


# ------------------ PÁGINAS (lo que ve el navegador) ------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Puerta de entrada: usuario y contraseña."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = logica.obtener_conexion()
        cur = conn.cursor()
        cur.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
        usuario = cur.fetchone()
        conn.close()

        if usuario:
            guardada = usuario['password_hash']
            ingresada = hashlib.sha256(password.encode()).hexdigest()
            # MODO DESARROLLO: si todavía no hay contraseña guardada
            # (campo vacío), entra con cualquier cosa.
            # Cuando estrenemos, acá mismo se comparará el hash real.
            if guardada == '' or guardada == ingresada:
                session['usuario'] = username
                return redirect(url_for('index'))

        return render_template('login.html',
                               error='Usuario o contraseña incorrectos')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Cierra la sesión y vuelve al login."""
    session.pop('usuario', None)
    return redirect(url_for('login'))


@app.route('/')
@login_requerido
def index():
    """Página principal: racha, panel de control y botones de compartir."""
    return render_template('index.html',
                           config=logica.obtener_configuracion(),
                           tematicas=logica.obtener_tematicas(),
                           tipos=logica.obtener_tipos_estudio(),
                           entradas_hoy=logica.obtener_entradas_hoy(),
                           usuario=session['usuario'])


@app.route('/analisis')
@login_requerido
def analisis():
    """Página de gráficos y estadísticas (imprimible en PDF)."""
    return render_template('analytics.html', usuario=session['usuario'])


# ------------------ VENTANITAS DE DATOS (API) ------------------
# Las usa el JavaScript de las páginas para guardar y pedir cosas
# sin recargar todo el navegador.

@app.route('/api/tematicas', methods=['GET', 'POST'])
@login_requerido
def api_tematicas():
    """Lista o agrega temáticas."""
    if request.method == 'POST':
        datos = request.get_json()
        ok, mensaje = logica.agregar_tematica(datos.get('nombre', '').strip())
        return jsonify({'ok': ok, 'mensaje': mensaje})
    return jsonify(logica.obtener_tematicas())


@app.route('/api/tematicas/<int:id_tematica>', methods=['DELETE'])
@login_requerido
def api_borrar_tematica(id_tematica):
    """Desactiva una temática (no borra su historial)."""
    logica.eliminar_tematica(id_tematica)
    return jsonify({'ok': True, 'mensaje': 'Temática desactivada'})


@app.route('/api/entradas', methods=['POST'])
@login_requerido
def api_guardar_entrada():
    """Guarda una entrada de estudio de HOY (la fecha no se elige: disciplina 💪)."""
    datos = request.get_json()
    hoy = datetime.now().strftime('%Y-%m-%d')

    logica.guardar_entrada(
        fecha=hoy,
        tematica_id=datos.get('tematica_id'),
        descripcion=datos.get('descripcion', ''),
        tipos=datos.get('tipos', []),          # lista de IDs de tipos
        resumen=datos.get('resumen', ''),
        observaciones=datos.get('observaciones', ''),
        minutos=int(datos.get('minutos', 0) or 0)
    )
    return jsonify({'ok': True, 'mensaje': '¡Entrada guardada! La racha ya lo siente 🔥'})


@app.route('/api/entradas/hoy')
@login_requerido
def api_entradas_hoy():
    """Devuelve las entradas del día."""
    return jsonify(logica.obtener_entradas_hoy())


@app.route('/api/estadisticas')
@login_requerido
def api_estadisticas():
    """Números para los gráficos, filtrados por período si vienen fechas."""
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    return jsonify(logica.obtener_estadisticas(desde, hasta))


@app.route('/api/calendario')
@login_requerido
def api_calendario():
    """Calendario tipo GitHub (cuadraditos de actividad)."""
    return jsonify(logica.obtener_calendario_actividad())


@app.route('/api/compilado')
@login_requerido
def api_compilado():
    """El resumen del día en texto, listo para WhatsApp o email."""
    return jsonify({'texto': logica.generar_compilado_hoy()})


@app.route('/api/github', methods=['POST'])
@login_requerido
def subir_a_github():
    hoy = datetime.now().strftime('%Y-%m-%d')
    compilado = logica.generar_compilado_hoy()

    os.makedirs('compilados', exist_ok=True)
    with open(os.path.join('compilados', f'{hoy}.md'), 'w', encoding='utf-8') as archivo:
        archivo.write(compilado + '\n')

    pasos = [
        (['git', 'add', '-A'], 'preparar archivos'),
        (['git', 'commit', '-m', f'Diario: compilado del dia {hoy}'], 'guardar cambio'),
        (['git', 'push', 'origin', 'main'], 'subir a GitHub'),
    ]

    for comando, descripcion in pasos:
        resultado = subprocess.run(comando, capture_output=True, text=True)
        salida = (resultado.stdout + resultado.stderr).strip()
        
        if resultado.returncode != 0 and 'nothing to commit' not in salida:
            # IMPRESO EN LA CONSOLA DE TERMUX PARA QUE LO VEAS
            print(f"\n❌ ERROR GIT AL {descripcion.upper()}:")
            print(salida)
            print("-" * 40)
            
            # Mensaje corto y claro para la web
            error_corto = salida.split('\n')[-1] if salida else 'Error desconocido'
            return jsonify({'ok': False, 'mensaje': f'Error al {descripcion}: {error_corto}'})

    return jsonify({'ok': True, 'mensaje': '¡Todo subido a GitHub! 🎉'})


# ------------------ ARRANQUE ------------------


@app.route('/api/validar_blockchain')
@login_requerido
def api_validar_blockchain():
    """Verifica que la cadena de hashes y firmas esté intacta."""
    return jsonify(logica.validar_blockchain())


# Aseguramos que exista la tablita de charlas al arrancar
logica.asegurar_tabla_chats()

@app.route('/tutor')
@login_requerido
def tutor():
    """La página del tutor con IA."""
    return render_template('tutor.html', usuario=session['usuario'])

@app.route('/api/historial')
@login_requerido
def api_historial():
    """Devuelve la charla completa para pintarla en la página."""
    return jsonify(logica.obtener_historial_chat())

@app.route('/api/chat', methods=['POST'])
@login_requerido
def api_chat():
    """Recibe tu pregunta, la guarda, consulta a Gemini y guarda la respuesta."""
    datos = request.get_json()
    mensaje = (datos.get('mensaje') or '').strip()
    if not mensaje:
        return jsonify({'ok': False, 'mensaje': 'El mensaje vino vacío.'})

    try:
        logica.guardar_chat('usuario', mensaje)
        profundidad = datos.get('profundidad', 'normal')
        documentos = datos.get('documentos', [])
        ok, respuesta, docs_usados = logica.preguntar_gemini(mensaje, profundidad, documentos)

        if not ok:
            return jsonify({'ok': False, 'mensaje': respuesta})

        # Si Sibeli escribió bloques de taller, se guardan y salen de la respuesta
        respuesta, avisos_taller = logica.extraer_y_guardar_bloques(respuesta)

        id_mensaje = logica.guardar_chat('tutor', respuesta)
        return jsonify({'ok': True, 'respuesta': respuesta, 'id_mensaje': id_mensaje,
                        'docs_usados': docs_usados, 'guardados': avisos_taller})
    except Exception as error:
        # Si algo explota, lo anotamos en la consola y respondemos amable
        print('❌ Error en /api/chat:', error)
        return jsonify({'ok': False, 'mensaje': 'Error interno del servidor: ' + str(error)})


@app.route('/api/chat/buscar')
@login_requerido
def api_buscar_chat():
    """Busca mensajes en el historial del chat."""
    texto = request.args.get('q', '').strip()
    if not texto:
        return jsonify([])
    return jsonify(logica.buscar_en_chat(texto))

@app.route('/api/chat/borrar', methods=['POST'])
@login_requerido
def api_borrar_chat():
    """Borra todo el historial del chat."""
    logica.borrar_historial_chat()
    return jsonify({'ok': True, 'mensaje': 'Historial borrado'})

@app.route('/api/chat/favorito/<int:id_mensaje>', methods=['POST'])
@login_requerido
def api_favorito(id_mensaje):
    """Marca o desmarca un mensaje como favorito."""
    datos = request.get_json()
    es_favorito = datos.get('favorito', False)
    logica.marcar_favorito(id_mensaje, es_favorito)
    return jsonify({'ok': True})

@app.route('/api/chat/exportar')
@login_requerido
def api_exportar_chat():
    """Devuelve el chat en formato Markdown para descargar."""
    md = logica.exportar_chat_markdown()
    return jsonify({'markdown': md})

@app.route('/api/chat/sugerencias')
@login_requerido
def api_sugerencias():
    """Devuelve sugerencias de preguntas de seguimiento."""
    return jsonify(logica.generar_sugerencias_seguimiento(''))


# ==================== TROFEOS ====================

@app.route('/api/trofeos')
@login_requerido
def api_trofeos():
    """Devuelve la vitrina de medallas con sus desbloqueos."""
    return jsonify(logica.obtener_trofeos())

# ==================== VIGILANTE DE LA RACHA ====================
import threading

HORA_RECORDATORIO = 20  # la hora en que suena la alarma si no estudiaste

def vigilante_de_racha():
    """
    Hilito que vive con el servidor: todos los días a la HORA_RECORDATORIO
    fija si hoy registraste alguna entrada. Si no, te manda una
    notificación al celular con termux-notification.
    """
    import subprocess
    import time as _time
    avisado_el = ''
    while True:
        ahora = datetime.now()
        dia = ahora.strftime('%Y-%m-%d')
        if ahora.hour == HORA_RECORDATORIO and avisado_el != dia:
            avisado_el = dia  # marcamos el día aunque falle, para no spamear
            try:
                if not logica.obtener_entradas_hoy():
                    subprocess.run([
                        'termux-notification',
                        '--title', '🔥 ¡Tu racha está en peligro!',
                        '--content', 'Hoy no registraste ninguna sesión. Con 5 minutos la mantenés viva.',
                        '--priority', 'high',
                    ], timeout=15)
                    print('🔔 Aviso de racha enviado')
            except Exception as error:
                print('⚠️ No pude notificar (¿Termux:API instalado?):', error)
        _time.sleep(30)  # dormita medio minuto y vuelve a mirar el reloj


# ==================== CONFIGURACIÓN DEL SISTEMA ====================

@app.route('/configuracion')
@login_requerido
def configuracion():
    """Página de administración de tablas."""
    return render_template('configuracion.html', usuario=session['usuario'])

@app.route('/api/config/tipos', methods=['GET', 'POST'])
@login_requerido
def api_tipos():
    if request.method == 'POST':
        datos = request.get_json()
        ok, msg = logica.agregar_tipo(datos.get('nombre', ''))
        return jsonify({'ok': ok, 'mensaje': msg})
    return jsonify(logica.obtener_tipos_estudio())

@app.route('/api/config/tipos/<int:id_tipo>', methods=['PUT', 'DELETE'])
@login_requerido
def api_tipos_accion(id_tipo):
    if request.method == 'DELETE':
        logica.eliminar_tipo(id_tipo)
        return jsonify({'ok': True, 'mensaje': 'Tipo eliminado'})
    datos = request.get_json()
    ok, msg = logica.editar_tipo(id_tipo, datos.get('nombre', ''))
    return jsonify({'ok': ok, 'mensaje': msg})

@app.route('/api/config/tematicas/<int:id_tematica>', methods=['PUT'])
@login_requerido
def api_editar_tematica(id_tematica):
    datos = request.get_json()
    ok, msg = logica.editar_tematica(id_tematica, datos.get('nombre', ''))
    return jsonify({'ok': ok, 'mensaje': msg})

@app.route('/api/config/entradas_crudas')
@login_requerido
def api_entradas_crudas():
    """Historial solo lectura con hashes."""
    return jsonify(logica.obtener_entradas_crudas())


# ==================== CHARLAS DE SIBELI EN CONFIG ====================

@app.route('/api/config/chats')
@login_requerido
def api_config_chats():
    """Lista completa de la charla para administrarla."""
    return jsonify(logica.obtener_historial_chat())

@app.route('/api/config/chats/borrar_todo', methods=['POST'])
@login_requerido
def api_config_borrar_todo():
    logica.borrar_historial_chat()
    return jsonify({'ok': True, 'mensaje': 'Charla completa borrada'})

@app.route('/api/config/chats/<int:id_mensaje>', methods=['DELETE'])
@login_requerido
def api_config_borrar_mensaje(id_mensaje):
    logica.eliminar_mensaje_chat(id_mensaje)
    return jsonify({'ok': True, 'mensaje': 'Mensaje borrado'})


# ==================== DOCUMENTOS DE SIBELI ====================

@app.route('/api/documentos')
@login_requerido
def api_documentos():
    """Catálogo de la carpeta de Sibeli."""
    return jsonify(logica.listar_documentos())

@app.route('/api/documentos/ver')
@login_requerido
def api_ver_documento():
    nombre = request.args.get('nombre', '')
    ok, texto, aviso = logica.leer_documento(nombre)
    return jsonify({'ok': ok, 'texto': texto, 'aviso': aviso})

@app.route('/api/documentos/guardar', methods=['POST'])
@login_requerido
def api_guardar_documento():
    datos = request.get_json()
    ok, msg = logica.guardar_documento(datos.get('nombre', ''), datos.get('contenido', ''))
    return jsonify({'ok': ok, 'mensaje': msg})

@app.route('/api/documentos/borrar', methods=['POST'])
@login_requerido
def api_borrar_documento():
    datos = request.get_json()
    ruta = logica.ruta_permitida(datos.get('nombre', ''))
    if ruta and os.path.exists(ruta):
        os.remove(ruta)
        return jsonify({'ok': True, 'mensaje': 'Documento borrado'})
    return jsonify({'ok': False, 'mensaje': 'No encontrado'})

@app.route('/api/config/sibeli', methods=['GET', 'POST'])
@login_requerido
def api_config_sibeli():
    """Preferencias de la biblioteca y el taller."""
    if request.method == 'POST':
        datos = request.get_json()
        if 'biblioteca' in datos:
            logica.actualizar_configuracion('sibeli_biblioteca', '1' if datos['biblioteca'] else '0')
        if 'escritura' in datos:
            logica.actualizar_configuracion('sibeli_escritura', '1' if datos['escritura'] else '0')
        return jsonify({'ok': True, 'mensaje': 'Preferencias guardadas'})
    config = logica.obtener_configuracion()
    return jsonify({
        'carpeta': logica.obtener_carpeta_sibeli(),
        'biblioteca': config.get('sibeli_biblioteca', '1') == '1',
        'escritura': config.get('sibeli_escritura', '1') == '1',
    })


@app.route('/api/chat/resumen_entrada', methods=['POST'])
@login_requerido
def api_resumen_entrada():
    """Sibeli resume la charla actual en campos de entrada de estudio."""
    ok, resultado = logica.resumir_charla_para_entrada()
    if not ok:
        return jsonify({'ok': False, 'mensaje': resultado})
    return jsonify({'ok': True, 'campos': resultado})


import time as _time_auto

def auto_push_diario():
    """Hilo que sube el compilado de ayer a GitHub a las 00:01 si está activado."""
    import subprocess
    while True:
        ahora = datetime.now()
        # Esperamos hasta las 00:01
        if ahora.hour == 0 and ahora.minute == 1:
            config = logica.obtener_configuracion()
            if config.get('auto_push_github', '1') == '1':
                ayer = (ahora - timedelta(days=1)).strftime('%Y-%m-%d')
                try:
                    compilado = logica.generar_compilado_fecha(ayer)
                    os.makedirs('compilados', exist_ok=True)
                    with open(os.path.join('compilados', f'{ayer}.md'), 'w', encoding='utf-8') as f:
                        f.write(compilado)
                    
                    subprocess.run(['git', 'add', '-A'], timeout=10)
                    subprocess.run(['git', 'commit', '-m', f'Auto-push: compilado del {ayer}'], timeout=10)
                    subprocess.run(['git', 'push', 'origin', 'main'], timeout=30)
                    print(f'✅ Auto-push exitoso para {ayer}')
                except Exception as e:
                    print(f'❌ Error en auto-push: {e}')
            _time_auto.sleep(60) # Dormimos 1 minuto para no ejecutarlo 60 veces en el minuto 1
        else:
            _time_auto.sleep(30) # Revisamos cada 30 segundos


@app.route('/api/entradas/buscar')
@login_requerido
def api_buscar_entradas():
    texto = request.args.get('q', '').strip()
    if not texto:
        return jsonify([])
    return jsonify(logica.buscar_entradas(texto))

@app.route('/api/config/auto_push', methods=['POST'])
@login_requerido
def api_config_auto_push():
    datos = request.get_json()
    logica.actualizar_configuracion('auto_push_github', datos.get('valor', '1'))
    return jsonify({'ok': True})

@app.route('/reportes')
@login_requerido
def reportes():
    return render_template('reportes.html', usuario=session['usuario'])

@app.route('/api/entradas/historial')
@login_requerido
def api_historial_entradas():
    """Devuelve la lista completa de entradas para armar la tabla de reportes."""
    conn = logica.obtener_conexion()
    cur = conn.cursor()
    cur.execute('''
        SELECT e.id, e.fecha, e.tematica_id, t.nombre as tematica_nombre
        FROM entradas e
        JOIN tematicas t ON e.tematica_id = t.id
        ORDER BY e.fecha DESC, e.id DESC
    ''')
    resultados = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(resultados)

@app.route('/api/entradas/<int:entrada_id>')
@login_requerido
def api_detalle_entrada(entrada_id):
    """Devuelve el contenido completo de una entrada específica."""
    conn = logica.obtener_conexion()
    cur = conn.cursor()
    cur.execute('''
        SELECT e.*, t.nombre as tematica_nombre,
               GROUP_CONCAT(te.nombre, ', ') as tipos_nombres
        FROM entradas e
        JOIN tematicas t ON e.tematica_id = t.id
        LEFT JOIN entrada_tipos et ON e.id = et.entrada_id
        LEFT JOIN tipos_estudio te ON et.tipo_id = te.id
        WHERE e.id = ?
        GROUP BY e.id
    ''', (entrada_id,))
    entrada = cur.fetchone()
    conn.close()
    if entrada:
        return jsonify(dict(entrada))
    return jsonify({'error': 'Entrada no encontrada'}), 404
if __name__ == '__main__':
    threading.Thread(target=vigilante_de_racha, daemon=True).start()
    threading.Thread(target=auto_push_diario, daemon=True).start()
    print(' Auto-push diario activo (00:01)')
    print(f'🔔 Vigilante de racha activo (avisa a las {HORA_RECORDATORIO}:00)')
    print('🚀 Diario de Capacitación andando:')
    print(f'   👉 En este celu:  http://localhost:{PUERTO}')
    print(f'   👉 En tu WiFi:    http://{ip_local()}:{PUERTO}')
    print('   (Para detenerlo: Ctrl + C)')
    # host='0.0.0.0' significa: "atiende a todos los dispositivos de la red"
    app.run(host='0.0.0.0', port=PUERTO, debug=False)
