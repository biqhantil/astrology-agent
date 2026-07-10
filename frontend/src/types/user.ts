/* ── User & Auth types ───────────────────────────────── */

export interface UserPublic {
  id: string;
  email?: string;
  display_name?: string;
  locale: string;
  created_at: string;
  last_active_at: string;
}

export interface UserUpdate {
  display_name?: string;
  locale?: string;
}

export interface AnonymousLoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  expires_at: string;
}

export interface SessionResponse {
  user_id: string;
  token_type: string;
  auth_provider: string;
  issued_at: string;
  expires_at: string;
}

export interface DevLoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
  expires_at: string;
}

export interface GoogleLoginRequest {
  credential: string;
}

export interface GoogleLoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
  email?: string;
  expires_at: string;
}

export type AuthProvider = 'anonymous' | 'google' | 'dev';

export interface BirthProfile {
  id: string;
  user_id: string;
  birth_date: string;
  birth_time?: string;
  time_zone: string;
  utc_offset?: string;
  latitude: number;
  longitude: number;
  location_name?: string;
  house_system: string;
  has_unknown_time: boolean;
  sun_sign?: string;
  moon_sign?: string;
  rising_sign?: string;
  updated_at: string;
}

export interface BirthProfileCreate {
  birth_date: string;
  birth_time?: string;
  time_zone: string;
  latitude: number;
  longitude: number;
  location_name?: string;
  house_system?: string;
}

export interface ChartCreate {
  chart_type: string;
  calculation_date: string;
  location: {
    latitude: number;
    longitude: number;
    time_zone: string;
    location_name?: string;
  };
  house_system?: string;
}
