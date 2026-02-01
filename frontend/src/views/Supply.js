import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FiDroplet, FiPackage, FiAlertCircle, FiRefreshCw, 
  FiTruck, FiDownload, FiSearch, FiActivity, FiFilter, 
  FiCheckSquare, FiHash, FiFileText, FiShoppingCart 
} from 'react-icons/fi';
import '../App.css';

/**
 * =====================================================================
 * MÓDULO DE GESTIÓN DE SUMINISTROS (Supply.js)
 * Versión: 6.0 Ultimate (Order Generator Integrated)
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
  // 1. CONFIGURACIÓN DE RED (AUTO-DETECT)
  // ==========================================
  const PROTOCOL = window.location.protocol;
  const HOST = window.location.hostname;
  const PORT = '8000';
  const API_URL = `${PROTOCOL}//${HOST}:${PORT}`;

  // ==========================================
  // 2. ESTADOS
  // ==========================================
  const [data, setData] = useState({ tanks: [], inventory: [] });
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  
  // Estado del Buscador
  const [searchTerm, setSearchTerm] = useState('');

  // ==========================================
  // 3. CARGA DE DATOS
  // ==========================================
  const loadSupplyData = () => {
    axios.get(`${API_URL}/api/supplies/data`)
      .then(res => {
        setData(res.data);
        if (loading) setLoading(false);
        setLastUpdate(new Date());
      })
      .catch(err => {
        console.error("Error crítico cargando suministros:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadSupplyData();
    const interval = setInterval(loadSupplyData, 3000); 
    return () => clearInterval(interval);
  }, [API_URL]);

  // ==========================================
  // 4. FUNCIONALIDAD: EXPORTAR A EXCEL (CSV)
  // ==========================================
  const downloadCSV = () => {
    console.log("Generando reporte CSV...");
    const dateStr = new Date().toLocaleString();
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "TIPO,SKU,NOMBRE,CATEGORIA,CANTIDAD,NIVEL_MINIMO,ESTADO,UBICACION,FECHA\n";

    data.tanks.forEach(t => {
      csvContent += `TANQUE,TK-${t.id},${t.name} (${t.product}),FLUIDOS,${t.current_level} L,N/A,${t.status},PATIO,${dateStr}\n`;
    });

    data.inventory.forEach(i => {
      const sku = `RE-${1000 + i.id}`;
      const status = i.quantity <= i.min_level ? 'CRITICO' : 'NORMAL';
      csvContent += `REPUESTO,${sku},${i.item_name},${i.category},${i.quantity},${i.min_level},${status},${i.location},${dateStr}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Inventario_RefineryIQ_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // ==========================================
  // 5. FUNCIONALIDAD: GENERAR ORDEN DE COMPRA
  // ==========================================
  const generatePurchaseOrder = () => {
    // 1. Filtrar solo los ítems críticos
    const criticalItems = data.inventory.filter(item => item.quantity <= item.min_level);

    if (criticalItems.length === 0) {
      alert("✅ Inventario Saludable: No hay ítems por debajo del mínimo. No se requiere orden de compra.");
      return;
    }

    // 2. Construir el contenido del archivo de texto (Formato carta formal)
    let content = "================================================\n";
    content += "       ORDEN DE COMPRA AUTOMÁTICA - REFINERY IQ\n";
    content += "================================================\n\n";
    content += `FECHA DE EMISIÓN: ${new Date().toLocaleString()}\n`;
    content += `SOLICITANTE: Sistema de Gestión de Suministros (Módulo IA)\n`;
    content += `PRIORIDAD: ALTA (Stock Crítico detectado)\n\n`;
    
    content += "DETALLE DE REQUERIMIENTOS:\n";
    content += "----------------------------------------------------------------------\n";
    content += "SKU       | DESCRIPCIÓN                | STOCK ACTUAL | CANTIDAD A PEDIR\n";
    content += "----------------------------------------------------------------------\n";

    criticalItems.forEach(item => {
      const sku = `RE-${1000 + item.id}`;
      // Lógica de pedido: Pedir lo necesario para llegar al doble del mínimo (Stock de seguridad)
      const quantityToOrder = (item.min_level * 2) - item.quantity;
      
      // Formateo de espacios para que se vea alineado en el TXT
      const skuPad = sku.padEnd(9, ' ');
      const namePad = item.item_name.substring(0, 25).padEnd(26, ' ');
      const stockPad = item.quantity.toString().padEnd(12, ' ');
      
      content += `${skuPad} | ${namePad} | ${stockPad} | ${quantityToOrder} Uds.\n`;
    });

    content += "----------------------------------------------------------------------\n\n";
    content += "NOTAS ADICIONALES:\n";
    content += "- Favor confirmar fecha de entrega antes de 48 horas.\n";
    content += "- Entregar en Almacén Central, Muelle de Carga B.\n\n";
    content += "___________________________\n";
    content += "Firma Autorizada Digitalmente";

    // 3. Descargar el archivo .txt
    const element = document.createElement("a");
    const file = new Blob([content], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = `Orden_Compra_Urgente_${Date.now()}.txt`;
    document.body.appendChild(element);
    element.click();
    
    // 4. Feedback al usuario
    alert(`🚀 Orden de compra generada exitosamente para ${criticalItems.length} ítems críticos.`);
  };

  // ==========================================
  // 6. MOTOR DE BÚSQUEDA INTELIGENTE
  // ==========================================
  const normalizeText = (text) => {
    if (!text) return "";
    return text.toString().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  };

  const filteredInventory = data.inventory.filter(item => {
    const term = normalizeText(searchTerm);
    if (!term) return true;
    const name = normalizeText(item.item_name);
    const category = normalizeText(item.category);
    const location = normalizeText(item.location);
    const sku = normalizeText(`RE-${1000 + item.id}`);
    return name.includes(term) || category.includes(term) || location.includes(term) || sku.includes(term);
  });

  // ==========================================
  // 7. RENDERIZADO VISUAL
  // ==========================================
  return (
    <div className="page-container">
      
      {/* HEADER */}
      <div className="page-header">
        <div className="page-title">
          <h1>Gestión de Suministros</h1>
          <p>Monitor de niveles de tanques y control de stock en almacenes</p>
        </div>
        
        <div className="control-panel-top">
          <button onClick={downloadCSV} className="btn-export" title="Descargar Excel">
            <FiDownload /> <span>Exportar Data</span>
          </button>
          <div className="update-badge">
            <FiRefreshCw className={loading ? 'spin' : ''} />
            <span className="hide-mobile">Sincronizado:</span> {lastUpdate.toLocaleTimeString()}
          </div>
        </div>

        <style>{`
          .control-panel-top { display: flex; gap: 12px; align-items: center; }
          .btn-export {
            display: flex; align-items: center; gap: 8px; padding: 10px 16px;
            background: white; border: 1px solid #e2e8f0; border-radius: 8px;
            cursor: pointer; font-weight: 600; color: #1e293b;
            transition: all 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
          }
          .btn-export:hover { background: #f8fafc; border-color: #cbd5e1; transform: translateY(-1px); }
          .update-badge {
            display: flex; align-items: center; gap: 8px; font-size: 0.8rem;
            color: #64748b; background: #f1f5f9; padding: 8px 14px;
            border-radius: 20px; border: 1px solid #e2e8f0;
          }
          .spin { animation: spin 1s linear infinite; } 
          @keyframes spin { 100% { transform: rotate(360deg); } }
          
          .mobile-stack { display: grid; grid-template-columns: 1fr; gap: 1.5rem; }
          @media (min-width: 1024px) { .mobile-stack { grid-template-columns: 4fr 3fr; } }
          @media (max-width: 640px) { 
            .hide-mobile { display: none; } 
            .page-header { flex-direction: column; align-items: flex-start; gap: 15px; }
            .control-panel-top { width: 100%; justify-content: space-between; }
          }
        `}</style>
      </div>

      <div className="mobile-stack">
        
        {/* ==========================================
            SECCIÓN A: PATIO DE TANQUES
           ========================================== */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiDroplet /> Patio de Tanques</h3>
            <span className="badge-pro" style={{background:'#eff6ff', color:'#1d4ed8'}}>Sensores IoT</span>
          </div>
          
          {loading && data.tanks.length === 0 ? (
            <div style={{padding:'50px', textAlign:'center', color:'#9ca3af'}}>
              <FiActivity className="spin" size={30} style={{marginBottom:'10px'}}/> 
              <div>Conectando con sensores...</div>
            </div>
          ) : (
            <div style={{display: 'flex', flexDirection: 'column', gap: '28px'}}>
              {data.tanks.map((tank, idx) => {
                const pct = (tank.current_level / tank.capacity) * 100;
                let barColor = '#3b82f6'; let statusColor = '#2563eb'; let isStriped = false;
                
                if (pct > 92) { barColor = '#ef4444'; statusColor = '#b91c1c'; isStriped = true; } 
                else if (pct < 15) { barColor = '#f59e0b'; statusColor = '#b45309'; isStriped = true; } 
                else if (tank.status === 'FILLING') { barColor = '#10b981'; statusColor='#047857'; }

                const stripeGradient = 'linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent)';

                return (
                  <div key={idx} style={{position: 'relative'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '8px', flexWrap: 'wrap', gap: '10px'}}>
                      <div style={{minWidth: '140px'}}>
                        <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
                          <strong style={{fontSize: '1rem', color: '#1e293b'}}>{tank.name}</strong>
                          {tank.status !== 'STATIC' && (
                            <span className="badge-pro" style={{fontSize:'0.65rem', padding:'2px 6px', background: statusColor, color: 'white', border:'none'}}>
                              {tank.status === 'FILLING' ? 'ENTRADA' : 'SALIDA'}
                            </span>
                          )}
                        </div>
                        <span style={{fontSize: '0.8rem', color: '#64748b', fontWeight: 500}}>Contenido: {tank.product}</span>
                      </div>
                      <div style={{textAlign: 'right', flexGrow: 1}}>
                        <div style={{fontWeight: 700, color: '#0f172a', fontSize: '1.1rem', fontFamily:'monospace'}}>
                          {tank.current_level.toLocaleString('es-ES')} <span style={{fontSize:'0.8rem', color:'#94a3b8', fontWeight:400}}>L</span>
                        </div>
                        <span style={{fontSize: '0.75rem', color: statusColor, fontWeight: 700, textTransform: 'uppercase'}}>{pct.toFixed(1)}% Capacidad</span>
                      </div>
                    </div>
                    <div style={{width: '100%', height: '34px', background: '#f8fafc', borderRadius: '8px', position: 'relative', overflow: 'hidden', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0'}}>
                      <div style={{width: `${pct}%`, height: '100%', background: barColor, backgroundImage: isStriped ? stripeGradient : 'none', backgroundSize: '1rem 1rem', transition: 'width 1s cubic-bezier(0.4, 0, 0.2, 1)', borderRadius: '6px', boxShadow: '2px 0 8px rgba(0,0,0,0.1)'}}></div>
                      <div style={{position: 'absolute', right: '12px', top: 0, bottom: 0, display: 'flex', alignItems: 'center', fontSize: '0.7rem', fontWeight: 800, color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.05em', textShadow: '0 0 10px rgba(255,255,255,0.8)', pointerEvents: 'none'}}>
                        {tank.status === 'STATIC' ? '● ESTÁTICO' : tank.status === 'FILLING' ? '▲ LLENANDO' : '▼ DRENANDO'}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* ==========================================
            SECCIÓN B: INVENTARIO (Búsqueda Avanzada)
           ========================================== */}
        <div className="card" style={{display: 'flex', flexDirection: 'column', overflow: 'hidden'}}>
          
          <div className="card-header" style={{flexWrap: 'wrap', gap: '15px', paddingBottom:'15px', borderBottom:'none'}}>
            <div style={{display:'flex', alignItems:'center', gap:'10px'}}>
               <h3 className="card-title"><FiPackage /> Inventario</h3>
               <span className="badge-pro" style={{fontSize:'0.7rem'}}>{filteredInventory.length} Items</span>
            </div>
            
            <div style={{position:'relative', marginLeft:'auto', flexGrow: 1, maxWidth:'300px', minWidth:'220px'}}>
              <FiSearch style={{position:'absolute', left:'12px', top:'50%', transform:'translateY(-50%)', color:'#94a3b8'}} />
              <input 
                type="text" 
                placeholder="Buscar SKU, nombre, cat..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width:'100%', padding:'12px 12px 12px 38px', borderRadius:'8px', 
                  border:'1px solid #e2e8f0', fontSize:'0.9rem', outline:'none',
                  background: '#f8fafc', transition: 'all 0.2s', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)'
                }}
                onFocus={(e) => {e.target.style.background='white'; e.target.style.borderColor='#3b82f6'; e.target.style.boxShadow='0 0 0 3px rgba(59,130,246,0.1)'}}
                onBlur={(e) => {e.target.style.background='#f8fafc'; e.target.style.borderColor='#e2e8f0'; e.target.style.boxShadow='inset 0 1px 2px rgba(0,0,0,0.02)'}}
              />
            </div>
          </div>
          
          <div style={{flex: 1, overflowX: 'auto', width: '100%', borderTop:'1px solid #f1f5f9'}}>
            <table className="modern-table" style={{width: '100%', minWidth: '600px'}}>
              <thead>
                <tr style={{background:'#f8fafc'}}>
                  <th style={{padding: '14px 16px', color:'#64748b', fontSize:'0.75rem', letterSpacing:'0.05em'}}>ITEM / SKU</th>
                  <th style={{padding: '14px 16px', color:'#64748b', fontSize:'0.75rem', letterSpacing:'0.05em'}}>CATEGORÍA</th>
                  <th style={{padding: '14px 16px', color:'#64748b', fontSize:'0.75rem', letterSpacing:'0.05em'}}>STOCK</th>
                  <th style={{padding: '14px 16px', color:'#64748b', fontSize:'0.75rem', letterSpacing:'0.05em'}}>UBICACIÓN</th>
                </tr>
              </thead>
              <tbody>
                {filteredInventory.length > 0 ? filteredInventory.map((item, idx) => {
                  const skuDisplay = `RE-${1000 + item.id}`; 
                  return (
                    <tr key={idx} style={{transition:'background 0.2s'}} className="table-row-hover">
                      <td style={{padding: '14px 16px'}}>
                        <div style={{fontWeight: 600, color: '#334155', fontSize: '0.9rem', marginBottom:'2px', display:'flex', alignItems:'center', gap:'8px'}}>
                          {item.item_name}
                        </div>
                        <div style={{fontSize: '0.7rem', color: '#6366f1', fontFamily:'monospace', background: '#eef2ff', display: 'inline-block', padding: '2px 6px', borderRadius: '4px', border: '1px solid #e0e7ff'}}>
                          <FiHash style={{verticalAlign:'middle', marginRight:2}} size={10}/>{skuDisplay}
                        </div>
                      </td>
                      <td style={{padding: '14px 16px'}}>
                        <span className="badge-pro" style={{fontSize: '0.7rem', display:'inline-flex', alignItems:'center', gap:'4px'}}>
                          <FiFilter size={10}/> {item.category}
                        </span>
                      </td>
                      <td style={{padding: '14px 16px'}}>
                        {item.quantity <= item.min_level ? (
                          <div style={{display:'flex', flexDirection:'column', alignItems:'flex-start'}}>
                             <span className="status-badge status-danger" style={{whiteSpace:'nowrap', justifyContent:'center'}}>{item.quantity} (BAJO)</span>
                             <span style={{fontSize:'0.65rem', color:'#ef4444', marginTop:'2px', fontWeight:600}}>Min: {item.min_level}</span>
                          </div>
                        ) : (
                          <span className="status-badge status-success" style={{whiteSpace:'nowrap', justifyContent:'center'}}>
                             <FiCheckSquare style={{marginRight:4}}/> {item.quantity} OK
                          </span>
                        )}
                      </td>
                      <td style={{padding: '14px 16px', fontSize: '0.85rem', color: '#64748b'}}>
                        <div style={{display:'flex', alignItems:'center', gap:'6px'}}><FiTruck size={14} color="#94a3b8"/> {item.location}</div>
                      </td>
                    </tr>
                  );
                }) : (
                  <tr>
                    <td colSpan="4" style={{textAlign:'center', padding:'60px 20px', color:'#94a3b8'}}>
                      <div style={{marginBottom:'15px', background:'#f1f5f9', width:'60px', height:'60px', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', margin:'0 auto 15px auto'}}>
                        <FiSearch size={24} color="#cbd5e1"/>
                      </div>
                      <div style={{fontWeight:600, color:'#475569'}}>No se encontraron resultados</div>
                      <div style={{fontSize:'0.85rem'}}>Prueba buscando por SKU (ej: RE-1002) o nombre sin acentos</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <style>{`.table-row-hover:hover { background: #f8fafc; }`}</style>
          </div>

          {/* Footer de Alerta y Acción */}
          <div style={{
            marginTop: '20px', padding: '16px', 
            background: 'linear-gradient(to right, #fff7ed, #ffedd5)', 
            border: '1px solid #fed7aa', borderRadius: '10px', 
            display: 'flex', gap: '16px', alignItems: 'center',
            flexWrap: 'wrap' // Permite que baje en móvil
          }}>
             <div style={{
               minWidth: '40px', height: '40px', background: '#f97316', 
               borderRadius: '50%', display:'flex', alignItems:'center', justifyContent:'center', 
               boxShadow: '0 4px 6px rgba(249, 115, 22, 0.2)'
             }}>
               <FiAlertCircle color="white" size={20} />
             </div>
             <div style={{flex: 1, minWidth: '200px'}}>
               <div style={{fontWeight: 700, color: '#9a3412', fontSize: '0.95rem'}}>Estado del Almacén</div>
               <div style={{fontSize: '0.85rem', color: '#c2410c', marginTop: '2px'}}>
                 Se han detectado existencias por debajo del umbral de seguridad.
               </div>
             </div>
             
             {/* BOTÓN DE GENERAR ORDEN - AHORA FUNCIONAL */}
             <button 
               onClick={generatePurchaseOrder}
               style={{
                 padding:'10px 16px', background:'white', border:'1px solid #fdba74', 
                 borderRadius:'6px', color:'#c2410c', fontWeight:'bold', cursor:'pointer', fontSize:'0.85rem',
                 boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                 display: 'flex', alignItems: 'center', gap: '8px',
                 transition: 'all 0.2s', whiteSpace: 'nowrap'
               }}
               onMouseOver={(e) => {e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)'}}
               onMouseOut={(e) => {e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)'}}
             >
               <FiShoppingCart /> Generar Orden
             </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Supply;