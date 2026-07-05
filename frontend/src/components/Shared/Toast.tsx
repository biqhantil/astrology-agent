/* ── Toast notification ──────────────────────────────── */

import { useState, useEffect, type FC, type ReactNode } from 'react';

type ToastType = 'info' | 'success' | 'warning' | 'error';

interface ToastProps {
  message: string;
  type?: ToastType;
  duration?: number; // ms, 0 = persistent
  onClose?: () => void;
  action?: { label: string; onClick: () => void };
}

const typeStyles: Record<ToastType, string> = {
  info: 'border-accent/30 bg-accent/10 text-accent-light',
  success: 'border-green-500/30 bg-green-500/10 text-green-400',
  warning: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400',
  error: 'border-red-500/30 bg-red-500/10 text-red-400',
};

const Toast: FC<ToastProps> = ({
  message,
  type = 'info',
  duration = 5000,
  onClose,
  action,
}) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        setVisible(false);
        onClose?.();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  if (!visible) return null;

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-lg border shadow-xl backdrop-blur-sm transition-all duration-300 ${typeStyles[type]}`}
      role="alert"
    >
      <span className="text-sm flex-1">{message}</span>
      {action && (
        <button
          onClick={action.onClick}
          className="text-sm font-medium underline hover:no-underline whitespace-nowrap"
        >
          {action.label}
        </button>
      )}
      <button
        onClick={() => {
          setVisible(false);
          onClose?.();
        }}
        className="p-1 rounded hover:bg-black/20 transition-colors"
        aria-label="Dismiss"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
};

/* ── Toast container for multiple toasts ─────────────── */

export interface ToastItem {
  id: string;
  message: string;
  type?: ToastType;
  duration?: number;
  action?: { label: string; onClick: () => void };
}

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: FC<ToastContainerProps> = ({ toasts, onDismiss }) => (
  <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
    {toasts.map((t) => (
      <Toast
        key={t.id}
        message={t.message}
        type={t.type}
        duration={t.duration}
        onClose={() => onDismiss(t.id)}
        action={t.action}
      />
    ))}
  </div>
);

export default Toast;
