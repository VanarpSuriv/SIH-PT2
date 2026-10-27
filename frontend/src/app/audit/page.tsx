'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Database,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  Lock,
  ArrowRight,
  Sliders,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { ConfirmModal } from '@/components/ui/ConfirmModal';

interface AuditEvent {
  id: string;
  application_id: string;
  action: string;
  timestamp: string;
  payload: Record<string, any>;
  prev_hash: string;
  hash: string;
}

interface ChainVerificationResponse {
  valid: boolean;
  events_checked: number;
  message?: string;
  corrupted_event_id?: string;
  expected_hash?: string;
  actual_hash?: string;
}

const API_BASE = 'http://localhost:8000';
const DEMO_OFFICER_TOKEN = process.env.NEXT_PUBLIC_OFFICER_TOKEN || 'demo-sih-2026-officer-token';

/**
 * Cryptographic Audit Trail Screen:
 * Displays all platform ingestion, evaluation, and officer review events with
 * live SHA-256 hash-chain verification and simulated tamper detection.
 */
export default function AuditTrailPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Chain Verification State
  const [verificationResult, setVerificationResult] = useState<ChainVerificationResponse | null>(null);
  const [verifying, setVerifying] = useState(false);

  // Search filter
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedPayloadId, setExpandedPayloadId] = useState<string | null>(null);

  // Demo Tamper Modal State
  const [tamperModalOpen, setTamperModalOpen] = useState(false);
  const [targetEventId, setTargetEventId] = useState<string>('');
  const [tampering, setTampering] = useState(false);
  const [tamperResult, setTamperResult] = useState<string | null>(null);

  useEffect(() => {
    fetchAuditEvents();
  }, []);

  const fetchAuditEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/api/audit`);
      if (!res.ok) throw new Error('Failed to load audit trail events');
      const data: AuditEvent[] = await res.json();
      setEvents(data);
    } catch (err: any) {
      setError(err.message || 'Error connecting to audit service');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    try {
      setVerifying(true);
      const res = await fetch(`${API_BASE}/api/audit/verify`);
      if (!res.ok) throw new Error('Verification request failed');
      const data: ChainVerificationResponse = await res.json();
      setVerificationResult(data);
    } catch (err: any) {
      setVerificationResult({
        valid: false,
        events_checked: 0,
        message: err.message || 'Error verifying hash chain'
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleExecuteTamper = async () => {
    if (!targetEventId) return;

    try {
      setTampering(true);
      setTamperResult(null);

      const formData = new FormData();
      formData.append('event_id', targetEventId);

      const res = await fetch(`${API_BASE}/api/audit/tamper`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${DEMO_OFFICER_TOKEN}`,
          'X-Demo-Mode': 'true',
          'X-Officer-Role': 'AICTE_ADMIN'
        },
        body: formData
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Tamper call failed. Ensure ENABLE_DEMO_TAMPER=true is configured.');
      }

      const data = await res.json();
      setTamperResult(`Demonstration tamper injected on event ${targetEventId}. Now run 'Verify Hash Chain Integrity' to see cryptographic detection.`);
      setTamperModalOpen(false);
      fetchAuditEvents();
    } catch (err: any) {
      alert(`Tamper error: ${err.message}`);
    } finally {
      setTampering(false);
    }
  };

  const filteredEvents = events.filter((evt) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      evt.id.toLowerCase().includes(q) ||
      evt.action.toLowerCase().includes(q) ||
      evt.application_id.toLowerCase().includes(q) ||
      JSON.stringify(evt.payload).toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Database className="w-6 h-6 text-emerald-600" />
            Tamper-Evident Cryptographic Audit Trail
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            SHA-256 hash-chained log guaranteeing non-repudiation and traceability of all system ingestions and reviewer determinations.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchAuditEvents}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors focus-ring"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition-colors focus-ring"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{verifying ? 'Verifying Hashes...' : 'Verify Hash Chain Integrity'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          {error}
        </div>
      )}

      {tamperResult && (
        <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{tamperResult}</span>
          </div>
          <button
            onClick={handleVerifyChain}
            className="font-semibold text-xs text-blue-700 hover:underline shrink-0 ml-3"
          >
            Verify Now &rarr;
          </button>
        </div>
      )}

      {/* Verification Result Banner */}
      {verificationResult && (
        <Card
          padding="md"
          className={
            verificationResult.valid
              ? 'bg-emerald-50/70 border-emerald-300 text-emerald-950'
              : 'bg-rose-50/70 border-rose-300 text-rose-950'
          }
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              {verificationResult.valid ? (
                <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700 shrink-0">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
              ) : (
                <div className="p-2 rounded-lg bg-rose-100 text-rose-700 shrink-0">
                  <XCircle className="w-5 h-5" />
                </div>
              )}
              <div className="space-y-1">
                <h3 className="text-sm font-bold">
                  {verificationResult.valid
                    ? 'Cryptographic Chain Integrity Confirmed'
                    : 'Cryptographic Tampering / Collision Detected!'}
                </h3>
                <p className="text-xs leading-relaxed">
                  {verificationResult.message ||
                    `Successfully validated SHA-256 recursive hashes across all ${verificationResult.events_checked} blocks.`}
                </p>
                {verificationResult.corrupted_event_id && (
                  <div className="text-[11px] font-mono mt-1 space-y-0.5">
                    <div>Corrupted Event ID: {verificationResult.corrupted_event_id}</div>
                    <div>Expected Hash: {verificationResult.expected_hash}</div>
                    <div>Actual Hash: {verificationResult.actual_hash}</div>
                  </div>
                )}
              </div>
            </div>

            <span className="text-xs font-mono font-semibold px-2 py-1 rounded bg-white/80 border shrink-0">
              {verificationResult.events_checked} Events Scanned
            </span>
          </div>
        </Card>
      )}

      {/* Search Bar */}
      <Card padding="sm" className="bg-white">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            id="search-audit"
            name="search_audit"
            type="text"
            aria-label="Search audit events by action, event ID, or payload keys"
            placeholder="Search by Action, Event ID, Application ID, or payload keys..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-9 pr-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus-ring"
          />
        </div>
      </Card>

      {/* Audit Log Table */}
      <Card padding="none" className="overflow-hidden border border-slate-200">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={6} />
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No Audit Events Recorded"
              description="No audit transactions match the current query. Ingest an application to populate the log."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Event & Action</th>
                  <th className="py-3 px-4">Application Case</th>
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">SHA-256 Hash Digest</th>
                  <th className="py-3 px-4 text-right">Payload</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 bg-white">
                {filteredEvents.map((evt) => {
                  const isPayloadOpen = expandedPayloadId === evt.id;

                  return (
                    <React.Fragment key={evt.id}>
                      <tr className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 font-mono whitespace-nowrap">
                          <div className="font-bold text-blue-700">{evt.action}</div>
                          <div className="text-[10px] text-slate-400">{evt.id}</div>
                        </td>

                        <td className="py-3 px-4 font-mono font-medium text-slate-900 whitespace-nowrap">
                          <Link
                            href={`/application/${evt.application_id}`}
                            className="hover:text-blue-600 hover:underline"
                          >
                            {evt.application_id}
                          </Link>
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap text-slate-500">
                          {new Date(evt.timestamp).toLocaleString()}
                        </td>

                        <td className="py-3 px-4 font-mono text-[11px] text-slate-600 max-w-xs truncate" title={evt.hash}>
                          <span className="text-emerald-700 font-bold">&#x2713;</span> {evt.hash.slice(0, 16)}...
                        </td>

                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <button
                            onClick={() =>
                              setExpandedPayloadId(isPayloadOpen ? null : evt.id)
                            }
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
                          >
                            <span>{isPayloadOpen ? 'Hide' : 'Inspect'}</span>
                            {isPayloadOpen ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </td>
                      </tr>

                      {isPayloadOpen && (
                        <tr className="bg-slate-50/70 border-b border-slate-100">
                          <td colSpan={5} className="p-4">
                            <div className="space-y-2 bg-white p-3 rounded-lg border border-slate-200 font-mono text-[11px]">
                              <div className="text-[10px] uppercase font-bold text-slate-400">
                                Event Payload Structure:
                              </div>
                              <pre className="text-slate-800 overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(evt.payload, null, 2)}
                              </pre>
                              <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-4 text-[10px] text-slate-500">
                                <span>Prev Hash: {evt.prev_hash}</span>
                                <span>Block Hash: {evt.hash}</span>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Isolated Sandbox Demonstration Tools */}
      <Card padding="md" className="border-amber-200 bg-amber-50/20 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-amber-100 pb-2">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-amber-600" />
                Isolated Sandbox Security Demonstration Tools
              </h3>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
                LOCAL DEMO ONLY
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Simulate an unauthorized database mutation to test the platform&apos;s SHA-256 hash-chain tamper detection capabilities.
            </p>
          </div>

          <button
            onClick={() => {
              if (events.length > 0) {
                setTargetEventId(events[0].id);
                setTamperModalOpen(true);
              }
            }}
            disabled={events.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-amber-900 bg-amber-100 hover:bg-amber-200 border border-amber-300 shadow-sm transition-colors shrink-0 focus-ring"
          >
            <Sliders className="w-3.5 h-3.5 text-amber-700" />
            <span>Simulate Unauthorized Mutation</span>
          </button>
        </div>

        <p className="text-[11px] text-slate-500 leading-relaxed">
          <strong>Security Boundary Notice:</strong> The <code>/api/audit/tamper</code> endpoint is strictly disabled by default (<code>ENABLE_DEMO_TAMPER=false</code>) and cannot be activated via client-side controls alone. It requires both server-level environment configuration and server-verified officer credentials.
        </p>
      </Card>

      {/* Simulated Tamper Modal */}
      <ConfirmModal
        isOpen={tamperModalOpen}
        onClose={() => setTamperModalOpen(false)}
        onConfirm={handleExecuteTamper}
        title="Simulate Audit Trail Tampering"
        description="This demo feature intentionally alters a database row payload without recalculating its cryptographic SHA-256 hash, demonstrating how unauthorized tampering is immediately caught by the chain verification algorithm."
        confirmLabel="Inject Tampered Payload"
        tone="warning"
        loading={tampering}
      >
        <div className="space-y-2 text-xs">
          <label htmlFor="target-event-select" className="block text-slate-700 font-semibold">Select Event ID to Tamper:</label>
          <select
            id="target-event-select"
            name="target_event_id"
            value={targetEventId}
            onChange={(e) => setTargetEventId(e.target.value)}
            className="w-full text-xs p-2 rounded border border-slate-300 font-mono"
          >
            {events.map((e) => (
              <option key={e.id} value={e.id}>
                {e.action} ({e.id})
              </option>
            ))}
          </select>
          <p className="text-[11px] text-slate-500">
            Note: This endpoint is strictly guarded on the server by ENABLE_DEMO_TAMPER=true and valid officer credentials.
          </p>
        </div>
      </ConfirmModal>
    </div>
  );
}
