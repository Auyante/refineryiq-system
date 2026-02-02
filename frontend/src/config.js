// ==========================================
// CONFIGURACIÓN CENTRAL DE CONEXIÓN (V4.0)
// ==========================================

// 1. Detectamos si estamos corriendo en la Nube (HTTPS) o en Local
const isSecure = window.location.protocol === 'https:';

// 2. Definimos la URL del Backend
// - Si es Nube (Render): Usa la dirección oficial https://refineryiq-system.onrender.com
// - Si es Local (Tu PC): Usa http://localhost:8000
export const API_URL = isSecure
  ? "https://refineryiq-system.onrender.com" 
  : "http://localhost:8000";

// 3. Exportamos el Host para mostrarlo en la UI (ej: "Conectado a Render")
export const APP_HOST = window.location.hostname;

console.log("🚀 SISTEMA INICIADO");
console.log("🌐 Modo:", isSecure ? "NUBE (Producción)" : "LOCAL (Desarrollo)");
console.log("🔗 Backend:", API_URL);