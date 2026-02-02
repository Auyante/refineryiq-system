// ==========================================
// CONFIGURACIÓN CENTRAL DE CONEXIÓN
// ==========================================

// Detectamos si estamos en un entorno seguro (HTTPS)
const isSecure = window.location.protocol === 'https:';

// MODO NUBE FORZADA:
// Usamos siempre la URL de Render para evitar errores de "localhost" sin backend.
// Si algún día quieres trabajar 100% local, cambia esta URL a "http://localhost:8000"
export const API_URL = "https://refineryiq-system.onrender.com";

// Exportamos el HOST para mostrarlo en el Dashboard (solo visual)
export const APP_HOST = window.location.hostname;

console.log("🚀 SISTEMA INICIADO");
console.log("🌐 Conectando a Backend:", API_URL);