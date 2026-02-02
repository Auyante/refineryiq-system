import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { FiCpu, FiAlertTriangle } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- IMPORTACIÓN DE LA CONEXIÓN CENTRAL
import '../App.css';

const Maintenance = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Conectando al endpoint de predicciones usando la URL dinámica
    axios.get(`${API_URL}/api/maintenance/predictions`)
      .then(res => {
        setData(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error cargando mantenimiento:", err);
        setLoading(false);
      });
  }, []);

  // Función para determinar el color de la barra según la probabilidad de falla
  const getRiskColor = (prob) => prob > 80 ? '#ef4444' : prob > 40 ? '#f59e0b' : '#10b981';

  if (loading) return <div className="page-container" style={{textAlign:'center', padding:'4rem'}}>Cargando diagnósticos IA...</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Mantenimiento Predictivo</h1>
          <p>Análisis de salud de activos basado en Machine Learning</p>
        </div>
      </div>

      <div className="grid-2">
        {/* Gráfico de Barras: Probabilidad de Falla */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiCpu /> Probabilidad de Falla</h3>
          </div>
          <div style={{height: '350px'}}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{top: 5, right: 30, left: 40, bottom: 5}}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis type="category" dataKey="equipment_name" width={100} tick={{fontSize: 11}} />
                <Tooltip 
                  cursor={{fill: 'transparent'}}
                  contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)'}}
                />
                <Bar dataKey="failure_probability" barSize={20} radius={[0, 4, 4, 0]}>
                  {data.map((entry, index) => (
                    <Cell key={index} fill={getRiskColor(entry.failure_probability)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Lista de Diagnósticos */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiAlertTriangle /> Diagnóstico IA</h3>
          </div>
          <div style={{display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '350px', overflowY: 'auto', paddingRight:'5px'}}>
            {data.length > 0 ? data.map((item, idx) => (
              <div key={idx} style={{
                padding: '12px', border: '1px solid var(--border-light)', borderRadius: '8px',
                borderLeft: `4px solid ${getRiskColor(item.failure_probability)}`,
                background: '#f8fafc'
              }}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '4px'}}>
                  <strong style={{fontSize: '0.9rem', color: '#1e293b'}}>{item.equipment_name}</strong>
                  <span style={{fontSize: '0.8rem', fontWeight: 700, color: getRiskColor(item.failure_probability)}}>
                    {item.failure_probability.toFixed(1)}% Riesgo
                  </span>
                </div>
                <div style={{fontSize: '0.85rem', color: '#64748b'}}>
                  {item.recommendation}
                </div>
                <div style={{fontSize: '0.75rem', color: '#94a3b8', marginTop:'5px', textAlign:'right'}}>
                   Predicción: {item.prediction}
                </div>
              </div>
            )) : (
              <div style={{textAlign:'center', padding:'2rem', color:'#94a3b8'}}>
                No hay predicciones disponibles. El modelo se está entrenando.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Maintenance;