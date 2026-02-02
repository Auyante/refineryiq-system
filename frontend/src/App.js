import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { FiMenu } from 'react-icons/fi';
import './App.css';
import Sidebar from './components/Sidebar';
import Dashboard from './views/Dashboard';
import Maintenance from './views/Maintenance';
import Energy from './views/Energy';
import Alerts from './views/Alerts';
import Assets from './views/Assets';
import Supply from './views/Supply';
import Login from './views/Login';
import NormalizedDataViewer from './components/NormalizedDataViewer';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [user, setUser] = useState(() => {
    // Intentar recuperar usuario del localStorage al iniciar
    const savedUser = localStorage.getItem('refineryiq_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('refineryiq_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('refineryiq_user');
  };

  if (!user) return <Login onLogin={handleLogin} />;

  return (
    <Router>
      <div className="app-layout">
        <div className={`sidebar-overlay ${isSidebarOpen ? 'visible' : ''}`} onClick={() => setIsSidebarOpen(false)}></div>
        <Sidebar 
          isOpen={isSidebarOpen} 
          closeSidebar={() => setIsSidebarOpen(false)} 
          userName={user.user} 
          onLogout={handleLogout}
        />
        <main className="main-content">
          <div className="mobile-header">
            <div className="brand" style={{border: 'none', padding: 0}}>
              <div className="brand-logo">IQ</div>
              <span style={{color: 'white', fontWeight: 600, fontSize: '0.9rem'}}>RefineryIQ</span>
            </div>
            <button className="hamburger-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
              <FiMenu />
            </button>
          </div>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/supply" element={<Supply />} />
            <Route path="/assets" element={<Assets />} />
            <Route path="/maintenance" element={<Maintenance />} />
            <Route path="/energy" element={<Energy />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/normalized" element={<div className="page-container"><NormalizedDataViewer /></div>} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;