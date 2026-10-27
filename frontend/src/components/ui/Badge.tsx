import React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  FileCheck,
  Sparkles,
  Search
} from 'lucide-react';

/**
 * StatusBadge props definition.
 */
interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
  className?: string;
}

/**
 * Standardized status badge communicating compliance, verification, and lifecycle states.
 * Enforces WCAG 2.2 AA contrast ratios and pair status text with semantic icons.
 *
 * @param status - Backend status code (e.g., PASS, FAIL, FLAGGED, INDETERMINATE, VERIFIED).
 * @param size - Visual scale ('sm' or 'md').
 * @param showIcon - Whether to render the status icon.
 */
export function StatusBadge({ status, size = 'sm', showIcon = true, className = '' }: StatusBadgeProps) {
  const norm = (status || '').toUpperCase().trim();

  let bg = 'bg-slate-100 text-slate-700 border-slate-200';
  let Icon = HelpCircle;
  let label = status || 'Unknown';

  if (norm === 'PASS' || norm === 'VERIFIED' || norm === 'COMPLIANT' || norm === 'VERIFIED_COMPLIANT' || norm === 'INTACT' || norm === 'REQUIREMENT_SATISFIED') {
    bg = 'bg-emerald-50 text-emerald-800 border-emerald-200';
    Icon = CheckCircle2;
    label = norm === 'PASS' ? 'Requirement Satisfied' : norm === 'VERIFIED_COMPLIANT' ? 'Verified Compliant' : norm === 'VERIFIED' ? 'Verified' : 'Compliant';
  } else if (norm === 'CONFIRMED' || norm === 'CONFIRMED_DEFECT') {
    bg = 'bg-purple-50 text-purple-900 border-purple-200 font-medium';
    Icon = FileCheck;
    label = 'Reviewer-Confirmed Defect';
  } else if (norm === 'DISMISSED' || norm === 'DISMISSED_BENIGN' || norm === 'RESOLVED') {
    bg = 'bg-slate-100 text-slate-700 border-slate-200';
    Icon = ShieldCheck;
    label = norm === 'DISMISSED_BENIGN' ? 'Reviewer-Dismissed (Benign)' : 'Review Completed';
  } else if (norm === 'REQUEST_CLARIFICATION' || norm === 'IN_REVIEW') {
    bg = 'bg-sky-50 text-sky-800 border-sky-200';
    Icon = Clock;
    label = norm === 'REQUEST_CLARIFICATION' ? 'Clarification Requested' : 'Under Review';
  } else if (norm === 'FAIL' || norm === 'ACTION_REQUIRED' || norm === 'NON_COMPLIANT' || norm === 'DEFECT_DETECTED') {
    bg = 'bg-rose-50 text-rose-800 border-rose-200';
    Icon = XCircle;
    label = norm === 'ACTION_REQUIRED' ? 'Officer Review Required' : 'Deficiency Flagged';
  } else if (norm === 'EXPIRED') {
    bg = 'bg-rose-50 text-rose-800 border-rose-200';
    Icon = Clock;
    label = 'Document Expired';
  } else if (norm === 'MISMATCH') {
    bg = 'bg-orange-50 text-orange-800 border-orange-200';
    Icon = AlertTriangle;
    label = 'Field Mismatch Detected';
  } else if (norm === 'TAMPERED') {
    bg = 'bg-rose-100 text-rose-900 border-rose-300 font-semibold';
    Icon = ShieldAlert;
    label = 'Tampering Detected';
  } else if (norm === 'FLAGGED' || norm === 'WARNING' || norm === 'MODIFIED') {
    bg = 'bg-amber-50 text-amber-800 border-amber-200';
    Icon = AlertTriangle;
    label = 'Flagged for Review';
  } else if (norm === 'FORENSIC_ADVISORY' || norm === 'ANOMALY_DETECTED') {
    bg = 'bg-indigo-50 text-indigo-900 border-indigo-200';
    Icon = Sparkles;
    label = 'Forensic Advisory';
  } else if (norm === 'SOURCE_UNAVAILABLE' || norm === 'UNAVAILABLE_SOURCE') {
    bg = 'bg-amber-50 text-amber-900 border-amber-300';
    Icon = HelpCircle;
    label = 'Source Registry Unavailable';
  } else if (norm === 'INDETERMINATE' || norm === 'INSUFFICIENT_EVIDENCE') {
    bg = 'bg-amber-50 text-amber-900 border-amber-300';
    Icon = HelpCircle;
    label = 'Insufficient Evidence';
  } else if (norm === 'PENDING') {
    bg = 'bg-slate-100 text-slate-600 border-slate-200';
    Icon = Clock;
    label = 'Verification Pending';
  } else if (norm === 'UNREVIEWED' || norm === 'OPEN') {
    bg = 'bg-blue-50 text-blue-800 border-blue-200';
    Icon = Clock;
    label = 'Awaiting Review';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-md whitespace-nowrap ${sizeClasses} ${bg} ${className}`}
    >
      {showIcon && <Icon className={size === 'sm' ? 'w-3.5 h-3.5 shrink-0' : 'w-4 h-4 shrink-0'} />}
      <span>{label}</span>
    </span>
  );
}

/**
 * SeverityBadge props definition.
 */
interface SeverityBadgeProps {
  severity: string;
}

/**
 * Renders priority/severity levels with semantic coloring and non-color text labels.
 *
 * @param severity - CRITICAL, HIGH, MEDIUM, LOW, or ADVISORY.
 */
export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const norm = (severity || '').toUpperCase().trim();

  let bg = 'bg-slate-100 text-slate-700 border-slate-200';
  if (norm === 'CRITICAL') {
    bg = 'bg-rose-100 text-rose-900 border-rose-300 font-semibold';
  } else if (norm === 'HIGH') {
    bg = 'bg-rose-50 text-rose-800 border-rose-200';
  } else if (norm === 'MEDIUM') {
    bg = 'bg-amber-50 text-amber-800 border-amber-200';
  } else if (norm === 'LOW') {
    bg = 'bg-blue-50 text-blue-700 border-blue-200';
  } else if (norm === 'ADVISORY' || norm === 'INFO') {
    bg = 'bg-indigo-50 text-indigo-700 border-indigo-200';
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${bg}`}>
      {norm}
    </span>
  );
}

/**
 * CategoryBadge props definition.
 */
interface CategoryBadgeProps {
  category?: string;
}

/**
 * Distinguishes statutory legal requirements from technical application consistency checks,
 * metadata integrity, and computer vision forensic advisories.
 *
 * @param category - Rule category enum from backend.
 */
export function CategoryBadge({ category }: CategoryBadgeProps) {
  const norm = (category || 'STATUTORY_MANDATE').toUpperCase().trim();

  if (norm === 'STATUTORY_MANDATE') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-purple-50 text-purple-900 border border-purple-200">
        <ShieldAlert className="w-3 h-3 text-purple-700" />
        Statutory Mandate
      </span>
    );
  }

  if (norm === 'METADATA_INTEGRITY') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200">
        <Search className="w-3 h-3 text-amber-700" />
        Metadata Integrity
      </span>
    );
  }

  if (norm === 'FORENSIC_ADVISORY') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-900 border border-indigo-200">
        <Sparkles className="w-3 h-3 text-indigo-700" />
        Forensic Advisory
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200">
      <FileCheck className="w-3 h-3 text-slate-600" />
      Technical Consistency
    </span>
  );
}
