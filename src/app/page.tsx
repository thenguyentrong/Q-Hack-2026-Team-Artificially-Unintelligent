"use client";

import { useState } from "react";

export default function WorkspacePage() {
  const [activeTab, setActiveTab] = useState("layer1");

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
        <div 
          className={`tab ${activeTab === 'layer1' ? 'active' : ''}`}
          onClick={() => setActiveTab('layer1')}
        >
          1. Requirements Inference
        </div>
        <div 
          className={`tab ${activeTab === 'layer2' ? 'active' : ''}`}
          onClick={() => setActiveTab('layer2')}
        >
          2. Supplier Discovery
        </div>
        <div 
          className={`tab ${activeTab === 'layer3' ? 'active' : ''}`}
          onClick={() => setActiveTab('layer3')}
        >
          3. Quality Verification
        </div>
        <div 
          className={`tab ${activeTab === 'layer4' ? 'active' : ''}`}
          onClick={() => setActiveTab('layer4')}
        >
          4. Consensus & Decision
        </div>
      </div>

      <div className="layer-grid">
        {activeTab === 'layer1' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-primary)'}}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
              </span> 
              Requirements Extraction
            </h2>
            <p className="card-description">
              Extracting hard constraints and soft preferences based on internal BOM history and regulatory standards.
            </p>
            
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '12px', opacity: 0.5 }}><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                <p>Waiting for Target Component...</p>
              </div>
            </div>
          </div>
        )}

        {/* Keeping similar structure for the other tabs, matched to new CSS */}
        {activeTab === 'layer2' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-primary)'}}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
              </span> 
              Competitor Discovery Pipeline
            </h2>
            <p className="card-description">
              Agentic search executing to find functional substitutes from external market data and existing supplier catalogs.
            </p>
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                <p>Pending Requirements Layer completion...</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'layer3' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-primary)'}}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
              </span> 
              Traceable Quality Document Verification
            </h2>
            <p className="card-description">
              Comparing extracted compliance fields from Technical Data Sheets (TDS) and Certificates of Analysis (COA).
            </p>
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                <p>Pending Evidence retrieval...</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'layer4' && (
          <div className="glass-panel animate-in" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-primary)'}}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
              </span> 
              Consolidated Sourcing Proposal
            </h2>
            <p className="card-description">
              Aggregated tradeoffs across cost metrics, supplier count reduction, and strict compliance assurance.
            </p>
            <div style={{ background: '#060606', border: '1px solid var(--border-subtle)', padding: '1.5rem', borderRadius: '12px', minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                <p>Awaiting Consensus Engine...</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
