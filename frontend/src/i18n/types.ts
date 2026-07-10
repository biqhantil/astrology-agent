/** Supported UI locales (BCP 47). Default: en-US. */
export type Locale = 'en-US' | 'pt-BR';

export const LOCALES: readonly Locale[] = ['en-US', 'pt-BR'] as const;

export const DEFAULT_LOCALE: Locale = 'en-US';

export const LOCALE_STORAGE_KEY = 'astro_locale';

/** BCP 47 tags used for Intl / toLocaleDateString */
export const LOCALE_BCP47: Record<Locale, string> = {
  'en-US': 'en-US',
  'pt-BR': 'pt-BR',
};

export const LOCALE_LABEL: Record<Locale, string> = {
  'en-US': 'English (US)',
  'pt-BR': 'Português (BR)',
};

export type MessageTree = {
  [key: string]: string | MessageTree;
};
