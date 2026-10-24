import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';
import { ShieldCheck, FileCheck, Layers, Cpu, Database } from 'lucide-react';

export const metadata: Metadata = {
  title: 'AICTE EoA Verification Engine | Regulatory Document Intelligence',
  description: 'Evidence Graph & Hash-Chained Audit Compliance for AICTE Extension of Approval',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-blue-600 selection:text-white">
        {/* Navigation Bar */}
        <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 px-6 py-3.5 shadow-lg">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="p-2 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform duration-200">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-200 to-white">
                    AICTE EoA Verification Engine
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    SIMULATED ENVIRONMENT
                  </span>
                </div>
                <p className="text-xs text-slate-400 hidden sm:block">
                  Automated Evidence Graphing & Cryptographic Audit Trail
                </p>
              </div>
            </Link>

            <nav className="flex items-center gap-4">
              <Link
                href="/"
                className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white px-3.5 py-1.5 rounded-lg hover:bg-slate-800/60 transition-colors"
              >
                <FileCheck className="w-4 h-4 text-blue-400" />
                <span>Upload & Cases</span>
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500 glass-panel mt-auto">
          <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p>AICTE Approval Process Handbook (EoA) Compliance Engine &copy; 2025-2026</p>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 text-slate-400">
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                Immutable SHA-256 Chained Log
              </span>
              <span>&bull;</span>
              <span className="inline-flex items-center gap-1.5 text-slate-400">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                PyMuPDF Coordinate Evidence Graph
              </span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
