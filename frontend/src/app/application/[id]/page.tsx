'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ShieldCheck,
  AlertTriangle,
  FileText,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Database,
  Lock,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Hash,
  AlertOctagon,
  ArrowLeft
} from 'lucide-react';

interface DocumentRecord {
  id: string;
  filename: string;
  document_type: string;
  sha256_hash: string;
  page_count: number;
  metadata: {
    is_signed: boolean;
    title?: string;
  };
}

interface Finding {
  id: string;
  rule_id: string;
  rule_version: string;
  rule_name: string;
  severity: string;
  status: string;
  claim: string;
  description: string;
  user_status: string;
  verification_result?: {
    status: string;
    source: string;
    message: string;
  };
}

interface ApplicationCase {
  id: string;
  institution_name: string;
  application_date: string;
  status: string;
  documents: DocumentRecord[];
  findings: Finding[];
}

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appId = params?.id as string;

  const [appCase, setAppCase] = useState<ApplicationCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [chainVerification, setChainVerification] = useState<any | null>(null);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [tampering, setTampering] = useState(false);
  const [showAudit, setShowAudit] = useState(false);

  useEffect(() => {
    if (appId) {
      loadApplication();
    }
  }, [appId]);

  const loadApplication = async () => {
    try {
      setLoading(true);
      const res = await fetch(`http://localhost:8000/api/applications/${appId}`);
      if (!res.ok) throw new Error('Failed to retrieve application details');
      const data = await res.json();
      setAppCase(data);
      loadAuditEvents();
    } catch (err: any) {
      setError(err.message || 'Error fetching application');
    } finally {
      setLoading(false);
    }
  };

  const loadAuditEvents = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/audit?application_id=${appId}`);
      if (res.ok) {
        const events = await res.json();
        setAuditEvents(events);
      }
    } catch {
      // Ignore background audit load errors
    }
  };

  const handleVerifyChain = async () => {
    try {
      setVerifyingChain(true);
      const res = await fetch('http://localhost:8000/api/audit/verify');
      const data = await res.json();
      setChainVerification(data);
    } catch (err: any) {
      setChainVerification({ is_valid: false, reason: 'Failed to communicate with audit service' });
    } finally {
      setVerifyingChain(false);
    }
  };

  const handleTamperDemo = async () => {
    if (auditEvents.length === 0) return;
    try {
      setTampering(true);
      const targetEventId = auditEvents[0].id;
      const formData = new FormData();
      formData.append('event_id', targetEventId);

      const res = await fetch('http://localhost:8000/api/audit/tamper', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        // Automatically re-verify chain to show live failure
        await handleVerifyChain();
        await loadAuditEvents();
      }
    } catch {
      // Ignore
    } finally {
      setTampering(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400 mb-3" />
        <p className="text-slate-300 font-medium">Reconciling Regulatory Evidence Graph...</p>
      </div>
    );
  }

  if (error || !appCase) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Application Record Not Found</h2>
        <p className="text-slate-400 text-sm">{error}</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-sm hover:bg-slate-700"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Upload</span>
        </Link>
      </div>
    );
  }

  const failedFindings = appCase.findings.filter((f) => f.status === 'FAIL');
  const passedFindings = appCase.findings.filter((f) => f.status === 'PASS');
  const isCompliant = failedFindings.length === 0;

  return (
    <div className="space-y-8">
      {/* Top Breadcrumb & Status Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-6 rounded-2xl shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Link href="/" className="hover:text-blue-400 transition-colors">
              Applications
            </Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="font-mono text-slate-300">{appCase.id}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {appCase.institution_name}
          </h1>
          <p className="text-xs text-slate-400 font-mono">
            Application Date: {appCase.application_date} &bull; {appCase.documents.length} Uploaded Documents &bull; {appCase.findings.length} Compliance Rules Evaluated
          </p>
        </div>

        {/* Global Compliance Chip */}
        <div className="flex items-center gap-3">
          {isCompliant ? (
            <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shadow-sm shadow-emerald-500/10">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold uppercase tracking-wider">VERIFIED COMPLIANT</div>
                <div className="text-[11px] text-emerald-300/80">No handbook violations detected</div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 shadow-sm shadow-rose-500/10">
              <AlertOctagon className="w-5 h-5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold uppercase tracking-wider">ACTION REQUIRED</div>
                <div className="text-[11px] text-rose-300/80">
                  {failedFindings.length} Critical Flag{failedFindings.length > 1 ? 's' : ''} Identified
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Grid: Documents on Left + Findings on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Uploaded Documents Table */}
        <div className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-5 rounded-2xl shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-400" />
                <h2 className="text-sm font-semibold text-white">Submitted Documents ({appCase.documents.length})</h2>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">PyMuPDF Ingested</span>
            </div>

            <div className="space-y-2.5">
              {appCase.documents.map((doc) => (
                <div
                  key={doc.id}
                  className="glass-card p-3 rounded-xl border border-slate-800/80 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-200 uppercase tracking-wide">
                      {doc.document_type.replace('_', ' ')}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                      {doc.page_count} Page{doc.page_count > 1 ? 's' : ''}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 truncate">{doc.filename}</p>
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
                    <Hash className="w-3 h-3 text-slate-600 flex-shrink-0" />
                    <span className="truncate" title={doc.sha256_hash}>
                      SHA-256: {doc.sha256_hash.substring(0, 16)}...
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cryptographic Audit Trail Card */}
          <div className="glass-panel p-5 rounded-2xl shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-emerald-400" />
                <h2 className="text-sm font-semibold text-white">Audit Trail Integrity</h2>
              </div>
              <button
                onClick={() => setShowAudit(!showAudit)}
                className="text-[11px] text-blue-400 hover:text-blue-300 underline"
              >
                {showAudit ? 'Hide Chain' : 'View Events'}
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Every document ingestion, rule evaluation, and officer decision is immutably appended to a SHA-256 hash chain:
              <code className="block mt-1 p-1.5 rounded bg-slate-900 text-slate-300 font-mono text-[10px]">
                hash = sha256(prev_hash + payload)
              </code>
            </p>

            {chainVerification && (
              <div
                className={`p-3 rounded-xl border text-xs flex items-start gap-2.5 ${
                  chainVerification.is_valid
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                }`}
              >
                {chainVerification.is_valid ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="font-semibold">
                    {chainVerification.is_valid ? 'Chain Cryptographically Valid' : 'Tamper Detected!'}
                  </div>
                  <div className="text-[11px] text-slate-300 mt-0.5">
                    {chainVerification.reason || chainVerification.message}
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={handleVerifyChain}
                disabled={verifyingChain}
                className="flex-1 py-2 px-3 rounded-xl bg-blue-600/90 hover:bg-blue-600 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>{verifyingChain ? 'Verifying...' : 'Verify Chain'}</span>
              </button>

              <button
                onClick={handleTamperDemo}
                disabled={tampering}
                title="Tampers with a row payload to live demo cryptographic detection"
                className="py-2 px-3 rounded-xl bg-rose-950/60 hover:bg-rose-900 border border-rose-800/60 text-rose-300 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <span>Demo Tamper</span>
              </button>
            </div>

            {showAudit && (
              <div className="space-y-2 max-h-56 overflow-y-auto pt-2 border-t border-slate-800">
                <span className="text-[11px] font-semibold text-slate-400 block">
                  Logged Events ({auditEvents.length}):
                </span>
                {auditEvents.map((evt, idx) => (
                  <div key={idx} className="p-2 rounded bg-slate-900/60 border border-slate-800 text-[10px] space-y-1">
                    <div className="flex items-center justify-between text-slate-300 font-semibold">
                      <span>{evt.action}</span>
                      <span className="text-slate-500 font-mono">{evt.timestamp.split('T')[1].split('.')[0]}</span>
                    </div>
                    <div className="text-slate-500 font-mono truncate">
                      hash: {evt.hash.substring(0, 20)}...
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Findings & Evidence Cards */}
        <div className="lg:col-span-8 space-y-6">
          {/* Flagged Findings Section */}
          <div className="glass-panel p-6 rounded-2xl shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
                <h2 className="text-base font-semibold text-white">
                  Compliance Findings & Handbook Checks ({appCase.findings.length})
                </h2>
              </div>
              <span className="text-xs text-slate-400">
                Click any finding for Evidence Graph & Highlighting
              </span>
            </div>

            {appCase.findings.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-sm">
                No findings generated for this application.
              </div>
            ) : (
              <div className="space-y-3">
                {appCase.findings.map((finding) => {
                  const isFail = finding.status === 'FAIL';
                  return (
                    <Link
                      key={finding.id}
                      href={`/application/${appCase.id}/finding/${finding.id}`}
                      className={`block glass-card p-4 rounded-xl border transition-all hover:scale-[1.01] ${
                        isFail
                          ? 'border-rose-500/40 hover:border-rose-400 hover:bg-rose-950/20'
                          : 'border-slate-800/80 hover:border-blue-500/40 hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider font-mono ${
                              isFail
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}
                          >
                            {finding.status}
                          </span>
                          <span className="text-xs font-mono font-semibold text-slate-300">
                            {finding.rule_id} v{finding.rule_version}
                          </span>
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                              finding.severity === 'CRITICAL'
                                ? 'bg-red-500/20 text-red-300'
                                : finding.severity === 'HIGH'
                                ? 'bg-amber-500/20 text-amber-300'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {finding.severity}
                          </span>
                        </div>

                        {/* Reviewer Action Status */}
                        {finding.user_status !== 'UNREVIEWED' && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                            OFFICER {finding.user_status}
                          </span>
                        )}
                      </div>

                      <h3 className="text-sm font-semibold text-slate-200">{finding.rule_name}</h3>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">{finding.claim}</p>

                      {/* Verification Adapter Banner if present */}
                      {finding.verification_result && (
                        <div className="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            {finding.verification_result.source}
                          </span>
                          <span>{finding.verification_result.message}</span>
                        </div>
                      )}

                      <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-blue-400">
                        <span>View Evidence Coordinates & Document Highlighting</span>
                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
