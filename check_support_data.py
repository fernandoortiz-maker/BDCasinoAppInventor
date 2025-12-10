import os
import psycopg2
from db_config import get_db_connection
import datetime

def check_data():
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to DB")
        return

    cursor = conn.cursor()

    try:
        # 1. Check raw counts
        cursor.execute("SELECT COUNT(*) FROM Soporte")
        total_tickets = cursor.fetchone()[0]
        print(f"[INFO] Total Tickets in 'Soporte' table: {total_tickets}")

        cursor.execute("SELECT COUNT(*) FROM Usuario")
        total_users = cursor.fetchone()[0]
        print(f"[INFO] Total Users in 'Usuario' table: {total_users}")

        # 2. Check if tickets have valid users (Integrity check)
        cursor.execute("""
            SELECT s.id_ticket, s.id_jugador, u.nombre, u.email
            FROM Soporte s
            LEFT JOIN Usuario u ON s.id_jugador = u.id_usuario
        """)
        tickets = cursor.fetchall()
        
        print("\n[INFO] detailed Ticket Check:")
        valid_count = 0
        for t in tickets:
            id_ticket, id_jugador, nombre, email = t
            status = "[OK] Valid User" if nombre else "[ERROR] ORPHAN (User not found)"
            print(f"  - Ticket #{id_ticket} (Player ID: {id_jugador}) -> {status} - User: {email if email else 'N/A'}")
            if nombre: valid_count += 1
            
        print(f"\n[INFO] Valid tickets visible to API (INNER JOIN): {valid_count}")

        # 3. Simulate the exact API query
        print("\n[INFO] Simulating API Query...")
        query = """
            SELECT 
                s.id_ticket,
                s.asunto
            FROM Soporte s
            JOIN Usuario uj ON s.id_jugador = uj.id_usuario
            LEFT JOIN Usuario ua ON s.id_agente = ua.id_usuario
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"[OK] API would return {len(rows)} rows.")

    except Exception as e:
        print(f"[ERROR] Error: {e}")

    conn.close()

if __name__ == "__main__":
    from db_config import get_db_connection
    if not get_db_connection():
         print("[ERROR] Failed to connect to DB (Check DATABASE_URL)")
    else:
         check_data()
