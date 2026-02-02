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
import { API_URL, APP_HOST } from '../config'; // <--- CONEXIÓN INTELIGENTE
import '../App.css'; 

/**
 * ============================================================================
 * COMPONENTE DASHBOARD PRINCIPAL (V3.5 ULTIMATE)
 * ============================================================================
 * Características: 
 * - Auto-conexión Cloud/Local.
 * - Refresco silencioso de datos en segundo plano.
 * - Gráficos avanzados con Recharts.
 * - Interfaz ejecutiva con KPIs financieros y operativos.
 */
const Dashboard = () => {
  // ==========================================
  // 1. CONFIGURACIÓN DE UI
  // ==========================================
  // Usamos el host detectado automáticamente para mostrar en la barra de estado
  const HOST = APP_HOST; 

  // ==========================================
  // 2. ESTADOS DE DATOS
  // ==========================================
  const [stats, setStats] = useState(null);       // KPIs Numéricos (OEE, Perdidas)
  const [history, setHistory] = useState([]);     // Datos históricos para gráficos
  const [advanced, setAdvanced] = useState(null); // Datos avanzados (Radar OEE)
  
  // Estados de carga y error
  const [loading, setLoading] = useState(true);   // Carga inicial (Pantalla completa)
  const [refreshing, setRefreshing] = useState(false); // Refresco en segundo plano
  const [error, setError] = useState(null);       // Mensajes de error críticos

  // ==========================================
  // 3. GENERADOR DE REPORTE PDF
  // ==========================================
  const handlePrintReport = () => {
    // Abre el endpoint de generación de reportes en una nueva pestaña
    const reportUrl = `${API_URL}/api/reports/daily`;
    console.log(`🖨️ Iniciando generación de reporte en: ${reportUrl}`);
    window.open(reportUrl, '_blank');
  };

  // ==========================================
  // 4. MOTOR DE DATOS (DATA FETCHING ENGINE)
  // ==========================================
  const loadData = async (isBackground = false) => {
    try {
      // Gestión de estados de carga para no interrumpir al usuario
      if (!isBackground) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      console.log(`📡 Sincronizando Dashboard con ${API_URL}... [Modo: ${isBackground ? 'Silencioso' : 'Completo'}]`);
      
      // Ejecución paralela de peticiones para máxima eficiencia
      const [alertsRes, energyRes, maintRes, historyRes, advRes] = await Promise.all([
        axios.get(`${API_URL}/api/alerts`),
        axios.get(`${API_URL}/api/energy/analysis`),
        axios.get(`${API_URL}/api/maintenance/predictions`),
        axios.get(`${API_URL}/api/dashboard/history`),
        axios.get(`${API_URL}/api/stats/advanced`)
      ]);

      // --- Procesamiento de Alertas ---
      const activeAlerts = alertsRes.data.filter(a => !a.acknowledged).length;
      
      // --- Procesamiento de Eficiencia Energética ---
      const efficiencyList = energyRes.data.map(item => parseFloat(item.efficiency_score) || 0);
      const avgEff = efficiencyList.length > 0 
        ? efficiencyList.reduce((a, b) => a + b, 0) / efficiencyList.length 
        : 0;

      // Actualización de Estados
      setStats({
        active_alerts: activeAlerts,
        efficiency: avgEff.toFixed(1),
        predictions_count: maintRes.data.length
      });

      setHistory(historyRes.data);
      setAdvanced(advRes.data);
      
      // Finalización exitosa
      setLoading(false);
      setRefreshing(false);
      setError(null);

    } catch (err) { 
      console.error("❌ Error de Sincronización:", err);
      // Solo mostramos error intrusivo si falla la carga inicial
      if (!isBackground) setError("No se pudo establecer conexión con el Núcleo de Planta.");
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ==========================================
  // 5. CICLO DE VIDA (LIFECYCLE)
  // ==========================================
  useEffect(() => {
    // 1. Carga inicial inmediata
    loadData(false);

    // 2. Programar actualización automática cada 60 segundos
    const interval = setInterval(() => {
      loadData(true); 
    }, 60000);

    // Limpieza al desmontar componente
    return () => clearInterval(interval);
  }, []);

  // ==========================================
  // 6. COMPONENTES AUXILIARES (TOOLTIPS)
  // ==========================================
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          padding: '12px',
          borderRadius: '8px',
          color: 'white',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
        }}>
          <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {label}
          </p>
          <p style={{ margin: '4px 0 0', fontWeight: 'bold', fontSize: '1.1rem', color: '#60a5fa' }}>
            {payload[0].value.toLocaleString()} <span style={{fontSize: '0.8rem', fontWeight: 400}}>BPD</span>
          </p>
        </div>
      );
    }
    return null;
  };

  // ==========================================
  // 7. RENDERIZADO: CARGA Y ERROR
  // ==========================================
  if (loading) {
    return (
      <div className="page-container" style={{display:'flex', justifyContent:'center', alignItems:'center', height:'80vh', flexDirection:'column'}}>
         <div className="brand-logo" style={{
           width: 64, height: 64, fontSize: '1.8rem', marginBottom: '24px', 
           background: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: 'white',
           display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '16px',
           animation: 'pulse 2s infinite'
         }}>IQ</div>
         <h3 style={{color: '#1e293b', marginBottom: '8px', fontWeight: 700}}>Inicializando Dashboard</h3>
         <p style={{color: '#64748b', fontSize: '0.9rem'}}>Estableciendo enlace seguro con {HOST}...</p>
         <style>{`@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); } 70% { box-shadow: 0 0 0 20px rgba(59, 130, 246, 0); } 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container" style={{display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', marginTop:'100px'}}>
        <div style={{background: '#fef2f2', padding: '20px', borderRadius: '50%', marginBottom: '20px'}}>
          <FiAlertCircle size={48} color="#ef4444" />
        </div>
        <h3 style={{color: '#1e293b', fontSize: '1.5rem', fontWeight: 700}}>Conexión Interrumpida</h3>
        <p style={{color: '#64748b', maxWidth: '450px', textAlign: 'center', margin: '10px 0 25px', lineHeight: '1.6'}}>
          No se pudo sincronizar con el backend en <strong>{API_URL}</strong>. <br/>
          Esto puede deberse a que el servidor "dormido" de Render se está despertando.
        </p>
        <button onClick={() => window.location.reload()} style={{
          padding: '12px 28px', background: '#2563eb', color: 'white', border: 'none', 
          borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '1rem',
          boxShadow: '0 4px 6px -1px rgba(37, 99, 235, 0.2)'
        }}>
          Reintentar Conexión
        </button>
      </div>
    );
  }

  // ==========================================
  // 8. PREPARACIÓN DE DATOS (RADAR CHART)
  // ==========================================
  const oeeChartData = advanced ? [
    { subject: 'Calidad', A: advanced.oee.quality, fullMark: 100 },
    { subject: 'Disp.', A: advanced.oee.availability, fullMark: 100 },
    { subject: 'Rendim.', A: advanced.oee.performance, fullMark: 100 },
    { subject: 'Salud', A: stats ? Math.max(0, 100 - (stats.active_alerts * 8)) : 80, fullMark: 100 },
    { subject: 'Energía', A: parseFloat(stats?.efficiency || 0), fullMark: 100 },
  ] : [];

  // ==========================================
  // 9. RENDERIZADO PRINCIPAL
  // ==========================================
  return (
    <div className="page-container">
      {/* HEADER */}
      <div className="page-header">
        <div className="page-title">
          <h1>Panel de Control Ejecutivo</h1>
          <p>Visión en tiempo real de operaciones, finanzas y mantenimiento</p>
        </div>
        
        {/* Badge de Estado del Sistema */}
        <div className="status-badge status-success" title={`Conectado a ${API_URL}`} style={{display: 'flex', alignItems: 'center', padding: '8px 16px', gap: '10px'}}>
          {refreshing ? (
            <FiRefreshCw className="spin-slow" size={18} color="#2563eb"/>
          ) : (
            <div style={{position: 'relative'}}>
              <FiWifi size={18} color="#16a34a"/>
              <span style={{position:'absolute', top:-2, right:-2, width:6, height:6, background:'#16a34a', borderRadius:'50%'}}></span>
            </div>
          )}
          <div style={{display: 'flex', flexDirection: 'column', lineHeight: '1.2'}}>
            <span style={{fontWeight: 700, fontSize: '0.85rem', color: '#0f172a'}}>SISTEMA ONLINE</span>
            <span style={{fontSize: '0.7rem', color: '#64748b'}}>{HOST}</span>
          </div>
        </div>
        <style>{`.spin-slow { animation: spin 2s linear infinite; } @keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>

      {/* --- SECCIÓN 1: TARJETAS KPI (4 COLUMNAS) --- */}
      <div className="grid-4">
        
        {/* KPI 1: OEE */}
        <div className="card" style={{borderLeft: '4px solid #8b5cf6', position: 'relative', overflow:'hidden'}}>
          <div style={{position:'absolute', right:-10, top:-10, opacity:0.05}}><FiActivity size={120}/></div>
          <div className="kpi-label" style={{color: '#8b5cf6'}}>EFICIENCIA GLOBAL (OEE)</div>
          <div className="kpi-value" style={{display:'flex', alignItems:'center', gap:'10px'}}>
            {advanced?.oee.score}%
            {advanced?.oee.score > 85 ? <FiArrowUp size={24} color="#16a34a"/> : <FiArrowDown size={24} color="#ef4444"/>}
          </div>
          <div className="kpi-sub" style={{display:'flex', alignItems:'center', gap:'5px'}}>
            {advanced?.oee.score > 85 ? <FiCheckCircle color="#16a34a"/> : <FiAlertCircle color="#ef4444"/>}
            <span style={{color: advanced?.oee.score > 85 ? '#16a34a' : '#ef4444', fontWeight: 600}}>
              {advanced?.oee.score > 85 ? 'Meta Alcanzada' : 'Debajo de Meta'}
            </span>
          </div>
        </div>

        {/* KPI 2: FINANZAS */}
        <div className="card" style={{borderLeft: '4px solid #ef4444'}}>
          <div className="kpi-label" style={{color: '#ef4444'}}>IMPACTO FINANCIERO (24H)</div>
          <div className="kpi-value">${advanced?.financial.daily_loss_usd}</div>
          <div className="kpi-sub" style={{color: '#64748b'}}>Pérdida estimada por ineficiencia</div>
        </div>

        {/* KPI 3: ESTABILIDAD */}
        <div className="card" style={{borderLeft: '4px solid #10b981'}}>
          <div className="kpi-label" style={{color: '#10b981'}}>ÍNDICE DE ESTABILIDAD</div>
          <div className="kpi-value">{advanced?.stability.index}/100</div>
          <div className="kpi-sub" style={{color: '#10b981', fontWeight: 600}}>Variabilidad de proceso baja</div>
        </div>

        {/* KPI 4: PRODUCCIÓN */}
        <div className="card" style={{borderLeft: '4px solid #3b82f6'}}>
          <div className="kpi-label" style={{color: '#3b82f6'}}>PRODUCCIÓN VOLUMÉTRICA</div>
          <div className="kpi-value">
            {history.length > 0 ? (history[history.length-1].production / 1000).toFixed(1) : 0}k
          </div>
          <div className="kpi-sub" style={{color: '#64748b'}}>Barriles por día (BPD)</div>
        </div>
      </div>

      {/* --- SECCIÓN 2: GRÁFICOS Y PANELES (2 COLUMNAS) --- */}
      <div className="grid-2">
        
        {/* GRÁFICO DE TENDENCIA */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiTrendingUp /> Tendencia Operativa (24h)</h3>
            <span className="badge-pro" style={{background:'#eff6ff', color:'#2563eb', border:'1px solid #dbeafe'}}>Datos Reales</span>
          </div>
          <div style={{height: '380px', width: '100%'}}>
            <ResponsiveContainer>
              <AreaChart data={history} margin={{top:20, right:10, left:0, bottom:0}}>
                <defs>
                  <linearGradient id="colorProd" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="time_label" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 11, fill: '#64748b', fontWeight: 500}} 
                  interval="preserveStartEnd"
                  minTickGap={30}
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 11, fill: '#64748b', fontWeight: 500}} 
                />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="production" 
                  stroke="#3b82f6" 
                  strokeWidth={3}
                  fill="url(#colorProd)" 
                  animationDuration={2000}
                  activeDot={{r: 6, strokeWidth: 0, fill: '#2563eb'}}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* PANELES LATERALES (RADAR + ACCIONES) */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          
          {/* Gráfico Radar */}
          <div className="card" style={{flex: 1, minHeight: '340px', display:'flex', flexDirection:'column'}}>
            <div className="card-header">
              <h3 className="card-title"><FiPieChart /> Análisis Multidimensional</h3>
            </div>
            <div style={{flex: 1, width: '100%', minHeight: '250px'}}>
              <ResponsiveContainer>
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={oeeChartData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="subject" tick={{fill: '#475569', fontSize: 11, fontWeight: 700}} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar 
                    name="Performance" 
                    dataKey="A" 
                    stroke="#8b5cf6" 
                    strokeWidth={3} 
                    fill="#8b5cf6" 
                    fillOpacity={0.4} 
                  />
                  <Tooltip 
                    contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'}}
                    itemStyle={{color: '#4f46e5', fontWeight: 600}}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Centro de Control */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title"><FiServer /> Centro de Control</h3>
            </div>
            
            <div style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
              
              {/* Botón de Reporte */}
              <button 
                onClick={handlePrintReport}
                className="action-button"
                style={{ 
                  padding: '16px', background: 'white', border: '1px solid #e2e8f0', 
                  borderRadius: '12px', textAlign: 'left', fontWeight: 600, 
                  color: '#334155', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '15px',
                  transition: 'all 0.2s ease', position: 'relative', overflow: 'hidden',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.05)';
                  e.currentTarget.style.borderColor = '#3b82f6';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.02)';
                  e.currentTarget.style.borderColor = '#e2e8f0';
                }}
              >
                <div style={{background: '#eff6ff', padding: '10px', borderRadius: '10px'}}>
                  <FiPrinter size={22} color="#3b82f6" />
                </div>
                <div>
                  <div style={{fontSize: '1rem', color: '#1e293b'}}>Generar Reporte Diario</div>
                  <div style={{fontSize: '0.8rem', color: '#64748b', fontWeight: 400}}>Formato PDF Oficial (ISO-9001)</div>
                </div>
              </button>

              {/* Estado de IA */}
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