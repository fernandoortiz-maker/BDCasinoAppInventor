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

            # --- GENERAR REDIRECT URL PARA APP INVENTOR ---
            # Esto permite que App Inventor navegue directamente sin perder la sesión
            # El WebViewer debe usar esta URL tal cual.
            rol = usuario["nombre_rol"]
            redirect_url = "/"

            if rol == "Administrador":
                redirect_url = f"/admin?user_email={usuario['email']}"
            elif rol in ["Agente", "Soporte"]:
                redirect_url = f"/agente?user_email={usuario['email']}"
            else:
                redirect_url = f"/?user_email={usuario['email']}"
            
            return jsonify({
                "exito": True, 
                "mensaje": "Bienvenido",
                "user_id": usuario["email"],
                "nombre": usuario["nombre"],
                "saldo": float(usuario["saldo_actual"]),
                "rol": usuario["nombre_rol"],
                "redirect_url": redirect_url  # <--- NUEVO CAMPO CRÍTICO
            })
        else:
            return jsonify({"exito": False, "mensaje": "Credenciales incorrectas"}), 401
            
    except Exception as e:
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


# D. API PARA GUARDAR LOS DATOS EN NEON
@app.route("/api/guardar_checklist", methods=["POST"])
def api_guardar_checklist():
    try:
        data = request.get_json(force=True)
        email = session.get("user_id") or data.get("email")
        
        if not email:
            return jsonify({"exito": False, "mensaje": "No logueado"}), 401

        respuestas = data.get("respuestas", {})
        comentarios = data.get("comentarios", {})
        
        # Combinar respuestas y comentarios en un solo objeto
        datos_auditoria = {
            "respuestas": respuestas,
            "comentarios": comentarios
        }
        
        checklist_json = json.dumps(datos_auditoria)
        
        id_audit = guardar_auditoria(email, f"Auditoría {data.get('fecha')}", checklist_json)
        
        if id_audit:
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
    datos = obtener_datos_auditoria(id_auditoria)
    if not datos:
        return "Auditoría no encontrada", 404
        
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # --- CONFIGURACIÓN DE FUENTES ---
    # Usaremos Helvetica como sustituto estándar de Arial
    font_title = "Helvetica-Bold"
    font_body = "Helvetica"
    size_title = 14
    size_body = 12
    
    # --- ENCABEZADO ---
    c.setFont(font_title, size_title)
    c.drawString(50, height - 50, "REPORTE DE AUDITORÍA ISO 14001")
    
    c.setFont(font_body, size_body)
    c.drawString(50, height - 80, f"Auditor: {datos['nombre']} {datos['apellido']}")
    c.drawString(50, height - 100, f"Email: {datos['email']}")
    c.drawString(400, height - 80, f"Fecha: {datos['fecha_auditoria']}")
    c.drawString(400, height - 100, f"ID Reporte: #{id_auditoria}")
    
    c.setLineWidth(1)
    c.line(50, height - 115, 562, height - 115)
    
    # --- CONTENIDO ---
    raw_data = datos['datos_auditoria']
    
    # Parsear JSON si es string
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except Exception as e:
            print(f"Error parseando JSON: {e}")
            raw_data = {}
    
    # Determinar estructura: nueva (con respuestas/comentarios) o antigua (solo respuestas)
    if isinstance(raw_data, dict) and 'respuestas' in raw_data:
        items = raw_data.get('respuestas', {})
        comentarios = raw_data.get('comentarios', {})
    else:
        items = raw_data if isinstance(raw_data, dict) else {}
        comentarios = {}
    
    # --- ANÁLISIS DE RESPUESTAS PARA CLASIFICACIÓN ---
    total_cumple = 0
    total_no_cumple = 0
    total_parcial = 0
    total_no_aplica = 0
    total_respuestas = len(items)
    
    for pregunta, respuesta in items.items():
        estado = str(respuesta)
        if "No Cumple" in estado:
            total_no_cumple += 1
        elif "Parcialmente" in estado:
            total_parcial += 1
        elif "No Aplica" in estado:
            total_no_aplica += 1
        elif "Cumple" in estado:
            total_cumple += 1
    
    # Calcular clasificación
    total_problemas = total_no_cumple + total_parcial
    porcentaje_cumple = (total_cumple / total_respuestas * 100) if total_respuestas > 0 else 0
    
    # Determinar nivel de clasificación
    if total_problemas == 0 and porcentaje_cumple >= 90:
        clasificacion = "✅ BUENA PRÁCTICA"
        clasificacion_color = (0.2, 0.7, 0.2)  # Verde
        clasificacion_desc = "Excelente desempeño ambiental. Todas las áreas cumplen con los requisitos."
    elif total_problemas <= 2:
        clasificacion = "📋 CUMPLIMIENTO ACEPTABLE"
        clasificacion_color = (0.4, 0.6, 0.2)  # Verde-amarillo
        clasificacion_desc = f"Desempeño aceptable con {total_problemas} observaciones menores."
    elif total_problemas <= 5:
        clasificacion = "⚠️ NO CONFORMIDAD MENOR"
        clasificacion_color = (0.9, 0.7, 0.1)  # Amarillo
        clasificacion_desc = f"Se detectaron {total_problemas} incumplimientos que requieren atención."
    elif total_problemas <= 10:
        clasificacion = "🔶 NO CONFORMIDAD MAYOR"
        clasificacion_color = (0.9, 0.5, 0.1)  # Naranja
        clasificacion_desc = f"Múltiples incumplimientos ({total_problemas}) que requieren acción correctiva inmediata."
    else:
        clasificacion = "🚨 MULTA / SANCIÓN POTENCIAL"
        clasificacion_color = (0.8, 0.2, 0.2)  # Rojo
        clasificacion_desc = f"Incumplimiento grave con {total_problemas} no conformidades. Riesgo de sanción."
    
    # --- DIBUJAR RESUMEN DE CLASIFICACIÓN ---
    # Fondo del cuadro de clasificación
    c.setFillColorRGB(*clasificacion_color, alpha=0.1)
    c.rect(50, height - 200, 512, 70, fill=True, stroke=False)
    
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_title, 14)
    c.drawString(55, height - 145, "RESULTADO DE LA AUDITORÍA:")
    
    c.setFillColorRGB(*clasificacion_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(260, height - 145, clasificacion)
    
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_body, 10)
    c.drawString(55, height - 165, clasificacion_desc)
    
    # Estadísticas rápidas
    c.setFont(font_body, 9)
    stats_y = height - 185
    c.drawString(55, stats_y, f"📊 Total: {total_respuestas} items  |  ✅ Cumple: {total_cumple}  |  ❌ No Cumple: {total_no_cumple}  |  ⚠️ Parcial: {total_parcial}  |  ➖ N/A: {total_no_aplica}")
    
    c.setLineWidth(1)
    c.line(50, height - 205, 562, height - 205)
    
    y = height - 230
    
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_body, size_body)
    
    # Coordenadas X
    x_start = 50
    x_cumple_label = 280
    x_cumple_box = 340
    x_no_cumple_label = 365
    x_no_cumple_box = 445
    x_parcial_label = 470
    x_parcial_box = 537
    x_end = 562
    
    row_height = 30
    
    # Agrupar preguntas por sección (basado en nombres de sección en comentarios)
    secciones_con_comentarios = set(comentarios.keys())
    seccion_actual = None
    preguntas_seccion_count = 0
    
    for pregunta, respuesta in items.items():
        # Control de salto de página
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont(font_body, size_body)
        
        # Determinar marcas
        estado = str(respuesta)
        mark_cumple = "X" if "Cumple" in estado and "No" not in estado and "Parcialmente" not in estado else ""
        mark_no_cumple = "X" if "No Cumple" in estado else ""
        mark_parcial = "X" if "Parcialmente" in estado else ""
        
        # Dibujar líneas horizontales
        c.setLineWidth(0.5)
        c.line(x_start, y + row_height, x_end, y + row_height)
        c.line(x_start, y, x_end, y)
        
        # Dibujar líneas verticales
        c.line(x_start, y, x_start, y + row_height)
        c.line(x_cumple_label, y, x_cumple_label, y + row_height)
        c.line(x_cumple_box, y, x_cumple_box, y + row_height)
        c.line(x_no_cumple_label, y, x_no_cumple_label, y + row_height)
        c.line(x_no_cumple_box, y, x_no_cumple_box, y + row_height)
        c.line(x_parcial_label, y, x_parcial_label, y + row_height)
        c.line(x_parcial_box, y, x_parcial_box, y + row_height)
        c.line(x_end, y, x_end, y + row_height)
        
        text_y = y + 10
        
        # Pregunta
        c.setFont(font_body, 10)
        pregunta_corta = (pregunta[:45] + '..') if len(pregunta) > 45 else pregunta
        c.drawString(x_start + 5, text_y, pregunta_corta)
        
        # Labels
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x_cumple_label + 5, text_y, "CUMPLE")
        c.drawString(x_no_cumple_label + 5, text_y + 5, "NO")
        c.drawString(x_no_cumple_label + 5, text_y - 5, "CUMPLE")
        c.drawString(x_parcial_label + 5, text_y + 5, "CUMPLE")
        c.drawString(x_parcial_label + 5, text_y - 5, "PARCIAL")
        
        # Marcas
        c.setFont("Helvetica-Bold", 12)
        if mark_cumple:
            c.drawCentredString(x_cumple_box + 12, text_y, "X")
        if mark_no_cumple:
            c.drawCentredString(x_no_cumple_box + 12, text_y, "X")
        if mark_parcial:
            c.drawCentredString(x_parcial_box + 12, text_y, "X")
            
        y -= row_height
    
    # Agregar sección de comentarios al final si hay comentarios
    if comentarios:
        y -= 20
        if y < 150:
            c.showPage()
            y = height - 50
            
        c.setFont(font_title, size_title)
        c.drawString(50, y, "OBSERVACIONES Y COMENTARIOS")
        c.line(50, y - 5, 300, y - 5)
        y -= 30
        
        c.setFont(font_body, 10)
        for seccion, comentario in comentarios.items():
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont(font_body, 10)
            
            # Título de la sección
            c.setFont("Helvetica-Bold", 10)
            seccion_corta = (seccion[:60] + '..') if len(seccion) > 60 else seccion
            c.drawString(50, y, f"• {seccion_corta}")
            y -= 15
            
            # Comentario (dividir en líneas si es largo)
            c.setFont(font_body, 9)
            palabras = comentario.split()
            linea = ""
            for palabra in palabras:
                if len(linea + " " + palabra) < 90:
                    linea = linea + " " + palabra if linea else palabra
                else:
                    c.drawString(60, y, linea)
                    y -= 12
                    linea = palabra
                    if y < 50:
                        c.showPage()
                        y = height - 50
            if linea:
                c.drawString(60, y, linea)
                y -= 20
        
    c.save()
    buffer.seek(0)
    
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
        # Detectar usuario desde App Inventor (parámetro URL) o sesión
        # Acepta tanto user_id como user_email para compatibilidad
        user_id = request.args.get('user_id') or request.args.get('user_email') or session.get("user_id")
        
        # Verificar que hay usuario válido
        if not user_id or user_id == "Invitado":
            return jsonify({"error": "No autorizado", "mensaje": "Debe iniciar sesión para acceder al panel de administración"}), 401
        
        # Guardar en sesión
        session["user_id"] = user_id
        session.permanent = True
        
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

