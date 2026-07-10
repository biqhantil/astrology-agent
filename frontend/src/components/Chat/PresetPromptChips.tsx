/* ── Preset prompt chips for quick questions ─────────── */

import { useMemo, type FC } from 'react';
import { useI18n } from '../../i18n/I18nContext';

export interface PresetChip {
  id: string;
  label: string;
  prompt: string;
  icon?: string;
}

interface PresetPromptChipsProps {
  presets?: PresetChip[];
  onSelect: (prompt: string) => void;
  disabled?: boolean;
}

const PresetPromptChips: FC<PresetPromptChipsProps> = ({
  presets: customPresets,
  onSelect,
  disabled = false,
}) => {
  const { t } = useI18n();

  const presets = useMemo(() => {
    if (customPresets) return customPresets;
    return [
      {
        id: 'daily',
        label: t('presets.daily'),
        prompt: t('presets.dailyPrompt'),
        icon: '☀️',
      },
      {
        id: 'weekly',
        label: t('presets.weekly'),
        prompt: t('presets.weeklyPrompt'),
        icon: '📅',
      },
      {
        id: 'my-chart',
        label: t('presets.myChart'),
        prompt: t('presets.myChartPrompt'),
        icon: '♄',
      },
      {
        id: 'saturn-return',
        label: t('presets.saturnReturn'),
        prompt: t('presets.saturnReturnPrompt'),
        icon: '⏳',
      },
      {
        id: 'transits',
        label: t('presets.transits'),
        prompt: t('presets.transitsPrompt'),
        icon: '🪐',
      },
      {
        id: 'year-ahead',
        label: t('presets.yearAhead'),
        prompt: t('presets.yearAheadPrompt'),
        icon: '🌟',
      },
    ];
  }, [customPresets, t]);

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

export default PresetPromptChips;
