/**
 * Capa i18n JAIOS — preparada para múltiples idiomas.
 * Por ahora: español (es-DO) único.
 */
import { esDO, type LocaleMessages } from "./locales/es-DO";

const DEFAULT_LOCALE = "es-DO";

const catalogs: Record<string, LocaleMessages> = {
  "es-DO": esDO,
};

export function getLocale(): string {
  return DEFAULT_LOCALE;
}

export function t(): LocaleMessages {
  return catalogs[DEFAULT_LOCALE] ?? esDO;
}

export { esDO };
