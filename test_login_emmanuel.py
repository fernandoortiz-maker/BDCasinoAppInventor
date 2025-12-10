"""
Script para verificar qué está pasando con el login del agente Emmanuel
"""
import os
from db_config import validar_login

print("="*60)
print("PRUEBA DE LOGIN AGENTE EMMANUEL")
print("="*60)

# Probar login con el email del usuario Emmanuel
# Necesitarás ingresar la contraseña correcta
email = input("\nIngresa el email de Emmanuel: ").strip()
password = input("Ingresa la contraseña: ").strip()

print(f"\n🔍 Intentando login con:")
print(f"   Email: {email}")
print(f"   Password: {'*' * len(password)}")

try:
    usuario = validar_login(email, password)
    
    if usuario:
        print(f"\n✅ LOGIN EXITOSO")
        print(f"\nDatos retornados por validar_login:")
        print(f"   id_usuario: {usuario.get('id_usuario')}")
        print(f"   nombre: {usuario.get('nombre')}")
        print(f"   apellido: {usuario.get('apellido')}")
        print(f"   email: {usuario.get('email')}")
        print(f"   nombre_rol: '{usuario.get('nombre_rol')}'")
        print(f"   longitud del rol: {len(usuario.get('nombre_rol', ''))}")
        
        # Verificar si el rol es exactamente el esperado
        rol = usuario.get('nombre_rol')
        if rol == "Agente de Soporte":
            print(f"\n✅ El rol es EXACTAMENTE 'Agente de Soporte'")
            print(f"   El acceso debería funcionar")
        else:
            print(f"\n❌ ERROR: El rol es '{rol}' != 'Agente de Soporte'")
            print(f"   Caracteres en el rol: {[c for c in rol]}")
            print(f"   Código ASCII: {[ord(c) for c in rol]}")
    else:
        print(f"\n❌ LOGIN FALLIDO")
        print(f"   Email o contraseña incorrectos")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
