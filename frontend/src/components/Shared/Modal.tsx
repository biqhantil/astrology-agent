/* ── Modal / Overlay dialog ──────────────────────────── */

import { useEffect, type FC, type ReactNode } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  /** Max width class (default: max-w-md) */
  maxWidth?: string;
}

const Modal: FC<ModalProps> = ({
  open,
  onClose,
  title,
  children,
  maxWidth = 'max-w-md',
}) => {
  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={`relative w-full ${maxWidth} rounded-xl bg-surface border border-gray-800 shadow-2xl animate-in fade-in zoom-in-95`}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
            <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-surface-light text-gray-400 hover:text-gray-200 transition-colors"
              aria-label="Close modal"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
        {/* Body */}
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
};

export default Modal;
