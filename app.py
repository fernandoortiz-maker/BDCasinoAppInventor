from flask import Flask, session, jsonify, request, send_file, render_template, send_from_directory
import os
import json
import io

# Librerías para generar el PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Importamos TODAS las funciones de la base de datos
from db_config import (
    registrar_usuario_nuevo, 
    validar_login, 
    obtener_perfil, 
    actualizar_datos_usuario, 
    realizar_transaccion_saldo,
    guardar_auditoria,
    obtener_datos_auditoria,
    obtener_historial_auditorias
)

# --- 1. INICIALIZACIÓN ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# --- 2. CONFIGURACIÓN DE COOKIES (CRÍTICO PARA APP INVENTOR) ---
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hora

# ==========================================
# SECCIÓN 1: RUTAS BÁSICAS Y AUTENTICACIÓN
# ==========================================

@app.route("/", methods=["GET"])
def index():
    return "✅ Servidor Central del Casino Activo.<br>Usa la App Móvil para interactuar."

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    print("--- INICIO DE REGISTRO ---")
    try:
        datos = request.get_json(force=True, silent=True)
        
        if not datos:
            return jsonify({"exito": False, "mensaje": "JSON inválido"}), 400

        print(f"📥 Datos recibidos: {datos}")
        
        campos = ["nombre", "apellido", "curp", "email", "password"]
        faltantes = [campo for campo in campos if campo not in datos]
        
        if faltantes:
            return jsonify({"exito": False, "mensaje": f"Faltan datos: {faltantes}"}), 400

        resultado = registrar_usuario_nuevo(datos)
        
        codigo = 200 if resultado["exito"] else 400
        return jsonify(resultado), codigo

    except Exception as e:
        print(f"🔥 ERROR INTERNO: {e}")
        return jsonify({"exito": False, "mensaje": f"Error servidor: {str(e)}"}), 500

@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        datos = request.get_json(force=True)
        email = datos.get("email")
        password = datos.get("password")
        
        usuario = validar_login(email, password)
        
        if usuario:
            session.clear()
            session.permanent = True
            session["user_id"] = usuario["email"]
            session["rol"] = usuario["nombre_rol"]
            
            # Debug logging
            print(f"✅ LOGIN EXITOSO - Email: {email}")
            print(f"   Rol asignado en sesión: '{session['rol']}'")
            print(f"   ID Usuario: {usuario['id_usuario']}")
            
            return jsonify({
                "exito": True, 
                "mensaje": "Bienvenido",
                "user_id": usuario["email"],
                "id_usuario": usuario["id_usuario"],  # ID numérico para APIs
                "nombre": usuario["nombre"],
                "saldo": float(usuario["saldo_actual"]),
                "rol": usuario["nombre_rol"]
            })
        else:
            print(f"❌ LOGIN FALLIDO - Email: {email}")
            return jsonify({"exito": False, "mensaje": "Credenciales incorrectas"}), 401
            
    except Exception as e:
        print(f"🔥 ERROR EN LOGIN: {e}")
        return jsonify({"exito": False, "mensaje": str(e)}), 400

# ==========================================
# SECCIÓN 2: PERFIL Y BILLETERA
# ==========================================

@app.route("/api/perfil", methods=["POST"])
def api_perfil():
    try:
        data = request.get_json(force=True)
        email = data.get("email")
        perfil = obtener_perfil(email)
        
        if perfil:
            # Convertimos Decimal a float por si acaso
            perfil['saldo_actual'] = float(perfil['saldo_actual'])
            return jsonify({"exito": True, "datos": perfil})
            
        return jsonify({"exito": False, "mensaje": "Usuario no encontrado"}), 404
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400

@app.route("/api/actualizar_perfil", methods=["POST"])
def api_update_perfil():
    try:
        data = request.get_json(force=True)
        email = data.get("email")
        nombre = data.get("nombre")
        apellido = data.get("apellido")
        password = data.get("password") 
        
        if actualizar_datos_usuario(email, nombre, apellido, password):
            return jsonify({"exito": True, "mensaje": "Datos actualizados"})
        return jsonify({"exito": False, "mensaje": "Error al actualizar"}), 400
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 500

@app.route("/api/transaccion", methods=["POST"])
def api_transaccion():
    try:
        data = request.get_json(force=True)
        email = data.get("email")
        monto = float(data.get("monto", 0))
        tipo = data.get("tipo") # "deposito" o "retiro"
        
        resultado = realizar_transaccion_saldo(email, monto, tipo)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400

