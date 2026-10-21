// Band names with a fixed meaning — same as PAGE_ROLES / DETAIL_BAND in
// renderer/andrep/renderer.py and clients/js/src/engine.ts.
// Page roles are placed by the renderer at page breaks; the detail band
// (one emission per data row) is a convention for the consumers of the records.

export const DETAIL_BAND = 'band';

export const PAGE_ROLES = ['first_header', 'page_header', 'page_footer', 'last_footer', 'page_filler'];

// Reserved names in the order offered by "+ Row", with what each one does (passed through _())
export const RESERVED_BANDS: { name: string; hint: string }[] = [
  { name: DETAIL_BAND,    hint: 'Detail: once per data row' },
  { name: 'first_header', hint: 'Top of the first page' },
  { name: 'page_header',  hint: 'Top of every page' },
  { name: 'page_footer',  hint: 'Bottom of every page' },
  { name: 'last_footer',  hint: 'Bottom of the last page' },
  { name: 'page_filler',  hint: 'Fills the space before the footer' },
];

export function isReservedBand(name: string): boolean {
  return RESERVED_BANDS.some((b) => b.name === name);
}
