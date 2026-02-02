import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell 
} from 'recharts';
import { FiCpu, FiAlertTriangle, FiActivity, FiCheckCircle } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- CONEXIÓN CENTRALIZADA
import '../App.css';

/**
 * MÓDULO DE MANTENIMIENTO PREDICTIVO
 * Visualiza las probabilidades de fallo calculadas por el motor de IA (Random Forest/XGBoost).
 */
const Maintenance = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log(`🧠 Consultando modelo predictivo en: ${API_URL}`);
        const res = await axios.get(`${API_URL}/api/maintenance/predictions`);
        
        // Validación de seguridad para evitar pantallas blancas
        const safeData = Array.isArray(res.data) ? res.data : [];
        setData(safeData);
        setLoading(false);
      } catch (err) {
        console.error("Error Maintenance:", err);
        setError("No se pudieron obtener los diagnósticos del modelo IA.");
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Función auxiliar para determinar el color del riesgo
  const getRiskColor = (prob) => {
    if (prob > 80) return '#ef4444'; // Rojo (Crítico)
    if (prob > 40) return '#f59e0b'; // Naranja (Advertencia)
    return '#10b981';                // Verde (Seguro)
  };

  if (loading) return (
    <div className="page-container" style={{display:'flex', justifyContent:'center', alignItems:'center', height:'80vh', flexDirection:'column'}}>
      <div className="spinner" style={{marginBottom:'20px'}}></div>
      <p style={{color:'#64748b'}}>Procesando diagnósticos de maquinaria...</p>
    </div>
  );

  return (
    <div className="page-container">
      {/* HEADER */}
      <div className="page-header">
        <div className="page-title">
          <h1>Mantenimiento Predictivo</h1>
          <p>Análisis de salud de activos basado en Inteligencia Artificial</p>
        </div>
        <div className="status-badge status-success">
          <FiCpu style={{ marginRight: '8px' }} />
          Modelo IA Activo
        </div>
      </div>

      {error && (
        <div className="card" style={{borderLeft:'4px solid #ef4444', color:'#ef4444', marginBottom:'20px'}}>
          <FiAlertTriangle style={{marginRight:'10px'}}/> {error}
        </div>
      )}

      <div className="grid-2">
        {/* GRÁFICO DE BARRAS: PROBABILIDAD DE FALLA */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiActivity /> Probabilidad de Falla por Equipo</h3>
          </div>
          <div style={{height: '350px', width: '100%'}}>
            {data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{top: 5, right: 30, left: 40, bottom: 5}}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                  <XAxis type="number" domain={[0, 100]} hide />
                  <YAxis 
                    type="category" 
                    dataKey="equipment_name" 
                    width={100} 
                    tick={{fontSize: 11, fill: '#4b5563'}} 
                  />
                  <Tooltip 
                    cursor={{fill: '#f3f4f6'}}
                    contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)'}}
                    formatter={(value) => [`${value.toFixed(1)}%`, 'Probabilidad']}
                  />
                  <Bar dataKey="failure_probability" barSize={20} radius={[0, 4, 4, 0]}>
                    {data.map((entry, index) => (
                      <Cell key={index} fill={getRiskColor(entry.failure_probability)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{height:'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'#9ca3af'}}>
                No hay datos suficientes para generar gráfico.
              </div>
            )}
          </div>
        </div>

        {/* LISTA DETALLADA DE DIAGNÓSTICOS */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiAlertTriangle /> Diagnóstico Detallado</h3>
          </div>
          
          <div style={{display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '350px', overflowY: 'auto', paddingRight:'5px'}}>
            {data.length > 0 ? data.map((item, idx) => (
              <div key={idx} style={{
                padding: '16px', 
                border: '1px solid #e2e8f0', 
                borderRadius: '10px',
                borderLeft: `5px solid ${getRiskColor(item.failure_probability)}`,
                background: '#ffffff',
                transition: 'transform 0.2s',
                boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
              }}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems:'center'}}>
                  <div>
                    <strong style={{fontSize: '0.95rem', color: '#1e293b', display:'block'}}>{item.equipment_name || item.equipment_id}</strong>
                    <span style={{fontSize: '0.75rem', color: '#64748b'}}>ID: {item.equipment_id}</span>
                  </div>
                  <div style={{textAlign:'right'}}>
                    <span style={{
                      fontSize: '0.9rem', fontWeight: 800, 
                      color: getRiskColor(item.failure_probability)
                    }}>
                      {item.failure_probability.toFixed(1)}%
                    </span>
                    <div style={{fontSize:'0.7rem', color:'#94a3b8', textTransform:'uppercase'}}>Riesgo</div>
                  </div>
                </div>
                
                <div style={{background: '#f8fafc', padding:'10px', borderRadius:'6px', marginTop:'5px'}}>
                  <div style={{fontSize: '0.85rem', color: '#334155', fontWeight: 500, marginBottom:'4px'}}>
                    Recomendación:
                  </div>
                  <div style={{fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic'}}>
                    "{item.recommendation || "Sin acción requerida actualmente."}"
                  </div>
                </div>

                <div style={{marginTop:'10px', display:'flex', justifyContent:'space-between', fontSize:'0.75rem', color:'#94a3b8'}}>
                   <span>Confianza del modelo: {(item.confidence || 95).toFixed(1)}%</span>
                   <span>Predicción: <strong>{item.prediction}</strong></span>
                </div>
              </div>
            )) : (
              <div style={{textAlign:'center', padding:'3rem', color:'#94a3b8'}}>
                <FiCheckCircle size={40} style={{marginBottom:'10px', color:'#10b981'}}/>
                <p>No se han detectado anomalías. <br/>Todos los sistemas operan dentro de parámetros normales.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Maintenance;