# ==========================================
# SECCIÓN 3: AUDITORÍA Y CHECKLIST (HTML + PDF)
# ==========================================

# A. RUTA PARA VER EL MENÚ DEL AUDITOR
@app.route("/auditor")
def panel_auditor():
    # Detectar usuario desde App Inventor
    user_email = request.args.get('user_email')
    if user_email:
        session["user_id"] = user_email
    
    # Obtener email del usuario
    usuario_email = session.get("user_id", None)
    
    # Obtener el nombre del usuario desde la BD
    if usuario_email and usuario_email != "Invitado":
        perfil = obtener_perfil(usuario_email)
        usuario_nombre = perfil['nombre'] if perfil else "Invitado"
    else:
        usuario_nombre = "Invitado"
        
    return render_template("auditoria.html", usuario=usuario_nombre)

# B. RUTA PARA VER EL FORMULARIO CHECKLIST
@app.route("/auditor/realizar")
def realizar_auditoria():
    return render_template("auditor-realizar.html")

# C. RUTA PARA VER EL HISTORIAL
@app.route("/auditor/historial")
def historial_auditoria():
    # Obtener email del usuario autenticado
    usuario_email = session.get("user_id", None)
    
    if not usuario_email or usuario_email == "Invitado":
        return render_template("auditor-historial.html", auditorias=[])
    
    # Obtener historial de auditorías desde la BD
    try:
        auditorias = obtener_historial_auditorias(usuario_email)
        if auditorias is None:
            auditorias = []
        print(f"DEBUG: Auditorias recuperadas: {len(auditorias)}")
    except Exception as e:
        print(f"ERROR recuperando historial: {e}")
        auditorias = []
        
    return render_template("auditor-historial.html", auditorias=auditorias)

# Función para calcular no conformidades y buenas prácticas
def calcular_no_conformidades(respuestas):
    """Calcula no conformidades menores, mayores, sanciones y buenas prácticas"""
    consecutivas_no_cumple = 0
    consecutivas_cumple = 0
    no_conformidades_menores = []
    no_conformidades_mayores = []
    buenas_practicas = []
    preguntas_lista = list(respuestas.items())
    
    # Contadores para métricas
    total_preguntas = len(preguntas_lista)
    cumple_count = 0
    no_cumple_count = 0
    parcial_count = 0
    no_aplica_count = 0
    
    for i, (pregunta, respuesta) in enumerate(preguntas_lista):
        # Contar respuestas
        if respuesta == "Cumple":
            cumple_count += 1
        elif respuesta == "No Cumple":
            no_cumple_count += 1
        elif respuesta == "Cumple Parcialmente":
            parcial_count += 1
        elif respuesta == "No Aplica":
            no_aplica_count += 1
        
        # Detectar No Conformidades
        if respuesta in ["No Cumple", "Cumple Parcialmente"]:
            consecutivas_no_cumple += 1
            consecutivas_cumple = 0
            
            if consecutivas_no_cumple >= 3:
                inicio = max(0, i - 2)
                preguntas_afectadas = [preguntas_lista[j][0] for j in range(inicio, i + 1)]
                no_conformidades_menores.append({
                    "tipo": "menor",
                    "descripcion": f"No Conformidad Menor: {consecutivas_no_cumple} incumplimientos consecutivos",
                    "preguntas": preguntas_afectadas,
                    "ubicacion": f"Preguntas {inicio + 1} a {i + 1}"
                })
                consecutivas_no_cumple = 0
        # Detectar Buenas Prácticas
        elif respuesta == "Cumple":
            consecutivas_cumple += 1
            consecutivas_no_cumple = 0
            
            if consecutivas_cumple >= 3:
                inicio = max(0, i - 2)
                preguntas_afectadas = [preguntas_lista[j][0] for j in range(inicio, i + 1)]
                buenas_practicas.append({
                    "descripcion": f"Buena Práctica: {consecutivas_cumple} cumplimientos consecutivos",
                    "preguntas": preguntas_afectadas,
                    "ubicacion": f"Preguntas {inicio + 1} a {i + 1}"
                })
                consecutivas_cumple = 0
        else:
            consecutivas_no_cumple = 0
            consecutivas_cumple = 0
    
    # Verificar no conformidades mayores (3 menores = 1 mayor)
    if len(no_conformidades_menores) >= 3:
        no_conformidades_mayores.append({
            "tipo": "mayor",
            "descripcion": f"No Conformidad Mayor: {len(no_conformidades_menores)} NC menores acumuladas",
            "nc_menores_relacionadas": len(no_conformidades_menores)
        })
    
    # Verificar sanción económica (3 mayores)
    sancion = False
    if len(no_conformidades_mayores) >= 3:
        sancion = True
    
    # Calcular porcentajes
    preguntas_aplicables = total_preguntas - no_aplica_count
    porcentaje_cumplimiento = (cumple_count / preguntas_aplicables * 100) if preguntas_aplicables > 0 else 0
    porcentaje_no_cumplimiento = (no_cumple_count / preguntas_aplicables * 100) if preguntas_aplicables > 0 else 0
    porcentaje_parcial = (parcial_count / preguntas_aplicables * 100) if preguntas_aplicables > 0 else 0
    
    return {
        "menores": no_conformidades_menores,
        "mayores": no_conformidades_mayores,
        "sancion": sancion,
        "total_menores": len(no_conformidades_menores),
        "total_mayores": len(no_conformidades_mayores),
        "buenas_practicas": buenas_practicas,
        "total_buenas_practicas": len(buenas_practicas),
        "metricas": {
            "total_preguntas": total_preguntas,
            "preguntas_aplicables": preguntas_aplicables,
            "cumple": cumple_count,
            "no_cumple": no_cumple_count,
            "parcial": parcial_count,
            "no_aplica": no_aplica_count,
            "porcentaje_cumplimiento": round(porcentaje_cumplimiento, 2),
            "porcentaje_no_cumplimiento": round(porcentaje_no_cumplimiento, 2),
            "porcentaje_parcial": round(porcentaje_parcial, 2)
        }
    }


