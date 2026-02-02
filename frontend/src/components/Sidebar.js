import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { FiHome, FiDatabase, FiCpu, FiZap, FiAlertTriangle, FiSettings, FiLayers, FiPackage, FiLogOut } from 'react-icons/fi';
import '../App.css';

const Sidebar = ({ isOpen, closeSidebar, userName, onLogout }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    }
    navigate('/');
  };

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="brand">
        <div className="brand-logo">IQ</div>
        <div>
          <h2>RefineryIQ</h2>
          <span style={{fontSize:'0.7rem', color:'#9ca3af'}}>v3.0 Enterprise</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        <p style={{fontSize:'0.7rem', color:'#6b7280', margin:'1rem 0 0.5rem 1rem', fontWeight:'bold'}}>GENERAL</p>
        <NavLink to="/" className={({isActive})=>isActive?"nav-item active":"nav-item"} onClick={closeSidebar}>
          <FiHome/> Dashboard
        </NavLink>
        <NavLink to="/assets" className={({isActive})=>isActive?"nav-item active":"nav-item"} onClick={closeSidebar}>
          <FiLayers/> Activos
        </NavLink>
        <NavLink to="/supply" className={({isActive})=>isActive?"nav-item active":"nav-item"} onClick={closeSidebar}>
          <FiPackage/> Suministros
        </NavLink>
        
        <p style={{fontSize:'0.7rem', color:'#6b7280', margin:'1rem 0 0.5rem 1rem', fontWeight:'bold'}}>INTELIGENCIA</p>
        <NavLink to="/maintenance" className={({isActive})=>isActive?"nav-item active":"nav-item"} onClick={closeSidebar}>
          <FiCpu/> Mantenimiento ML
        </NavLink>
        <NavLink to="/energy" className={({isActive})=>isActive?"nav-item active":"nav-item"} onClick={closeSidebar}>
          <FiZap/> Energía
        </NavLink>
        <NavLink to="/alerts" className={({isActive})=>isActive?"nav-item active":"nav-item"} onClick={closeSidebar}>
          <FiAlertTriangle/> Alertas
        </NavLink>
        <NavLink to="/normalized" className={({isActive})=>isActive?"nav-item active":"nav-item"} onClick={closeSidebar}>
          <FiDatabase/> Base de Datos
        </NavLink>
      </nav>
      
      <div style={{
        padding:'1.5rem', 
        borderTop:'1px solid rgba(255,255,255,0.1)', 
        display:'flex', 
        alignItems:'center', 
        gap:'10px'
      }}>
        <div style={{
          width:32, 
          height:32, 
          background:'#374151', 
          borderRadius:'50%', 
          display:'flex', 
          alignItems:'center', 
          justifyContent:'center',
          color: 'white',
          fontWeight: 'bold'
        }}>
          {userName?.charAt(0) || 'U'}
        </div>
        <div style={{flex:1}}>
          <div style={{fontSize:'0.9rem', color: 'white'}}>{userName || 'Usuario'}</div>
          <div style={{fontSize:'0.7rem', color:'#10b981'}}>● Online</div>
        </div>
        <button 
          onClick={handleLogout}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#9ca3af',
            cursor: 'pointer',
            padding: '5px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Cerrar sesión"
        >
          <FiLogOut size={18} />
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;