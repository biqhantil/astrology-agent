/* ── Aspect type color and label mapping ─────────────── */

import type { AspectType } from '../types/chart';

export interface AspectStyle {
  color: string;
  label: string;
  strokeWidth: number;
  strokeDasharray?: string;
  opacity: number;
}

const aspectStyles: Record<AspectType, AspectStyle> = {
  conjunction: {
    color: '#a855f7',
    label: '☌ Conjunction',
    strokeWidth: 2.5,
    opacity: 0.85,
  },
  sextile: {
    color: '#22c55e',
    label: '⚹ Sextile',
    strokeWidth: 1.5,
    strokeDasharray: '6,4',
    opacity: 0.7,
  },
  square: {
    color: '#ef4444',
    label: '□ Square',
    strokeWidth: 2,
    opacity: 0.8,
  },
  trine: {
    color: '#3b82f6',
    label: '△ Trine',
    strokeWidth: 2,
    strokeDasharray: '8,3',
    opacity: 0.75,
  },
  opposition: {
    color: '#f97316',
    label: '☍ Opposition',
    strokeWidth: 2.5,
    opacity: 0.85,
  },
  quincunx: {
    color: '#a3a3a3',
    label: '⚻ Quincunx',
    strokeWidth: 1,
    strokeDasharray: '3,3',
    opacity: 0.5,
  },
  semi_sextile: {
    color: '#a3a3a3',
    label: '⚺ Semi-sextile',
    strokeWidth: 1,
    strokeDasharray: '2,3',
    opacity: 0.4,
  },
  semi_square: {
    color: '#fca5a5',
    label: '∠ Semi-square',
    strokeWidth: 1,
    strokeDasharray: '4,4',
    opacity: 0.5,
  },
  sesquiquadrate: {
    color: '#fca5a5',
    label: '⚼ Sesquiquadrate',
    strokeWidth: 1,
    strokeDasharray: '4,2,2,2',
    opacity: 0.5,
  },
};

export function getAspectStyle(aspect: AspectType): AspectStyle {
  return aspectStyles[aspect] ?? aspectStyles.conjunction;
}

export function getAspectColor(aspect: AspectType): string {
  return getAspectStyle(aspect).color;
}
