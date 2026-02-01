import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiAlertTriangle, FiCheckCircle, FiClock, FiFilter } from 'react-icons/fi';

const Alerts = () => {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    axios.get('http://192.168.1.108:8000/api/alerts/history')
      .then(res => setAlerts(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Centro de Alertas</h1>
          <p>Bitácora de incidencias operativas</p>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title"><FiFilter /> Registros Recientes</h3>
        </div>
        
        <div className="table-container">
          <table className="modern-table">
            <thead>
              <tr>
                <th>Estado</th>
                <th>Severidad</th>
                <th>Hora</th>
                <th>Unidad</th>
                <th>Mensaje</th>
                <th>Variable</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length > 0 ? alerts.map((alert) => (
                <tr key={alert.id}>
                  <td>
                    {alert.acknowledged ? 
                      <FiCheckCircle size={18} color="var(--success)" title="Atendida" /> : 
                      <div style={{width: 10, height: 10, background: 'var(--danger)', borderRadius: '50%'}} title="Pendiente"></div>
                    }
                  </td>
                  <td>
                    <span className={`status-badge ${
                      alert.severity === 'HIGH' ? 'status-danger' : 
                      alert.severity === 'MEDIUM' ? 'status-warning' : 'status-success'
                    }`}>
                      {alert.severity}
                    </span>
                  </td>
                  <td style={{color: 'var(--text-secondary)', fontSize: '0.85rem'}}>
                    <FiClock style={{marginRight: 6, verticalAlign: 'text-bottom'}} />
                    {new Date(alert.timestamp).toLocaleString()}
                  </td>
                  <td><strong>{alert.unit_name || alert.unit_id}</strong></td>
                  <td>{alert.message}</td>
                  <td style={{fontFamily: 'monospace', color: 'var(--text-secondary)'}}>
                    {alert.tag_name || alert.tag_id}
                  </td>
                </tr>
              )) : (
                <tr><td colSpan="6" style={{textAlign: 'center', padding: '2rem'}}>No hay datos</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Alerts;