import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiSearch, FiCheckCircle, FiTool, FiBox, FiActivity, FiServer, FiAlertTriangle } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- CONEXIÓN CENTRALIZADA
import '../App.css';

const Assets = () => {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAssets();
  }, []);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      console.log(`🛠️ Cargando inventario de activos desde: ${API_URL}`);
      
      const res = await axios.get(`${API_URL}/api/assets/overview`);
      
      // Validación de Seguridad: Aseguramos que siempre sea un array
      const safeData = Array.isArray(res.data) ? res.data : [];
      setAssets(safeData);
      setLoading(false);
    } catch (err) {
      console.error("Error Assets:", err);
      setError("No se pudo cargar el catálogo de equipos.");
      setLoading(false);
    }
  };

  // --- FILTRADO SEGURO (PROTECCIÓN ANTI-CRASH) ---
  const filteredAssets = assets.filter(asset => {
    // Convertimos a string seguro antes de buscar (evita error toLowerCase on null)
    const name = (asset.equipment_name || "").toLowerCase();
    const unit = (asset.unit_id || "").toLowerCase();
    const type = (asset.equipment_type || "").toLowerCase();
    const id = (asset.equipment_id || "").toLowerCase();
    
    const searchTerm = filter.toLowerCase();

    return name.includes(searchTerm) || 
           unit.includes(searchTerm) || 
           type.includes(searchTerm) ||
           id.includes(searchTerm);
  });

  if (loading) return (
    <div className="page-container" style={{display:'flex', justifyContent:'center', alignItems:'center', height:'80vh', flexDirection:'column'}}>
      <div className="spinner" style={{marginBottom:'20px'}}></div>
      <p style={{color:'#64748b'}}>Cargando Inventario de Planta...</p>
    </div>
  );

  return (
    <div className="page-container">
      {/* HEADER */}
      <div className="page-header">
        <div className="page-title">
          <h1>Inventario de Activos</h1>
          <p>Monitorización detallada de equipos y sensores en tiempo real</p>
        </div>
        <div className="status-badge status-success">
          <FiServer style={{ marginRight: '8px' }} />
          {assets.length} Equipos Registrados
        </div>
      </div>

      {error && (
        <div className="card" style={{borderLeft:'4px solid #ef4444', color:'#ef4444', display:'flex', alignItems:'center', gap:'10px', marginBottom:'20px'}}>
          <FiAlertTriangle/> {error}
        </div>
      )}

      {/* PANEL PRINCIPAL */}
      <div className="card" style={{padding:'0', overflow:'hidden'}}>
        
        {/* BARRA DE BÚSQUEDA */}
        <div className="card-header" style={{background:'#f8fafc', borderBottom:'1px solid #e2e8f0', padding:'15px'}}>
          <div className="search-box" style={{ position: 'relative', maxWidth: '400px', width: '100%' }}>
            <FiSearch style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input 
              type="text" 
              placeholder="Buscar por nombre, ID, tipo o unidad..." 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{
                width: '100%', padding: '10px 10px 10px 38px', borderRadius: '8px', 
                border: '1px solid #cbd5e1', outline: 'none', fontSize: '0.9rem'
              }}
            />
          </div>
        </div>
        
        {/* TABLA DE ACTIVOS */}
        <div className="table-container">
          <table className="modern-table" style={{width:'100%'}}>
            <thead>
              <tr style={{background:'#f1f5f9'}}>
                <th style={{padding:'15px', textAlign:'left'}}>Equipo / ID</th>
                <th style={{padding:'15px', textAlign:'left'}}>Tipo</th>
                <th style={{padding:'15px', textAlign:'left'}}>Ubicación</th>
                <th style={{padding:'15px', textAlign:'left'}}>Estado</th>
                <th style={{padding:'15px', textAlign:'left'}}>Lecturas (Sensores)</th>
              </tr>
            </thead>
            <tbody>
              {filteredAssets.length > 0 ? filteredAssets.map((asset, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #f1f5f9'}}>
                  {/* Columna Nombre */}
                  <td style={{padding:'15px'}}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ 
                        background: '#eff6ff', padding: '10px', borderRadius: '8px', 
                        color: '#3b82f6', display:'flex', alignItems:'center', justifyContent:'center'
                      }}>
                        <FiBox size={18} />
                      </div>
                      <div>
                        <div style={{fontWeight: 700, color: '#1e293b'}}>
                          {asset.equipment_name || "Equipo Sin Nombre"}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'monospace', marginTop:'2px' }}>
                          ID: {asset.equipment_id || "N/A"}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Columna Tipo */}
                  <td style={{padding:'15px'}}>
                    <span className="badge-pro" style={{ 
                      background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0', 
                      padding:'4px 8px', borderRadius:'6px', fontSize:'0.8rem', fontWeight:600 
                    }}>
                      {asset.equipment_type || "GENÉRICO"}
                    </span>
                  </td>

                  {/* Columna Ubicación */}
                  <td style={{padding:'15px'}}>
                    <strong style={{ color: '#334155' }}>{asset.unit_id || "PLANTA"}</strong>
                  </td>

                  {/* Columna Estado */}
                  <td style={{padding:'15px'}}>
                    {asset.status === 'OPERATIONAL' ? (
                      <span className="status-badge status-success" style={{display:'inline-flex', alignItems:'center', gap:'5px'}}>
                        <FiCheckCircle /> Operativo
                      </span>
                    ) : (
                      <span className="status-badge status-warning" style={{display:'inline-flex', alignItems:'center', gap:'5px'}}>
                        <FiTool /> Mantenimiento
                      </span>
                    )}
                  </td>

                  {/* Columna Sensores (Manejo Seguro de Arrays) */}
                  <td style={{padding:'15px'}}>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {asset.sensors && Array.isArray(asset.sensors) && asset.sensors.length > 0 ? (
                        asset.sensors.map((sensor, sIdx) => (
                          <div key={sIdx} style={{ 
                            padding: '6px 10px', background: '#ffffff', borderRadius: '6px', 
                            border: '1px solid #e2e8f0', minWidth: '110px',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                          }}>
                            <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '2px', display:'flex', alignItems:'center', gap:'4px' }}>
                              <FiActivity size={10}/> {sensor.tag_name || "TAG"}
                            </div>
                            <div style={{ fontWeight: 700, color: '#0f172a', fontSize: '0.9rem' }}>
                              {sensor.value !== null ? Number(sensor.value).toFixed(2) : '--'} 
                              <span style={{ fontSize: '0.75rem', fontWeight: 400, marginLeft: '3px', color: '#94a3b8' }}>
                                {sensor.units}
                              </span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <span style={{ color: '#94a3b8', fontSize: '0.85rem', fontStyle: 'italic', display:'flex', alignItems:'center', gap:'5px' }}>
                          <FiActivity style={{opacity:0.5}}/> Sin lecturas
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '4rem', color: '#94a3b8' }}>
                    <FiSearch size={30} style={{marginBottom:'10px', opacity:0.5}}/>
                    <p>No se encontraron equipos que coincidan con la búsqueda.</p>
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

export default Assets;