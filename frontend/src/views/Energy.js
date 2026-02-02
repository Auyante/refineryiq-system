import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiZap, FiTarget, FiActivity } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- IMPORTACIÓN DE LA CONEXIÓN CENTRAL
import '../App.css';

const Energy = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Conectando al endpoint de análisis energético
    axios.get(`${API_URL}/api/energy/analysis`)
      .then(res => {
        // Protección contra datos nulos
        const safeData = Array.isArray(res.data) ? res.data : [];
        setData(safeData);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error cargando energía:", err);
        setLoading(false);
      });
  }, []);

  // Función original para abreviar nombres largos automáticamente en el gráfico/tabla
  const formatXAxis = (name) => {
    if (!name) return 'UNK';
    if (name.includes('Destilación')) return 'CDU'; // Crude Distillation Unit
    if (name.includes('Craqueo')) return 'FCC';     // Fluid Catalytic Cracking
    if (name.includes('Hidrotratamiento')) return 'HT'; // Hydrotreating
    return name;
  };

  if (loading) return <div className="page-container" style={{textAlign:'center', padding:'4rem'}}>Calculando eficiencia energética...</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Gestión Energética</h1>
          <p>Auditoría de consumo vs Benchmark en tiempo real</p>
        </div>
      </div>

      <div className="card" style={{marginBottom: '2rem'}}>
        <div className="card-header">
          <h3 className="card-title"><FiZap /> Eficiencia por Unidad</h3>
        </div>
        
        <div className="table-container">
          <table className="modern-table">
            <thead>
              <tr>
                <th>Unidad de Proceso</th>
                <th>Índice de Eficiencia</th>
                <th>Estado</th>
                <th>Ahorro Potencial</th>
              </tr>
            </thead>
            <tbody>
              {data.length > 0 ? data.map((row, index) => (
                <tr key={index}>
                  <td>
                    {/* Nombre completo + ID abreviado */}
                    <strong style={{color: '#1e293b'}}>{row.unit_name || row.unit_id}</strong>
                    <div style={{fontSize: '0.75rem', color: '#6b7280'}}>
                      ID: {formatXAxis(row.unit_name || row.unit_id)}
                    </div>
                  </td>
                  <td>
                    <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                      {/* Barra de progreso visual */}
                      <div style={{width: '80px', height: '8px', background: '#e5e7eb', borderRadius: '4px', overflow:'hidden'}}>
                        <div style={{
                          width: `${Math.min(row.efficiency_score, 100)}%`, 
                          height: '100%', 
                          background: row.efficiency_score > 90 ? '#10b981' : row.efficiency_score > 75 ? '#f59e0b' : '#ef4444',
                          borderRadius: '4px',
                          transition: 'width 1s ease'
                        }}></div>
                      </div>
                      <span style={{fontWeight:600}}>{row.efficiency_score.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td>
                    <span className={`status-badge ${row.efficiency_score > 90 ? 'status-success' : 'status-warning'}`}>
                      {row.efficiency_score > 90 ? 'OPTIMAL' : 'REVISAR'}
                    </span>
                  </td>
                  <td style={{fontWeight: 600, color: row.estimated_savings > 0 ? '#10b981' : '#9ca3af'}}>
                    {row.estimated_savings > 0 ? (
                      <span style={{display:'flex', alignItems:'center', gap:'4px'}}>
                        <FiTarget size={14}/> -{row.estimated_savings.toFixed(2)} kWh
                      </span>
                    ) : '-'}
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="4" style={{textAlign:'center', padding:'2rem', color:'#9ca3af'}}>
                    <FiActivity size={24} style={{marginBottom:'10px'}}/><br/>
                    No hay datos de análisis disponibles.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Energy;