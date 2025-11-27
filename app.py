from flask import Flask, session, jsonify, send_from_directory, request
import random
import os
# Importamos nuestras funciones de base de datos
from db_config import registrar_usuario_nuevo, validar_login, get_user_balance, update_user_balance

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "llave-secreta-desarrollo")

# --- CONFIGURACIÓN DE COOKIES (CRÍTICO PARA APP INVENTOR) ---
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 # 1 hora

# ==========================================
# RUTAS DE API PARA APP INVENTOR
# ==========================================

@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    # Depuración: Ver qué llega
    print("--- INTENTO DE REGISTRO ---")
    try:
        # forzamos lectura de JSON aunque el header falle
        datos = request.get_json(force=True, silent=True)
        if not datos:
            # Si falla, imprimimos el texto crudo para ver el error
            print(f"Raw data: {request.get_data(as_text=True)}")
            return jsonify({"exito": False, "mensaje": "JSON inválido o vacío"}), 400
            
        print(f"Datos recibidos: {datos}")
        
        # Validar campos
        requeridos = ['nombre', 'apellido', 'curp', 'email', 'password']
        if not all(k in datos for k in requeridos):
            return jsonify({"exito": False, "mensaje": "Faltan datos obligatorios"}), 400

        # Guardar en Neon
        resultado = registrar_usuario_nuevo(datos)
        
        if resultado['exito']:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400 # Error lógico (ej. correo duplicado)

    except Exception as e:
        print(f"🔥 EXCEPCIÓN: {e}")
        return jsonify({"exito": False, "mensaje": f"Error interno: {str(e)}"}), 500

@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        datos = request.get_json(force=True)
        email = datos.get('email')
        password = datos.get('password')
        
        # Validar en Base de Datos
        usuario = validar_login(email, password)
        
        if usuario:
            # Crear sesión
            session.clear()
            session.permanent = True
            session["user_id"] = usuario['email'] # Usamos el email como ID de sesión
            session["nombre"] = usuario['nombre']
            
            # Inicializar juego si no existe
            if "game" not in session:
                get_game() 
            
            return jsonify({
                "exito": True,
                "mensaje": "Login correcto",
                "saldo": float(usuario['saldo_actual']),
                "user_id": usuario['email']
            })
        else:
            return jsonify({"exito": False, "mensaje": "Credenciales incorrectas"}), 401
            
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400

# ==========================================
# LÓGICA DEL JUEGO (BLACKJACK)
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
    user_email = session.get("user_id")
    
    # Si no hay juego en memoria, creamos uno nuevo
    if not g:
        saldo_db = 500
        if user_email:
            saldo_db = get_user_balance(user_email)

        g = {
            "deck": new_deck(),
            "player": [], "dealer": [],
            "bet": 0,
            "bank": saldo_db,
            "phase": "BETTING",
            "message": "HAZ TU APUESTA"
        }
    
    # Recarga automática de bancarrota
    if g["bank"] < 10 and g["bet"] == 0:
        g["bank"] = 500
        g["message"] = "¡BANCARROTA! TE REGALAMOS $500"
        if user_email: update_user_balance(user_email, 500)
            
    return g

def save_game(g):
    session["game"] = g
    user_email = session.get("user_id")
    if user_email:
        update_user_balance(user_email, g["bank"])

# --- RUTAS DEL JUEGO ---

@app.route("/")
def index():
    # Soporte para ?user_id=email (Webview legado)
    user_id = request.args.get('user_id')
    if user_id:
        session["user_id"] = user_id
    return send_from_directory("static", "index.html")

@app.route("/api/state", methods=["GET"])
def api_state():
    g = get_game()
    save_game(g)
    return jsonify(serialize_state(g))

def serialize_state(g):
    # Convierte el juego a JSON para el frontend
    return {
        "player": g["player"],
        "dealer": g["dealer"],
        "player_value": hand_value(g["player"]),
        "dealer_value": hand_value(g["dealer"]),
        "bet": g["bet"],
        "bank": g["bank"],
        "phase": g["phase"],
        "message": g["message"],
        "dealer_hidden": g["phase"] == "PLAYER" and len(g["dealer"]) >= 2
    }

@app.route("/api/bet", methods=["POST"])
def api_bet():
    g = get_game()
    if g["phase"] != "BETTING": return jsonify(serialize_state(g))
    
    data = request.get_json(force=True)
    amount = int(data.get("amount", 0))
    
    if amount > 0 and amount <= g["bank"]:
        g["bet"] += amount
        g["bank"] -= amount # Descontamos del banco visual
        set_msg(g, f"APUESTA: ${g['bet']}")
    
    save_game(g)
    return jsonify(serialize_state(g))

@app.route("/api/deal", methods=["POST"])
def api_deal():
    g = get_game()
    if g["bet"] == 0: 
        set_msg(g, "¡DEBES APOSTAR ALGO!")
        return jsonify(serialize_state(g))
        
    g["player"] = [draw(g), draw(g)]
    g["dealer"] = [draw(g), draw(g)]
    g["phase"] = "PLAYER"
    
    # Check Blackjack instantáneo
    if hand_value(g["player"]) == 21:
        if hand_value(g["dealer"]) == 21:
            g["bank"] += g["bet"] # Empate
            set_msg(g, "EMPATE - AMBOS TIENEN BLACKJACK")
        else:
            win = g["bet"] + (g["bet"] * 1.5)
            g["bank"] += win
            set_msg(g, "¡BLACKJACK! GANASTE")
        g["phase"] = "END"
        g["bet"] = 0

    save_game(g)
    return jsonify(serialize_state(g))

@app.route("/api/hit", methods=["POST"])
def api_hit():
    g = get_game()
    g["player"].append(draw(g))
    if hand_value(g["player"]) > 21:
        set_msg(g, "TE PASASTE (BUST)")
        g["phase"] = "END"
        g["bet"] = 0
    save_game(g)
    return jsonify(serialize_state(g))

@app.route("/api/stand", methods=["POST"])
def api_stand():
    g = get_game()
    # Dealer juega
    while hand_value(g["dealer"]) < 17:
        g["dealer"].append(draw(g))
    
    p_val = hand_value(g["player"])
    d_val = hand_value(g["dealer"])
    
    if d_val > 21 or p_val > d_val:
        win = g["bet"] * 2
        g["bank"] += win
        set_msg(g, "¡GANASTE!")
    elif p_val < d_val:
        set_msg(g, "LA CASA GANA")
    else:
        g["bank"] += g["bet"]
        set_msg(g, "EMPATE (PUSH)")
        
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
    set_msg(g, "NUEVA RONDA - APUESTA")
    save_game(g)
    return jsonify(serialize_state(g))

# --- AYUDANTES ---
def draw(g):
    if not g["deck"]: g["deck"] = new_deck()
    return g["deck"].pop()

def set_msg(g, t): g["message"] = t

if __name__ == "__main__":
    # Render usa el puerto de la variable de entorno
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
