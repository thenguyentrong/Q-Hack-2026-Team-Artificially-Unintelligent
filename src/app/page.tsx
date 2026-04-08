"use client";

import { useState } from "react";

export default function WorkspacePage() {
  const [activeTab, setActiveTab] = useState("layer1");
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, any>>({});

  const runTest = async (layer: string, endpoint: string) => {
    setLoading(prev => ({ ...prev, [layer]: true }));
    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      setResults(prev => ({ ...prev, [layer]: data }));
    } catch (err) {
      setResults(prev => ({ ...prev, [layer]: { error: "Failed to fetch from backend" } }));
    }
    setLoading(prev => ({ ...prev, [layer]: false }));
  };

  return (
    <div className="animate-in">
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.5rem', letterSpacing: '-0.5px' }}>
          Ingredient Analysis
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Identify functional substitutes and verify quality compliance across the selected BOM component.
        </p>
      </div>

      <div className="tabs-container">
        {['layer1', 'layer2', 'layer3', 'layer4'].map((layer, index) => {
          const titles = ["1. Requirements Inference", "2. Supplier Discovery", "3. Quality Verification", "4. Consensus & Decision"];
          return (
            <div 
              key={layer}
              className={`tab ${activeTab === layer ? 'active' : ''}`}
              onClick={() => setActiveTab(layer)}
            >
              {titles[index]}
            </div>
          )
        })}
      </div>

      <div className="layer-grid">
        {activeTab === 'layer1' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
              <div>
                <h2 className="card-title">
                  <span style={{color: 'var(--accent-primary)'}}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                  </span> 
                  Requirements Extraction
                </h2>
                <p className="card-description" style={{marginBottom: 0}}>
                  Extracting hard constraints and soft preferences based on internal BOM history and regulatory standards.
                </p>
              </div>
              <button 
                className="btn-primary" 
                onClick={() => runTest('layer1', '/api/layer1?ingredient=Ascorbic+Acid')}
                disabled={loading['layer1']}
              >
                {loading['layer1'] ? 'Running Engine...' : 'Run Layer 1 Test'}
              </button>
            </div>
            
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: results['layer1'] ? 'flex-start' : 'center', justifyContent: results['layer1'] ? 'flex-start' : 'center' }}>
              {loading['layer1'] ? (
                <div style={{ textAlign: 'center', color: 'var(--accent-primary)' }}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="spin" style={{animation: 'spin 1.5s linear infinite'}}><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
                  <p style={{marginTop: '1rem'}}>Executing LLM extraction pipeline...</p>
                </div>
              ) : results['layer1'] ? (
                <pre style={{ width: '100%', color: '#A0A0A0', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                  {JSON.stringify(results['layer1'], null, 2)}
                </pre>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '12px', opacity: 0.5 }}><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                  <p>Click "Run Layer 1 Test" to simulate python engine.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'layer2' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
              <div>
                <h2 className="card-title">
                  <span style={{color: 'var(--accent-primary)'}}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                  </span> 
                  Competitor Discovery Pipeline
                </h2>
                <p className="card-description" style={{marginBottom: 0}}>
                  Agentic search executing to find functional substitutes from external market data and existing supplier catalogs.
                </p>
              </div>
              <button 
                className="btn-primary" 
                onClick={() => runTest('layer2', '/api/layer2')}
                disabled={loading['layer2']}
              >
                {loading['layer2'] ? 'Running Agents...' : 'Run Layer 2 Test'}
              </button>
            </div>
            
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: results['layer2'] ? 'flex-start' : 'center', justifyContent: results['layer2'] ? 'flex-start' : 'center' }}>
              {loading['layer2'] ? (
                <div style={{ textAlign: 'center', color: 'var(--accent-primary)' }}>
                   <p className="animate-pulse" style={{marginTop: '1rem'}}>Sending parallel queries...</p>
                </div>
              ) : results['layer2'] ? (
                <pre style={{ width: '100%', color: '#aa9', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                  {JSON.stringify(results['layer2'], null, 2)}
                </pre>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                  <p>Awaiting Trigger...</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'layer3' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
              <div>
                <h2 className="card-title">
                  <span style={{color: 'var(--accent-primary)'}}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                  </span> 
                  Traceable Quality Document Verification
                </h2>
                <p className="card-description" style={{marginBottom: 0}}>
                  Comparing extracted compliance fields from Technical Data Sheets (TDS) and Certificates of Analysis (COA).
                </p>
              </div>
              <button 
                className="btn-primary" 
                onClick={() => runTest('layer3', '/api/layer3')}
                disabled={loading['layer3']}
              >
                {loading['layer3'] ? 'Analyzing PDFs...' : 'Run Layer 3 Test'}
              </button>
            </div>
            
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: results['layer3'] ? 'flex-start' : 'center', justifyContent: results['layer3'] ? 'flex-start' : 'center' }}>
              {loading['layer3'] ? (
                <div style={{ textAlign: 'center', color: 'var(--accent-primary)' }}>
                   <p className="animate-pulse" style={{marginTop: '1rem'}}>Extracting text from TDS files...</p>
                </div>
              ) : results['layer3'] ? (
                <pre style={{ width: '100%', color: '#9a9', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                  {JSON.stringify(results['layer3'], null, 2)}
                </pre>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                  <p>Awaiting Trigger...</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'layer4' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
              <div>
                <h2 className="card-title">
                  <span style={{color: 'var(--accent-primary)'}}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                  </span> 
                  Consolidated Sourcing Proposal
                </h2>
                <p className="card-description" style={{marginBottom: 0}}>
                  Aggregated tradeoffs across cost metrics, supplier count reduction, and strict compliance assurance.
                </p>
              </div>
              <button 
                className="btn-primary" 
                onClick={() => runTest('layer4', '/api/layer4')}
                disabled={loading['layer4']}
              >
                {loading['layer4'] ? 'Deciding...' : 'Run Layer 4 Test'}
              </button>
            </div>
            
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: results['layer4'] ? 'flex-start' : 'center', justifyContent: results['layer4'] ? 'flex-start' : 'center' }}>
              {loading['layer4'] ? (
                <div style={{ textAlign: 'center', color: 'var(--accent-primary)' }}>
                   <p className="animate-pulse" style={{marginTop: '1rem'}}>Evaluating consensus...</p>
                </div>
              ) : results['layer4'] ? (
                <pre style={{ width: '100%', color: '#A0C0FF', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                  {JSON.stringify(results['layer4'], null, 2)}
                </pre>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                  <p>Awaiting Trigger...</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
      `}} />
    </div>
  );
}
