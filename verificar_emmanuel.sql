-- SQL para verificar el usuario Emmanuel (Agente de Soporte)
-- Ejecutar en consola de Neon

-- 1. Verificar datos completos del usuario Emmanuel
SELECT 
    u.id_usuario,
    u.nombre,
    u.apellido,
    u.email,
    u.activo,
    r.id_rol,
    r.nombre as nombre_rol
FROM Usuario u
JOIN Rol r ON u.id_rol = r.id_rol
WHERE u.id_usuario = 3;

-- 2. Verificar que el rol sea exactamente "Agente de Soporte"
SELECT 
    id_rol, 
    nombre,
    LENGTH(nombre) as longitud_nombre,
    nombre = 'Agente de Soporte' as es_exacto
FROM Rol 
WHERE id_rol = 4;

-- 3. Si necesitas actualizar el email del usuario Emmanuel:
-- UPDATE Usuario SET email = 'emmanuel@casino.com' WHERE id_usuario = 3;

-- 4. Si necesitas resetear la contraseña (usa el hash de Argon2):
-- Primero genera el hash con Python:
-- from passlib.context import CryptContext
-- pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
-- print(pwd_context.hash("tu_nueva_password"))
-- Luego ejecuta:
-- UPDATE Usuario SET password_hash = 'TU_HASH_AQUI' WHERE id_usuario = 3;
