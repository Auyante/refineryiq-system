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
import { API_URL, APP_HOST } from '../config'; // <--- IMPORTACIÓN CORRECTA
import '../App.css'; 

/**
 * COMPONENTE DASHBOARD PRINCIPAL
 * Versión: 3.6 Cloud Native
 */
const Dashboard = () => {
  // ==========================================
  // ESTADOS DE DATOS Y UI
  // ==========================================
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [advanced, setAdvanced] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // ==========================================
  // GENERADOR DE REPORTE PDF
  // ==========================================
  const handlePrintReport = () => {
    const reportUrl = `${API_URL}/api/reports/daily`;
    window.open(reportUrl, '_blank');
  };

  // ==========================================
  // LÓGICA DE CARGA DE DATOS
  // ==========================================
  const loadData = async (isBackground = false) => {
    try {
      if (!isBackground) setLoading(true);
      else setRefreshing(true);

      console.log(`📡 Dashboard sincronizando con: ${API_URL}`);
      
      const [alertsRes, energyRes, maintRes, historyRes, advRes] = await Promise.all([
        axios.get(`${API_URL}/api/alerts`),
        axios.get(`${API_URL}/api/energy/analysis`),
        axios.get(`${API_URL}/api/maintenance/predictions`),
        axios.get(`${API_URL}/api/dashboard/history`),
        axios.get(`${API_URL}/api/stats/advanced`)
      ]);

      const activeAlerts = alertsRes.data.filter(a => !a.acknowledged).length;
      const efficiencyList = energyRes.data.map(item => parseFloat(item.efficiency_score) || 0);
      const avgEff = efficiencyList.length > 0 
        ? efficiencyList.reduce((a, b) => a + b, 0) / efficiencyList.length 
        : 0;

      setStats({
        active_alerts: activeAlerts,
        efficiency: avgEff.toFixed(1),
        predictions_count: maintRes.data.length
      });

      setHistory(historyRes.data);
      setAdvanced(advRes.data);
      
      setLoading(false);
      setRefreshing(false);
      setError(null);

    } catch (err) { 
      console.error("❌ Error Dashboard:", err);
      if (!isBackground) setError("No se pudo establecer conexión con la nube.");
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData(false);
    const interval = setInterval(() => { loadData(true); }, 60000);
    return () => clearInterval(interval);
  }, []);

  // TOOLTIP PERSONALIZADO
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'rgba(17, 24, 39, 0.9)', border: '1px solid rgba(255,255,255,0.1)',
          padding: '12px', borderRadius: '8px', color: 'white', boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
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

  // PANTALLAS DE CARGA / ERROR
  if (loading) {
    return (
      <div className="page-container" style={{display:'flex', justifyContent:'center', alignItems:'center', height:'80vh', flexDirection:'column'}}>
         <div className="brand-logo" style={{width: 64, height: 64, fontSize: '1.8rem', marginBottom: '24px', animation: 'pulse 1.5s infinite'}}>IQ</div>
         <h3 style={{color: '#1f2937', marginBottom: '8px'}}>Conectando a Nube...</h3>
         <p style={{color: '#6b7280', fontSize: '0.9rem'}}>Estableciendo enlace con {API_URL}</p>
         <style>{`@keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container" style={{display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', marginTop:'80px'}}>
        <FiAlertCircle size={60} color="#ef4444" style={{marginBottom: '20px'}} />
        <h3 style={{color: '#ef4444', fontSize: '1.5rem'}}>Sistema Offline</h3>
        <p style={{color: '#374151', maxWidth: '400px', textAlign: 'center', margin: '10px 0 20px'}}>
          {error} <br/> El backend en Render podría estar iniciándose.
        </p>
        <button onClick={() => window.location.reload()} style={{
          padding: '12px 24px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600
        }}>Reintentar</button>
      </div>
    );
  }

  const oeeChartData = advanced ? [
    { subject: 'Calidad', A: advanced.oee.quality, fullMark: 100 },
    { subject: 'Disp.', A: advanced.oee.availability, fullMark: 100 },
    { subject: 'Rendimiento', A: advanced.oee.performance, fullMark: 100 },
    { subject: 'Salud', A: stats ? 100 - (stats.active_alerts * 5) : 80, fullMark: 100 },
    { subject: 'Energía', A: parseFloat(stats?.efficiency || 0), fullMark: 100 },
  ] : [];

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Control Operativo Principal</h1>
          <p>Visión integral de producción y mantenimiento</p>
        </div>
        
        <div className="status-badge status-success" style={{display: 'flex', alignItems: 'center', padding: '8px 16px', gap: '8px'}}>
          {refreshing ? <FiRefreshCw className="spin-slow" size={16} /> : <FiWifi size={16} />}
          <div style={{display: 'flex', flexDirection: 'column', lineHeight: '1.1'}}>
            <span style={{fontWeight: 700}}>ONLINE</span>
            <span style={{fontSize: '0.7rem', opacity: 0.8}}>{APP_HOST}</span>
          </div>
        </div>
        <style>{`.spin-slow { animation: spin 2s linear infinite; } @keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>

      <div className="grid-4">
        {/* KPI 1 */}
        <div className="card" style={{borderLeft: '4px solid var(--accent)'}}>
          <div className="kpi-label">OEE DE PLANTA</div>
          <div className="kpi-value">{advanced?.oee.score}%</div>
          <div className="kpi-sub">{advanced?.oee.score > 85 ? 'Óptimo' : 'Mejorable'}</div>
        </div>
        {/* KPI 2 */}
        <div className="card" style={{borderLeft: '4px solid var(--danger)'}}>
          <div className="kpi-label">PÉRDIDA (24H)</div>
          <div className="kpi-value">${advanced?.financial.daily_loss_usd}</div>
          <div className="kpi-sub">Impacto financiero</div>
        </div>
        {/* KPI 3 */}
        <div className="card" style={{borderLeft: '4px solid var(--success)'}}>
          <div className="kpi-label">ESTABILIDAD</div>
          <div className="kpi-value">{advanced?.stability.index}/100</div>
          <div className="kpi-sub">Variabilidad de proceso</div>
        </div>
        {/* KPI 4 */}
        <div className="card" style={{borderLeft: '4px solid #6366f1'}}>
          <div className="kpi-label">PRODUCCIÓN</div>
          <div className="kpi-value">{history.length > 0 ? (history[history.length-1].production / 1000).toFixed(1) : 0}k</div>
          <div className="kpi-sub">Barriles por día (BPD)</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><h3 className="card-title"><FiTrendingUp /> Tendencia (24h)</h3></div>
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
                <XAxis dataKey="time_label" axisLine={false} tickLine={false} tick={{fontSize: 11}} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 11}} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="production" stroke="#3b82f6" fill="url(#colorProd)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          <div className="card" style={{flex: 1, minHeight: '340px'}}>
            <div className="card-header"><h3 className="card-title"><FiPieChart /> Análisis OEE</h3></div>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={oeeChartData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{fontSize: 11}} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="Planta" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
             <div className="card-header"><h3 className="card-title"><FiServer /> Acciones Rápidas</h3></div>
             <button onClick={handlePrintReport} className="action-button" style={{
               padding:'15px', width:'100%', background:'#f8fafc', border:'1px solid #e2e8f0', 
               borderRadius:'8px', cursor:'pointer', display:'flex', alignItems:'center', gap:'10px'
             }}>
               <FiPrinter size={20} color="#3b82f6"/> <span>Generar Reporte Diario PDF</span>
             </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;