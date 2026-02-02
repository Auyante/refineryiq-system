// ============================================================================
// CONFIGURACIÓN DEFINITIVA CON DOMINIO PERSONALIZADO
// ============================================================================

// DETECCIÓN AUTOMÁTICA DEL ENTORNO
const getBackendUrl = () => {
  const host = window.location.hostname;
  
  // PRODUCCIÓN - Dominio personalizado
  if (host === 'refineryiq.dev' || host === 'www.refineryiq.dev') {
    return 'https://api.refineryiq.dev';
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

// Logs para depuración
console.log("🌍 REFINERYIQ - CONFIGURACIÓN ACTIVA");
console.log(`📱 Dominio: ${APP_HOST}`);
console.log(`🔗 Backend: ${API_URL}`);
console.log("======================================");