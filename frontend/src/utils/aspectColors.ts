/* ── Aspect type color and label mapping ─────────────── */

import type { AspectType } from '../types/chart';

export interface AspectStyle {
  color: string;
  label: string;
  strokeWidth: number;
  strokeDasharray?: string;
  opacity: number;
}

/** Brighter aspect colors for pure-black wheel */
const aspectStyles: Record<AspectType, AspectStyle> = {
  conjunction: {
    color: '#c084fc',
    label: '☌ Conjunction',
    strokeWidth: 2.2,
    opacity: 0.9,
  },
  sextile: {
    color: '#4ade80',
    label: '⚹ Sextile',
    strokeWidth: 1.6,
    strokeDasharray: '6,4',
    opacity: 0.85,
  },
  square: {
    color: '#f87171',
    label: '□ Square',
    strokeWidth: 2,
    opacity: 0.9,
  },
  trine: {
    color: '#60a5fa',
    label: '△ Trine',
    strokeWidth: 2,
    strokeDasharray: '8,3',
    opacity: 0.88,
  },
  opposition: {
    color: '#fb923c',
    label: '☍ Opposition',
    strokeWidth: 2.2,
    opacity: 0.9,
  },
  quincunx: {
    color: '#a1a1aa',
    label: '⚻ Quincunx',
    strokeWidth: 1.2,
    strokeDasharray: '3,3',
    opacity: 0.55,
  },
  semi_sextile: {
    color: '#a1a1aa',
    label: '⚺ Semi-sextile',
    strokeWidth: 1,
    strokeDasharray: '2,3',
    opacity: 0.45,
  },
  semi_square: {
    color: '#fca5a5',
    label: '∠ Semi-square',
    strokeWidth: 1.1,
    strokeDasharray: '4,4',
    opacity: 0.55,
  },
  sesquiquadrate: {
    color: '#fca5a5',
    label: '⚼ Sesquiquadrate',
    strokeWidth: 1.1,
    strokeDasharray: '4,2,2,2',
    opacity: 0.55,
  },
};

export function getAspectStyle(aspect: AspectType): AspectStyle {
  return aspectStyles[aspect] ?? aspectStyles.conjunction;
}

export function getAspectColor(aspect: AspectType): string {
  return getAspectStyle(aspect).color;
}
