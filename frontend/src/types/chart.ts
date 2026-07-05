/* ── Chart type definitions mirroring backend API ─────── */

export type ChartType =
  | 'natal'
  | 'transit'
  | 'progressed'
  | 'solar_return'
  | 'synastry_composite'
  | 'event';

export type BodyKey =
  | 'sun' | 'moon' | 'mercury' | 'venus' | 'mars'
  | 'jupiter' | 'saturn' | 'uranus' | 'neptune' | 'pluto'
  | 'north_node' | 'south_node' | 'chiron'
  | 'asc' | 'mc' | 'dsc' | 'ic'
  | 'lilith' | 'part_of_fortune';

export type AspectType =
  | 'conjunction' | 'sextile' | 'square' | 'trine' | 'opposition'
  | 'quincunx' | 'semi_sextile' | 'semi_square' | 'sesquiquadrate';

export type HouseSystem = 'P' | 'W' | 'K' | 'E' | 'R' | 'C' | 'V';

export type SignName =
  | 'aries' | 'taurus' | 'gemini' | 'cancer'
  | 'leo' | 'virgo' | 'libra' | 'scorpio'
  | 'sagittarius' | 'capricorn' | 'aquarius' | 'pisces';

export type Dignity =
  | 'domicile' | 'exaltation' | 'detriment' | 'fall' | 'peregrine';

export type RenderMode = 'replace' | 'overlay' | 'split';

/* ── Interfaces ──────────────────────────────────────── */

export interface ChartLocation {
  latitude: number;
  longitude: number;
  time_zone: string;
  location_name?: string;
}

export interface ChartBody {
  body_key: BodyKey;
  longitude: number;
  latitude?: number;
  sign: SignName;
  sign_degree: number;
  house: number | null;
  speed: number;
  is_retrograde: boolean;
  dignity: Dignity | null;
}

export interface ChartHouse {
  house_number: number;
  cusps_longitude: number;
  sign: SignName;
  sign_degree: number;
}

export interface ChartAspect {
  body_a_key: BodyKey;
  body_b_key: BodyKey;
  aspect_type: AspectType;
  orb: number;
  is_applying: boolean | null;
  is_major: boolean;
}

export interface ChartMetadata {
  ephemeris_version?: string;
  calculation_library?: string;
  house_system?: string;
}

export interface ChartPayload {
  id: string;
  chart_type: ChartType;
  user_id?: string;
  calculation_date: string;
  location?: ChartLocation;
  house_system: HouseSystem;
  latitude?: number;
  longitude?: number;
  time_zone?: string;
  location_name?: string;
  title?: string;
  bodies: ChartBody[];
  houses: ChartHouse[];
  aspects: ChartAspect[];
  metadata: ChartMetadata;
  created_at?: string;
}

export interface ChartSummary {
  id: string;
  chart_type: ChartType;
  calculation_date: string;
  sun: ChartBody | null;
  moon: ChartBody | null;
  rising: ChartBody | null;
  key_aspects: ChartAspect[];
}

/* ── Transit types ───────────────────────────────────── */

export interface TransitEvent {
  date: string;
  exact_date: string;
  transiting_body: BodyKey;
  natal_body: BodyKey;
  aspect_type: AspectType;
  orb: number;
  is_stationing: boolean;
  is_entering_sign: boolean;
}

export interface RetrogradePeriod {
  body: BodyKey;
  station_retrograde: string;
  station_direct: string;
  affected_natal_houses: number[];
}

export interface TransitSnapshot {
  natal_chart_id: string;
  date_from: string;
  date_to: string;
  events: TransitEvent[];
  retrograde_periods: RetrogradePeriod[];
}

/* ── Synastry types ──────────────────────────────────── */

export interface SynastryHouseOverlay {
  body_key: BodyKey;
  in_partner_house: number;
  partner_chart_id: string;
}

export interface SynastryScore {
  emotional: number;
  communication: number;
  passion: number;
  commitment: number;
  overall: number;
}

export interface SynastryPayload {
  id: string;
  chart_a: ChartPayload;
  chart_b: ChartPayload;
  relationship_type?: string;
  inter_aspects: ChartAspect[];
  house_overlays: SynastryHouseOverlay[];
  composite_chart?: ChartPayload;
  score_summary?: SynastryScore;
  render_mode?: 'bi_wheel' | 'composite' | 'aspect_table';
}

/* ── Life Phase types ────────────────────────────────── */

export interface LifePhase {
  id: number;
  phase_key: string;
  title: string;
  start_date: string;
  end_date: string | null;
  dominant_transits: Record<string, unknown> | null;
  description: string | null;
}