# D. API PARA GUARDAR LOS DATOS EN NEON
@app.route("/api/guardar_checklist", methods=["POST"])
def api_guardar_checklist():
    try:
        data = request.get_json(force=True)
        email = session.get("user_id") or data.get("email")
        
        if not email:
            return jsonify({"exito": False, "mensaje": "No logueado"}), 401

        respuestas = data.get("respuestas")
        comentarios = data.get("comentarios", {})
        
        # Calcular no conformidades
        no_conformidades = calcular_no_conformidades(respuestas)
        
        # Preparar datos completos para guardar
        datos_completos = {
            "respuestas": respuestas,
            "comentarios": comentarios,
            "no_conformidades": no_conformidades
        }
        
        # Convertimos el diccionario a texto para guardar en BD
        datos_json = json.dumps(datos_completos, ensure_ascii=False)
        
        id_audit = guardar_auditoria(email, f"Auditoría {data.get('fecha')}", datos_json)
        
        if id_audit:
            # URL para descargar el PDF
            pdf_url = f"/api/pdf_auditoria/{id_audit}"
            return jsonify({"exito": True, "mensaje": "Guardado", "pdf_url": pdf_url})
        else:
            return jsonify({"exito": False, "mensaje": "Error al guardar en BD"}), 500
            
    except Exception as e:
        print(f"Error checklist: {e}")
        return jsonify({"exito": False, "mensaje": str(e)}), 400

# E. API PARA GENERAR Y DESCARGAR EL PDF
@app.route("/auditor/ver_pdf/<int:id_auditoria>")
def ver_pdf_page(id_auditoria):
    return render_template("auditor-ver-pdf.html", id_auditoria=id_auditoria)

@app.route("/api/pdf_auditoria/<int:id_auditoria>", methods=["GET"])
def generar_pdf(id_auditoria):
    from pdf_generator import generar_pdf_profesional
    
    datos = obtener_datos_auditoria(id_auditoria)
    if not datos:
        return "Auditoría no encontrada", 404
    
    buffer = generar_pdf_profesional(datos, id_auditoria)
    
    return send_file(
        buffer, 
        as_attachment=False, 
        download_name=f"reporte_{id_auditoria}.pdf", 
        mimetype='application/pdf'
    )

# ==========================================
# SECCIÓN 4: PANEL DE ADMINISTRADOR
# ==========================================

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # En producción, verificaríamos session.get("rol") == "Administrador"
        # Por ahora, permitimos acceso para desarrollo o si hay sesión
        if "user_id" not in session:
             return render_template("index.html") # Redirigir a login si no hay sesión
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin.html")

