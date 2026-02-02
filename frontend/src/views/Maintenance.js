import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { FiCpu, FiAlertTriangle } from 'react-icons/fi';
import { API_URL } from '../config';
import axios from 'axios';
// (Borra la línea vieja const API_URL = ...)
const Maintenance = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    // Usar comillas invertidas ` `
    axios.get(`${API_URL}/api/maintenance/predictions`)
      .then(res => setData(res.data))
      .catch(err => console.error(err));
}, []);

  const getRiskColor = (prob) => prob > 80 ? '#ef4444' : prob > 40 ? '#f59e0b' : '#10b981';

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Mantenimiento Predictivo</h1>
          <p>Análisis de salud de activos basado en Machine Learning</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiCpu /> Probabilidad de Falla</h3>
          </div>
          <div style={{height: '350px'}}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis dataKey="equipment_name" type="category" width={140} tick={{fontSize: 12, fill: '#4b5563'}} />
                <Tooltip cursor={{fill: 'transparent'}} contentStyle={{borderRadius: '8px'}} />
                <Bar dataKey="failure_probability" radius={[0, 4, 4, 0]} barSize={24}>
                  {data.map((entry, index) => (
                    <Cell key={index} fill={getRiskColor(entry.failure_probability)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiAlertTriangle /> Diagnóstico IA</h3>
          </div>
          <div style={{display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '350px', overflowY: 'auto'}}>
            {data.map((item, idx) => (
              <div key={idx} style={{
                padding: '12px', border: '1px solid var(--border-light)', borderRadius: '8px',
                borderLeft: `4px solid ${getRiskColor(item.failure_probability)}`
              }}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '4px'}}>
                  <strong style={{fontSize: '0.9rem'}}>{item.equipment_name}</strong>
                  <span style={{fontSize: '0.8rem', fontWeight: 700, color: getRiskColor(item.failure_probability)}}>
                    {item.failure_probability.toFixed(1)}%
                  </span>
                </div>
                <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)'}}>
                  {item.recommendation}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Maintenance;