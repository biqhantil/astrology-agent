/* ── Birth Profile Form — esoteric side-by-side layout ── */

import { useState, useMemo, useCallback, useRef, useEffect, type FC, type FormEvent } from 'react';
import { post, put } from '../../api/client';
import CelestialSystem from './CelestialSystem';
import type { BirthProfile, BirthProfileCreate } from '../../types';
import { useI18n } from '../../i18n/I18nContext';

interface BirthProfileFormProps {
  onSaved: (profile: BirthProfile) => void;
  existingProfile?: BirthProfile | null;
}

const TIMEZONES = [
  'Pacific/Pago_Pago', 'Pacific/Honolulu', 'America/Anchorage',
  'America/Los_Angeles', 'America/Phoenix', 'America/Denver',
  'America/Chicago', 'America/New_York', 'America/Halifax',
  'America/St_Johns', 'America/Sao_Paulo', 'America/Argentina/Buenos_Aires',
  'Atlantic/Azores', 'UTC', 'Europe/London', 'Europe/Berlin',
  'Europe/Paris', 'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam',
  'Europe/Moscow', 'Asia/Dubai', 'Asia/Kolkata', 'Asia/Bangkok',
  'Asia/Shanghai', 'Asia/Tokyo', 'Asia/Seoul', 'Australia/Sydney',
  'Pacific/Auckland',
];

const HOUSE_SYSTEMS: { value: string; label: string; desc: string }[] = [
  { value: 'P', label: 'Placidus', desc: 'Most common' },
  { value: 'W', label: 'Whole Sign', desc: 'Ancient' },
  { value: 'K', label: 'Koch', desc: 'German' },
  { value: 'E', label: 'Equal', desc: 'Equal 30°' },
  { value: 'R', label: 'Regiomontanus', desc: 'Renaissance' },
  { value: 'C', label: 'Campanus', desc: 'Vertical-based' },
  { value: 'V', label: 'Vehlow', desc: 'Modified Equal' },
];

const SIGNS = [
  'aries', 'taurus', 'gemini', 'cancer',
  'leo', 'virgo', 'libra', 'scorpio',
  'sagittarius', 'capricorn', 'aquarius', 'pisces',
];

const SIGN_GLYPH: Record<string, string> = {
  aries: '♈', taurus: '♉', gemini: '♊', cancer: '♋',
  leo: '♌', virgo: '♍', libra: '♎', scorpio: '♏',
  sagittarius: '♐', capricorn: '♑', aquarius: '♒', pisces: '♓',
};

const SIGN_ELEMENT: Record<string, string> = {
  aries: 'fire', leo: 'fire', sagittarius: 'fire',
  taurus: 'earth', virgo: 'earth', capricorn: 'earth',
  gemini: 'air', libra: 'air', aquarius: 'air',
  cancer: 'water', scorpio: 'water', pisces: 'water',
};

const ELEMENT_COLOR: Record<string, string> = {
  fire: 'bg-orange-500/10 border-orange-500/20 text-orange-400',
  earth: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
  air: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400',
  water: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
};

function computeSunSign(birthDate: string): string {
  if (!birthDate) return '';
  const [y, m, d] = birthDate.split('-').map(Number);
  const val = m * 100 + d;
  const ranges = [
    [321, 419], [420, 520], [521, 620], [621, 722],
    [723, 822], [823, 922], [923, 1022], [1023, 1121],
    [1122, 1221], [1222, 1231], [101, 119], [120, 218],
    [219, 320],
  ];
  const signMap = [
    'aries', 'taurus', 'gemini', 'cancer',
    'leo', 'virgo', 'libra', 'scorpio',
    'sagittarius', 'capricorn', 'aquarius', 'pisces',
    'pisces',
  ];
  for (let i = 0; i < ranges.length; i++) {
    if (val >= ranges[i][0] && val <= ranges[i][1]) return signMap[i];
  }
  return 'capricorn';
}

// ── Calendar Dropdown ──────────────────────────────────

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DAYS = ['Su','Mo','Tu','We','Th','Fr','Sa'];
const YEARS = Array.from({ length: 151 }, (_, i) => 1900 + i); // 1900–2050

interface DatePickerProps {
  value: string;
  onChange: (v: string) => void;
}

