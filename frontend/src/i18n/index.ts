import enUS from './messages/en-US';
import ptBR from './messages/pt-BR';
import {
  DEFAULT_LOCALE,
  LOCALES,
  LOCALE_BCP47,
  LOCALE_LABEL,
  LOCALE_STORAGE_KEY,
  type Locale,
  type MessageTree,
} from './types';

export {
  DEFAULT_LOCALE,
  LOCALES,
  LOCALE_BCP47,
  LOCALE_LABEL,
  LOCALE_STORAGE_KEY,
  type Locale,
};

const catalog: Record<Locale, MessageTree> = {
  'en-US': enUS,
  'pt-BR': ptBR,
};

export function isLocale(value: string | null | undefined): value is Locale {
  return value === 'en-US' || value === 'pt-BR';
}

export function resolveLocale(raw?: string | null): Locale {
  if (isLocale(raw)) return raw;
  // Accept loose tags
  if (raw?.toLowerCase().startsWith('pt')) return 'pt-BR';
  if (raw?.toLowerCase().startsWith('en')) return 'en-US';
  return DEFAULT_LOCALE;
}

export function loadStoredLocale(): Locale {
  try {
    return resolveLocale(localStorage.getItem(LOCALE_STORAGE_KEY));
  } catch {
    return DEFAULT_LOCALE;
  }
}

export function storeLocale(locale: Locale): void {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {
    /* ignore */
  }
}

function getPath(tree: MessageTree, path: string): string | undefined {
  const parts = path.split('.');
  let cur: string | MessageTree | undefined = tree;
  for (const p of parts) {
    if (cur == null || typeof cur === 'string') return undefined;
    cur = cur[p];
  }
  return typeof cur === 'string' ? cur : undefined;
}

export type TranslateParams = Record<string, string | number>;

/**
 * Translate a dotted key. Falls back to en-US, then the key itself.
 * Interpolates ``{{name}}`` placeholders from params.
 */
export function translate(
  locale: Locale,
  key: string,
  params?: TranslateParams,
): string {
  const primary = getPath(catalog[locale], key);
  const fallback =
    locale === DEFAULT_LOCALE ? undefined : getPath(catalog[DEFAULT_LOCALE], key);
  let text = primary ?? fallback ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replaceAll(`{{${k}}}`, String(v));
    }
  }
  return text;
}

export function formatDate(
  locale: Locale,
  date: Date,
  options: Intl.DateTimeFormatOptions,
): string {
  return date.toLocaleDateString(LOCALE_BCP47[locale], options);
}
