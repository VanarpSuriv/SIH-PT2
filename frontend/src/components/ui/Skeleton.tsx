import React from 'react';

interface SkeletonProps {
  className?: string;
}

/**
 * Accessible skeleton loader component mimicking layout shapes during asynchronous data fetching.
 *
 * @param className - Size and positioning classes.
 */
export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-slate-200/80 ${className}`}
      aria-hidden="true"
    />
  );
}

/**
 * Skeleton container mimicking a table of records.
 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full rounded-lg" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-14 w-full rounded-lg" />
      ))}
    </div>
  );
}
