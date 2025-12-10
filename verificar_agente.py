"""
Script para verificar que existe un usuario con rol 'Agente de Soporte'
y crear uno si no existe.
"""
from db_config import get_db_connection, pwd_context

def verificar_y_crear_agente():
    conn = get_db_connection()
    if not conn:
        print("❌ No se pudo conectar a la base de datos")
        return
    
    try:
        cursor = conn.cursor()
        
        # 1. Verificar que existe el rol 'Agente de Soporte'
        print("\n🔍 Verificando rol 'Agente de Soporte'...")
        cursor.execute("SELECT id_rol, nombre FROM Rol WHERE nombre = 'Agente de Soporte'")
        rol = cursor.fetchone()
        
        if not rol:
            print("❌ El rol 'Agente de Soporte' NO existe en la base de datos")
            print("   Creando rol...")
            cursor.execute("INSERT INTO Rol (nombre) VALUES ('Agente de Soporte') RETURNING id_rol")
            id_rol = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ Rol creado con ID: {id_rol}")
        else:
            id_rol = rol[0]
            print(f"✅ Rol encontrado - ID: {id_rol}, Nombre: '{rol[1]}'")
        
        # 2. Verificar si existe un usuario con ese rol
        print("\n🔍 Buscando usuarios con rol 'Agente de Soporte'...")
        cursor.execute("""
            SELECT u.id_usuario, u.email, u.nombre, u.apellido, u.activo
            FROM Usuario u
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE r.nombre = 'Agente de Soporte'
        """)
        usuarios = cursor.fetchall()
        
        if not usuarios:
            print("❌ No hay usuarios con rol 'Agente de Soporte'")
            print("\n📝 Creando usuario de prueba...")
            
            # Crear usuario agente
            email = "agente@casino.com"
            password = "agente123"
            nombre = "Agente"
            apellido = "Soporte"
            
            password_hash = pwd_context.hash(password)
            
            cursor.execute("""
                INSERT INTO Usuario (id_rol, nombre, apellido, curp, email, password_hash, fecha_registro, activo)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), true)
                RETURNING id_usuario
            """, (id_rol, nombre, apellido, 'AGNT000000XXXXXX00', email, password_hash))
            
            id_usuario = cursor.fetchone()[0]
            
            # Crear saldo inicial
            cursor.execute("INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion) VALUES (%s, 0.00, NOW())", (id_usuario,))
            
            conn.commit()
            
            print(f"\n✅ Usuario agente creado exitosamente!")
            print(f"   📧 Email: {email}")
            print(f"   🔑 Password: {password}")
            print(f"   👤 Nombre: {nombre} {apellido}")
            print(f"   🆔 ID: {id_usuario}")
        else:
            print(f"✅ Encontrados {len(usuarios)} usuario(s) con rol 'Agente de Soporte':")
            for usuario in usuarios:
                estado = "✅ Activo" if usuario[4] else "❌ Inactivo"
                print(f"\n   🆔 ID: {usuario[0]}")
                print(f"   📧 Email: {usuario[1]}")
                print(f"   👤 Nombre: {usuario[2]} {usuario[3]}")
                print(f"   📊 Estado: {estado}")
        
        conn.close()
        
        print("\n" + "="*60)
        print("INSTRUCCIONES PARA PROBAR:")
        print("="*60)
        print("1. Inicia sesión en /login con las credenciales del agente")
        print("2. Revisa los logs del servidor para ver el debug")
        print("3. Deberías ver mensajes como:")
        print("   ✅ LOGIN EXITOSO - Email: agente@casino.com")
        print("   Rol asignado en sesión: 'Agente de Soporte'")
        print("4. Al acceder a /agente deberías ver:")
        print("   ✅ ACCESO PERMITIDO: Usuario es Agente de Soporte")
        print("="*60)
        
    except Exception as e:
        print(f"\n🔥 ERROR: {e}")
        if conn:
            conn.rollback()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("="*60)
    print("VERIFICACIÓN DE USUARIO AGENTE DE SOPORTE")
    print("="*60)
    verificar_y_crear_agente()
