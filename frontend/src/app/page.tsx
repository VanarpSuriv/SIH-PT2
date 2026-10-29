'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  UploadCloud,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  Inbox,
  Sparkles,
  Info,
  ChevronRight,
  Database,
  Layers,
  FileCheck2,
  History,
  BookOpen
} from 'lucide-react';
import { Card, MetricCard } from '@/components/ui/Card';
import { StatusBadge, SeverityBadge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';

interface SyntheticCase {
  case_id: string;
  institution_name: string;
  application_id: string;
  permanent_id: string;
  expected_defects: string[];
  clean: boolean;
  generated_files: string[];
}

interface ApplicationSummary {
  id: string;
  institution_name: string;
  application_date: string;
  status: string;
  created_at: string;
  documents: { id: string; filename: string; document_type: string }[];
  findings: {
    id: string;
    severity: string;
    status: string;
    rule_category?: string;
    lifecycle?: string;
    review?: { decision?: string; officer_id?: string; timestamp?: string; notes?: string };
  }[];
}

interface AuditEventItem {
  id: string;
  action: string;
  application_id: string;
  timestamp: string;
  payload: Record<string, any>;
}

const API_BASE = '/api';

/**
 * Overview Dashboard answering the core operational questions:
 * 1. What needs attention now?
 * 2. Which applications are blocked or incomplete?
 * 3. Which verifications are pending?
 * 4. What actions should the officer take next?
 */
export default function OverviewPage() {
  const router = useRouter();

  const [syntheticCases, setSyntheticCases] = useState<SyntheticCase[]>([]);
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [recentAudit, setRecentAudit] = useState<AuditEventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Upload Form State
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [institutionName, setInstitutionName] = useState('National Institute of Advanced Technology');
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    loadOverviewData();
  }, []);

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Concurrent fetch of cases, applications, and audit events
      const [casesRes, appsRes, auditRes] = await Promise.allSettled([
        fetch(`${API_BASE}/cases`),
        fetch(`${API_BASE}/applications`),
        fetch(`${API_BASE}/audit`)
      ]);

      if (casesRes.status === 'fulfilled' && casesRes.value.ok) {
        const data = await casesRes.value.json();
        setSyntheticCases(data);
      }

      if (appsRes.status === 'fulfilled' && appsRes.value.ok) {
        const data = await appsRes.value.json();
        setApplications(data);
      }

      if (auditRes.status === 'fulfilled' && auditRes.value.ok) {
        const data = await auditRes.value.json();
        setRecentAudit(data.slice(-5).reverse());
      }
    } catch (err: any) {
      setError('Unable to connect to the verification backend service.');
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchCase = async (caseId: string) => {
    try {
      setLoadingAction(`launch_${caseId}`);
      setUploadError(null);
      const res = await fetch(`${API_BASE}/cases/${caseId}/load`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to load application case package');
      const app = await res.json();
      router.push(`/application/${app.id}`);
    } catch (err: any) {
      setUploadError(err.message || 'Error loading pre-indexed case');
      setLoadingAction(null);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (uploadedFiles.length === 0) {
      setUploadError('Please select at least one PDF document to verify.');
      return;
    }

    try {
      setLoadingAction('uploading');
      setUploadError(null);
      const formData = new FormData();
      formData.append('institution_name', institutionName);
      uploadedFiles.forEach((file) => {
        formData.append('files', file);
      });

      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Document upload and verification pipeline failed');
      }

      const app = await res.json();
      router.push(`/application/${app.id}`);
    } catch (err: any) {
      setUploadError(err.message || 'Upload error');
      setLoadingAction(null);
    }
  };

  // Operational metrics calculated strictly from live application state
  const totalApps = applications.length;
  const actionRequiredApps = applications.filter((a) => a.status === 'ACTION_REQUIRED').length;
  const compliantApps = applications.filter((a) => a.status === 'VERIFIED_COMPLIANT' || a.status === 'PASS').length;
  const flaggedFindingsCount = applications.reduce((acc, a) => {
    return acc + (a.findings ? a.findings.filter((f) => f.status === 'FAIL' && f.lifecycle !== 'RESOLVED').length : 0);
  }, 0);
  const reviewerConfirmedCount = applications.reduce((acc, a) => {
    return acc + (a.findings ? a.findings.filter((f) => f.review?.decision === 'CONFIRMED_DEFECT').length : 0);
  }, 0);

  // Derive quick attention benchmark cases
  const highPriorityCases = syntheticCases.filter(
    (c) => !c.clean && (c.expected_defects.some((d) => d.includes('FIRE') || d.includes('EXPIRED') || d.includes('AREA') || d.includes('MISSING')))
  ).slice(0, 4);

  return (
    <div className="space-y-8">
      {/* Page Title & Operational Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            AICTE Scrutiny & Regulatory Intelligence Desk
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Official decision-support platform for AICTE Extension of Approval (EoA) application verification (APH 2024–2027).
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadOverviewData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors focus-ring"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Live Queue</span>
          </button>
          <Link
            href="/applications"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm transition-colors focus-ring"
          >
            <Inbox className="w-3.5 h-3.5" />
            <span>Open Backlog Queue</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadOverviewData}
            className="text-xs font-semibold underline text-amber-800 hover:text-amber-950"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Operational KPI Metric Strip (Derived strictly from live applications) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Ingested Applications"
          value={totalApps}
          subtitle={totalApps > 0 ? `${actionRequiredApps} require scrutiny review` : '0 live cases in session memory'}
          icon={Inbox}
          tone={actionRequiredApps > 0 ? 'warning' : 'default'}
        />
        <MetricCard
          title="Flagged Deficiencies"
          value={flaggedFindingsCount}
          subtitle="Automated checks awaiting review"
          icon={ShieldAlert}
          tone={flaggedFindingsCount > 0 ? 'danger' : 'default'}
        />
        <MetricCard
          title="Reviewer-Confirmed Findings"
          value={reviewerConfirmedCount}
          subtitle="Affirmed by authorized officers"
          icon={CheckCircle2}
          tone={reviewerConfirmedCount > 0 ? 'info' : 'default'}
        />
        <MetricCard
          title="Audit Trail Integrity"
          value={recentAudit.length > 0 ? `${recentAudit.length} Events` : 'Intact'}
          subtitle="SHA-256 hash-chain verified"
          icon={Database}
          tone="success"
        />
      </div>

      {/* Two-Column Core Layout: Intake Desk + Priority Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Direct Document Ingestion Desk */}
        <div className="lg:col-span-5 space-y-6">
          <Card padding="md" className="space-y-5">
            <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-blue-600" />
                <h2 className="text-sm font-semibold text-slate-900">Direct Document Ingestion Desk</h2>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                15 MB Max / PDF
              </span>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              Upload multi-document institutional packages for automated PyMuPDF parsing, computer vision forensic screening, and APH compliance checks.
            </p>

            {uploadError && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleFileUpload} className="space-y-4">
              <div>
                <label htmlFor="inst_name" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Institutional Name (Applicant)
                </label>
                <input
                  id="inst_name"
                  name="inst_name"
                  type="text"
                  aria-label="Institutional Name (Applicant)"
                  value={institutionName}
                  onChange={(e) => setInstitutionName(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus-ring"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Document Package Upload
                </label>
                <div className="border-2 border-dashed border-slate-300 rounded-xl p-5 text-center hover:border-blue-400 bg-slate-50/50 transition-colors">
                  <UploadCloud className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                  <div className="text-xs text-slate-600 font-medium">
                    Drag and drop PDF files here, or{' '}
                    <label htmlFor="file_upload_input" className="text-blue-600 hover:underline cursor-pointer">
                      browse files
                    </label>
                    <input
                      id="file_upload_input"
                      name="file_upload_input"
                      type="file"
                      multiple
                      accept="application/pdf"
                      aria-label="Upload PDF document package"
                      onChange={(e) => setUploadedFiles(Array.from(e.target.files || []))}
                      className="sr-only"
                    />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Accepts Application Form, Fire Safety NOC, Land Title Deed, Faculty List, Approval Letter
                  </p>
                </div>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                    Selected Files ({uploadedFiles.length})
                  </p>
                  <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white max-h-36 overflow-y-auto">
                    {uploadedFiles.map((file, idx) => (
                      <li key={idx} className="p-2 text-xs flex items-center justify-between text-slate-700">
                        <div className="flex items-center gap-2 truncate">
                          <FileText className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                          <span className="truncate">{file.name}</span>
                        </div>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {(file.size / 1024).toFixed(0)} KB
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <button
                type="submit"
                disabled={loadingAction === 'uploading'}
                className="w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-sm transition-colors flex items-center justify-center gap-2 focus-ring"
              >
                {loadingAction === 'uploading' ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Executing Ingestion & Forensics...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>Ingest Package & Run Scrutiny</span>
                  </>
                )}
              </button>
            </form>
          </Card>

          {/* Quick Regulatory Reference Card */}
          <Card padding="md" className="space-y-3 bg-slate-50/60 border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                <BookOpen className="w-4 h-4 text-indigo-600" />
                AICTE APH 2024–2027 Regulatory Baseline
              </span>
              <Link href="/rules" className="text-xs text-blue-600 hover:underline">
                View All Rules &rarr;
              </Link>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Statutory verification criteria substantiated against Chapter VI §6.17(i) (Fire Safety Certificate presence & validity) and Annexure 3 §3.1 (Acreage & Built-up Norms).
            </p>
          </Card>
        </div>

        {/* Right Column: Live Ingested Queue & Separated Synthetic Benchmark Suite */}
        <div className="lg:col-span-7 space-y-6">
          {/* Card 1: Live Ingested Applications Queue */}
          <Card padding="md" className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Live Scrutiny Priority Backlog</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Applications currently processed in memory requiring scrutiny review or officer determination.
                </p>
              </div>
              <Link
                href="/applications"
                className="text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
              >
                <span>Full Queue ({applications.length})</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : applications.length > 0 ? (
              <div className="space-y-2.5">
                {applications.map((app) => (
                  <div
                    key={app.id}
                    className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm transition-all flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-slate-900">
                          {app.id}
                        </span>
                        <StatusBadge status={app.status} size="sm" />
                      </div>
                      <h3 className="text-xs font-medium text-slate-800 truncate">
                        {app.institution_name}
                      </h3>
                      <p className="text-[11px] text-slate-400">
                        {app.documents?.length || 0} document(s) &bull; {app.findings?.length || 0} compliance check(s) evaluated
                      </p>
                    </div>

                    <Link
                      href={`/application/${app.id}`}
                      className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm transition-colors shrink-0 focus-ring"
                    >
                      <span>Open Workspace</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Live Applications Ingested Yet"
                description="Upload an institutional package using the Ingestion Desk on the left, or launch an evaluation case from the benchmark suite below."
              />
            )}
          </Card>

          {/* Card 2: Dedicated Synthetic Benchmark Evaluation Suite */}
          <Card padding="md" className="space-y-4 border-amber-200/80 bg-gradient-to-b from-amber-50/20 to-white">
            <div className="flex items-center justify-between border-b border-amber-100 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold text-slate-900">Synthetic Benchmark Evaluation Suite</h2>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                    DEMO & EVALUATION ONLY
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Pre-indexed synthetic institutional filings with ground-truth compliance defects for SIH26261 evaluation.
                </p>
              </div>
              <Link
                href="/applications"
                className="text-xs text-amber-800 hover:text-amber-950 font-medium inline-flex items-center gap-1"
              >
                <span>All 25 Cases</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2.5">
              {highPriorityCases.map((c) => (
                <div
                  key={c.case_id}
                  className="p-3 rounded-lg border border-slate-200 bg-white hover:border-amber-300 transition-colors flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-slate-800">
                        {c.case_id.toUpperCase()}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                        {c.expected_defects.join(', ')}
                      </span>
                    </div>
                    <div className="text-xs text-slate-700 truncate">
                      {c.institution_name}
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      PID: {c.permanent_id} &bull; {c.generated_files.length} documents
                    </div>
                  </div>

                  <button
                    onClick={() => handleLaunchCase(c.case_id)}
                    disabled={loadingAction === `launch_${c.case_id}`}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 shadow-sm transition-colors shrink-0 focus-ring"
                  >
                    {loadingAction === `launch_${c.case_id}` ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        <span>Loading...</span>
                      </>
                    ) : (
                      <>
                        <span>Load & Evaluate</span>
                        <ArrowRight className="w-3 h-3" />
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          </Card>

          {/* Recent Cryptographic Audit Activity */}
          <Card padding="md" className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-slate-500" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                  Recent Hash-Chained Audit Events
                </h3>
              </div>
              <Link href="/audit" className="text-xs text-blue-600 hover:underline">
                Verify Integrity Chain &rarr;
              </Link>
            </div>

            {recentAudit.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {recentAudit.map((evt) => (
                  <div key={evt.id} className="py-2.5 text-xs flex items-center justify-between text-slate-600">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2 font-medium text-slate-800">
                        <span className="font-mono text-[11px] text-blue-600">{evt.action}</span>
                        <span className="text-slate-400">&bull;</span>
                        <span className="text-slate-600 font-mono text-[11px]">{evt.application_id}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {evt.timestamp ? new Date(evt.timestamp).toLocaleString() : 'Recent timestamp'}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                      SHA-256 Intact
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 text-center py-4">
                No recent audit events in current session.
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
