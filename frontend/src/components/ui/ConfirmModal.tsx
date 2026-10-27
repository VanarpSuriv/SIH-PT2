'use client';

import React, { useEffect } from 'react';
import { AlertTriangle, X, ShieldAlert, Check } from 'lucide-react';

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: 'danger' | 'warning' | 'primary';
  loading?: boolean;
  children?: React.ReactNode;
}

/**
 * Accessible confirmation modal for high-friction officer review determinations
 * (confirming defects, dismissing findings, or triggering simulated tampering).
 */
export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm Action',
  cancelLabel = 'Cancel',
  tone = 'primary',
  loading = false,
  children
}: ConfirmModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !loading) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, loading, onClose]);

  if (!isOpen) return null;

  const toneConfig = {
    danger: {
      btn: 'bg-rose-600 hover:bg-rose-700 text-white',
      icon: AlertTriangle,
      iconBg: 'bg-rose-100 text-rose-600'
    },
    warning: {
      btn: 'bg-amber-600 hover:bg-amber-700 text-white',
      icon: AlertTriangle,
      iconBg: 'bg-amber-100 text-amber-600'
    },
    primary: {
      btn: 'bg-blue-600 hover:bg-blue-700 text-white',
      icon: ShieldAlert,
      iconBg: 'bg-blue-100 text-blue-600'
    }
  }[tone];

  const Icon = toneConfig.icon;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150 space-y-4"
      >
        <div className="flex items-start gap-3.5">
          <div className={`p-2.5 rounded-full ${toneConfig.iconBg} shrink-0`}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 id="modal-title" className="text-base font-semibold text-slate-900">
              {title}
            </h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              {description}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg focus-ring"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {children && <div className="pt-2">{children}</div>}

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors border border-slate-300"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2 text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-1.5 ${toneConfig.btn}`}
          >
            {loading ? (
              <span>Recording decision...</span>
            ) : (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>{confirmLabel}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
