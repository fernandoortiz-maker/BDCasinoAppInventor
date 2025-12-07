/**
 * SCRIPT DE SEGURIDAD - Royal Crumbs Admin Panel
 * Bloquea: zoom, selección, copiar/pegar, clic derecho, modo desarrollador
 */

// Bloquear teclas de desarrollador
document.addEventListener('keydown', function (e) {
    // F12
    if (e.key === 'F12') { e.preventDefault(); return false; }
    // Ctrl+Shift+I (Inspector)
    if (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'i')) { e.preventDefault(); return false; }
    // Ctrl+Shift+J (Consola)
    if (e.ctrlKey && e.shiftKey && (e.key === 'J' || e.key === 'j')) { e.preventDefault(); return false; }
    // Ctrl+Shift+C (Selector de elementos)
    if (e.ctrlKey && e.shiftKey && (e.key === 'C' || e.key === 'c')) { e.preventDefault(); return false; }
    // Ctrl+U (Ver código fuente)
    if (e.ctrlKey && (e.key === 'u' || e.key === 'U')) { e.preventDefault(); return false; }
    // Ctrl+S (Guardar)
    if (e.ctrlKey && (e.key === 's' || e.key === 'S')) { e.preventDefault(); return false; }
    // Ctrl+C, Ctrl+V, Ctrl+X (Copiar, Pegar, Cortar)
    if (e.ctrlKey && (e.key === 'c' || e.key === 'C' || e.key === 'v' || e.key === 'V' || e.key === 'x' || e.key === 'X')) {
        e.preventDefault(); return false;
    }
    // Ctrl+A (Seleccionar todo)
    if (e.ctrlKey && (e.key === 'a' || e.key === 'A')) { e.preventDefault(); return false; }
});

// Bloquear clic derecho
document.addEventListener('contextmenu', function (e) {
    e.preventDefault();
    return false;
});

// Bloquear arrastrar
document.addEventListener('dragstart', function (e) {
    e.preventDefault();
    return false;
});

// Bloquear selección
document.addEventListener('selectstart', function (e) {
    e.preventDefault();
    return false;
});

// Bloquear copiar
document.addEventListener('copy', function (e) {
    e.preventDefault();
    return false;
});

// Bloquear pegar
document.addEventListener('paste', function (e) {
    e.preventDefault();
    return false;
});

// Bloquear cortar
document.addEventListener('cut', function (e) {
    e.preventDefault();
    return false;
});

// Detectar si DevTools está abierto (método básico)
(function () {
    const threshold = 160;
    const checkDevTools = function () {
        if (window.outerWidth - window.innerWidth > threshold ||
            window.outerHeight - window.innerHeight > threshold) {
            // DevTools posiblemente abierto
            document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;background:#202020;color:#ab925c;font-size:24px;text-align:center;padding:20px;">⚠️ Acceso no autorizado detectado</div>';
        }
    };

    // Revisar periódicamente (desactivar en desarrollo si es necesario)
    // setInterval(checkDevTools, 1000);
})();

console.log('%c⚠️ ALTO', 'color: red; font-size: 50px; font-weight: bold;');
console.log('%cEsta función del navegador está destinada a desarrolladores. Si alguien le dijo que copiara y pegara algo aquí, es una estafa.', 'color: white; font-size: 18px;');
