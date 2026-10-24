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
  MapPin,
  Clock,
  RefreshCw,
  Eye,
  Check,
  X,
  ExternalLink,
  Layers,
  Database
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

interface Finding {
  id: string;
  application_id: string;
  rule_id: string;
  rule_version: string;
  rule_name: string;
  severity: string;
  status: string;
  claim: string;
  description: string;
  fields_involved: ExtractedField[];
  verification_result?: VerificationResult;
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
    } catch (err: any) {
      setError(err.message || 'Error fetching finding');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (actionType: 'confirm' | 'dismiss') => {
    try {
      setActionLoading(true);
      setAuditMessage(null);
      const formData = new FormData();
      formData.append('reviewer_notes', reviewerNotes || `Officer ${actionType.toUpperCase()}`);

      const res = await fetch(`http://localhost:8000/api/findings/${findingId}/${actionType}`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`Failed to ${actionType} finding`);
      const result = await res.json();
      setFinding((prev) => (prev ? { ...prev, user_status: actionType.toUpperCase() } : prev));
      setAuditMessage(`Action recorded to SHA-256 Audit Chain (Event ID: ${result.audit_event_id})`);
    } catch (err: any) {
      setError(err.message || 'Action error');
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
  const currentField = finding.fields_involved[selectedFieldIdx] || null;

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

        {finding.user_status !== 'UNREVIEWED' && (
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
            Current Review Status: {finding.user_status}
          </span>
        )}
      </div>

      {/* Finding Banner Header */}
      <div className="glass-panel p-6 sm:p-7 rounded-2xl shadow-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wider font-mono ${
                isFail
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              }`}
            >
              {finding.status}
            </span>
            <span className="text-sm font-mono font-bold text-slate-200">
              {finding.rule_id} (Version {finding.rule_version})
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

          <span className="text-xs text-slate-400 font-mono">
            Finding ID: {finding.id}
          </span>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
          {finding.rule_name}
        </h1>

        {/* Claim Box */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-sm leading-relaxed text-slate-200 flex items-start gap-3">
          <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${isFail ? 'text-rose-400' : 'text-blue-400'}`} />
          <div>
            <div className="font-semibold text-xs text-slate-400 uppercase tracking-wider mb-1">
              Evaluated Regulatory Claim
            </div>
            <div>{finding.claim}</div>
          </div>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          {finding.description}
        </p>

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
            <h2 className="text-base font-semibold text-white">Officer Determination</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Actions are committed to the tamper-evident hash chain
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
                Officer Inspection Notes
              </label>
              <textarea
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="Enter justification, statutory exemption, or confirmation notes..."
                rows={4}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="space-y-2.5">
              <button
                onClick={() => handleAction('confirm')}
                disabled={actionLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 transition-all disabled:opacity-50"
              >
                <Check className="w-4 h-4" />
                <span>Confirm Finding as Authentic Defect</span>
              </button>

              <button
                onClick={() => handleAction('dismiss')}
                disabled={actionLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-medium text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                <span>Dismiss Finding (Officer Exemption)</span>
              </button>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-1.5">
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <Database className="w-3.5 h-3.5 text-blue-400" />
              <span>Cryptographic Governance</span>
            </div>
            <p>
              Confirming or dismissing a finding triggers an automated cryptographic event row with SHA-256 hash chaining, preventing retroactive tampering of compliance approvals.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
