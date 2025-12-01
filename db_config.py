import psycopg2
from psycopg2.extras import RealDictCursor
import os
from passlib.context import CryptContext

# Configuración de seguridad (Argon2)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

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

# --- USUARIOS Y LOGIN ---

def registrar_usuario_nuevo(datos):
    conn = get_db_connection()
    if not conn: return {"exito": False, "mensaje": "Error de conexión"}
    try:
        cursor = conn.cursor()
        pass_hash = pwd_context.hash(datos['password'])
        
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
        
<<<<<<< HEAD
        # Saldo inicial
        cursor.execute("INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion) VALUES (%s, 500.00, NOW());", (id_nuevo,))
=======
        # 3. Crear Saldo inicial
        sql_saldo = "INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion) VALUES (%s, 0.00, NOW());"
        cursor.execute(sql_saldo, (id_nuevo,))
>>>>>>> 0fff547bc6b22b8741decf8497e940e918c3a124
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"exito": True, "mensaje": "Registro exitoso"}
    except Exception as e:
        if conn: conn.rollback()
        return {"exito": False, "mensaje": str(e)}

def validar_login(email, password):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT u.id_usuario, u.email, u.nombre, u.password_hash, 
                   s.saldo_actual, r.nombre as nombre_rol
            FROM Usuario u
            JOIN Saldo s ON u.id_usuario = s.id_usuario
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE u.email = %s AND u.activo = true
        """
        cursor.execute(sql, (email,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario and pwd_context.verify(password, usuario['password_hash']):
            del usuario['password_hash']
            return usuario
        return None
    except Exception as e:
        print(f"Error login: {e}")
        return None

# --- PERFIL Y TRANSACCIONES ---

def obtener_perfil(email):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT u.id_usuario, u.nombre, u.apellido, u.email, s.saldo_actual 
            FROM Usuario u
            JOIN Saldo s ON u.id_usuario = s.id_usuario
            WHERE u.email = %s
        """
        cursor.execute(sql, (email,))
        datos = cursor.fetchone()
        conn.close()
        return datos
    except Exception:
        return None

def actualizar_datos_usuario(email, nombre, apellido, nueva_password=None):
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        if nueva_password and len(nueva_password) > 0:
            pass_hash = pwd_context.hash(nueva_password)
            sql = "UPDATE Usuario SET nombre = %s, apellido = %s, password_hash = %s WHERE email = %s"
            cursor.execute(sql, (nombre, apellido, pass_hash, email))
        else:
            sql = "UPDATE Usuario SET nombre = %s, apellido = %s WHERE email = %s"
            cursor.execute(sql, (nombre, apellido, email))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def realizar_transaccion_saldo(email, monto, tipo):
    conn = get_db_connection()
    if not conn: return {"exito": False, "mensaje": "Sin conexión"}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT saldo_actual FROM Saldo s JOIN Usuario u ON s.id_usuario = u.id_usuario WHERE u.email = %s", (email,))
        res = cursor.fetchone()
        if not res: return {"exito": False, "mensaje": "Usuario no encontrado"}
        
        saldo_actual = float(res[0])
        monto_final = monto if tipo != "retiro" else -monto
        
        if tipo == "retiro" and saldo_actual < monto:
            return {"exito": False, "mensaje": "Fondos insuficientes"}

        sql = """
            UPDATE Saldo SET saldo_actual = saldo_actual + %s, ultima_actualizacion = NOW()
            WHERE id_usuario = (SELECT id_usuario FROM Usuario WHERE email = %s)
            RETURNING saldo_actual;
        """
        cursor.execute(sql, (monto_final, email))
        nuevo_saldo = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return {"exito": True, "mensaje": "Éxito", "nuevo_saldo": float(nuevo_saldo)}
    except Exception as e:
        if conn: conn.rollback()
        return {"exito": False, "mensaje": str(e)}

# --- AUDITORÍA ---

def guardar_auditoria(email, resumen, datos_json):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO Auditoria (id_usuario, resumen, datos_auditoria, fecha_auditoria)
            VALUES (
                (SELECT id_usuario FROM Usuario WHERE email = %s),
                %s, %s, NOW()
            )
            RETURNING id_auditoria;
        """
        cursor.execute(sql, (email, resumen, datos_json))
        id_auditoria = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return id_auditoria
    except Exception as e:
        print(f"Error auditoria: {e}")
        if conn: conn.rollback()
        return None

def obtener_datos_auditoria(id_auditoria):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT a.*, u.nombre, u.apellido, u.email
            FROM Auditoria a
            JOIN Usuario u ON a.id_usuario = u.id_usuario
            WHERE a.id_auditoria = %s
        """
        cursor.execute(sql, (id_auditoria,))
        data = cursor.fetchone()
        conn.close()
        return data
    except Exception:
        return None
