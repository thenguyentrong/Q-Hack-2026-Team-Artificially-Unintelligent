import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agnes | AI Supply Chain Engine",
  description: "Intelligent supplier consolidation and ingredient analysis powered by multi-agent AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="layout-container">
          <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-header">
              <div className="logo-mark">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              </div>
              <div className="logo-text">Agnes <span>AI</span></div>
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
              <div className="nav-group-label">Workspace</div>

              <Link href="/" className="nav-item" id="nav-workspace">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                Ingredient Analysis
                <span className="nav-badge">AI</span>
              </Link>

              <div className="nav-item" id="nav-dashboard" style={{ cursor: 'default', opacity: 0.4 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
                  <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
                </svg>
                Dashboard
                <span className="nav-badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-tertiary)', borderColor: 'transparent' }}>Soon</span>
              </div>

              <div className="nav-item" id="nav-catalog" style={{ cursor: 'default', opacity: 0.4 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
                Ingredient Catalog
                <span className="nav-badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-tertiary)', borderColor: 'transparent' }}>Soon</span>
              </div>

              <div className="nav-group-label" style={{ marginTop: '1.25rem' }}>System</div>

              <Link href="/settings" className="nav-item" id="nav-settings">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                Diagnostics
              </Link>
            </nav>

            {/* Footer */}
            <div className="sidebar-footer">
              <div className="system-status">
                <div className="status-dot" id="sidebar-status-dot" />
                <span id="sidebar-status-text">Agnes Engine Ready</span>
              </div>
            </div>
          </aside>

          <main className="main-content">
            <header className="topbar">
              <div className="topbar-left">
                <div className="topbar-title">Supplier Consolidation Engine</div>
                <span className="topbar-crumb" style={{ color: 'var(--border-subtle)' }}>·</span>
                <span className="topbar-crumb">Agnes v2</span>
              </div>
              <div className="topbar-right">
                <Link href="/settings">
                  <button className="btn-ghost" id="topbar-diagnostics-btn">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg>
                    Diagnostics
                  </button>
                </Link>
                <button className="btn-primary" id="topbar-new-analysis-btn">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  New Analysis
                </button>
              </div>
            </header>

            <div className="content-area">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
