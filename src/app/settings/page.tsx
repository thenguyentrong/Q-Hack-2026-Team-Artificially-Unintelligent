"use client";

import { useState } from "react";

export default function SettingsPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  const runDiagnostics = async () => {
    setLoading(true);
    setResults(null);
    try {
      const res = await fetch("/api/health/keys");
      
      let data;
      try {
        data = await res.json();
      } catch (parseError) {
        // If Vercel or local Proxy throws a 504 HTML page due to dead backend or timeouts
        throw new Error(`Server returned a non-JSON framework error (Status: ${res.status}). Verify your FastAPI backend is actually running natively!`);
      }
      
      if (!res.ok && data.error) {
        throw new Error(data.detail || data.error);
      }
      
      setResults(data);
    } catch (err: any) {
      setResults({
        error: true,
        detail: err.message
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tab-pane active fade-in" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: "600", marginBottom: "0.5rem" }}>System Diagnostics</h2>
        <p style={{ color: "rgba(255, 255, 255, 0.6)", lineHeight: "1.6" }}>
          Verify that your local environment variables and API tokens are correctly injected into the backend engines.
        </p>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "3rem" }}>
        <button 
          className="btn-primary" 
          onClick={runDiagnostics} 
          disabled={loading}
          style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          {loading ? (
            <div className="spinner" style={{ width: "16px", height: "16px", borderWidth: "2px" }}></div>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
          )}
          {loading ? "Running Network Protocol..." : "Run Diagnostics"}
        </button>
      </div>

      {results && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          
          {/* Gemini AI Integration */}
          <div className="action-card" style={{ padding: "1.5rem", borderLeft: results.gemini?.pass ? "4px solid #10b981" : "4px solid #ef4444" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid rgba(255,255,255,0.1)" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={results.gemini?.pass ? "#10b981" : "#ef4444"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2v20"></path><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                  </svg>
                </div>
                <div>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Gemini Generative AI</h3>
                  <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.5)", marginTop: "0.25rem" }}>Agent reasoning framework connection</div>
                </div>
              </div>
              <div style={{ 
                padding: "0.25rem 0.75rem", 
                borderRadius: "999px", 
                fontSize: "0.75rem", 
                fontWeight: "600", 
                backgroundColor: results.gemini?.pass ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                color: results.gemini?.pass ? "#10b981" : "#ef4444",
                border: results.gemini?.pass ? "1px solid rgba(16, 185, 129, 0.2)" : "1px solid rgba(239, 68, 68, 0.2)"
              }}>
                {results.gemini?.status || "Error"}
              </div>
            </div>

            <div style={{ padding: "1rem", backgroundColor: "rgba(0,0,0,0.3)", borderRadius: "8px", fontSize: "0.9rem", color: "rgba(255,255,255,0.8)", border: "1px solid rgba(255,255,255,0.05)" }}>
              <div style={{ marginBottom: "0.5rem" }}><strong>Key Injected:</strong> {results.gemini?.key_present ? "✅ Yes" : "❌ No"}</div>
              <div><strong>Network Response:</strong> <span style={{ fontFamily: "monospace", color: results.gemini?.pass ? "#10b981" : "#ef4444" }}>{results.gemini?.detail}</span></div>
            </div>
          </div>

          {/* Google Search Integration */}
          <div className="action-card" style={{ padding: "1.5rem", borderLeft: (results.google_search?.api_key_present && results.google_search?.cse_id_present) ? "4px solid #10b981" : "4px solid #f59e0b" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid rgba(255,255,255,0.1)" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                </div>
                <div>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Google Custom Search</h3>
                  <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.5)", marginTop: "0.25rem" }}>Competitor discovery internet access</div>
                </div>
              </div>
              <div style={{ 
                padding: "0.25rem 0.75rem", 
                borderRadius: "999px", 
                fontSize: "0.75rem", 
                fontWeight: "600", 
                backgroundColor: "rgba(245, 158, 11, 0.1)",
                color: "#f59e0b",
                border: "1px solid rgba(245, 158, 11, 0.2)"
              }}>
                {(results.google_search?.api_key_present && results.google_search?.cse_id_present) ? "Active" : "Incomplete"}
              </div>
            </div>

            <div style={{ padding: "1rem", backgroundColor: "rgba(0,0,0,0.3)", borderRadius: "8px", fontSize: "0.9rem", color: "rgba(255,255,255,0.8)", border: "1px solid rgba(255,255,255,0.05)" }}>
              <div style={{ marginBottom: "0.5rem" }}><strong>Google API Key:</strong> {results.google_search?.api_key_present ? "✅ Present" : "❌ Missing"}</div>
              <div style={{ marginBottom: "0.5rem" }}><strong>Search Engine ID (CSE):</strong> {results.google_search?.cse_id_present ? "✅ Present" : "❌ Missing"}</div>
              <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.5)", fontStyle: "italic", marginTop: "0.75rem" }}>
                {results.google_search?.detail} Note: To avoid burning your quota, the live test only verifies key formatting, not network connection.
              </div>
            </div>
          </div>

          {/* Raw Dump */}
          <div style={{ marginTop: "1rem" }}>
            <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.4)", marginBottom: "0.5rem" }}>RAW PAYLOAD:</div>
            <pre style={{ backgroundColor: "rgba(0,0,0,0.5)", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)", margin: 0, color: "rgba(255,255,255,0.7)", overflowX: "auto", fontSize: "0.85rem" }}>
              {JSON.stringify(results, null, 2)}
            </pre>
          </div>

        </div>
      )}
    </div>
  );
}