@app.route("/admin/administradores")
@admin_required
def admin_administradores():
    return render_template("admin-administradores.html")

@app.route("/api/admin/administradores", methods=["GET"])
@admin_required
def api_admin_administradores():
    """Obtener lista de usuarios con rol Administrador"""
    from db_config import obtener_administradores
    admins = obtener_administradores()
    return jsonify({"admins": admins})

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
    return render_template("admin-configuracion.html")

# --- API ENDPOINTS PARA GESTIÓN DE IPs ---

@app.route("/api/admin/ips-bloqueadas", methods=["GET"])
@admin_required
def api_admin_ips_bloqueadas():
    """Obtener lista de IPs bloqueadas"""
    from db_config import obtener_ips_bloqueadas
    ips = obtener_ips_bloqueadas()
    return jsonify({"ips": ips})

@app.route("/api/admin/ips-bloqueadas", methods=["POST"])
@admin_required
def api_admin_bloquear_ip():
    """Agregar una IP a la lista de bloqueadas"""
    from db_config import agregar_ip_bloqueada
    try:
        data = request.get_json(force=True)
        direccion_ip = data.get("direccion_ip", "").strip()
        motivo = data.get("motivo", "")
        
        if not direccion_ip:
            return jsonify({"exito": False, "mensaje": "La dirección IP es requerida"}), 400
        
        # Obtener email del admin que bloquea
        bloqueado_por = session.get("user_id", "Admin")
        
        resultado = agregar_ip_bloqueada(direccion_ip, motivo, bloqueado_por)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 500

