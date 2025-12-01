from flask import Flask, session, jsonify, request, send_file
import os
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from db_config import guardar_auditoria, obtener_datos_auditoria

# Importamos solo las funciones de gestión de usuarios y saldo
from db_config import registrar_usuario_nuevo, validar_login

# --- 1. INICIALIZACIÓN ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# --- 2. CONFIGURACIÓN DE COOKIES (CRÍTICO PARA APP INVENTOR) ---
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hora

# ==========================================
# RUTAS API (APP INVENTOR)
# ==========================================


@app.route("/", methods=["GET"])
def index():
    return "Servidor Central del Casino Activo. Usa /api/login o /api/registrar."


@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    print("--- INICIO DE REGISTRO ---")
    try:
        # Intentamos leer JSON (force=True ayuda si el header falla en App Inventor)
        datos = request.get_json(force=True, silent=True)

        if not datos:
            cuerpo = request.get_data(as_text=True)
            print(f"❌ ERROR: JSON vacío o inválido. Recibido: {cuerpo}")
            return jsonify({"exito": False, "mensaje": "JSON inválido"}), 400

        print(f"📥 Datos recibidos: {datos}")

        # Validar campos obligatorios
        campos = ["nombre", "apellido", "curp", "email", "password"]
        faltantes = [campo for campo in campos if campo not in datos]

        if faltantes:
            return (
                jsonify({"exito": False, "mensaje": f"Faltan datos: {faltantes}"}),
                400,
            )

        # Guardar en Neon (llama a db_config.py)
        resultado = registrar_usuario_nuevo(datos)

        codigo = 200 if resultado["exito"] else 400
        return jsonify(resultado), codigo

    except Exception as e:
        print(f"🔥 ERROR INTERNO: {e}")
        return (
            jsonify({"exito": False, "mensaje": f"Error del servidor: {str(e)}"}),
            500,
        )


@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        datos = request.get_json(force=True)
        email = datos.get("email")
        password = datos.get("password")

        # Validar credenciales en Neon
        usuario = validar_login(email, password)

        if usuario:
            # Crear sesión segura
            session.clear()
            session.permanent = True
            session["user_id"] = usuario["email"]
            session["rol"] = usuario["nombre_rol"]

            # Respondemos con el ROL para que App Inventor sepa qué pantalla abrir
            return jsonify(
                {
                    "exito": True,
                    "mensaje": "Bienvenido",
                    "user_id": usuario["email"],
                    "nombre": usuario[
                        "nombre"
                    ],  # <--- Nombre del usuario para mostrar en pantalla
                    "saldo": float(usuario["saldo_actual"]),
                    "rol": usuario["nombre_rol"],  # <--- CLAVE PARA TU REDIRECCIÓN
                }
            )
        else:
            return jsonify({"exito": False, "mensaje": "Credenciales incorrectas"}), 401

    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400


# ==========================================
# ARRANQUE DEL SERVIDOR

# --- EN app.py ---
from db_config import (
    obtener_perfil,
    actualizar_datos_usuario,
    realizar_transaccion_saldo,
)


@app.route("/api/perfil", methods=["POST"])
def api_perfil():
    # App Inventor pide los datos al entrar a la pantalla
    data = request.get_json(force=True)
    email = data.get("email")
    perfil = obtener_perfil(email)
    if perfil:
        return jsonify({"exito": True, "datos": perfil})
    return jsonify({"exito": False, "mensaje": "Error al cargar perfil"}), 400


@app.route("/api/actualizar_perfil", methods=["POST"])
def api_update_perfil():
    data = request.get_json(force=True)
    email = data.get("email")
    nombre = data.get("nombre")
    apellido = data.get("apellido")
    password = data.get("password")  # Puede venir vacío si no quiere cambiarla

    if actualizar_datos_usuario(email, nombre, apellido, password):
        return jsonify({"exito": True, "mensaje": "Datos actualizados"})
    return jsonify({"exito": False, "mensaje": "Error al actualizar"}), 400


@app.route("/api/transaccion", methods=["POST"])
def api_transaccion():
    data = request.get_json(force=True)
    email = data.get("email")
    monto = float(data.get("monto", 0))
    tipo = data.get("tipo")  # "deposito" o "retiro"

    resultado = realizar_transaccion_saldo(email, monto, tipo)
    return jsonify(resultado)

    # --- AUDITORIA Y CHECKLISTS ---


def guardar_auditoria(email, resumen, datos_json):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()

        # Insertamos en la tabla Auditoria
        # Usamos una subconsulta para obtener el id_usuario desde el email
        sql = """
            INSERT INTO Auditoria (id_usuario, resumen, datos_auditoria, fecha_auditoria)
            VALUES (
                (SELECT id_usuario FROM Usuario WHERE email = %s),
                %s, %s, NOW()
            )
            RETURNING id_auditoria;
        """
        # datos_json debe ser un string JSON válido (json.dumps)
        cursor.execute(sql, (email, resumen, datos_json))
        id_auditoria = cursor.fetchone()[0]

        conn.commit()
        conn.close()
        return id_auditoria
    except Exception as e:
        print(f"Error auditoria: {e}")
        if conn:
            conn.rollback()
        return None


