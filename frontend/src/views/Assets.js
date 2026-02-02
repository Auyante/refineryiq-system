import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiSearch, FiCheckCircle, FiTool } from 'react-icons/fi';
import '../App.css'; // Importando estilos globales
const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
const Assets = () => {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    // Conectando al endpoint de inventario
    axios.get(`${API_URL}/api/assets/overview`)
      .then(res => {
       setAssets(res.data);
        setLoading(false);
      })
      .catch(err => {
       console.error("Error cargando activos:", err);
        setLoading(false);
      });
  }, []);

  // Lógica de filtrado
  const filteredAssets = assets.filter(asset => 
    asset.equipment_name.toLowerCase().includes(filter.toLowerCase()) ||
    asset.unit_id.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Inventario de Activos</h1>
          <p>Monitorización detallada de equipos y sensores</p>
        </div>
        <div className="status-badge status-success">
          {assets.length} Equipos Conectados
        </div>
      </div>

      <div className="card">
        {/* Barra de Búsqueda */}
        <div style={{ paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-light)', marginBottom: '1.5rem' }}>
          <div style={{ position: 'relative', maxWidth: '400px' }}>
            <FiSearch style={{ position: 'absolute', left: '12px', top: '12px', color: '#9CA3AF' }} />
            <input 
              type="text" 
              placeholder="Buscar por nombre o unidad (ej: PUMP, CDU-101)..." 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{
                width: '100%', padding: '10px 10px 10px 40px', borderRadius: '8px', 
                border: '1px solid #E5E7EB', outline: 'none', fontSize: '0.95rem'
              }}
            />
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#6B7280' }}>Cargando inventario de planta...</div>
        ) : (
          <div className="table-container">
            <table className="modern-table">
              <thead>
                <tr>
                  <th>Equipo</th>
                  <th>Tipo</th>
                  <th>Ubicación</th>
                  <th>Estado</th>
                  <th>Lecturas en Tiempo Real</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.length > 0 ? filteredAssets.map((asset, idx) => (
                  <tr key={idx}>
                    <td>
                      <div style={{fontWeight: 600, color: 'var(--text-main)'}}>{asset.equipment_name}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6B7280' }}>ID: {asset.equipment_id}</div>
                    </td>
                    <td><span className="badge-pro bg-gray">{asset.equipment_type}</span></td>
                    <td><strong style={{ color: 'var(--accent)' }}>{asset.unit_id}</strong></td>
                    <td>
                      {asset.equipment_status === 'OPERATIONAL' ? (
                        <span className="status-badge status-success"><FiCheckCircle /> Operativo</span>
                      ) : (
                        <span className="status-badge status-warning"><FiTool /> Mantenimiento</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {asset.sensors && asset.sensors.length > 0 ? (
                          asset.sensors.map((sensor, sIdx) => (
                            <div key={sIdx} style={{ 
                              background: '#F3F4F6', padding: '6px 10px', borderRadius: '6px', 
                              border: '1px solid #E5E7EB', minWidth: '100px'
                            }}>
                              <div style={{ fontSize: '0.65rem', color: '#6B7280', textTransform: 'uppercase', marginBottom: '2px' }}>
                                {sensor.tag_name}
                              </div>
                              <div style={{ fontWeight: 700, color: '#1F2937', fontSize: '0.9rem' }}>
                                {typeof sensor.value === 'number' ? sensor.value.toFixed(1) : sensor.value} 
                                <span style={{ fontSize: '0.75rem', fontWeight: 400, marginLeft: '2px', color: '#6B7280' }}>
                                  {sensor.units}
                                </span>
                              </div>
                            </div>
                          ))
                        ) : (
                          <span style={{ color: '#9CA3AF', fontSize: '0.85rem', fontStyle: 'italic' }}>Sin sensores</span>
                        )}
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '2rem' }}>No se encontraron equipos</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Assets;