@app.route("/api/admin/ips-bloqueadas/<int:id_ip>", methods=["DELETE"])
@admin_required
def api_admin_desbloquear_ip(id_ip):
    """Eliminar una IP de la lista de bloqueadas"""
    from db_config import eliminar_ip_bloqueada
    if eliminar_ip_bloqueada(id_ip):
        return jsonify({"exito": True, "mensaje": "IP desbloqueada correctamente"})
    return jsonify({"exito": False, "mensaje": "No se pudo desbloquear la IP"}), 500

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

@app.route("/api/admin/usuarios/<int:id_usuario>/estado", methods=["POST"])
@admin_required
def api_admin_usuario_cambiar_estado(id_usuario):
    """Cambiar el estado activo/inactivo de un usuario"""
    from db_config import cambiar_estado_usuario
    try:
        data = request.get_json(force=True)
        nuevo_estado = data.get("activo", True)
        
        resultado = cambiar_estado_usuario(id_usuario, nuevo_estado)
        if resultado:
            return jsonify({"success": True, "mensaje": f"Usuario {'activado' if nuevo_estado else 'desactivado'} correctamente"})
        return jsonify({"success": False, "error": "No se pudo actualizar el estado"}), 500
    except Exception as e:
        print(f"Error cambiando estado: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# SECCIÓN 5: PANEL DE AGENTE DE SOPORTE
# ==========================================

def agente_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Detectar usuario desde App Inventor (parámetro URL) o sesión
        user_id = request.args.get('user_id') or request.args.get('user_email') or session.get("user_id")
        
        # Verificar que hay usuario válido
        if not user_id or user_id == "Invitado":
            return jsonify({"error": "No autorizado", "mensaje": "Debe iniciar sesión para acceder al panel de agente"}), 401
        
        # Guardar en sesión
        session["user_id"] = user_id
        session.permanent = True
        
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS HTML ---

@app.route("/agente")
@agente_required
def panel_agente():
    """Menú principal del panel de agente"""
    return render_template("agente.html")

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
    from db_config import obtener_dashboard_agente
    try:
        metricas = obtener_dashboard_agente(id_agente)
        return jsonify(metricas)
    except Exception as e:
        print(f"Error dashboard agente: {e}")
        return jsonify({"error": str(e)}), 500

# Tickets
@app.route("/api/agente/tickets", methods=["GET"])
def api_agente_tickets():
    """Obtener todos los tickets con filtros opcionales"""
    from db_config import obtener_tickets
    try:
        estado = request.args.get('estado', None)
        asignado = request.args.get('asignado', None)
        tickets = obtener_tickets(estado, asignado)
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

