/* ── User / Assistant Avatar ─────────────────────────── */

import type { FC } from 'react';

interface AvatarProps {
  /** 'user' or 'assistant' (or any string for initial extraction) */
  role: string;
  /** Optional image URL */
  src?: string;
  /** Optional name for initials fallback */
  name?: string;
  /** Size in pixels (default: 32) */
  size?: number;
}

/**
 * Avatar component for chat bubbles.
 *
 * Displays a user icon, assistant icon, or image.
 */
const Avatar: FC<AvatarProps> = ({ role, src, name, size = 32 }) => {
  const isUser = role === 'user';
  const initials = name
    ? name.slice(0, 2).toUpperCase()
    : isUser
      ? 'U'
      : 'A';

  if (src) {
    return (
      <img
        src={src}
        alt={name ?? role}
        className="rounded-full object-cover flex-shrink-0"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      className={`rounded-full flex items-center justify-center flex-shrink-0 font-semibold text-xs ${
        isUser
          ? 'bg-accent-dark text-white'
          : 'bg-surface-light text-accent-light'
      }`}
      style={{ width: size, height: size }}
      title={name ?? role}
    >
      {isUser ? (
        <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      ) : (
        <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      )}
    </div>
  );
};

export default Avatar;
