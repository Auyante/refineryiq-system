import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { FiCpu, FiAlertTriangle, FiActivity, FiCheckCircle, FiClock, FiZap, FiShield } from 'react-icons/fi';
import { API_URL } from '../config';
import '../App.css';

/**
 * MÓDULO DE MANTENIMIENTO PREDICTIVO — AI Core v2.0
 * Visualiza predicciones RUL, anomalías Zero-Day, y explicaciones SHAP
 * generadas por el motor de deep learning (LSTM + Autoencoder).
 */
const Maintenance = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEquipment, setSelectedEquipment] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log(`🧠 AI Core v2.0: Consultando predicciones en: ${API_URL}`);
        const res = await axios.get(`${API_URL}/api/maintenance/predictions`);
        const safeData = Array.isArray(res.data) ? res.data : [];
        setData(safeData);
        setLoading(false);
      } catch (err) {
        console.error("Error Maintenance:", err);
        setError("No se pudieron obtener los diagnósticos del motor de IA.");
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getRiskColor = (prob) => {
    if (prob > 80) return '#ef4444';
    if (prob > 40) return '#f59e0b';
    return '#10b981';
  };

  const getRiskLevel = (prob) => {
    if (prob > 80) return { text: 'CRÍTICO', bg: '#fef2f2', border: '#fecaca' };
    if (prob > 40) return { text: 'ADVERTENCIA', bg: '#fffbeb', border: '#fde68a' };
    return { text: 'NORMAL', bg: '#f0fdf4', border: '#bbf7d0' };
  };

  if (loading) return (
    <div className="page-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh', flexDirection: 'column' }}>
      <div style={{
        width: 64, height: 64, borderRadius: '50%',
        background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: '20px', animation: 'pulse 1.5s infinite',
        boxShadow: '0 0 30px rgba(59,130,246,0.3)'
      }}>
        <FiCpu size={28} color="white" />
      </div>
      <p style={{ color: '#64748b', fontWeight: 500 }}>Motor IA procesando diagnósticos...</p>
      <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>LSTM + Autoencoder + SHAP</p>
      <style>{`@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(59,130,246,0.7); transform:scale(1); } 70% { box-shadow: 0 0 0 15px rgba(59,130,246,0); transform:scale(1.05); } 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0); transform:scale(1); } }`}</style>
    </div>
  );

  const criticalCount = data.filter(d => d.failure_probability > 80).length;
  const warningCount = data.filter(d => d.failure_probability > 40 && d.failure_probability <= 80).length;
  const normalCount = data.filter(d => d.failure_probability <= 40).length;
  const anomalyCount = data.filter(d => d.is_anomaly).length;

  return (
    <div className="page-container">
      {/* HEADER */}
      <div className="page-header">
        <div className="page-title">
          <h1>Mantenimiento Predictivo</h1>
          <p>Motor de Deep Learning — RUL (LSTM) + Detección de Anomalías (Autoencoder) + XAI (SHAP)</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div className="status-badge status-success" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FiCpu style={{ fontSize: '14px' }} />
            AI Core v2.0 Activo
          </div>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderLeft: '4px solid #ef4444', color: '#ef4444', marginBottom: '20px', padding: '16px' }}>
          <FiAlertTriangle style={{ marginRight: '10px' }} /> {error}
        </div>
      )}

      {/* KPI CARDS */}
      <div className="grid-4" style={{ marginBottom: '24px' }}>
        <div className="card" style={{ borderLeft: '4px solid #ef4444', textAlign: 'center', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em', marginBottom: '8px' }}>CRÍTICOS</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#ef4444' }}>{criticalCount}</div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Riesgo &gt; 80%</div>
        </div>
        <div className="card" style={{ borderLeft: '4px solid #f59e0b', textAlign: 'center', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em', marginBottom: '8px' }}>ADVERTENCIA</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#f59e0b' }}>{warningCount}</div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Riesgo 40-80%</div>
        </div>
        <div className="card" style={{ borderLeft: '4px solid #10b981', textAlign: 'center', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em', marginBottom: '8px' }}>NORMALES</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#10b981' }}>{normalCount}</div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Riesgo &lt; 40%</div>
        </div>
        <div className="card" style={{ borderLeft: '4px solid #8b5cf6', textAlign: 'center', padding: '20px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em', marginBottom: '8px' }}>ANOMALÍAS</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#8b5cf6' }}>{anomalyCount}</div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Zero-Day detectadas</div>
        </div>
      </div>

      <div className="grid-2">
        {/* GRÁFICO DE BARRAS: PROBABILIDAD DE FALLA */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiActivity /> Riesgo de Fallo por Equipo</h3>
          </div>
          <div style={{ height: '380px', width: '100%' }}>
            {data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 60, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <YAxis
                    type="category"
                    dataKey="equipment_name"
                    width={140}
                    tick={{ fontSize: 11, fill: '#4b5563' }}
                  />
                  <Tooltip
                    cursor={{ fill: '#f3f4f6' }}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    formatter={(value, name) => {
                      if (name === 'failure_probability') return [`${value.toFixed(1)}%`, 'Prob. Fallo'];
                      return [value, name];
                    }}
                  />
                  <Bar dataKey="failure_probability" barSize={22} radius={[0, 6, 6, 0]}>
                    {data.map((entry, index) => (
                      <Cell key={index} fill={getRiskColor(entry.failure_probability)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                No hay datos suficientes para generar gráfico.
              </div>
            )}
          </div>
        </div>

        {/* LISTA DETALLADA DE DIAGNÓSTICOS */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FiAlertTriangle /> Diagnóstico Detallado IA</h3>
            <span style={{ fontSize: '0.75rem', color: '#8b5cf6', fontWeight: 600, background: '#f5f3ff', padding: '4px 10px', borderRadius: '20px' }}>
              LSTM + SHAP
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '380px', overflowY: 'auto', paddingRight: '5px' }}>
            {data.length > 0 ? data.map((item, idx) => {
              const risk = getRiskLevel(item.failure_probability);
              return (
                <div key={idx}
                  onClick={() => setSelectedEquipment(selectedEquipment === idx ? null : idx)}
                  style={{
                    padding: '16px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '12px',
                    borderLeft: `5px solid ${getRiskColor(item.failure_probability)}`,
                    background: '#ffffff',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: selectedEquipment === idx ? '0 4px 12px rgba(0,0,0,0.08)' : '0 2px 4px rgba(0,0,0,0.02)'
                  }}
                >
                  {/* Header row */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                    <div>
                      <strong style={{ fontSize: '0.95rem', color: '#1e293b', display: 'block' }}>{item.equipment_name || item.equipment_id}</strong>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {item.equipment_type} • ID: {item.equipment_id}
                      </span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{
                        fontSize: '1rem', fontWeight: 800,
                        color: getRiskColor(item.failure_probability)
                      }}>
                        {(item.failure_probability || 0).toFixed(1)}%
                      </span>
                      <div style={{
                        fontSize: '0.65rem', fontWeight: 700,
                        padding: '2px 8px', borderRadius: '10px',
                        background: risk.bg, color: getRiskColor(item.failure_probability),
                        border: `1px solid ${risk.border}`, marginTop: '2px'
                      }}>
                        {risk.text}
                      </div>
                    </div>
                  </div>

                  {/* RUL + Anomaly row */}
                  <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
                    {item.rul_hours != null && (
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '5px',
                        fontSize: '0.8rem', color: '#334155',
                        background: '#f1f5f9', padding: '4px 10px', borderRadius: '6px'
                      }}>
                        <FiClock size={13} />
                        RUL: <strong>{item.rul_hours.toFixed(0)}h</strong>
                      </div>
                    )}
                    {item.is_anomaly && (
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '5px',
                        fontSize: '0.8rem', color: '#7c3aed', fontWeight: 600,
                        background: '#f5f3ff', padding: '4px 10px', borderRadius: '6px'
                      }}>
                        <FiZap size={13} />
                        Anomalía Zero-Day
                      </div>
                    )}
                  </div>

                  {/* Recommendation */}
                  <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.8rem', color: '#334155', fontWeight: 600, marginBottom: '3px' }}>
                      <FiShield size={12} style={{ marginRight: '4px' }} />
                      Recomendación IA:
                    </div>
                    <div style={{ fontSize: '0.82rem', color: '#475569' }}>
                      {item.recommendation || "Sin acción requerida actualmente."}
                    </div>
                  </div>

                  {/* Expandable: Narrative + SHAP */}
                  {selectedEquipment === idx && (
                    <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed #e2e8f0' }}>
                      {/* AI Narrative */}
                      {item.narrative && (
                        <div style={{
                          background: 'linear-gradient(135deg, #eff6ff, #f5f3ff)',
                          padding: '12px', borderRadius: '8px', marginBottom: '10px',
                          border: '1px solid #ddd6fe'
                        }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6366f1', marginBottom: '4px' }}>
                            🧠 EXPLICACIÓN IA (SHAP)
                          </div>
                          <div style={{ fontSize: '0.82rem', color: '#334155', lineHeight: '1.4' }}>
                            {item.narrative}
                          </div>
                        </div>
                      )}

                      {/* SHAP Feature Importance */}
                      {item.shap_explanation?.top_drivers && (
                        <div style={{ background: '#fafafa', padding: '10px', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#475569', marginBottom: '6px' }}>
                            Factores principales:
                          </div>
                          {item.shap_explanation.top_drivers.slice(0, 3).map((driver, i) => (
                            <div key={i} style={{
                              display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px'
                            }}>
                              <div style={{
                                width: `${Math.max(driver.contribution_pct * 2, 20)}px`, height: '8px',
                                background: driver.direction === 'aumento' ? '#ef4444' : '#3b82f6',
                                borderRadius: '4px', transition: 'width 0.5s'
                              }} />
                              <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                                {driver.feature.replace(/_/g, ' ')}: <strong>{driver.contribution_pct}%</strong> ({driver.direction})
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '0.72rem', color: '#94a3b8' }}>
                        <span>Confianza: {(item.confidence || 75).toFixed(1)}%</span>
                        <span>Modelo: {item.model_source || 'AI Core v2'}</span>
                        <span>{item.prediction}</span>
                      </div>
                    </div>
                  )}

                  {/* Click hint */}
                  <div style={{ textAlign: 'center', marginTop: '10px' }}>
                    <span style={{
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      color: selectedEquipment === idx ? '#ef4444' : '#6366f1',
                      background: selectedEquipment === idx ? '#fef2f2' : '#eef2ff',
                      padding: '6px 16px',
                      borderRadius: '20px',
                      border: `1px solid ${selectedEquipment === idx ? '#fecaca' : '#c7d2fe'}`,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      {selectedEquipment === idx ? '✕ Cerrar detalle' : '🧠 Ver explicación IA'}
                    </span>
                  </div>
                </div>
              );
            }) : (
              <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                <FiCheckCircle size={40} style={{ marginBottom: '10px', color: '#10b981' }} />
                <p>No se han detectado anomalías. <br />Todos los sistemas operan dentro de parámetros normales.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Maintenance;