import type { Metadata } from "next";
import "./globals.css";
import SideNav from "./side-nav";

export const metadata: Metadata = {
  title: "Agnes | Procurement Intelligence",
  description: "AI-powered supplier consolidation engine for procurement teams.",
};

const STEPS = [
  { label: "Selection", num: 1 },
  { label: "Requirements", num: 2 },
  { label: "Verification", num: 3 },
  { label: "Decision", num: 4 },
];

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="light">
      <body className="bg-background text-on-background antialiased flex min-h-screen">
        <SideNav />

        {/* Main content */}
        <div className="flex-1 ml-64 flex flex-col min-h-screen">


          <main className="flex-1 p-8">
            {children}
          </main>

          {/* Footer */}
          <footer className="border-t border-surface-container bg-white px-8 py-4 sticky bottom-0 z-20">
            <div className="max-w-7xl mx-auto flex justify-between items-center">
              <span className="text-xs font-bold text-on-surface-variant flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-tertiary inline-block" />
                Agnes Engine · Active
              </span>
              <div className="flex items-center gap-3">
                <button className="px-5 py-2 rounded-lg text-sm font-bold text-on-surface-variant border border-outline-variant/30 hover:bg-surface-container transition-all">
                  Save Progress
                </button>
                <button className="primary-gradient text-on-primary px-7 py-2 rounded-lg text-sm font-bold shadow-lg hover:opacity-90 transition-all">
                  Execute Decision
                </button>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
