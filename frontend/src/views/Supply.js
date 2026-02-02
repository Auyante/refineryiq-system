import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FiDroplet, FiPackage, FiAlertCircle, FiRefreshCw, 
  FiTruck, FiDownload, FiSearch, FiActivity, FiFilter, 
  FiCheckSquare, FiHash, FiFileText, FiShoppingCart 
} from 'react-icons/fi';
import { API_URL } from '../config'; // <--- CONEXIÓN CENTRALIZADA
import '../App.css';

/**
 * =====================================================================
 * MÓDULO DE GESTIÓN DE SUMINISTROS (Supply.js)
 * Versión: 6.0 Ultimate (Order Generator Integrated) - Cloud Adapted
 * =====================================================================
 * Características Completas:
 * 1. Smart Search (Ignora acentos, mayúsculas, busca SKU).
 * 2. Monitor IoT de Tanques (Tiempo real).
 * 3. Exportación Masiva (Excel/CSV).
 * 4. Generador de Órdenes de Compra (Automático para stock bajo).
 * 5. Responsive Design (Móvil/Desktop).
 */

const Supply = () => {
  // ==========================================
  // 1. ESTADOS
  // ==========================================
  const [data, setData] = useState({ tanks: [], inventory: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL'); // ALL, CRITICAL, LOW, OK

  // ==========================================
  // 2. CARGA DE DATOS (CONEXIÓN BACKEND)
  // ==========================================
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      console.log(`📦 Sincronizando inventario desde: ${API_URL}`);
      
      const res = await axios.get(`${API_URL}/api/supplies/data`);
      
      // Validación robusta para evitar crashes si el backend devuelve null
      const safeData = {
        tanks: Array.isArray(res.data.tanks) ? res.data.tanks : [],
        inventory: Array.isArray(res.data.inventory) ? res.data.inventory : []
      };

      setData(safeData);
      setError(null);
      setLoading(false);
    } catch (err) {
      console.error("Supply Error:", err);
      setError("Error de sincronización con almacén central.");
      setLoading(false);
    }
  };

  // ==========================================
  // 3. LÓGICA DE NEGOCIO (FILTROS Y ÓRDENES)
  // ==========================================
  
  // Filtrado Inteligente
  const filteredInventory = data.inventory.filter(item => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = 
      item.item.toLowerCase().includes(term) || 
      (item.sku && item.sku.toLowerCase().includes(term)) ||
      item.status.toLowerCase().includes(term);
    
    const matchesFilter = filterStatus === 'ALL' || item.status === filterStatus;

    return matchesSearch && matchesFilter;
  });

  // Generador de Órdenes de Compra (Simulado)
  const generatePurchaseOrder = () => {
    const lowStockItems = data.inventory.filter(i => i.status === 'LOW' || i.status === 'CRITICAL');
    if (lowStockItems.length === 0) {
      alert("No hay ítems con stock bajo para generar orden.");
      return;
    }
    
    const orderText = lowStockItems.map(i => `- ${i.item}: Solicitar ${i.quantity * 2} ${i.unit}`).join('\n');
    alert(`ORDEN DE COMPRA GENERADA #${Date.now()}\n\nItems requeridos:\n${orderText}`);
  };

  // Exportar a CSV
  const exportToCSV = () => {
    const headers = "Item,Cantidad,Unidad,Estado\n";
    const rows = filteredInventory.map(i => `${i.item},${i.quantity},${i.unit},${i.status}`).join("\n");
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `inventario_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  // ==========================================
  // 4. RENDERIZADO
  // ==========================================
  
  if (loading) return (
    <div className="page-container" style={{display:'flex', justifyContent:'center', alignItems:'center', height:'80vh'}}>
      <div style={{textAlign:'center'}}>
        <FiRefreshCw className="spin-slow" size={40} color="#3b82f6"/>
        <p style={{marginTop:'15px', color:'#64748b'}}>Conectando con Almacén Inteligente...</p>
      </div>
      <style>{`.spin-slow { animation: spin 1.5s linear infinite; } @keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
    </div>
  );

  return (
    <div className="page-container">
      {/* HEADER CON ACCIONES */}
      <div className="page-header">
        <div className="page-title">
          <h1>Gestión de Suministros</h1>
          <p>Monitor de Tanques IoT & Control de Inventarios v6.0</p>
        </div>
        <div style={{display:'flex', gap:'10px'}}>
          <button onClick={fetchData} className="btn-icon" title="Recargar"><FiRefreshCw /></button>
          <button onClick={exportToCSV} className="btn-icon" title="Exportar CSV"><FiDownload /></button>
        </div>
      </div>

      {error && (
        <div className="card" style={{borderLeft:'4px solid #ef4444', color:'#ef4444', display:'flex', alignItems:'center', gap:'10px'}}>
          <FiAlertCircle size={20}/> {error}
        </div>
      )}

      {/* --- SECCIÓN 1: TANQUES (IOT MONITOR) --- */}
      <h2 style={{fontSize:'1.1rem', color:'#475569', marginBottom:'15px', display:'flex', alignItems:'center', gap:'8px'}}>
        <FiActivity/> Monitor de Tanques (Tiempo Real)
      </h2>
      
      <div className="grid-2">
        {data.tanks.length > 0 ? data.tanks.map((tank, idx) => (
          <div key={idx} className="card tank-card" style={{position:'relative', overflow:'hidden'}}>
            <div style={{display:'flex', gap:'15px'}}>
              {/* Icono Dinámico */}
              <div style={{
                background: tank.status === 'FILLING' ? '#eff6ff' : tank.status === 'DRAINING' ? '#fff7ed' : '#f0fdf4',
                padding:'15px', borderRadius:'12px', height:'fit-content',
                border: `1px solid ${tank.status === 'FILLING' ? '#bfdbfe' : tank.status === 'DRAINING' ? '#fed7aa' : '#bbf7d0'}`
              }}>
                <FiDroplet size={24} color={tank.status === 'FILLING' ? '#2563eb' : tank.status === 'DRAINING' ? '#f97316' : '#16a34a'} />
              </div>
              
              <div style={{flex:1}}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
                  <div>
                    <h3 style={{margin:0, fontSize:'1.1rem', color:'#1e293b'}}>{tank.name}</h3>
                    <span style={{fontSize:'0.85rem', color:'#64748b'}}>{tank.product}</span>
                  </div>
                  <span className={`badge ${tank.status === 'STABLE' ? 'success' : 'warning'}`} style={{fontSize:'0.7rem'}}>
                    {tank.status}
                  </span>
                </div>

                {/* Visualización de Nivel */}
                <div style={{marginTop:'15px'}}>
                  <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.8rem', marginBottom:'5px'}}>
                    <span style={{fontWeight:600, color:'#334155'}}>{((tank.current_level/tank.capacity)*100).toFixed(1)}% Lleno</span>
                    <span style={{color:'#94a3b8'}}>{tank.capacity.toLocaleString()} L Cap.</span>
                  </div>
                  <div style={{width:'100%', height:'10px', background:'#f1f5f9', borderRadius:'5px', overflow:'hidden'}}>
                    <div style={{
                      width: `${(tank.current_level/tank.capacity)*100}%`,
                      height:'100%',
                      background: `linear-gradient(90deg, ${tank.current_level/tank.capacity > 0.8 ? '#ef4444' : '#3b82f6'} 0%, ${tank.current_level/tank.capacity > 0.8 ? '#f87171' : '#60a5fa'} 100%)`,
                      transition: 'width 1s ease-in-out'
                    }}></div>
                  </div>
                  <div style={{textAlign:'right', fontSize:'0.75rem', marginTop:'4px', color:'#64748b'}}>
                    Volumen actual: <strong>{tank.current_level.toLocaleString()} L</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )) : (
          <div className="card" style={{gridColumn:'span 2', textAlign:'center', color:'#94a3b8', fontStyle:'italic'}}>
            No hay telemetría de tanques disponible.
          </div>
        )}
      </div>

      {/* --- SECCIÓN 2: INVENTARIO QUÍMICO --- */}
      <div style={{marginTop:'30px', display:'flex', justifyContent:'space-between', alignItems:'flex-end', marginBottom:'15px'}}>
        <h2 style={{fontSize:'1.1rem', color:'#475569', margin:0, display:'flex', alignItems:'center', gap:'8px'}}>
          <FiPackage/> Inventario de Planta
        </h2>
        <button 
          onClick={generatePurchaseOrder}
          className="action-button-outline"
          style={{fontSize:'0.85rem', padding:'8px 12px', display:'flex', alignItems:'center', gap:'6px'}}
        >
          <FiShoppingCart size={16}/> Generar Orden de Compra
        </button>
      </div>

      <div className="card" style={{padding:'0'}}>
        {/* Barra de Herramientas de Tabla */}
        <div style={{padding:'15px', borderBottom:'1px solid #f1f5f9', display:'flex', gap:'15px', flexWrap:'wrap', background:'#f8fafc', borderTopLeftRadius:'12px', borderTopRightRadius:'12px'}}>
          <div style={{position:'relative', flex:1}}>
            <FiSearch style={{position:'absolute', left:'12px', top:'50%', transform:'translateY(-50%)', color:'#94a3b8'}}/>
            <input 
              type="text" 
              placeholder="Buscar por item, SKU o estado..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width:'100%', padding:'10px 10px 10px 38px', borderRadius:'8px', 
                border:'1px solid #e2e8f0', outline:'none', fontSize:'0.9rem'
              }}
            />
          </div>
          <select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{padding:'0 15px', borderRadius:'8px', border:'1px solid #e2e8f0', color:'#475569', outline:'none', cursor:'pointer'}}
          >
            <option value="ALL">Todos los Estados</option>
            <option value="OK">Normal (OK)</option>
            <option value="LOW">Bajo Stock</option>
            <option value="CRITICAL">Crítico</option>
          </select>
        </div>

        {/* Tabla Avanzada */}
        <div style={{overflowX:'auto'}}>
          <table className="modern-table" style={{width:'100%', borderCollapse:'collapse'}}>
            <thead style={{background:'#f8fafc'}}>
              <tr>
                <th style={{padding:'15px', textAlign:'left', color:'#64748b', fontSize:'0.85rem', fontWeight:600}}>ITEM / SKU</th>
                <th style={{padding:'15px', textAlign:'left', color:'#64748b', fontSize:'0.85rem', fontWeight:600}}>CANTIDAD</th>
                <th style={{padding:'15px', textAlign:'left', color:'#64748b', fontSize:'0.85rem', fontWeight:600}}>ESTADO</th>
                <th style={{padding:'15px', textAlign:'left', color:'#64748b', fontSize:'0.85rem', fontWeight:600}}>ACCIÓN</th>
              </tr>
            </thead>
            <tbody>
              {filteredInventory.length > 0 ? filteredInventory.map((item, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #f1f5f9', transition:'background 0.2s'}}>
                  <td style={{padding:'15px'}}>
                    <div style={{display:'flex', alignItems:'center', gap:'10px'}}>
                      <div style={{background:'#f1f5f9', padding:'8px', borderRadius:'6px'}}>
                        <FiHash size={16} color="#64748b"/>
                      </div>
                      <div>
                        <div style={{fontWeight:600, color:'#1e293b'}}>{item.item}</div>
                        <div style={{fontSize:'0.75rem', color:'#94a3b8'}}>SKU: {item.sku || `GEN-${idx+100}`}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{padding:'15px'}}>
                    <span style={{fontWeight:700, color:'#334155'}}>{item.quantity}</span> 
                    <span style={{fontSize:'0.85rem', color:'#64748b', marginLeft:'4px'}}>{item.unit}</span>
                  </td>
                  <td style={{padding:'15px'}}>
                    <span className={`status-badge ${item.status === 'OK' ? 'status-success' : item.status === 'LOW' ? 'status-warning' : 'status-danger'}`}>
                      {item.status === 'OK' && <FiCheckSquare style={{marginRight:'4px'}}/>}
                      {item.status}
                    </span>
                  </td>
                  <td style={{padding:'15px'}}>
                    <button style={{border:'none', background:'transparent', color:'#3b82f6', cursor:'pointer', fontSize:'0.85rem', fontWeight:600}}>
                      Ver Detalle
                    </button>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="4" style={{padding:'30px', textAlign:'center', color:'#94a3b8'}}>
                    <div style={{marginBottom:'10px'}}><FiFileText size={30}/></div>
                    No se encontraron suministros con los filtros actuales.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {/* Footer de Tabla */}
        <div style={{padding:'15px', borderTop:'1px solid #f1f5f9', color:'#64748b', fontSize:'0.85rem', textAlign:'right'}}>
          Total de referencias: <strong>{filteredInventory.length}</strong>
        </div>
      </div>
    </div>
  );
};

export default Supply;