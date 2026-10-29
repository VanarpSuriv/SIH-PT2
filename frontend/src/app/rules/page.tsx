'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  BookOpen,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  Sparkles,
  Info
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { CategoryBadge, SeverityBadge } from '@/components/ui/Badge';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';

interface RuleDefinition {
  id: string;
  version: string;
  rule_type: string;
  rule_category: string;
  title: string;
  aph_reference: string;
  source_section: string;
  page_reference?: string;
  applicability_conditions: string;
  supported_requirement: string;
  severity: string;
  description: string;
}

interface RulesResponse {
  version: string;
  handbook_edition: string;
  rules: RuleDefinition[];
}

const API_BASE = '/api';

/**
 * Regulatory Rules Matrix Screen:
 * Displays all active compliance checks configured in accordance with the
 * official AICTE Approval Process Handbook (APH) 2024–2027.
 */
export default function RegulatoryRulesPage() {
  const [rulesData, setRulesData] = useState<RulesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [expandedRule, setExpandedRule] = useState<string | null>(null);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/rules`);
      if (!res.ok) throw new Error('Failed to load regulatory rules matrix');
      const data: RulesResponse = await res.json();
      setRulesData(data);
    } catch (err: any) {
      setError(err.message || 'Error connecting to rules repository');
    } finally {
      setLoading(false);
    }
  };

  const rulesList = rulesData?.rules || [];

  const filteredRules = rulesList.filter((r) => {
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !q ||
      r.id.toLowerCase().includes(q) ||
      r.title.toLowerCase().includes(q) ||
      r.description.toLowerCase().includes(q) ||
      (r.aph_reference && r.aph_reference.toLowerCase().includes(q));

    if (!matchesSearch) return false;

    if (categoryFilter !== 'ALL' && r.rule_category !== categoryFilter) {
      return false;
    }

    return true;
  });

  const statutoryCount = rulesList.filter((r) => r.rule_category === 'STATUTORY_MANDATE').length;
  const consistencyCount = rulesList.filter((r) => r.rule_category === 'TECHNICAL_CONSISTENCY').length;
  const metadataCount = rulesList.filter((r) => r.rule_category === 'METADATA_INTEGRITY').length;
  const forensicCount = rulesList.filter((r) => r.rule_category === 'FORENSIC_ADVISORY').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-blue-600" />
            AICTE Regulatory Matrix & Rule Citations
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Authoritative legal traceability against {rulesData?.handbook_edition || 'AICTE Approval Process Handbook 2024–2027'}.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="https://www.aicte-india.org/sites/default/files/APH%20Final.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors focus-ring"
          >
            <BookOpen className="w-3.5 h-3.5 text-blue-600" />
            <span>Official APH PDF</span>
            <ExternalLink className="w-3 h-3 text-slate-400" />
          </a>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          {error}
        </div>
      )}

      {/* Category Filter Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <button
          onClick={() => setCategoryFilter('STATUTORY_MANDATE')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            categoryFilter === 'STATUTORY_MANDATE'
              ? 'bg-purple-50 border-purple-300 ring-2 ring-purple-600/20'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <span className="text-[10px] font-semibold uppercase text-purple-700">Legal Requirements</span>
          <div className="text-lg font-bold text-purple-950 mt-0.5">{statutoryCount} Rules</div>
          <p className="text-[11px] text-purple-800/80 mt-1">
            Ch. VI §6.17(i) Fire & Safety, Annexure 3 §3.1 Land
          </p>
        </button>

        <button
          onClick={() => setCategoryFilter('TECHNICAL_CONSISTENCY')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            categoryFilter === 'TECHNICAL_CONSISTENCY'
              ? 'bg-slate-100 border-slate-400 ring-2 ring-slate-600/20'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <span className="text-[10px] font-semibold uppercase text-slate-600">Reconciliation Checks</span>
          <div className="text-lg font-bold text-slate-900 mt-0.5">{consistencyCount} Rules</div>
          <p className="text-[11px] text-slate-500 mt-1">
            Cross-document RapidFuzz matching & entity consistency
          </p>
        </button>

        <button
          onClick={() => setCategoryFilter('METADATA_INTEGRITY')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            categoryFilter === 'METADATA_INTEGRITY'
              ? 'bg-amber-50 border-amber-300 ring-2 ring-amber-600/20'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <span className="text-[10px] font-semibold uppercase text-amber-700">Metadata Signals</span>
          <div className="text-lg font-bold text-amber-950 mt-0.5">{metadataCount} Rules</div>
          <p className="text-[11px] text-amber-800/80 mt-1">
            PDF header date parsing, timestamp anomalies & warnings
          </p>
        </button>

        <button
          onClick={() => setCategoryFilter('FORENSIC_ADVISORY')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            categoryFilter === 'FORENSIC_ADVISORY'
              ? 'bg-indigo-50 border-indigo-300 ring-2 ring-indigo-600/20'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <span className="text-[10px] font-semibold uppercase text-indigo-700">CV Forensics</span>
          <div className="text-lg font-bold text-indigo-950 mt-0.5">{forensicCount} Rules</div>
          <p className="text-[11px] text-indigo-800/80 mt-1">
            Error Level Analysis (ELA), SRM energy, copy-move
          </p>
        </button>
      </div>

      {/* Search Bar */}
      <Card padding="sm" className="bg-white">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              id="search-rules"
              name="search_rules"
              type="text"
              aria-label="Search regulatory rules by Rule ID, handbook clause, or requirement"
              placeholder="Search by Rule ID, Handbook clause, title, or requirement..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-9 pr-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus-ring"
            />
          </div>
          {categoryFilter !== 'ALL' && (
            <button
              onClick={() => setCategoryFilter('ALL')}
              className="text-xs text-blue-600 hover:underline shrink-0 font-medium"
            >
              Clear Category Filter
            </button>
          )}
        </div>
      </Card>

      {/* Rules List */}
      {loading ? (
        <TableSkeleton rows={6} />
      ) : filteredRules.length === 0 ? (
        <EmptyState
          title="No Rules Match Your Filter"
          description="Try broadening your search term or clearing the active category filter."
          actionLabel="Show All Rules"
          onAction={() => {
            setSearchQuery('');
            setCategoryFilter('ALL');
          }}
        />
      ) : (
        <div className="space-y-3">
          {filteredRules.map((rule) => {
            const isExpanded = expandedRule === rule.id;

            return (
              <Card key={rule.id} padding="none" className="overflow-hidden border border-slate-200">
                <div
                  onClick={() => setExpandedRule(isExpanded ? null : rule.id)}
                  className="p-4 bg-white hover:bg-slate-50 cursor-pointer flex items-center justify-between transition-colors border-b border-slate-100"
                >
                  <div className="space-y-1 min-w-0 pr-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900">{rule.id}</span>
                      <CategoryBadge category={rule.rule_category} />
                      <SeverityBadge severity={rule.severity} />
                      <span className="text-[10px] font-mono text-slate-500">v{rule.version}</span>
                    </div>
                    <h3 className="text-xs font-semibold text-slate-800">{rule.title}</h3>
                    <p className="text-xs text-slate-500 leading-snug line-clamp-1">{rule.description}</p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-blue-600 font-medium">
                      {isExpanded ? 'Hide Citation' : 'View Full Citation'}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 bg-slate-50/70 text-xs space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1">
                        <span className="text-[10px] uppercase font-bold text-slate-400">
                          Handbook Legal Citation:
                        </span>
                        <p className="font-mono text-slate-800 text-[11px] font-medium">
                          {rule.aph_reference || 'N/A'}
                        </p>
                        {rule.page_reference && (
                          <p className="text-[10px] text-slate-500">
                            Pages: {rule.page_reference}
                          </p>
                        )}
                      </div>

                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1">
                        <span className="text-[10px] uppercase font-bold text-slate-400">
                          Applicability Conditions:
                        </span>
                        <p className="text-slate-700 text-[11px] leading-relaxed">
                          {rule.applicability_conditions || 'Applies to all institutional applications.'}
                        </p>
                      </div>
                    </div>

                    <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-400">
                        Supported Statutory Requirement:
                      </span>
                      <p className="text-slate-800 text-xs leading-relaxed font-medium">
                        {rule.supported_requirement || rule.description}
                      </p>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
