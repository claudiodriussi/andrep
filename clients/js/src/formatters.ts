/**
 * formatters.ts — Client-side formatter registry.
 *
 * Only formatters listed here are applied by the JS engine before storing
 * values in compiled records.  All other formatters (upper, lower, .2, img,
 * barcode, …) are intentionally left to the Python renderer, which applies
 * them at render time using the formatter chain in the template cell content.
 *
 * Adding a formatter here means: the value stored in values[] is already
 * formatted.  Python will encounter an unknown formatter name and fall through
 * to str(value), so the pre-formatted value is used as-is.  This is the
 * "JS-only formatter" pattern.
 *
 * Built-in demo: `capitalize` — Title Case on every word.
 */

export type FormatterFn = (value: unknown, fmt: string) => unknown;

// Built-in JS formatters (applied locally; unknown to the Python renderer).
const BUILTIN: Record<string, FormatterFn> = {
  capitalize: (value) => {
    if (value == null) return "";
    return String(value)
      .toLowerCase()
      .replace(/(?:^|\s)\S/g, (c) => c.toUpperCase());
  },
};

/**
 * Apply a single formatter to a value.
 *
 * - If the formatter name is registered (built-in or custom), it is applied.
 * - Otherwise the value is returned unchanged — Python will handle it.
 *
 * @param value    - Raw or partially-formatted value.
 * @param fmt      - Formatter string, e.g. "capitalize", "upper", ".2".
 * @param customs  - Per-engine custom formatters (checked before built-ins).
 */
export function applyFormatter(
  value: unknown,
  fmt: string,
  customs: Record<string, FormatterFn> = {}
): unknown {
  const name = fmt.split(",")[0].trim();

  const fn = customs[name] ?? BUILTIN[name];
  if (fn) return fn(value, fmt);

  // Not a JS formatter — return unchanged; Python will handle it.
  return value;
}
