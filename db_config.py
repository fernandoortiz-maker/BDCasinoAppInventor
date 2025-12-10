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
        
        # Crear saldo inicial de 500.00 para nuevos usuarios
        cursor.execute("INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion) VALUES (%s, 500.00, NOW());", (id_nuevo,))
        
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

def obtener_historial_auditorias(email):
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT a.id_auditoria, a.fecha_auditoria, a.resumen
            FROM Auditoria a
            JOIN Usuario u ON a.id_usuario = u.id_usuario
            WHERE u.email = %s
            ORDER BY a.fecha_auditoria DESC
        """
        cursor.execute(sql, (email,))
        auditorias = cursor.fetchall()
        conn.close()
        return [dict(row) for row in auditorias]
    except Exception as e:
        print(f"Error historial: {e}")
        return []

# --- ADMIN FUNCTIONS ---

def obtener_todos_usuarios():
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT u.id_usuario, u.nombre, u.apellido, u.email, u.activo, r.nombre as rol, s.saldo_actual
            FROM Usuario u
            JOIN Rol r ON u.id_rol = r.id_rol
            LEFT JOIN Saldo s ON u.id_usuario = s.id_usuario
            ORDER BY u.id_usuario DESC
        """
        cursor.execute(sql)
        users = cursor.fetchall()
        conn.close()
        return [dict(row) for row in users]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def obtener_usuario_por_id(id_usuario):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT u.id_usuario, u.nombre, u.apellido, u.email, u.activo, r.nombre as rol, s.saldo_actual
            FROM Usuario u
            JOIN Rol r ON u.id_rol = r.id_rol
            LEFT JOIN Saldo s ON u.id_usuario = s.id_usuario
            WHERE u.id_usuario = %s
        """
        cursor.execute(sql, (id_usuario,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    except Exception as e:
        print(f"Error fetching user detail: {e}")
        return None

def obtener_juegos():
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Asumimos que la tabla Juego ya existe según el esquema proporcionado
        sql = "SELECT * FROM Juego ORDER BY id_juego DESC"
        cursor.execute(sql)
        games = cursor.fetchall()
        conn.close()
        return [dict(row) for row in games]
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []

def crear_juego(datos):
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO Juego (nombre, descripcion, rtp, min_apuesta, max_apuesta, activo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            datos['nombre'], 
            datos['descripcion'], 
            float(datos['rtp']), 
            float(datos['min_apuesta']), 
            float(datos['max_apuesta']), 
            datos['activo'] == 'true' or datos['activo'] == True
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating game: {e}")
        if conn: conn.rollback()
        return False

def obtener_promociones():
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = "SELECT * FROM Bono ORDER BY id_bono DESC"
        cursor.execute(sql)
        promos = cursor.fetchall()
        conn.close()
        return [dict(row) for row in promos]
    except Exception as e:
        print(f"Error fetching promos: {e}")
        return []

def crear_promocion(datos):
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO Bono (nombre_bono, tipo, descripcion, fecha_expiracion, activo)
            VALUES (%s, %s, %s, %s, %s)
        """
        # fecha_expiracion puede ser None o string YYYY-MM-DD
        fecha = datos.get('fecha_expiracion')
        if not fecha: fecha = None
        
        cursor.execute(sql, (
            datos['nombre_bono'],
            datos['tipo'],
            datos['descripcion'],
            fecha,
            True # Activo por defecto
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating promo: {e}")
        if conn: conn.rollback()
        return False

def obtener_metricas():
    conn = get_db_connection()
    if not conn: return {"total_users": 0, "active_users": 0, "total_deposits": 0, "total_withdrawals": 0}
    try:
        cursor = conn.cursor()
        
        # Usuarios
        cursor.execute("SELECT COUNT(*) FROM Usuario")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Usuario WHERE activo = true")
        active_users = cursor.fetchone()[0]
        
        # Finanzas (Transaccion)
        # Asumiendo tipos: 'Depósito', 'Retiro'
        cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM Transaccion WHERE tipo_transaccion = 'Depósito' AND estado = 'Completada'")
        total_deposits = float(cursor.fetchone()[0])
        
        cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM Transaccion WHERE tipo_transaccion = 'Retiro' AND estado = 'Completada'")
        total_withdrawals = float(cursor.fetchone()[0])
        
        conn.close()
        return {
            "total_users": total_users, 
            "active_users": active_users,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals
        }
    except Exception as e:
        print(f"Error metrics: {e}")
        return {"total_users": 0, "active_users": 0, "total_deposits": 0, "total_withdrawals": 0}

def actualizar_usuario_admin(id_usuario, nombre, apellido, nueva_password=None):
    """Actualizar datos de un usuario desde el panel de admin"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        if nueva_password and len(nueva_password) > 0:
            pass_hash = pwd_context.hash(nueva_password)
            sql = "UPDATE Usuario SET nombre = %s, apellido = %s, password_hash = %s WHERE id_usuario = %s"
            cursor.execute(sql, (nombre, apellido, pass_hash, id_usuario))
        else:
            sql = "UPDATE Usuario SET nombre = %s, apellido = %s WHERE id_usuario = %s"
            cursor.execute(sql, (nombre, apellido, id_usuario))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando usuario: {e}")
        if conn: conn.rollback()
        return False

def cambiar_estado_usuario(id_usuario, activo):
    """Activar o desactivar un usuario"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = "UPDATE Usuario SET activo = %s WHERE id_usuario = %s"
        cursor.execute(sql, (activo, id_usuario))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error cambiando estado: {e}")
        if conn: conn.rollback()
        return False

def eliminar_usuario(id_usuario):
    """Eliminar un usuario (solo si no tiene dependencias críticas)"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        # Primero eliminar saldo (CASCADE debería hacerlo automáticamente)
        sql = "DELETE FROM Usuario WHERE id_usuario = %s"
        cursor.execute(sql, (id_usuario,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error eliminando usuario: {e}")
        if conn: conn.rollback()
        return False

def obtener_administradores_y_auditores():
    """Obtener lista de administradores y auditores"""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT u.id_usuario, u.nombre, u.apellido, u.email, u.activo, r.nombre as rol
            FROM Usuario u
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE r.nombre IN ('Administrador', 'Auditor', 'Agente de Soporte')
            ORDER BY r.nombre, u.id_usuario DESC
        """
        cursor.execute(sql)
        users = cursor.fetchall()
        conn.close()
        return [dict(row) for row in users]
    except Exception as e:
        print(f"Error fetching admins/auditors: {e}")
        return []

# ==========================================
# SECCIÓN 5: FUNCIONES PANEL DE AGENTE DE SOPORTE
# ==========================================

# --- TICKETS (Tabla: Soporte) ---

def obtener_tickets(estado=None, asignado=None):
    """Obtener todos los tickets con filtros opcionales"""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Base query usando la tabla Soporte
        sql = """
            SELECT s.id_ticket, s.asunto, s.mensaje, s.estado, s.fecha_creacion, s.fecha_cierre,
                   u.nombre || ' ' || u.apellido as nombre_usuario, u.email,
                   a.nombre || ' ' || a.apellido as nombre_agente,
                   s.id_jugador, s.id_agente
            FROM Soporte s
            JOIN Usuario u ON s.id_jugador = u.id_usuario
            LEFT JOIN Usuario a ON s.id_agente = a.id_usuario
            WHERE 1=1
        """
        params = []
        
        # Filtros
        if estado:
            sql += " AND s.estado = %s"
            params.append(estado)
        
        if asignado == 'si':
            sql += " AND s.id_agente IS NOT NULL"
        elif asignado == 'no':
            sql += " AND s.id_agente IS NULL"
        
        sql += " ORDER BY s.fecha_creacion DESC"
        
        cursor.execute(sql, params)
        tickets = cursor.fetchall()
        conn.close()
        return [dict(row) for row in tickets]
    except Exception as e:
        print(f"Error obteniendo tickets: {e}")
        return []

def obtener_ticket_por_id(id_ticket):
    """Obtener detalles de un ticket específico"""
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT s.id_ticket, s.asunto, s.mensaje, s.estado, s.fecha_creacion, s.fecha_cierre,
                   u.nombre || ' ' || u.apellido as nombre_usuario, u.email,
                   a.nombre || ' ' || a.apellido as nombre_agente,
                   s.id_jugador, s.id_agente
            FROM Soporte s
            JOIN Usuario u ON s.id_jugador = u.id_usuario
            LEFT JOIN Usuario a ON s.id_agente = a.id_usuario
            WHERE s.id_ticket = %s
        """
        cursor.execute(sql, (id_ticket,))
        ticket = cursor.fetchone()
        conn.close()
        return dict(ticket) if ticket else None
    except Exception as e:
        print(f"Error obteniendo ticket: {e}")
        return None

def obtener_respuestas_ticket(id_ticket):
    """Obtener respuestas de un ticket - NO IMPLEMENTADO (no hay tabla de respuestas)"""
    # La DB actual no tiene tabla de respuestas, retornar lista vacía
    return []

def asignar_ticket(id_ticket, id_agente):
    """Asignar un ticket a un agente"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = """
            UPDATE Soporte 
            SET id_agente = %s, estado = 'En Proceso'
            WHERE id_ticket = %s
        """
        cursor.execute(sql, (id_agente, id_ticket))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error asignando ticket: {e}")
        if conn: conn.rollback()
        return False

def responder_ticket(id_ticket, id_usuario, mensaje, es_agente=True):
    """Agregar una respuesta a un ticket - NO IMPLEMENTADO (no hay tabla de respuestas)"""
    # La DB actual no tiene tabla de respuestas
    # Podrías actualizar el mensaje del ticket o simplemente retornar False
    return False

def cerrar_ticket(id_ticket):
    """Cerrar un ticket"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = "UPDATE Soporte SET estado = 'Cerrado', fecha_cierre = NOW() WHERE id_ticket = %s"
        cursor.execute(sql, (id_ticket,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error cerrando ticket: {e}")
        if conn: conn.rollback()
        return False

def obtener_tickets_agente(id_agente):
    """Obtener tickets asignados a un agente específico"""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT s.id_ticket, s.asunto, s.mensaje, s.estado, s.fecha_creacion, s.fecha_cierre,
                   u.nombre || ' ' || u.apellido as nombre_usuario, u.email,
                   s.id_jugador, s.id_agente
            FROM Soporte s
            JOIN Usuario u ON s.id_jugador = u.id_usuario
            WHERE s.id_agente = %s AND s.estado != 'Cerrado'
            ORDER BY s.fecha_creacion DESC
        """
        cursor.execute(sql, (id_agente,))
        tickets = cursor.fetchall()
        conn.close()
        
        # Agregar fecha_asignacion ficticia para compatibilidad con frontend
        result = []
        for ticket in tickets:
            t = dict(ticket)
            t['fecha_asignacion'] = t['fecha_creacion']  # Usar fecha_creacion como aproximación
            result.append(t)
        return result
    except Exception as e:
        print(f"Error obteniendo tickets del agente: {e}")
        return []

# --- CHATS (Tabla: Chat y Mensaje_Chat) ---

def obtener_chats_esperando():
    """Obtener chats en espera de ser asignados a un agente"""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT c.id_chat, c.fecha_inicio, c.estado,
                   u.nombre || ' ' || u.apellido as nombre_usuario, u.email
            FROM Chat c
            JOIN Usuario u ON c.id_jugador = u.id_usuario
            WHERE c.estado = 'Esperando'
            ORDER BY c.fecha_inicio ASC
        """
        cursor.execute(sql)
        chats = cursor.fetchall()
        conn.close()
        return [dict(row) for row in chats]
    except Exception as e:
        print(f"Error obteniendo chats en espera: {e}")
        return []

def obtener_chats_agente(id_agente):
    """Obtener chats activos asignados a un agente específico"""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = """
            SELECT c.id_chat, c.fecha_inicio, c.fecha_asignacion, c.estado,
                   u.nombre || ' ' || u.apellido as nombre_usuario, u.email
            FROM Chat c
            JOIN Usuario u ON c.id_jugador = u.id_usuario
            WHERE c.id_agente = %s AND c.estado = 'Activo'
            ORDER BY c.fecha_asignacion DESC
        """
        cursor.execute(sql, (id_agente,))
        chats = cursor.fetchall()
        conn.close()
        return [dict(row) for row in chats]
    except Exception as e:
        print(f"Error obteniendo chats del agente: {e}")
        return []

def obtener_mensajes_chat(id_chat):
    """Obtener información del chat y todos sus mensajes"""
    conn = get_db_connection()
    if not conn: return {'chat': None, 'mensajes': []}
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener información del chat
        sql_chat = """
            SELECT c.id_chat, c.fecha_inicio, c.fecha_asignacion, c.fecha_cierre, c.estado,
                   u.nombre || ' ' || u.apellido as nombre_usuario, u.email as email_usuario,
                   a.nombre || ' ' || a.apellido as nombre_agente
            FROM Chat c
            JOIN Usuario u ON c.id_jugador = u.id_usuario
            LEFT JOIN Usuario a ON c.id_agente = a.id_usuario
            WHERE c.id_chat = %s
        """
        cursor.execute(sql_chat, (id_chat,))
        chat = cursor.fetchone()
        
        if not chat:
            conn.close()
            return {'chat': None, 'mensajes': []}
        
        # Obtener mensajes del chat
        sql_mensajes = """
            SELECT m.id_mensaje, m.mensaje, m.fecha_mensaje, m.es_agente, m.leido,
                   u.nombre || ' ' || u.apellido as nombre_usuario
            FROM Mensaje_Chat m
            JOIN Usuario u ON m.id_usuario = u.id_usuario
            WHERE m.id_chat = %s
            ORDER BY m.fecha_mensaje ASC
        """
        cursor.execute(sql_mensajes, (id_chat,))
        mensajes = cursor.fetchall()
        
        conn.close()
        return {
            'chat': dict(chat),
            'mensajes': [dict(row) for row in mensajes]
        }
    except Exception as e:
        print(f"Error obteniendo mensajes del chat: {e}")
        return {'chat': None, 'mensajes': []}

def tomar_chat(id_chat, id_agente):
    """Asignar un chat a un agente y cambiar su estado a Activo"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = """
            UPDATE Chat 
            SET id_agente = %s, estado = 'Activo', fecha_asignacion = NOW()
            WHERE id_chat = %s AND estado = 'Esperando'
        """
        cursor.execute(sql, (id_agente, id_chat))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error tomando chat: {e}")
        if conn: conn.rollback()
        return False

def enviar_mensaje_chat(id_chat, id_usuario, mensaje, es_agente=True):
    """Enviar un mensaje en un chat"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO Mensaje_Chat (id_chat, id_usuario, mensaje, es_agente, fecha_mensaje, leido)
            VALUES (%s, %s, %s, %s, NOW(), false)
        """
        cursor.execute(sql, (id_chat, id_usuario, mensaje, es_agente))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        if conn: conn.rollback()
        return False

def cerrar_chat(id_chat):
    """Cerrar un chat"""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = "UPDATE Chat SET estado = 'Cerrado', fecha_cierre = NOW() WHERE id_chat = %s"
        cursor.execute(sql, (id_chat,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error cerrando chat: {e}")
        if conn: conn.rollback()
        return False

# --- DASHBOARD ---

def obtener_dashboard_agente(id_agente):
    """Obtener métricas para el dashboard del agente"""
    conn = get_db_connection()
    if not conn: 
        return {
            'tickets_pendientes': 0,
            'mis_tickets': 0,
            'chats_esperando': 0,
            'mis_chats': 0,
            'cerrados_hoy': 0
        }
    try:
        cursor = conn.cursor()
        
        # Tickets pendientes (sin asignar)
        cursor.execute("SELECT COUNT(*) FROM Soporte WHERE id_agente IS NULL AND estado = 'Abierto'")
        tickets_pendientes = cursor.fetchone()[0]
        
        # Mis tickets
        cursor.execute("SELECT COUNT(*) FROM Soporte WHERE id_agente = %s AND estado != 'Cerrado'", (id_agente,))
        mis_tickets = cursor.fetchone()[0]
        
        # Chats en espera
        cursor.execute("SELECT COUNT(*) FROM Chat WHERE estado = 'Esperando'")
        chats_esperando = cursor.fetchone()[0]
        
        # Mis chats activos
        cursor.execute("SELECT COUNT(*) FROM Chat WHERE id_agente = %s AND estado = 'Activo'", (id_agente,))
        mis_chats = cursor.fetchone()[0]
        
        # Cerrados hoy (tickets y chats)
        cursor.execute("""
            SELECT COUNT(*) FROM Soporte 
            WHERE id_agente = %s AND estado = 'Cerrado' 
            AND DATE(fecha_cierre) = CURRENT_DATE
        """, (id_agente,))
        tickets_cerrados_hoy = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM Chat 
            WHERE id_agente = %s AND estado = 'Cerrado' 
            AND DATE(fecha_cierre) = CURRENT_DATE
        """, (id_agente,))
        chats_cerrados_hoy = cursor.fetchone()[0]
        
        cerrados_hoy = tickets_cerrados_hoy + chats_cerrados_hoy
        
        conn.close()
        return {
            'tickets_pendientes': tickets_pendientes,
            'mis_tickets': mis_tickets,
            'chats_esperando': chats_esperando,
            'mis_chats': mis_chats,
            'cerrados_hoy': cerrados_hoy
        }
    except Exception as e:
        print(f"Error en dashboard agente: {e}")
        return {
            'tickets_pendientes': 0,
            'mis_tickets': 0,
            'chats_esperando': 0,
            'mis_chats': 0,
            'cerrados_hoy': 0
        }
