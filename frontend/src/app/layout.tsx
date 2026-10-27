import type { Metadata } from 'next';
import './globals.css';
import { AppShell } from '@/components/ui/AppShell';

export const metadata: Metadata = {
  title: 'VERITAS | AICTE EoA Document Intelligence & Regulatory Verification Platform',
  description:
    'Evidence-driven AICTE Approval Process Handbook (APH) compliance verification, document forensics, external registry validation, and tamper-evident audit trail.',
};

/**
 * Root Layout wrapping the entire application in the enterprise AppShell.
 *
 * @param children - Active page node.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased selection:bg-blue-100 selection:text-blue-900">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
