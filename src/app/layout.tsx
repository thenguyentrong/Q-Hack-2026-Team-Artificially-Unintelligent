import type { Metadata } from "next";
import "./globals.css";
import { Manrope, Inter } from "next/font/google";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-display" });
const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Agnes | AI Supply Chain Quality Engine",
  description: "Identify consolidation targets and verify alternatives with Agnes.",
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
    <html lang="en" className={`${manrope.variable} ${inter.variable}`}>
      <body className="bg-[#F8F9FA] text-[#1B263B] antialiased font-sans">
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="w-64 bg-[#1B263B] flex flex-col flex-shrink-0">
            <div className="h-[72px] border-b border-white/10 flex items-center px-5 gap-3">
              <div className="w-7 h-7 bg-white rounded-md flex items-center justify-center">
                <div className="w-3 h-3 bg-[#1B263B] rounded-sm" />
              </div>
              <span className="text-lg font-bold tracking-tight text-white font-display">Agnes</span>
            </div>

            <nav className="flex-1 p-4 space-y-1">
              <div className="text-[11px] uppercase tracking-widest font-semibold text-white/40 mb-3 px-3">
                Operations
              </div>
              <Link
                href="/"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/10 text-white text-sm font-medium shadow-[inset_3px_0_0_#4DA8DA]"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                Agnes Workspace
              </Link>
            </nav>
          </aside>

          {/* Main area */}
          <main className="flex-1 flex flex-col min-w-0">
            <header className="h-[72px] bg-white border-b border-[#E2E4E9] flex items-center justify-between px-6 flex-shrink-0 sticky top-0 z-10">
              <span className="text-base font-semibold font-display text-[#1B263B]">Supplier Consolidation Engine</span>
            </header>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
