// Minimal template types — mirrors editor/src/lib/types.ts (standalone copy).

export interface CellStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: "normal" | "bold";
  fontStyle: "normal" | "italic";
  textDecoration: "none" | "underline" | "line-through";
  color: string;
  backgroundColor: string;
  alignment: "left" | "center" | "right" | "justify";
  verticalAlignment: "top" | "middle" | "bottom";
  paddingTop: number;
  paddingBottom: number;
  paddingLeft: number;
  paddingRight: number;
  borders: {
    top: { width: number; style: string; color: string };
    bottom: { width: number; style: string; color: string };
    left: { width: number; style: string; color: string };
    right: { width: number; style: string; color: string };
  };
}

export interface Cell {
  id: string;
  content: string;
  type: "text" | "markdown" | "image" | "barcode" | "qrcode" | "embed";
  embedTarget?: string;
  x: number;
  width: number;
  height: number;
  wrap: boolean;
  autoStretch: boolean;
  rotation?: 0 | 90 | 180 | 270;
  cssExtra?: string;
  style: CellStyle;
}

export interface Row {
  id: string;
  name: string;
  cells: Cell[];
}

export interface BandOptions {
  keepTogether?: boolean;
  columns?: number;
  columnGap?: number;
}

export interface CompositionRule {
  rule: "IfNot" | "Replace" | "InsBefore" | "InsAfter";
  target: string;
}

export interface Template {
  _type: "andrep-template";
  name: string;
  version: string;
  page: {
    preset: string;
    width: number;
    height: number;
    marginTop: number;
    marginBottom: number;
    marginLeft: number;
    marginRight: number;
    orientation: "portrait" | "landscape";
    locale: string;
    currency: string;
    columns?: number;
    columnGap?: number;
  };
  rows: Row[];
  bands?: Record<string, BandOptions>;
  composition?: CompositionRule[];
}

// ---------------------------------------------------------------------------
// Compiled records format (consumed by python -m andrep render)
// ---------------------------------------------------------------------------

export type ScalarValue = string | number | boolean | null;

export interface CompiledRecord {
  band: string;
  /** One raw value per expression token, in declaration order across all cells. */
  values?: ScalarValue[];
  /** One CSS string per cell (including embed cells), same order as values. */
  css_extras?: string[];
  /** CSS applied to all cells of this band emission. */
  band_css?: string;
  /** Sub-records for embed cells, keyed by cell.id. */
  embeds?: Record<string, CompiledRecord>;
}

// ---------------------------------------------------------------------------
// Parsed token — one per [expr|fmt|fmt] group in a content string
// ---------------------------------------------------------------------------

export interface Token {
  /** Literal text before this token (may be empty). */
  text: string;
  /** Expression string, null for pure-literal tokens. */
  expr: string | null;
  /** Formatter chain (may be empty). */
  fmts: string[];
}

// ---------------------------------------------------------------------------
// Engine state — accessible as _r in template expressions
// ---------------------------------------------------------------------------

export interface EngineState {
  curBand: string;
  lastBand: string;
  started: boolean;
  count: number;
  bandCount: Record<string, number>;
  title: string;
  date: string;   // dd/mm/yyyy
  time: string;   // HH:MM:SS
  user: string;
}
