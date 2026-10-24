'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { UploadCloud, FileText, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck, RefreshCw, Sparkles, Filter } from 'lucide-react';

interface SyntheticCase {
  case_id: string;
  institution_name: string;
  application_id: string;
  permanent_id: string;
  expected_defects: string[];
  clean: boolean;
  generated_files: string[];
}

export default function UploadPage() {
  const router = useRouter();
  const [cases, setCases] = useState<SyntheticCase[]>([]);
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [institutionName, setInstitutionName] = useState('Apex Institute of Technology');
  const [filterTag, setFilterTag] = useState<string>('ALL');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      setLoadingCases(true);
      const res = await fetch('http://localhost:8000/api/cases');
      if (!res.ok) throw new Error('Failed to fetch synthetic cases');
      const data = await res.json();
      setCases(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Error connecting to verification service');
    } finally {
      setLoadingCases(false);
    }
  };

  const handleCaseSelect = async (caseId: string) => {
    try {
      setLoadingAction(`loading_${caseId}`);
      setErrorMessage(null);
      const res = await fetch(`http://localhost:8000/api/cases/${caseId}/load`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to load synthetic case');
      const app = await res.json();
      router.push(`/application/${app.id}`);
    } catch (err: any) {
      setErrorMessage(err.message || 'Error loading case');
      setLoadingAction(null);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (uploadedFiles.length === 0) {
      setErrorMessage('Please select at least one PDF file to upload.');
      return;
    }

    try {
      setLoadingAction('uploading');
      setErrorMessage(null);
      const formData = new FormData();
      formData.append('institution_name', institutionName);
      uploadedFiles.forEach((file) => {
        formData.append('files', file);
      });

      const res = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('File upload and verification failed');
      const app = await res.json();
      router.push(`/application/${app.id}`);
    } catch (err: any) {
      setErrorMessage(err.message || 'Upload error');
      setLoadingAction(null);
    }
  };

  const defectCategories = [
    { label: 'All Cases', value: 'ALL' },
    { label: 'Clean (5)', value: 'CLEAN' },
    { label: 'Missing Doc (3)', value: 'MISSING' },
    { label: 'Expired NOC (3)', value: 'EXPIRED' },
    { label: 'Name Mismatch (3)', value: 'NAME' },
    { label: 'Date Conflict (3)', value: 'DATE' },
    { label: 'Area Deficit (3)', value: 'AREA' },
    { label: 'Faculty Mismatch (2)', value: 'FACULTY' },
    { label: 'Simulated Unavailable (3)', value: 'SOURCE' },
  ];

  const filteredCases = cases.filter((c) => {
    if (filterTag === 'ALL') return true;
    if (filterTag === 'CLEAN') return c.clean;
    if (filterTag === 'MISSING') return c.expected_defects.some((d) => d.includes('MISSING'));
    if (filterTag === 'EXPIRED') return c.expected_defects.some((d) => d.includes('EXPIRED') || d.includes('OUTDATED'));
    if (filterTag === 'NAME') return c.expected_defects.some((d) => d.includes('NAME'));
    if (filterTag === 'DATE') return c.expected_defects.some((d) => d.includes('DATE'));
    if (filterTag === 'AREA') return c.expected_defects.some((d) => d.includes('AREA'));
    if (filterTag === 'FACULTY') return c.expected_defects.some((d) => d.includes('FACULTY'));
    if (filterTag === 'SOURCE') return c.expected_defects.some((d) => d.includes('SOURCE') || d.includes('ISSUER'));
    return true;
  });

  return (
    <div className="space-y-10">
      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Autonomous AICTE Approval Handshake & Evidence Extraction</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
          Extension of Approval (EoA) Verification
        </h1>
        <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
          Upload multi-document institutional packages or launch from the 25 pre-indexed synthetic ground truth cases.
          Verifies document completeness, validity dates, RapidFuzz cross-document consistency, and cryptographic audit chains.
        </p>
      </div>

      {errorMessage && (
        <div className="max-w-2xl mx-auto p-4 rounded-xl bg-red-950/60 border border-red-500/30 text-red-300 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Grid: Upload Box + Synthetic Case Selector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Upload Form Box */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-6 sm:p-7 shadow-xl space-y-6">
          <div className="flex items-center gap-2.5 border-b border-slate-800 pb-4">
            <UploadCloud className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">Direct Document Ingestion</h2>
          </div>

          <form onSubmit={handleFileUpload} className="space-y-5">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Applicant Institution Name
              </label>
              <input
                type="text"
                value={institutionName}
                onChange={(e) => setInstitutionName(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. Apex Institute of Technology"
                required
              />
            </div>

            {/* Drag & Drop Zone */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Upload Institutional PDFs (Application, Land Deed, Fire NOC, Approval, Faculty List)
              </label>
              <div className="border-2 border-dashed border-slate-700 hover:border-blue-500/60 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-slate-900/40 relative">
                <input
                  type="file"
                  multiple
                  accept=".pdf"
                  onChange={(e) => {
                    if (e.target.files) {
                      setUploadedFiles(Array.from(e.target.files));
                    }
                  }}
                  className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                />
                <div className="space-y-2">
                  <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 mx-auto flex items-center justify-center">
                    <FileText className="w-6 h-6" />
                  </div>
                  <p className="text-xs font-medium text-slate-300">
                    Drag and drop PDF files here, or click to browse
                  </p>
                  <p className="text-[11px] text-slate-500">
                    PDF format only. SHA-256 hash calculated at edge.
                  </p>
                </div>
              </div>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="space-y-2 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-xs font-semibold text-slate-400 block">
                  Selected Files ({uploadedFiles.length}):
                </span>
                <ul className="space-y-1 max-h-32 overflow-y-auto text-xs text-slate-300">
                  {uploadedFiles.map((f, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                      <span className="truncate">{f.name}</span>
                      <span className="text-slate-500 text-[10px]">({Math.round(f.size / 1024)} KB)</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button
              type="submit"
              disabled={loadingAction === 'uploading' || uploadedFiles.length === 0}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loadingAction === 'uploading' ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Ingesting & Verifying Evidence...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Run Verification Pipeline</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* 25 Synthetic Test Cases Grid */}
        <div className="lg:col-span-7 glass-panel rounded-2xl p-6 sm:p-7 shadow-xl space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-semibold text-white">
                Pre-indexed Test Set (25 Synthetic Cases)
              </h2>
            </div>
            <span className="text-xs text-slate-400">
              Click any case to test live
            </span>
          </div>

          {/* Filter Chips */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
            {defectCategories.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setFilterTag(cat.value)}
                className={`text-xs px-2.5 py-1 rounded-lg transition-all ${
                  filterTag === cat.value
                    ? 'bg-blue-600 text-white font-semibold shadow-sm'
                    : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Case Items List */}
          {loadingCases ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-400" />
              <span>Loading synthetic test cases...</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[480px] overflow-y-auto pr-1">
              {filteredCases.map((c) => {
                const isLoading = loadingAction === `loading_${c.case_id}`;
                return (
                  <div
                    key={c.case_id}
                    onClick={() => !isLoading && handleCaseSelect(c.case_id)}
                    className="glass-card rounded-xl p-3.5 hover:bg-slate-800/50 cursor-pointer transition-all border border-slate-800/90 hover:border-blue-500/40 group flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          {c.case_id}
                        </span>
                        {c.clean ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                            <CheckCircle2 className="w-3 h-3" />
                            Clean Case
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
                            <AlertTriangle className="w-3 h-3" />
                            Planted Defect
                          </span>
                        )}
                      </div>

                      <h3 className="text-sm font-semibold text-slate-200 group-hover:text-blue-300 transition-colors line-clamp-1">
                        {c.institution_name}
                      </h3>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {c.application_id} &bull; {c.generated_files.length} Docs
                      </p>

                      {c.expected_defects.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {c.expected_defects.map((def, idx) => (
                            <span
                              key={idx}
                              className="text-[9px] px-1.5 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/50 font-mono"
                            >
                              {def}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-xs text-blue-400 group-hover:text-blue-300">
                      <span>{isLoading ? 'Processing...' : 'Run EoA Verification'}</span>
                      <ArrowRight className={`w-3.5 h-3.5 group-hover:translate-x-1 transition-transform ${isLoading ? 'animate-pulse' : ''}`} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
