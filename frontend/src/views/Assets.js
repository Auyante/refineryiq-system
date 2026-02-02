import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiSearch, FiCheckCircle, FiTool, FiBox, FiActivity } from 'react-icons/fi';
import { API_URL } from '../config'; // <--- IMPORTACIÓN DE LA CONEXIÓN CENTRAL
import '../App.css'; 

const Assets = () => {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAssets = async () => {
      try {
        // Conectando al endpoint de inventario usando la URL dinámica
        console.log(`🛠️ Cargando activos desde: ${API_URL}`);
        const res = await axios.get(`${API_URL}/api/assets/overview`);
        
        // Validación de seguridad: Aseguramos que sea un array
        const safeData = Array.isArray(res.data) ? res.data : [];
        setAssets(safeData);
        setLoading(false);
      } catch (err) {
        console.error("Error cargando activos:", err);
        setError("No se pudo cargar el inventario de activos.");
        setLoading(false);
      }
    };

    fetchAssets();
  }, []);

  // Lógica de filtrado PROTEGIDA (Evita pantalla blanca)
  // Si equipment_name es null, usa "" para que .toLowerCase() no falle
  const filteredAssets = assets.filter(asset => {
    const name = asset.equipment_name || "";
    const unit = asset.unit_id || "";
    const type = asset.equipment_type || "";
    const searchTerm = filter.toLowerCase();

    return name.toLowerCase().includes(searchTerm) ||
           unit.toLowerCase().includes(searchTerm) ||
           type.toLowerCase().includes(searchTerm);
  });

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Inventario de Activos</h1>
          <p>Monitorización detallada de equipos y sensores</p>
        </div>
        <div className="status-badge status-success">
          <FiBox style={{ marginRight: '8px' }} />
          {assets.length} Equipos Totales
        </div>
      </div>

      <div className="card">
        {/* Barra de Búsqueda y Filtros */}
        <div className="card-header">
          <div className="search-box" style={{ position: 'relative', maxWidth: '400px', width: '100%' }}>
            <FiSearch style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9CA3AF' }} />
            <input 
              type="text" 
              placeholder="Buscar por nombre, ID o unidad..." 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="search-input"
              style={{
                width: '100%', padding: '10px 10px 10px 38px', borderRadius: '8px', 
                border: '1px solid #E5E7EB', outline: 'none', fontSize: '0.95rem'
              }}
            />
          </div>
        </div>
        
        {loading ? (
          <div style={{ padding: '4rem', textAlign: 'center', color: '#6B7280' }}>
            <div className="spinner" style={{margin: '0 auto 1rem'}}></div>
            Cargando inventario de planta...
          </div>
        ) : error ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#EF4444' }}>
            {error}
          </div>
        ) : (
          <div className="table-container">
            <table className="modern-table">
              <thead>
                <tr>
                  <th>Equipo</th>
                  <th>Tipo</th>
                  <th>Ubicación</th>
                  <th>Estado Operativo</th>
                  <th>Lecturas en Tiempo Real</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.length > 0 ? filteredAssets.map((asset, idx) => (
                  <tr key={idx}>
                    {/* Columna Nombre */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ 
                          background: '#F3F4F6', padding: '10px', borderRadius: '8px', 
                          color: '#4B5563'
                        }}>
                          <FiBox size={18} />
                        </div>
                        <div>
                          <div style={{fontWeight: 600, color: 'var(--text-main)'}}>
                            {asset.equipment_name || "Sin Nombre"}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#6B7280', fontFamily: 'monospace' }}>
                            ID: {asset.equipment_id}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Columna Tipo */}
                    <td>
                      <span className="badge-pro" style={{ background: '#EFF6FF', color: '#1D4ED8', border: '1px solid #DBEAFE' }}>
                        {asset.equipment_type}
                      </span>
                    </td>

                    {/* Columna Ubicación */}
                    <td>
                      <strong style={{ color: '#374151' }}>{asset.unit_id}</strong>
                    </td>

                    {/* Columna Estado */}
                    <td>
                      {asset.status === 'OPERATIONAL' ? (
                        <span className="status-badge status-success">
                          <FiCheckCircle /> Operativo
                        </span>
                      ) : (
                        <span className="status-badge status-warning">
                          <FiTool /> Mantenimiento
                        </span>
                      )}
                    </td>

                    {/* Columna Sensores (Datos Vivos) */}
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {asset.sensors && asset.sensors.length > 0 ? (
                          asset.sensors.map((sensor, sIdx) => (
                            <div key={sIdx} style={{ 
                              padding: '4px 8px', background: '#F9FAFB', borderRadius: '6px', 
                              border: '1px solid #E5E7EB', minWidth: '100px'
                            }}>
                              <div style={{ fontSize: '0.65rem', color: '#6B7280', textTransform: 'uppercase', marginBottom: '2px' }}>
                                <FiActivity style={{ marginRight: '4px', verticalAlign: 'middle' }} size={10}/>
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
                          <span style={{ color: '#9CA3AF', fontSize: '0.85rem', fontStyle: 'italic' }}>
                            Sin sensores conectados
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '3rem', color: '#9CA3AF' }}>
                      No se encontraron equipos que coincidan con "{filter}"
                    </td>
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