-- ===================================================================
-- SCRIPT DE DATOS DE PRUEBA PARA PANEL DE AGENTE DE SOPORTE
-- ===================================================================

-- 1. CREAR USUARIO AGENTE DE SOPORTE
-- Nota: La contraseña es "agente123" (debes hashearla con Argon2 en producción)
-- Este es un hash de ejemplo, deberás usar el hash real generado por tu aplicación
INSERT INTO Usuario (id_rol, nombre, apellido, curp, email, password_hash, activo)
VALUES (
    (SELECT id_rol FROM Rol WHERE nombre = 'Agente de Soporte'),
    'Juan', 
    'Pérez', 
    'PEJX850101HDFRXN01', 
    'agente@casino.com',
    -- Contraseña: agente123 (debes reemplazar con el hash real)
    '$argon2id$v=19$m=65536,t=3,p=4$somesalt$hash',
    true
)
ON CONFLICT (email) DO NOTHING;

-- Crear saldo para el agente (opcional, pero necesario por la estructura)
INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion)
VALUES (
    (SELECT id_usuario FROM Usuario WHERE email = 'agente@casino.com'),
    0.00,
    NOW()
)
ON CONFLICT (id_usuario) DO NOTHING;

-- 2. CREAR USUARIOS JUGADORES DE PRUEBA
INSERT INTO Usuario (id_rol, nombre, apellido, curp, email, password_hash, activo)
VALUES 
    (
        (SELECT id_rol FROM Rol WHERE nombre = 'Jugador'),
        'María', 'García', 'GARM900215MDFRXR02', 'maria@test.com',
        '$argon2id$v=19$m=65536,t=3,p=4$somesalt$hash', true
    ),
    (
        (SELECT id_rol FROM Rol WHERE nombre = 'Jugador'),
        'Carlos', 'López', 'LOPC880310HDFRXR03', 'carlos@test.com',
        '$argon2id$v=19$m=65536,t=3,p=4$somesalt$hash', true
    ),
    (
        (SELECT id_rol FROM Rol WHERE nombre = 'Jugador'),
        'Ana', 'Martínez', 'MARA920520MDFRXN04', 'ana@test.com',
        '$argon2id$v=19$m=65536,t=3,p=4$somesalt$hash', true
    )
ON CONFLICT (email) DO NOTHING;

-- Crear saldos para los jugadores
INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion)
SELECT id_usuario, 500.00, NOW()
FROM Usuario
WHERE email IN ('maria@test.com', 'carlos@test.com', 'ana@test.com')
ON CONFLICT (id_usuario) DO NOTHING;

-- 3. CREAR TICKETS DE PRUEBA
INSERT INTO Soporte (id_jugador, asunto, mensaje, estado, fecha_creacion)
VALUES
    -- Ticket sin asignar
    (
        (SELECT id_usuario FROM Usuario WHERE email = 'maria@test.com'),
        'No puedo depositar fondos',
        'He intentado depositar $100 pero me aparece un error. ¿Pueden ayudarme?',
        'Abierto',
        NOW() - INTERVAL '2 hours'
    ),
    -- Ticket sin asignar
    (
        (SELECT id_usuario FROM Usuario WHERE email = 'carlos@test.com'),
        'Problema con retiro',
        'Solicité un retiro hace 3 días y aún no lo he recibido.',
        'Abierto',
        NOW() - INTERVAL '1 day'
    ),
    -- Ticket ya asignado al agente
    (
        (SELECT id_usuario FROM Usuario WHERE email = 'ana@test.com'),
        'Cuenta bloqueada',
        'Mi cuenta fue bloqueada sin razón aparente. Necesito ayuda urgente.',
        'En Proceso',
        NOW() - INTERVAL '3 hours'
    );

-- Asignar el tercer ticket al agente
UPDATE Soporte 
SET id_agente = (SELECT id_usuario FROM Usuario WHERE email = 'agente@casino.com')
WHERE asunto = 'Cuenta bloqueada';

-- 4. CREAR CHATS DE PRUEBA
INSERT INTO Chat (id_jugador, estado, fecha_inicio)
VALUES
    -- Chat en espera
    (
        (SELECT id_usuario FROM Usuario WHERE email = 'maria@test.com'),
        'Esperando',
        NOW() - INTERVAL '10 minutes'
    ),
    -- Chat en espera
    (
        (SELECT id_usuario FROM Usuario WHERE email = 'carlos@test.com'),
        'Esperando',
        NOW() - INTERVAL '5 minutes'
    );

