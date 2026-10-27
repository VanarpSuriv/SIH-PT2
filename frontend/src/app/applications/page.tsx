'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Search,
  Filter,
  RefreshCw,
  Inbox,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  FileText,
  ChevronDown,
  ChevronUp,
  X,
  Sparkles,
  Info
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { StatusBadge, SeverityBadge } from '@/components/ui/Badge';
import { TableSkeleton } from '@/components/ui/Skeleton';
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

interface ApplicationCase {
  id: string;
  institution_name: string;
  application_date: string;
  status: string;
  created_at: string;
  documents: any[];
  findings: any[];
}

const API_BASE = 'http://localhost:8000';

/**
 * Application Queue screen: A high-density, searchable, filterable operational table
 * displaying ingested application packages, live compliance status, and 25 synthetic benchmark cases.
 */
export default function ApplicationQueuePage() {
  const router = useRouter();

  const [syntheticCases, setSyntheticCases] = useState<SyntheticCase[]>([]);
  const [liveApplications, setLiveApplications] = useState<ApplicationCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingCaseId, setLoadingCaseId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'live' | 'benchmark'>('live');

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [defectFilter, setDefectFilter] = useState<string>('ALL');
  const [sortField, setSortField] = useState<'id' | 'institution' | 'defects'>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {
    fetchQueueData();
  }, []);

  const fetchQueueData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [casesRes, appsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/cases`),
        fetch(`${API_BASE}/api/applications`)
      ]);

      if (casesRes.status === 'fulfilled' && casesRes.value.ok) {
        const data = await casesRes.value.json();
        setSyntheticCases(data);
      }

      if (appsRes.status === 'fulfilled' && appsRes.value.ok) {
        const data = await appsRes.value.json();
        setLiveApplications(data);
      }
    } catch (err: any) {
      setError('Error fetching queue items from backend service.');
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchCase = async (caseId: string) => {
    try {
      setLoadingCaseId(caseId);
      const res = await fetch(`${API_BASE}/api/cases/${caseId}/load`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to load application case');
      const app = await res.json();
      router.push(`/application/${app.id}`);
    } catch (err: any) {
      alert(err.message || 'Error launching case');
      setLoadingCaseId(null);
    }
  };

  // Filter & Search Logic
  const filteredCases = useMemo(() => {
    return syntheticCases.filter((c) => {
      // Search matching
      const query = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !query ||
        c.case_id.toLowerCase().includes(query) ||
        c.institution_name.toLowerCase().includes(query) ||
        c.permanent_id.toLowerCase().includes(query) ||
        c.expected_defects.some((d) => d.toLowerCase().includes(query));

      if (!matchesSearch) return false;

      // Status filter
      if (statusFilter === 'CLEAN' && !c.clean) return false;
      if (statusFilter === 'DEFECT' && c.clean) return false;

      // Defect category filter
      if (defectFilter !== 'ALL') {
        const hasDefect = c.expected_defects.some((d) => d.includes(defectFilter));
        if (!hasDefect) return false;
      }

      return true;
    }).sort((a, b) => {
      if (sortField === 'id') {
        return sortOrder === 'asc'
          ? a.case_id.localeCompare(b.case_id)
          : b.case_id.localeCompare(a.case_id);
      }
      if (sortField === 'institution') {
        return sortOrder === 'asc'
          ? a.institution_name.localeCompare(b.institution_name)
          : b.institution_name.localeCompare(a.institution_name);
      }
      return sortOrder === 'asc'
        ? a.expected_defects.length - b.expected_defects.length
        : b.expected_defects.length - a.expected_defects.length;
    });
  }, [syntheticCases, searchQuery, statusFilter, defectFilter, sortField, sortOrder]);

  const toggleSort = (field: 'id' | 'institution' | 'defects') => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const defectCategories = [
    { label: 'All Defects', value: 'ALL' },
    { label: 'Fire NOC / Expiry', value: 'FIRE' },
    { label: 'Land Area Shortfall', value: 'AREA' },
    { label: 'Missing Mandatory Doc', value: 'MISSING' },
    { label: 'Name / PID Mismatch', value: 'NAME' },
    { label: 'Date Conflict', value: 'DATE' },
    { label: 'Source Unavailable', value: 'SOURCE' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Application Scrutiny Backlog
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Browse and inspect institutional applications for AICTE Extension of Approval (EoA) against APH 2024–2027 norms.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchQueueData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors focus-ring"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Queue</span>
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm transition-colors focus-ring"
          >
            <span>+ Ingest New Package</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchQueueData} className="text-xs font-semibold underline text-rose-900">
            Retry
          </button>
        </div>
      )}

      {/* Queue Mode Selector: Strict separation of Live Scrutiny and Benchmark Suite */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setViewMode('live')}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            viewMode === 'live'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Inbox className="w-4 h-4" />
          <span>Live Ingested Queue</span>
          <span className="px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700 font-mono text-[10px]">
            {liveApplications.length}
          </span>
        </button>

        <button
          onClick={() => setViewMode('benchmark')}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            viewMode === 'benchmark'
              ? 'border-amber-600 text-amber-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4 text-amber-600" />
          <span>Synthetic Benchmark Suite</span>
          <span className="px-1.5 py-0.2 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-mono text-[10px]">
            25 Cases (Demo)
          </span>
        </button>
      </div>

      {/* VIEW 1: LIVE INGESTED APPLICATIONS */}
      {viewMode === 'live' && (
        <div className="space-y-4">
          {liveApplications.length === 0 ? (
            <Card padding="lg">
              <EmptyState
                title="No Live Applications Ingested Yet"
                description="Upload an institutional package using the Direct Ingestion Desk, or switch to the Synthetic Benchmark Suite to inspect pre-indexed cases."
                actionLabel="+ Ingest New Package"
                onAction={() => router.push('/')}
              />
            </Card>
          ) : (
            <Card padding="none" className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                      <th className="py-3 px-4">Application ID</th>
                      <th className="py-3 px-4">Institution Name</th>
                      <th className="py-3 px-4">Documents</th>
                      <th className="py-3 px-4">Findings Evaluated</th>
                      <th className="py-3 px-4">Processing Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700 bg-white">
                    {liveApplications.map((app) => (
                      <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-slate-900 whitespace-nowrap">
                          {app.id}
                        </td>
                        <td className="py-3 px-4 font-medium text-slate-900 max-w-xs">
                          <div className="truncate" title={app.institution_name}>
                            {app.institution_name}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                          {app.documents?.length || 0} PDF file(s)
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="font-semibold text-slate-800">{app.findings?.length || 0}</span> checks
                          {app.findings && app.findings.some((f) => f.status === 'FAIL') && (
                            <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                              Deficiencies Flagged
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <StatusBadge status={app.status} size="sm" />
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <Link
                            href={`/application/${app.id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm transition-colors focus-ring"
                          >
                            <span>Open Workspace</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* VIEW 2: SYNTHETIC BENCHMARK EVALUATION SUITE */}
      {viewMode === 'benchmark' && (
        <div className="space-y-4">
          {/* Benchmark Evaluation Disclosure Banner */}
          <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-950 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-amber-700 shrink-0" />
              <span>
                <strong>Evaluation Fixtures:</strong> These 25 benchmark cases are synthetic ground-truth test scenarios designed for SIH problem statement SIH26261 evaluation. They cover Fire NOC expiry, land shortfall, cloned seal tampering, and metadata anomalies.
              </span>
            </div>
          </div>

          {/* Filter and Search Bar */}
          <Card padding="sm" className="space-y-3 bg-white">
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Search Input */}
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  id="search-applications"
                  name="search_applications"
                  type="text"
                  aria-label="Search applications by ID, institution, or defect"
                  placeholder="Search by Case ID, institution name, permanent ID, or defect type..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full text-xs pl-9 pr-8 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus-ring"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => setStatusFilter('ALL')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    statusFilter === 'ALL'
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  All Status
                </button>
                <button
                  onClick={() => setStatusFilter('DEFECT')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    statusFilter === 'DEFECT'
                      ? 'bg-rose-600 text-white font-semibold'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Defects Flagged
                </button>
                <button
                  onClick={() => setStatusFilter('CLEAN')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    statusFilter === 'CLEAN'
                      ? 'bg-emerald-600 text-white font-semibold'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Compliant (Clean)
                </button>
              </div>
            </div>

            {/* Defect Category Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider shrink-0 mr-1">
                Category Filter:
              </span>
              {defectCategories.map((cat) => (
                <button
                  key={cat.value}
                  onClick={() => setDefectFilter(cat.value)}
                  className={`px-2.5 py-1 rounded-md text-xs whitespace-nowrap transition-colors ${
                    defectFilter === cat.value
                      ? 'bg-blue-50 text-blue-700 font-semibold border border-blue-200'
                      : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200/80'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
              {(searchQuery || statusFilter !== 'ALL' || defectFilter !== 'ALL') && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setStatusFilter('ALL');
                    setDefectFilter('ALL');
                  }}
                  className="text-xs text-rose-600 hover:text-rose-800 ml-2 font-medium shrink-0"
                >
                  Reset Filters
                </button>
              )}
            </div>
          </Card>

          {/* Benchmark Cases Table */}
          <Card padding="none" className="overflow-hidden">
            {loading ? (
              <div className="p-6">
                <TableSkeleton rows={8} />
              </div>
            ) : filteredCases.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  title="No Matching Benchmark Cases Found"
                  description="No benchmark test cases match your filter criteria. Clear filters to see all 25 scenarios."
                  actionLabel="Reset Search & Filters"
                  onAction={() => {
                    setSearchQuery('');
                    setStatusFilter('ALL');
                    setDefectFilter('ALL');
                  }}
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                      <th
                        className="py-3 px-4 cursor-pointer hover:text-slate-900"
                        onClick={() => toggleSort('id')}
                      >
                        <div className="flex items-center gap-1">
                          <span>Case ID</span>
                          {sortField === 'id' && (
                            sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 cursor-pointer hover:text-slate-900"
                        onClick={() => toggleSort('institution')}
                      >
                        <div className="flex items-center gap-1">
                          <span>Institution Name</span>
                          {sortField === 'institution' && (
                            sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </div>
                      </th>
                      <th className="py-3 px-4">PID & Documents</th>
                      <th
                        className="py-3 px-4 cursor-pointer hover:text-slate-900"
                        onClick={() => toggleSort('defects')}
                      >
                        <div className="flex items-center gap-1">
                          <span>Ground Truth Compliance / Defects</span>
                          {sortField === 'defects' && (
                            sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </div>
                      </th>
                      <th className="py-3 px-4">Expected State</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700 bg-white">
                    {filteredCases.map((c) => (
                      <tr key={c.case_id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-slate-900 whitespace-nowrap">
                          {c.case_id.toUpperCase()}
                        </td>
                        <td className="py-3 px-4 max-w-xs font-medium text-slate-900">
                          <div className="truncate" title={c.institution_name}>
                            {c.institution_name}
                          </div>
                          <div className="text-[11px] text-slate-400 font-normal">
                            Technical Education Applicant
                          </div>
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <div className="font-mono text-slate-600">{c.permanent_id}</div>
                          <div className="text-[11px] text-slate-400">
                            {c.generated_files.length} PDF attachments
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {c.clean ? (
                            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Full Ground Truth Compliance
                            </span>
                          ) : (
                            <div className="flex flex-wrap gap-1 max-w-sm">
                              {c.expected_defects.map((def, idx) => (
                                <span
                                  key={idx}
                                  className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-50 text-rose-800 border border-rose-200"
                                >
                                  {def}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <StatusBadge status={c.clean ? 'COMPLIANT' : 'ACTION_REQUIRED'} size="sm" />
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <button
                            onClick={() => handleLaunchCase(c.case_id)}
                            disabled={loadingCaseId === c.case_id}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 shadow-sm transition-colors focus-ring"
                          >
                            {loadingCaseId === c.case_id ? (
                              <>
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                <span>Processing...</span>
                              </>
                            ) : (
                              <>
                                <span>Load & Evaluate</span>
                                <ArrowRight className="w-3 h-3" />
                              </>
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
