export interface BorderSide {
  width: number;
  style: 'none' | 'solid' | 'dashed' | 'dotted' | 'double';
  color: string;
}

export interface CellBorders {
  top: BorderSide;
  bottom: BorderSide;
  left: BorderSide;
  right: BorderSide;
}

export interface CellStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold';
  fontStyle: 'normal' | 'italic';
  textDecoration: 'none' | 'underline' | 'line-through';
  color: string;
  backgroundColor: string;
  alignment: 'left' | 'center' | 'right' | 'justify';
  verticalAlignment: 'top' | 'middle' | 'bottom';
  paddingTop: number;
  paddingBottom: number;
  paddingLeft: number;
  paddingRight: number;
  borders: CellBorders;
}

export type CellType = 'text' | 'markdown' | 'image' | 'barcode' | 'qrcode' | 'embed';

// Semantics of the `content` field by cell type:
//   text     — plain text with [VAR|formatter] interpolation
//   markdown — markdown with [VAR|formatter] interpolation; renderer converts to HTML
//   image    — URL, relative path, or data URI; may contain [VAR] that resolves to one of these
//   barcode  — value to encode (string/number or [VAR])
//   qrcode   — value to encode (URL, text, or [VAR])
//   embed    — unused (the band name is in embedTarget)

export interface Cell {
  id: string;
  content: string;
  type: CellType;
  embedTarget?: string;               // only when type === 'embed': name of the band to expand inside this cell
  x: number;
  width: number;
  height: number;
  wrap: boolean;          // word wrap: text wraps to multiple lines
  autoStretch: boolean;   // height adapts to content (true = renderer measures and expands the cell)
  rotation?: 0 | 90 | 180 | 270;     // text rotation in degrees (0 = default)
  cssExtra?: string;                   // additional CSS properties string appended to inline style
  style: CellStyle;
}

export interface Row {
  id: string;
  name: string; // band name — multiple rows sharing the same name form a band
  cells: Cell[];
}

export type PagePreset = 'A5' | 'A4' | 'A3' | 'Letter' | 'Legal' | 'custom';

export interface PageConfig {
  preset: PagePreset;
  width: number;
  height: number;
  marginTop: number;
  marginBottom: number;
  marginLeft: number;
  marginRight: number;
  orientation: 'portrait' | 'landscape';
  locale: string;    // e.g. 'it-IT' — for date/number formatting in the renderer
  currency: string;  // e.g. 'EUR'
  columns?: number;    // number of columns for label/multi-column layouts (default: 1)
  columnGap?: number;  // horizontal gap between columns in px (default: 0)
}

export interface BandOptions {
  keepTogether?: boolean; // if true, all rows of this band are kept on the same page
  columns?: number;       // number of columns for multi-column bands (default: 1)
  columnGap?: number;     // horizontal gap between columns in px (default: 0)
}

export type CompositionRuleType = 'IfNot' | 'Replace' | 'InsBefore' | 'InsAfter';

export interface CompositionRule {
  rule: CompositionRuleType;
  target: string; // name of the external template to merge
}

export interface Template {
  _type: 'andrep-template'; // file signature — used to validate on load
  name: string;
  version: string;
  page: PageConfig;
  rows: Row[];
  bands?: Record<string, BandOptions>; // per-band options keyed by band name
  composition?: CompositionRule[];
}

// Toolbar group identifiers — controls order and visibility
export type ToolbarGroupId = 'file' | 'colors' | 'borders' | 'font' | 'align' | 'cell' | 'structure';

export interface EditorConfig {
  _type: 'andrep-config'; // file signature — used to validate on load
  locale: 'en' | 'it';
  draftMode: 'single' | 'session'; // 'single' = one shared draft; 'session' = one draft per tab (lost on close)
  units: 'px' | 'mm' | 'inch';
  // Defaults applied when creating a new template
  defaultPreset: PagePreset;
  defaultMargins: { top: number; bottom: number; left: number; right: number };
  // Default locale/currency for new templates (empty = not set)
  defaultLocale: string;
  defaultCurrency: string;
  toolbarGroups: ToolbarGroupId[]; // ordered list; absent groups are hidden
  defaultFont: string;
  defaultFontSize: number;
  bandNamePresets: string[]; // quick-pick list shown on "+ Row"
  showRenderingHints: boolean; // show page_role chips on "+ Row" and var-ref in cell dialog
  fontFamilies: string[]; // font family list shown in the font picker
  fgPalette: string[]; // foreground (text / border) color swatches
  bgPalette: string[]; // background color swatches
}