function DatePicker({ value, onChange }: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const parsed = value ? new Date(value + 'T12:00:00') : new Date();
  const [viewYear, setViewYear] = useState(parsed.getFullYear());
  const [viewMonth, setViewMonth] = useState(parsed.getMonth());

  useEffect(() => {
    if (value) {
      const d = new Date(value + 'T12:00:00');
      setViewYear(d.getFullYear());
      setViewMonth(d.getMonth());
    } else {
      const d = new Date();
      setViewYear(d.getFullYear());
      setViewMonth(d.getMonth());
    }
  }, [value]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const firstDow = new Date(viewYear, viewMonth, 1).getDay();
  const weeks: (number | null)[][] = [];
  let row: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) row.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    row.push(d);
    if (row.length === 7) { weeks.push(row); row = []; }
  }
  if (row.length) { while (row.length < 7) row.push(null); weeks.push(row); }

  const selectedDate = value ? new Date(value + 'T12:00:00') : null;
  const display = selectedDate
    ? `${MONTHS[selectedDate.getMonth()]} ${selectedDate.getDate()}, ${selectedDate.getFullYear()}`
    : '';

  const isToday = (d: number) => {
    const today = new Date();
    return d === today.getDate() && viewMonth === today.getMonth() && viewYear === today.getFullYear();
  };
  const isSelected = (d: number) =>
    selectedDate && d === selectedDate.getDate() && viewMonth === selectedDate.getMonth() && viewYear === selectedDate.getFullYear();

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(!open)}
        className="input-field w-full text-left flex items-center justify-between gap-2">
        <span className={display ? 'text-beige-light' : 'text-zinc-600'}>
          {display || 'Select birth date'}
        </span>
        <span className="text-zinc-500">📅</span>
      </button>
      {open && (
        <div className="absolute top-full mt-1 left-0 z-50 w-72 bg-[#121212] border border-zinc-800/40 rounded-xl shadow-2xl shadow-black/60 p-3 animate-fade-in">
          {/* Month / Year selectors */}
          <div className="flex items-center gap-2 mb-3">
            <select value={viewMonth} onChange={e => setViewMonth(Number(e.target.value))}
              className="flex-1 bg-zinc-900 border border-zinc-800 text-beige text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:border-accent/40">
              {MONTHS.map((m, i) => (
                <option key={m} value={i}>{m}</option>
              ))}
            </select>
            <select value={viewYear} onChange={e => setViewYear(Number(e.target.value))}
              className="flex-1 bg-zinc-900 border border-zinc-800 text-beige text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:border-accent/40">
              {YEARS.map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          {/* Day grid */}
          <div className="grid grid-cols-7 gap-0.5 text-center">
            {DAYS.map(d => (
              <div key={d} className="text-zinc-600 text-[10px] py-1 font-medium">{d}</div>
            ))}
            {weeks.flat().map((d, i) => (
              <button key={i} type="button" disabled={d === null}
                onClick={() => {
                  if (d === null) return;
                  const m = `${viewMonth + 1}`.padStart(2, '0');
                  const day = `${d}`.padStart(2, '0');
                  onChange(`${viewYear}-${m}-${day}`);
                  setOpen(false);
                }}
                className={`text-xs py-1.5 rounded transition-colors ${
                  d === null ? '' :
                  isSelected(d) ? 'bg-accent/25 text-accent-light font-medium' :
                  isToday(d) ? 'border border-accent/30 text-beige' :
                  'text-zinc-300 hover:bg-zinc-800'
                }`}>
                {d ?? ''}
              </button>
            ))}
          </div>
          {/* Quick today button */}
          <button type="button" onClick={() => {
            const t = new Date();
            const m = `${t.getMonth() + 1}`.padStart(2, '0');
            const day = `${t.getDate()}`.padStart(2, '0');
            onChange(`${t.getFullYear()}-${m}-${day}`);
            setOpen(false);
          }}
            className="mt-2 w-full text-center text-[10px] text-zinc-600 hover:text-zinc-400 py-1 rounded transition-colors">
            Today
          </button>
        </div>
      )}
    </div>
  );
}

// ── City Search (Nominatim) ────────────────────────────

interface CityResult {
  display_name: string;
  lat: string;
  lon: string;
}

