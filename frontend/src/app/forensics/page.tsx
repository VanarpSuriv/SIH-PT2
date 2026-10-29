'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  Layers,
  Search,
  Eye,
  Sliders,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Info,
  ArrowRight,
  ShieldAlert,
  Cpu,
  RefreshCw
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';

interface ApplicationCase {
  id: string;
  institution_name: string;
  status: string;
  documents: { id: string; filename: string; document_type: string }[];
  findings: { id: string; rule_id: string; rule_category?: string; claim: string; severity: string }[];
}

const API_BASE = '/api';

/**
 * Forensic Diagnostics Overview Screen:
 * Explains and surfaces multi-signal computer vision algorithms (ELA, SRM energy,
 * copy-move SIFT/RANSAC, typography analysis, and scan quality) for officer evaluation.
 */
export default function ForensicsOverviewPage() {
  const [applications, setApplications] = useState<ApplicationCase[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/applications`);
      if (res.ok) {
        const data = await res.json();
        setApplications(data);
      }
    } catch {
      // Non-critical fetch failure
    } finally {
      setLoading(false);
    }
  };

  const forensicAlgorithms = [
    {
      name: 'Error Level Analysis (ELA)',
      category: 'Compression Artifact Detection',
      description:
        'Resaves incoming document renders at 95% JPEG quality and computes differential residual error matrices to highlight regions with divergent compression histories (indicative of spliced or retouched content).',
      metric: 'Mean & Max Pixel Residuals',
      threshold: 'Mean > 12.0 / Max > 70.0'
    },
    {
      name: 'Spatial Rich Model (SRM) Noise Residuals',
      category: 'Steganographic / High-Pass Filtering',
      description:
        'Applies high-pass residual convolution kernels to isolate high-frequency pixel anomalies, revealing smoothed or cloned image regions across official seal and NOC boundaries.',
      metric: 'Average High-Pass Filter Energy',
      threshold: 'Energy Divergence > 3.0'
    },
    {
      name: 'SIFT / FLANN / RANSAC Copy-Move Detection',
      category: 'Keypoint Clustering & Homography',
      description:
        'Extracts Scale-Invariant Feature Transform keypoints and matches duplicated clusters within the same document to detect copy-pasted institutional stamps, signatures, or serial numbers.',
      metric: 'Inlier Keypoint Matches & Homography',
      threshold: 'Match Count >= 12'
    },
    {
      name: 'Typography Kerning & Font Outlier Analysis',
      category: 'Text Rendering Consistency',
      description:
        'Evaluates bounding-box stroke widths, character aspect ratios, and baseline alignments across numeric dates, acreage numbers, and institutional names to catch digitally inserted text.',
      metric: 'Z-Score Ratio on Token Geometry',
      threshold: 'Outlier Count > 3'
    },
    {
      name: 'Scan Quality & Glare Gate',
      category: 'Pre-flight Perspective & Luminescence',
      description:
        'Pre-screens document captures for excessive specular reflections, glare spots, or severe blur that would distort downstream OCR extraction or forensic accuracy.',
      metric: 'Laplacian Variance & Luminescence Ratio',
      threshold: 'Glare > 8.0% / Blur < 100'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-indigo-600" />
            Computer Vision Forensic Diagnostics Suite
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Algorithmic signal fusion detecting pixel manipulation, compression splicing, duplicated regions, and font anomalies.
          </p>
        </div>

        <Link
          href="/applications"
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm transition-colors focus-ring"
        >
          <span>Open Application Queue</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Mandatory Regulatory Forensic Disclosure */}
      <Card padding="md" className="border-indigo-200 bg-indigo-50/30 space-y-2">
        <div className="flex items-center gap-2 text-indigo-950 font-bold text-xs uppercase tracking-wide">
          <Info className="w-4 h-4 text-indigo-700 shrink-0" />
          <span>Decision-Support Forensics Protocol & Evidentiary Standard</span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          In strict accordance with administrative scrutiny standards, automated computer vision forensic signals (ELA heatmaps, SRM energy, copy-move keypoints) are <strong>preliminary decision-support observations</strong>. They prompt targeted visual examination by authorized scrutiny officers and do NOT independently establish legal proof of document forgery or institutional fraud.
        </p>
      </Card>

      {/* Forensic Techniques Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {forensicAlgorithms.map((algo, idx) => (
          <Card key={idx} padding="md" className="space-y-3 border-slate-200 bg-white">
            <div className="space-y-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600">
                {algo.category}
              </span>
              <h3 className="text-xs font-bold text-slate-900">{algo.name}</h3>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed min-h-[72px]">
              {algo.description}
            </p>

            <div className="pt-2 border-t border-slate-100 space-y-1 text-[11px] text-slate-500">
              <div className="flex justify-between">
                <span>Signal Metric:</span>
                <span className="font-mono text-slate-800">{algo.metric}</span>
              </div>
              <div className="flex justify-between">
                <span>Advisory Gate:</span>
                <span className="font-mono text-slate-700">{algo.threshold}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Ingested Cases Forensic Index */}
      <Card padding="md" className="space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-900">
            Active Application Cases with Forensic Signals
          </h2>
          <span className="text-xs text-slate-400">
            {applications.length} case(s) loaded
          </span>
        </div>

        {applications.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {applications.map((app) => (
              <div
                key={app.id}
                className="py-3 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 hover:bg-slate-50 px-2 rounded-lg transition-colors"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-900">{app.id}</span>
                    <StatusBadge status={app.status} size="sm" />
                  </div>
                  <div className="text-slate-600 font-medium mt-0.5">{app.institution_name}</div>
                  <div className="text-[11px] text-slate-400">
                    {app.documents.length} PDF attachments analyzed &bull; {app.findings.length} findings
                  </div>
                </div>

                <Link
                  href={`/application/${app.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 shadow-sm transition-colors shrink-0"
                >
                  <span>Inspect Evidence & ELA Heatmaps</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No Ingested Applications Yet"
            description="Ingest a document package or launch a pre-indexed case to inspect live computer vision forensic diagnostic signals."
            actionLabel="Go to Ingestion Desk"
            onAction={() => window.location.href = '/'}
          />
        )}
      </Card>
    </div>
  );
}
