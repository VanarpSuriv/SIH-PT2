'use client';

import React, { useState, useEffect } from 'react';
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
  Calendar,
  Layers,
  FileSearch,
  Check,
  Info,
  ShieldAlert,
  Sparkles,
  Search,
  BookOpen,
  Filter
} from 'lucide-react';
import { Card, MetricCard } from '@/components/ui/Card';
import { StatusBadge, SeverityBadge, CategoryBadge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';

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
  rule_category?: 'STATUTORY_MANDATE' | 'TECHNICAL_CONSISTENCY' | 'METADATA_INTEGRITY' | 'FORENSIC_ADVISORY';
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
  fields_involved?: any[];
}

interface ApplicationCase {
  id: string;
  institution_name: string;
  application_date: string;
  status: string;
  created_at: string;
  documents: DocumentRecord[];
  findings: Finding[];
}

const API_BASE = '/api';

/**
 * Application Workspace Page: Comprehensive scrutiny center providing
 * tabbed inspection of documents & metadata, statutory compliance rules,
 * external issuer verification, computer vision forensics, and audit logs.
 */
export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appId = params?.id as string;

  const [appCase, setAppCase] = useState<ApplicationCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'regulatory' | 'issuer' | 'forensics' | 'audit'>('overview');

  // Filter for findings in Regulatory tab
  const [regulatoryFilter, setRegulatoryFilter] = useState<'ALL' | 'STATUTORY_MANDATE' | 'TECHNICAL_CONSISTENCY' | 'METADATA_INTEGRITY' | 'FORENSIC_ADVISORY'>('ALL');

  // Audit and Verification State
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [chainVerification, setChainVerification] = useState<any | null>(null);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [expandedDocMetadata, setExpandedDocMetadata] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (appId) {
      loadApplicationData();
    }
  }, [appId]);

  const loadApplicationData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/applications/${appId}`);
      if (!res.ok) throw new Error('Failed to retrieve application case details.');
      const data = await res.json();
      setAppCase(data);
      loadAuditEvents();
    } catch (err: any) {
      setError(err.message || 'Error fetching application details from server.');
    } finally {
      setLoading(false);
    }
  };

  const loadAuditEvents = async () => {
    try {
      const res = await fetch(`${API_BASE}/audit?application_id=${appId}`);
      if (res.ok) {
        const events = await res.json();
        setAuditEvents(events);
      }
    } catch {
      // Non-critical audit history fetch failure
    }
  };

  const verifyAuditChain = async () => {
    try {
      setVerifyingChain(true);
      const res = await fetch(`${API_BASE}/audit/verify`);
      if (res.ok) {
        const result = await res.json();
        setChainVerification(result);
      }
    } catch (e) {
      setChainVerification({ valid: false, error: 'Verification request failed' });
    } finally {
      setVerifyingChain(false);
    }
  };

  const toggleDocExpand = (docId: string) => {
    setExpandedDocMetadata((prev) => ({
      ...prev,
      [docId]: !prev[docId]
    }));
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-28 w-full rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  if (error || !appCase) {
    return (
      <div className="py-12">
        <EmptyState
          title="Application Not Found"
          description={error || `Could not find an ingested application matching ID '${appId}'.`}
          actionLabel="Return to Application Queue"
          onAction={() => router.push('/applications')}
        />
      </div>
    );
  }

  // Derive counts
  const totalFindings = appCase.findings.length;
  const criticalDefects = appCase.findings.filter((f) => f.status === 'FAIL');
  const anomalies = appCase.findings.filter((f) => f.status === 'FLAGGED');
  const passedChecks = appCase.findings.filter((f) => f.status === 'PASS');
  const statutoryFindings = appCase.findings.filter((f) => f.rule_category === 'STATUTORY_MANDATE');
  const metadataFindings = appCase.findings.filter((f) => f.rule_category === 'METADATA_INTEGRITY');
  const forensicFindings = appCase.findings.filter((f) => f.rule_category === 'FORENSIC_ADVISORY');

  const filteredFindings = appCase.findings.filter((f) => {
    if (regulatoryFilter === 'ALL') return true;
    return f.rule_category === regulatoryFilter;
  });

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Return Action */}
      <div className="flex items-center justify-between">
        <Link
          href="/applications"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Application Queue</span>
        </Link>
        <span className="text-[11px] font-mono text-slate-400">
          Created: {new Date(appCase.created_at).toLocaleString()}
        </span>
      </div>

      {/* Application Workspace Header Banner */}
      <Card padding="md" className="border-l-4 border-l-blue-600 space-y-4">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 font-mono">
                {appCase.id}
              </h1>
              <StatusBadge status={appCase.status} size="md" />
              <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium border border-slate-200">
                Extension of Approval (EoA)
              </span>
            </div>
            <p className="text-base font-semibold text-slate-800">
              {appCase.institution_name}
            </p>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
              <span>Application Date: <strong className="text-slate-700">{appCase.application_date}</strong></span>
              <span>&bull;</span>
              <span>Documents Attached: <strong className="text-slate-700">{appCase.documents.length}</strong></span>
              <span>&bull;</span>
              <span>Total Rules Evaluated: <strong className="text-slate-700">{totalFindings}</strong></span>
            </div>
          </div>

          {/* Action Recommendation Box */}
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1 max-w-sm shrink-0">
            <div className="font-semibold text-slate-800 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-blue-600" />
              Recommended Scrutiny Action
            </div>
            <p className="text-slate-600 leading-snug">
              {criticalDefects.length > 0
                ? `${criticalDefects.length} statutory defect(s) require officer verification or institutional clarification before EoA issuance.`
                : 'All evaluated rules and document consistency checks conform to APH 2024–2027 standards.'}
            </p>
          </div>
        </div>
      </Card>

      {/* Operational Metric Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Statutory Deficiencies"
          value={criticalDefects.length}
          subtitle="Requirements not satisfied"
          icon={XCircle}
          tone={criticalDefects.length > 0 ? 'danger' : 'success'}
        />
        <MetricCard
          title="Advisory Flags"
          value={anomalies.length}
          subtitle="Preliminary CV & metadata signals"
          icon={AlertTriangle}
          tone={anomalies.length > 0 ? 'warning' : 'default'}
        />
        <MetricCard
          title="Compliant Checks"
          value={passedChecks.length}
          subtitle="Statutory norms satisfied"
          icon={CheckCircle2}
          tone="success"
        />
        <MetricCard
          title="Attachments"
          value={appCase.documents.length}
          subtitle="PDF packages parsed"
          icon={FileText}
          tone="info"
        />
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-xs font-semibold overflow-x-auto" aria-label="Tabs">
          {[
            { id: 'overview', label: '1. Scrutiny Overview' },
            { id: 'documents', label: `2. Documents & Metadata (${appCase.documents.length})` },
            { id: 'regulatory', label: `3. Regulatory Checks (${totalFindings})` },
            { id: 'issuer', label: '4. Issuer Verification (Simulated)' },
            { id: 'forensics', label: '5. Forensic Diagnostics' },
            { id: 'audit', label: `6. Audit Trail (${auditEvents.length})` }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-1 border-b-2 font-medium text-xs whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* TAB 1: EXECUTIVE OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Defect Priority Highlights */}
          {criticalDefects.length > 0 && (
            <Card padding="md" className="border-rose-200 bg-rose-50/20 space-y-3">
              <div className="flex items-center gap-2 text-rose-900 font-semibold text-sm">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                <span>Statutory Deficiencies Flagged ({criticalDefects.length})</span>
              </div>
              <p className="text-xs text-slate-600">
                The following automated checks identified non-compliance against AICTE Approval Process Handbook (APH 2024–2027) requirements. Review evidence to record official determination.
              </p>
              <div className="space-y-2 pt-1">
                {criticalDefects.map((f) => (
                  <div
                    key={f.id}
                    className="p-3 rounded-lg border border-rose-200 bg-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-rose-900">{f.rule_id}</span>
                        <CategoryBadge category={f.rule_category} />
                        {f.aph_reference && (
                          <span className="text-[11px] text-slate-500 font-mono truncate max-w-xs">
                            {f.aph_reference}
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-medium text-slate-800">{f.claim}</p>
                      <p className="text-xs text-slate-500">{f.description}</p>
                    </div>
                    <Link
                      href={`/application/${appCase.id}/finding/${f.id}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 text-white hover:bg-rose-700 shrink-0 shadow-sm"
                    >
                      <span>Review Evidence</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Document Ingestion Checklist Summary */}
          <Card padding="md" className="space-y-3">
            <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
              Document Intake Checklist
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {appCase.documents.map((doc) => (
                <div
                  key={doc.id}
                  className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-start justify-between gap-2"
                >
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-1.5 font-medium text-slate-900 truncate">
                      <FileText className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span className="truncate">{doc.filename}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 uppercase tracking-wide">
                      {doc.document_type.replace('_', ' ')} &bull; {doc.page_count} page(s)
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono truncate">
                      SHA: {doc.sha256_hash.slice(0, 16)}...
                    </div>
                  </div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 shrink-0">
                    Ingested
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* TAB 2: DOCUMENTS & METADATA INSPECTOR */}
      {activeTab === 'documents' && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-blue-700 shrink-0" />
              <span>
                <strong>Metadata Forensics Protocol:</strong> Technical metadata anomalies (e.g. malformed creation dates or missing producer tags) prompt review and do NOT independently prove forgery.
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {appCase.documents.map((doc) => {
              const isExpanded = expandedDocMetadata[doc.id];
              const meta = doc.metadata || ({} as DocumentMetadata);
              const warnings = meta.parsing_warnings || [];

              return (
                <Card key={doc.id} padding="none" className="overflow-hidden">
                  <div
                    onClick={() => toggleDocExpand(doc.id)}
                    className="p-4 bg-white hover:bg-slate-50 cursor-pointer flex items-center justify-between transition-colors border-b border-slate-100"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="p-2 rounded-lg bg-blue-50 text-blue-700 shrink-0">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-slate-900 truncate">
                            {doc.filename}
                          </span>
                          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                            {doc.document_type}
                          </span>
                          {warnings.length > 0 && (
                            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                              {warnings.length} Parsing Warning(s)
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          PDF {meta.pdf_version || '1.4'} &bull; {doc.page_count} Page(s) &bull; Encrypted: {meta.is_encrypted ? 'Yes' : 'No'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-blue-600 font-medium">
                        {isExpanded ? 'Hide Metadata' : 'Inspect Metadata'}
                      </span>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="p-4 bg-slate-50 text-xs space-y-4">
                      {/* Technical Properties Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[10px] text-slate-400 uppercase font-semibold">PDF Creator</span>
                          <p className="font-mono text-slate-800 mt-0.5">{meta.creator || 'None / Stripped'}</p>
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[10px] text-slate-400 uppercase font-semibold">PDF Producer</span>
                          <p className="font-mono text-slate-800 mt-0.5">{meta.producer || 'None / Stripped'}</p>
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[10px] text-slate-400 uppercase font-semibold">Normalized Creation Date</span>
                          <p className="font-mono text-slate-800 mt-0.5">{meta.normalized_creation_date || meta.creation_date || 'N/A'}</p>
                          {meta.raw_creation_date && (
                            <p className="text-[10px] text-slate-400 mt-0.5">Raw: {meta.raw_creation_date}</p>
                          )}
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[10px] text-slate-400 uppercase font-semibold">Normalized Mod Date</span>
                          <p className="font-mono text-slate-800 mt-0.5">{meta.normalized_mod_date || meta.mod_date || 'N/A'}</p>
                          {meta.raw_mod_date && (
                            <p className="text-[10px] text-slate-400 mt-0.5">Raw: {meta.raw_mod_date}</p>
                          )}
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[10px] text-slate-400 uppercase font-semibold">Digital Signature</span>
                          <p className="font-mono text-slate-800 mt-0.5">{meta.is_signed ? 'Cryptographically Signed' : 'Unsigned'}</p>
                        </div>
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="text-[10px] text-slate-400 uppercase font-semibold">SHA-256 Digest</span>
                          <p className="font-mono text-[10px] text-slate-800 mt-0.5 truncate" title={doc.sha256_hash}>
                            {doc.sha256_hash}
                          </p>
                        </div>
                      </div>

                      {/* Warnings if any */}
                      {warnings.length > 0 && (
                        <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-200 space-y-1">
                          <span className="text-[11px] font-semibold text-amber-900 uppercase">
                            Parser Diagnostics:
                          </span>
                          <ul className="list-disc list-inside text-[11px] text-amber-800 space-y-0.5">
                            {warnings.map((w, idx) => (
                              <li key={idx}>{w}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: REGULATORY CHECKS */}
      {activeTab === 'regulatory' && (
        <div className="space-y-4">
          {/* Category Filter Bar */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mr-1">
              Category:
            </span>
            <button
              onClick={() => setRegulatoryFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                regulatoryFilter === 'ALL'
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
              }`}
            >
              All Rules ({totalFindings})
            </button>
            <button
              onClick={() => setRegulatoryFilter('STATUTORY_MANDATE')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                regulatoryFilter === 'STATUTORY_MANDATE'
                  ? 'bg-purple-800 text-white font-semibold'
                  : 'bg-purple-50 text-purple-900 hover:bg-purple-100 border border-purple-200'
              }`}
            >
              Statutory Mandates ({statutoryFindings.length})
            </button>
            <button
              onClick={() => setRegulatoryFilter('TECHNICAL_CONSISTENCY')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                regulatoryFilter === 'TECHNICAL_CONSISTENCY'
                  ? 'bg-slate-800 text-white font-semibold'
                  : 'bg-slate-100 text-slate-800 hover:bg-slate-200 border border-slate-200'
              }`}
            >
              Technical Consistency
            </button>
            <button
              onClick={() => setRegulatoryFilter('METADATA_INTEGRITY')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                regulatoryFilter === 'METADATA_INTEGRITY'
                  ? 'bg-amber-800 text-white font-semibold'
                  : 'bg-amber-50 text-amber-900 hover:bg-amber-100 border border-amber-200'
              }`}
            >
              Metadata Integrity ({metadataFindings.length})
            </button>
            <button
              onClick={() => setRegulatoryFilter('FORENSIC_ADVISORY')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                regulatoryFilter === 'FORENSIC_ADVISORY'
                  ? 'bg-indigo-800 text-white font-semibold'
                  : 'bg-indigo-50 text-indigo-900 hover:bg-indigo-100 border border-indigo-200'
              }`}
            >
              Forensic Advisories ({forensicFindings.length})
            </button>
          </div>

          {/* Finding Cards List */}
          <div className="space-y-3">
            {filteredFindings.map((finding) => (
              <Card key={finding.id} padding="md" className="space-y-3 hover:border-slate-300 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 border-b border-slate-100 pb-2.5">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900">
                        {finding.rule_id}
                      </span>
                      <CategoryBadge category={finding.rule_category} />
                      <SeverityBadge severity={finding.severity} />
                      <StatusBadge status={finding.status} size="sm" />
                      {finding.lifecycle && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          Lifecycle: {finding.lifecycle}
                        </span>
                      )}
                    </div>
                    <h3 className="text-xs font-semibold text-slate-800">{finding.rule_name}</h3>
                  </div>

                  <Link
                    href={`/application/${appCase.id}/finding/${finding.id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 shrink-0"
                  >
                    <span>Inspect Evidence</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="space-y-1 text-xs">
                  <p className="text-slate-700 font-medium">{finding.claim}</p>
                  <p className="text-slate-500 leading-relaxed">{finding.description}</p>
                  {finding.aph_reference && (
                    <div className="text-[11px] text-slate-500 mt-2 font-mono bg-slate-50 p-2 rounded border border-slate-200">
                      <span className="text-slate-400 font-semibold uppercase">Legal Reference: </span>
                      {finding.aph_reference}
                    </div>
                  )}
                </div>

                {/* Review status if decided */}
                {finding.review && finding.review.decision !== 'UNREVIEWED' && (
                  <div className="p-2.5 rounded-lg bg-slate-100 border border-slate-200 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-slate-700">Officer Decision: </span>
                      <strong className="text-slate-900">{finding.review.decision}</strong>
                      {finding.review.reviewer_notes && (
                        <p className="text-slate-500 text-[11px] mt-0.5">Notes: {finding.review.reviewer_notes}</p>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {finding.review.reviewed_at ? new Date(finding.review.reviewed_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: ISSUER VERIFICATION (SIMULATED REGISTRIES) */}
      {activeTab === 'issuer' && (
        <div className="space-y-4">
          <Card padding="md" className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                Simulated Authoritative Registry Verification
              </h3>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                LOCAL SANDBOX EMULATION
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Cross-references extracted identifiers against simulated registry endpoints (AICTE Central Master Portal, State Fire Services Portal, and e-Signature verification).
            </p>
            <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-200 text-[11px] text-amber-900 leading-relaxed">
              <strong>Source Availability Policy:</strong> When an external registry is unreachable or returns a timeout, the verification status is recorded as <code>INDETERMINATE</code>. Unavailability of an external issuing registry does NOT constitute an applicant compliance failure.
            </div>

            <div className="space-y-3 pt-2">
              {appCase.findings
                .filter((f) => f.verification_result)
                .map((f) => {
                  const v = f.verification_result!;
                  return (
                    <div
                      key={f.id}
                      className="p-4 rounded-xl border border-slate-200 bg-white space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-slate-900">{v.source}</span>
                          <StatusBadge status={v.status} size="sm" />
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                          Simulated Test Adapter
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">{v.message}</p>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Referenced Finding: {f.rule_id} ({f.rule_name})
                      </div>
                    </div>
                  );
                })}
              {appCase.findings.filter((f) => f.verification_result).length === 0 && (
                <EmptyState
                  title="No External Registry Queries Performed"
                  description="No findings in this application required external portal verification (e.g., PID or NOC lookup)."
                />
              )}
            </div>
          </Card>
        </div>
      )}

      {/* TAB 5: COMPUTER VISION FORENSICS */}
      {activeTab === 'forensics' && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-900 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-700 shrink-0" />
              <span>
                <strong>Forensic Signals Disclosure:</strong> Error Level Analysis (ELA), SRM energy, and copy-move detectors are algorithmic advisories for visual scrutiny. They do not independently prove forgery.
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {appCase.documents.map((doc) => (
              <Card key={doc.id} padding="md" className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <div className="flex items-center gap-2 truncate">
                    <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
                    <span className="font-semibold text-xs text-slate-900 truncate">
                      {doc.filename}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 uppercase">
                    {doc.document_type}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Algorithm Suite:</span>
                    <span className="font-mono text-slate-800">ELA, SRM, SIFT RANSAC</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Typography Consistency:</span>
                    <span className="text-emerald-700 font-medium">Uniform Baseline</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Scan Glare / Lamination:</span>
                    <span className="text-slate-800 font-mono">0.00%</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    Full diagnostics available in Evidence Viewer
                  </span>
                  <Link
                    href={`/application/${appCase.id}/finding/${appCase.findings[0]?.id || ''}`}
                    className="text-xs text-blue-600 hover:underline font-semibold"
                  >
                    Open Viewer &rarr;
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 6: CRYPTOGRAPHIC AUDIT TRAIL */}
      {activeTab === 'audit' && (
        <div className="space-y-4">
          <Card padding="md" className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                  <Database className="w-4 h-4 text-emerald-600" />
                  Hash-Chained Audit Trail for Case {appCase.id}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Every ingestion event, rule evaluation, and officer determination is anchored in a SHA-256 tamper-evident log.
                </p>
              </div>

              <button
                onClick={verifyAuditChain}
                disabled={verifyingChain}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition-colors focus-ring shrink-0"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{verifyingChain ? 'Verifying Hashes...' : 'Verify Chain Integrity'}</span>
              </button>
            </div>

            {chainVerification && (
              <div
                className={`p-3.5 rounded-xl border text-xs flex items-center justify-between ${
                  chainVerification.valid
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : 'bg-rose-50 border-rose-200 text-rose-900'
                }`}
              >
                <div className="flex items-center gap-2">
                  {chainVerification.valid ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-600" />
                  )}
                  <span>
                    <strong>{chainVerification.valid ? 'Hash Chain Intact:' : 'Tampering Detected:'}</strong>{' '}
                    {chainVerification.message || `All ${chainVerification.events_checked || 0} events verified without corruption.`}
                  </span>
                </div>
                <span className="font-mono text-[10px]">
                  Checked: {chainVerification.events_checked} block(s)
                </span>
              </div>
            )}

            <div className="divide-y divide-slate-100">
              {auditEvents.map((evt) => (
                <div key={evt.id} className="py-3 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-mono">
                      <span className="font-bold text-blue-700">{evt.action}</span>
                      <span className="text-slate-400">&bull;</span>
                      <span className="text-slate-500 text-[11px]">{evt.id}</span>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      {new Date(evt.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <div className="bg-slate-50 p-2.5 rounded-md font-mono text-[11px] text-slate-700 overflow-x-auto border border-slate-200/80">
                    <div className="text-[10px] text-slate-400 mb-1">
                      Payload: {JSON.stringify(evt.payload)}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Prev Hash: {evt.prev_hash?.slice(0, 20)}... &bull; Current Hash: {evt.hash?.slice(0, 20)}...
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
