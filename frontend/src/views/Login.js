import React, { useState } from 'react';
import axios from 'axios';
import { FiUser, FiLock, FiEye, FiEyeOff, FiCpu, FiActivity } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- IMPORTACIÓN DE LA CONEXIÓN SEGURA
import '../App.css';

const Login = ({ onLogin }) => {
  // --- ESTADOS ---
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // --- MANEJO DE LOGIN ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Simulamos un pequeño delay artificial (800ms) para que se vea la animación de carga
    // Esto da sensación de seguridad y procesamiento robusto.
    setTimeout(async () => {
      try {
        console.log(`🔐 Intentando login en: ${API_URL}/api/auth/login`);
        
        // Petición real al backend
        const res = await axios.post(`${API_URL}/api/auth/login`, { 
          username, 
          password 
        });
        
        if (res.data.token) {
          console.log("✅ Autenticación exitosa");
          onLogin(res.data); // Éxito: Pasamos datos al App.js
        }
      } catch (err) {
        setLoading(false);
        console.error("Login Error:", err);
        
        // Manejo de errores específicos para dar feedback útil al usuario
        if (err.response && err.response.status === 401) {
          setError('Credenciales incorrectas. Verifique su ID y contraseña.');
        } else if (err.code === "ERR_NETWORK" || err.message === "Network Error") {
          setError('No se pudo conectar con el Servidor. Verifique su internet o el estado del Backend.');
        } else {
          setError('Error del sistema. Intente nuevamente más tarde.');
        }
      }
    }, 800);
  };

  return (
    <div className="login-container">
      {/* ESTILOS EN LÍNEA PARA GARANTIZAR VISUALIZACIÓN 
         (Manteniendo tu diseño original intacto)
      */}
      <style>{`
        .login-container {
          height: 100vh;
          width: 100vw;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          position: relative;
          overflow: hidden;
        }
        
        /* Efecto de partículas sutiles en el fondo */
        .login-container::before {
          content: '';
          position: absolute;
          width: 200%;
          height: 200%;
          background: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
          background-size: 30px 30px;
          animation: moveBackground 20s linear infinite;
        }

        @keyframes moveBackground {
          0% { transform: translate(0, 0); }
          100% { transform: translate(-50px, -50px); }
        }

        .login-card {
          background: rgba(30, 41, 59, 0.7);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 3rem;
          border-radius: 20px;
          width: 100%;
          max-width: 420px;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
          position: relative;
          z-index: 10;
          animation: fadeIn 0.8s ease-out;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .brand-header {
          text-align: center;
          margin-bottom: 2.5rem;
        }

        .input-group {
          position: relative;
          margin-bottom: 1.5rem;
        }

        .input-icon {
          position: absolute;
          left: 16px;
          top: 50%;
          transform: translateY(-50%);
          color: #94a3b8;
          font-size: 1.2rem;
          transition: color 0.3s;
        }

        .input-field {
          width: 100%;
          padding: 14px 14px 14px 50px;
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(148, 163, 184, 0.2);
          border-radius: 12px;
          color: white;
          font-size: 1rem;
          transition: all 0.3s ease;
          outline: none;
        }

        .input-field:focus {
          border-color: #3b82f6;
          background: rgba(15, 23, 42, 0.8);
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
        }

        .input-field:focus + .input-icon {
          color: #3b82f6;
        }

        .password-toggle {
          position: absolute;
          right: 16px;
          top: 50%;
          transform: translateY(-50%);
          color: #64748b;
          cursor: pointer;
          transition: color 0.3s;
        }

        .password-toggle:hover {
          color: #e2e8f0;
        }

        .login-btn {
          width: 100%;
          padding: 14px;
          background: linear-gradient(to right, #2563eb, #3b82f6);
          color: white;
          border: none;
          border-radius: 12px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
          margin-top: 1rem;
          position: relative;
          overflow: hidden;
        }

        .login-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
        }

        .login-btn:active {
          transform: translateY(0);
        }

        .login-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .spinner {
          width: 20px;
          height: 20px;
          border: 3px solid rgba(255,255,255,0.3);
          border-radius: 50%;
          border-top-color: white;
          animation: spin 1s linear infinite;
          margin: 0 auto;
        }

        @keyframes spin {
          100% { transform: rotate(360deg); }
        }

        .hint-text {
          margin-top: 2rem;
          text-align: center;
          font-size: 0.8rem;
          color: #64748b;
          line-height: 1.5;
        }
      `}</style>

      <div className="login-card">
        <div className="brand-header">
          <div style={{
            width: 64, height: 64, margin: '0 auto 1rem',
            background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
            borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(59, 130, 246, 0.3)'
          }}>
            <FiCpu size={32} color="white" />
          </div>
          <h2 style={{color: 'white', margin: 0, fontSize: '1.8rem', fontWeight: 700}}>RefineryIQ</h2>
          <p style={{color: '#94a3b8', margin: '5px 0 0', fontSize: '0.95rem'}}>Acceso Seguro v4.0</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <input 
              type="text" 
              className="input-field" 
              placeholder="ID de Usuario"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <FiUser className="input-icon" />
          </div>

          <div className="input-group">
            <input 
              type={showPassword ? "text" : "password"} 
              className="input-field" 
              placeholder="Contraseña de Acceso"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <FiLock className="input-icon" />
            <div 
              className="password-toggle"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <FiEyeOff /> : <FiEye />}
            </div>
          </div>

          {/* MENSAJE DE ERROR VISUAL */}
          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', 
              color: '#fca5a5', padding: '10px', borderRadius: '8px', fontSize: '0.85rem', marginBottom: '1rem',
              display: 'flex', alignItems: 'center', gap: '8px'
            }}>
              <FiActivity /> {error}
            </div>
          )}

          {/* BOTÓN DE LOGIN */}
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? <div className="spinner"></div> : 'Iniciar Sesión'}
          </button>
        </form>

        <div className="hint-text">
          <p>Credenciales de prueba: <strong>admin</strong> / <strong>admin123</strong></p>
          <p style={{opacity: 0.6, fontSize: '0.75rem', marginTop: '5px'}}>
            Conexión: {API_URL.includes('localhost') ? 'Modo Local' : 'Nube Segura Encrypted'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;