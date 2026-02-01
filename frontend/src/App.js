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
  const [user, setUser] = useState(null);

  if (!user) return <Login onLogin={setUser} />;

  return (
    <Router>
      <div className="app-layout">
        <div className={`sidebar-overlay ${isSidebarOpen ? 'visible' : ''}`} onClick={() => setIsSidebarOpen(false)}></div>
        <Sidebar isOpen={isSidebarOpen} closeSidebar={() => setIsSidebarOpen(false)} userName={user.user} />
        <main className="main-content">
          <div className="mobile-header">
            <div className="brand" style={{border: 'none', padding: 0}}><div className="brand-logo">IQ</div>RefineryIQ</div>
            <button className="hamburger-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}><FiMenu /></button>
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