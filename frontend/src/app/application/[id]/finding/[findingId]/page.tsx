'use client';

import { useState, useEffect } from 'react';
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
  Binary,
  HelpCircle,
  Info,
  Calendar,
  AlertOctagon
} from 'lucide-react';

interface ExtractedField {
  name: string;
  value: any;
  raw_text: string;
  document_type: string;
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

interface Finding {
  id: string;
  application_id: string;
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
  fields_involved: ExtractedField[];
  metadata_context?: MetadataEvidenceContext;
  verification_result?: VerificationResult;
  review?: HumanReviewDecision;
  user_status: string;
  created_at: string;
}

export default function FindingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appId = params?.id as string;
  const findingId = params?.findingId as string;

  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFieldIdx, setSelectedFieldIdx] = useState(0);
  const [actionLoading, setActionLoading] = useState(false);
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [auditMessage, setAuditMessage] = useState<string | null>(null);
  const [imageReloadKey, setImageReloadKey] = useState(0);

  useEffect(() => {
    if (findingId) {
      loadFinding();
    }
  }, [findingId]);

  const loadFinding = async () => {
    try {
      setLoading(true);
      const res = await fetch(`http://localhost:8000/api/findings/${findingId}`);
      if (!res.ok) throw new Error('Failed to load finding details');
      const data = await res.json();
      setFinding(data);
      if (data.review?.reviewer_notes) {
        setReviewerNotes(data.review.reviewer_notes);
      }
    } catch (err: any) {
      setError(err.message || 'Error fetching finding');
    } finally {
      setLoading(false);
    }
  };

  const handleStructuredReview = async (
    decision: 'CONFIRMED_DEFECT' | 'DISMISSED_BENIGN' | 'REQUEST_CLARIFICATION'
  ) => {
    try {
      setActionLoading(true);
      setAuditMessage(null);

      const res = await fetch(`http://localhost:8000/api/findings/${findingId}/review`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          decision,
          reviewer_notes: reviewerNotes || `Officer selected ${decision}`,
          reviewer_id: 'AICTE-OFFICER-01',
        }),
      });

      if (!res.ok) throw new Error(`Failed to record review decision`);
      const result = await res.json();

      setFinding((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          lifecycle: result.lifecycle,
          review: {
            decision,
            reviewer_notes: reviewerNotes,
            reviewed_at: new Date().toISOString(),
            reviewed_by: 'AICTE-OFFICER-01',
          },
          user_status: decision === 'CONFIRMED_DEFECT' ? 'CONFIRMED' : decision === 'DISMISSED_BENIGN' ? 'DISMISSED' : 'IN_REVIEW',
        };
      });

      setAuditMessage(
        `Review decision '${decision}' immutably recorded to SHA-256 Audit Chain (Event ID: ${result.audit_event_id})`
      );
    } catch (err: any) {
      setError(err.message || 'Review action error');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400 mb-3" />
        <p className="text-slate-300 font-medium">Extracting Evidence Coordinates with PyMuPDF...</p>
      </div>
    );
  }

  if (error || !finding) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Finding Not Found</h2>
        <p className="text-slate-400 text-sm">{error}</p>
        <Link
          href={`/application/${appId}`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-sm hover:bg-slate-700"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Application</span>
        </Link>
      </div>
    );
  }

  const isFail = finding.status === 'FAIL';
  const isFlagged = finding.status === 'FLAGGED';
  const currentField = finding.fields_involved[selectedFieldIdx] || null;
  const lifecycle = finding.lifecycle || 'OPEN';
  const currentDecision = finding.review?.decision || (finding.user_status === 'CONFIRMED' ? 'CONFIRMED_DEFECT' : finding.user_status === 'DISMISSED' ? 'DISMISSED_BENIGN' : 'UNREVIEWED');
  const isMetadata = finding.rule_category === 'METADATA_INTEGRITY' || !!finding.metadata_context;

  return (
    <div className="space-y-8">
      {/* Back Button & Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href={`/application/${appId}`}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white px-3 py-1.5 rounded-xl hover:bg-slate-800/60 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Application Overview</span>
        </Link>

        {/* Triple Schema Separation Badges */}
        <div className="flex flex-wrap items-center gap-2">
          {/* 1. Lifecycle Badge */}
          <span
            className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-full border ${
              lifecycle === 'RESOLVED'
                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                : lifecycle === 'IN_REVIEW'
                ? 'bg-amber-950/60 border-amber-500/40 text-amber-300'
                : 'bg-slate-800 border-slate-700 text-slate-300'
            }`}
          >
            Lifecycle: {lifecycle}
          </span>

          {/* 2. Review Decision Badge */}
          {currentDecision !== 'UNREVIEWED' && (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
              Officer: {currentDecision}
            </span>
          )}
        </div>
      </div>

      {/* Finding Banner Header */}
      <div className="glass-panel p-6 sm:p-7 rounded-2xl shadow-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wider font-mono ${
                isFail
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  : isFlagged
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              }`}
            >
              {finding.status}
            </span>

            <span className="text-sm font-mono font-bold text-slate-200">
              {finding.rule_id} (Version {finding.rule_version})
            </span>

            <span
              className={`text-xs font-semibold px-2.5 py-0.5 rounded border ${
                finding.rule_category === 'STATUTORY_MANDATE'
                  ? 'bg-blue-500/10 border-blue-500/30 text-blue-300'
                  : isMetadata
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  : 'bg-purple-500/10 border-purple-500/30 text-purple-300'
              }`}
            >
              {finding.rule_category === 'STATUTORY_MANDATE'
                ? 'Statutory Mandate'
                : isMetadata
                ? 'Metadata Integrity'
                : 'Technical Consistency'}
            </span>

            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded ${
                finding.severity === 'CRITICAL'
                  ? 'bg-red-500/20 text-red-300'
                  : finding.severity === 'HIGH'
                  ? 'bg-amber-500/20 text-amber-300'
                  : 'bg-slate-800 text-slate-300'
              }`}
            >
              {finding.severity} SEVERITY
            </span>
          </div>

          <div className="flex items-center gap-2">
            {finding.aph_reference && (
              <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 font-mono">
                AICTE APH: {finding.aph_reference}
              </span>
            )}
            <span className="text-xs text-slate-500 font-mono">ID: {finding.id}</span>
          </div>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
          {finding.rule_name}
        </h1>

        {/* Claim Box */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-sm leading-relaxed text-slate-200 flex items-start gap-3">
          <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${isFail ? 'text-rose-400' : isMetadata ? 'text-amber-400' : 'text-blue-400'}`} />
          <div>
            <div className="font-semibold text-xs text-slate-400 uppercase tracking-wider mb-1">
              Evaluated Regulatory Finding
            </div>
            <div>{finding.claim}</div>
          </div>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          {finding.description}
        </p>

        {/* Dedicated Metadata Forensic Panel (Req 5) */}
        {finding.metadata_context && (
          <div className="p-5 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-4">
            <div className="flex items-center justify-between border-b border-amber-500/20 pb-2.5">
              <div className="flex items-center gap-2">
                <Binary className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold text-amber-300">
                  PDF Metadata Forensic Evidence Panel
                </h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                {finding.metadata_context.rule_triggered}
              </span>
            </div>

            {/* Non-Prejudicial Notice */}
            <div className="p-3 rounded-lg bg-amber-900/30 border border-amber-500/30 text-xs text-amber-200/90 leading-relaxed flex items-start gap-2.5">
              <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Technical Review Advisory: </span>
                Flagged for technical officer review; this does not constitute proof of document forgery. Metadata temporal differences or parser warnings may stem from PDF printer configurations, timezone shifts, or administrative re-saving.
              </div>
            </div>

            {/* Reason for Review */}
            <div className="space-y-1">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Reason for Review:
              </span>
              <p className="text-xs text-slate-200 font-mono bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                {finding.metadata_context.reason_for_review}
              </p>
            </div>

            {/* Side-by-Side: Original vs Normalized Values */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Original Values */}
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="text-xs font-semibold text-slate-300 border-b border-slate-800 pb-1 flex items-center justify-between">
                  <span>Original / Raw Document Values</span>
                  <span className="text-[10px] text-amber-400 font-mono">Raw ASN.1 / PDF Info</span>
                </div>
                <div className="space-y-1 text-xs font-mono text-slate-300">
                  {Object.entries(finding.metadata_context.original_values || {}).map(([k, v]) => (
                    <div key={k} className="flex flex-col">
                      <span className="text-slate-500 text-[10px]">{k}:</span>
                      <span className="text-amber-200 break-all">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Normalized Values */}
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="text-xs font-semibold text-slate-300 border-b border-slate-800 pb-1 flex items-center justify-between">
                  <span>Normalized Timestamps & Metrics</span>
                  <span className="text-[10px] text-emerald-400 font-mono">ISO-8601 UTC</span>
                </div>
                <div className="space-y-1 text-xs font-mono text-slate-300">
                  {Object.entries(finding.metadata_context.normalized_values || {}).map(([k, v]) => (
                    <div key={k} className="flex flex-col">
                      <span className="text-slate-500 text-[10px]">{k}:</span>
                      <span className="text-emerald-300 break-all">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Parsing Warnings */}
            {finding.metadata_context.parsing_warnings && finding.metadata_context.parsing_warnings.length > 0 && (
              <div className="space-y-1 pt-1">
                <span className="text-xs font-semibold text-amber-300">Parser Warnings Encountered:</span>
                <ul className="list-disc pl-4 text-xs text-slate-300 space-y-0.5 font-mono">
                  {finding.metadata_context.parsing_warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Verification Adapter Result */}
        {finding.verification_result && (
          <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800/90 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                External Authority Verification Result
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                {finding.verification_result.source}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400 font-mono">Issuer: {finding.verification_result.issuer}</span>
              <span className="text-slate-600">&bull;</span>
              <span className="font-semibold text-slate-200 uppercase font-mono">
                Status: {finding.verification_result.status}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed font-mono">
              {finding.verification_result.message}
            </p>
          </div>
        )}
      </div>

      {/* Grid: Document Highlighting on Left + Action Controls on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Server-Side PyMuPDF Evidence Highlighting */}
        <div className="lg:col-span-8 glass-panel p-6 rounded-2xl shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-400" />
              <h2 className="text-base font-semibold text-white">
                Server-Side Evidence Visualizer (PyMuPDF)
              </h2>
            </div>
            <span className="text-xs text-slate-400">
              Evidence bounding box highlighted directly on source PDF
            </span>
          </div>

          {/* Multiple Fields Selector if finding links across docs */}
          {finding.fields_involved.length > 1 && (
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-slate-400 block">
                Cross-Document Evidence Sources ({finding.fields_involved.length}):
              </span>
              <div className="flex flex-wrap gap-2">
                {finding.fields_involved.map((fld, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setSelectedFieldIdx(idx);
                      setImageReloadKey((k) => k + 1);
                    }}
                    className={`text-xs px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
                      selectedFieldIdx === idx
                        ? 'bg-blue-600 text-white font-semibold shadow-md shadow-blue-600/20'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>
                      {fld.document_type.replace('_', ' ').toUpperCase()} ({fld.name}: {String(fld.value)})
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Coordinate Metadata */}
          {currentField && (
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300 font-mono">
              <div>
                <span className="text-slate-500">Document: </span>
                <span className="text-blue-300 font-semibold">{currentField.document_type}</span>
                <span className="text-slate-500 ml-2">Page: </span>
                <span>{currentField.page_number}</span>
              </div>
              <div>
                <span className="text-slate-500">Bounding Box: </span>
                <span>[{currentField.bbox.map((v) => v.toFixed(1)).join(', ')}]</span>
                <span className="text-slate-500 ml-2">Confidence: </span>
                <span className="text-emerald-400">{(currentField.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}

          {/* Rendered Image Viewer */}
          <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center min-h-[420px] relative p-2 shadow-inner">
            <img
              key={imageReloadKey}
              src={`http://localhost:8000/api/findings/${finding.id}/evidence_image?field_idx=${selectedFieldIdx}&t=${imageReloadKey}`}
              alt="PyMuPDF Evidence Highlighting"
              className="max-w-full h-auto rounded-lg shadow-md transition-opacity duration-300"
            />
          </div>
        </div>

        {/* Right Column: Reviewer Action & Audit Trail Trigger */}
        <div className="lg:col-span-4 glass-panel p-6 rounded-2xl shadow-xl space-y-6">
          <div className="border-b border-slate-800 pb-3">
            <h2 className="text-base font-semibold text-white">Officer Review Determination</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Decisions are immutably logged to the SHA-256 cryptographic audit chain
            </p>
          </div>

          {auditMessage && (
            <div className="p-3.5 rounded-xl bg-emerald-950/50 border border-emerald-500/30 text-emerald-300 text-xs flex items-start gap-2 leading-relaxed">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <span>{auditMessage}</span>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Officer Justification / Audit Notes
              </label>
              <textarea
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="Enter justification, statutory exemption, or rationale for clarification..."
                rows={4}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="space-y-2.5">
              <button
                onClick={() => handleStructuredReview('CONFIRMED_DEFECT')}
                disabled={actionLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 transition-all disabled:opacity-50"
              >
                <Check className="w-4 h-4" />
                <span>Confirm Finding as Authentic Defect</span>
              </button>

              <button
                onClick={() => handleStructuredReview('DISMISSED_BENIGN')}
                disabled={actionLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-medium text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                <span>Dismiss Finding (Benign Anomaly / Exemption)</span>
              </button>

              <button
                onClick={() => handleStructuredReview('REQUEST_CLARIFICATION')}
                disabled={actionLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-amber-950/60 hover:bg-amber-900 border border-amber-600/50 text-amber-300 font-medium text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <HelpCircle className="w-4 h-4" />
                <span>Request Clarification from Applicant</span>
              </button>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-1.5">
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <Database className="w-3.5 h-3.5 text-blue-400" />
              <span>Immutable Chain Binding</span>
            </div>
            <p>
              Submitting a decision transitions the finding lifecycle and signs the officer notes directly into the hash chain, ensuring tamper-evident accountability.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
