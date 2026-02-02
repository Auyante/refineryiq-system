// ============================================================================
// CONFIGURACIÓN DEFINITIVA - CORREGIDA PARA CORS
// ============================================================================

// DETECCIÓN AUTOMÁTICA DEL BACKEND
const getBackendUrl = () => {
  const host = window.location.hostname;
  
  // PRODUCCIÓN - Dominio personalizado (usa api.subdominio)
  if (host === 'refineryiq.dev' || host === 'www.refineryiq.dev') {
    return 'https://api.refineryiq.dev';
  }
  
  // Si estás en el dominio del backend (por si acaso)
  if (host === 'api.refineryiq.dev' || host === 'system.refineryiq.dev') {
    return `https://${host}`;
  }
  
  // DESARROLLO LOCAL
  if (host === 'localhost' || host === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  
  // POR DEFECTO (Render temporal)
  return 'https://refineryiq-system.onrender.com';
};

export const API_URL = getBackendUrl();
export const APP_HOST = window.location.hostname;

// Logs para depuración (siempre visibles para debug)
console.log("🌍 REFINERYIQ - CONFIGURACIÓN ACTIVA");
console.log(`📱 Dominio: ${APP_HOST}`);
console.log(`🔗 Backend: ${API_URL}`);
console.log("======================================");