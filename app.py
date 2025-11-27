@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        # 1. Recibir datos
        datos = request.get_json(force=True)
        email = datos.get('email')
        password = datos.get('password')
        
        # 2. Consultar a la BD
        usuario = validar_login(email, password)
        
        if usuario:
            # 3. Guardar sesión (Cookies)
            session.clear()
            session.permanent = True
            session["user_id"] = usuario['email']
            session["rol"] = usuario['nombre_rol'] # Guardamos el rol en sesión también
            
            # 4. RESPONDER A APP INVENTOR CON EL ROL
            return jsonify({
                "exito": True, 
                "mensaje": "Bienvenido",
                "user_id": usuario['email'],
                "saldo": float(usuario['saldo_actual']),
                "rol": usuario['nombre_rol']  # <--- ESTO ES LO IMPORTANTE
            })
        else:
            return jsonify({"exito": False, "mensaje": "Credenciales incorrectas"}), 401
            
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400