@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    return render_template("admin-usuarios.html")

@app.route("/admin/gestion-usuarios")
@admin_required
def admin_gestion_usuarios():
    # Por ahora redirige directo a la lista de usuarios, 
    # pero podría tener el menú intermedio si se crean más roles
    return render_template("admin-gestion-usuarios.html")

@app.route("/admin/juegos")
@admin_required
def admin_juegos():
    return render_template("admin-juegos.html")

@app.route("/admin/info-general")
@admin_required
def admin_info_general():
    return render_template("admin-info-general.html")

@app.route("/admin/promociones")
@admin_required
def admin_promociones():
    return render_template("admin-promociones.html") # Necesita ser creado si no existe

@app.route("/admin/configuracion")
@admin_required
def admin_configuracion():
    return render_template("admin-configuracion.html") # Necesita ser creado

# --- API ENDPOINTS PARA ADMIN ---

@app.route("/api/admin/usuarios", methods=["GET"])
@admin_required
def api_admin_usuarios():
    from db_config import obtener_todos_usuarios
    users = obtener_todos_usuarios()
    return jsonify({"users": users})

@app.route("/api/admin/games", methods=["GET", "POST"])
@admin_required
def api_admin_games():
    from db_config import obtener_juegos, crear_juego
    
    if request.method == "GET":
        games = obtener_juegos()
        return jsonify({"games": games})
    
    if request.method == "POST":
        data = request.get_json(force=True)
        resultado = crear_juego(data)
        if resultado:
            return jsonify({"success": True})
        return jsonify({"error": "Error al crear juego"}), 500

@app.route("/api/admin/metrics", methods=["GET"])
@admin_required
def api_admin_metrics():
    from db_config import obtener_metricas
    metrics = obtener_metricas()
    return jsonify({"success": True, **metrics})

@app.route("/api/admin/promos", methods=["GET", "POST"])
@admin_required
def api_admin_promos():
    from db_config import obtener_promociones, crear_promocion
    
    if request.method == "GET":
        promos = obtener_promociones()
        return jsonify({"promos": promos})
        
    if request.method == "POST":
        data = request.get_json(force=True)
        resultado = crear_promocion(data)
        if resultado:
            return jsonify({"success": True})
        return jsonify({"error": "Error al crear promoción"}), 500

@app.route("/admin/usuarios/perfil")
@admin_required
def admin_usuario_perfil_page():
    return render_template("admin-usuario-perfil.html")

@app.route("/api/admin/usuarios/<int:id_usuario>", methods=["GET"])
@admin_required
def api_admin_usuario_detail(id_usuario):
    from db_config import obtener_usuario_por_id
    user = obtener_usuario_por_id(id_usuario)
    if user:
        # Convertir decimales a float
        if 'saldo_actual' in user and user['saldo_actual']:
            user['saldo_actual'] = float(user['saldo_actual'])
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False, "error": "Usuario no encontrado"}), 404

@app.route("/api/admin/usuarios/<int:id_usuario>", methods=["PUT"])
@admin_required
def api_admin_actualizar_usuario(id_usuario):
    """Actualizar datos de un usuario"""
    from db_config import actualizar_usuario_admin
    try:
        data = request.get_json(force=True)
        nombre = data.get('nombre')
        apellido = data.get('apellido')
        nueva_password = data.get('password', None)
        
        if actualizar_usuario_admin(id_usuario, nombre, apellido, nueva_password):
            return jsonify({"success": True, "mensaje": "Usuario actualizado correctamente"})
        return jsonify({"success": False, "error": "No se pudo actualizar el usuario"}), 500
    except Exception as e:
        print(f"Error actualizando usuario: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/usuarios/<int:id_usuario>/estado", methods=["PUT"])
@admin_required
def api_admin_cambiar_estado(id_usuario):
    """Cambiar estado activo/inactivo de un usuario"""
    from db_config import cambiar_estado_usuario
    try:
        data = request.get_json(force=True)
        activo = data.get('activo', True)
        
        if cambiar_estado_usuario(id_usuario, activo):
            return jsonify({"success": True, "mensaje": "Estado actualizado correctamente"})
        return jsonify({"success": False, "error": "No se pudo cambiar el estado"}), 500
    except Exception as e:
        print(f"Error cambiando estado: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/admin/usuarios/<int:id_usuario>", methods=["DELETE"])
