"""
Script de debugging para verificar el flujo completo del dashboard
"""

# Primero verificar que el endpoint user_info existe
print("1. Verificando si existe /api/user_info...")
print("   Buscar en app.py alrededor de línea 106-140")

# Segundo verificar que localStorage se está guardando
print("\n2. En la consola del navegador, ejecuta:")
print("   localStorage.getItem('userId')")
print("   localStorage.getItem('userEmail')")
print("   Si devuelve null, el problema es que /api/user_info no existe")

# Tercero verificar que el dashboard esté llamando al API correcto
print("\n3. En la consola del navegador (en /agente/dashboard):")
print("   Abre Network tab en DevTools")
print("   Busca la llamada a /api/agente/dashboard/X")
print("   Ve el Response - debería tener los números")

# Cuarto verificar los logs del servidor
print("\n4. En los logs de Render, busca:")
print("   - 'Error dashboard agente' si hay error")
print("   - El query SELECT COUNT(*) debería ejecutarse")

print("\n" + "="*60)
print("SOLUCIÓN RÁPIDA:")
print("="*60)
print("Si /api/user_info no existe, necesito agregarlo.")
print("Voy a verificar el código ahora.")
