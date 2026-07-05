/* ── Preset prompt chips for quick questions ─────────── */

import type { FC } from 'react';

export interface PresetChip {
  id: string;
  label: string;
  prompt: string;
  icon?: string;
}

const defaultPresets: PresetChip[] = [
  {
    id: 'daily',
    label: 'Daily',
    prompt: 'What do the stars say about today? Give me a daily astrological forecast.',
    icon: '☀️',
  },
  {
    id: 'weekly',
    label: 'Weekly',
    prompt: 'Give me a weekly astrological forecast for this week.',
    icon: '📅',
  },
  {
    id: 'my-chart',
    label: 'My Chart',
    prompt: 'Show me my natal chart and explain the main placements.',
    icon: '♄',
  },
  {
    id: 'saturn-return',
    label: 'Saturn Return',
    prompt: 'Tell me about my Saturn return. When is it and what does it mean?',
    icon: '⏳',
  },
  {
    id: 'transits',
    label: 'Current Transits',
    prompt: 'What are the current transits affecting my chart?',
    icon: '🪐',
  },
  {
    id: 'year-ahead',
    label: 'Year Ahead',
    prompt: 'Give me a year-ahead forecast based on my chart.',
    icon: '🌟',
  },
];

interface PresetPromptChipsProps {
  /** Optional custom preset list */
  presets?: PresetChip[];
  /** Called when a chip is clicked — receives the full prompt text */
  onSelect: (prompt: string) => void;
  /** If true, chips are disabled (e.g., during streaming) */
  disabled?: boolean;
}

/**
 * Horizontal scrollable row of preset prompt chips.
 * Users tap a chip to instantly send that prompt to the astrologer.
 */
const PresetPromptChips: FC<PresetPromptChipsProps> = ({
  presets = defaultPresets,
  onSelect,
  disabled = false,
}) => {
  if (presets.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 px-3 py-2">
      {presets.map((chip) => (
        <button
          key={chip.id}
          onClick={() => onSelect(chip.prompt)}
          disabled={disabled}
          className="chip flex items-center gap-1 text-xs"
          title={chip.prompt}
        >
          {chip.icon && <span className="text-xs">{chip.icon}</span>}
          {chip.label}
        </button>
      ))}
    </div>
  );
};

export { defaultPresets };
export default PresetPromptChips;
