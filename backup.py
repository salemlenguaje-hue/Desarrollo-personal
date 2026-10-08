"""
Script de Backup del Diario de Capacitación.
Empaqueta la base de datos, la clave secreta y el código en un ZIP
y lo guarda en la carpeta Download de Android.
"""

import os
import zipfile
from datetime import datetime

# Rutas mágicas de Termux
CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
CARPETA_DOWNLOAD = os.path.expanduser('~/storage/shared/Download')

# Qué cosas queremos salvar (tu tesoro digital)
A_RESPALDAR = [
    'database.db',     # Tu historial y rachas
    '.secreto',        # Tu clave maestra de la blockchain
    'init_db.py',      # El creador de la base de datos
    'logica.py',       # El cerebro
    'server.py',       # El servidor web
    'templates',       # Las pantallas HTML
    'static',          # Tu logo, estilos y scripts
    'compilados',      # Las actas diarias
    'README.md'        # La carta de presentación
]

def hacer_backup():
    # Verificamos que Termux tenga permiso para tocar las carpetas de Android
    if not os.path.exists(CARPETA_DOWNLOAD):
        print("❌ No encuentro la carpeta Download.")
        print("💡 Asegurate de haber corrido: termux-setup-storage")
        return

    # Creamos el nombre del archivo con la fecha y hora exacta
    fecha = datetime.now().strftime('%Y-%m-%d_%H%M')
    nombre_zip = f'Diario_Capacitacion_Backup_{fecha}.zip'
    ruta_zip = os.path.join(CARPETA_DOWNLOAD, nombre_zip)

    print(f"📦 Empaquetando tu diario en {nombre_zip}...")

    # Creamos el archivo ZIP
    with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in A_RESPALDAR:
            ruta_item = os.path.join(CARPETA_PROYECTO, item)
            
            # Si el archivo o carpeta existe, lo metemos al zip
            if os.path.exists(ruta_item):
                if os.path.isfile(ruta_item):
                    zipf.write(ruta_item, item)
                elif os.path.isdir(ruta_item):
                    # Si es carpeta, recorremos todo su interior
                    for root, dirs, files in os.walk(ruta_item):
                        for file in files:
                            ruta_archivo = os.path.join(root, file)
                            # Guardamos la ruta relativa para que al descomprimir
                            # quede todo en su carpetita correspondiente
                            arcname = os.path.relpath(ruta_archivo, CARPETA_PROYECTO)
                            zipf.write(ruta_archivo, arcname)
            else:
                print(f"⚠️ Ignorado (aún no existe): {item}")

    print(f"✅ ¡Backup exitoso!")
    print(f"📂 Guardado en: {ruta_zip}")

if __name__ == '__main__':
    hacer_backup()
