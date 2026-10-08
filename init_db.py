"""
Script para inicializar la base de datos.
Crea las tablas necesarias para el Diario de Capacitación.
"""

import sqlite3
import hashlib

def crear_base_datos():
    """
    Crea todas las tablas necesarias en la base de datos SQLite.
    """
    # Nos conectamos a la base de datos (si no existe, la crea)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Tabla de usuarios (por ahora solo vos, Martín)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de temáticas (Ingeniería de Software, Mandarín, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tematicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activa INTEGER DEFAULT 1
        )
    ''')
    
    # Tabla de tipos de estudio (Lectura, Práctica, Video, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipos_estudio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Tabla de entradas de estudio (lo más importante)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            tematica_id INTEGER NOT NULL,
            descripcion TEXT,
            resumen TEXT,
            observaciones TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tematica_id) REFERENCES tematicas (id)
        )
    ''')
    
    # Tabla intermedia para relacionar entradas con tipos de estudio
    # (porque una entrada puede tener varios tipos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrada_tipos (
            entrada_id INTEGER,
            tipo_id INTEGER,
            PRIMARY KEY (entrada_id, tipo_id),
            FOREIGN KEY (entrada_id) REFERENCES entradas (id),
            FOREIGN KEY (tipo_id) REFERENCES tipos_estudio (id)
        )
    ''')
    
    # Tabla de configuración (para guardar la racha actual, mejor racha, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')
    
    # Insertamos datos iniciales si la base está vacía
    
    # Usuario por defecto: Martin, sin contraseña por ahora
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (username, password_hash)
        VALUES (?, ?)
    ''', ('Martin', ''))  # Password vacío por ahora
    
    # Tipos de estudio por defecto
    tipos_default = ['Lectura', 'Práctica', 'Video', 'Ejercicio', 'Examen', 'Repaso', 'Proyecto']
    for tipo in tipos_default:
        cursor.execute('''
            INSERT OR IGNORE INTO tipos_estudio (nombre) VALUES (?)
        ''', (tipo,))
    
    # Configuración inicial
    config_inicial = [
        ('racha_actual', '0'),
        ('mejor_racha', '0'),
        ('ultimo_dia_estudio', ''),
        ('dias_descanso_usados', '0'),
        ('nivel_actual', '1')
    ]
    for clave, valor in config_inicial:
        cursor.execute('''
            INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)
        ''', (clave, valor))
    
    # Guardamos los cambios y cerramos la conexión
    conn.commit()
    conn.close()
    
    print("✅ Base de datos creada exitosamente!")
    print("📊 Tablas creadas: usuarios, tematicas, tipos_estudio, entradas, entrada_tipos, configuracion")

if __name__ == '__main__':
    crear_base_datos()
