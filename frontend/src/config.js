// Detectamos si estamos corriendo en localhost (tu PC)
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

// Si es local, usa el puerto 8000. Si es nube, usa la URL de Render SIN PUERTO.
export const API_URL = isLocal 
  ? "http://localhost:8000" 
  : "https://refineryiq-system.onrender.com"; // <--- TU BACKEND EN RENDER

console.log("🌐 Conectando a:", API_URL); // Para depurar en consola