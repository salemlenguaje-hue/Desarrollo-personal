"""
Migración: agrega los campos de blockchain a la tabla entradas.
Solo corre una vez.
"""

import sqlite3

def migrar():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Agregamos las 3 columnas nuevas (si no existen)
    try:
        cursor.execute('ALTER TABLE entradas ADD COLUMN hash TEXT')
        print("✅ Columna 'hash' agregada")
    except sqlite3.OperationalError:
        print("ℹ️  Columna 'hash' ya existía")
    
    try:
        cursor.execute('ALTER TABLE entradas ADD COLUMN hash_previo TEXT')
        print("✅ Columna 'hash_previo' agregada")
    except sqlite3.OperationalError:
        print("ℹ️  Columna 'hash_previo' ya existía")
    
    try:
        cursor.execute('ALTER TABLE entradas ADD COLUMN firma TEXT')
        print("✅ Columna 'firma' agregada")
    except sqlite3.OperationalError:
        print("ℹ️  Columna 'firma' ya existía")
    
    conn.commit()
    conn.close()
    print("🎉 Migración completa. La base ya soporta blockchain.")

if __name__ == '__main__':
    migrar()
