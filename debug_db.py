import os
import psycopg2
from db_config import get_db_connection

def check_db():
    print("Connecting to DB...")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect.")
        return

    cursor = conn.cursor()
    
    # List all tables
    print("\n--- TABLES ---")
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()
    for table_name in tables:
        t = table_name[0]
        # Count rows
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            count = cursor.fetchone()[0]
            print(f"{t}: {count} rows")
        except Exception as e:
            print(f"{t}: Error counting rows - {e}")
            conn.rollback()

    conn.close()

if __name__ == "__main__":
    check_db()
