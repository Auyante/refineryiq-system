// ============================================================================
// ARCHIVO DE CONFIGURACIÓN CENTRAL (V4.0)
// ============================================================================
// Este archivo detecta automáticamente el entorno y define la ruta del backend.
// ============================================================================

// 1. Detección de Entorno
// Si la URL empieza por 'https', asumimos que estamos en la nube (Render).
const isSecure = window.location.protocol === 'https:';

// 2. Definición de la URL del Backend
// - Producción (Nube): Usamos la URL oficial de Render.
// - Desarrollo (Local): Usamos localhost:8000.
export const API_URL = isSecure
  ? "https://refineryiq-system.onrender.com" 
  : "http://localhost:8000";

// 3. Host para visualización en UI (ej: "Conectado a refineryiq.dev")
export const APP_HOST = window.location.hostname;

// Logs de diagnóstico para consola
console.log("========================================");
console.log("🚀 SISTEMA INICIADO: REFINERYIQ CLIENT");
console.log(`🌍 MODO: ${isSecure ? "NUBE (PRODUCCIÓN)" : "LOCAL (DESARROLLO)"}`);
console.log(`🔗 BACKEND OBJETIVO: ${API_URL}`);
console.log("========================================");