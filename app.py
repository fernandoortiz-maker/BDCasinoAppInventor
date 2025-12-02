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
            
            return jsonify({
                "exito": True, 
                "mensaje": "Bienvenido",
                "user_id": usuario["email"],
                "nombre": usuario["nombre"],
                "saldo": float(usuario["saldo_actual"]),
                "rol": usuario["nombre_rol"]
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

        checklist = data.get("respuestas")
        # Convertimos el diccionario a texto para guardar en BD
        checklist_json = json.dumps(checklist)
        
        id_audit = guardar_auditoria(email, f"Auditoría {data.get('fecha')}", checklist_json)
        
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
    y = height - 150
    items = datos['datos_auditoria']
    
    # Asegurar que items es un diccionario
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception as e:
            print(f"Error parseando JSON: {e}")
            items = {}
            
    if not isinstance(items, dict):
         items = {}
    
    c.setFont(font_body, size_body)
    
    # Dimensiones de la tabla
    # Col 1: Pregunta (Ancho variable)
    # Col 2: CUMPLE (Ancho fijo)
    # Col 3: X (Casilla)
    # Col 4: NO CUMPLE (Ancho fijo)
    # Col 5: X (Casilla)
    # Col 6: PARCIAL (Ancho fijo)
    # Col 7: X (Casilla)
    
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
    
    for pregunta, respuesta in items.items():
        # Control de salto de página
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont(font_body, size_body)
        
        # Determinar marcas
        estado = str(respuesta)
        mark_cumple = "X" if "Cumple" in estado and "No" not in estado and "Parcialmente" not in estado else ""
        mark_no_cumple = "X" if "No Cumple" in estado else ""
        mark_parcial = "X" if "Parcialmente" in estado else ""
        
        # Dibujar líneas horizontales (Arriba y Abajo de la fila)
        c.setLineWidth(0.5)
        c.line(x_start, y + row_height, x_end, y + row_height) # Arriba
        c.line(x_start, y, x_end, y) # Abajo
        
        # Dibujar líneas verticales
        c.line(x_start, y, x_start, y + row_height) # Inicio
        c.line(x_cumple_label, y, x_cumple_label, y + row_height) # Separa Pregunta de Cumple
        c.line(x_cumple_box, y, x_cumple_box, y + row_height) # Separa Label Cumple de Box
        c.line(x_no_cumple_label, y, x_no_cumple_label, y + row_height) # Separa Box Cumple de Label No Cumple
        c.line(x_no_cumple_box, y, x_no_cumple_box, y + row_height) # Separa Label No Cumple de Box
        c.line(x_parcial_label, y, x_parcial_label, y + row_height) # Separa Box No Cumple de Label Parcial
        c.line(x_parcial_box, y, x_parcial_box, y + row_height) # Separa Label Parcial de Box
        c.line(x_end, y, x_end, y + row_height) # Fin
        
        # Texto Centrado Verticalmente
        text_y = y + 10
        
        # Pregunta (Recortar si es muy larga para que quepa en la celda)
        c.setFont(font_body, 10) # Un poco más pequeño para que quepa mejor
        pregunta_corta = (pregunta[:45] + '..') if len(pregunta) > 45 else pregunta
        c.drawString(x_start + 5, text_y, pregunta_corta)
        
        # Labels
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x_cumple_label + 5, text_y, "CUMPLE")
        
        c.drawString(x_no_cumple_label + 5, text_y + 5, "NO")
        c.drawString(x_no_cumple_label + 5, text_y - 5, "CUMPLE")
        
        c.drawString(x_parcial_label + 5, text_y + 5, "CUMPLE")
        c.drawString(x_parcial_label + 5, text_y - 5, "PARCIAL")
        
        # Marcas (X)
        c.setFont("Helvetica-Bold", 12)
        if mark_cumple:
            c.drawCentredString(x_cumple_box + 12, text_y, "X")
        if mark_no_cumple:
            c.drawCentredString(x_no_cumple_box + 12, text_y, "X")
        if mark_parcial:
            c.drawCentredString(x_parcial_box + 12, text_y, "X")
            
        y -= row_height
        
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
