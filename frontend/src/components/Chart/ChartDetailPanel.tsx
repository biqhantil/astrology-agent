/* ── Chart Details — two columns: Natal | Aspects ── */

import type { FC } from 'react';
import type { ChartPayload } from '../../types/chart';
import { bodyGlyph } from '../../utils/glyphs';
import { useI18n } from '../../i18n/I18nContext';

interface ChartDetailPanelProps {
  natalChart: ChartPayload;
  aspectChart?: ChartPayload | null;
  aspectTitle?: string;
}

const DIGNITY_STYLE: Record<string, string> = {
  domicile: 'text-emerald-400',
  exaltation: 'text-sky-400',
  detriment: 'text-red-400',
  fall: 'text-orange-400',
  peregrine: 'text-zinc-500',
};

const ChartDetailPanel: FC<ChartDetailPanelProps> = ({
  natalChart,
  aspectChart,
  aspectTitle,
}) => {
  const { t } = useI18n();
  const aspectsSource = aspectChart ?? natalChart;
  const majorAspects = aspectsSource.aspects.filter((a) => a.is_major).slice(0, 24);
  const title = aspectTitle ?? t('chart.natalAspects');

  const bodyName = (key: string) => t(`body.${key}`);
  const signName = (sign: string) => t(`sign.${sign}`);
  const digShort = (d: string | null | undefined) =>
    d ? t(`dignity.${d}`) : '';

  if (!natalChart.bodies.length) {
    return <div className="p-4 text-zinc-500 text-sm">{t('common.noChartData')}</div>;
  }

  return (
    <div className="h-full flex flex-col bg-black text-[#f5f0e6]">
      <div className="flex-1 min-h-0 flex divide-x divide-amber-500/15">
        <section className="flex-1 min-w-0 flex flex-col">
          <header className="shrink-0 px-2.5 py-2.5 border-b border-amber-500/20">
            <div className="text-[10px] tracking-[0.28em] uppercase text-amber-400 font-semibold">
              {t('chart.natal')}
            </div>
            <div className="text-[11px] text-zinc-500 mt-0.5 truncate">
              {natalChart.location_name ?? t('chart.birthChart')}
            </div>
          </header>
          <div className="flex-1 min-h-0 overflow-y-auto px-1.5 py-1.5 space-y-0.5">
            {natalChart.bodies.map((body) => (
              <div
                key={body.body_key}
                className="grid grid-cols-[1.5rem_minmax(0,1fr)_1.75rem] items-center gap-x-1.5 py-1.5 px-1 rounded hover:bg-zinc-900/70"
              >
                <span
                  className="text-center text-base leading-none text-amber-300"
                  title={bodyName(body.body_key)}
                >
                  {bodyGlyph(body.body_key)}
                </span>
                <div className="min-w-0 overflow-hidden">
                  <div className="text-[12px] font-semibold text-[#f5f0e6] truncate leading-tight">
                    {bodyName(body.body_key)}
                  </div>
                  <div className="text-[11px] text-zinc-400 font-mono truncate leading-tight mt-0.5">
                    {body.is_retrograde && <span className="text-red-400 mr-0.5">℞</span>}
                    <span className="text-amber-200/90">{signName(body.sign)}</span>
                    {' '}
                    {body.sign_degree.toFixed(1)}°
                    {body.house != null && (
                      <span className="text-zinc-600 ml-1">H{body.house}</span>
                    )}
                  </div>
                </div>
                <span
                  className={`text-[9px] font-semibold uppercase tracking-wide text-right ${
                    DIGNITY_STYLE[body.dignity ?? ''] ?? 'text-zinc-600'
                  }`}
                  title={body.dignity ?? undefined}
                >
                  {digShort(body.dignity)}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="flex-1 min-w-0 flex flex-col">
          <header className="shrink-0 px-2.5 py-2.5 border-b border-amber-500/20">
            <div className="text-[10px] tracking-[0.28em] uppercase text-amber-400 font-semibold">
              {title}
            </div>
            <div className="text-[11px] text-zinc-500 mt-0.5 truncate">
              {majorAspects.length} {t('common.major')}
            </div>
          </header>
          <div className="flex-1 min-h-0 overflow-y-auto px-1.5 py-1.5 space-y-0.5">
            {majorAspects.length === 0 ? (
              <p className="text-zinc-600 text-xs px-1 py-2">{t('common.noMajorAspects')}</p>
            ) : (
              majorAspects.map((a, i) => (
                <div
                  key={i}
                  className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_2rem] items-center gap-x-0.5 px-1 py-1.5 text-[11px] rounded hover:bg-zinc-900/70"
                >
                  <span className="font-medium text-zinc-200 truncate text-right">
                    {bodyName(a.body_a_key)}
                  </span>
                  <span
                    className="text-amber-500/90 text-[9px] uppercase tracking-wide px-0.5 shrink-0"
                    title={a.aspect_type}
                  >
                    {a.aspect_type.slice(0, 4)}
                  </span>
                  <span className="font-medium text-zinc-200 truncate">
                    {bodyName(a.body_b_key)}
                  </span>
                  <span className="text-[10px] text-zinc-500 font-mono text-right tabular-nums">
                    {a.orb.toFixed(1)}°
                  </span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default ChartDetailPanel;
