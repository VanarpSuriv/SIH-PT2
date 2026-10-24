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
  ChevronDown,
  ChevronUp,
  Hash,
  AlertOctagon,
  ArrowLeft,
  Binary,
  Calendar,
  Layers,
  FileSearch,
  Check,
  Info
} from 'lucide-react';

interface DocumentMetadata {
  title?: string;
  author?: string;
  creator?: string;
  producer?: string;
  raw_creation_date?: string;
  normalized_creation_date?: string;
  raw_mod_date?: string;
  normalized_mod_date?: string;
  creation_date?: string;
  mod_date?: string;
  pdf_version?: string;
  is_encrypted: boolean;
  page_count: number;
  sha256_hash: string;
  parsing_warnings?: string[];
  metadata_anomalies?: string[];
  is_signed: boolean;
}

interface DocumentRecord {
  id: string;
  filename: string;
  document_type: string;
  sha256_hash: string;
  page_count: number;
  metadata: DocumentMetadata;
}

interface MetadataEvidenceContext {
  original_values: Record<string, any>;
  normalized_values: Record<string, any>;
  rule_triggered: string;
  rule_title: string;
  reason_for_review: string;
  parsing_warnings: string[];
}

interface HumanReviewDecision {
  decision: 'UNREVIEWED' | 'CONFIRMED_DEFECT' | 'DISMISSED_BENIGN' | 'REQUEST_CLARIFICATION';
  reviewer_notes?: string;
  reviewed_at?: string;
  reviewed_by?: string;
}

