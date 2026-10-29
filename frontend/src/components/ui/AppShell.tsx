'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldCheck,
  LayoutDashboard,
  Inbox,
  FileCheck2,
  Sparkles,
  History,
  BookOpen,
  Menu,
  X,
  ExternalLink,
  Lock,
  ChevronRight,
  HelpCircle,
  AlertCircle
} from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * Enterprise Application Shell providing responsive sidebar navigation,
 * active route state tracking, breadcrumb hierarchy, and officer security context.
 *
 * @param children - Main viewport content.
 */
export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    {
      name: 'Overview',
      href: '/',
      icon: LayoutDashboard,
      description: 'Executive triage & intake desk'
    },
    {
      name: 'Application Queue',
      href: '/applications',
      icon: Inbox,
      description: 'Scrutiny backlog & cases'
    },
    {
      name: 'Regulatory Rules',
      href: '/rules',
      icon: BookOpen,
      description: 'AICTE APH 2024-2027 norms'
    },
    {
      name: 'Forensic Diagnostics',
      href: '/forensics',
      icon: Sparkles,
      description: 'ELA & signal tampering checks'
    },
    {
      name: 'Audit Trail',
      href: '/audit',
      icon: History,
      description: 'Tamper-evident hash chain'
    }
  ];

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  // Derive dynamic breadcrumb
  const getBreadcrumbs = () => {
    const parts = pathname.split('/').filter(Boolean);
    const crumbs = [{ label: 'VERITAS', href: '/' }];

    if (parts.length === 0) {
      return crumbs;
    }

    if (parts[0] === 'applications') {
      crumbs.push({ label: 'Application Queue', href: '/applications' });
    } else if (parts[0] === 'application' && parts[1]) {
      crumbs.push({ label: 'Application Queue', href: '/applications' });
      crumbs.push({ label: parts[1].length > 18 ? `${parts[1].slice(0, 18)}...` : parts[1], href: `/application/${parts[1]}` });

      if (parts[2] === 'finding' && parts[3]) {
        crumbs.push({ label: `Finding ${parts[3].slice(0, 8)}`, href: `/application/${parts[1]}/finding/${parts[3]}` });
      }
    } else if (parts[0] === 'rules') {
      crumbs.push({ label: 'Regulatory Rules', href: '/rules' });
    } else if (parts[0] === 'forensics') {
      crumbs.push({ label: 'Forensic Diagnostics', href: '/forensics' });
    } else if (parts[0] === 'audit') {
      crumbs.push({ label: 'Cryptographic Audit Trail', href: '/audit' });
    }

    return crumbs;
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row text-slate-900">
      {/* Mobile Top Navigation */}
      <header className="md:hidden bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between sticky top-0 z-40">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
            V
          </div>
          <div>
            <div className="font-semibold text-sm text-slate-900 tracking-tight">VERITAS</div>
            <div className="text-[10px] text-slate-500 font-medium">AICTE Regulatory Engine</div>
          </div>
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus-ring"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Desktop Sidebar / Mobile Drawer */}
      <aside
        className={`${
          mobileMenuOpen ? 'block' : 'hidden'
        } md:flex flex-col w-full md:w-64 bg-white border-r border-slate-200 shrink-0 z-30 md:sticky md:top-0 md:h-screen`}
      >
        {/* Brand Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm group-hover:bg-blue-700 transition-colors">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="font-semibold text-sm text-slate-900 tracking-tight flex items-center gap-1.5">
                VERITAS
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-medium border border-blue-200">
                  2026
                </span>
              </div>
              <div className="text-xs text-slate-500 font-normal">Regulatory Intelligence</div>
            </div>
          </Link>
        </div>

        {/* Environment Disclosure Badge */}
        <div className="px-4 py-2.5 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider">
              Simulated Sandbox
            </span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">APH 2024–27</span>
        </div>

        {/* Primary Navigation Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-blue-50 text-blue-700 border border-blue-100 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-blue-600' : 'text-slate-400'}`} />
                <div className="flex-1">
                  <div>{item.name}</div>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Officer Security & Governance Context */}
        <div className="p-3.5 border-t border-slate-200 bg-slate-50 text-xs space-y-2">
          <div className="flex items-center justify-between text-slate-600">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-500">Officer Context</span>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium border border-emerald-200 text-[10px]">
              <Lock className="w-2.5 h-2.5" />
              Token Verified
            </span>
          </div>
          <div className="bg-white p-2.5 rounded-md border border-slate-200/80 space-y-1 text-slate-700">
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-500">Role:</span>
              <span className="font-semibold text-slate-900">SCRUTINY_OFFICER</span>
            </div>
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-500">Authority:</span>
              <span>AICTE EOA Regional</span>
            </div>
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-500">Mode:</span>
              <span className="text-amber-700 font-medium">Decision Support</span>
            </div>
          </div>
          <p className="text-[10px] text-slate-400 leading-tight">
            Automated signals assist authorized officers. Final statutory decision remains with competent authority.
          </p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Application Bar */}
        <header className="hidden md:flex items-center justify-between px-6 py-3 bg-white border-b border-slate-200 sticky top-0 z-20">
          {/* Breadcrumb Trail */}
          <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
            {getBreadcrumbs().map((crumb, idx, arr) => (
              <React.Fragment key={crumb.href}>
                {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                {idx === arr.length - 1 ? (
                  <span className="font-semibold text-slate-800">{crumb.label}</span>
                ) : (
                  <Link href={crumb.href} className="hover:text-blue-600 transition-colors">
                    {crumb.label}
                  </Link>
                )}
              </React.Fragment>
            ))}
          </nav>

          {/* Right Header Affordances */}
          <div className="flex items-center gap-3">
            <a
              href="https://www.aicte-india.org/sites/default/files/APH%20Final.pdf"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-blue-600 px-2.5 py-1 rounded border border-slate-200 hover:border-blue-300 transition-colors"
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-400" />
              <span>APH 2024–27</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>

            <div className="h-4 w-px bg-slate-200" />

            <div className="flex items-center gap-2 text-xs text-slate-600">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="font-medium text-slate-700">Service Online (Backend)</span>
            </div>
          </div>
        </header>

        {/* Dynamic Page Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
