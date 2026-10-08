"""
Genera un archivo .secreto con una clave maestra aleatoria.
Solo corre una vez (si el archivo ya existe, no lo sobreescribe).
"""

import os
import secrets

ARCHIVO_SECRETO = '.secreto'

def generar():
    if os.path.exists(ARCHIVO_SECRETO):
        print(f"ℹ️  El archivo {ARCHIVO_SECRETO} ya existe. No se regenera.")
        with open(ARCHIVO_SECRETO, 'r') as f:
            print(f"🔑 Tu clave actual: {f.read().strip()[:16]}...")
        return
    
    # Generamos 32 bytes aleatorios y los convertimos a texto hexadecimal
    clave = secrets.token_hex(32)
    
    with open(ARCHIVO_SECRETO, 'w') as f:
        f.write(clave)
    
    # Lo hacemos de solo lectura para vos (nadie más puede leerlo)
    os.chmod(ARCHIVO_SECRETO, 0o600)
    
    print(f"✅ Clave maestra generada y guardada en {ARCHIVO_SECRETO}")
    print(f"🔑 Tu clave: {clave[:16]}... (guardala en un lugar seguro)")

if __name__ == '__main__':
    generar()
