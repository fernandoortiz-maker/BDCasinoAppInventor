/**
 * Sistema de Internacionalización (i18n) - Royal Crumbs
 * Maneja la persistencia del idioma y la traducción básica de la interfaz.
 */

const translations = {
    'es': {
        'login_title': 'Casino Login',
        'email_label': 'Email',
        'password_label': 'Contraseña',
        'login_btn': 'Iniciar Sesión',
        'welcome_msg': '¡Bienvenido! Redirigiendo...',
        'error_msg': 'Error al iniciar sesión',
        'connection_error': 'Error de conexión. Intenta nuevamente.',
        'admin_title': 'Administrador',
        'support_agent': 'Agente de Soporte',
        'auditor_panel': 'Panel Auditor'
    },
    'en': {
        'login_title': 'Casino Login',
        'email_label': 'Email',
        'password_label': 'Password',
        'login_btn': 'Log In',
        'welcome_msg': 'Welcome! Redirecting...',
        'error_msg': 'Login failed',
        'connection_error': 'Connection error. Please try again.',
        'admin_title': 'Administrator',
        'support_agent': 'Support Agent',
        'auditor_panel': 'Auditor Panel'
    }
};

class I18n {
    constructor() {
        this.lang = localStorage.getItem('appLang') || navigator.language.split('-')[0] || 'es';
        if (!['es', 'en'].includes(this.lang)) this.lang = 'es';
        this.applyLanguage(this.lang);
        this.renderLanguageSelector();
    }

    setLanguage(lang) {
        this.lang = lang;
        localStorage.setItem('appLang', lang);
        this.applyLanguage(lang);
    }

    applyLanguage(lang) {
        document.documentElement.lang = lang;
        
        // Actualizar textos con atributo data-i18n
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (translations[lang] && translations[lang][key]) {
                if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {
                    el.placeholder = translations[lang][key];
                } else {
                    el.textContent = translations[lang][key];
                }
            }
        });

        // Actualizar selector visual si existe
        const selector = document.getElementById('lang-selector');
        if (selector) selector.value = lang;
    }

    translate(key) {
        return (translations[this.lang] && translations[this.lang][key]) || key;
    }

    renderLanguageSelector() {
        // Solo renderizar si existe un contenedor específico o en el body si es login
        const container = document.querySelector('.login-container');
        if (container && !document.getElementById('lang-container')) {
            const langDiv = document.createElement('div');
            langDiv.id = 'lang-container';
            langDiv.style.textAlign = 'right';
            langDiv.style.marginBottom = '15px';
            
            langDiv.innerHTML = `
                <select id="lang-selector" onchange="i18n.setLanguage(this.value)" style="padding:5px; border-radius:5px;">
                    <option value="es">Español 🇪🇸</option>
                    <option value="en">English 🇺🇸</option>
                </select>
            `;
            container.insertBefore(langDiv, container.firstChild);
            document.getElementById('lang-selector').value = this.lang;
        }
    }
}

// Inicializar globalmente
const i18n = new I18n();
