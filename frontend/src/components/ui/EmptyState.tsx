import React from 'react';
import { HelpCircle } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ElementType;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

/**
 * Standardized empty state component guiding user toward clear operational recovery actions.
 *
 * @param title - Heading for empty state.
 * @param description - Explanatory text.
 * @param icon - Lucide icon.
 * @param actionLabel - Primary recovery button text.
 * @param onAction - Button action callback.
 */
export function EmptyState({
  title,
  description,
  icon: Icon = HelpCircle,
  actionLabel,
  onAction,
  className = ''
}: EmptyStateProps) {
  return (
    <div
      className={`text-center py-12 px-4 rounded-xl border border-dashed border-slate-300 bg-white/60 ${className}`}
    >
      <div className="mx-auto w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mb-3.5">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-900 mb-1">{title}</h3>
      <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="inline-flex items-center justify-center px-3.5 py-1.5 rounded-lg text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition-colors focus-ring"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
