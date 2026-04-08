"use client";

import { useState } from "react";

export default function WorkspacePage() {
  const [activeTab, setActiveTab] = useState("layer1");

  return (
    <div>
      <div className="tabs-container">
        <div 
          className={`tab ${activeTab === 'layer1' ? 'active' : ''}`}
          onClick={() => setActiveTab('layer1')}
        >
          1. Requirements
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
          4. Recommendation
        </div>
      </div>

      <div className="layer-grid">
        {activeTab === 'layer1' && (
          <div className="glass-panel" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-cyan)'}}>O</span> 
              Layer 1: Requirements Extractor
            </h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Identifies hard constraints and soft preferences based on internal BOMs and standard references.
            </p>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', minHeight: '150px' }}>
              <em style={{color: '#666'}}>Awaiting Target Ingredient...</em>
            </div>
          </div>
        )}

        {activeTab === 'layer2' && (
          <div className="glass-panel" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-violet)'}}>O</span> 
              Layer 2: Competitor & Discovery
            </h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Extracts supplier candidates from internal knowledge and external scraping.
            </p>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', minHeight: '150px' }}>
              <em style={{color: '#666'}}>Awaiting Requirements...</em>
            </div>
          </div>
        )}

        {activeTab === 'layer3' && (
          <div className="glass-panel" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-cyan)'}}>O</span> 
              Layer 3: Quality Verification
            </h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Analyzes TDS & COA documents from found suppliers to verify quality constraints automatically.
            </p>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', minHeight: '150px' }}>
              <em style={{color: '#666'}}>Awaiting Candidates...</em>
            </div>
          </div>
        )}

        {activeTab === 'layer4' && (
          <div className="glass-panel" style={{ gridColumn: '1 / -1' }}>
            <h2 className="card-title">
              <span style={{color: 'var(--accent-violet)'}}>O</span> 
              Layer 4: Final Recommendation
            </h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Synthesizes gathered evidence and assigns a final Accept/Reject/Condition score.
            </p>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', minHeight: '150px' }}>
              <em style={{color: '#666'}}>Awaiting Verification Results...</em>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
