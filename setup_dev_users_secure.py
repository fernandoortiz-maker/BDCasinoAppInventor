#!/usr/bin/env python3
"""
Script SEGURO para crear usuarios de prueba.
Las contraseñas se leen desde variables de entorno o se piden al usuario.

Uso:
1. Configurar variables de entorno (recomendado):
   export DEV_AGENT_PASSWORD="tu_password_seguro"
   
2. O ejecutar y el script pedirá las contraseñas interactivamente
"""

import os
import sys
import getpass
from passlib.context import CryptContext
import psycopg2

# Configuración de Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_db_connection():
    """Obtener conexión a la base de datos"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ ERROR: Falta DATABASE_URL en las variables de entorno")
            return None
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        return None

def obtener_password_segura(nombre_usuario, variable_env=None):
    """Obtener password desde variable de entorno o input seguro"""
    if variable_env and os.environ.get(variable_env):
        return os.environ.get(variable_env)
    
    # Pedir password de forma segura
    password = getpass.getpass(f"Ingrese password para {nombre_usuario}: ")
    confirmar = getpass.getpass(f"Confirme password: ")
    
    if password != confirmar:
        print("❌ Las contraseñas no coinciden")
        return None
    
    if len(password) < 8:
        print("❌ La contraseña debe tener al menos 8 caracteres")
        return None
    
    return password

def crear_usuario(conn, rol, nombre, apellido, curp, email, password):
    """Crear un usuario con contraseña hasheada"""
    try:
        cursor = conn.cursor()
        
        # Hashear la contraseña
        password_hash = pwd_context.hash(password)
        
        # Insertar usuario
        sql_usuario = """
            INSERT INTO Usuario (id_rol, nombre, apellido, curp, email, password_hash, activo)
            VALUES (
                (SELECT id_rol FROM Rol WHERE nombre = %s),
                %s, %s, %s, %s, %s, true
            )
            RETURNING id_usuario;
        """
        cursor.execute(sql_usuario, (rol, nombre, apellido, curp, email, password_hash))
        id_usuario = cursor.fetchone()[0]
        
        # Crear saldo inicial
        cursor.execute(
            "INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion) VALUES (%s, %s, NOW())",
            (id_usuario, 500.00 if rol == 'Jugador' else 0.00)
        )
        
        conn.commit()
        print(f"✅ Usuario creado: {email} (ID: {id_usuario})")
        return id_usuario
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creando usuario {email}: {e}")
        return None

def main():
    print("=" * 60)
    print("CREACIÓN SEGURA DE USUARIOS DE PRUEBA")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        sys.exit(1)
    
    print("\n🔐 Configuración de contraseñas seguras...")
    print("Puedes usar variables de entorno o ingresarlas manualmente.\n")
    
    # Obtener passwords de forma segura
    password_agente = obtener_password_segura("agente@casino.com", "DEV_AGENT_PASSWORD")
    if not password_agente:
        sys.exit(1)
    
    print("\n📝 Creando usuarios...")
    
    # Crear agente de soporte
    id_agente = crear_usuario(
        conn, 
        'Agente de Soporte', 
        'Juan', 
        'Pérez',
        'PEJX850101HDFRXN01',
        'agente@casino.com',
        password_agente
    )
    
    if not id_agente:
        print("❌ No se pudo crear el agente. Abortando.")
        conn.close()
        sys.exit(1)
    
    # Crear jugadores con passwords generadas aleatoriamente
    import secrets
    import string
    
    def generar_password_aleatoria():
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(12))
    
    jugadores = [
        ('María', 'García', 'GARM900215MDFRXR02', 'maria@test.com'),
        ('Carlos', 'López', 'LOPC880310HDFRXR03', 'carlos@test.com'),
        ('Ana', 'Martínez', 'MARA920520MDFRXN04', 'ana@test.com'),
    ]
    
    id_jugadores = []
    credenciales_generadas = []
    
    for nombre, apellido, curp, email in jugadores:
        password = generar_password_aleatoria()
        id_usuario = crear_usuario(conn, 'Jugador', nombre, apellido, curp, email, password)
        if id_usuario:
            id_jugadores.append(id_usuario)
            credenciales_generadas.append((email, password))
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ USUARIOS CREADOS EXITOSAMENTE")
    print("=" * 60)
    print("\n📋 CREDENCIALES DE ACCESO:")
    print("\n🔐 Agente de Soporte:")
    print("   Email: agente@casino.com")
    print("   Contraseña: (la que configuraste)")
    print("\n👥 Jugadores (contraseñas generadas aleatoriamente):")
    for email, password in credenciales_generadas:
        print(f"   {email} / {password}")
    print("\n⚠️  IMPORTANTE: Guarda estas credenciales en un lugar seguro!")
    print("=" * 60)

if __name__ == "__main__":
    main()
