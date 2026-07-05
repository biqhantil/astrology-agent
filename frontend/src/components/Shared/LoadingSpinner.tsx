/* ── Loading spinner ─────────────────────────────────── */

import type { FC } from 'react';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
  label?: string;
}

const LoadingSpinner: FC<LoadingSpinnerProps> = ({
  size = 24,
  className = '',
  label = 'Loading...',
}) => (
  <div
    className={`inline-flex items-center gap-2 text-gray-400 ${className}`}
    role="status"
    aria-label={label}
  >
    <svg
      className="animate-spin"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
    {label && <span className="text-sm">{label}</span>}
  </div>
);

export default LoadingSpinner;