function CitySearch({
  onSelect,
  initialQuery = '',
}: {
  onSelect: (name: string, lat: number, lng: number) => void;
  initialQuery?: string;
}) {
  const { t, bcp47 } = useI18n();
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<CityResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const search = useCallback((q: string) => {
    setQuery(q);
    if (timer.current) clearTimeout(timer.current);
    if (q.length < 2) { setResults([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=5&addressdetails=1`,
          { headers: { 'Accept-Language': bcp47, 'User-Agent': 'AstrologyAgent/1.0' } }
        );
        const data = await res.json();
        setResults(data);
        setOpen(true);
      } catch { setResults([]); } finally { setLoading(false); }
    }, 300);
  }, [bcp47]);

  return (
    <div ref={ref} className="relative">
      <input type="text" value={query}
        onChange={e => search(e.target.value)}
        placeholder={t('profile.searchCity')}
        className="input-field w-full"
      />
      {loading && <span className="absolute right-3 top-3 text-zinc-500 text-xs">…</span>}
      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 left-0 z-50 w-full glass-card rounded-xl max-h-48 overflow-y-auto animate-fade-in">
          {results.map((r, i) => (
            <button key={i} type="button"
              onClick={() => {
                onSelect(r.display_name, parseFloat(r.lat), parseFloat(r.lon));
                setQuery(r.display_name.split(',')[0]);
                setOpen(false);
              }}
              className="w-full text-left px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800/50 border-b border-zinc-800/30 last:border-0">
              {r.display_name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Searchable Timezone ────────────────────────────────

function TimezoneSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = TIMEZONES.filter(tz => tz.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <input type="text" value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        placeholder="Search timezone..."
        className="input-field w-full"
      />
      {open && filtered.length > 0 && (
        <div className="absolute top-full mt-1 left-0 z-50 w-full glass-card rounded-xl max-h-40 overflow-y-auto animate-fade-in">
          {filtered.map(tz => (
            <button key={tz} type="button"
              onClick={() => { onChange(tz); setQuery(tz); setOpen(false); }}
              className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                value === tz ? 'text-accent-light bg-accent/10' : 'text-zinc-300 hover:bg-zinc-800/50'
              }`}>
              {tz}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Default birth data (prefill for new profiles) ──────
// 9 November 2000 · 19:30 · São Paulo, Brazil
const DEFAULT_BIRTH = {
  birthDate: '2000-11-09',
  birthTime: '19:30',
  timeZone: 'America/Sao_Paulo',
  locationName: 'São Paulo, Brazil',
  latitude: '-23.550520',
  longitude: '-46.633308',
  houseSystem: 'P',
} as const;

// ── Main component ─────────────────────────────────────

const BirthProfileForm: FC<BirthProfileFormProps> = ({ onSaved, existingProfile }) => {
  const [birthDate, setBirthDate] = useState(
    existingProfile?.birth_date ?? DEFAULT_BIRTH.birthDate,
  );
  const [birthTime, setBirthTime] = useState(
    existingProfile?.birth_time?.slice(0, 5) ?? DEFAULT_BIRTH.birthTime,
  );
  const [timeZone, setTimeZone] = useState(
    existingProfile?.time_zone ?? DEFAULT_BIRTH.timeZone,
  );
  const [locationName, setLocationName] = useState(
    existingProfile?.location_name ?? DEFAULT_BIRTH.locationName,
  );
  const [latitude, setLatitude] = useState(
    existingProfile?.latitude != null
      ? existingProfile.latitude.toString()
      : DEFAULT_BIRTH.latitude,
  );
  const [longitude, setLongitude] = useState(
    existingProfile?.longitude != null
      ? existingProfile.longitude.toString()
      : DEFAULT_BIRTH.longitude,
  );
  const [houseSystem, setHouseSystem] = useState(
    existingProfile?.house_system ?? DEFAULT_BIRTH.houseSystem,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { t } = useI18n();

  const sunSign = computeSunSign(birthDate);
  const element = sunSign ? SIGN_ELEMENT[sunSign] ?? '' : '';
  const elementColor = element ? ELEMENT_COLOR[element] : '';

  const handleCitySelect = useCallback((name: string, lat: number, lng: number) => {
    setLocationName(name);
    setLatitude(lat.toFixed(6));
    setLongitude(lng.toFixed(6));
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    if (!birthDate || !timeZone || !latitude || !longitude) {
      setError(t('profile.requiredFields'));
      setSaving(false);
      return;
    }
    const payload: BirthProfileCreate = {
      birth_date: birthDate,
      time_zone: timeZone,
      latitude: parseFloat(latitude),
      longitude: parseFloat(longitude),
      house_system: houseSystem,
      location_name: locationName || undefined,
    };
    if (birthTime) payload.birth_time = birthTime + ':00';
    try {
      const profile = existingProfile
        ? await put<BirthProfile>('/v1/me/profile', payload)
        : await post<BirthProfile>('/v1/me/profile', payload);
      onSaved(profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('profile.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="relative h-full w-full bg-black overflow-hidden">
      {/* ── Full-viewport starfield + planets ─── */}
      <div className="absolute inset-0">
        <CelestialSystem />
      </div>

      {/* ── Floating form card (right side) ─── */}
      <div className="absolute top-4 right-4 bottom-4 z-30
        w-[clamp(320px,40vw,520px)] max-h-[80vh]
        overflow-y-auto rounded-2xl
        bg-black/50 backdrop-blur-2xl
        border border-zinc-800/20
        shadow-2xl shadow-black/60 form-scroll">
        <div className="p-5 md:p-6 animate-fade-in">
          {/* Header */}
          <div className="mb-6">
            <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-accent/10 border border-accent/20 mb-3">
              <span className="text-lg">♄</span>
            </div>
            <h1 className="text-lg font-light tracking-widest uppercase text-beige mb-0.5">
              {t('profile.title')}
            </h1>
            <p className="text-zinc-600 text-[11px] tracking-wide">
              {t('profile.subtitle')}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {/* Date */}
            <div>
              <label className="block text-[10px] tracking-wider uppercase text-zinc-500 mb-1">
                {t('profile.birthDate')} <span className="text-accent">*</span>
              </label>
              <DatePicker value={birthDate} onChange={setBirthDate} />
            </div>

            {/* Time */}
            <div>
              <label className="block text-[10px] tracking-wider uppercase text-zinc-500 mb-1">
                {t('profile.birthTime')}{' '}
                <span className="text-zinc-700 font-normal normal-case">{t('profile.optional')}</span>
              </label>
              <input type="time" value={birthTime}
                onChange={e => setBirthTime(e.target.value)}
                className="input-field w-full" />
            </div>

            {/* Sun sign preview */}
            {sunSign && (
              <div className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${elementColor} animate-fade-in`}>
                <span className="text-lg">{SIGN_GLYPH[sunSign]}</span>
                <div className="flex-1">
                  <span className="text-sm font-medium">{t(`sign.${sunSign}`)}</span>
                </div>
                <span className="text-xs capitalize text-zinc-500">{element}</span>
              </div>
            )}

            {/* Timezone */}
            <div>
              <label className="block text-[10px] tracking-wider uppercase text-zinc-500 mb-1">
                {t('profile.timezone')} <span className="text-accent">*</span>
              </label>
              <TimezoneSelect value={timeZone} onChange={setTimeZone} />
            </div>

            {/* City / Place of Birth */}
            <div>
              <label className="block text-[10px] tracking-wider uppercase text-zinc-500 mb-1">
                {t('profile.placeOfBirth')}
              </label>
              <CitySearch
                onSelect={handleCitySelect}
                initialQuery={locationName || DEFAULT_BIRTH.locationName}
              />
            </div>

            {/* Lat / Lng */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] tracking-wider uppercase text-zinc-500 mb-1">
                  {t('profile.latitude')} <span className="text-accent">*</span>
                </label>
                <input type="number" step="any" value={latitude}
                  onChange={e => setLatitude(e.target.value)}
                  placeholder="0.000000" required
                  className="input-field w-full text-xs" />
              </div>
              <div>
                <label className="block text-[10px] tracking-wider uppercase text-zinc-500 mb-1">
                  {t('profile.longitude')} <span className="text-accent">*</span>
                </label>
                <input type="number" step="any" value={longitude}
                  onChange={e => setLongitude(e.target.value)}
                  placeholder="0.000000" required
                  className="input-field w-full text-xs" />
              </div>
            </div>

            {/* House System */}
            <div>
              <label className="block text-[10px] tracking-wider uppercase text-zinc-500 mb-1">
                {t('profile.houseSystem')}
              </label>
              <div className="grid grid-cols-4 gap-1.5">
                {HOUSE_SYSTEMS.map(hs => (
                  <button key={hs.value} type="button" onClick={() => setHouseSystem(hs.value)}
                    className={`text-center px-2 py-1.5 rounded-lg text-[10px] transition-all duration-200 border ${
                      houseSystem === hs.value
                        ? 'border-accent/40 bg-accent/10 text-beige'
                        : 'border-zinc-800/40 bg-black/30 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300'
                    }`}>
                    <div className="font-medium">{hs.label}</div>
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="text-red-400/90 text-xs bg-red-400/5 border border-red-400/10 px-3 py-2 rounded-lg">
                {error}
              </div>
            )}

            <button type="submit" disabled={saving}
              className="btn-primary w-full py-3 text-xs tracking-widest">
              {saving ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t('profile.saving')}
                </span>
              ) : t('profile.save')}
            </button>
          </form>

          <p className="text-center text-zinc-800 text-[10px] mt-5 tracking-wide">
            {t('profile.footer')}
          </p>
        </div>
      </div>

      {/* ── Brand watermark ─── */}
      <div className="hidden md:block absolute bottom-6 left-6 z-20 pointer-events-none">
        <p className="text-zinc-800 text-[10px] tracking-[0.3em] uppercase">Sidereus Nuncius</p>
      </div>
    </div>
  );
};

export default BirthProfileForm;
