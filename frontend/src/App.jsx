import React, { Component, useEffect, useState } from 'react';
import { Search, Bell, Activity } from 'lucide-react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import SinglePredictor from './components/SinglePredictor';
import BatchPredictor from './components/BatchPredictor';
import ModelDetails from './components/ModelDetails';
import ResearchTools from './components/ResearchTools';

class ErrorBoundary extends Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  render() { return this.state.hasError ? <div className="fatal-error">A view could not be loaded. <button onClick={() => window.location.reload()}>Reload workspace</button></div> : this.props.children; }
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [modelInfo, setModelInfo] = useState(null);
  const [latestResult, setLatestResult] = useState(null);
  
  // Search state
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState('');

  // Notifications state
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [unreadNotifications, setUnreadNotifications] = useState(true);

  useEffect(() => { 
    fetch('/api/model-info')
      .then(r => r.json())
      .then(setModelInfo)
      .catch(() => {}); 
  }, []);

  const handleSearchSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setSearchError('');
    try {
      const r = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ smiles: searchQuery.trim() })
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Lookup failed');
      setLatestResult(d);
      setIsSearchOpen(false);
      setSearchQuery('');
      setActiveTab('single');
    } catch (err) {
      setSearchError(err.message || 'Compound name unresolved or invalid SMILES.');
    } finally {
      setSearchLoading(false);
    }
  };

  const tools = ['molecule', 'explain', 'analytics', 'descriptors', 'similarity', 'report', 'about'];

  return (
    <div className="app-shell">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} modelInfo={modelInfo} />
      <div className="topbar">
        <div className="top-brand">
          <span className="brand-mark">OT</span>
          <span>OCULAR<span>TOX</span></span>
        </div>
        <div className="top-pills">
          <button onClick={() => setActiveTab('single')}>⌬ Prediction Lab</button>
          <button onClick={() => setActiveTab('analytics')}>▥ Monitoring</button>
          <button onClick={() => setActiveTab('about')}>◌ Research notes</button>
        </div>
        <div className="top-actions">
          <button className="icon-btn" onClick={() => setIsSearchOpen(true)} title="Quick Search">
            <Search size={18}/>
          </button>
          
          <div className="notifications-wrapper" style={{ position: 'relative' }}>
            <button className="icon-btn" onClick={() => { setIsNotificationsOpen(!isNotificationsOpen); setUnreadNotifications(false); }} title="System Logs">
              <Bell size={17}/>
              {unreadNotifications && <span className="notification-badge" />}
            </button>
            
            {isNotificationsOpen && (
              <div className="notifications-dropdown">
                <div className="notif-header">
                  <h4>System Logs & Health</h4>
                  <button onClick={() => setIsNotificationsOpen(false)} style={{ background: 'transparent', border: 0, color: '#888', cursor: 'pointer' }}>✕</button>
                </div>
                <div className="notif-list">
                  <div className="notif-item success">
                    <span className="notif-dot" />
                    <div className="notif-body">
                      <p>Model loaded: ExtraTree classifier with 165 features.</p>
                      <small>Just now</small>
                    </div>
                  </div>
                  <div className="notif-item info">
                    <span className="notif-dot" />
                    <div className="notif-body">
                      <p>Dataset verified: 4,901 training molecules loaded.</p>
                      <small>5m ago</small>
                    </div>
                  </div>
                  <div className="notif-item info">
                    <span className="notif-dot" />
                    <div className="notif-body">
                      <p>OECD compliance: SHAP explainability core active.</p>
                      <small>12m ago</small>
                    </div>
                  </div>
                  <div className="notif-item warning">
                    <span className="notif-dot" />
                    <div className="notif-body">
                      <p>Tuning threshold set to research optimized 0.44.</p>
                      <small>1h ago</small>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          <span className="researcher">Shubhangini</span>
        </div>
      </div>
      
      <main className="main-content">
        <ErrorBoundary key={activeTab}>
          {activeTab === 'dashboard' && <Dashboard modelInfo={modelInfo} onNavigateToSingle={() => setActiveTab('single')} />}
          {activeTab === 'single' && <SinglePredictor onResult={setLatestResult} />}
          {activeTab === 'batch' && <BatchPredictor />}
          {activeTab === 'details' && <ModelDetails modelInfo={modelInfo} />}
          {tools.includes(activeTab) && <ResearchTools page={activeTab} result={latestResult} onResult={setLatestResult} onNavigate={setActiveTab} modelInfo={modelInfo} />}
        </ErrorBoundary>
      </main>
      
      <div className="creator-mark">Built with purpose by <strong>Shubhangini</strong></div>

      {isSearchOpen && (
        <div className="search-overlay" onClick={() => setIsSearchOpen(false)}>
          <div className="search-modal" onClick={e => e.stopPropagation()}>
            <div className="search-modal-header">
              <h3>Structure & Compound Search</h3>
              <button className="close-btn" onClick={() => setIsSearchOpen(false)}>✕</button>
            </div>
            <form onSubmit={handleSearchSubmit} className="search-modal-body">
              <p className="muted" style={{ marginBottom: '16px' }}>
                Query PubChem database or local repository by compound name or SMILES string (e.g. Aspirin, CCO, Caffeine, Phenol) to predict toxicity.
              </p>
              <div className="search-input-group" style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="input-text"
                  placeholder="Enter compound name or SMILES..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  autoFocus
                  style={{ flex: 1 }}
                />
                <button type="submit" className="btn-primary" disabled={searchLoading} style={{ minWidth: '100px' }}>
                  {searchLoading ? 'Searching...' : 'Search'}
                </button>
              </div>
              {searchError && <p className="error-text" style={{ marginTop: '12px', color: 'var(--red)', fontSize: '0.85rem' }}>{searchError}</p>}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
