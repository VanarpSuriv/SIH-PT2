'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  Clock,
  RefreshCw,
  Check,
  X,
  ExternalLink,
  Layers,
  Database,
  HelpCircle,
  Info,
  Calendar,
  AlertOctagon,
  Sparkles,
  Search,
  Eye,
  Sliders,
  Maximize2,
  BookOpen
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { StatusBadge, SeverityBadge, CategoryBadge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { ConfirmModal } from '@/components/ui/ConfirmModal';

interface ExtractedField {
  name: string;
  value: any;
  raw_text: string;
  document_type: string;
  document_id?: string;
  page_number: number;
  bbox: number[];
  confidence: number;
}

interface VerificationResult {
  issuer: string;
  record_id: string;
  status: string;
  source: string;
  message: string;
  verified_data?: any;
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

interface ForensicTokenDetail {
  text: string;
  bbox: number[];
  size_ratio: number;
  stroke_ratio: number;
  style_score: number;
  style_outlier: boolean;
}

interface ForensicPageResult {
  page_number: number;
  ela_mean_residual: number;
  ela_max_residual: number;
  srm_energy: number;
  copy_move_detected: boolean;
  copy_move_matches: number;
  copy_move_score: number;
  blur_score: number;
  glare_ratio: number;
  qr_detected: boolean;
  qr_payload?: string;
  style_outliers_count: number;
  token_style_outliers: ForensicTokenDetail[];
  anomalies: string[];
  heatmap_preview_base64?: string;
}

interface DocumentForensicsResult {
  document_id: string;
  filename: string;
  page_count: number;
  page_results: ForensicPageResult[];
  summary_advisory: string;
  overall_score: number;
  findings_generated: string[];
}

interface Finding {
  id: string;
  application_id: string;
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
  fields_involved: ExtractedField[];
  metadata_context?: MetadataEvidenceContext;
  verification_result?: VerificationResult;
  review?: HumanReviewDecision;
  user_status: string;
  created_at: string;
}

const API_BASE = 'http://localhost:8000';
const DEMO_OFFICER_TOKEN = process.env.NEXT_PUBLIC_OFFICER_TOKEN || 'demo-sih-2026-officer-token';

/**
 * Finding Detail & Evidence Viewer: Dual-pane analyst workbench providing
 * high-resolution PyMuPDF highlighted document views, ELA compression heatmaps,
 * metadata delta tables, and official human reviewer determination console.
 */
export default function FindingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appId = params?.id as string;
  const findingId = params?.findingId as string;

  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFieldIdx, setSelectedFieldIdx] = useState(0);

  // Evidence Display Mode: 'EVIDENCE' (Bounding box on document) vs 'ELA_HEATMAP'
  const [viewMode, setViewMode] = useState<'EVIDENCE' | 'ELA_HEATMAP'>('EVIDENCE');
  const [imageReloadKey, setImageReloadKey] = useState(0);

  // Computer Vision Forensics state
  const [forensicResult, setForensicResult] = useState<DocumentForensicsResult | null>(null);
  const [loadingForensics, setLoadingForensics] = useState(false);

  // Officer Review Console state
  const [actionLoading, setActionLoading] = useState(false);
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [auditMessage, setAuditMessage] = useState<string | null>(null);

  // Confirmation Modal State
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    decision: 'CONFIRMED_DEFECT' | 'DISMISSED_BENIGN' | 'REQUEST_CLARIFICATION' | null;
    title: string;
    description: string;
    tone: 'danger' | 'warning' | 'primary';
  }>({
    isOpen: false,
    decision: null,
    title: '',
    description: '',
    tone: 'primary'
  });

  useEffect(() => {
    if (findingId) {
      loadFindingData();
    }
  }, [findingId]);

  const loadFindingData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/api/findings/${findingId}`);
      if (!res.ok) throw new Error('Failed to retrieve finding details');
      const data: Finding = await res.json();
      setFinding(data);

      if (data.review?.reviewer_notes) {
        setReviewerNotes(data.review.reviewer_notes);
      }

      // If there are fields involved with a document_id, load document forensics
      const targetDocId = data.fields_involved?.[0]?.document_id;
      if (targetDocId) {
        loadDocumentForensics(targetDocId);
      }
    } catch (err: any) {
      setError(err.message || 'Error loading finding');
    } finally {
      setLoading(false);
    }
  };

  const loadDocumentForensics = async (docId: string) => {
    try {
      setLoadingForensics(true);
      const res = await fetch(`${API_BASE}/api/documents/${docId}/forensics`);
      if (res.ok) {
        const forensicData = await res.json();
        setForensicResult(forensicData);
      }
    } catch {
      // Non-critical forensic fetch failure
    } finally {
      setLoadingForensics(false);
    }
  };

  const openDecisionModal = (decision: 'CONFIRMED_DEFECT' | 'DISMISSED_BENIGN' | 'REQUEST_CLARIFICATION') => {
    if (decision === 'CONFIRMED_DEFECT') {
      setModalState({
        isOpen: true,
        decision,
        title: 'Record Confirmed Defect Assessment',
        description:
          'This action records your officer assessment that the document exhibits an authentic deficiency under APH 2024–2027 norms. This determination is logged to the cryptographic audit trail and does not constitute an autonomous AICTE council rejection.',
        tone: 'danger'
      });
    } else if (decision === 'DISMISSED_BENIGN') {
      setModalState({
        isOpen: true,
        decision,
        title: 'Dismiss as Benign Variation',
        description:
          'This action records your officer assessment that the flagged variation is benign or permissible under official guidelines. Logged to the cryptographic audit trail.',
        tone: 'primary'
      });
    } else {
      setModalState({
        isOpen: true,
        decision,
        title: 'Request Institutional Clarification',
        description:
          'This action marks the finding as Pending Clarification and records a formal request for the applicant institution to furnish certified explanatory documents.',
        tone: 'warning'
      });
    }
  };

  const handleExecuteReview = async () => {
    if (!modalState.decision || !finding) return;

    try {
      setActionLoading(true);
      setAuditMessage(null);

      const res = await fetch(`${API_BASE}/api/findings/${finding.id}/review`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${DEMO_OFFICER_TOKEN}`,
          'X-Officer-Role': 'OFFICER'
        },
        body: JSON.stringify({
          decision: modalState.decision,
          reviewer_notes: reviewerNotes,
          reviewer_id: 'SCRUTINY-OFFICER-01'
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to submit review decision to server');
      }

      const outcome = await res.json();

      setAuditMessage(`Determination recorded successfully (Audit Event ID: ${outcome.audit_event_id})`);
      setImageReloadKey((k) => k + 1);
      setModalState((prev) => ({ ...prev, isOpen: false }));
      loadFindingData();
    } catch (err: any) {
      alert(`Error submitting determination: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-24 w-full rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Skeleton className="lg:col-span-7 h-96 rounded-xl" />
          <Skeleton className="lg:col-span-5 h-96 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !finding) {
    return (
      <div className="py-12">
        <EmptyState
          title="Finding Record Unavailable"
          description={error || `Could not find an evaluated finding matching ID '${findingId}'.`}
          actionLabel="Return to Application"
          onAction={() => router.push(`/application/${appId}`)}
        />
      </div>
    );
  }

  const activeField = finding.fields_involved?.[selectedFieldIdx];
  const pageResult = forensicResult?.page_results?.[0];

  return (
    <div className="space-y-6">
      {/* Return link */}
      <div className="flex items-center justify-between">
        <Link
          href={`/application/${appId}`}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Application Case {appId}</span>
        </Link>
        <span className="text-[11px] font-mono text-slate-400">
          Rule: {finding.rule_id} &bull; v{finding.rule_version}
        </span>
      </div>

      {/* Top Banner: Finding Identification & Category */}
      <Card padding="md" className="space-y-3 border-l-4 border-l-blue-600">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-slate-900">{finding.rule_id}</span>
              <CategoryBadge category={finding.rule_category} />
              <SeverityBadge severity={finding.severity} />
              <StatusBadge status={finding.status} size="sm" />
              {finding.lifecycle && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  Lifecycle: {finding.lifecycle}
                </span>
              )}
            </div>
            <h1 className="text-base font-bold text-slate-900">{finding.rule_name}</h1>
            <p className="text-xs text-slate-600 font-medium">{finding.claim}</p>
          </div>

          {finding.review && finding.review.decision !== 'UNREVIEWED' && (
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs shrink-0 max-w-xs space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-500">Recorded Decision</span>
              <div className="font-bold text-slate-900">{finding.review.decision}</div>
              {finding.review.reviewer_notes && (
                <p className="text-slate-600 text-[11px]">{finding.review.reviewer_notes}</p>
              )}
            </div>
          )}
        </div>

        {finding.aph_reference && (
          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700 flex items-start gap-2">
            <BookOpen className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
            <div className="leading-snug">
              <strong className="text-slate-900">Authoritative Statutory Reference:</strong>{' '}
              <span className="font-mono text-[11px]">{finding.aph_reference}</span>
            </div>
          </div>
        )}
      </Card>

      {auditMessage && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{auditMessage}</span>
        </div>
      )}

      {/* DUAL-PANE WORKBENCH */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANE: Document Region & Forensic Image Viewer (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card padding="none" className="overflow-hidden border border-slate-200 bg-white">
            {/* Viewer Header / Toolbar */}
            <div className="p-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-semibold text-slate-700">Display Layer:</span>
                <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-white">
                  <button
                    onClick={() => setViewMode('EVIDENCE')}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      viewMode === 'EVIDENCE'
                        ? 'bg-blue-600 text-white font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Document Evidence
                  </button>
                  <button
                    onClick={() => setViewMode('ELA_HEATMAP')}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      viewMode === 'ELA_HEATMAP'
                        ? 'bg-indigo-600 text-white font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    ELA Heatmap
                  </button>
                </div>
              </div>

              {finding.fields_involved?.length > 1 && (
                <div className="flex items-center gap-1.5 text-xs">
                  <label htmlFor="field-select" className="text-slate-500">Field:</label>
                  <select
                    id="field-select"
                    name="field_select"
                    value={selectedFieldIdx}
                    onChange={(e) => setSelectedFieldIdx(Number(e.target.value))}
                    className="text-xs px-2 py-1 rounded border border-slate-300 bg-white text-slate-800"
                  >
                    {finding.fields_involved.map((fld, idx) => (
                      <option key={idx} value={idx}>
                        {fld.name} (p.{fld.page_number})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Evidence Image Canvas */}
            <div className="p-4 bg-slate-100/70 flex items-center justify-center min-h-[460px] overflow-auto">
              {viewMode === 'EVIDENCE' ? (
                <img
                  key={`evidence_${imageReloadKey}_${selectedFieldIdx}`}
                  src={`${API_BASE}/api/findings/${finding.id}/evidence_image?field_idx=${selectedFieldIdx}&t=${imageReloadKey}`}
                  alt={`Highlighted evidence for ${finding.rule_id}`}
                  className="max-w-full h-auto rounded-lg shadow-sm border border-slate-300 bg-white"
                />
              ) : (
                <div className="w-full space-y-3">
                  {pageResult?.heatmap_preview_base64 ? (
                    <img
                      src={`data:image/png;base64,${pageResult.heatmap_preview_base64}`}
                      alt="Error Level Analysis (ELA) Heatmap"
                      className="max-w-full h-auto rounded-lg shadow-sm border border-slate-300 mx-auto bg-black"
                    />
                  ) : (
                    <div className="p-8 text-center bg-white rounded-lg border border-slate-200 text-xs text-slate-500 space-y-2">
                      <Sliders className="w-6 h-6 text-indigo-500 mx-auto" />
                      <p className="font-semibold text-slate-800">ELA Heatmap Preview Initializing</p>
                      <p className="text-slate-500 max-w-sm mx-auto">
                        Computer vision error level analysis processes compression noise residuals at 95% JPEG quality.
                      </p>
                    </div>
                  )}
                  <p className="text-[11px] text-center text-slate-500 italic">
                    Bright intensity pixels indicate areas with differing compression histories (potential splice/copy-move).
                  </p>
                </div>
              )}
            </div>

            {/* Mandatory Legal Forensic Disclaimer */}
            <div className="p-3 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 flex items-start gap-2">
              <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <span>
                <strong>Persistent Disclosure:</strong> Automated forensic and metadata indicators are preliminary decision-support observations. They do NOT independently establish document forgery, fraud, or misconduct. Consequential determinations remain with authorized officials.
              </span>
            </div>
          </Card>
        </div>

        {/* RIGHT PANE: Findings Panel & Review Action Console (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          {/* Detailed Observations Card */}
          <Card padding="md" className="space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-900 border-b border-slate-100 pb-2">
              Finding Diagnostics & Extracted Evidence
            </h2>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center text-slate-600">
                <span>Rule Category:</span>
                <CategoryBadge category={finding.rule_category} />
              </div>
              <div className="flex justify-between items-center text-slate-600">
                <span>Evaluated Severity:</span>
                <SeverityBadge severity={finding.severity} />
              </div>
              <div className="flex justify-between items-center text-slate-600">
                <span>Verification State:</span>
                <StatusBadge status={finding.status} size="sm" />
              </div>
            </div>

            <div className="space-y-1.5 text-xs pt-1">
              <span className="font-semibold text-slate-800">Technical Rationale:</span>
              <p className="text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                {finding.description}
              </p>
            </div>

            {/* If metadata context is present: show original vs normalized delta table */}
            {finding.metadata_context && (
              <div className="space-y-2 pt-2 border-t border-slate-100 text-xs">
                <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <Search className="w-3.5 h-3.5 text-amber-600" />
                  PDF Metadata Forensic Context
                </span>
                <div className="bg-amber-50/50 p-2.5 rounded-lg border border-amber-200 space-y-2">
                  <p className="text-[11px] text-amber-900 font-medium">
                    Reason for Review: {finding.metadata_context.reason_for_review}
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="bg-white p-2 rounded border border-amber-200">
                      <span className="text-[10px] font-semibold text-slate-400 uppercase">Original Field</span>
                      <pre className="font-mono text-slate-800 mt-0.5 truncate">
                        {JSON.stringify(finding.metadata_context.original_values, null, 1)}
                      </pre>
                    </div>
                    <div className="bg-white p-2 rounded border border-amber-200">
                      <span className="text-[10px] font-semibold text-slate-400 uppercase">Normalized Field</span>
                      <pre className="font-mono text-slate-800 mt-0.5 truncate">
                        {JSON.stringify(finding.metadata_context.normalized_values, null, 1)}
                      </pre>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* If external verification result exists */}
            {finding.verification_result && (
              <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
                <span className="font-semibold text-slate-800">External Registry Check:</span>
                <div className="p-2.5 rounded-lg bg-blue-50/60 border border-blue-200 space-y-1 text-[11px]">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-blue-900">{finding.verification_result.source}</span>
                    <StatusBadge status={finding.verification_result.status} size="sm" />
                  </div>
                  <p className="text-slate-700">{finding.verification_result.message}</p>
                </div>
              </div>
            )}
          </Card>

          {/* HUMAN REVIEW DECISION CONSOLE */}
          <Card padding="md" className="space-y-4 border-2 border-blue-100 bg-white">
            <div className="border-b border-slate-100 pb-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                Authorized Human Reviewer Determination
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Enforces server-verified officer credentials. All determinations are written to the SHA-256 audit log.
              </p>
            </div>

            <div className="space-y-3">
              <div>
                <label htmlFor="rev_notes" className="block text-xs font-semibold text-slate-700 mb-1">
                  Scrutiny Officer Justification & Notes:
                </label>
                <textarea
                  id="rev_notes"
                  rows={3}
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  placeholder="State official basis for determination (e.g., 'Inspected original Fire NOC stamp, verified valid under APH 2024–27 Chapter VI §6.17(i)')..."
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus-ring"
                />
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => openDecisionModal('CONFIRMED_DEFECT')}
                  className="px-3 py-2 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors flex items-center justify-center gap-1 focus-ring"
                >
                  <XCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>Record Confirmed Defect</span>
                </button>

                <button
                  type="button"
                  onClick={() => openDecisionModal('DISMISSED_BENIGN')}
                  className="px-3 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-900 text-white shadow-sm transition-colors flex items-center justify-center gap-1 focus-ring"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  <span>Dismiss as Benign</span>
                </button>

                <button
                  type="button"
                  onClick={() => openDecisionModal('REQUEST_CLARIFICATION')}
                  className="px-3 py-2 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white shadow-sm transition-colors flex items-center justify-center gap-1 focus-ring"
                >
                  <Clock className="w-3.5 h-3.5 shrink-0" />
                  <span>Request Clarification</span>
                </button>
              </div>

              <p className="text-[10px] text-slate-400 text-center leading-tight pt-1">
                Reviewer determinations record officer assessments for committee review. They do not constitute an autonomous AICTE approval or rejection.
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={modalState.isOpen}
        onClose={() => setModalState((prev) => ({ ...prev, isOpen: false }))}
        onConfirm={handleExecuteReview}
        title={modalState.title}
        description={modalState.description}
        confirmLabel="Confirm & Sign to Audit Trail"
        tone={modalState.tone}
        loading={actionLoading}
      >
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-500">Target Rule:</span>
            <span className="font-mono font-semibold text-slate-900">{finding.rule_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Officer Role:</span>
            <span className="font-semibold text-slate-900">SCRUTINY_COMMITTEE</span>
          </div>
          {reviewerNotes && (
            <div className="pt-1 border-t border-slate-200 text-slate-600">
              <strong>Notes:</strong> {reviewerNotes}
            </div>
          )}
        </div>
      </ConfirmModal>
    </div>
  );
}