def obtener_datos_auditoria(id_auditoria):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Traemos la info de la auditoría y quién la hizo
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
    except Exception as e:
        return None

    # 1. GUARDAR DATOS


@app.route("/api/guardar_checklist", methods=["POST"])
def api_guardar_checklist():
    try:
        data = request.get_json(force=True)
        email = data.get("email")
        resumen = data.get("resumen")  # Ej: "Revisión diaria Máquinas"
        checklist = data.get(
            "checklist"
        )  # Diccionario Ej: {"luces": "OK", "limpieza": "FALLO"}

        # Convertimos el diccionario a texto JSON para la base de datos
        checklist_json = json.dumps(checklist)

        id_audit = guardar_auditoria(email, resumen, checklist_json)

        if id_audit:
            # Devolvemos la URL directa para descargar el PDF
            pdf_url = f"/api/pdf_auditoria/{id_audit}"
            return jsonify({"exito": True, "mensaje": "Guardado", "pdf_url": pdf_url})
        else:
            return jsonify({"exito": False, "mensaje": "Error al guardar en BD"}), 500

    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400


# 2. GENERAR Y DESCARGAR PDF
@app.route("/api/pdf_auditoria/<int:id_auditoria>", methods=["GET"])
def generar_pdf(id_auditoria):
    # 1. Obtener datos de la BD
    datos = obtener_datos_auditoria(id_auditoria)
    if not datos:
        return "Auditoría no encontrada", 404

    # 2. Crear PDF en memoria (RAM)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # 3. Dibujar contenido
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"REPORTE DE AUDITORÍA #{id_auditoria}")

    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Auditor: {datos['nombre']} {datos['apellido']}")
    c.drawString(100, 705, f"Fecha: {datos['fecha_auditoria']}")
    c.drawString(100, 690, f"Resumen: {datos['resumen']}")

    c.line(100, 680, 500, 680)  # Línea separadora

    # Dibujar el Checklist
    y = 650
    items = datos["datos_auditoria"]  # PostgreSQL ya lo devuelve como diccionario

    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "DETALLE DE REVISIÓN:")
    y -= 20

    c.setFont("Helvetica", 11)
    for key, value in items.items():
        # Ejemplo: "Luces: OK"
        estado = "✅ APROBADO" if value else "❌ FALLO"
        c.drawString(120, y, f"- {key}: {estado}")
        y -= 20

    c.showPage()
    c.save()

    # 4. Enviar archivo al navegador/celular
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"auditoria_{id_auditoria}.pdf",
        mimetype="application/pdf",
    )  # 1. GUARDAR DATOS


@app.route("/api/guardar_checklist", methods=["POST"])
def api_guardar_checklist():
    try:
        data = request.get_json(force=True)
        email = data.get("email")
        resumen = data.get("resumen")  # Ej: "Revisión diaria Máquinas"
        checklist = data.get(
            "checklist"
        )  # Diccionario Ej: {"luces": "OK", "limpieza": "FALLO"}

        # Convertimos el diccionario a texto JSON para la base de datos
        checklist_json = json.dumps(checklist)

        id_audit = guardar_auditoria(email, resumen, checklist_json)

        if id_audit:
            # Devolvemos la URL directa para descargar el PDF
            pdf_url = f"/api/pdf_auditoria/{id_audit}"
            return jsonify({"exito": True, "mensaje": "Guardado", "pdf_url": pdf_url})
        else:
            return jsonify({"exito": False, "mensaje": "Error al guardar en BD"}), 500

    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400


# 2. GENERAR Y DESCARGAR PDF
@app.route("/api/pdf_auditoria/<int:id_auditoria>", methods=["GET"])
def generar_pdf(id_auditoria):
    # 1. Obtener datos de la BD
    datos = obtener_datos_auditoria(id_auditoria)
    if not datos:
        return "Auditoría no encontrada", 404

    # 2. Crear PDF en memoria (RAM)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # 3. Dibujar contenido
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"REPORTE DE AUDITORÍA #{id_auditoria}")

    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Auditor: {datos['nombre']} {datos['apellido']}")
    c.drawString(100, 705, f"Fecha: {datos['fecha_auditoria']}")
    c.drawString(100, 690, f"Resumen: {datos['resumen']}")

    c.line(100, 680, 500, 680)  # Línea separadora

    # Dibujar el Checklist
    y = 650
    items = datos["datos_auditoria"]  # PostgreSQL ya lo devuelve como diccionario

    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "DETALLE DE REVISIÓN:")
    y -= 20

    c.setFont("Helvetica", 11)
    for key, value in items.items():
        # Ejemplo: "Luces: OK"
        estado = "✅ APROBADO" if value else "❌ FALLO"
        c.drawString(120, y, f"- {key}: {estado}")
        y -= 20

    c.showPage()
    c.save()

    # 4. Enviar archivo al navegador/celular
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"auditoria_{id_auditoria}.pdf",
        mimetype="application/pdf",
    )


# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
