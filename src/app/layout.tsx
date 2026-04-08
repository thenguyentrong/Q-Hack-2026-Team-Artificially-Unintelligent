import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agnes Workspace",
  description: "AI Supply Chain Manager",
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
            <div className="logo-container">
              <div className="logo-icon"></div>
              <div className="logo-text">Agnes</div>
            </div>
            <nav className="nav-menu">
              <div className="nav-item">🌍 Dashboard (Layer 0)</div>
              <div className="nav-item active">⚡ Workspace (Layers 1-4)</div>
              <div className="nav-item">📄 Evidence Vault</div>
              <div className="nav-item">⚙️ Settings</div>
            </nav>
          </aside>
          
          <main className="main-content">
            <header className="topbar">
              <div className="topbar-title">Ingredient Consolidation Analysis</div>
              <div>
                <button className="btn-primary">New Analysis</button>
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
