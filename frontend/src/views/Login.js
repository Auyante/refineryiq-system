import React, { useState } from 'react';
import axios from 'axios';
import { FiUser, FiLock, FiEye, FiEyeOff, FiCpu, FiActivity, FiWifiOff } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- IMPORTACIÓN CENTRALIZADA
import '../App.css';

const Login = ({ onLogin }) => {
  // --- ESTADOS ---
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isNetworkError, setIsNetworkError] = useState(false);

  // --- MANEJO DE LOGIN ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsNetworkError(false);
    setLoading(true);

    try {
      console.log(`🔐 Intentando login en: ${API_URL}/api/auth/login`);
      
      // Aumentamos el timeout a 30 segundos porque Render versión gratuita se "duerme"
      const res = await axios.post(`${API_URL}/api/auth/login`, 
        { username, password },
        { timeout: 30000 } 
      );

      if (res.data.token) {
        console.log("✅ Login exitoso");
        onLogin(res.data);
      }
    } catch (err) {
      console.error("❌ Error de Login:", err);
      setLoading(false);

      // DIAGNÓSTICO EXACTO DEL ERROR
      if (err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED') {
        // Error de conexión (Backend apagado o sin internet)
        setError('No se pudo conectar con el servidor. El sistema podría estar iniciándose (espere 30s).');
        setIsNetworkError(true);
      } else if (err.response && err.response.status === 401) {
        // Credenciales malas real
        setError('Usuario o contraseña incorrectos.');
      } else {
        // Otro error
        setError('Error del sistema. Intente nuevamente.');
      }

      if (navigator.vibrate) navigator.vibrate(200);
    }
  };

  return (
    <div className="login-container">
      {/* FONDO ANIMADO CSS */}
      <style>{`
        .login-container {
          height: 100vh; width: 100vw; display: flex; align-items: center; justify-content: center;
          background: linear-gradient(-45deg, #0f172a, #1e3a8a, #020617, #1e40af);
          background-size: 400% 400%; animation: gradientBG 15s ease infinite;
          position: relative; overflow: hidden;
        }
        @keyframes gradientBG {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .grid-overlay {
          position: absolute; width: 100%; height: 100%;
          background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
          background-size: 40px 40px; pointer-events: none;
        }
        .login-card {
          background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 3rem 2.5rem; border-radius: 20px; width: 100%; max-width: 420px;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); text-align: center;
          animation: fadeInUp 0.6s ease-out;
        }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .input-group { position: relative; margin-bottom: 1.25rem; text-align: left; }
        .input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: 1.2rem; }
        .input-field {
          width: 100%; padding: 14px 14px 14px 45px; background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: white; font-size: 1rem; outline: none;
          transition: all 0.3s ease;
        }
        .input-field:focus { border-color: #3b82f6; background: rgba(15, 23, 42, 0.8); box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15); }
        .password-toggle { position: absolute; right: 14px; top: 50%; transform: translateY(-50%); color: #64748b; cursor: pointer; }
        .login-btn {
          width: 100%; padding: 14px; background: linear-gradient(to right, #2563eb, #3b82f6);
          color: white; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer;
          transition: transform 0.2s; display: flex; align-items: center; justify-content: center; margin-top: 1rem;
        }
        .login-btn:hover { transform: translateY(-2px); }
        .login-btn:disabled { opacity: 0.7; cursor: wait; }
        .spinner {
          width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%;
          border-top-color: white; animation: spin 1s linear infinite;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>

      <div className="grid-overlay"></div>

      <div className="login-card">
        <div style={{
          width: 64, height: 64, margin: '0 auto 1.5rem',
          background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
          borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)'
        }}>
          <FiCpu size={32} color="white" />
        </div>

        <h2 style={{color: 'white', marginBottom: '0.5rem', fontWeight: 700, fontSize: '1.8rem'}}>RefineryIQ</h2>
        <p style={{color: '#94a3b8', marginBottom: '2.5rem', fontSize: '0.95rem'}}>Acceso Seguro de Planta v3.0</p>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <input type="text" className="input-field" placeholder="Usuario ID" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <FiUser className="input-icon" />
          </div>

          <div className="input-group">
            <input type={showPassword ? "text" : "password"} className="input-field" placeholder="Contraseña" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <FiLock className="input-icon" />
            <div className="password-toggle" onClick={() => setShowPassword(!showPassword)}>{showPassword ? <FiEyeOff /> : <FiEye />}</div>
          </div>

          {error && (
            <div style={{
              background: isNetworkError ? 'rgba(234, 179, 8, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              border: `1px solid ${isNetworkError ? 'rgba(234, 179, 8, 0.3)' : 'rgba(239, 68, 68, 0.2)'}`,
              color: isNetworkError ? '#fde047' : '#fca5a5',
              padding: '12px', borderRadius: '8px', fontSize: '0.85rem', marginBottom: '1rem',
              display: 'flex', alignItems: 'center', gap: '8px', textAlign: 'left'
            }}>
              {isNetworkError ? <FiWifiOff size={24} /> : <FiActivity size={20} />} 
              <span>{error}</span>
            </div>
          )}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? <div className="spinner"></div> : 'Iniciar Sesión'}
          </button>
        </form>

        <div style={{marginTop: '2rem', fontSize: '0.8rem', color: '#64748b'}}>
          <p>Credenciales: <strong>admin</strong> / <strong>admin123</strong></p>
          <p style={{marginTop:'5px', fontSize:'0.7rem', opacity:0.5}}>Conectando a: {API_URL.replace('https://', '')}</p>
        </div>
      </div>
    </div>
  );
};

export default Login;