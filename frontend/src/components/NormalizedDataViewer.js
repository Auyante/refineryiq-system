import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FiDatabase, FiPackage, FiTag, FiCpu, FiTrendingUp,
  FiAlertTriangle, FiZap, FiBarChart2, FiList, FiGrid,
  FiCheck, FiX, FiAlertCircle, FiThermometer, FiDroplet,
  FiClock, FiActivity
} from 'react-icons/fi';
import { API_URL } from '../config'; // Asegúrate que la ruta sea correcta
import axios from 'axios';
const NormalizedDataViewer = () => {
  const [activeTab, setActiveTab] = useState('units');
  const [units, setUnits] = useState([]);
  const [tags, setTags] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [enrichedData, setEnrichedData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // 1. Obtener estadísticas (Fíjate en las comillas invertidas ` `)
      const statsResponse = await axios.get(`${API_URL}/api/normalized/stats`);
      setStats(statsResponse.data);

      // 2. Obtener datos según la pestaña activa
      switch (activeTab) {
        case 'units':
          const unitsResponse = await axios.get(`${API_URL}/api/normalized/units`);
          setUnits(unitsResponse.data);
          break;
        case 'tags':
          const tagsResponse = await axios.get(`${API_URL}/api/normalized/tags`);
          setTags(tagsResponse.data);
          break;
        case 'equipment':
          const eqResponse = await axios.get(`${API_URL}/api/normalized/equipment`);
          setEquipment(eqResponse.data);
          break;
        case 'enriched':
          const enrichedResponse = await axios.get(`${API_URL}/api/normalized/process-data/enriched?limit=50`);
          setEnrichedData(enrichedResponse.data);
          break;
        case 'stats':
          break;
        default:
          break;
    }
// ... resto del código ...
    } catch (error) {
      console.error('Error fetching normalized data:', error);
      setError('No se pudo conectar a la API normalizada. ¿Ejecutaste la migración?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const tabs = [
    { id: 'units', name: 'Unidades', icon: <FiPackage />, color: '#3B82F6' },
    { id: 'tags', name: 'Variables', icon: <FiTag />, color: '#10B981' },
    { id: 'equipment', name: 'Equipos', icon: <FiCpu />, color: '#8B5CF6' },
    { id: 'enriched', name: 'Datos Enriquecidos', icon: <FiDatabase />, color: '#F59E0B' },
    { id: 'stats', name: 'Estadísticas', icon: <FiBarChart2 />, color: '#EF4444' },
  ];

  const renderUnitsTable = () => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Tipo</th>
            <th>Capacidad</th>
            <th>Estado</th>
            <th>Descripción</th>
          </tr>
        </thead>
        <tbody>
          {units.map(unit => (
            <tr key={unit.unit_id}>
              <td><strong style={{ color: '#1F2937' }}>{unit.unit_id}</strong></td>
              <td>{unit.unit_name}</td>
              <td>
                <span style={{
                  padding: '4px 8px',
                  background: '#E0E7FF',
                  color: '#3730A3',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: '600'
                }}>
                  {unit.unit_type}
                </span>
              </td>
              <td>{unit.capacity ? `${unit.capacity.toLocaleString()} bbl/d` : 'N/A'}</td>
              <td>
                <span style={{
                  padding: '4px 12px',
                  background: unit.status === 'ACTIVE' ? '#D1FAE5' : '#FEE2E2',
                  color: unit.status === 'ACTIVE' ? '#065F46' : '#991B1B',
                  borderRadius: '20px',
                  fontSize: '12px',
                  fontWeight: '600'
                }}>
                  {unit.status}
                </span>
              </td>
              <td style={{ color: '#6B7280', fontSize: '14px' }}>{unit.description || 'Sin descripción'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderTagsTable = () => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Unidad</th>
            <th>Tipo</th>
            <th>Unidades</th>
            <th>Crítico</th>
          </tr>
        </thead>
        <tbody>
          {tags.map(tag => (
            <tr key={tag.tag_id}>
              <td><code style={{ background: '#F3F4F6', padding: '2px 6px', borderRadius: '4px' }}>{tag.tag_id}</code></td>
              <td>{tag.tag_name}</td>
              <td><strong>{tag.unit_id}</strong></td>
              <td>
                <span style={{
                  padding: '4px 8px',
                  background: '#FEF3C7',
                  color: '#92400E',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: '600'
                }}>
                  {tag.tag_type || 'GENERAL'}
                </span>
              </td>
              <td>{tag.engineering_units || 'N/A'}</td>
              <td>
                {tag.is_critical ? (
                  <span style={{
                    padding: '4px 8px',
                    background: '#FEE2E2',
                    color: '#991B1B',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: '700'
                  }}>
                    CRÍTICO
                  </span>
                ) : (
                  <span style={{ color: '#6B7280' }}>No</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderEquipmentTable = () => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Tipo</th>
            <th>Unidad</th>
            <th>Estado</th>
            <th>Fabricante</th>
          </tr>
        </thead>
        <tbody>
          {equipment.map(eq => (
            <tr key={eq.equipment_id}>
              <td><code style={{ background: '#F3F4F6', padding: '2px 6px', borderRadius: '4px' }}>{eq.equipment_id}</code></td>
              <td>{eq.equipment_name}</td>
              <td>
                <span style={{
                  padding: '4px 8px',
                  background: '#E0E7FF',
                  color: '#3730A3',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: '600'
                }}>
                  {eq.equipment_type}
                </span>
              </td>
              <td><strong>{eq.unit_id}</strong></td>
              <td>
                <span style={{
                  padding: '4px 12px',
                  background: eq.status === 'OPERATIONAL' ? '#D1FAE5' : '#FEE2E2',
                  color: eq.status === 'OPERATIONAL' ? '#065F46' : '#991B1B',
                  borderRadius: '20px',
                  fontSize: '12px',
                  fontWeight: '600'
                }}>
                  {eq.status}
                </span>
              </td>
              <td>{eq.manufacturer || 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderEnrichedData = () => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Unidad</th>
            <th>Variable</th>
            <th>Valor</th>
            <th>Unidades</th>
            <th>Calidad</th>
          </tr>
        </thead>
        <tbody>
          {enrichedData.slice(0, 30).map((row, index) => (
            <tr key={index}>
              <td style={{ fontSize: '12px', color: '#6B7280' }}>
                {new Date(row.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </td>
              <td>
                <div>
                  <strong>{row.unit_id}</strong>
                  <div style={{ fontSize: '12px', color: '#6B7280' }}>{row.unit_name}</div>
                </div>
              </td>
              <td>
                <div>
                  <code style={{ fontSize: '12px' }}>{row.tag_id}</code>
                  <div style={{ fontSize: '12px', color: '#6B7280' }}>{row.tag_name}</div>
                </div>
              </td>
              <td>
                <span style={{
                  fontFamily: "'Consolas', 'Monaco', monospace",
                  fontWeight: '600',
                  color: '#1F2937'
                }}>
                  {typeof row.value === 'number' ? row.value.toFixed(2) : row.value}
                </span>
              </td>
              <td>{row.engineering_units || '-'}</td>
              <td>
                <span style={{
                  padding: '4px 8px',
                  background: row.quality === 1 ? '#D1FAE5' : '#FEF3C7',
                  color: row.quality === 1 ? '#065F46' : '#92400E',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: '500'
                }}>
                  {row.quality === 1 ? '✓ Buena' : '⚠️ Dudosa'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderStats = () => {
    if (!stats) return null;
    
    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: '1rem',
        marginTop: '1rem'
      }}>
        {[
          { label: 'Unidades Totales', value: stats.total_units || 0, sub: `${stats.active_units || 0} activas`, icon: <FiPackage />, color: '#3B82F6' },
          { label: 'Variables', value: stats.total_tags || 0, sub: 'Monitoreadas', icon: <FiTag />, color: '#10B981' },
          { label: 'Equipos', value: stats.total_equipment || 0, sub: `${stats.operational_equipment || 0} operacionales`, icon: <FiCpu />, color: '#8B5CF6' },
          { label: 'Registros', value: `${((stats.total_process_records || 0) / 1000).toFixed(1)}k`, sub: `${stats.process_records_today || 0} hoy`, icon: <FiDatabase />, color: '#F59E0B' },
          { label: 'Alertas', value: stats.total_alerts || 0, sub: `${stats.active_alerts || 0} activas`, icon: <FiAlertTriangle />, color: '#EF4444' },
          { label: 'Normalizada', value: stats.database_normalized ? '✅' : '❌', sub: '3FN Implementada', icon: <FiCheck />, color: '#06B6D4' },
        ].map((stat, idx) => (
          <div key={idx} style={{
            background: '#F9FAFB',
            border: '1px solid #E5E7EB',
            borderRadius: '10px',
            padding: '1.5rem',
            textAlign: 'center',
            transition: 'transform 0.2s'
          }}>
            <div style={{ fontSize: '2rem', color: stat.color, marginBottom: '0.5rem' }}>
              {stat.icon}
            </div>
            <div style={{ fontSize: '2rem', fontWeight: '700', color: '#1F2937', margin: '0.5rem 0' }}>
              {stat.value}
            </div>
            <div style={{ fontSize: '0.9rem', color: '#4B5563', fontWeight: '500' }}>
              {stat.label}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#6B7280', marginTop: '0.25rem' }}>
              {stat.sub}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (error) {
    return (
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '2rem',
        boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        marginBottom: '2rem',
        border: '1px solid #E5E7EB'
      }}>
        <div style={{ color: '#EF4444', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
          <FiAlertCircle size={24} />
          <h2 style={{ color: '#1F2937', fontSize: '1.5rem' }}>Error de Normalización</h2>
        </div>
        <p style={{ color: '#6B7280', marginBottom: '1.5rem' }}>{error}</p>
        <div style={{ background: '#FEF3C7', padding: '1rem', borderRadius: '8px', border: '1px solid #F59E0B' }}>
          <strong style={{ color: '#92400E' }}>Solución:</strong>
          <ol style={{ marginTop: '0.5rem', paddingLeft: '1.5rem', color: '#92400E' }}>
            <li>Ejecuta primero: <code>python normalization_migration.py</code></li>
            <li>Actualiza tu <code>main.py</code> con los nuevos endpoints</li>
            <li>Reinicia el backend: <code>python main.py</code></li>
          </ol>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      background: 'white',
      borderRadius: '12px',
      padding: '1.5rem',
      boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
      marginBottom: '2rem',
      border: '1px solid #E5E7EB'
    }}>
      <div style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '2px solid #F3F4F6' }}>
        <h2 style={{ color: '#1F2937', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '0.5rem' }}>
          <FiDatabase /> Base de Datos Normalizada (3FN)
        </h2>
        <p style={{ color: '#6B7280', fontSize: '0.95rem' }}>
          Estructura relacional normalizada con integridad referencial
        </p>
      </div>
      
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        borderBottom: '1px solid #E5E7EB',
        paddingBottom: '1rem'
      }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '0.5rem 1rem',
              background: activeTab === tab.id ? tab.color : '#F9FAFB',
              border: `1px solid ${activeTab === tab.id ? tab.color : '#E5E7EB'}`,
              borderRadius: '8px',
              fontSize: '0.9rem',
              fontWeight: '500',
              color: activeTab === tab.id ? 'white' : '#4B5563',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            {tab.icon} {tab.name}
          </button>
        ))}
      </div>
      
      <div>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '3px solid #E5E7EB',
              borderTopColor: '#3B82F6',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              marginBottom: '1rem'
            }}></div>
            <p style={{ color: '#6B7280' }}>Cargando datos normalizados...</p>
          </div>
        ) : (
          <>
            {activeTab === 'units' && renderUnitsTable()}
            {activeTab === 'tags' && renderTagsTable()}
            {activeTab === 'equipment' && renderEquipmentTable()}
            {activeTab === 'enriched' && renderEnrichedData()}
            {activeTab === 'stats' && renderStats()}
          </>
        )}
      </div>
      
      <div style={{
        marginTop: '1.5rem',
        paddingTop: '1rem',
        borderTop: '1px solid #F3F4F6',
        color: '#6B7280',
        fontSize: '0.9rem'
      }}>
        <p>
          <strong>Base de datos normalizada:</strong> Elimina redundancias, 
          asegura integridad referencial y mejora el rendimiento de consultas.
        </p>
      </div>
      
      <style>
        {`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
          
          .table-container {
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
          }
          
          .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
          }
          
          .data-table thead {
            background: #F9FAFB;
            position: sticky;
            top: 0;
          }
          
          .data-table th {
            padding: 0.75rem 1rem;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #E5E7EB;
            white-space: nowrap;
          }
          
          .data-table td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #F3F4F6;
            vertical-align: top;
          }
          
          .data-table tr:hover {
            background: #F8FAFC;
          }
          
          @media (max-width: 768px) {
            .data-table {
              font-size: 0.8rem;
            }
            
            .data-table th,
            .data-table td {
              padding: 0.5rem;
            }
          }
        `}
      </style>
    </div>
  );
};

export default NormalizedDataViewer;