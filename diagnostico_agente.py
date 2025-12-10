# Script para diagnosticar el problema de acceso del agente
import os
import sys
sys.path.insert(0, r'd:\proyectos uni\Nueva carpeta\BDCasinoAppInventor')

print("="*60)
print("DIAGNÓSTICO DE ACCESO AGENTE DE SOPORTE")
print("="*60)

# 1. Verificar que el decorador existe
print("\n1. Verificando decorador agente_required...")
try:
    from app import agente_required
    print("   ✅ Decorador encontrado")
except ImportError as e:
    print(f"   ❌ ERROR: Decorador no encontrado - {e}")
    print("   ⚠️  ESTE ES EL PROBLEMA: El decorador no está definido")

# 2. Verificar base de datos
print("\n2. Verificando rol en base de datos...")
try:
    from db_config import get_db_connection
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_rol, nombre FROM Rol WHERE nombre LIKE '%Agente%' OR nombre LIKE '%Soporte%'")
        roles = cursor.fetchall()
        
        if roles:
            print(f"   ✅ Roles encontrados:")
            for rol in roles:
                print(f"      - ID: {rol[0]}, Nombre: '{rol[1]}'")
        else:
            print("   ❌ No se encontraron roles de agente")
        
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.apellido, u.email, r.nombre as rol
            FROM Usuario u
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE r.nombre LIKE '%Agente%' OR r.nombre LIKE '%Soporte%'
        """)
        usuarios = cursor.fetchall()
        
        if usuarios:
            print(f"\n   ✅ Usuarios con rol de agente:")
            for usuario in usuarios:
                print(f"      - ID: {usuario[0]}, Nombre: {usuario[1]} {usuario[2]}")
                print(f"        Email: {usuario[3]}, Rol: '{usuario[4]}'")
        else:
            print(f"\n   ❌ No hay usuarios con rol de agente")
        
        conn.close()
except Exception as e:
    print(f"   ❌ Error conectando a BD: {e}")

print("\n" + "="*60)
print("SOLUCIÓN:")
print("="*60)
print("El decorador @agente_required no está definido en app.py")
print("Esto causa que las rutas del agente fallen.")
print("\nSe necesita:")
print("1. Crear el decorador agente_required")
print("2. Verificar que el rol en sesión sea exactamente igual al de la BD")
print("="*60)
