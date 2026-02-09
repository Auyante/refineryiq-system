import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiSave, FiTrash2, FiPlus, FiEdit3, FiX, FiPackage, FiArrowLeft, FiHome } from 'react-icons/fi';
import { API_URL } from '../config';
import '../App.css';

const AdminInventory = () => {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [newItem, setNewItem] = useState({ 
    item: '', 
    sku: '', 
    quantity: 0, 
    unit: '', 
    status: 'OK', 
    location: 'Almacén Central' 
  });
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_URL}/api/inventory`);
      setInventory(res.data);
      setLoading(false);
    } catch (error) {
      console.error('Error cargando inventario:', error);
      setMessage('Error al cargar el inventario');
      setLoading(false);
    }
  };

  const handleEditClick = (item) => {
    setEditingId(item.id);
    setEditForm({ 
      item: item.item || '',
      sku: item.sku || '',
      quantity: item.quantity || 0,
      unit: item.unit || '',
      status: item.status || 'OK',
      location: item.location || 'Almacén Central'
    });
  };

  const handleSaveEdit = async (id) => {
    try {
      // Preparar datos para enviar (solo campos modificados)
      const updateData = {};
      if (editForm.item !== undefined) updateData.item = editForm.item;
      if (editForm.sku !== undefined) updateData.sku = editForm.sku;
      if (editForm.quantity !== undefined) updateData.quantity = parseFloat(editForm.quantity);
      if (editForm.unit !== undefined) updateData.unit = editForm.unit;
      if (editForm.status !== undefined) updateData.status = editForm.status;
      if (editForm.location !== undefined) updateData.location = editForm.location;

      await axios.put(`${API_URL}/api/inventory/${id}`, updateData);
      setEditingId(null);
      setMessage('Ítem actualizado correctamente');
      fetchInventory();
    } catch (error) {
      console.error('Error actualizando:', error);
      setMessage('Error al actualizar el ítem');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('¿Estás seguro de eliminar este ítem?')) {
      try {
        await axios.delete(`${API_URL}/api/inventory/${id}`);
        setMessage('Ítem eliminado correctamente');
        fetchInventory();
      } catch (error) {
        console.error('Error eliminando:', error);
        setMessage('Error al eliminar el ítem');
      }
    }
  };

  const handleAddItem = async () => {
    if (!newItem.item || !newItem.sku || newItem.quantity < 0) {
      setMessage('Por favor, complete todos los campos requeridos');
      return;
    }

    try {
      await axios.post(`${API_URL}/api/inventory`, newItem);
      setMessage('Ítem agregado correctamente');
      setNewItem({ 
        item: '', 
        sku: '', 
        quantity: 0, 
        unit: '', 
        status: 'OK', 
        location: 'Almacén Central' 
      });
      fetchInventory();
    } catch (error) {
      console.error('Error agregando:', error);
      setMessage(error.response?.data?.detail || 'Error al agregar el ítem');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditForm({});
  };

  if (loading) {
    return (
      <div className="page-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <div className="spinner"></div>
        <p style={{ marginLeft: '1rem', color: '#64748b' }}>Cargando inventario...</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Header con navegación */}
      <div className="page-header">
        <div className="page-title">
          <h1>🧑‍💼 Panel de Administración</h1>
          <p>Gestión completa del inventario (Acceso Privado)</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => window.location.href = '/#'}
            style={{
              padding: '10px 16px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            <FiHome /> Volver al Dashboard
          </button>
        </div>
      </div>

      {/* Mensajes de estado */}
      {message && (
        <div className="card" style={{ 
          borderLeft: '4px solid #3b82f6', 
          background: '#eff6ff', 
          marginBottom: '1.5rem',
          padding: '1rem'
        }}>
          <p style={{ margin: 0, color: '#1d4ed8', fontWeight: 500 }}>{message}</p>
        </div>
      )}

      {/* Formulario para agregar nuevo ítem */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <FiPlus color="#16a34a" /> Agregar Nuevo Ítem al Inventario
        </h3>
        
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '1rem',
          marginBottom: '1.5rem'
        }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Nombre del ítem *</label>
            <input
              type="text"
              value={newItem.item}
              onChange={(e) => setNewItem({ ...newItem, item: e.target.value })}
              placeholder="Ej: Catalizador FCC"
              style={{ 
                width: '100%', 
                padding: '0.75rem', 
                border: '1px solid #d1d5db', 
                borderRadius: '6px',
                fontSize: '0.9rem'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>SKU *</label>
            <input
              type="text"
              value={newItem.sku}
              onChange={(e) => setNewItem({ ...newItem, sku: e.target.value })}
              placeholder="Ej: CAT-ZSM5"
              style={{ 
                width: '100%', 
                padding: '0.75rem', 
                border: '1px solid #d1d5db', 
                borderRadius: '6px',
                fontSize: '0.9rem'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Cantidad *</label>
            <input
              type="number"
              step="0.01"
              value={newItem.quantity}
              onChange={(e) => setNewItem({ ...newItem, quantity: parseFloat(e.target.value) || 0 })}
              style={{ 
                width: '100%', 
                padding: '0.75rem', 
                border: '1px solid #d1d5db', 
                borderRadius: '6px',
                fontSize: '0.9rem'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Unidad</label>
            <input
              type="text"
              value={newItem.unit}
              onChange={(e) => setNewItem({ ...newItem, unit: e.target.value })}
              placeholder="kg, L, pza, etc."
              style={{ 
                width: '100%', 
                padding: '0.75rem', 
                border: '1px solid #d1d5db', 
                borderRadius: '6px',
                fontSize: '0.9rem'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Estado</label>
            <select
              value={newItem.status}
              onChange={(e) => setNewItem({ ...newItem, status: e.target.value })}
              style={{ 
                width: '100%', 
                padding: '0.75rem', 
                border: '1px solid #d1d5db', 
                borderRadius: '6px',
                fontSize: '0.9rem'
              }}
            >
              <option value="OK">OK - Stock Normal</option>
              <option value="LOW">LOW - Stock Bajo</option>
              <option value="CRITICAL">CRITICAL - Stock Crítico</option>
            </select>
          </div>
        </div>
        
        <button
          onClick={handleAddItem}
          style={{
            padding: '0.75rem 1.5rem',
            background: '#16a34a',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.9rem',
            fontWeight: 600,
            transition: 'all 0.2s'
          }}
          onMouseOver={(e) => e.currentTarget.style.opacity = '0.9'}
          onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
        >
          <FiSave /> Agregar al Inventario
        </button>
      </div>

      {/* Tabla de inventario */}
      <div className="card">
        <div className="card-header" style={{ background: '#f8fafc' }}>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FiPackage /> Inventario Actual ({inventory.length} ítems)
          </h3>
          <button
            onClick={fetchInventory}
            style={{
              padding: '8px 12px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.85rem'
            }}
          >
            🔄 Actualizar
          </button>
        </div>
        
        <div className="table-container">
          <table className="modern-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Ítem</th>
                <th>SKU</th>
                <th>Cantidad</th>
                <th>Unidad</th>
                <th>Estado</th>
                <th>Ubicación</th>
                <th>Última Actualización</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {inventory.length === 0 ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                    <FiPackage size={40} style={{ marginBottom: '10px', opacity: 0.5 }} />
                    <p>No hay ítems en el inventario. Agrega uno nuevo arriba.</p>
                  </td>
                </tr>
              ) : (
                inventory.map((item) => (
                  <tr key={item.id}>
                    {editingId === item.id ? (
                      // Modo edición
                      <>
                        <td style={{ fontWeight: 'bold' }}>{item.id}</td>
                        <td>
                          <input
                            type="text"
                            value={editForm.item}
                            onChange={(e) => setEditForm({ ...editForm, item: e.target.value })}
                            style={{ 
                              padding: '8px', 
                              width: '100%', 
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px'
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={editForm.sku}
                            onChange={(e) => setEditForm({ ...editForm, sku: e.target.value })}
                            style={{ 
                              padding: '8px', 
                              width: '100%', 
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px'
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            value={editForm.quantity}
                            onChange={(e) => setEditForm({ ...editForm, quantity: parseFloat(e.target.value) || 0 })}
                            style={{ 
                              padding: '8px', 
                              width: '100%', 
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px'
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            value={editForm.unit}
                            onChange={(e) => setEditForm({ ...editForm, unit: e.target.value })}
                            style={{ 
                              padding: '8px', 
                              width: '100%', 
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px'
                            }}
                          />
                        </td>
                        <td>
                          <select
                            value={editForm.status}
                            onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                            style={{ 
                              padding: '8px', 
                              width: '100%', 
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px'
                            }}
                          >
                            <option value="OK">OK</option>
                            <option value="LOW">LOW</option>
                            <option value="CRITICAL">CRITICAL</option>
                          </select>
                        </td>
                        <td>
                          <input
                            type="text"
                            value={editForm.location}
                            onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                            style={{ 
                              padding: '8px', 
                              width: '100%', 
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px'
                            }}
                          />
                        </td>
                        <td>{new Date(item.last_updated).toLocaleString()}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                              onClick={() => handleSaveEdit(item.id)}
                              style={{
                                padding: '6px 12px',
                                background: '#16a34a',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.8rem'
                              }}
                            >
                              <FiSave size={12} /> Guardar
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              style={{
                                padding: '6px 12px',
                                background: '#dc2626',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.8rem'
                              }}
                            >
                              <FiX size={12} /> Cancelar
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      // Modo visualización
                      <>
                        <td style={{ fontWeight: 'bold', color: '#64748b' }}>{item.id}</td>
                        <td><strong>{item.item}</strong></td>
                        <td><code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>{item.sku}</code></td>
                        <td style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{item.quantity}</td>
                        <td>{item.unit}</td>
                        <td>
                          <span className={`status-badge ${
                            item.status === 'OK' ? 'status-success' : 
                            item.status === 'LOW' ? 'status-warning' : 'status-danger'
                          }`}>
                            {item.status}
                          </span>
                        </td>
                        <td>{item.location}</td>
                        <td style={{ fontSize: '0.85rem', color: '#64748b' }}>
                          {new Date(item.last_updated).toLocaleString()}
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                              onClick={() => handleEditClick(item)}
                              style={{
                                padding: '6px 12px',
                                background: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.8rem'
                              }}
                            >
                              <FiEdit3 size={12} /> Editar
                            </button>
                            <button
                              onClick={() => handleDelete(item.id)}
                              style={{
                                padding: '6px 12px',
                                background: '#dc2626',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.8rem'
                              }}
                            >
                              <FiTrash2 size={12} /> Eliminar
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Footer de la tabla */}
        <div style={{
          padding: '15px',
          borderTop: '1px solid #f1f5f9',
          background: '#f8fafc',
          fontSize: '0.85rem',
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>Total: <strong>{inventory.length}</strong> ítems</div>
          <div>Última actualización: {new Date().toLocaleTimeString()}</div>
        </div>
      </div>
      
      {/* Mensaje de ayuda */}
      <div className="card" style={{ 
        background: 'linear-gradient(to right, #eff6ff, #dbeafe)',
        border: '1px solid #bfdbfe',
        marginTop: '1.5rem'
      }}>
        <h4 style={{ color: '#1e40af', marginBottom: '0.5rem' }}>📝 Instrucciones:</h4>
        <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#374151' }}>
          <li>Para editar un ítem, haz clic en el botón <strong>Editar</strong></li>
          <li>Para eliminar un ítem, haz clic en el botón <strong>Eliminar</strong></li>
          <li>Los cambios se guardan automáticamente en la base de datos</li>
          <li>Acceso directo a esta página: <code>https://refineryiq.dev/#/admin-inventory</code></li>
        </ul>
      </div>
    </div>
  );
};

export default AdminInventory;