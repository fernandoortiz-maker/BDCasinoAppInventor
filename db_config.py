import psycopg2
from psycopg2.extras import RealDictCursor
import os
import hashlib

# --- CONEXIÓN ---
def get_db_connection():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ ERROR: Falta DATABASE_URL")
            return None
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Neon: {e}")
        return None

# --- REGISTRO (Esta es la función que te faltaba y causaba el error) ---
def registrar_usuario_nuevo(datos):
    conn = get_db_connection()
    if not conn:
        return {"exito": False, "mensaje": "Error de conexión"}
    
    try:
        cursor = conn.cursor()
        pass_hash = hashlib.sha256(datos['password'].encode()).hexdigest()
        
        # Buscamos el ID del rol 'Jugador'
        sql_usuario = """
            INSERT INTO Usuario (id_rol, nombre, apellido, curp, email, password_hash, fecha_registro, activo)
            VALUES (
                (SELECT id_rol FROM Rol WHERE nombre = 'Jugador'), 
                %s, %s, %s, %s, %s, NOW(), true
            )
            RETURNING id_usuario;
        """
        cursor.execute(sql_usuario, (datos['nombre'], datos['apellido'], datos['curp'], datos['email'], pass_hash))
        id_nuevo = cursor.fetchone()[0]
        
        # Saldo inicial
        sql_saldo = "INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion) VALUES (%s, 500.00, NOW());"
        cursor.execute(sql_saldo, (id_nuevo,))
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"exito": True, "mensaje": "Registro exitoso"}
        
    except Exception as e:
        if conn: conn.rollback()
        return {"exito": False, "mensaje": str(e)}

# --- LOGIN ---
def validar_login(email, password):
    conn = get_db_connection()
    if not conn: return None
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        
        sql = """
            SELECT u.id_usuario, u.email, u.nombre, s.saldo_actual, r.nombre as nombre_rol
            FROM Usuario u
            JOIN Saldo s ON u.id_usuario = s.id_usuario
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE u.email = %s AND u.password_hash = %s AND u.activo = true
        """
        cursor.execute(sql, (email, pass_hash))
        usuario = cursor.fetchone()
        conn.close()
        return usuario
    except Exception as e:
        print(f"Error login: {e}")
        return None