-- Crear un chat activo asignado al agente
INSERT INTO Chat (id_jugador, id_agente, estado, fecha_inicio, fecha_asignacion)
VALUES
    (
        (SELECT id_usuario FROM Usuario WHERE email = 'ana@test.com'),
        (SELECT id_usuario FROM Usuario WHERE email = 'agente@casino.com'),
        'Activo',
        NOW() - INTERVAL '20 minutes',
        NOW() - INTERVAL '18 minutes'
    );

-- 5. CREAR MENSAJES EN EL CHAT ACTIVO
-- Obtener el id del chat activo
DO $$
DECLARE
    chat_id INTEGER;
    jugador_id INTEGER;
    agente_id INTEGER;
BEGIN
    SELECT id_chat INTO chat_id
    FROM Chat
    WHERE estado = 'Activo'
    LIMIT 1;

    SELECT id_usuario INTO jugador_id
    FROM Usuario
    WHERE email = 'ana@test.com';

    SELECT id_usuario INTO agente_id
    FROM Usuario
    WHERE email = 'agente@casino.com';

    -- Mensaje del jugador
    INSERT INTO Mensaje_Chat (id_chat, id_usuario, mensaje, es_agente, fecha_mensaje, leido)
    VALUES
        (chat_id, jugador_id, 'Hola, necesito ayuda con mi cuenta', false, NOW() - INTERVAL '18 minutes', true),
        (chat_id, agente_id, 'Hola Ana, con gusto te ayudo. ¿Cuál es el problema?', true, NOW() - INTERVAL '17 minutes', true),
        (chat_id, jugador_id, 'Mi cuenta fue bloqueada y no sé por qué', false, NOW() - INTERVAL '16 minutes', true),
        (chat_id, agente_id, 'Déjame revisar tu cuenta. Un momento por favor.', true, NOW() - INTERVAL '15 minutes', true),
        (chat_id, agente_id, 'Ya revisé y veo que hubo actividad sospechosa. Voy a desbloquearla.', true, NOW() - INTERVAL '10 minutes', false);
END $$;

-- 6. CREAR UN TICKET CERRADO (para estadísticas)
INSERT INTO Soporte (id_jugador, id_agente, asunto, mensaje, estado, fecha_creacion, fecha_cierre)
VALUES
    (
        (SELECT id_usuario FROM Usuario WHERE email = 'maria@test.com'),
        (SELECT id_usuario FROM Usuario WHERE email = 'agente@casino.com'),
        'Consulta sobre bonos',
        '¿Cómo puedo obtener el bono de bienvenida?',
        'Cerrado',
        CURRENT_DATE - INTERVAL '1 hour',
        CURRENT_DATE
    );

-- ===================================================================
-- VERIFICACIÓN DE DATOS
-- ===================================================================

-- Ver todos los usuarios creados
SELECT u.id_usuario, u.nombre, u.apellido, u.email, r.nombre as rol
FROM Usuario u
JOIN Rol r ON u.id_rol = r.id_rol
WHERE u.email IN ('agente@casino.com', 'maria@test.com', 'carlos@test.com', 'ana@test.com');

-- Ver todos los tickets
SELECT s.id_ticket, s.asunto, s.estado, 
       u.nombre || ' ' || u.apellido as jugador,
       a.nombre || ' ' || a.apellido as agente
FROM Soporte s
JOIN Usuario u ON s.id_jugador = u.id_usuario
LEFT JOIN Usuario a ON s.id_agente = a.id_usuario;

-- Ver todos los chats
SELECT c.id_chat, c.estado, c.fecha_inicio,
       u.nombre || ' ' || u.apellido as jugador,
       a.nombre || ' ' || a.apellido as agente
FROM Chat c
JOIN Usuario u ON c.id_jugador = u.id_usuario
LEFT JOIN Usuario a ON c.id_agente = a.id_usuario;

-- ===================================================================
-- NOTAS IMPORTANTES
-- ===================================================================
-- 
-- 1. CONTRASEÑAS: Los hashes de contraseña en este script son ejemplos.
--    Para crear usuarios reales, debes:
--    a) Registrar usuarios a través de la API /api/registrar
--    b) O generar hashes Argon2 reales usando Python:
--       from passlib.context import CryptContext
--       pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
--       hash = pwd_context.hash("agente123")
--
-- 2. CREDENCIALES DE PRUEBA:
--    Email: agente@casino.com
--    Contraseña: agente123 (después de hashear correctamente)
--
-- 3. Para probar el panel:
--    - Inicia sesión con el usuario agente
--    - Verás 2 tickets pendientes, 1 ticket asignado
--    - Verás 2 chats en espera, 1 chat activo
--    - Podrás asignar tickets, responder, cerrar, etc.
--