interface Finding {
  id: string;
  rule_id: string;
  rule_version: string;
  rule_name: string;
  rule_category?: 'STATUTORY_MANDATE' | 'TECHNICAL_CONSISTENCY' | 'METADATA_INTEGRITY';
  aph_reference?: string;
  severity: string;
  status: string;
  lifecycle?: 'OPEN' | 'IN_REVIEW' | 'RESOLVED' | 'CLOSED';
  claim: string;
  description: string;
  metadata_context?: MetadataEvidenceContext;
  review?: HumanReviewDecision;
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
  const [expandedDocMetadata, setExpandedDocMetadata] = useState<Record<string, boolean>>({});
  const [activeTab, setActiveTab] = useState<'all' | 'statutory' | 'consistency' | 'metadata'>('all');

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
        await handleVerifyChain();
        await loadAuditEvents();
      }
    } catch {
      // Ignore
    } finally {
      setTampering(false);
    }
  };

  const toggleDocMetadata = (docId: string) => {
    setExpandedDocMetadata((prev) => ({
      ...prev,
      [docId]: !prev[docId],
    }));
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
  const flaggedFindings = appCase.findings.filter((f) => f.status === 'FLAGGED');
  const isCompliant = failedFindings.length === 0 && flaggedFindings.length === 0;

  const filteredFindings = appCase.findings.filter((f) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'statutory') return f.rule_category === 'STATUTORY_MANDATE';
    if (activeTab === 'consistency') return f.rule_category === 'TECHNICAL_CONSISTENCY';
    if (activeTab === 'metadata') return f.rule_category === 'METADATA_INTEGRITY' || !!f.metadata_context;
    return true;
  });

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
            Application Date: {appCase.application_date} &bull; {appCase.documents.length} Ingested Documents &bull; {appCase.findings.length} Compliance & Metadata Rules Evaluated
          </p>
        </div>

        {/* Global Compliance Status Chip */}
        <div className="flex items-center gap-3">
          {isCompliant ? (
            <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shadow-sm shadow-emerald-500/10">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold uppercase tracking-wider">VERIFIED COMPLIANT</div>
                <div className="text-[11px] text-emerald-300/80">Zero statutory defects or flags</div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 shadow-sm shadow-rose-500/10">
              <AlertOctagon className="w-5 h-5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold uppercase tracking-wider">ACTION REQUIRED</div>
                <div className="text-[11px] text-rose-300/80">
                  {failedFindings.length} Critical Defect{failedFindings.length === 1 ? '' : 's'} &bull; {flaggedFindings.length} Review Flag{flaggedFindings.length === 1 ? '' : 's'}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Grid: Documents & Metadata on Left + Compliance Findings on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Submitted Documents & Dedicated Metadata Forensics Panel */}
        <div className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-5 rounded-2xl shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-400" />
                <h2 className="text-sm font-semibold text-white">Submitted Documents ({appCase.documents.length})</h2>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">Dedicated PDF Metadata Service</span>
            </div>

            <div className="space-y-3">
              {appCase.documents.map((doc) => {
                const isExpanded = !!expandedDocMetadata[doc.id];
                const meta = doc.metadata || ({} as DocumentMetadata);
                const hasWarnings = (meta.parsing_warnings && meta.parsing_warnings.length > 0) || (meta.metadata_anomalies && meta.metadata_anomalies.length > 0);

                return (
                  <div
                    key={doc.id}
                    className="glass-card p-3.5 rounded-xl border border-slate-800/80 space-y-2 transition-all hover:border-slate-700"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200 uppercase tracking-wide">
                        {doc.document_type.replace('_', ' ')}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {doc.page_count} Page{doc.page_count > 1 ? 's' : ''}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 truncate" title={doc.filename}>{doc.filename}</p>

                    <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
                      <Hash className="w-3 h-3 text-slate-600 flex-shrink-0" />
                      <span className="truncate" title={doc.sha256_hash}>
                        SHA-256: {doc.sha256_hash ? doc.sha256_hash.substring(0, 16) : 'N/A'}...
                      </span>
                    </div>

                    {/* Quick Indicator Badges */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      {meta.pdf_version && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono">
                          PDF v{meta.pdf_version}
                        </span>
                      )}
                      {meta.is_encrypted ? (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
                          Encrypted
                        </span>
                      ) : (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400">
                          Unencrypted
                        </span>
                      )}
                      {hasWarnings && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                          <AlertTriangle className="w-2.5 h-2.5" />
                          <span>Review Flag</span>
                        </span>
                      )}
                    </div>

                    {/* Metadata Toggle Button */}
                    <button
                      onClick={() => toggleDocMetadata(doc.id)}
                      className="w-full mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      <span className="flex items-center gap-1">
                        <Binary className="w-3 h-3" />
                        <span>{isExpanded ? 'Hide Forensic Metadata' : 'Inspect PDF Metadata'}</span>
                      </span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {/* Collapsible Forensic Metadata Details Panel */}
                    {isExpanded && (
                      <div className="mt-2 pt-2 border-t border-slate-800 space-y-2 text-[10px] text-slate-300 font-mono bg-slate-950/70 p-2.5 rounded-lg">
                        <div>
                          <span className="text-slate-500 block">Producer:</span>
                          <span className="text-slate-300 break-all">{meta.producer || 'Not specified'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Creator:</span>
                          <span className="text-slate-300 break-all">{meta.creator || 'Not specified'}</span>
                        </div>

                        <div className="grid grid-cols-1 gap-1.5 pt-1 border-t border-slate-800/60">
                          <div>
                            <span className="text-slate-500 block">Raw CreationDate:</span>
                            <span className="text-amber-300/90 break-all">{meta.raw_creation_date || 'None'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Normalized CreationDate:</span>
                            <span className="text-emerald-300/90">{meta.normalized_creation_date || 'N/A'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Raw ModDate:</span>
                            <span className="text-amber-300/90 break-all">{meta.raw_mod_date || 'None'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Normalized ModDate:</span>
                            <span className="text-emerald-300/90">{meta.normalized_mod_date || 'N/A'}</span>
                          </div>
                        </div>

                        {/* Parsing Warnings List */}
                        {meta.parsing_warnings && meta.parsing_warnings.length > 0 && (
                          <div className="pt-1.5 border-t border-slate-800/60">
                            <span className="text-amber-400 font-bold block mb-1">Parsing Syntax Warnings:</span>
                            <ul className="list-disc pl-3 space-y-0.5 text-slate-400">
                              {meta.parsing_warnings.map((warn, wIdx) => (
                                <li key={wIdx}>{warn}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Non-prejudicial disclaimer */}
                        <div className="pt-1 text-[9px] text-slate-500 italic leading-snug">
                          Note: Metadata inconsistencies flag files for technical review; they do not constitute proof of document forgery.
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
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
                      <span className="text-slate-500 font-mono">{evt.timestamp ? evt.timestamp.split('T')[1].split('.')[0] : ''}</span>
                    </div>
                    <div className="text-slate-500 font-mono truncate">
                      hash: {evt.hash ? evt.hash.substring(0, 20) : ''}...
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Findings & Evidence Cards */}
        <div className="lg:col-span-8 space-y-6">
          <div className="glass-panel p-6 rounded-2xl shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
                <h2 className="text-base font-semibold text-white">
                  Compliance Findings & Regulatory Checks ({appCase.findings.length})
                </h2>
              </div>
              <span className="text-xs text-slate-400">
                Click any finding for Evidence Graph & Highlighting
              </span>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap items-center gap-2 pb-1">
              <button
                onClick={() => setActiveTab('all')}
                className={`text-xs px-3 py-1.5 rounded-xl transition-all ${
                  activeTab === 'all'
                    ? 'bg-blue-600 text-white font-semibold shadow-md shadow-blue-600/20'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                }`}
              >
                All Checks ({appCase.findings.length})
              </button>
              <button
                onClick={() => setActiveTab('statutory')}
                className={`text-xs px-3 py-1.5 rounded-xl transition-all ${
                  activeTab === 'statutory'
                    ? 'bg-blue-600 text-white font-semibold shadow-md shadow-blue-600/20'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Statutory Mandates ({appCase.findings.filter((f) => f.rule_category === 'STATUTORY_MANDATE').length})
              </button>
              <button
                onClick={() => setActiveTab('consistency')}
                className={`text-xs px-3 py-1.5 rounded-xl transition-all ${
                  activeTab === 'consistency'
                    ? 'bg-blue-600 text-white font-semibold shadow-md shadow-blue-600/20'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Technical Consistency ({appCase.findings.filter((f) => f.rule_category === 'TECHNICAL_CONSISTENCY').length})
              </button>
              <button
                onClick={() => setActiveTab('metadata')}
                className={`text-xs px-3 py-1.5 rounded-xl transition-all ${
                  activeTab === 'metadata'
                    ? 'bg-amber-600 text-white font-semibold shadow-md shadow-amber-600/20'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Metadata Integrity ({appCase.findings.filter((f) => f.rule_category === 'METADATA_INTEGRITY' || !!f.metadata_context).length})
              </button>
            </div>

            {filteredFindings.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-sm">
                No findings in this category.
              </div>
            ) : (
              <div className="space-y-3">
                {filteredFindings.map((finding) => {
                  const isFail = finding.status === 'FAIL';
                  const isFlagged = finding.status === 'FLAGGED';
                  const isMetadata = finding.rule_category === 'METADATA_INTEGRITY' || !!finding.metadata_context;

                  // Schema Separation:
                  // 1. Lifecycle
                  const lifecycle = finding.lifecycle || 'OPEN';
                  // 2. Issuer Verification Status
                  const issuerStatus = finding.verification_result?.status;
                  // 3. Human Review Decision
                  const reviewDecision = finding.review?.decision || finding.user_status || 'UNREVIEWED';

                  return (
                    <Link
                      key={finding.id}
                      href={`/application/${appCase.id}/finding/${finding.id}`}
                      className={`block glass-card p-4 rounded-xl border transition-all hover:scale-[1.01] ${
                        isFail
                          ? 'border-rose-500/40 hover:border-rose-400 hover:bg-rose-950/20'
                          : isMetadata
                          ? 'border-amber-500/40 hover:border-amber-400 hover:bg-amber-950/20'
                          : 'border-slate-800/80 hover:border-blue-500/40 hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                        <div className="flex flex-wrap items-center gap-2">
                          {/* Finding Status Badge */}
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider font-mono ${
                              isFail
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : isFlagged
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}
                          >
                            {finding.status}
                          </span>

                          {/* Rule ID & Version */}
                          <span className="text-xs font-mono font-semibold text-slate-300">
                            {finding.rule_id} v{finding.rule_version}
                          </span>

                          {/* Rule Category Badge */}
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                              finding.rule_category === 'STATUTORY_MANDATE'
                                ? 'bg-blue-500/15 text-blue-300 border border-blue-500/25'
                                : finding.rule_category === 'METADATA_INTEGRITY'
                                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/25'
                                : 'bg-purple-500/15 text-purple-300 border border-purple-500/25'
                            }`}
                          >
                            {finding.rule_category === 'STATUTORY_MANDATE'
                              ? 'Statutory Mandate'
                              : finding.rule_category === 'METADATA_INTEGRITY'
                              ? 'Metadata Integrity'
                              : 'Technical Consistency'}
                          </span>

                          {/* Severity Badge */}
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

                        {/* Lifecycle & Review Badges */}
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                            lifecycle === 'RESOLVED'
                              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/30'
                              : lifecycle === 'IN_REVIEW'
                              ? 'bg-amber-950/60 text-amber-300 border border-amber-500/30'
                              : 'bg-slate-800 text-slate-400'
                          }`}>
                            Lifecycle: {lifecycle}
                          </span>

                          {reviewDecision !== 'UNREVIEWED' && (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                              {reviewDecision}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Rule Name & AICTE Handbook Reference */}
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-slate-200">{finding.rule_name}</h3>
                        {finding.aph_reference && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 font-mono">
                            Ref: {finding.aph_reference}
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">{finding.claim}</p>

                      {/* Metadata Forensic Banner if Present */}
                      {finding.metadata_context && (
                        <div className="mt-2.5 p-2 rounded-lg bg-amber-950/30 border border-amber-500/30 text-[11px] text-amber-200/90 flex items-start gap-2">
                          <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold block text-amber-300">
                              Review Reason: {finding.metadata_context.reason_for_review}
                            </span>
                            <span className="text-[10px] text-slate-400 italic">
                              Advisory: Metadata anomalies flag files for technical review; they do not constitute proof of document forgery.
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Issuer Verification Result Banner */}
                      {finding.verification_result && (
                        <div className="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            {finding.verification_result.source}
                          </span>
                          <span className="font-semibold text-slate-200">
                            [{finding.verification_result.status.toUpperCase()}]:
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
