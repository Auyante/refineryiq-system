import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { FiZap, FiTarget } from 'react-icons/fi';
import { API_URL } from '../config';
import axios from 'axios';
// (Borra la línea vieja const API_URL = ...)
const Energy = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    axios.get(`${API_URL}/api/energy/analysis`)
      .then(res => setData(res.data))
      .catch(err => console.error(err));
}, []);

  // Función para abreviar nombres largos automáticamente en el gráfico
  const formatXAxis = (name) => {
    if (name.includes('Destilación')) return 'CDU'; // Crude Distillation Unit
    if (name.includes('Craqueo')) return 'FCC';     // Fluid Catalytic Cracking
    if (name.includes('Hidrotratamiento')) return 'HT'; // Hydrotreating
    return name;
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Gestión Energética</h1>
          <p>Auditoría de consumo vs Benchmark</p>
        </div>
      </div>

      <div className="card" style={{marginBottom: '2rem'}}>
        <div className="card-header">
          <h3 className="card-title"><FiZap /> Consumo Real vs Meta</h3>
        </div>
        <div style={{height: '350px'}}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorEnergy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
              
              {/* AQUÍ ESTÁ EL CAMBIO CLAVE: tickFormatter */}
              <XAxis 
                dataKey="unit_name" 
                axisLine={false} 
                tickLine={false} 
                tickFormatter={formatXAxis} 
                interval={0} // Obliga a mostrar todos los nombres
                tick={{fill: '#6b7280', fontSize: 12, fontWeight: 600}}
              />
              
              <YAxis axisLine={false} tickLine={false} />
              
              {/* El Tooltip seguirá mostrando el nombre completo */}
              <Tooltip 
                formatter={(value, name) => [value, name === 'avg_energy_consumption' ? 'Consumo Real' : 'Meta Ideal']}
                labelStyle={{fontWeight: 'bold', color: '#111827'}}
              />
              
              <Area type="monotone" dataKey="avg_energy_consumption" stroke="#3b82f6" fill="url(#colorEnergy)" name="Consumo Real" />
              <Area type="monotone" dataKey="benchmark" stroke="#10b981" strokeDasharray="5 5" fill="none" name="Benchmark" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title"><FiTarget /> Detalle de Eficiencia</h3>
        </div>
        <div className="table-container">
          <table className="modern-table">
            <thead>
              <tr>
                <th>Unidad</th>
                <th>Eficiencia</th>
                <th>Estado</th>
                <th>Ahorro Estimado</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr key={idx}>
                  <td>
                    {/* Aquí mostramos nombre completo + sigla */}
                    <strong>{row.unit_name}</strong>
                    <div style={{fontSize: '0.75rem', color: '#6b7280'}}>ID: {formatXAxis(row.unit_name)}</div>
                  </td>
                  <td>
                    <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                      <div style={{width: '60px', height: '6px', background: '#e5e7eb', borderRadius: '3px'}}>
                        <div style={{
                          width: `${Math.min(row.efficiency_score, 100)}%`, 
                          height: '100%', 
                          background: row.efficiency_score > 90 ? '#10b981' : '#f59e0b',
                          borderRadius: '3px'
                        }}></div>
                      </div>
                      {row.efficiency_score.toFixed(1)}%
                    </div>
                  </td>
                  <td>
                    <span className={`status-badge ${row.efficiency_score > 90 ? 'status-success' : 'status-warning'}`}>
                      {row.status}
                    </span>
                  </td>
                  <td style={{fontWeight: 600, color: '#10b981'}}>
                    {row.estimated_savings > 0 ? `-${row.estimated_savings.toFixed(2)} kWh` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Energy;