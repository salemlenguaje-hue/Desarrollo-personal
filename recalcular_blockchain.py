"""
Recalcula hash, hash_previo y firma para todas las entradas existentes.
Esto es para que las entradas viejas también tengan blockchain.
"""

import sqlite3
import hashlib
import hmac
import os

ARCHIVO_SECRETO = '.secreto'

def cargar_clave_secreta():
    with open(ARCHIVO_SECRETO, 'r') as f:
        return f.read().strip()

def calcular_hash_entrada(fecha, tematica_id, descripcion, resumen, observaciones):
    contenido = f"{fecha}|{tematica_id}|{descripcion}|{resumen}|{observaciones}"
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()

def calcular_firma(hash_entrada, clave_secreta):
    return hmac.new(
        clave_secreta.encode('utf-8'),
        hash_entrada.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def recalcular():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Traemos todas las entradas ordenadas por ID (de más vieja a más nueva)
    cursor.execute('SELECT * FROM entradas ORDER BY id ASC')
    entradas = cursor.fetchall()
    
    if not entradas:
        print("ℹ️  No hay entradas para recalcular.")
        conn.close()
        return
    
    clave_secreta = cargar_clave_secreta()
    hash_previo = None
    
    for entrada in entradas:
        # Calculamos el hash de esta entrada
        hash_actual = calcular_hash_entrada(
            entrada['fecha'],
            entrada['tematica_id'],
            entrada['descripcion'] or '',
            entrada['resumen'] or '',
            entrada['observaciones'] or ''
        )
        
        # Calculamos la firma
        firma = calcular_firma(hash_actual, clave_secreta)
        
        # Actualizamos la entrada con los 3 campos
        cursor.execute('''
            UPDATE entradas 
            SET hash = ?, hash_previo = ?, firma = ?
            WHERE id = ?
        ''', (hash_actual, hash_previo, firma, entrada['id']))
        
        # El hash de esta entrada será el "previo" de la siguiente
        hash_previo = hash_actual
    
    conn.commit()
    conn.close()
    
    print(f"✅ Blockchain recalculada para {len(entradas)} entrada(s)")

if __name__ == '__main__':
    recalcular()
