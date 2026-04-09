"use client";

import { useState } from "react";

type KeyResult = { pass?: boolean; key_present?: boolean; detail?: string; status?: string; api_key_present?: boolean; cse_id_present?: boolean };
type DiagResult = { error?: boolean; detail?: string; gemini?: KeyResult; google_search?: KeyResult };

export default function SettingsPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DiagResult | null>(null);

  const runDiagnostics = async () => {
    setLoading(true);
    setResults(null);
    try {
      const res = await fetch("/api/py/health/keys");
      const text = await res.text();
      let data: DiagResult;
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(`Non-JSON response (${res.status}): ${text.substring(0, 300)}`);
      }
      if (!res.ok && data.error) throw new Error(data.detail || "Unknown error");
      setResults(data);
    } catch (err: any) {
      setResults({ error: true, detail: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2 text-xs font-medium text-outline-variant">
          <span>System</span>
          <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          <span className="text-primary font-bold">Diagnostics</span>
        </div>
        <h1 className="text-3xl font-extrabold text-on-surface tracking-tight">System Diagnostics</h1>
        <p className="text-on-surface-variant mt-1 text-sm">
          Verify that your environment variables and API tokens are correctly injected into the backend engines.
        </p>
      </div>

      <button
        onClick={runDiagnostics}
        disabled={loading}
        className="primary-gradient text-on-primary px-6 py-3 rounded-xl font-bold text-sm shadow-lg hover:opacity-90 transition-all disabled:opacity-60 flex items-center gap-2 mb-10"
      >
        {loading ? (
          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
        ) : (
          <span className="material-symbols-outlined text-[18px]">monitor_heart</span>
        )}
        {loading ? "Running Network Protocol..." : "Run Diagnostics"}
      </button>

      {results && (
        <div className="space-y-4">
          {/* Error state */}
          {results.error && (
            <div className="bg-error-container/10 border border-error/20 rounded-xl p-6">
              <div className="flex items-center gap-3 mb-3">
                <span className="material-symbols-outlined text-error text-xl fill-icon">error_outline</span>
                <h3 className="font-bold text-on-surface">Backend Unreachable</h3>
              </div>
              <p className="text-xs text-on-surface-variant font-mono break-all">{results.detail}</p>
            </div>
          )}

          {/* Gemini */}
          {results.gemini && (
            <div className={`bg-surface-container-lowest rounded-xl p-6 border-l-4 shadow-sm ${results.gemini.pass ? "border-tertiary" : "border-error"}`}>
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${results.gemini.pass ? "bg-tertiary-container" : "bg-error-container/20"}`}>
                    <span className={`material-symbols-outlined fill-icon ${results.gemini.pass ? "text-tertiary" : "text-error"}`}>
                      {results.gemini.pass ? "verified" : "error_outline"}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-bold text-on-surface">Gemini Generative AI</h3>
                    <p className="text-xs text-on-surface-variant">Agent reasoning framework connection</p>
                  </div>
                </div>
                <span className={`text-[0.7rem] font-bold px-3 py-1 rounded-full ${results.gemini.pass ? "bg-tertiary-container text-on-tertiary-container" : "bg-error-container/20 text-on-error-container"}`}>
                  {results.gemini.status || (results.gemini.pass ? "Active" : "Error")}
                </span>
              </div>
              <div className="bg-surface-container-low rounded-lg p-4 text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-on-surface-variant font-medium">Key Injected</span>
                  <span className={`font-bold ${results.gemini.key_present ? "text-tertiary" : "text-error"}`}>
                    {results.gemini.key_present ? "✅ Yes" : "❌ No"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant font-medium">Network Response</span>
                  <span className={`font-mono text-xs ${results.gemini.pass ? "text-tertiary" : "text-error"}`}>
                    {results.gemini.detail}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Google Search */}
          {results.google_search && (
            <div className={`bg-surface-container-lowest rounded-xl p-6 border-l-4 shadow-sm ${results.google_search.api_key_present && results.google_search.cse_id_present ? "border-tertiary" : "border-outline-variant"}`}>
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center">
                    <span className="material-symbols-outlined text-outline">search</span>
                  </div>
                  <div>
                    <h3 className="font-bold text-on-surface">Google Custom Search</h3>
                    <p className="text-xs text-on-surface-variant">Competitor discovery internet access</p>
                  </div>
                </div>
                <span className={`text-[0.7rem] font-bold px-3 py-1 rounded-full ${results.google_search.api_key_present && results.google_search.cse_id_present ? "bg-tertiary-container text-on-tertiary-container" : "bg-surface-container text-on-surface-variant"}`}>
                  {results.google_search.api_key_present && results.google_search.cse_id_present ? "Active" : "Incomplete"}
                </span>
              </div>
              <div className="bg-surface-container-low rounded-lg p-4 text-sm space-y-2">
                {[
                  { label: "Google API Key", ok: results.google_search.api_key_present },
                  { label: "Search Engine ID (CSE)", ok: results.google_search.cse_id_present },
                ].map((item) => (
                  <div key={item.label} className="flex justify-between">
                    <span className="text-on-surface-variant font-medium">{item.label}</span>
                    <span className={`font-bold ${item.ok ? "text-tertiary" : "text-error"}`}>
                      {item.ok ? "✅ Present" : "❌ Missing"}
                    </span>
                  </div>
                ))}
                <p className="text-xs text-on-surface-variant italic mt-2 pt-2 border-t border-surface-container">
                  Note: Live test verifies key formatting only, not network connection.
                </p>
              </div>
            </div>
          )}

          {/* Raw Payload */}
          <details className="bg-surface-container-lowest rounded-xl border border-surface-container">
            <summary className="px-6 py-4 text-sm font-bold text-on-surface-variant cursor-pointer hover:text-on-surface transition-colors">
              Raw Payload
            </summary>
            <pre className="px-6 pb-4 text-xs text-on-surface-variant overflow-x-auto font-mono">
              {JSON.stringify(results, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
