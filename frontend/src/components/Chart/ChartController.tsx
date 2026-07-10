/* ── Chart Controller — wheel + monthly timeline ── */

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
  type FC,
  type RefObject,
} from 'react';
import { post } from '../../api/client';
import { useChartContext } from '../../context/ChartContext';
import ZodiacWheel from './ZodiacWheel';
import type { BirthProfile, ChartPayload, ChartCreate } from '../../types';
import { useI18n } from '../../i18n/I18nContext';

export type AnalysisScope = 'day' | 'month' | 'year';

interface ChartControllerProps {
  natalChart: ChartPayload;
  profile: BirthProfile;
  onSkyChartChange?: (chart: ChartPayload | null, selectedDate: Date) => void;
  onAskAnalysis?: (date: Date, scope: AnalysisScope) => void;
}

function useWheelSize(min = 320, max = 900): [RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState(560);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const next = Math.floor(Math.min(el.clientWidth, el.clientHeight) - 8);
      setSize(Math.max(min, Math.min(max, next)));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [min, max]);

  return [ref, size];
}

function parseBirthDate(profile: BirthProfile): Date {
  const [y, m, day] = profile.birth_date.split('-').map(Number);
  return new Date(y, (m ?? 1) - 1, day ?? 1);
}

/** Calendar months from birth month → target month (0 = birth month). */
function monthsBetween(birth: Date, target: Date): number {
  return (
    (target.getFullYear() - birth.getFullYear()) * 12 +
    (target.getMonth() - birth.getMonth())
  );
}

function addMonths(birth: Date, offset: number): Date {
  // Anchor non-birth months on the 15th for a stable monthly sky snapshot
  if (offset === 0) {
    return new Date(birth.getFullYear(), birth.getMonth(), birth.getDate());
  }
  return new Date(birth.getFullYear(), birth.getMonth() + offset, 15);
}

function toIsoLocalDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function toMonthInputValue(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

const ChartController: FC<ChartControllerProps> = ({
  natalChart,
  profile,
  onSkyChartChange,
  onAskAnalysis,
}) => {
  const { state } = useChartContext();
  const { loading, error } = state;
  const { t, formatDate } = useI18n();
  const [containerRef, wheelSize] = useWheelSize(320, 920);

  const birth = useMemo(() => parseBirthDate(profile), [profile.birth_date]);

  const totalMonths = useMemo(() => {
    const endByAge = new Date(birth.getFullYear() + 100, birth.getMonth(), 1);
    const forecast = new Date();
    forecast.setFullYear(forecast.getFullYear() + 5);
    forecast.setDate(1);
    const end = endByAge > forecast ? endByAge : forecast;
    return Math.max(1, monthsBetween(birth, end));
  }, [birth]);

  const [monthOffset, setMonthOffset] = useState(() =>
    Math.min(totalMonths, Math.max(0, monthsBetween(birth, new Date()))),
  );

  const selectedDate = useMemo(
    () => addMonths(birth, monthOffset),
    [birth, monthOffset],
  );

  const isBirthMonth = monthOffset === 0;
  const [skyChart, setSkyChart] = useState<ChartPayload | null>(null);
  const [skyLoading, setSkyLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    onSkyChartChange?.(isBirthMonth ? natalChart : skyChart, selectedDate);
  }, [isBirthMonth, natalChart, skyChart, selectedDate, onSkyChartChange]);

  useEffect(() => {
    if (isBirthMonth) {
      setSkyChart(null);
      setSkyLoading(false);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    setSkyLoading(true);

    debounceRef.current = setTimeout(async () => {
      try {
        const iso = toIsoLocalDate(selectedDate);
        const birthTime = profile.birth_time ?? '12:00:00';
        const time = birthTime.length === 5 ? `${birthTime}:00` : birthTime;
        const body: ChartCreate = {
          chart_type: 'event',
          calculation_date: `${iso}T${time}`,
          location: {
            latitude: Number(profile.latitude),
            longitude: Number(profile.longitude),
            time_zone: profile.time_zone,
            location_name: profile.location_name ?? undefined,
          },
          house_system: (profile.house_system as ChartCreate['house_system']) || 'P',
        };
        const chart = await post<ChartPayload>('/v1/charts', body);
        setSkyChart(chart);
      } catch (e) {
        console.warn('Sky chart fetch failed', e);
        setSkyChart(null);
      } finally {
        setSkyLoading(false);
      }
    }, 280);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [selectedDate, isBirthMonth, profile, monthOffset]);

  useEffect(() => {
    if (!menuOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [menuOpen]);

  const displayChart = isBirthMonth ? natalChart : (skyChart ?? natalChart);

  const monthLabel = formatDate(selectedDate, {
    month: 'long',
    year: 'numeric',
  });
  const dayLabel = formatDate(selectedDate, {
    month: 'long',
    day: 'numeric',
  });

  const jumpToday = useCallback(() => {
    setMonthOffset(Math.min(totalMonths, Math.max(0, monthsBetween(birth, new Date()))));
  }, [birth, totalMonths]);

  const jumpBirth = useCallback(() => setMonthOffset(0), []);

  const ask = (scope: AnalysisScope) => {
    setMenuOpen(false);
    onAskAnalysis?.(selectedDate, scope);
  };

  if (loading && !natalChart) {
    return (
      <div className="flex items-center justify-center h-full bg-black text-amber-500/60">
        <svg className="animate-spin h-9 w-9" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (error && !natalChart) {
    return (
      <div className="flex items-center justify-center h-full p-8 bg-black">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="relative h-full flex flex-col bg-black">
      {/* Large date — month-forward */}
      <div className="absolute top-3 right-4 z-10 text-right pointer-events-none select-none">
        <div className="text-[11px] tracking-[0.35em] uppercase text-amber-500/80 font-medium">
          {isBirthMonth ? t('chart.natalMonth') : t('chart.skyFor')}
        </div>
        <div className="text-3xl sm:text-4xl font-semibold text-[#f5f0e6] leading-tight tracking-tight mt-0.5">
          {formatDate(selectedDate, { month: 'long' })}
        </div>
        <div className="text-2xl sm:text-3xl text-amber-300/90 font-medium tabular-nums">
          {selectedDate.getFullYear()}
        </div>
        {isBirthMonth ? (
          <div className="text-[12px] text-zinc-500 mt-0.5">{t('chart.born')} {dayLabel}</div>
        ) : (
          <div className="text-[12px] text-zinc-500 mt-0.5">{t('chart.midMonthSky')} · {dayLabel}</div>
        )}
        {skyLoading && !isBirthMonth && (
          <div className="text-[11px] text-amber-500/70 mt-1">{t('chart.updatingChart')}</div>
        )}
      </div>

      <div
        ref={containerRef}
        className="flex-1 min-h-0 flex items-center justify-center overflow-hidden pt-2 pb-1"
      >
        <ZodiacWheel chart={displayChart} size={wheelSize} />
      </div>

      <div className="shrink-0 border-t border-amber-500/15 bg-black/95 px-4 pt-3 pb-3 space-y-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={jumpBirth}
            className="text-[11px] font-semibold tracking-wide text-zinc-500 hover:text-amber-300 shrink-0"
            title={t('chart.jumpBirth')}
          >
            {t('chart.birth')}
          </button>
          <input
            type="range"
            min={0}
            max={totalMonths}
            step={1}
            value={monthOffset}
            onChange={(e) => setMonthOffset(Number(e.target.value))}
            className="flex-1 h-1.5 accent-amber-500 cursor-pointer"
            aria-label={t('chart.timelineAria')}
            aria-valuetext={monthLabel}
          />
          <button
            type="button"
            onClick={jumpToday}
            className="text-[11px] font-semibold tracking-wide text-zinc-500 hover:text-amber-300 shrink-0"
            title={t('chart.jumpToday')}
          >
            {t('chart.today')}
          </button>
          <input
            type="month"
            value={toMonthInputValue(selectedDate)}
            min={toMonthInputValue(birth)}
            max={toMonthInputValue(addMonths(birth, totalMonths))}
            onChange={(e) => {
              if (!e.target.value) return;
              const [y, m] = e.target.value.split('-').map(Number);
              const next = new Date(y, m - 1, 1);
              setMonthOffset(Math.min(totalMonths, Math.max(0, monthsBetween(birth, next))));
            }}
            className="bg-zinc-950 border border-zinc-800 text-zinc-300 text-[12px] rounded px-2 py-1 font-mono shrink-0 focus:outline-none focus:border-amber-500/40"
            aria-label={t('chart.selectMonth')}
          />
        </div>

        <div className="flex items-center justify-between gap-3 flex-wrap">
          <p className="text-[11px] text-zinc-600">
            {isBirthMonth
              ? t('chart.natalHint')
              : `${t('chart.monthlySky')} · ${monthLabel}`}
          </p>

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-200 text-[12px] font-semibold tracking-wide transition-colors"
            >
              <span>{t('chart.askAgent')}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
            {menuOpen && (
              <div className="absolute bottom-full right-0 mb-2 w-56 rounded-lg border border-amber-500/25 bg-zinc-950 shadow-xl shadow-black/60 py-1 z-20">
                <div className="px-3 py-1.5 text-[10px] uppercase tracking-widest text-zinc-500">
                  {t('chart.scope')}
                </div>
                {(
                  [
                    ['month', t('chart.thisMonth'), monthLabel],
                    ['year', t('chart.thisYear'), String(selectedDate.getFullYear())],
                    ['day', t('chart.midMonthDay'), toIsoLocalDate(selectedDate)],
                  ] as const
                ).map(([scope, label, detail]) => (
                  <button
                    key={scope}
                    type="button"
                    onClick={() => ask(scope)}
                    className="w-full text-left px-3 py-2.5 hover:bg-amber-500/10 transition-colors"
                  >
                    <div className="text-[13px] font-medium text-[#f5f0e6]">{label}</div>
                    <div className="text-[11px] text-zinc-500 mt-0.5">{detail}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChartController;
