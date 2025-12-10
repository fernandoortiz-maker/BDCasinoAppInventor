"""
FIX URGENTE PARA EL ACCESO DEL AGENTE

PROBLEMA ENCONTRADO:
- La sesión tiene: {'_permanent': True, 'user_id': 'auditor@gmail.com'}  
- NO tiene 'rol'
- Está accediendo con ?user_email=soporte@gmail.com pero sesión tiene auditor

CAUSA:
El usuario NO está haciendo login con /api/login antes de acceder a /agente
Está intentando acceder directamente con ?user_email= (parámetro de App Inventor)

SOLUCIÓN 1: Login primero
El usuario debe hacer login correcto que ejecute /api/login para que guarde session['rol']

SOLUCIÓN 2: Crear endpoint de autologin para App Inventor
"""

# Agregar esta ruta ANTES de @app.route("/agente")
# Línea 573 aproximadamente

@app.route("/agente")
@agente_required
def panel_agente():
    """Menú principal del panel de agente"""
    # Verificar si viene de App Inventor con user_email
    user_email_param = request.args.get('user_email')
    
    if user_email_param:
        print(f"🔄 Auto-login desde App Inventor: {user_email_param}")
        
        # Verificar si el usuario existe y es agente
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
            
            if usuario and usuario[4] == "Agente de Soporte":
                # Auto-login: guardar en sesión
                session.clear()
                session.permanent = True
                session["user_id"] = usuario[3]  # email
                session["rol"] = usuario[4]  # nombre_rol
                
                print(f"✅ Auto-login exitoso")
                print(f"   Email: {session['user_id']}")
                print(f"   Rol: {session['rol']}")
    
    print(f"📋 Accediendo a panel_agente - Usuario: {session.get('user_id')}")
    return render_template("agente.html")
