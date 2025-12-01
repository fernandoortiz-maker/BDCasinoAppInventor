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
    
    # --- ENCABEZADO ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "REPORTE DE AUDITORÍA ISO 14001")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 75, f"Auditor: {datos['nombre']} {datos['apellido']}")
    c.drawString(50, height - 90, f"Email: {datos['email']}")
    c.drawString(400, height - 75, f"Fecha: {datos['fecha_auditoria']}")
    c.drawString(400, height - 90, f"ID Reporte: #{id_auditoria}")
    
    c.line(50, height - 105, 550, height - 105)
    
    # --- CONTENIDO ---
    y = height - 130
    items = datos['datos_auditoria'] # Es un diccionario
    
    c.setFont("Helvetica", 9)
    
    for pregunta, respuesta in items.items():
        # Control de salto de página
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)
        
        # Color del estado
        estado = str(respuesta)
        if "No Cumple" in estado:
            c.setFillColorRGB(0.8, 0, 0) # Rojo
        elif "Parcialmente" in estado:
            c.setFillColorRGB(1, 0.5, 0) # Naranja
        else:
            c.setFillColorRGB(0, 0.5, 0) # Verde oscuro
            
        # Imprimir Pregunta (recortada si es muy larga)
        pregunta_corta = (pregunta[:90] + '..') if len(pregunta) > 90 else pregunta
        c.drawString(50, y, f"• {pregunta_corta}")
        
        # Imprimir Respuesta (alineada a la derecha)
        c.drawRightString(550, y, f"[{estado}]")
        
        # Restaurar color negro para la siguiente línea
        c.setFillColorRGB(0, 0, 0)
        y -= 15
        
    c.save()
    buffer.seek(0)
    
    return send_file(
        buffer, 
        as_attachment=False,  # Mostrar en navegador en lugar de descargar
        download_name=f"reporte_{id_auditoria}.pdf", 
        mimetype='application/pdf'
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
