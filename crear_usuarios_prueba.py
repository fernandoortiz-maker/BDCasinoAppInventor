#!/usr/bin/env python3
"""
Script para crear usuarios de prueba con contraseñas hasheadas correctamente.
Ejecutar: python crear_usuarios_prueba.py
"""

import os
import sys
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

def crear_tickets_prueba(conn, id_agente, id_jugadores):
    """Crear tickets de prueba"""
    try:
        cursor = conn.cursor()
        
        # Ticket sin asignar
        cursor.execute("""
            INSERT INTO Soporte (id_jugador, asunto, mensaje, estado, fecha_creacion)
            VALUES (%s, %s, %s, 'Abierto', NOW() - INTERVAL '2 hours')
        """, (id_jugadores[0], 'No puedo depositar fondos', 
              'He intentado depositar $100 pero me aparece un error. ¿Pueden ayudarme?'))
        
        # Otro ticket sin asignar
        cursor.execute("""
            INSERT INTO Soporte (id_jugador, asunto, mensaje, estado, fecha_creacion)
            VALUES (%s, %s, %s, 'Abierto', NOW() - INTERVAL '1 day')
        """, (id_jugadores[1], 'Problema con retiro', 
              'Solicité un retiro hace 3 días y aún no lo he recibido.'))
        
        # Ticket asignado al agente
        cursor.execute("""
            INSERT INTO Soporte (id_jugador, id_agente, asunto, mensaje, estado, fecha_creacion)
            VALUES (%s, %s, %s, %s, 'En Proceso', NOW() - INTERVAL '3 hours')
        """, (id_jugadores[2], id_agente, 'Cuenta bloqueada', 
              'Mi cuenta fue bloqueada sin razón aparente. Necesito ayuda urgente.'))
        
        # Ticket cerrado (para estadísticas)
        cursor.execute("""
            INSERT INTO Soporte (id_jugador, id_agente, asunto, mensaje, estado, fecha_creacion, fecha_cierre)
            VALUES (%s, %s, %s, %s, 'Cerrado', CURRENT_DATE - INTERVAL '1 hour', CURRENT_DATE)
        """, (id_jugadores[0], id_agente, 'Consulta sobre bonos', 
              '¿Cómo puedo obtener el bono de bienvenida?'))
        
        conn.commit()
        print("✅ Tickets de prueba creados")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creando tickets: {e}")

def crear_chats_prueba(conn, id_agente, id_jugadores):
    """Crear chats de prueba"""
    try:
        cursor = conn.cursor()
        
        # Chat en espera
        cursor.execute("""
            INSERT INTO Chat (id_jugador, estado, fecha_inicio)
            VALUES (%s, 'Esperando', NOW() - INTERVAL '10 minutes')
        """, (id_jugadores[0],))
        
        # Otro chat en espera
        cursor.execute("""
            INSERT INTO Chat (id_jugador, estado, fecha_inicio)
            VALUES (%s, 'Esperando', NOW() - INTERVAL '5 minutes')
        """, (id_jugadores[1],))
        
        # Chat activo con el agente
        cursor.execute("""
            INSERT INTO Chat (id_jugador, id_agente, estado, fecha_inicio, fecha_asignacion)
            VALUES (%s, %s, 'Activo', NOW() - INTERVAL '20 minutes', NOW() - INTERVAL '18 minutes')
            RETURNING id_chat
        """, (id_jugadores[2], id_agente))
        id_chat = cursor.fetchone()[0]
        
        # Mensajes en el chat activo
        mensajes = [
            (id_chat, id_jugadores[2], 'Hola, necesito ayuda con mi cuenta', False, '18 minutes'),
            (id_chat, id_agente, 'Hola, con gusto te ayudo. ¿Cuál es el problema?', True, '17 minutes'),
            (id_chat, id_jugadores[2], 'Mi cuenta fue bloqueada y no sé por qué', False, '16 minutes'),
            (id_chat, id_agente, 'Déjame revisar tu cuenta. Un momento por favor.', True, '15 minutes'),
            (id_chat, id_agente, 'Ya revisé y veo que hubo actividad sospechosa. Voy a desbloquearla.', True, '10 minutes'),
        ]
        
        for msg in mensajes:
            cursor.execute("""
                INSERT INTO Mensaje_Chat (id_chat, id_usuario, mensaje, es_agente, fecha_mensaje, leido)
                VALUES (%s, %s, %s, %s, NOW() - INTERVAL %s, true)
            """, msg)
        
        conn.commit()
        print("✅ Chats de prueba creados")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creando chats: {e}")

def main():
    print("=" * 60)
    print("CREACIÓN DE USUARIOS DE PRUEBA PARA PANEL DE AGENTE")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
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
        'agente123'
    )
    
    if not id_agente:
        print("❌ No se pudo crear el agente. Abortando.")
        conn.close()
        sys.exit(1)
    
    # Crear jugadores
    id_jugadores = []
    
    jugadores = [
        ('María', 'García', 'GARM900215MDFRXR02', 'maria@test.com', 'maria123'),
        ('Carlos', 'López', 'LOPC880310HDFRXR03', 'carlos@test.com', 'carlos123'),
        ('Ana', 'Martínez', 'MARA920520MDFRXN04', 'ana@test.com', 'ana123'),
    ]
    
    for nombre, apellido, curp, email, password in jugadores:
        id_usuario = crear_usuario(conn, 'Jugador', nombre, apellido, curp, email, password)
        if id_usuario:
            id_jugadores.append(id_usuario)
    
    if len(id_jugadores) < 3:
        print("❌ No se pudieron crear todos los jugadores. Abortando.")
        conn.close()
        sys.exit(1)
    
    print("\n🎫 Creando tickets de prueba...")
    crear_tickets_prueba(conn, id_agente, id_jugadores)
    
    print("\n💬 Creando chats de prueba...")
    crear_chats_prueba(conn, id_agente, id_jugadores)
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ DATOS DE PRUEBA CREADOS EXITOSAMENTE")
    print("=" * 60)
    print("\n📋 CREDENCIALES DE ACCESO:")
    print("\n🔐 Agente de Soporte:")
    print("   Email: agente@casino.com")
    print("   Contraseña: agente123")
    print("\n👥 Jugadores:")
    print("   maria@test.com / maria123")
    print("   carlos@test.com / carlos123")
    print("   ana@test.com / ana123")
    print("\n🌐 Para acceder:")
    print("   1. Ve a http://localhost:10000/login")
    print("   2. Inicia sesión con agente@casino.com")
    print("   3. Serás redirigido al panel de agente")
    print("\n📊 Datos creados:")
    print("   - 4 tickets (2 sin asignar, 1 en proceso, 1 cerrado)")
    print("   - 3 chats (2 en espera, 1 activo con mensajes)")
    print("=" * 60)

if __name__ == "__main__":
    main()
