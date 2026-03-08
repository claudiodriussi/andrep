import { config } from '$lib/store/config.svelte';
import it from './it';

const translations: Record<string, Record<string, string>> = { it };

// gettext-style translation function.
// The key IS the English string — no separate EN file needed.
// Falls back to the key itself if no translation is found.
export function _(key: string): string {
  const locale = config.config.locale;
  if (locale === 'en') return key;
  return translations[locale]?.[key] ?? key;
}
