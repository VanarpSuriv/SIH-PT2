import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

/**
 * Standard enterprise container surface with crisp 1px borders and refined padding.
 *
 * @param children - Inner content.
 * @param className - Optional Tailwind overrides.
 * @param padding - Padding scale ('none', 'sm', 'md', 'lg').
 */
export function Card({ children, className = '', padding = 'md' }: CardProps) {
  const padMap = {
    none: 'p-0',
    sm: 'p-3 sm:p-4',
    md: 'p-5 sm:p-6',
    lg: 'p-6 sm:p-8'
  };

  return (
    <div
      className={`bg-white rounded-xl border border-slate-200/90 shadow-sm ${padMap[padding]} ${className}`}
    >
      {children}
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ElementType;
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  onClick?: () => void;
}

/**
 * High-density operational metric display card.
 *
 * @param title - Concise metric label.
 * @param value - Numerical or status count.
 * @param subtitle - Contextual detail.
 * @param icon - Lucide icon component.
 * @param tone - Visual semantic tone.
 * @param onClick - Optional click handler for drill-down filtering.
 */
export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  tone = 'default',
  onClick
}: MetricCardProps) {
  const toneMap = {
    default: { text: 'text-slate-900', iconBg: 'bg-slate-100 text-slate-700' },
    success: { text: 'text-emerald-900', iconBg: 'bg-emerald-50 text-emerald-700' },
    warning: { text: 'text-amber-900', iconBg: 'bg-amber-50 text-amber-700' },
    danger: { text: 'text-rose-900', iconBg: 'bg-rose-50 text-rose-700' },
    info: { text: 'text-blue-900', iconBg: 'bg-blue-50 text-blue-700' }
  };

  const selectedTone = toneMap[tone];

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-sm transition-all ${
        onClick ? 'cursor-pointer hover:border-slate-300 hover:shadow-md' : ''
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <div className={`text-2xl font-bold tracking-tight ${selectedTone.text}`}>
            {value}
          </div>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-lg ${selectedTone.iconBg}`}>
            <Icon className="w-5 h-5 shrink-0" />
          </div>
        )}
      </div>
    </div>
  );
}
