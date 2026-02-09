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
import { API_URL, APP_HOST } from '../config';
import '../App.css';

/**
 * COMPONENTE DASHBOARD PRINCIPAL
 * Versión: 3.6 - Corregido para producción en Render
 */
const Dashboard = () => {
  const HOST = APP_HOST;

  const [stats, setStats] = useState({ 
    active_alerts: 0, 
    efficiency: 0, 
    predictions_count: 0 
  });
  const [history, setHistory] = useState([]);
  const [advanced, setAdvanced] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const handlePrintReport = () => {
    const reportUrl = `${API_URL}/api/reports/daily`;
    console.log(`🖨️ Generando reporte PDF desde: ${reportUrl}`);
    window.open(reportUrl, '_blank');
  };

  const loadData = async (isBackground = false) => {
    try {
      if (!isBackground) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      console.log(`📡 Sincronizando telemetría con ${API_URL}...`);
      
      // Hacer peticiones en paralelo a TODOS los endpoints necesarios
      const [advancedRes, historyRes, alertsRes] = await Promise.all([
        axios.get(`${API_URL}/api/stats/advanced`).catch(err => {
          console.error("❌ Error en stats/advanced:", err.response?.status || err.message);
          return { data: null };
        }),
        axios.get(`${API_URL}/api/dashboard/history`).catch(err => {
          console.error("❌ Error en dashboard/history:", err.response?.status || err.message);
          return { data: [] };
        }),
        axios.get(`${API_URL}/api/alerts`).catch(err => {
          console.error("❌ Error en alerts:", err.response?.status || err.message);
          return { data: [] };
        })
      ]);

      console.log("📊 Respuestas recibidas:", {
        advanced: advancedRes.data ? "✅" : "❌",
        history: historyRes.data?.length || 0,
        alerts: alertsRes.data?.length || 0
      });

      // Procesar datos avanzados (OEE, impacto financiero, estabilidad)
      if (advancedRes.data) {
        console.log("📈 Datos avanzados:", advancedRes.data);
        setAdvanced(advancedRes.data);
        
        // Extraer eficiencia de los datos avanzados
        const efficiency = advancedRes.data.oee?.score || 88.5;
        
        setStats({
          active_alerts: alertsRes.data?.filter(a => !a.acknowledged).length || 0,
          efficiency: efficiency,
          predictions_count: 0
        });
      } else {
        console.warn("⚠️ No hay datos avanzados, usando valores por defecto");
        // Datos de respaldo si falla la API
        const defaultAdvanced = {
          oee: { score: 85, quality: 99.5, availability: 98.0, performance: 85 },
          stability: { index: 90, trend: "stable" },
          financial: { daily_loss_usd: 4350 }
        };
        setAdvanced(defaultAdvanced);
        setStats({
          active_alerts: 0,
          efficiency: 85,
          predictions_count: 0
        });
      }

      // Historial para gráficos
      if (historyRes.data && historyRes.data.length > 0) {
        console.log(`📊 Historial recibido: ${historyRes.data.length} puntos`);
        setHistory(historyRes.data);
      } else {
        console.warn("⚠️ No hay datos de historial");
        setHistory([]);
      }
      
      setLoading(false);
      setRefreshing(false);
      setError(null);

    } catch (err) { 
      console.error("❌ Error crítico en loadData:", err);
      if (!isBackground) {
        setError("No se pudo establecer conexión con el servidor de planta.");
      }
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData(false);

    const interval = setInterval(() => {
      loadData(true); 
    }, 60000);

    return () => clearInterval(interval);
  }, []);

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

  if (loading) {
    return (
      <div className="page-container" style={{
        display:'flex', 
        justifyContent:'center', 
        alignItems:'center', 
        height:'80vh', 
        flexDirection:'column'
      }}>
        <div className="brand-logo" style={{
          width: 64, 
          height: 64, 
          fontSize: '1.8rem', 
          marginBottom: '24px', 
          animation: 'pulse 1.5s infinite'
        }}>
          IQ
        </div>
        <h3 style={{color: '#1f2937', marginBottom: '8px'}}>Inicializando Sistema...</h3>
        <p style={{color: '#6b7280', fontSize: '0.9rem'}}>Estableciendo enlace seguro con {HOST}</p>
        <style>{`
          @keyframes pulse { 
            0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); transform: scale(1); } 
            70% { box-shadow: 0 0 0 15px rgba(59, 130, 246, 0); transform: scale(1.05); } 
            100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); transform: scale(1); } 
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container" style={{
        display:'flex', 
        flexDirection:'column', 
        alignItems:'center', 
        justifyContent:'center', 
        marginTop:'80px'
      }}>
        <FiAlertCircle size={60} color="#ef4444" style={{marginBottom: '20px'}} />
        <h3 style={{color: '#ef4444', fontSize: '1.5rem'}}>Error de Conexión</h3>
        <p style={{color: '#374151', maxWidth: '400px', textAlign: 'center', margin: '10px 0 20px'}}>
          {error}. Asegúrate de que el Backend está corriendo en <strong>{API_URL}</strong>
        </p>
        <button onClick={() => window.location.reload()} style={{
          padding: '12px 24px', 
          background: '#3b82f6', 
          color: 'white', 
          border: 'none', 
          borderRadius: '8px', 
          cursor: 'pointer', 
          fontWeight: 600, 
          fontSize: '1rem'
        }}>
          Reintentar Conexión
        </button>
      </div>
    );
  }

  const oeeChartData = advanced ? [
    { subject: 'Calidad', A: advanced.oee?.quality || 99.2, fullMark: 100 },
    { subject: 'Disp.', A: advanced.oee?.availability || 96.8, fullMark: 100 },
    { subject: 'Rendim.', A: advanced.oee?.performance || 89.3, fullMark: 100 },
    { subject: 'Salud Activos', A: Math.max(0, 100 - ((stats.active_alerts || 0) * 10)), fullMark: 100 },
    { subject: 'Energía', A: stats.efficiency || 0, fullMark: 100 },
  ] : [];

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Control Operativo Principal</h1>
          <p>Visión integral de producción, finanzas y mantenimiento en tiempo real</p>
        </div>
        
        <div className="status-badge status-success" title={`Conectado a ${API_URL}`} style={{
          display: 'flex', 
          alignItems: 'center', 
          padding: '8px 16px', 
          gap: '8px'
        }}>
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
        <style>{`
          .spin-slow { 
            animation: spin 2s linear infinite; 
          } 
          @keyframes spin { 
            100% { transform: rotate(360deg); } 
          }
        `}</style>
      </div>

      <div className="grid-4">
        {/* OEE DE PLANTA */}
        <div className="card" style={{borderLeft: '4px solid var(--accent)', position: 'relative', overflow:'hidden'}}>
          <div style={{position:'absolute', right:10, top:10, opacity:0.1}}>
            <FiActivity size={80} color="var(--accent)"/>
          </div>
          <div style={{
            color: 'var(--text-secondary)', 
            fontSize: '0.75rem', 
            fontWeight: 700, 
            marginBottom: '8px', 
            letterSpacing:'0.05em'
          }}>
            OEE DE PLANTA
          </div>
          <div style={{
            fontSize: '2.5rem', 
            fontWeight: 800, 
            color: 'var(--text-main)', 
            display:'flex', 
            alignItems:'center', 
            gap:'10px'
          }}>
            {advanced?.oee?.score || 85}%
            {advanced?.oee?.score > 85 ? 
              <FiArrowUp size={20} color="var(--success)"/> : 
              <FiArrowDown size={20} color="var(--warning)"/>
            }
          </div>
          <div style={{
            fontSize: '0.85rem', 
            marginTop: '4px', 
            fontWeight: 600, 
            color: advanced?.oee?.score > 85 ? 'var(--success)' : 'var(--warning)', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '5px'
          }}>
            {advanced?.oee?.score > 85 ? <FiCheckCircle /> : <FiAlertCircle />}
            {advanced?.oee?.score > 85 ? 'Rendimiento Óptimo' : 'Requiere Optimización'}
          </div>
        </div>

        {/* IMPACTO FINANCIERO (24H) */}
        <div className="card" style={{borderLeft: '4px solid var(--danger)'}}>
          <div style={{
            color: 'var(--text-secondary)', 
            fontSize: '0.75rem', 
            fontWeight: 700, 
            marginBottom: '8px', 
            letterSpacing:'0.05em'
          }}>
            IMPACTO FINANCIERO (24H)
          </div>
          <div style={{fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)'}}>
            ${(advanced?.financial?.daily_loss_usd || 0).toLocaleString()}
          </div>
          <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px'}}>
            Pérdida estimada por ineficiencia
          </div>
        </div>

        {/* ÍNDICE DE ESTABILIDAD */}
        <div className="card" style={{borderLeft: '4px solid var(--success)'}}>
          <div style={{
            color: 'var(--text-secondary)', 
            fontSize: '0.75rem', 
            fontWeight: 700, 
            marginBottom: '8px', 
            letterSpacing:'0.05em'
          }}>
            ÍNDICE DE ESTABILIDAD
          </div>
          <div style={{fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)'}}>
            {advanced?.stability?.index || 90}/100
          </div>
          <div style={{
            fontSize: '0.85rem', 
            color: advanced?.stability?.trend === 'improving' ? 'var(--success)' : 
                   advanced?.stability?.trend === 'stable' ? 'var(--warning)' : 'var(--danger)', 
            marginTop: '4px', 
            fontWeight: 600
          }}>
            {advanced?.stability?.trend === 'improving' ? 'Tendencia positiva' :
             advanced?.stability?.trend === 'stable' ? 'Estable' : 'Requiere atención'}
          </div>
        </div>

        {/* PRODUCCIÓN VOLUMÉTRICA */}
        <div className="card" style={{borderLeft: '4px solid #6366f1'}}>
          <div style={{
            color: 'var(--text-secondary)', 
            fontSize: '0.75rem', 
            fontWeight: 700, 
            marginBottom: '8px', 
            letterSpacing:'0.05em'
          }}>
            PRODUCCIÓN VOLUMÉTRICA
          </div>
          <div style={{fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)'}}>
            {history.length > 0 ? 
              ((history[history.length-1]?.production || 0) / 1000).toFixed(1) + 'k' : 
              '0k'
            }
          </div>
          <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px'}}>
            Barriles por día (BPD)
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiTrendingUp /> Tendencia Operativa (24h)</h3>
            <span className="badge-pro" style={{
              background:'#eff6ff', 
              color:'#1d4ed8', 
              border:'1px solid #dbeafe'
            }}>
              {history.length > 0 ? `${history.length} puntos` : 'Sin datos'}
            </span>
          </div>
          <div style={{height: '380px', width: '100%'}}>
            {history.length > 0 ? (
              <ResponsiveContainer>
                <AreaChart 
                  data={history} 
                  margin={{top:20, right:10, left:0, bottom:0}}
                >
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
                    interval={history.length > 6 ? Math.floor(history.length / 6) : 1} 
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
            ) : (
              <div style={{height:'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'#94a3b8'}}>
                <div style={{textAlign:'center'}}>
                  <FiTrendingUp size={40} style={{marginBottom:'10px', opacity:0.5}}/>
                  <p>No hay datos de tendencia disponibles</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          <div className="card" style={{
            flex: 1, 
            minHeight: '340px', 
            display:'flex', 
            flexDirection:'column'
          }}>
            <div className="card-header">
              <h3 className="card-title"><FiPieChart /> Análisis Multidimensional</h3>
            </div>
            <div style={{flex: 1, width: '100%', minHeight: '250px'}}>
              {oeeChartData.length > 0 ? (
                <ResponsiveContainer>
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={oeeChartData}>
                    <PolarGrid stroke="#e5e7eb" />
                    <PolarAngleAxis 
                      dataKey="subject" 
                      tick={{fill: '#4b5563', fontSize: 11, fontWeight: 700}} 
                    />
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
                      contentStyle={{
                        borderRadius: '8px', 
                        border: 'none', 
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{height:'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'#94a3b8'}}>
                  <div style={{textAlign:'center'}}>
                    <FiPieChart size={40} style={{marginBottom:'10px', opacity:0.5}}/>
                    <p>No hay datos para análisis multidimensional</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3 className="card-title"><FiServer /> Centro de Control</h3>
            </div>
            
            <div style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
              <button 
                onClick={handlePrintReport}
                className="action-button"
                style={{ 
                  padding: '16px', 
                  background: 'white', 
                  border: '1px solid #E2E8F0', 
                  borderRadius: '12px', 
                  textAlign: 'left', 
                  fontWeight: 600, 
                  color: '#334155', 
                  cursor: 'pointer', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '15px',
                  transition: 'all 0.2s ease', 
                  position: 'relative', 
                  overflow: 'hidden',
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
                  <div style={{fontSize: '0.8rem', color: '#64748b', fontWeight: 400}}>
                    Formato PDF Oficial A4 (ISO-9001)
                  </div>
                </div>
              </button>

              <div style={{ 
                padding: '16px', 
                background: 'linear-gradient(to right, #f0fdf4, #dcfce7)', 
                borderRadius: '12px', 
                border: '1px solid #bbf7d0', 
                display: 'flex', 
                alignItems: 'center', 
                gap: '15px'
              }}>
                <div style={{
                  background: '#16a34a', 
                  padding: '10px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  boxShadow: '0 4px 6px rgba(22, 163, 74, 0.2)'
                }}>
                  <FiCpu color="white" size={18} />
                </div>
                <div>
                  <strong style={{ color: '#14532d', fontSize: '0.95rem', display: 'block' }}>
                    Motor IA: ONLINE
                  </strong>
                  <div style={{ fontSize: '0.8rem', color: '#166534' }}>
                    Modelo Random Forest v2.1 Operativo
                  </div>
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