from flask import Flask, session, jsonify, send_from_directory, request
import random
import os
# Importamos la lógica de base de datos
from db_config import registrar_usuario_nuevo, validar_login, get_user_balance, update_user_balance

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# --- CONFIGURACIÓN DE SESIONES PARA APP INVENTOR ---
# Esto es vital para que las cookies viajen bien entre Android y Render
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 # 1 hora

# ==========================================
# 1. API DE REGISTRO (Con Depuración)
# ==========================================
@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    print("--- INICIO DE REGISTRO ---")
    try:
        # Intentamos leer el JSON. force=True ayuda si el header falla.
        # silent=True evita que explote si está vacío.
        datos = request.get_json(force=True, silent=True)
        
        if not datos:
            # Si no hay JSON, imprimimos qué llegó para depurar
            cuerpo = request.get_data(as_text=True)
            print(f"❌ ERROR: JSON vacío o inválido. Recibido: {cuerpo}")
            return jsonify({"exito": False, "mensaje": "JSON inválido"}), 400
            
        print(f"📥 Datos recibidos: {datos}")
        
        # Validar campos obligatorios
        campos = ['nombre', 'apellido', 'curp', 'email', 'password']
        faltantes = [campo for campo in campos if campo not in datos]
        
        if faltantes:
            return jsonify({"exito": False, "mensaje": f"Faltan datos: {faltantes}"}), 400

        # Llamar a db_config.py para guardar en Neon
        resultado = registrar_usuario_nuevo(datos)
        
        # Devolver respuesta a App Inventor
        codigo = 200 if resultado['exito'] else 400
        return jsonify(resultado), codigo

    except Exception as e:
        print(f"🔥 ERROR INTERNO: {e}")
        return jsonify({"exito": False, "mensaje": f"Error del servidor: {str(e)}"}), 500

# ==========================================
# 2. API DE LOGIN
# ==========================================
@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        datos = request.get_json(force=True)
        email = datos.get('email')
        password = datos.get('password')
        
        usuario = validar_login(email, password)
        
        if usuario:
            # Crear sesión de Flask
            session.clear()
            session.permanent = True
            session["user_id"] = usuario['email']
            
            # Inicializar juego si no existe
            get_game()
            
            return jsonify({
                "exito": True, 
                "mensaje": "Login correcto",
                "user_id": usuario['email'],
                "saldo": float(usuario['saldo_actual'])
            })
        else:
            return jsonify({"exito": False, "mensaje": "Credenciales incorrectas"}), 401
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400

# ==========================================
# 3. LÓGICA DEL JUEGO BLACKJACK
# ==========================================

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

def new_deck():
    deck = [(r, s) for s in SUITS for r in RANKS] * 4
    random.shuffle(deck)
    return deck

def card_value(rank):
    if rank == "A": return 11
    if rank in ("J","Q","K"): return 10
    return int(rank)

def hand_value(hand):
    total = sum(card_value(r) for r, s in hand)
    aces = sum(1 for r, s in hand if r == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def get_game():
    g = session.get("game")
    user_id = session.get("user_id")
    
    if not g:
        saldo = 500
        if user_id: saldo = get_user_balance(user_id)
        
        g = {
            "deck": new_deck(),
            "player": [], "dealer": [],
            "bet": 0, "bank": saldo,
            "phase": "BETTING", "message": "HAZ TU APUESTA"
        }
    
    # Recarga automática de bancarrota
    if g["bank"] < 10 and g["bet"] == 0:
        g["bank"] = 500
        g["message"] = "¡BANCARROTA! TE REGALAMOS $500"
        if user_id: update_user_balance(user_id, 500)
            
    return g

def save_game(g):
    session["game"] = g
    user_id = session.get("user_id")
    if user_id: update_user_balance(user_id, g["bank"])

# --- RUTAS DE JUEGO ---
@app.route("/")
def index():
    # Compatibilidad con WebViewer (/?user_id=...)
    uid = request.args.get('user_id')
    if uid: session["user_id"] = uid
    return send_from_directory("static", "index.html")

@app.route("/api/state")
def api_state():
    g = get_game()
    return jsonify(serialize_state(g))

def serialize_state(g):
    return {
        "player": g["player"], "dealer": g["dealer"],
        "player_value": hand_value(g["player"]),
        "dealer_value": hand_value(g["dealer"]),
        "bet": g["bet"], "bank": g["bank"],
        "phase": g["phase"], "message": g["message"],
        "dealer_hidden": g["phase"] == "PLAYER" and len(g["dealer"]) >= 2
    }

@app.route("/api/bet", methods=["POST"])
def api_bet():
    g = get_game()
    if g["phase"] != "BETTING": return jsonify(serialize_state(g))
    data = request.get_json(force=True)
    amount = int(data.get("amount", 0))
    if 0 < amount <= g["bank"]:
        g["bet"] += amount
        g["bank"] -= amount
        g["message"] = f"APUESTA: ${g['bet']}"
    save_game(g)
    return jsonify(serialize_state(g))

@app.route("/api/deal", methods=["POST"])
def api_deal():
    g = get_game()
    if g["bet"] == 0: return jsonify(serialize_state(g))
    
    g["player"] = [draw(g), draw(g)]
    g["dealer"] = [draw(g), draw(g)]
    g["phase"] = "PLAYER"
    
    if hand_value(g["player"]) == 21: # Blackjack natural
        win = g["bet"] * 2.5 if hand_value(g["dealer"]) != 21 else g["bet"]
        g["bank"] += win
        g["message"] = "¡BLACKJACK!"
        g["phase"] = "END"
        g["bet"] = 0
        
    save_game(g)
    return jsonify(serialize_state(g))

@app.route("/api/hit", methods=["POST"])
def api_hit():
    g = get_game()
    if g["phase"] == "PLAYER":
        g["player"].append(draw(g))
        if hand_value(g["player"]) > 21:
            g["message"] = "TE PASASTE"
            g["phase"] = "END"
            g["bet"] = 0
    save_game(g)
    return jsonify(serialize_state(g))

@app.route("/api/stand", methods=["POST"])
def api_stand():
    g = get_game()
    if g["phase"] == "PLAYER":
        while hand_value(g["dealer"]) < 17:
            g["dealer"].append(draw(g))
        
        p = hand_value(g["player"])
        d = hand_value(g["dealer"])
        
        if d > 21 or p > d:
            g["bank"] += g["bet"] * 2
            g["message"] = "¡GANASTE!"
        elif p < d:
            g["message"] = "LA CASA GANA"
        else:
            g["bank"] += g["bet"]
            g["message"] = "EMPATE"
            
        g["phase"] = "END"
        g["bet"] = 0
    save_game(g)
    return jsonify(serialize_state(g))

@app.route("/api/new_round", methods=["POST"])
def api_new_round():
    g = get_game()
    g["phase"] = "BETTING"
    g["player"] = []
    g["dealer"] = []
    g["message"] = "HAZ TU APUESTA"
    save_game(g)
    return jsonify(serialize_state(g))

def draw(g):
    if not g["deck"]: g["deck"] = new_deck()
    return g["deck"].pop()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