@admin_required
def api_admin_eliminar_usuario(id_usuario):
    """Eliminar un usuario"""
    from db_config import eliminar_usuario
    try:
        if eliminar_usuario(id_usuario):
            return jsonify({"success": True, "mensaje": "Usuario eliminado correctamente"})
        return jsonify({"success": False, "error": "No se pudo eliminar el usuario"}), 500
    except Exception as e:
        print(f"Error eliminando usuario: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/admin/administradores")
@admin_required
def admin_administradores():
    return render_template("admin-administradores.html")

@app.route("/api/admin/administradores", methods=["GET"])
@admin_required
def api_admin_administradores():
    from db_config import obtener_administradores_y_auditores
    users = obtener_administradores_y_auditores()
    return jsonify({"success": True, "users": users})

# ==========================================
# SECCIÓN 5: PANEL DE AGENTE DE SOPORTE
# ==========================================

# Decorador para verificar que el usuario es Agente de Soporte
def agente_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Debug logging
        print(f"\n🔍 VERIFICACIÓN AGENTE_REQUIRED:")
        print(f"   user_id en sesión: {session.get('user_id', 'NO EXISTE')}")
        print(f"   rol en sesión: '{session.get('rol', 'NO EXISTE')}'")
        print(f"   Sesión completa: {dict(session)}")
        
        if "user_id" not in session:
            print("❌ ACCESO DENEGADO: No hay user_id en sesión")
            return render_template("login.html")
        
        rol_actual = session.get("rol")
        if rol_actual != "Agente de Soporte":
            print(f"❌ ACCESO DENEGADO: Rol '{rol_actual}' != 'Agente de Soporte'")
            return f"Acceso denegado. Solo agentes de soporte pueden acceder a esta sección. Tu rol actual es: {rol_actual}", 403
        
        print("✅ ACCESO PERMITIDO: Usuario es Agente de Soporte")
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS HTML ---

