// Unit conversion utilities — 96 DPI base (CSS standard)

const PX_PER_MM   = 96 / 25.4;  // ≈ 3.7795 px/mm
const PX_PER_INCH = 96;

export function pxToMm(px: number): number   { return px / PX_PER_MM; }
export function mmToPx(mm: number): number   { return Math.round(mm * PX_PER_MM); }
export function pxToInch(px: number): number { return px / PX_PER_INCH; }
export function inchToPx(i: number): number  { return Math.round(i * PX_PER_INCH); }

// Page setup uses mm or inch — never raw px (unintuitive for paper dimensions)
export type PageUnit = 'mm' | 'inch';

export function pageUnitFromConfig(u: 'px' | 'mm' | 'inch'): PageUnit {
  return u === 'inch' ? 'inch' : 'mm';
}

// px ↔ display unit (rounded for UI inputs)
export function pxToPageUnit(px: number, u: PageUnit): number {
  return u === 'inch'
    ? Math.round(px / PX_PER_INCH * 100) / 100   // 2 decimals for inches
    : Math.round(px / PX_PER_MM   * 10)  / 10;   // 1 decimal for mm
}

export function pageUnitToPx(val: number, u: PageUnit): number {
  return u === 'inch' ? Math.round(val * PX_PER_INCH) : Math.round(val * PX_PER_MM);
}

// mm ↔ display unit (for preset detection / apply)
export function mmToPageUnit(mm: number, u: PageUnit): number {
  return u === 'inch'
    ? Math.round(mm / 25.4 * 100) / 100
    : Math.round(mm * 10) / 10;
}
export function pageUnitToMm(val: number, u: PageUnit): number {
  return u === 'inch' ? val * 25.4 : val;
}

export function pageUnitLabel(u: PageUnit): string { return u === 'inch' ? 'in' : 'mm'; }
export function pageUnitStep(u: PageUnit): number  { return u === 'inch' ? 0.01 : 0.5;  }

// Standard page sizes in mm (portrait)
import type { PagePreset } from './types';

export const PAGE_SIZES: Record<string, { wMm: number; hMm: number }> = {
  A6:     { wMm: 105, hMm: 148 },
  A5:     { wMm: 148, hMm: 210 },
  A4:     { wMm: 210, hMm: 297 },
  A3:     { wMm: 297, hMm: 420 },
  Letter: { wMm: 216, hMm: 279 },
  Legal:  { wMm: 216, hMm: 356 },
};

// Returns width/height in px for a preset + orientation (falls back to A4 portrait)
export function presetToPx(
  preset: PagePreset,
  orientation: 'portrait' | 'landscape',
): { width: number; height: number } {
  const size = PAGE_SIZES[preset];
  if (!size) return { width: mmToPx(210), height: mmToPx(297) };
  const wMm = orientation === 'portrait' ? size.wMm : size.hMm;
  const hMm = orientation === 'portrait' ? size.hMm : size.wMm;
  return { width: mmToPx(wMm), height: mmToPx(hMm) };
}

// Ruler tick generation — returns ticks for a ruler of width `rulerWidth` px
export interface RulerTick {
  x: number;
  h: number;
  label?: string;
}

export function rulerTicks(rulerWidth: number, units: 'px' | 'mm' | 'inch'): RulerTick[] {
  const ticks: RulerTick[] = [];

  if (units === 'mm') {
    const ppm = PX_PER_MM;
    for (let mm = 1; mm * ppm <= rulerWidth; mm++) {
      const x = mm * ppm;
      if      (mm % 10 === 0) ticks.push({ x, h: 11, label: String(mm) });
      else if (mm % 5  === 0) ticks.push({ x, h: 7 });
      else                    ticks.push({ x, h: 4 });
    }
  } else if (units === 'inch') {
    // Steps of 1/16"
    const step = PX_PER_INCH / 16;
    for (let i = 1; i * step <= rulerWidth; i++) {
      const x = i * step;
      if      (i % 16 === 0) ticks.push({ x, h: 11, label: String(i / 16) });
      else if (i % 4  === 0) ticks.push({ x, h: 7 });
      else                   ticks.push({ x, h: 3 });
    }
  } else {
    // px — steps of 10
    for (let p = 10; p <= rulerWidth; p += 10) {
      if      (p % 100 === 0) ticks.push({ x: p, h: 11, label: String(p) });
      else if (p % 50  === 0) ticks.push({ x: p, h: 7 });
      else                    ticks.push({ x: p, h: 4 });
    }
  }

  return ticks;
}
