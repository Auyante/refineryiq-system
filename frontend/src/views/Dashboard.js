import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar 
} from 'recharts';
import { 
  FiTrendingUp, FiCheckCircle, FiPieChart, FiAlertCircle, 
  FiPrinter, FiCpu, FiServer, FiWifi, FiRefreshCw, FiActivity, FiArrowUp, FiArrowDown
} from 'react-icons/fi';
import '../App.css'; 

/**
 * COMPONENTE DASHBOARD PRINCIPAL
 * Versión: 3.5 Ultimate
 * Características: Auto-IP, Silent Refresh, Custom Tooltips, Full UI
 */
const Dashboard = () => {
  // ==========================================
  // 1. CONFIGURACIÓN DE CONEXIÓN DINÁMICA
  // ==========================================
  const PROTOCOL = window.location.protocol;
  const HOST = window.location.hostname; 
  const PORT = '8000';
  const API_URL = `${PROTOCOL}//${HOST}:${PORT}`; 

  // ==========================================
  // 2. ESTADOS DE DATOS Y UI
  // ==========================================
  const [stats, setStats] = useState(null);       // KPIs Numéricos (OEE, Perdidas)
  const [history, setHistory] = useState([]);     // Datos para el gráfico de Área
  const [advanced, setAdvanced] = useState(null); // Datos para el Radar y Finanzas
  
  // Estados de carga
  const [loading, setLoading] = useState(true);   // Carga inicial (Pantalla completa)
  const [refreshing, setRefreshing] = useState(false); // Refresco en segundo plano
  const [error, setError] = useState(null);       // Mensajes de error

  // ==========================================
  // 3. GENERADOR DE REPORTE PDF
  // ==========================================
  const handlePrintReport = () => {
    const reportUrl = `${API_URL}/api/reports/daily`;
    console.log(`🖨️ Generando reporte PDF desde: ${reportUrl}`);
    window.open(reportUrl, '_blank');
  };

  // ==========================================
  // 4. LÓGICA DE CARGA DE DATOS (DATA FETCHING)
  // ==========================================
  const loadData = async (isBackground = false) => {
    try {
      // Si es carga inicial, mostramos spinner grande.
      // Si es actualización de fondo, solo activamos el indicador pequeño.
      if (!isBackground) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      console.log(`📡 Sincronizando telemetría... [Modo: ${isBackground ? 'Silencioso' : 'Completo'}]`);
      
      // Ejecutamos todas las peticiones en paralelo para máxima velocidad
      const [alertsRes, energyRes, maintRes, historyRes, advRes] = await Promise.all([
        axios.get(`${API_URL}/api/alerts`),
        axios.get(`${API_URL}/api/energy/analysis`),
        axios.get(`${API_URL}/api/maintenance/predictions`),
        axios.get(`${API_URL}/api/dashboard/history`),
        axios.get(`${API_URL}/api/stats/advanced`)
      ]);

      // --- Procesamiento de Alertas ---
      const activeAlerts = alertsRes.data.filter(a => !a.acknowledged).length;
      
      // --- Procesamiento de Eficiencia ---
      const efficiencyList = energyRes.data.map(item => parseFloat(item.efficiency_score) || 0);
      const avgEff = efficiencyList.length > 0 
        ? efficiencyList.reduce((a, b) => a + b, 0) / efficiencyList.length 
        : 0;

      // Actualizamos estados
      setStats({
        active_alerts: activeAlerts,
        efficiency: avgEff.toFixed(1),
        predictions_count: maintRes.data.length
      });

      setHistory(historyRes.data);
      setAdvanced(advRes.data);
      
      // Finalizamos estados de carga
      setLoading(false);
      setRefreshing(false);
      setError(null); // Limpiamos errores si hubo éxito

    } catch (err) { 
      console.error("❌ Error de conexión:", err);
      // Solo mostramos error en pantalla completa si falló la carga inicial
      if (!isBackground) setError("No se pudo establecer conexión con el servidor de planta.");
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ==========================================
  // 5. EFECTOS (INICIO Y INTERVALO)
  // ==========================================
  useEffect(() => {
    // 1. Carga inicial inmediata
    loadData(false);

    // 2. Programar actualización cada 60 segundos (Silenciosa)
    const interval = setInterval(() => {
      loadData(true); 
    }, 60000);

    // Limpiar intervalo al salir
    return () => clearInterval(interval);
  }, [API_URL]);

  // ==========================================
  // 6. COMPONENTE: CUSTOM TOOLTIP (Gráficos)
  // ==========================================
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'rgba(17, 24, 39, 0.9)',
          border: '1px solid rgba(255,255,255,0.1)',
          padding: '12px',
          borderRadius: '8px',
          color: 'white',
          boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
        }}>
          <p style={{ margin: 0, fontSize: '0.8rem', color: '#9ca3af' }}>{label}</p>
          <p style={{ margin: '4px 0 0', fontWeight: 'bold', fontSize: '1rem', color: '#60a5fa' }}>
            {payload[0].value.toLocaleString()} bbl
          </p>
        </div>
      );
    }
    return null;
  };

  // ==========================================
  // 7. RENDERIZADO: PANTALLAS DE CARGA / ERROR
  // ==========================================
  if (loading) {
    return (
      <div className="page-container" style={{display:'flex', justifyContent:'center', alignItems:'center', height:'80vh', flexDirection:'column'}}>
         <div className="brand-logo" style={{width: 64, height: 64, fontSize: '1.8rem', marginBottom: '24px', animation: 'pulse 1.5s infinite'}}>IQ</div>
         <h3 style={{color: '#1f2937', marginBottom: '8px'}}>Inicializando Sistema...</h3>
         <p style={{color: '#6b7280', fontSize: '0.9rem'}}>Estableciendo enlace seguro con {HOST}</p>
         <style>{`@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); transform: scale(1); } 70% { box-shadow: 0 0 0 15px rgba(59, 130, 246, 0); transform: scale(1.05); } 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); transform: scale(1); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container" style={{display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', marginTop:'80px'}}>
        <FiAlertCircle size={60} color="#ef4444" style={{marginBottom: '20px'}} />
        <h3 style={{color: '#ef4444', fontSize: '1.5rem'}}>Error de Conexión</h3>
        <p style={{color: '#374151', maxWidth: '400px', textAlign: 'center', margin: '10px 0 20px'}}>
          {error}. Asegúrate de que el Backend está corriendo en <strong>{API_URL}</strong>
        </p>
        <button onClick={() => window.location.reload()} style={{
          padding: '12px 24px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '1rem'
        }}>
          Reintentar Conexión
        </button>
      </div>
    );
  }

  // ==========================================
  // 8. PREPARACIÓN DE DATOS (RADAR)
  // ==========================================
  const oeeChartData = advanced ? [
    { subject: 'Calidad', A: advanced.oee.quality, fullMark: 100 },
    { subject: 'Disponibilidad', A: advanced.oee.availability, fullMark: 100 },
    { subject: 'Rendimiento', A: advanced.oee.performance, fullMark: 100 },
    { subject: 'Salud Activos', A: stats ? 100 - (stats.active_alerts * 5) : 80, fullMark: 100 },
    { subject: 'Energía', A: parseFloat(stats?.efficiency || 0), fullMark: 100 },
  ] : [];

  // ==========================================
  // 9. RENDERIZADO PRINCIPAL (DASHBOARD)
  // ==========================================
  return (
    <div className="page-container">
      {/* HEADER PRINCIPAL */}
      <div className="page-header">
        <div className="page-title">
          <h1>Control Operativo Principal</h1>
          <p>Visión integral de producción, finanzas y mantenimiento en tiempo real</p>
        </div>
        
        {/* Badge de Estado de Conexión */}
        <div className="status-badge status-success" title={`Conectado a ${API_URL}`} style={{display: 'flex', alignItems: 'center', padding: '8px 16px', gap: '8px'}}>
          {refreshing ? (
            <FiRefreshCw className="spin-slow" size={16} />
          ) : (
            <FiWifi size={16} />
          )}
          <div style={{display: 'flex', flexDirection: 'column', lineHeight: '1.1'}}>
            <span style={{fontWeight: 700}}>ONLINE</span>
            <span style={{fontSize: '0.7rem', opacity: 0.8}}>{HOST}</span>
          </div>
        </div>
        <style>{`.spin-slow { animation: spin 2s linear infinite; } @keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>

      {/* --- SECCIÓN 1: GRID DE KPIs (4 TARJETAS) --- */}
      <div className="grid-4">
        {/* KPI 1: OEE */}
        <div className="card" style={{borderLeft: '4px solid var(--accent)', position: 'relative', overflow:'hidden'}}>
          <div style={{position:'absolute', right:10, top:10, opacity:0.1}}><FiActivity size={80} color="var(--accent)"/></div>
          <div style={{color: 'var(--text-secondary)', fontSize: '0.75rem', fontWeight: 700, marginBottom: '8px', letterSpacing:'0.05em'}}>
            OEE DE PLANTA
          </div>
          <div style={{fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)', display:'flex', alignItems:'center', gap:'10px'}}>
            {advanced?.oee.score}%
            {advanced?.oee.score > 85 ? <FiArrowUp size={20} color="var(--success)"/> : <FiArrowDown size={20} color="var(--warning)"/>}
          </div>
          <div style={{fontSize: '0.85rem', marginTop: '4px', fontWeight: 600, color: advanced?.oee.score > 85 ? 'var(--success)' : 'var(--warning)', display: 'flex', alignItems: 'center', gap: '5px'}}>
            {advanced?.oee.score > 85 ? <FiCheckCircle /> : <FiAlertCircle />}
            {advanced?.oee.score > 85 ? 'Rendimiento Óptimo' : 'Requiere Optimización'}
          </div>
        </div>

        {/* KPI 2: FINANZAS */}
        <div className="card" style={{borderLeft: '4px solid var(--danger)'}}>
          <div style={{color: 'var(--text-secondary)', fontSize: '0.75rem', fontWeight: 700, marginBottom: '8px', letterSpacing:'0.05em'}}>
            IMPACTO FINANCIERO (24H)
          </div>
          <div style={{fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)'}}>
            ${advanced?.financial.daily_loss_usd}
          </div>
          <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px'}}>
            Pérdida estimada por ineficiencia
          </div>
        </div>

        {/* KPI 3: ESTABILIDAD */}
        <div className="card" style={{borderLeft: '4px solid var(--success)'}}>
          <div style={{color: 'var(--text-secondary)', fontSize: '0.75rem', fontWeight: 700, marginBottom: '8px', letterSpacing:'0.05em'}}>
            ÍNDICE DE ESTABILIDAD
          </div>
          <div style={{fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)'}}>
            {advanced?.stability.index}/100
          </div>
          <div style={{fontSize: '0.85rem', color: 'var(--success)', marginTop: '4px', fontWeight: 600}}>
            Variabilidad de proceso baja
          </div>
        </div>

        {/* KPI 4: PRODUCCIÓN */}
        <div className="card" style={{borderLeft: '4px solid #6366f1'}}>
          <div style={{color: 'var(--text-secondary)', fontSize: '0.75rem', fontWeight: 700, marginBottom: '8px', letterSpacing:'0.05em'}}>
            PRODUCCIÓN VOLUMÉTRICA
          </div>
          <div style={{fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)'}}>
            {history.length > 0 ? (history[history.length-1].production / 1000).toFixed(1) : 0}k
          </div>
          <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px'}}>
            Barriles por día (BPD)
          </div>
        </div>
      </div>

      {/* --- SECCIÓN 2: GRID GRÁFICO (2 COLUMNAS) --- */}
      <div className="grid-2">
        
        {/* COLUMNA IZQUIERDA: GRÁFICO DE ÁREA */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiTrendingUp /> Tendencia Operativa (24h)</h3>
            <span className="badge-pro" style={{background:'#eff6ff', color:'#1d4ed8', border:'1px solid #dbeafe'}}>Datos Reales</span>
          </div>
          <div style={{height: '380px', width: '100%'}}>
            <ResponsiveContainer>
              <AreaChart data={history} margin={{top:20, right:10, left:0, bottom:0}}>
                <defs>
                  <linearGradient id="colorProd" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="time_label" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 11, fill: '#6b7280', fontWeight: 500}} 
                  interval={Math.floor(history.length / 6)} 
                  dy={10}
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 11, fill: '#6b7280', fontWeight: 500}} 
                />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="production" 
                  stroke="#3b82f6" 
                  strokeWidth={3} 
                  fill="url(#colorProd)" 
                  animationDuration={1500} 
                  activeDot={{r: 6, strokeWidth: 0}}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* COLUMNA DERECHA: RADAR Y ACCIONES */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          
          {/* GRÁFICO RADAR OEE */}
          <div className="card" style={{flex: 1, minHeight: '340px', display:'flex', flexDirection:'column'}}>
            <div className="card-header">
              <h3 className="card-title"><FiPieChart /> Análisis Multidimensional</h3>
            </div>
            <div style={{flex: 1, width: '100%', minHeight: '250px'}}>
              <ResponsiveContainer>
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={oeeChartData}>
                  <PolarGrid stroke="#e5e7eb" />
                  <PolarAngleAxis dataKey="subject" tick={{fill: '#4b5563', fontSize: 11, fontWeight: 700}} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar 
                    name="Performance Planta" 
                    dataKey="A" 
                    stroke="#8b5cf6" 
                    strokeWidth={3} 
                    fill="#8b5cf6" 
                    fillOpacity={0.3} 
                  />
                  <Tooltip 
                     contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)'}}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* PANEL DE CENTRO DE CONTROL */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title"><FiServer /> Centro de Control</h3>
            </div>
            
            <div style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
              
              {/* Botón de Reporte (Estilo Premium) */}
              <button 
                onClick={handlePrintReport}
                className="action-button"
                style={{ 
                  padding: '16px', background: 'white', border: '1px solid #E2E8F0', 
                  borderRadius: '12px', textAlign: 'left', fontWeight: 600, 
                  color: '#334155', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '15px',
                  transition: 'all 0.2s ease', position: 'relative', overflow: 'hidden',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
                  e.currentTarget.style.borderColor = '#3b82f6';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.02)';
                  e.currentTarget.style.borderColor = '#E2E8F0';
                }}
              >
                <div style={{background: '#eff6ff', padding: '10px', borderRadius: '10px'}}>
                  <FiPrinter size={22} color="#3b82f6" />
                </div>
                <div>
                  <div style={{fontSize: '1rem', color: '#1e293b'}}>Generar Reporte Diario</div>
                  <div style={{fontSize: '0.8rem', color: '#64748b', fontWeight: 400}}>Formato PDF Oficial A4 (ISO-9001)</div>
                </div>
              </button>

              {/* Estado del ML (Estilo Tarjeta) */}
              <div style={{ 
                padding: '16px', background: 'linear-gradient(to right, #f0fdf4, #dcfce7)', borderRadius: '12px', 
                border: '1px solid #bbf7d0', display: 'flex', alignItems: 'center', gap: '15px'
              }}>
                <div style={{background: '#16a34a', padding: '10px', borderRadius: '50%', display: 'flex', boxShadow: '0 4px 6px rgba(22, 163, 74, 0.2)'}}>
                  <FiCpu color="white" size={18} />
                </div>
                <div>
                  <strong style={{ color: '#14532d', fontSize: '0.95rem', display: 'block' }}>Motor IA: ONLINE</strong>
                  <div style={{ fontSize: '0.8rem', color: '#166534' }}>Modelo Random Forest v2.1 Operativo</div>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;