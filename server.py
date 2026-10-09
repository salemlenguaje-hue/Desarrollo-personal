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
    """Todos los números para los gráficos."""
    return jsonify(logica.obtener_estadisticas())


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
        ok, respuesta = logica.preguntar_gemini(mensaje, profundidad)

        if not ok:
            return jsonify({'ok': False, 'mensaje': respuesta})

        id_mensaje = logica.guardar_chat('tutor', respuesta)
        return jsonify({'ok': True, 'respuesta': respuesta, 'id_mensaje': id_mensaje})
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

if __name__ == '__main__':
    threading.Thread(target=vigilante_de_racha, daemon=True).start()
    print(f'🔔 Vigilante de racha activo (avisa a las {HORA_RECORDATORIO}:00)')
    print('🚀 Diario de Capacitación andando:')
    print(f'   👉 En este celu:  http://localhost:{PUERTO}')
    print(f'   👉 En tu WiFi:    http://{ip_local()}:{PUERTO}')
    print('   (Para detenerlo: Ctrl + C)')
    # host='0.0.0.0' significa: "atiende a todos los dispositivos de la red"
    app.run(host='0.0.0.0', port=PUERTO, debug=False)