@app.route("/agente")
def panel_agente_wrapper():
    """Wrapper para manejar auto-login de App Inventor"""
    user_email_param = request.args.get('user_email')
    
    # Auto-login si viene desde App Inventor
    if user_email_param:
        print(f"🔄 Intento de auto-login: {user_email_param}")
        print(f"   Sesión actual: {dict(session)}")
        
        # Solo hacer auto-login si no hay sesión o es diferente usuario
        if not session.get('user_id') or session.get('user_id') != user_email_param:
            from db_config import get_db_connection
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.id_usuario, u.nombre, u.apellido, u.email, r.nombre as nombre_rol
                    FROM Usuario u
                    JOIN Rol r ON u.id_rol = r.id_rol
                    WHERE u.email = %s AND u.activo = true
                """, (user_email_param,))
                
                usuario = cursor.fetchone()
                conn.close()
                
                if usuario:
                    session.clear()
                    session.permanent = True
                    session["user_id"] = usuario[3]
                    session["rol"] = usuario[4]
                    print(f"✅ Auto-login exitoso: {session['user_id']} | Rol: {session['rol']}")
                else:
                    print(f"❌ Usuario no encontrado: {user_email_param}")
    
    # Ahora verificar acceso de agente
    @agente_required
    def panel_agente():
        print(f"📋 Accediendo a panel_agente - Usuario: {session.get('user_id')}")
        return render_template("agente.html")
    
    return panel_agente()

@app.route("/agente/dashboard")
@agente_required
def agente_dashboard():
    """Dashboard del agente con métricas"""
    return render_template("agente-dashboard.html")

@app.route("/agente/tickets")
@agente_required
def agente_tickets():
    """Lista de todos los tickets"""
    return render_template("agente-tickets.html")

@app.route("/agente/ticket/<int:id_ticket>")
@agente_required
def agente_ticket_detalle(id_ticket):
    """Detalle de un ticket específico"""
    return render_template("agente-ticket-detalle.html")

@app.route("/agente/mis-tickets")
@agente_required
def agente_mis_tickets():
    """Tickets asignados al agente"""
    return render_template("agente-mis-tickets.html")

@app.route("/agente/chats")
@agente_required
def agente_chats():
    """Chats en espera de ser asignados"""
    return render_template("agente-chats.html")

@app.route("/agente/chat/<int:id_chat>")
@agente_required
def agente_chat_activo(id_chat):
    """Vista de chat activo"""
    return render_template("agente-chat-activo.html")

@app.route("/agente/mis-chats")
@agente_required
def agente_mis_chats():
    """Chats asignados al agente"""
    return render_template("agente-mis-chats.html")

# --- API ENDPOINTS ---

# Dashboard
@app.route("/api/agente/dashboard/<int:id_agente>", methods=["GET"])
def api_agente_dashboard(id_agente):
    """Obtener métricas del dashboard para un agente"""
    try:
        from db_config import get_db_connection
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error de conexión"}), 500
        
        cursor = conn.cursor()
        
        # Tickets pendientes (Abiertos sin asignar)
        cursor.execute("""
            SELECT COUNT(*) FROM Soporte 
            WHERE estado = 'Abierto' AND id_agente IS NULL
        """)
        tickets_pendientes = cursor.fetchone()[0]
        
        # Mis tickets (asignados a este agente)
        cursor.execute("""
            SELECT COUNT(*) FROM Soporte 
            WHERE id_agente = %s AND estado != 'Cerrado'
        """, (id_agente,))
        mis_tickets = cursor.fetchone()[0]
        
        # Chats en espera
        cursor.execute("""
            SELECT COUNT(*) FROM Chat 
            WHERE estado = 'Esperando'
        """)
        chats_esperando = cursor.fetchone()[0]
        
        # Mis chats activos
        cursor.execute("""
            SELECT COUNT(*) FROM Chat 
            WHERE id_agente = %s AND estado = 'Activo'
        """, (id_agente,))
        mis_chats = cursor.fetchone()[0]
        
        # Cerrados hoy
        cursor.execute("""
            SELECT COUNT(*) FROM Soporte 
            WHERE id_agente = %s 
              AND estado = 'Cerrado' 
              AND DATE(fecha_cierre) = CURRENT_DATE
        """, (id_agente,))
        cerrados_hoy = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "tickets_pendientes": tickets_pendientes,
            "mis_tickets": mis_tickets,
            "chats_esperando": chats_esperando,
            "mis_chats": mis_chats,
            "cerrados_hoy": cerrados_hoy
        })
    except Exception as e:
        print(f"Error dashboard agente: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Tickets
@app.route("/api/agente/tickets", methods=["GET"])
def api_agente_tickets():
    """Obtener todos los tickets con filtros opcionales"""
    try:
        from db_config import get_db_connection
        conn = get_db_connection()
        if not conn:
            return jsonify({"tickets": []}), 500
        
        cursor = conn.cursor()
        estado = request.args.get('estado', None)
        asignado = request.args.get('asignado', None)
        
        query = """
            SELECT 
                s.id_ticket,
                s.asunto,
                s.mensaje,
                s.estado,
                s.fecha_creacion,
                uj.nombre || ' ' || uj.apellido as nombre_usuario,
                ua.nombre || ' ' || ua.apellido as nombre_agente
            FROM Soporte s
            JOIN Usuario uj ON s.id_jugador = uj.id_usuario
            LEFT JOIN Usuario ua ON s.id_agente = ua.id_usuario
            WHERE 1=1
        """
        
        params = []
        if estado:
            query += " AND s.estado = %s"
            params.append(estado)
        
        if asignado == 'si':
            query += " AND s.id_agente IS NOT NULL"
        elif asignado == 'no':
            query += " AND s.id_agente IS NULL"
        
        query += " ORDER BY s.fecha_creacion DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        tickets = []
        for row in rows:
            tickets.append({
                "id_ticket": row[0],
                "asunto": row[1],
                "mensaje": row[2],
                "estado": row[3],
                "fecha_creacion": row[4].isoformat() if row[4] else None,
                "nombre_usuario": row[5],
                "nombre_agente": row[6] if row[6] else None
            })
        
        conn.close()
        return jsonify({"tickets": tickets})
        
    except Exception as e:
        print(f"Error obtener tickets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"tickets": []}), 500
        return jsonify({"tickets": tickets})
    except Exception as e:
        print(f"Error obteniendo tickets: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/agente/ticket/<int:id_ticket>", methods=["GET"])
def api_agente_ticket_detalle(id_ticket):
    """Obtener detalles de un ticket y sus respuestas"""
    from db_config import obtener_ticket_por_id, obtener_respuestas_ticket
    try:
        ticket = obtener_ticket_por_id(id_ticket)
        if not ticket:
            return jsonify({"error": "Ticket no encontrado"}), 404
        
        respuestas = obtener_respuestas_ticket(id_ticket)
        return jsonify({"ticket": ticket, "respuestas": respuestas})
    except Exception as e:
        print(f"Error obteniendo ticket: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/agente/mis-tickets/<int:id_agente>", methods=["GET"])
def api_agente_mis_tickets(id_agente):
    """Obtener tickets asignados a un agente"""
    from db_config import obtener_tickets_agente
    try:
        tickets = obtener_tickets_agente(id_agente)
        return jsonify({"tickets": tickets})
    except Exception as e:
        print(f"Error obteniendo mis tickets: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/agente/asignar-ticket", methods=["POST"])
def api_agente_asignar_ticket():
    """Asignar un ticket a un agente"""
    from db_config import asignar_ticket
    try:
        id_ticket = request.form.get('id_ticket')
        id_agente = request.form.get('id_agente')
        
        if asignar_ticket(int(id_ticket), int(id_agente)):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "No se pudo asignar"}), 500
    except Exception as e:
        print(f"Error asignando ticket: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agente/responder-ticket", methods=["POST"])
def api_agente_responder_ticket():
    """Agregar una respuesta a un ticket"""
    from db_config import responder_ticket
    try:
        id_ticket = request.form.get('id_ticket')
        id_agente = request.form.get('id_agente')
        mensaje = request.form.get('mensaje')
        
        if responder_ticket(int(id_ticket), int(id_agente), mensaje, es_agente=True):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "No se pudo responder"}), 500
    except Exception as e:
        print(f"Error respondiendo ticket: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agente/cerrar-ticket", methods=["POST"])
def api_agente_cerrar_ticket():
    """Cerrar un ticket"""
    from db_config import cerrar_ticket
    try:
        id_ticket = request.form.get('id_ticket')
        
        if cerrar_ticket(int(id_ticket)):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "No se pudo cerrar"}), 500
    except Exception as e:
        print(f"Error cerrando ticket: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Chats
@app.route("/api/agente/chats-esperando", methods=["GET"])
def api_agente_chats_esperando():
    """Obtener chats en espera"""
    from db_config import obtener_chats_esperando
    try:
        chats = obtener_chats_esperando()
        return jsonify({"chats": chats})
    except Exception as e:
        print(f"Error obteniendo chats en espera: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/agente/mis-chats/<int:id_agente>", methods=["GET"])
def api_agente_mis_chats(id_agente):
    """Obtener chats asignados a un agente"""
    from db_config import obtener_chats_agente
    try:
        chats = obtener_chats_agente(id_agente)
        return jsonify({"chats": chats})
    except Exception as e:
        print(f"Error obteniendo mis chats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/agente/chat-mensajes/<int:id_chat>", methods=["GET"])
def api_agente_chat_mensajes(id_chat):
    """Obtener mensajes de un chat"""
    from db_config import obtener_mensajes_chat
    try:
        data = obtener_mensajes_chat(id_chat)
        if not data['chat']:
            return jsonify({"error": "Chat no encontrado"}), 404
        return jsonify(data)
    except Exception as e:
        print(f"Error obteniendo mensajes: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/agente/tomar-chat", methods=["POST"])
def api_agente_tomar_chat():
    """Tomar un chat (asignar al agente)"""
    from db_config import tomar_chat
    try:
        id_chat = request.form.get('id_chat')
        id_agente = request.form.get('id_agente')
        
        if tomar_chat(int(id_chat), int(id_agente)):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "No se pudo tomar el chat"}), 500
    except Exception as e:
        print(f"Error tomando chat: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agente/enviar-mensaje-chat", methods=["POST"])
def api_agente_enviar_mensaje_chat():
    """Enviar un mensaje en el chat"""
    from db_config import enviar_mensaje_chat
    try:
        id_chat = request.form.get('id_chat')
        id_agente = request.form.get('id_agente')
        mensaje = request.form.get('mensaje')
        
        if enviar_mensaje_chat(int(id_chat), int(id_agente), mensaje, es_agente=True):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "No se pudo enviar el mensaje"}), 500
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agente/cerrar-chat", methods=["POST"])
def api_agente_cerrar_chat():
    """Cerrar un chat"""
    from db_config import cerrar_chat
    try:
        id_chat = request.form.get('id_chat')
        
        if cerrar_chat(int(id_chat)):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "No se pudo cerrar"}), 500
    except Exception as e:
        print(f"Error cerrando chat: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

