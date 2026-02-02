import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiZap, FiTarget, FiActivity, FiBarChart2 } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- CONEXIÓN CENTRALIZADA
import '../App.css';

/**
 * MÓDULO DE GESTIÓN ENERGÉTICA
 * Visualiza el consumo, eficiencia y oportunidades de ahorro.
 */
const Energy = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchEnergyData();
  }, []);

  const fetchEnergyData = async () => {
    try {
      setLoading(true);
      console.log(`⚡ Analizando consumo energético en: ${API_URL}`);
      
      const res = await axios.get(`${API_URL}/api/energy/analysis`);
      
      // Validación para asegurar que siempre sea un array
      const safeData = Array.isArray(res.data) ? res.data : [];
      setData(safeData);
      setLoading(false);
    } catch (err) {
      console.error("Error Energy:", err);
      setError("No se pudieron cargar los datos de auditoría energética.");
      setLoading(false);
    }
  };

  // Función para abreviar IDs largos en la interfaz
  const formatUnitID = (name) => {
    if (!name) return 'UNK';
    if (name.includes('Destilación') || name.includes('CDU')) return 'CDU';
    if (name.includes('Craqueo') || name.includes('FCC')) return 'FCC';
    if (name.includes('Hidro') || name.includes('HT')) return 'HT';
    return name.substring(0, 4).toUpperCase();
  };

  // Función para determinar color de eficiencia
  const getEfficiencyColor = (score) => {
    if (score >= 90) return '#10b981'; // Verde (Excelente)
    if (score >= 75) return '#f59e0b'; // Amarillo (Regular)
    return '#ef4444';                // Rojo (Malo)
  };

  if (loading) return (
    <div className="page-container" style={{display:'flex', justifyContent:'center', alignItems:'center', height:'80vh', flexDirection:'column'}}>
      <div className="spinner" style={{marginBottom:'20px'}}></div>
      <p style={{color:'#64748b'}}>Calculando índices de eficiencia...</p>
    </div>
  );

  return (
    <div className="page-container">
      {/* HEADER */}
      <div className="page-header">
        <div className="page-title">
          <h1>Gestión Energética</h1>
          <p>Auditoría de consumo vs Benchmark en tiempo real</p>
        </div>
        <div className="status-badge status-success">
          <FiZap style={{ marginRight: '8px' }} />
          Monitor Activo
        </div>
      </div>

      {error && (
        <div className="card" style={{borderLeft:'4px solid #ef4444', color:'#ef4444', marginBottom:'20px'}}>
          <FiActivity style={{marginRight:'10px'}}/> {error}
        </div>
      )}

      {/* TARJETA PRINCIPAL DE ANÁLISIS */}
      <div className="card" style={{padding:'0', overflow:'hidden'}}>
        <div className="card-header" style={{background:'#f8fafc', borderBottom:'1px solid #e2e8f0', padding:'15px'}}>
          <h3 className="card-title" style={{margin:0, display:'flex', alignItems:'center', gap:'10px'}}>
            <FiBarChart2 /> Eficiencia por Unidad de Proceso
          </h3>
        </div>
        
        <div className="table-container">
          <table className="modern-table" style={{width:'100%'}}>
            <thead>
              <tr style={{background:'#f1f5f9'}}>
                <th style={{padding:'15px', textAlign:'left'}}>Unidad</th>
                <th style={{padding:'15px', textAlign:'left'}}>Índice de Eficiencia</th>
                <th style={{padding:'15px', textAlign:'left'}}>Estado</th>
                <th style={{padding:'15px', textAlign:'left'}}>Ahorro Potencial</th>
                <th style={{padding:'15px', textAlign:'left'}}>Recomendación IA</th>
              </tr>
            </thead>
            <tbody>
              {data.length > 0 ? data.map((row, index) => (
                <tr key={index} style={{borderBottom:'1px solid #f1f5f9'}}>
                  {/* Columna Unidad */}
                  <td style={{padding:'15px'}}>
                    <div>
                      <strong style={{color: '#1e293b', display:'block'}}>
                        {row.unit_name || row.unit_id || "Unidad Desconocida"}
                      </strong>
                      <span style={{fontSize: '0.75rem', color: '#64748b', background:'#f1f5f9', padding:'2px 6px', borderRadius:'4px'}}>
                        ID: {formatUnitID(row.unit_name || row.unit_id)}
                      </span>
                    </div>
                  </td>

                  {/* Columna Barra de Progreso */}
                  <td style={{padding:'15px', width:'25%'}}>
                    <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                      <div style={{flex:1, height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow:'hidden'}}>
                        <div style={{
                          width: `${Math.min(row.efficiency_score || 0, 100)}%`, 
                          height: '100%', 
                          background: getEfficiencyColor(row.efficiency_score || 0),
                          borderRadius: '4px',
                          transition: 'width 1s ease'
                        }}></div>
                      </div>
                      <span style={{fontWeight:700, color:'#334155', minWidth:'45px'}}>
                        {(row.efficiency_score || 0).toFixed(1)}%
                      </span>
                    </div>
                  </td>

                  {/* Columna Estado */}
                  <td style={{padding:'15px'}}>
                    <span className={`status-badge ${(row.efficiency_score || 0) > 90 ? 'status-success' : 'status-warning'}`}>
                      {(row.efficiency_score || 0) > 90 ? 'OPTIMAL' : 'REVISAR'}
                    </span>
                  </td>

                  {/* Columna Ahorro */}
                  <td style={{padding:'15px'}}>
                    {(row.savings_potential || row.estimated_savings) > 0 ? (
                      <div style={{color: '#10b981', fontWeight: 600, display:'flex', alignItems:'center', gap:'5px'}}>
                        <FiTarget /> -{(row.savings_potential || row.estimated_savings).toFixed(0)} kWh
                      </div>
                    ) : (
                      <span style={{color:'#94a3b8'}}>-</span>
                    )}
                  </td>

                  {/* Columna Recomendación */}
                  <td style={{padding:'15px', maxWidth:'250px'}}>
                    <span style={{fontSize:'0.85rem', color:'#475569', fontStyle:'italic'}}>
                      "{row.recommendation || "Sin acciones requeridas."}"
                    </span>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" style={{textAlign:'center', padding:'3rem', color:'#94a3b8'}}>
                    <FiActivity size={30} style={{marginBottom:'10px', opacity:0.5}}/>
                    <p>No hay datos de análisis energético disponibles.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {/* Footer */}
        <div style={{padding:'15px', background:'#f8fafc', borderTop:'1px solid #e2e8f0', textAlign:'right', fontSize:'0.8rem', color:'#64748b'}}>
          Datos actualizados en tiempo real por Smart Metering V4.0
        </div>
      </div>
    </div>
  );
};

export default Energy;