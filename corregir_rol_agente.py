#!/usr/bin/env python3
"""
Script para verificar y corregir el rol de Agente de Soporte
"""
import os
import sys
from db_config import get_db_connection

def verificar_y_corregir_rol():
    print("="*60)
    print("VERIFICACIÓN Y CORRECCIÓN DE ROL AGENTE DE SOPORTE")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ No se pudo conectar a la base de datos")
        return False
    
    cursor = conn.cursor()
    
    # 1. Verificar todos los roles existentes
    print("\n📋 1. Roles existentes en la base de datos:")
    cursor.execute("SELECT id_rol, nombre FROM Rol ORDER BY id_rol")
    roles = cursor.fetchall()
    
    for rol in roles:
        print(f"   ID {rol[0]}: '{rol[1]}'")
    
    # 2. Buscar rol de agente (variaciones)
    print("\n🔍 2. Buscando rol de Agente de Soporte...")
    cursor.execute("""
        SELECT id_rol, nombre FROM Rol 
        WHERE LOWER(nombre) LIKE '%agente%' 
           OR LOWER(nombre) LIKE '%soporte%'
    """)
    roles_agente = cursor.fetchall()
    
    if not roles_agente:
        print("   ❌ No se encontró ningún rol de agente")
        print("\n   Creando rol 'Agente de Soporte'...")
        cursor.execute("INSERT INTO Rol (nombre) VALUES ('Agente de Soporte') RETURNING id_rol")
        id_rol_correcto = cursor.fetchone()[0]
        conn.commit()
        print(f"   ✅ Rol creado con ID {id_rol_correcto}")
    else:
        print(f"   Encontrados {len(roles_agente)} rol(es):")
        for rol in roles_agente:
            print(f"      ID {rol[0]}: '{rol[1]}'")
        
        # Verificar si el nombre es EXACTAMENTE "Agente de Soporte"
        rol_correcto = None
        for rol in roles_agente:
            if rol[1] == "Agente de Soporte":
                rol_correcto = rol
                print(f"\n   ✅ Rol correcto encontrado: ID {rol[0]}")
                break
        
        if not rol_correcto:
            print(f"\n   ⚠️  Ningún rol tiene el nombre EXACTO 'Agente de Soporte'")
            print(f"   El código busca exactamente: 'Agente de Soporte' (con mayúsculas)")
            
            # Corregir el nombre del primer rol encontrado
            rol_a_corregir = roles_agente[0]
            print(f"\n   🔧 Corrigiendo rol ID {rol_a_corregir[0]}: '{rol_a_corregir[1]}' → 'Agente de Soporte'")
            
            cursor.execute(
                "UPDATE Rol SET nombre = 'Agente de Soporte' WHERE id_rol = %s",
                (rol_a_corregir[0],)
            )
            conn.commit()
            print(f"   ✅ Rol corregido exitosamente")
            id_rol_correcto = rol_a_corregir[0]
        else:
            id_rol_correcto = rol_correcto[0]
    
    # 3. Verificar usuarios con ese rol
    print(f"\n👥 3. Usuarios con rol 'Agente de Soporte' (ID {id_rol_correcto}):")
    cursor.execute("""
        SELECT u.id_usuario, u.nombre, u.apellido, u.email, r.nombre as rol
        FROM Usuario u
        JOIN Rol r ON u.id_rol = r.id_rol
        WHERE u.id_rol = %s
    """, (id_rol_correcto,))
    
    usuarios = cursor.fetchall()
    
    if usuarios:
        print(f"   ✅ Encontrados {len(usuarios)} usuario(s):")
        for usuario in usuarios:
            print(f"\n   Usuario ID: {usuario[0]}")
            print(f"   Nombre: {usuario[1]} {usuario[2]}")
            print(f"   Email: {usuario[3]}")
            print(f"   Rol: '{usuario[4]}'")
    else:
        print("   ⚠️  No hay usuarios con este rol")
        print("\n   Puedes crear uno con el script setup_dev_users_secure.py")
    
    # 4. Verificar que el nombre del rol es EXACTAMENTE correcto
    print(f"\n✅ 4. Verificación final:")
    cursor.execute("SELECT nombre FROM Rol WHERE id_rol = %s", (id_rol_correcto,))
    nombre_final = cursor.fetchone()[0]
    
    if nombre_final == "Agente de Soporte":
        print(f"   ✅ Rol configurado correctamente: '{nombre_final}'")
        print(f"   ✅ El login debería funcionar ahora")
    else:
        print(f"   ❌ ERROR: Rol sigue siendo '{nombre_final}'")
        print(f"   ❌ Debe ser exactamente: 'Agente de Soporte'")
    
    conn.close()
    
    print("\n" + "="*60)
    print("INSTRUCCIONES:")
    print("="*60)
    print("1. El rol ahora debe estar configurado correctamente")
    print("2. Intenta iniciar sesión con tu usuario agente")
    print("3. Si sigue fallando, revisa los logs del servidor")
    print("   Los logs mostrarán exactamente qué rol tiene en sesión")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        verificar_y_corregir_rol()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
